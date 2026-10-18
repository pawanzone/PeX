"""UI v2 batch views, built on the existing batch pipeline (metadata + results.jsonl + failed.jsonl)."""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from app.db.models import CaseModel
from app.db.session import SessionLocal
from app.services.batch_pipeline import get_pipeline, TERMINAL
from app.services.data_loader import repo
from app.services.v2 import logic as lg
from app.services.v2.core import V2Error, bad_state, invalid, not_found, iso, now, ext_store, parse_ts

OUTCOMES = ("accepted", "duplicate", "rejected", "needs_review")
LABEL = {"accepted": "Accepted", "duplicate": "Duplicate", "rejected": "Rejected", "needs_review": "Needs review"}


def _lines(bid: str) -> Iterator[Dict[str, Any]]:
    p = get_pipeline().results_path(bid)
    if not p.exists():
        return
    with open(p, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    yield json.loads(ln)
                except Exception:
                    continue


def outcome_of(ln: Dict[str, Any]) -> str:
    st = ln.get("status")
    if st == "FAILED":
        return "rejected"
    if st == "DUPLICATE":
        return "duplicate"
    if ln.get("needs_review"):
        return "needs_review"
    return "accepted"


_LOC = re.compile(r"for \w+\s+(?P<loc>[\w\.\[\]]+)\s+(?P<msg>.*?)(?:\s+\[type=|$)")


def _humanize(loc: str) -> str:
    last = loc.split(".")[-1]
    last = re.sub(r"\[\d+\]", "", last)
    return last.replace("_", " ")


def friendly_error(err: str) -> str:
    e = (err or "").strip()
    if e.startswith("Schema validation failed"):
        m = _LOC.search(e)
        if m:
            loc, msg = m.group("loc"), m.group("msg").strip()
            if "Field required" in msg or "field required" in msg:
                return f"Missing required field: {_humanize(loc)}"
            if loc.endswith("amount") and ("number" in msg or "float" in msg):
                return "Invalid amount format"
            return f"Invalid value for {_humanize(loc)}: {msg[:120]}"
        return "Record does not match the expected format"
    return e or "Rejected"


def _existing_case_for(ln: Dict[str, Any]) -> Optional[str]:
    eid, uetr = ln.get("exception_id"), ln.get("uetr")
    if eid and repo.get_case(eid):
        return eid
    if uetr:
        db = SessionLocal()
        try:
            r = db.query(CaseModel.case_id).filter(CaseModel.uetr == uetr).first()
            return r[0] if r else None
        finally:
            db.close()
    return None


def detail_of(ln: Dict[str, Any], outcome: str) -> Tuple[str, Optional[str]]:
    if outcome == "rejected":
        return friendly_error((ln.get("errors") or [""])[0]), None
    if outcome == "duplicate":
        cid = _existing_case_for(ln)
        return (f"Duplicate matches {cid}" if cid else "Duplicate of an earlier record"), cid
    if outcome == "needs_review":
        return f"Possible duplicate · not identical (matches {ln.get('possible_duplicate_of')})", ln.get("exception_id")
    q = ln.get("queue") or "worklist"
    return f"Case created · routed to {q}", ln.get("exception_id")


def _item(ln: Dict[str, Any]) -> Dict[str, Any]:
    oc = outcome_of(ln)
    detail, case_id = detail_of(ln, oc)
    action = {"rejected": {"type": "download", "label": "Download"}, "needs_review": {"type": "review", "label": "Review"}}.get(oc, {"type": "view_case", "label": "View case"})
    return {"record": int(ln.get("record_index", 0)) + 1, "source_reference": ln.get("source_reference") or ln.get("exception_id"),
            "case_id": case_id if oc != "rejected" else None, "outcome": oc, "outcome_label": LABEL[oc], "detail": detail, "action": action,
            "exception_id": ln.get("exception_id")}


def source_of(m: Dict[str, Any]) -> str:
    if m.get("source"):
        return m["source"]
    bid = m.get("batch_id", "")
    return "Upload" if bid.startswith("UPL") else ("Synthetic" if bid.startswith("GEN") else ("Reprocess" if bid.startswith("RPR") else "Bank adapter"))


def counts_of(m: Dict[str, Any]) -> Dict[str, int]:
    nr = int(m.get("needs_review") or 0)
    processed = int(m.get("processed") or 0)
    return {"received": int(m.get("total") or 0), "accepted": max(0, processed - nr), "duplicate": int(m.get("duplicates") or 0),
            "rejected": int(m.get("failed") or 0), "needs_review": nr}


def status_label(m: Dict[str, Any], c: Dict[str, int]) -> str:
    st = m.get("status")
    if st in ("QUEUED", "PROCESSING"):
        return "Processing"
    if st == "FAILED":
        return "Failed"
    return "Partially processed" if (c["duplicate"] or c["rejected"] or c["needs_review"]) else "Processed"


def list_batches(page: int, page_size: int) -> Dict[str, Any]:
    items = get_pipeline().list_batches()
    page_size = max(1, min(int(page_size or 25), 200))
    page = max(1, int(page or 1))
    out = []
    for m in items[(page - 1) * page_size: page * page_size]:
        c = counts_of(m)
        out.append({"batch_id": m["batch_id"], "filename": m["filename"], "status": m["status"], "status_label": status_label(m, c),
                    "received_at": m.get("queued_at"), "source": source_of(m), "records": c["received"], "accepted": c["accepted"],
                    "duplicate": c["duplicate"], "rejected": c["rejected"], "needs_review": c["needs_review"],
                    "parent_batch_id": m.get("parent_batch_id")})
    return {"page": page, "page_size": page_size, "total": len(items), "items": out}


def _meta(bid: str) -> Dict[str, Any]:
    m = get_pipeline().get_batch(bid)
    if not m:
        raise not_found(f"Batch {bid}")
    return m


def _handoff_count(bid: str) -> int:
    n = 0
    for cid in ext_store.all_ids():
        e = ext_store.get(cid) or {}
        if (e.get("batch") or {}).get("batch_id") == bid:
            c = repo.get_case(cid)
            if c and lg.status_of(c) in ("DISPATCHED", "EXECUTED_CONFIRMED", "SETTLED"):
                n += 1
    return n


def get_batch(bid: str, tab: str, page: int, page_size: int) -> Dict[str, Any]:
    m = _meta(bid)
    tab = (tab or "all").lower()
    if tab != "all" and tab not in OUTCOMES:
        raise invalid("tab must be all, accepted, duplicate, rejected or needs_review", "tab")
    c = counts_of(m)
    page_size = max(1, min(int(page_size or 25), 200))
    page = max(1, int(page or 1))
    tab_counts = {"all": 0, **{k: 0 for k in OUTCOMES}}
    items: List[Dict[str, Any]] = []
    start, end = (page - 1) * page_size, page * page_size
    seen = 0
    for ln in _lines(bid):
        oc = outcome_of(ln)
        tab_counts["all"] += 1
        tab_counts[oc] += 1
        if tab == "all" or tab == oc:
            if start <= seen < end:
                items.append(_item(ln))
            seen += 1
    st = m.get("stages") or {}
    done = m.get("status") in TERMINAL
    stages = [
        {"key": "received", "label": "Received", "at": st.get("received") or m.get("queued_at"), "state": "done"},
        {"key": "schema", "label": "Schema checked", "at": st.get("schema_checked"), "state": "done" if (done or m.get("status") == "PROCESSING") else "pending"},
        {"key": "duplicates", "label": "Duplicates checked", "at": st.get("duplicates_checked"), "state": "done" if (done or m.get("status") == "PROCESSING") else "pending"},
        {"key": "cases", "label": "Cases created", "at": st.get("cases_created"), "state": "done" if m.get("status") == "COMPLETED" else ("current" if m.get("status") == "PROCESSING" else "pending")},
        {"key": "archived", "label": "Archived", "at": st.get("archived"), "state": "done" if (m.get("archive") or {}).get("archived") else "pending"},
    ]
    total = c["received"]
    parts = f"{c['accepted']} accepted + {c['duplicate']} duplicate + {c['rejected']} rejected + {c['needs_review']} needs review"
    balanced = total == c["accepted"] + c["duplicate"] + c["rejected"] + c["needs_review"]
    sent = _handoff_count(bid)
    kids = [b["batch_id"] for b in get_pipeline().list_batches() if b.get("parent_batch_id") == bid]
    arch = m.get("archive") or {}
    return {
        "batch_id": bid, "filename": m["filename"], "status": m["status"], "status_label": status_label(m, c),
        "received_at": m.get("queued_at"), "source": source_of(m), "records": total, "mode": m.get("mode"),
        "stages": stages, "counts": c,
        "reconciliation": {"balanced": balanced and m.get("status") in TERMINAL,
                           "text": (f"{total} received = {parts}. Nothing lost." if balanced else f"{total} received; {parts}. Still reconciling.")},
        "tab": tab, "tab_counts": tab_counts, "page": page, "page_size": page_size, "total": seen, "items": items,
        "outputs": {"bank_handoff_requests": {"sent": sent, "text": (f"{sent} sent (simulated) · awaiting bank confirmation" if sent else "0 sent · cases not yet approved")},
                    "archive": {"archived": bool(arch.get("archived")), "checksum": arch.get("checksum"), "verified": bool(arch.get("verified")), "at": arch.get("at")}},
        "actions": {"download_rejected": f"/api/v2/batches/{bid}/rejected?format=jsonl" if c["rejected"] else None,
                    "reprocess": {"enabled": False, "reason": "Upload corrected records first" if c["rejected"] else "No rejected records to correct",
                                  "endpoint": f"/api/v2/batches/{bid}/reprocess", "has_rejected": c["rejected"] > 0},
                    "reprocessed_by": kids},
        "parent_batch_id": m.get("parent_batch_id"), "error": m.get("error"),
    }


def record_detail(bid: str, n: int) -> Dict[str, Any]:
    _meta(bid)
    for ln in _lines(bid):
        if int(ln.get("record_index", -1)) + 1 == int(n):
            it = _item(ln)
            raw = None
            fp = get_pipeline().failed / f"{bid}.failed.jsonl"
            if it["outcome"] == "rejected" and fp.exists():
                for fl in fp.read_text(encoding="utf-8").splitlines():
                    try:
                        d = json.loads(fl)
                    except Exception:
                        continue
                    if int(d.get("record_index", -1)) + 1 == int(n):
                        raw = d.get("record")
                        break
            return {"record": int(n), "outcome": it["outcome"], "outcome_label": it["outcome_label"], "detail": it["detail"], "errors": ln.get("errors") or [],
                    "case_id": it["case_id"], "source_reference": it["source_reference"], "raw": raw, "line": {k: ln.get(k) for k in ("exception_id", "uetr", "profile", "rail", "currency", "amount", "status", "queue")}}
    raise not_found(f"Record {n} in batch {bid}")


def rejected_download(bid: str, fmt: str) -> Tuple[bytes, str, str]:
    m = _meta(bid)
    if m["status"] not in TERMINAL:
        raise bad_state("The batch is still processing.")
    fp = get_pipeline().failed / f"{bid}.failed.jsonl"
    recs: List[Dict[str, Any]] = []
    if fp.exists():
        for ln in fp.read_text(encoding="utf-8").splitlines():
            try:
                recs.append(json.loads(ln))
            except Exception:
                continue
    fmt = (fmt or "jsonl").lower()
    if fmt == "jsonl":
        body = "".join(json.dumps(r["record"], default=str) + "\n" for r in recs if isinstance(r.get("record"), dict))
        return body.encode(), "application/x-ndjson", f"{bid}.rejected.jsonl"
    if fmt == "json":
        return json.dumps([{"record": r.get("record_index", 0) + 1, "error": friendly_error(r.get("error", "")), "payload": r.get("record")} for r in recs], indent=2, default=str).encode(), "application/json", f"{bid}.rejected.json"
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["record", "error", "payload"])
        for r in recs:
            w.writerow([r.get("record_index", 0) + 1, friendly_error(r.get("error", "")), json.dumps(r.get("record"), default=str)])
        return buf.getvalue().encode(), "text/csv", f"{bid}.rejected.csv"
    raise invalid("format must be jsonl, json or csv", "format")


def reprocess(bid: str, filename: str, fileobj) -> Dict[str, Any]:
    m = _meta(bid)
    if m["status"] not in TERMINAL:
        raise bad_state("The batch is still processing.")
    if not int(m.get("failed") or 0):
        raise bad_state("This batch has no rejected records to correct.")
    low = (filename or "").lower()
    if not low.endswith((".json", ".jsonl", ".ndjson", ".json.gz", ".jsonl.gz", ".ndjson.gz")):
        raise V2Error(415, "VALIDATION", "Unsupported file type. Use .json, .jsonl, .ndjson or .json.gz", "file")
    new_id = get_pipeline().save_upload(filename, fileobj, parent_batch_id=bid)
    return {"batch_id": new_id, "parent_batch_id": bid, "status": "QUEUED"}
