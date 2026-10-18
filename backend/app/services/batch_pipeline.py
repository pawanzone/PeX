"""Streaming, chunked batch pipeline for PeX (P0.5 demo build).

Reads very large JSON / JSONL / NDJSON / .json.gz files with bounded memory, pushes every record through the
canonical E2E path (``FileWatcherService._process_single_record`` - tokenization, intake audit, 8-predicate
harness, routing via ``transition_case``, persistence, recommendation, disposition audit) and persists each chunk
in ONE database transaction (``repo.begin_batch`` / ``commit_batch``).

Outputs per batch (in ``<BATCH_IO_DIR>/outbox``):
  * ``{batch_id}.results.jsonl``       one line per input record (incl. DUPLICATE / FAILED lines)
  * ``{batch_id}.summary.json``        counts, throughput, mode, ``bank_comm = SIMULATED``
  * ``{batch_id}.bank_handoff.jsonl``  STP-eligible items only, and only when mode != SHADOW (simulated handoff file)

PeX never executes or settles a payment: every handoff line carries ``execution_owner = BANK``.
"""
from __future__ import annotations

import gzip
import io
import hashlib
import json
import logging
import os
import queue
import re
import shutil
import threading
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)

STREAM_SUFFIXES = (".jsonl", ".ndjson", ".json.gz", ".jsonl.gz", ".ndjson.gz")
LARGE_JSON_BYTES = 1_000_000  # plain .json above this goes to the streaming pipeline
TERMINAL = ("COMPLETED", "FAILED")
_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_stream_candidate(p: Path) -> bool:
    n = p.name.lower()
    if n.endswith(STREAM_SUFFIXES):
        return True
    if n.endswith(".json"):
        try:
            return p.stat().st_size > LARGE_JSON_BYTES
        except OSError:
            return False
    return False


# ----------------------------------------------------------------------------------------------
# Streaming parsers
# ----------------------------------------------------------------------------------------------
class _Reader:
    """Opens a file (optionally gzip) as text and exposes progress based on the raw byte position."""

    def __init__(self, path: Path):
        self.path = path
        self.size = max(path.stat().st_size, 1)
        self._raw = open(path, "rb")
        stream: Any = self._raw
        if path.name.lower().endswith(".gz"):
            stream = gzip.GzipFile(fileobj=self._raw)
        self.text = io.TextIOWrapper(stream, encoding="utf-8-sig", errors="strict", newline=None)

    @property
    def progress(self) -> float:
        try:
            return min(self._raw.tell() / self.size, 1.0)
        except Exception:
            return 0.0

    def close(self):
        try:
            self.text.close()
        finally:
            self._raw.close()


_RECORDS_KEY = re.compile(r'"records"\s*:\s*\[')


def _iter_array_items(text: io.TextIOBase, buf: str = "") -> Iterator[Any]:
    """Yield elements of a JSON array whose '[' has already been consumed (buf = text after it)."""
    dec = json.JSONDecoder()
    idx = 0
    eof = False
    while True:
        # skip whitespace / commas
        while True:
            while idx < len(buf) and buf[idx] in " \t\r\n,":
                idx += 1
            if idx < len(buf) or eof:
                break
            chunk = text.read(1 << 20)
            if not chunk:
                eof = True
            else:
                buf = buf[idx:] + chunk
                idx = 0
        if idx >= len(buf):
            if eof:
                raise ValueError("Unexpected end of file inside JSON array")
        if buf[idx] == "]":
            return
        while True:
            try:
                obj, end = dec.raw_decode(buf, idx)
                break
            except json.JSONDecodeError:
                if eof:
                    raise
                chunk = text.read(1 << 20)
                if not chunk:
                    eof = True
                else:
                    buf = buf[idx:] + chunk
                    idx = 0
        yield obj
        idx = end
        if idx > (1 << 21):
            buf = buf[idx:]
            idx = 0


def iter_records(reader: _Reader, meta: Dict[str, Any]) -> Iterator[Tuple[int, Any, Optional[str]]]:
    """Yield (index, record, parse_error). Malformed JSONL lines yield (idx, None, error)."""
    name = reader.path.name.lower()
    text = reader.text
    if name.endswith((".jsonl", ".ndjson", ".jsonl.gz", ".ndjson.gz")):
        for i, line in enumerate(text):
            line = line.strip()
            if not line:
                continue
            try:
                yield i, json.loads(line), None
            except json.JSONDecodeError as e:
                yield i, None, f"Malformed JSON line {i + 1}: {e.msg}"
        return

    # .json / .json.gz : array, envelope or single record
    head = ""
    while len(head) < (1 << 20):
        chunk = text.read(1 << 16)
        if not chunk:
            break
        head += chunk
        stripped = head.lstrip()
        if stripped[:1] == "[":
            break
        if stripped[:1] == "{" and _RECORDS_KEY.search(head):
            break
        if stripped[:1] == "{" and len(head) > (1 << 19):
            break
    stripped = head.lstrip()
    if stripped[:1] == "[":
        pos = head.index("[") + 1
        for i, rec in enumerate(_iter_array_items(text, head[pos:])):
            yield i, rec, None
        return
    m = _RECORDS_KEY.search(head) if stripped[:1] == "{" else None
    if m:
        prefix = head[: m.start()].rstrip().rstrip(",")
        try:
            env = json.loads(prefix + "}")
            meta.update({k: v for k, v in env.items() if k != "records"})
        except json.JSONDecodeError:
            pass
        for i, rec in enumerate(_iter_array_items(text, head[m.end():])):
            yield i, rec, None
        return
    # single record (bounded: read the rest, it is one record)
    rest = text.read()
    try:
        yield 0, json.loads(head + rest), None
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON: {e.msg}")


# ----------------------------------------------------------------------------------------------
# Pipeline
# ----------------------------------------------------------------------------------------------
class BatchPipeline:
    def __init__(self, base_dir: Optional[Path] = None, watcher: Any = None, chunk_size: Optional[int] = None):
        base = Path(base_dir or getattr(settings, "BATCH_IO_DIR", Path("batch_io"))).resolve()
        self.base = base
        self.inbox = base / "inbox"
        self.outbox = base / "outbox"
        self.archive = base / "archive"
        self.failed = base / "failed"
        self.state_dir = base / "state"
        for d in (self.inbox, self.outbox, self.archive, self.failed, self.state_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.chunk_size = int(chunk_size or getattr(settings, "BATCH_CHUNK_SIZE", 500))
        self._watcher = watcher
        self._lock = threading.Lock()
        self._batches: Dict[str, Dict[str, Any]] = {}
        self._claimed: set = set()
        self._seen_sizes: Dict[str, Tuple[int, float]] = {}
        self._q: "queue.Queue[str]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._load_state()

    # -- state ----------------------------------------------------------------------------------
    def _state_path(self, batch_id: str) -> Path:
        return self.state_dir / f"{batch_id}.json"

    def _persist(self, meta: Dict[str, Any]):
        try:
            tmp = self._state_path(meta["batch_id"]).with_suffix(".tmp")
            tmp.write_text(json.dumps(meta, default=str), encoding="utf-8")
            os.replace(tmp, self._state_path(meta["batch_id"]))
        except Exception as e:  # pragma: no cover
            logger.warning("batch state persist failed: %s", e)

    def _load_state(self):
        for p in sorted(self.state_dir.glob("*.json")):
            try:
                meta = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            bid = meta.get("batch_id")
            if not bid:
                continue
            self._batches[bid] = meta
            if meta.get("status") in ("QUEUED", "PROCESSING"):
                src = meta.get("source_path")
                if src and Path(src).exists():
                    meta["status"] = "QUEUED"
                    meta["note"] = "Resumed after restart (idempotent: already-persisted records are skipped as duplicates)."
                    self._claimed.add(Path(src).name)
                    self._q.put(bid)
                else:
                    meta["status"] = "FAILED"
                    meta["error"] = "Interrupted by restart and source file no longer present."
                    self._persist(meta)
        if not self._q.empty():
            self._ensure_worker()

    def _ensure_worker(self):
        with self._lock:
            if self._worker and self._worker.is_alive():
                return
            self._worker = threading.Thread(target=self._run, name="pex-batch-worker", daemon=True)
            self._worker.start()

    def _get_watcher(self):
        if self._watcher is None:
            from app.services.file_watcher import file_watcher
            self._watcher = file_watcher
        return self._watcher

    # -- public API -----------------------------------------------------------------------------
    def new_batch_id(self, prefix: str = "BATCH") -> str:
        return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    def submit_file(self, path: Path, batch_id: Optional[str] = None, filename: Optional[str] = None,
                    parent_batch_id: Optional[str] = None, source: Optional[str] = None) -> str:
        path = Path(path)
        batch_id = batch_id or self._id_from_name(path)
        meta = {
            "batch_id": batch_id,
            "filename": filename or path.name,
            "source_path": str(path),
            "status": "QUEUED",
            "total": 0, "processed": 0, "failed": 0, "duplicates": 0,
            "progress": 0.0,
            "started_at": None, "finished_at": None,
            "queued_at": _now(),
            "records_per_sec": 0.0,
            "mode": str(getattr(settings, "PEX_OPERATION_MODE", "SHADOW")).upper(),
            "summary": None, "error": None,
            "needs_review": 0, "parent_batch_id": parent_batch_id, "source": source,
        }
        with self._lock:
            self._batches[batch_id] = meta
            self._claimed.add(path.name)
        self._persist(meta)
        self._q.put(batch_id)
        self._ensure_worker()
        return batch_id

    def _id_from_name(self, path: Path) -> str:
        stem = path.name
        for suf in (".json.gz", ".jsonl.gz", ".ndjson.gz", ".jsonl", ".ndjson", ".json"):
            if stem.lower().endswith(suf):
                stem = stem[: -len(suf)]
                break
        bid = _SAFE.sub("_", stem)[:80] or self.new_batch_id()
        if bid in self._batches:
            bid = f"{bid}-{uuid.uuid4().hex[:6].upper()}"
        return bid

    def save_upload(self, filename: str, fileobj, parent_batch_id: Optional[str] = None) -> str:
        """Persist an uploaded stream into the inbox and enqueue it. Returns batch_id."""
        batch_id = self.new_batch_id("UPL" if not parent_batch_id else "RPR")
        safe = _SAFE.sub("_", Path(filename or "upload.json").name)
        dest = self.inbox / f"{batch_id}__{safe}"
        with open(dest, "wb") as out:
            shutil.copyfileobj(fileobj, out, 1 << 20)
        return self.submit_file(dest, batch_id=batch_id, filename=safe, parent_batch_id=parent_batch_id,
                                source="Reprocess" if parent_batch_id else "Upload")

    def scan_inbox(self) -> List[str]:
        """Pick up stable streaming-format files dropped into the inbox. Never touches e2e_fixtures/."""
        started = []
        for p in sorted(self.inbox.iterdir()):
            if not p.is_file() or p.name in self._claimed or p.name.startswith("."):
                continue
            if not is_stream_candidate(p):
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            sig = (st.st_size, st.st_mtime)
            prev = self._seen_sizes.get(p.name)
            self._seen_sizes[p.name] = sig
            if prev != sig or time.time() - st.st_mtime < 1.0:
                continue  # still being written
            started.append(self.submit_file(p, source="Bank adapter"))
        return started

    def claims(self, name: str) -> bool:
        return name in self._claimed

    def list_batches(self) -> List[Dict[str, Any]]:
        with self._lock:
            items = [dict(m) for m in self._batches.values()]
        items.sort(key=lambda m: m.get("queued_at") or "", reverse=True)
        return [self._public(m) for m in items]

    def get_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            m = self._batches.get(batch_id)
            return self._public(dict(m)) if m else None

    @staticmethod
    def _public(m: Dict[str, Any]) -> Dict[str, Any]:
        keys = ("batch_id", "filename", "status", "total", "processed", "failed", "duplicates",
                "progress", "started_at", "finished_at", "records_per_sec", "summary", "mode", "error", "note", "queued_at",
                "needs_review", "parent_batch_id", "source", "stages", "archive")
        return {k: m.get(k) for k in keys}

    def results_path(self, batch_id: str) -> Path:
        return self.outbox / f"{batch_id}.results.jsonl"

    def wait(self, batch_id: str, timeout: float = 600.0) -> Dict[str, Any]:
        end = time.time() + timeout
        while time.time() < end:
            b = self.get_batch(batch_id)
            if b and b["status"] in TERMINAL:
                return b
            time.sleep(0.05)
        raise TimeoutError(batch_id)

    # -- worker ---------------------------------------------------------------------------------
    def _run(self):
        while True:
            try:
                batch_id = self._q.get(timeout=5)
            except queue.Empty:
                return
            meta = self._batches.get(batch_id)
            if not meta:
                continue
            try:
                self._process(meta)
            except Exception as e:  # file-level failure
                logger.exception("batch %s failed", batch_id)
                meta["status"] = "FAILED"
                meta["error"] = f"{type(e).__name__}: {e}"
                meta["finished_at"] = _now()
                src = Path(meta["source_path"])
                if src.exists():
                    try:
                        shutil.move(str(src), str(self.failed / src.name))
                    except Exception:
                        pass
                self._persist(meta)

    def _process(self, meta: Dict[str, Any]):
        from app.schemas.contracts.e2e_schemas import CanonicalE2EInput
        from app.db.repository import PeXDBRepository  # noqa: F401
        from app.services.data_loader import repo

        watcher = self._get_watcher()
        bid = meta["batch_id"]
        src = Path(meta["source_path"])
        meta["status"] = "PROCESSING"
        meta["started_at"] = _now()
        t0 = time.perf_counter()
        counts = {k: Counter() for k in ("status", "queue", "profile", "rail", "currency")}
        stats = {"stp": 0, "amount_total": 0.0, "bank_handoff": 0}
        mode = meta["mode"]
        env_meta: Dict[str, Any] = {}
        seen_ids: set = set()
        seen_uetr: set = set()

        res_path = self.results_path(bid)
        fail_path = self.failed / f"{bid}.failed.jsonl"
        hand_path = self.outbox / f"{bid}.bank_handoff.jsonl"
        res_f = open(res_path, "w", encoding="utf-8")
        fail_f = open(fail_path, "w", encoding="utf-8")
        hand_f = open(hand_path, "w", encoding="utf-8") if mode != "SHADOW" else None

        reader = _Reader(src)
        chunk: List[Tuple[int, Any, Optional[str]]] = []

        def flush():
            if not chunk:
                return
            self._process_chunk(chunk, bid, src, watcher, repo, CanonicalE2EInput, counts, stats, meta,
                                seen_ids, seen_uetr, res_f, fail_f, hand_f, mode)
            chunk.clear()
            self._trim_ports(watcher)
            elapsed = max(time.perf_counter() - t0, 1e-9)
            meta["progress"] = round(reader.progress, 4)
            meta["records_per_sec"] = round((meta["processed"] + meta["failed"] + meta["duplicates"]) / elapsed, 2)
            res_f.flush(); fail_f.flush()
            self._persist(meta)

        try:
            for item in iter_records(reader, env_meta):
                chunk.append(item)
                meta["total"] += 1
                if len(chunk) >= self.chunk_size:
                    flush()
            flush()
        finally:
            reader.close()
            res_f.close(); fail_f.close()
            if hand_f:
                hand_f.close()

        elapsed = max(time.perf_counter() - t0, 1e-9)
        n = meta["processed"] + meta["failed"] + meta["duplicates"]
        summary = {
            "batch_id": bid,
            "source_batch_id": env_meta.get("batch_id"),
            "source_system": env_meta.get("source_system"),
            "filename": meta["filename"],
            "mode": mode,
            "bank_comm": "SIMULATED",
            "execution_owner": "BANK",
            "total_records": meta["total"],
            "processed": meta["processed"],
            "failed": meta["failed"],
            "duplicates": meta["duplicates"],
            "stp_eligible": stats["stp"],
            "bank_handoff_records": stats["bank_handoff"],
            "by_status": dict(counts["status"]),
            "by_queue": dict(counts["queue"]),
            "by_profile": dict(counts["profile"]),
            "by_rail": dict(counts["rail"]),
            "by_currency": dict(counts["currency"]),
            "total_amount_processed": round(stats["amount_total"], 2),
            "elapsed_seconds": round(elapsed, 3),
            "records_per_sec": round(n / elapsed, 2),
            "peak_rss_mb": _peak_rss_mb(),
            "chunk_size": self.chunk_size,
            "started_at": meta["started_at"],
            "finished_at": _now(),
        }
        (self.outbox / f"{bid}.summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        if hand_f is None and hand_path.exists():
            hand_path.unlink()
        if fail_path.exists() and fail_path.stat().st_size == 0:
            fail_path.unlink()
        meta["summary"] = summary
        meta["records_per_sec"] = summary["records_per_sec"]
        meta["progress"] = 1.0
        meta["status"] = "COMPLETED"
        meta["finished_at"] = summary["finished_at"]
        arch_at = _now()
        try:
            shutil.move(str(src), str(self.archive / src.name))
            h = hashlib.sha256()
            with open(self.archive / src.name, "rb") as fh:
                for blk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(blk)
            meta["archive"] = {"archived": True, "checksum": "sha256:" + h.hexdigest(), "verified": True, "at": arch_at,
                               "path": str(self.archive / src.name)}
        except Exception as e:  # pragma: no cover
            logger.warning("archive move failed: %s", e)
            meta["archive"] = {"archived": False, "checksum": None, "verified": False, "at": arch_at}
        meta["stages"] = {"received": meta.get("queued_at"), "schema_checked": meta.get("started_at"),
                          "duplicates_checked": meta.get("started_at"), "cases_created": meta.get("finished_at"), "archived": arch_at}
        summary["needs_review"] = meta.get("needs_review", 0)
        self._persist(meta)

    def _process_chunk(self, chunk, bid, src, watcher, repo, Model, counts, stats, meta,
                       seen_ids, seen_uetr, res_f, fail_f, hand_f, mode):
        # 1) validate
        parsed: List[Tuple[int, Any, Any, Optional[str]]] = []  # idx, raw, model, error
        for idx, raw, perr in chunk:
            if perr:
                parsed.append((idx, raw, None, perr))
                continue
            if not isinstance(raw, dict):
                parsed.append((idx, raw, None, "Record is not a JSON object"))
                continue
            try:
                _m = Model(**raw)
                _pid = (_m.profile_id or "").upper()
                if _pid and not _known_profile(_pid):
                    parsed.append((idx, raw, None, f"Unknown exception type: {_m.profile_id}"))
                else:
                    parsed.append((idx, raw, _m, None))
            except Exception as e:
                msg = str(e).replace("\n", " ")[:400]
                parsed.append((idx, raw, None, f"Schema validation failed: {msg}"))

        # 2) dedupe: DB (bulk) + within batch
        ids = [m.exception_id for _, _, m, _ in parsed if m is not None]
        uetrs = [m.payment_info.uetr for _, _, m, _ in parsed if m is not None and m.payment_info.uetr]
        db_ids = repo.existing_case_ids(ids) if ids else set()
        db_uetr = repo.existing_uetrs(uetrs) if uetrs else set()

        lines: List[Dict[str, Any]] = []
        work: List[Tuple[int, Any, Any]] = []
        for idx, raw, model, err in parsed:
            if err:
                self._fail(meta, counts, fail_f, lines, idx, raw, err)
                continue
            eid = model.exception_id
            u = model.payment_info.uetr
            if eid in db_ids or eid in seen_ids or (u and (u in db_uetr or u in seen_uetr)):
                meta["duplicates"] += 1
                counts["status"]["DUPLICATE"] += 1
                lines.append(self._base_line(idx, model, "DUPLICATE", errors=["Duplicate exception_id/UETR - skipped (idempotent)"]))
                continue
            seen_ids.add(eid)
            if u:
                seen_uetr.add(u)
            work.append((idx, raw, model))

        dupe_of = self._possible_duplicates(work, stats)

        # 3) one transaction per chunk
        if work:
            repo.begin_batch()
            ok_lines: List[Tuple[Dict[str, Any], Any, Any]] = []
            try:
                for idx, raw, model in work:
                    repo.batch_record_begin()
                    try:
                        output, final_status = watcher._process_single_record(
                            e2e_input=model, file_path=Path(meta["filename"]), output_file=None,
                            content_hash="", batch_id=bid, record_index=idx)
                        case = repo.get_case(model.exception_id) or {}
                        ok_lines.append((self._ok_line(idx, model, output, final_status, case), output, model))
                    except Exception as e:
                        repo.batch_record_abort()
                        seen_ids.discard(model.exception_id)
                        if model.payment_info.uetr:
                            seen_uetr.discard(model.payment_info.uetr)
                        self._fail(meta, counts, fail_f, lines, idx, raw, f"Processing error: {type(e).__name__}: {e}")
                repo.commit_batch()
                try:
                    from app.services.v2.core import ext_store
                    ext_store.flush()
                except Exception:  # pragma: no cover
                    pass
            except Exception as e:
                repo.rollback_batch()
                logger.exception("chunk commit failed in %s", bid)
                for ln, _o, m in ok_lines:
                    seen_ids.discard(m.exception_id)
                    self._fail(meta, counts, fail_f, lines, ln["record_index"], m.model_dump(mode="json"),
                               f"Chunk transaction rolled back: {type(e).__name__}: {e}")
                ok_lines = []
            for ln, output, model in ok_lines:
                if model.exception_id in dupe_of:
                    ln["needs_review"] = True
                    ln["possible_duplicate_of"] = dupe_of[model.exception_id]
                    meta["needs_review"] = meta.get("needs_review", 0) + 1
                    try:
                        from app.services.v2.core import ext_store
                        ext_store.patch(model.exception_id, possible_duplicate_of=dupe_of[model.exception_id])
                        ext_store.flush()
                    except Exception:  # pragma: no cover
                        pass
                meta["processed"] += 1
                counts["status"][ln["status"]] += 1
                counts["queue"][ln["queue"]] += 1
                counts["profile"][ln["profile"]] += 1
                counts["rail"][ln["rail"]] += 1
                counts["currency"][ln["currency"]] += 1
                stats["amount_total"] += float(ln["amount"] or 0.0)
                if ln["stp_eligible"]:
                    stats["stp"] += 1
                    if hand_f is not None:
                        hand_f.write(json.dumps(self._handoff_line(bid, ln, output, model)) + "\n")
                        stats["bank_handoff"] += 1
                lines.append(ln)
        lines.sort(key=lambda l: l["record_index"])
        for ln in lines:
            res_f.write(json.dumps(ln, default=str) + "\n")

    @staticmethod
    def _possible_duplicates(work, stats) -> Dict[str, str]:
        """Records that are NOT identical (different id/UETR) but match an existing case, or an earlier record of this
        batch, on payment reference + amount + currency + creditor. Returned as {exception_id: matching_case_id}."""
        out: Dict[str, str] = {}
        if not work:
            return out
        from app.db.models import CaseModel
        from app.db.session import SessionLocal

        def key_of(m):
            p = m.payment_info
            return (p.remittance_info or f"REF-{p.payment_id}", round(float(p.amount), 2), p.currency, (p.creditor_name or "").strip().lower())

        refs = list({key_of(m)[0] for _, _, m in work})
        existing: Dict[Tuple[str, float, str, str], str] = {}
        db = SessionLocal()
        try:
            for i in range(0, len(refs), 500):
                for c in db.query(CaseModel).filter(CaseModel.payment_ref.in_(refs[i:i + 500])).all():
                    cp = c.creditor_party or {}
                    nm = str((cp.get("party_name") if isinstance(cp, dict) else cp) or "").strip().lower()
                    existing.setdefault((c.payment_ref, round(float(c.amount), 2), c.currency, nm), c.case_id)
        except Exception:  # pragma: no cover
            pass
        finally:
            db.close()
        seen = stats.setdefault("dupkeys", {})
        for _, _, m in work:
            k = key_of(m)
            hit = existing.get(k) or seen.get(k)
            if hit and hit != m.exception_id:
                out[m.exception_id] = hit
            seen.setdefault(k, m.exception_id)
        return out

    @staticmethod
    def _trim_ports(watcher, keep: Optional[int] = None):
        """The reference (in-memory) E2E ports retain every envelope/trace/lock for the life of the process.
        That is fine for single files but grows ~15 KB/record in a 100k batch. System of record is the DB;
        keep only the most recent ``keep`` entries (PEX_PORT_RETENTION, default 2000)."""
        keep = keep or int(os.getenv("PEX_PORT_RETENTION", "2000"))
        r = getattr(watcher, "e2e_runner", None)
        if r is None:
            return
        targets = [("evidence_port", "_packages"), ("observability_port", "_traces"), ("bank_handoff_port", "_envelopes"),
                   ("idempotency_port", "_active_locks"), ("idempotency_port", "_execution_history"), ("audit_port", "_chain")]
        for port_name, attr in targets:
            port = getattr(r, port_name, None)
            store = getattr(port, attr, None) if port is not None else None
            try:
                if isinstance(store, dict) and len(store) > keep * 1.25:
                    for k in list(store.keys())[: len(store) - keep]:
                        store.pop(k, None)
                elif isinstance(store, list) and len(store) > keep * 1.25:
                    del store[: len(store) - keep]
            except Exception:  # pragma: no cover
                pass

    # -- line builders --------------------------------------------------------------------------
    @staticmethod
    def _base_line(idx, model, status, errors=None) -> Dict[str, Any]:
        p = model.payment_info
        return {
            "record_index": idx, "exception_id": model.exception_id, "uetr": p.uetr,
            "profile": (model.profile_id or "").upper(), "rail": p.clearing_rail, "currency": p.currency,
            "amount": p.amount, "status": status, "queue": None, "stp_eligible": False,
            "predicates": None, "recommended_action": None, "proposed_changes": [],
            "decision_reason": None, "evidence_summary": None, "errors": errors or [],
            "source_reference": ((getattr(model, "processing_metadata", None) or {}).get("source_reference")
                                 or (getattr(model, "raw_payload", None) or {}).get("source_reference") or model.exception_id),
        }

    def _ok_line(self, idx, model, output, final_status, case) -> Dict[str, Any]:
        ln = self._base_line(idx, model, final_status)
        pb = output.predicate_breakdown
        ln["queue"] = case.get("queue")
        ln["stp_eligible"] = bool(output.stp_eligible)
        ln["predicates"] = {k: bool(getattr(pb, k)) for k in
                            ("e_suff", "r_det", "r_uniq", "v_det", "v_auth", "p_bank", "c_comp", "x_pre")}
        rec = output.resolution_recommendation or {}
        ln["recommended_action"] = (rec.get("action") if isinstance(rec, dict) else None) or output.next_action
        ln["proposed_changes"] = output.repaired_fields or []
        ln["decision_reason"] = output.stp_decision_reason
        ln["evidence_summary"] = {
            "status": output.evidence_status, "used": output.evidence_used,
            "missing": output.evidence_missing, "contradictions": output.evidence_contradictions,
        }
        ln["errors"] = list(output.errors or [])
        ln["dispatch_status"] = case.get("dispatch_status")
        return ln

    def _fail(self, meta, counts, fail_f, lines, idx, raw, err):
        meta["failed"] += 1
        counts["status"]["FAILED"] += 1
        eid = raw.get("exception_id") if isinstance(raw, dict) else None
        pi = (raw.get("payment_info") or {}) if isinstance(raw, dict) else {}
        if not isinstance(pi, dict):
            pi = {}
        lines.append({
            "record_index": idx, "exception_id": eid, "uetr": pi.get("uetr"),
            "profile": (raw.get("profile_id") if isinstance(raw, dict) else None), "rail": pi.get("clearing_rail"),
            "currency": pi.get("currency"), "amount": pi.get("amount"), "status": "FAILED", "queue": None,
            "stp_eligible": False, "predicates": None, "recommended_action": None, "proposed_changes": [],
            "decision_reason": None, "evidence_summary": None, "errors": [err],
            "source_reference": ((raw.get("source_reference") or (raw.get("processing_metadata") or {}).get("source_reference")
                                  or (raw.get("raw_payload") or {}).get("source_reference") or eid) if isinstance(raw, dict) else None),
        })
        fail_f.write(json.dumps({"record_index": idx, "error": err, "record": raw}, default=str) + "\n")

    @staticmethod
    def _handoff_line(bid, ln, output, model) -> Dict[str, Any]:
        return {
            "batch_id": bid, "exception_id": ln["exception_id"], "uetr": ln["uetr"],
            "amount": ln["amount"], "currency": ln["currency"], "clearing_rail": ln["rail"],
            "recommended_action": ln["recommended_action"], "repaired_fields": ln["proposed_changes"],
            "handoff_status": output.bank_handoff_status, "bank_comm": "SIMULATED",
            "execution_owner": "BANK", "note": "Instruction package for the bank's own systems. PeX does not execute or settle.",
        }


def _known_profile(pid: str) -> bool:
    try:
        from app.services.file_watcher import PROFILE_CODE_TO_ENUM
        return pid in PROFILE_CODE_TO_ENUM or pid in {e.value for e in PROFILE_CODE_TO_ENUM.values()}
    except Exception:  # pragma: no cover
        return True


def _peak_rss_mb() -> Optional[float]:
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)
    except Exception:
        return None


_pipeline: Optional[BatchPipeline] = None
_pl_lock = threading.Lock()


def get_pipeline() -> BatchPipeline:
    global _pipeline
    with _pl_lock:
        if _pipeline is None:
            _pipeline = BatchPipeline()
        return _pipeline
