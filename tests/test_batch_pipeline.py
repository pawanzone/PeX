"""Batch pipeline tests: streaming parsers, chunked transactions, idempotency, failure isolation, outputs, API.

Run:  python3 -m pytest tests/test_batch_pipeline.py -q
Scale (opt-in):  PEX_SCALE_N=100000 python3 -m pytest tests/test_batch_pipeline.py -q -k scale -s
"""
import gzip
import io
import json
import os
import random
import resource
import time
from pathlib import Path

import pytest

from app.config import settings
from app.db.repository import PeXDBRepository  # noqa: F401
from app.services import batch_pipeline as bp
from app.services.audit_service import audit_service
from app.services.batch_pipeline import BatchPipeline, _Reader, iter_records
from app.services.data_loader import repo
from app.services.file_watcher import FileWatcherService
from app.services.synthetic_batch import (
    aba_transposed, aba_valid, generate_records, iban_valid, write_batch, transpose_invalid, gen_iban,
)


def _seed() -> int:
    return random.randint(10**6, 10**9)  # DB persists across runs; keep UETRs unique per run


def _pipeline(tmp_path, chunk=50):
    w = FileWatcherService(input_dir=tmp_path / "inbox", output_dir=tmp_path / "outbox", archive_dir=tmp_path / "archive")
    return BatchPipeline(base_dir=tmp_path, watcher=w, chunk_size=chunk)


def _lines(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


# --------------------------------------------------------------------------------------------
# Generator
# --------------------------------------------------------------------------------------------
def test_generator_deterministic_and_valid_ibans():
    a = [json.dumps(r) for r in generate_records(300, seed=42)]
    b = [json.dumps(r) for r in generate_records(300, seed=42)]
    c = [json.dumps(r) for r in generate_records(300, seed=43)]
    assert a == b and a != c
    for raw in a:
        r = json.loads(raw)
        p = r["payment_info"]
        if r["profile_id"] == "DQ-01":
            ev = r["bank_supplied_evidence"].get("verified_iban")
            assert not iban_valid(p["creditor_account"]), "inbound IBAN must be invalid (so a repair exists)"
            if ev:
                assert iban_valid(ev)
        for acct in (p.get("debtor_account"), p.get("creditor_account")):
            assert not (acct or "").startswith("US") or not acct[2:4].isdigit() or len(acct) < 15, "no fake US IBANs"


def test_generator_rail_selection_and_aba():
    recs = list(generate_records(400, seed=7, rails=["EU"]))
    ccys = {r["payment_info"]["currency"] for r in recs if r["profile_id"] in ("DQ-01", "ST-01", "PR-01", "CO-04", "PR-08")}
    assert ccys == {"EUR"}
    us = list(generate_records(200, seed=7, rails=["US"]))
    assert any(r["profile_id"] == "DQ-08" for r in us)
    for r in us:
        if r["profile_id"] == "DQ-08":
            ev = r["external_authoritative_evidence"]
            assert aba_valid(ev["valid_routing_code"]) and not aba_valid(ev["inbound_routing_code"])
    rng = random.Random(1)
    for cc in ("GB", "DE", "FR", "NL", "ES", "IT"):
        good, _, _ = gen_iban(cc, rng)
        assert iban_valid(good) and not iban_valid(transpose_invalid(good, rng))


# --------------------------------------------------------------------------------------------
# Parsers
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name,fmt", [("a.jsonl", "jsonl"), ("a.ndjson", "jsonl"), ("a.json", "json"), ("a.json.gz", "json.gz"), ("a.jsonl.gz", "jsonl.gz")])
def test_streaming_parsers_all_formats(tmp_path, name, fmt):
    p = write_batch(tmp_path / name, 120, seed=3, fmt=fmt)
    r = _Reader(p)
    meta = {}
    got = list(iter_records(r, meta))
    r.close()
    assert len(got) == 120 and all(e is None for _, _, e in got)
    if fmt.startswith("json") and not fmt.startswith("jsonl"):
        assert meta.get("source_system") == "PEX_SYNTHETIC_GENERATOR"  # envelope header parsed without loading records


def test_parser_array_single_and_chunk_boundaries(tmp_path):
    recs = list(generate_records(4000, seed=11))  # ~> 8 MB: crosses many 1 MB read boundaries
    arr = tmp_path / "arr.json"
    arr.write_text(json.dumps(recs), encoding="utf-8")
    r = _Reader(arr)
    got = list(iter_records(r, {}))
    r.close()
    assert len(got) == 4000 and got[1234][1]["exception_id"] == recs[1234]["exception_id"]
    one = tmp_path / "one.json"
    one.write_text(json.dumps(recs[0]), encoding="utf-8")
    r = _Reader(one)
    assert len(list(iter_records(r, {}))) == 1
    r.close()


def test_parser_malformed_jsonl_line_does_not_abort(tmp_path):
    p = tmp_path / "m.jsonl"
    good = [json.dumps(r) for r in generate_records(3, seed=5)]
    p.write_text(good[0] + "\n{not json\n" + good[1] + "\n\n" + good[2] + "\n", encoding="utf-8")
    r = _Reader(p)
    got = list(iter_records(r, {}))
    r.close()
    assert [e is not None for _, _, e in got] == [False, True, False, False]


# --------------------------------------------------------------------------------------------
# Pipeline end to end
# --------------------------------------------------------------------------------------------
def test_pipeline_end_to_end_outputs_and_integrity(tmp_path):
    pl = _pipeline(tmp_path)
    f = write_batch(pl.inbox / "e2e.jsonl", 200, seed=_seed())
    before_cases = repo.case_count()
    b = pl.wait(pl.submit_file(f), 300)
    assert b["status"] == "COMPLETED"
    assert b["processed"] + b["failed"] + b["duplicates"] == b["total"] == 200
    assert b["failed"] == 0 and b["processed"] == 200
    assert repo.case_count() == before_cases + 200

    res = _lines(pl.results_path(b["batch_id"]))
    assert len(res) == 200
    need = {"exception_id", "profile", "rail", "currency", "amount", "status", "queue", "stp_eligible", "predicates",
            "recommended_action", "proposed_changes", "decision_reason", "evidence_summary", "errors"}
    assert need <= set(res[0])
    for ln in res:
        assert set(ln["predicates"]) == {"e_suff", "r_det", "r_uniq", "v_det", "v_auth", "p_bank", "c_comp", "x_pre"}
        # STP-eligible iff all 8 predicates pass
        assert ln["stp_eligible"] == all(ln["predicates"].values())
    summary = json.loads((pl.outbox / f"{b['batch_id']}.summary.json").read_text())
    assert summary["bank_comm"] == "SIMULATED" and summary["execution_owner"] == "BANK"
    assert summary["total_records"] == 200 and sum(summary["by_status"].values()) == 200
    assert summary["mode"] == str(settings.PEX_OPERATION_MODE).upper()
    assert (pl.archive / "e2e.jsonl").exists() and not (pl.inbox / "e2e.jsonl").exists()
    # cases queryable from the DB, recommendation fallback works, audit chain intact
    first = res[0]["exception_id"]
    assert repo.get_case(first) is not None and repo.get_recommendation(first) is not None
    assert audit_service.verify_chain().is_intact


def test_shadow_mode_writes_no_bank_handoff_and_live_mode_does(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "PEX_OPERATION_MODE", "SHADOW")
    pl = _pipeline(tmp_path / "shadow")
    b = pl.wait(pl.submit_file(write_batch(pl.inbox / "s.jsonl", 120, seed=_seed())), 300)
    assert b["summary"]["stp_eligible"] > 0
    assert not (pl.outbox / f"{b['batch_id']}.bank_handoff.jsonl").exists()
    assert all(l["status"] == "SHADOW_RECORDED" for l in _lines(pl.results_path(b["batch_id"])) if l["stp_eligible"])

    monkeypatch.setattr(settings, "PEX_OPERATION_MODE", "LIVE")
    pl2 = _pipeline(tmp_path / "live")
    b2 = pl2.wait(pl2.submit_file(write_batch(pl2.inbox / "l.jsonl", 120, seed=_seed())), 300)
    hand = _lines(pl2.outbox / f"{b2['batch_id']}.bank_handoff.jsonl")
    assert len(hand) == b2["summary"]["stp_eligible"] > 0
    assert all(h["execution_owner"] == "BANK" and h["bank_comm"] == "SIMULATED" for h in hand)
    stp_ids = {l["exception_id"] for l in _lines(pl2.results_path(b2["batch_id"])) if l["stp_eligible"]}
    assert {h["exception_id"] for h in hand} == stp_ids  # only STP-eligible items are handed off


def test_replay_is_idempotent_and_counts_duplicates(tmp_path):
    pl = _pipeline(tmp_path)
    seed = _seed()
    b1 = pl.wait(pl.submit_file(write_batch(pl.inbox / "r1.jsonl", 80, seed=seed)), 300)
    cases = repo.case_count()
    b2 = pl.wait(pl.submit_file(write_batch(pl.inbox / "r2.jsonl", 80, seed=seed)), 300)
    assert b1["processed"] == 80 and b2["processed"] == 0 and b2["duplicates"] == 80
    assert repo.case_count() == cases
    assert {l["status"] for l in _lines(pl.results_path(b2["batch_id"]))} == {"DUPLICATE"}


def test_duplicates_within_batch_and_malformed_records_isolated(tmp_path):
    pl = _pipeline(tmp_path, chunk=40)
    f = write_batch(pl.inbox / "mix.jsonl", 150, seed=_seed(), duplicate_rate=0.1, malformed_rate=0.08)
    with open(f, "a", encoding="utf-8") as fh:
        fh.write("{broken line\n")
    b = pl.wait(pl.submit_file(f), 300)
    assert b["status"] == "COMPLETED"
    assert b["failed"] >= 1 and b["duplicates"] >= 1 and b["processed"] > 80
    assert b["processed"] + b["failed"] + b["duplicates"] == b["total"]
    failed = _lines(pl.failed / f"{b['batch_id']}.failed.jsonl")
    assert len(failed) == b["failed"] and all("error" in x for x in failed)
    res = _lines(pl.results_path(b["batch_id"]))
    assert [r["record_index"] for r in res] == sorted(r["record_index"] for r in res)
    assert audit_service.verify_chain().is_intact


def test_record_failure_inside_chunk_rolls_back_only_that_record(tmp_path, monkeypatch):
    pl = _pipeline(tmp_path, chunk=100)
    seed = _seed()
    recs = list(generate_records(30, seed=seed))
    boom_id = recs[7]["exception_id"]
    w = pl._get_watcher()
    orig = w._process_single_record

    def flaky(*a, **kw):
        if kw["e2e_input"].exception_id == boom_id:
            # leave staged rows behind, then fail: they must be discarded
            repo.save_case({"case_id": boom_id, "profile": "X", "status": "INGESTED"})
            raise RuntimeError("boom")
        return orig(*a, **kw)

    monkeypatch.setattr(w, "_process_single_record", flaky)
    f = pl.inbox / "flaky.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
    b = pl.wait(pl.submit_file(f), 300)
    assert b["failed"] == 1 and b["processed"] == 29
    assert repo.get_case(boom_id) is None
    assert audit_service.verify_chain().is_intact


def test_state_is_persisted_and_resumed(tmp_path):
    pl = _pipeline(tmp_path)
    b = pl.wait(pl.submit_file(write_batch(pl.inbox / "st.jsonl", 40, seed=_seed())), 300)
    assert (pl.state_dir / f"{b['batch_id']}.json").exists()
    pl2 = BatchPipeline(base_dir=tmp_path, watcher=pl._get_watcher(), chunk_size=50)  # "restart"
    again = pl2.get_batch(b["batch_id"])
    assert again and again["status"] == "COMPLETED" and again["summary"]["total_records"] == 40


def test_scan_inbox_picks_up_stable_streaming_files_only(tmp_path):
    pl = _pipeline(tmp_path)
    f = write_batch(pl.inbox / "drop.jsonl", 20, seed=_seed())
    small = pl.inbox / "small.json"
    small.write_text(json.dumps(next(generate_records(1, seed=_seed()))), encoding="utf-8")  # watcher's own path
    old = time.time() - 5
    os.utime(f, (old, old))
    assert pl.scan_inbox() == []  # first sighting: size/mtime not yet confirmed stable
    ids = pl.scan_inbox()
    assert len(ids) == 1 and pl.get_batch(ids[0])["filename"] == "drop.jsonl"
    assert small.exists() and not pl.claims("small.json")
    pl.wait(ids[0], 120)


# --------------------------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------------------------
def _api_pipeline(tmp_path, monkeypatch):
    pl = _pipeline(tmp_path)
    monkeypatch.setattr(bp, "_pipeline", pl)
    return pl


def test_api_upload_list_detail_results_and_generate(client, tmp_path, monkeypatch):
    pl = _api_pipeline(tmp_path, monkeypatch)
    body = "\n".join(json.dumps(r) for r in generate_records(60, seed=_seed())).encode()
    r = client.post("/api/batch/upload", files={"file": ("up.jsonl", io.BytesIO(body), "application/x-ndjson")})
    assert r.status_code == 200 and r.json()["status"] == "QUEUED"
    bid = r.json()["batch_id"]
    assert client.get(f"/api/batch/{bid}/results").status_code in (200, 409)
    pl.wait(bid, 300)
    d = client.get(f"/api/batch/{bid}").json()
    assert d["status"] == "COMPLETED" and d["processed"] == 60 and d["records_per_sec"] > 0
    lst = client.get("/api/batch").json()
    assert any(x["batch_id"] == bid for x in lst)
    res = client.get(f"/api/batch/{bid}/results")
    assert res.status_code == 200 and len(res.text.strip().splitlines()) == 60
    assert client.get(f"/api/batch/{bid}/summary").json()["bank_comm"] == "SIMULATED"
    assert client.get("/api/batch/NOPE").status_code == 404
    assert client.post("/api/batch/upload", files={"file": ("x.exe", io.BytesIO(b"x"), "application/octet-stream")}).status_code == 415

    g = client.post(f"/api/batch/generate?count=40&seed={_seed()}&rails=GB,EU")
    assert g.status_code == 200
    gb = pl.wait(g.json()["batch_id"], 300)
    assert gb["processed"] == 40 and set(gb["summary"]["by_currency"]) <= {"GBP", "EUR", "USD", "BRL", "JPY"}


def test_api_generate_twice_with_same_seed_is_not_all_duplicates(client, tmp_path, monkeypatch):
    pl = _api_pipeline(tmp_path, monkeypatch)
    ids = [client.post("/api/batch/generate?count=20&seed=1&rails=GB").json()["batch_id"] for _ in range(2)]
    res = [pl.wait(i, 300) for i in ids]
    assert res[0]["processed"] == 20 and res[1]["processed"] == 20 and res[1]["duplicates"] == 0
    rep = [client.post("/api/batch/generate?count=10&seed=5&rails=GB&repeatable=true").json()["batch_id"] for _ in range(2)]
    r2 = [pl.wait(i, 300) for i in rep]
    assert r2[1]["duplicates"] == 10  # repeatable=true is idempotent by design


def test_api_gzip_upload(client, tmp_path, monkeypatch):
    pl = _api_pipeline(tmp_path, monkeypatch)
    raw = "\n".join(json.dumps(r) for r in generate_records(25, seed=_seed())).encode()
    r = client.post("/api/batch/upload", files={"file": ("z.jsonl.gz", io.BytesIO(gzip.compress(raw)), "application/gzip")})
    b = pl.wait(r.json()["batch_id"], 300)
    assert b["processed"] == 25


def test_paged_cases_and_summary_counts(client, tmp_path, monkeypatch):
    pl = _api_pipeline(tmp_path, monkeypatch)
    pl.wait(pl.submit_file(write_batch(pl.inbox / "pg.jsonl", 90, seed=_seed(), rails=["GB", "US", "EU"])), 300)
    page = client.get("/api/cases/page?limit=10&offset=0&sort=amount&order=desc").json()
    assert set(page) == {"items", "total", "limit", "offset"} and len(page["items"]) == 10 and page["total"] >= 90
    amts = [i["amount"] for i in page["items"]]
    assert amts == sorted(amts, reverse=True)
    f = client.get("/api/cases/page?queue=Repair&rail=SEPA_SCT&limit=500").json()
    assert all(i["queue"] == "Repair" and i["payment_rail"] == "SEPA_SCT" for i in f["items"])
    s = client.get("/api/cases/page?q=DQ-01&limit=5").json()
    assert all("DQ-01" in (i["profile"] + i["case_id"]) or "dq-01" in i["case_id"].lower() for i in s["items"])
    counts = client.get("/api/summary/counts").json()
    assert {"total", "by_status", "by_queue", "by_profile", "by_rail", "actionable_repair", "pending_approvals_all"} <= set(counts)
    assert counts["total"] == sum(counts["by_status"].values()) >= 90
    assert client.get("/api/cases").status_code == 200  # legacy endpoint unchanged


# --------------------------------------------------------------------------------------------
# Scale (opt-in)
# --------------------------------------------------------------------------------------------
@pytest.mark.skipif(not os.getenv("PEX_SCALE_N"), reason="set PEX_SCALE_N=100000 to run the scale test")
def test_scale_end_to_end(tmp_path):
    n = int(os.environ["PEX_SCALE_N"])
    pl = _pipeline(tmp_path, chunk=int(os.getenv("PEX_BATCH_CHUNK_SIZE", "500")))
    f = write_batch(pl.inbox / "scale.jsonl", n, seed=_seed())
    t0 = time.time()
    b = pl.wait(pl.submit_file(f), 7000)
    el = time.time() - t0
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(f"\nSCALE n={n} elapsed={el:.1f}s rec/s={b['records_per_sec']} peak_rss_mb={rss:.0f} processed={b['processed']} failed={b['failed']} dup={b['duplicates']}")
    assert b["status"] == "COMPLETED" and b["processed"] + b["failed"] + b["duplicates"] == n
    assert audit_service.verify_chain().is_intact
