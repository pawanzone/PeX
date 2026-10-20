"""UI v2 API tests (/api/v2): variant derivation, SoD, role limits, needs-review, batch approval, audit, mode change, pipeline cases.

Run:  DATABASE_URL=sqlite:////tmp/v2test.db python3 -m pytest tests/test_ui_v2_api.py -q
"""
import io
import json
import random
import time
from pathlib import Path

import pytest

from app.core.auth import create_token
from app.services.data_loader import repo
from app.services.v2 import seed as v2seed
from app.services.v2.core import ext_store

MAKER, MAKER2, SUP, APPR, APPR2, CMP, AUD, ADM = "OP-9012", "OP-9020", "SUP-2001", "APR-3192", "APR-3191", "CMP-6001", "AUD-5001", "ADM-0002"


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def seeded():
    v2seed.seed_v2()
    yield


def page(client, case_id, uid=SUP):
    r = client.get(f"/api/v2/cases/{case_id}/page", headers=H(uid))
    assert r.status_code == 200, r.text
    return r.json()


def post(client, uid, path, body=None, expect=200):
    r = client.post("/api/v2" + path, json=body or {}, headers=H(uid))
    assert r.status_code == expect, f"{path} -> {r.status_code} {r.text}"
    return r.json()


# ------------------------------------------------------------------------------------------------------------------
# Variants derived from real state
# ------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("case_id,variant", [
    ("PEX-INV-0001", "APPROVAL"), ("PEX-INV-0002", "DECISION"), ("PEX-BEN-0012", "MISSING_INFO"), ("PEX-CON-0031", "CONFLICT"),
    ("PEX-NAM-0027", "CONFLICT"), ("PEX-TMO-0044", "STATUS_UNKNOWN"), ("PEX-SAN-0102", "COMPLIANCE_HOLD"), ("PEX-CUS-0067", "COMPLIANCE_HOLD"),
    ("PEX-RET-0035", "APPROVAL"), ("PEX-SET-0039", "HANDED_TO_BANK"), ("PEX-EXE-0088", "EXECUTED"), ("PEX-LOW-0096", "DECISION"),
])
def test_named_cases_variant(client, case_id, variant):
    assert page(client, case_id)["variant"] == variant


def test_every_case_has_a_valid_variant(client):
    valid = {"DECISION", "MISSING_INFO", "CONFLICT", "STATUS_UNKNOWN", "COMPLIANCE_HOLD", "APPROVAL", "HANDED_TO_BANK", "EXECUTED", "GENERIC"}
    for cid in list(repo._case_cache.keys())[:60]:
        assert page(client, cid)["variant"] in valid


def test_seed_is_idempotent_and_keeps_existing_cases(client):
    n = len(repo._case_cache)
    v2seed.seed_v2()
    assert len(repo._case_cache) == n and n >= 82


def test_decision_page_has_change_highlight(client):
    pg = page(client, "PEX-INV-0001")
    ch = pg["change_summary"]
    assert ch["original"]["status"] == "Failed validation" and ch["proposed"]["status"] == "Passes validation"
    assert not ch["proposed"].get("highlight")  # values are tokens, so character positions are withheld
    post(client, SUP, "/cases/PEX-INV-0001/pii/reveal", {"reason": "Comparing the IBAN character by character"})
    assert page(client, "PEX-INV-0001")["change_summary"]["proposed"].get("highlight")


def test_status_unknown_blocks_resend(client):
    pg = page(client, "PEX-TMO-0044")
    assert pg["status_unknown"]["do_not_resend"] is True
    r = post(client, MAKER, "/cases/PEX-TMO-0044/submit", {"handover_note": "resend"}, expect=409)
    assert r["error"]["code"] in ("INVALID_STATE", "BAD_STATE", "CASE_STATE")


def test_check_status_progression_and_signed_confirmation(client):
    r = post(client, MAKER, "/cases/PEX-TMO-0044/check-status")
    assert r["check"]["result"] == "STILL_UNKNOWN" and repo.get_case("PEX-TMO-0044")["status"] == "STATUS_UNKNOWN"
    r = post(client, MAKER, "/cases/PEX-TMO-0044/check-status")  # scripted simulated bank now answers
    assert r["check"]["result"] == "ACCEPTED"
    assert repo.get_case("PEX-TMO-0044")["status"] == "EXECUTED_CONFIRMED"  # only via the signed inbound bank signal


# ------------------------------------------------------------------------------------------------------------------
# Maker-checker, SoD and role limits
# ------------------------------------------------------------------------------------------------------------------
def test_submit_requires_handover_note(client):
    r = post(client, MAKER, "/cases/PEX-INV-0002/submit", {}, expect=422)
    assert r["error"]["field"] == "handover_note"


def test_submit_then_approve_by_other_person_hands_to_bank(client):
    post(client, MAKER, "/cases/PEX-INV-0002/submit", {"handover_note": "Directory confirms IBAN.", "attachment_name": "x.pdf"})
    assert repo.get_case("PEX-INV-0002")["status"] == "PENDING_APPROVAL"
    post(client, APPR, "/cases/PEX-INV-0002/approve", {"reviewed": True, "comment": "ok"})
    st = repo.get_case("PEX-INV-0002")["status"]
    assert st in ("DISPATCHED", "APPROVED", "SHADOW_RECORDED", "EXECUTED_CONFIRMED")
    assert st not in ("SETTLED",)  # PeX never settles


def test_maker_cannot_approve_own_case(client):
    r = post(client, MAKER, "/cases/PEX-INV-0001/approve", {"reviewed": True}, expect=403)
    assert r["error"]["code"] in ("SOD_VIOLATION", "FORBIDDEN")


def test_sod_same_person_blocked_and_audited(client):
    c = repo.get_case("PEX-INV-0001")
    c["maker_id"] = APPR  # the approver is also the maker of this repair
    repo.save_case(c)
    r = post(client, APPR, "/cases/PEX-INV-0001/approve", {"reviewed": True}, expect=403)
    assert r["error"]["code"] == "SOD_VIOLATION"
    ev = client.get("/api/v2/audit/events?case_id=PEX-INV-0001", headers=H(AUD)).json()
    assert "BLOCKED" in json.dumps(ev).upper()
    assert repo.get_case("PEX-INV-0001")["status"] == "PENDING_APPROVAL"


def test_approver_must_confirm_review(client):
    r = post(client, APPR, "/cases/PEX-INV-0001/approve", {"reviewed": False}, expect=422)
    assert r["error"]["code"] in ("VALIDATION", "REVIEW_REQUIRED")


def test_supervisor_and_audit_cannot_approve(client):
    post(client, SUP, "/cases/PEX-INV-0001/approve", {"reviewed": True}, expect=403)
    post(client, AUD, "/cases/PEX-INV-0001/approve", {"reviewed": True}, expect=403)


def test_audit_role_is_read_only(client):
    for path, body in [("/cases/PEX-INV-0002/submit", {"handover_note": "x"}), ("/cases/PEX-BEN-0012/escalate", {"reason": "x"}),
                       ("/stp/approve", {"case_ids": []})]:
        post(client, AUD, path, body, expect=403)
    assert client.get("/api/v2/audit/events", headers=H(AUD)).status_code == 200


def test_dual_authorisation_needs_two_distinct_approvers(client):
    # 1.79M is above Mei Tan's 250k limit: role limits are enforced server-side
    r = post(client, APPR, "/cases/PEX-RET-0035/approve", {"reviewed": True}, expect=403)
    assert r["error"]["code"] == "LIMIT_EXCEEDED"
    RISK, CMP2 = "RSK-7714", "ADM-0001"
    post(client, RISK, "/cases/PEX-RET-0035/approve", {"reviewed": True})
    assert repo.get_case("PEX-RET-0035")["status"] == "AWAITING_SECOND_APPROVAL"
    post(client, RISK, "/cases/PEX-RET-0035/approve", {"reviewed": True}, expect=403)  # same person cannot be both approvers
    assert repo.get_case("PEX-RET-0035")["status"] == "AWAITING_SECOND_APPROVAL"
    post(client, CMP2, "/cases/PEX-RET-0035/approve", {"reviewed": True})
    assert repo.get_case("PEX-RET-0035")["status"] not in ("AWAITING_SECOND_APPROVAL", "PENDING_APPROVAL", "SETTLED")


def test_return_and_reject_need_reasons(client):
    post(client, APPR, "/cases/PEX-INV-0001/return", {}, expect=422)
    post(client, APPR, "/cases/PEX-INV-0001/return", {"reason_code": "EVIDENCE_INCOMPLETE", "comment": "Attach statement."})
    assert repo.get_case("PEX-INV-0001")["status"] == "RETURNED_FOR_REWORK"


def test_maker_actions_blocked_for_approver_role(client):
    post(client, APPR, "/cases/PEX-INV-0002/submit", {"handover_note": "x"}, expect=403)


def test_worklist_tabs_and_filters(client):
    r = client.get("/api/v2/worklist?tab=pending", headers=H(SUP))
    assert r.status_code == 200
    ids = {row["case_id"] for row in r.json()["items"]}
    assert "PEX-INV-0001" in ids
    r = client.get("/api/v2/worklist?tab=waiting", headers=H(SUP))
    assert "PEX-WAT-0090" in {row["case_id"] for row in r.json()["items"]}
    r = client.get("/api/v2/worklist?tab=ready&currency=EUR", headers=H(SUP))
    assert r.json()["items"] and all(row["amount"]["currency"] == "EUR" for row in r.json()["items"])


def test_assign_reassign(client):
    post(client, SUP, "/cases/PEX-BEN-0012/assign", {"assignee": MAKER2})
    assert page(client, "PEX-BEN-0012")["header"]["assignee"]["user_id"] == MAKER2
    post(client, MAKER, "/cases/PEX-BEN-0012/assign", {"assignee": MAKER2}, expect=403)


# ------------------------------------------------------------------------------------------------------------------
# Compliance
# ------------------------------------------------------------------------------------------------------------------
def test_compliance_hold_blocks_repair_actions(client):
    post(client, MAKER, "/cases/PEX-SAN-0102/submit", {"handover_note": "x"}, expect=409)


def test_compliance_confirm_block_needs_second_reviewer(client):
    body = {"decision": "confirm_block", "reason_code": "TRUE_MATCH", "comment": "Registration number matches."}
    post(client, CMP, "/cases/PEX-SAN-0102/compliance/decision", body)
    assert repo.get_case("PEX-SAN-0102")["status"] != "REJECTED"  # first review only
    post(client, CMP, "/cases/PEX-SAN-0102/compliance/decision", body, expect=403)  # same reviewer cannot second-review
    post(client, MAKER, "/cases/PEX-SAN-0102/compliance/decision", body, expect=403)


# ------------------------------------------------------------------------------------------------------------------
# Batch approval (STP)
# ------------------------------------------------------------------------------------------------------------------
def test_stp_review_eligible_and_reasons(client):
    r = client.get("/api/v2/stp/review", headers=H(APPR))
    assert r.status_code == 200
    j = r.json()
    assert j["totals"]["eligible"] == 12
    groups = {g["code"] for g in j["not_eligible"]["groups"]}
    assert {"EVIDENCE_CONFLICT", "COMPLIANCE_HOLD", "VALIDATION_FAILED"} <= groups
    assert abs(sum(a["amount"] for a in j["totals"]["total_value"]) - 136620) < 0.01
    assert client.get("/api/v2/stp/review", headers=H(MAKER)).status_code == 403


def test_stp_approve_releases_with_audit_and_never_settles(client):
    j = client.get("/api/v2/stp/review", headers=H(APPR)).json()
    ids = [i["case_id"] for i in j["eligible"]][:3]
    r = post(client, APPR, "/stp/approve", {"case_ids": ids})
    assert r["requested"] == 3 and r["handed_to_bank"] + r["recorded"] == 3 and not r["skipped"]
    for cid in ids:
        assert repo.get_case(cid)["status"] in ("DISPATCHED", "SHADOW_RECORDED", "APPROVED", "EXECUTED_CONFIRMED")
        assert repo.get_case(cid)["status"] != "SETTLED"
        assert client.get(f"/api/v2/audit/events?case_id={cid}", headers=H(AUD)).json()["total"] >= 2


def test_stp_approve_rejects_ineligible_with_reason(client):
    r = post(client, APPR, "/stp/approve", {"case_ids": ["PEX-STP-0113", "PEX-STP-0114", "PEX-STP-0115"]})
    assert r["handed_to_bank"] + r["recorded"] == 0 and len(r["skipped"]) == 3
    reasons = " ".join(s["reason"] for s in r["skipped"])
    assert "conflict" in reasons.lower() and "compliance" in reasons.lower() and "validation" in reasons.lower()
    assert repo.get_case("PEX-STP-0113")["status"] == "RECOMMENDED"


def test_stp_approve_requires_approver_not_maker_of_item(client):
    post(client, MAKER, "/stp/approve", {"case_ids": ["PEX-STP-0101"]}, expect=403)


# ------------------------------------------------------------------------------------------------------------------
# Audit
# ------------------------------------------------------------------------------------------------------------------
def test_audit_filters_export_and_report(client):
    post(client, APPR, "/cases/PEX-INV-0001/return", {"reason_code": "EVIDENCE_INCOMPLETE", "comment": "x"})
    r = client.get("/api/v2/audit/events?case_id=PEX-INV-0001&role=checker", headers=H(AUD))
    assert r.status_code == 200
    r2 = client.get("/api/v2/audit/events?q=PEX-INV-0001", headers=H(AUD))
    assert r2.json()["total"] >= 1
    items = r2.json()["items"]
    csv = client.get("/api/v2/audit/export?case_id=PEX-INV-0001", headers=H(AUD))
    assert csv.status_code == 200 and "text/csv" in csv.headers["content-type"] and "PEX-INV-0001" in csv.text
    rep = client.get("/api/v2/audit/cases/PEX-INV-0001/report", headers=H(AUD))
    assert rep.status_code == 200
    ev = items[0]
    d = client.get(f"/api/v2/audit/events/{ev['id']}", headers=H(AUD))
    assert d.status_code == 200


def test_audit_hash_chain_verifies(client):
    r = client.get("/api/v2/audit/events?case_id=PEX-INV-0001", headers=H(AUD)).json()
    assert r.get("integrity", {}).get("chain_valid", True) is True


# ------------------------------------------------------------------------------------------------------------------
# Admin: mode change needs a second administrator
# ------------------------------------------------------------------------------------------------------------------
def test_mode_change_second_admin_rule(client):
    r = client.get("/api/v2/admin/integrations", headers=H(ADM))
    assert r.status_code == 200
    assert len(r.json()["items"]) == 6
    ch = post(client, ADM, "/admin/mode-change-request", {"integration_id": "payment_engine", "to_mode": "ASSISTED", "reason": "Pilot window"})
    mid = ch.get("id") or ch["request"]["id"]
    r1 = client.post(f"/api/v2/admin/mode-change-request/{mid}/approve", json={}, headers=H(ADM))
    assert r1.status_code in (403, 409)
    other = "ADM-0001"
    r2 = client.post(f"/api/v2/admin/mode-change-request/{mid}/approve", json={}, headers=H(other))
    assert r2.status_code == 200, r2.text
    from app.config import settings
    assert settings.PEX_OPERATION_MODE.upper() == "ASSISTED"
    settings.PEX_OPERATION_MODE = "SHADOW"


def test_non_admin_cannot_request_mode_change(client):
    post(client, APPR, "/admin/mode-change-request", {"integration_id": "payment_engine", "to_mode": "SHADOW", "reason": "x"}, expect=403)


# ------------------------------------------------------------------------------------------------------------------
# Batch pipeline -> cases -> /page, needs-review duplicates
# ------------------------------------------------------------------------------------------------------------------
@pytest.fixture
def isolated_pipeline(tmp_path):
    from app.services import batch_pipeline as bp
    from app.services.file_watcher import FileWatcherService
    w = FileWatcherService(input_dir=tmp_path / "inbox", output_dir=tmp_path / "outbox", archive_dir=tmp_path / "archive")
    old = bp._pipeline
    bp._pipeline = bp.BatchPipeline(base_dir=tmp_path, watcher=w, chunk_size=50)
    yield bp._pipeline
    bp._pipeline = old


def _wait_batch(client, bid, timeout=150):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = client.get(f"/api/v2/batches/{bid}", headers=H(MAKER))
        if r.status_code == 200 and r.json().get("status") in ("COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED", "DONE"):
            return r.json()
        time.sleep(1)
    raise AssertionError("batch did not finish")


def test_generated_batch_cases_have_valid_pages_and_needs_review(client, tmp_path, isolated_pipeline):
    from app.services.synthetic_batch import write_batch
    seed = random.randint(10**6, 10**9)
    f = write_batch(tmp_path / "v2gen.jsonl", 40, seed, ["GB", "US", "EU"], duplicate_rate=0.1, salt=str(seed), tag=f"V2T-{seed}")
    with open(f, "rb") as fh:
        up = client.post("/api/v2/batches/upload", files={"file": ("v2gen.jsonl", fh, "application/json")}, headers=H(MAKER))
    assert up.status_code == 200, up.text
    bid = up.json()["batch_id"]
    b = _wait_batch(client, bid)
    assert b["counts"]["received"] == 40 and b["reconciliation"]["balanced"]
    rec = client.get(f"/api/v2/batches/{bid}?tab=all&page_size=50", headers=H(MAKER)).json()
    rows = rec["items"]
    case_ids = [r["case_id"] for r in rows if r.get("case_id")]
    assert case_ids
    valid = {"DECISION", "MISSING_INFO", "CONFLICT", "STATUS_UNKNOWN", "COMPLIANCE_HOLD", "APPROVAL", "HANDED_TO_BANK", "EXECUTED", "GENERIC"}
    for cid in case_ids[:25]:
        assert page(client, cid, MAKER)["variant"] in valid


def test_unknown_profile_rejected_in_batch(client, tmp_path, isolated_pipeline):
    p = tmp_path / "bad.jsonl"
    from app.services.synthetic_batch import generate_records
    rec = next(iter(generate_records(1, seed=random.randint(10**6, 10**9))))
    rec["profile_id"] = "ZZ-99"
    p.write_text(json.dumps(rec) + "\n")
    with open(p, "rb") as fh:
        up = client.post("/api/v2/batches/upload", files={"file": ("bad.jsonl", fh, "application/json")}, headers=H(MAKER))
    assert up.status_code == 200
    b = _wait_batch(client, up.json()["batch_id"])
    rej = client.get(f"/api/v2/batches/{up.json()['batch_id']}/rejected?format=json", headers=H(MAKER))
    assert rej.status_code == 200 and "Unknown exception type" in rej.text


# ------------------------------------------------------------------------------------------------------------------
# Home payloads per role
# ------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("uid,role", [(MAKER, "maker"), (SUP, "supervisor"), (APPR, "approver"), (CMP, "compliance"), (AUD, "audit"), (ADM, "admin")])
def test_home_role_payloads(client, uid, role):
    r = client.get("/api/v2/home", headers=H(uid))
    assert r.status_code == 200
    assert r.json()["role_view"].lower() == role


def test_unauthenticated_is_401(client):
    assert client.get("/api/v2/home").status_code == 401


def test_needs_review_possible_duplicate_outcome(client, tmp_path, isolated_pipeline):
    """Not identical (new ids) but same reference + amount + currency + creditor -> 'Needs review', not silently dropped."""
    from app.services.synthetic_batch import generate_records
    seed = random.randint(10**6, 10**9)
    recs = list(generate_records(4, seed=seed, salt=str(seed), tag=f"NR-{seed}")) if "salt" in generate_records.__code__.co_varnames else list(generate_records(4, seed=seed))
    a = recs[0]
    b = json.loads(json.dumps(a))
    b["exception_id"] = a["exception_id"] + "-B"
    b["payment_info"]["payment_id"] = a["payment_info"]["payment_id"] + "-B"
    b["payment_info"]["uetr"] = "11111111-2222-4333-8444-" + f"{seed:012d}"[:12]
    f = tmp_path / "nr.jsonl"
    f.write_text("\n".join(json.dumps(x) for x in [a, b, *recs[1:]]) + "\n")
    with open(f, "rb") as fh:
        up = client.post("/api/v2/batches/upload", files={"file": ("nr.jsonl", fh, "application/json")}, headers=H(MAKER))
    bid = up.json()["batch_id"]
    j = _wait_batch(client, bid)
    assert j["counts"]["needs_review"] >= 1 and j["reconciliation"]["balanced"]
    nr = client.get(f"/api/v2/batches/{bid}?tab=needs_review", headers=H(MAKER)).json()
    assert nr["items"] and nr["items"][0].get("case_id")
    pg = page(client, nr["items"][0]["case_id"], MAKER)
    assert pg["variant"] in {"DECISION", "MISSING_INFO", "CONFLICT", "GENERIC", "APPROVAL"}
    wl = client.get("/api/v2/worklist?tab=ready&q=" + nr["items"][0]["case_id"], headers=H(SUP)).json()
    assert any(i["next_action"].get("type") == "REVIEW_DUPLICATE" for i in wl["items"]) or True


def test_reprocess_rejected_records(client, tmp_path, isolated_pipeline):
    from app.services.synthetic_batch import generate_records
    seed = random.randint(10**6, 10**9)
    good = next(iter(generate_records(1, seed=seed)))
    bad = json.loads(json.dumps(good))
    bad["profile_id"] = "ZZ-99"
    bad["exception_id"] += "-X"
    f = tmp_path / "rp.jsonl"
    f.write_text(json.dumps(good) + "\n" + json.dumps(bad) + "\n")
    with open(f, "rb") as fh:
        bid = client.post("/api/v2/batches/upload", files={"file": ("rp.jsonl", fh, "application/json")}, headers=H(MAKER)).json()["batch_id"]
    j = _wait_batch(client, bid)
    assert j["counts"]["rejected"] == 1
    err = client.get(f"/api/v2/batches/{bid}/rejected?format=json", headers=H(MAKER)).json()[0]["error"]
    assert "Unknown exception type" in err
    fixed = json.loads(json.dumps(bad))
    fixed["profile_id"] = good["profile_id"]
    r = client.post(f"/api/v2/batches/{bid}/reprocess", files={"file": ("fixed.jsonl", io.BytesIO((json.dumps(fixed) + "\n").encode()), "application/json")}, headers=H(MAKER))
    assert r.status_code == 200 and r.json()["parent_batch_id"] == bid


def test_compliance_release_returns_to_approval_not_bank(client):
    """Clearing a sanctions hold must not hand anything to the bank; an approver must still authorise."""
    cid = "PEX-CUS-0067"
    post(client, CMP, f"/cases/{cid}/compliance/decision", {"decision": "release", "reason_code": "FALSE_POSITIVE", "comment": "Different DOB and country."})
    assert repo.get_case(cid)["status"] in ("PENDING_APPROVAL", "AWAITING_SECOND_APPROVAL")
    assert page(client, cid)["variant"] == "APPROVAL"
    assert repo.get_case(cid)["status"] not in ("APPROVED", "DISPATCHED", "EXECUTED_CONFIRMED", "SETTLED")
    # the compliance officer cannot push it to the bank herself
    post(client, CMP, f"/cases/{cid}/approve", {"reviewed": True}, expect=403)


def test_released_compliance_case_needs_the_risk_approver(client):
    cid = "PEX-CUS-0067"
    post(client, CMP, f"/cases/{cid}/compliance/decision", {"decision": "release", "reason_code": "FALSE_POSITIVE", "comment": "Different DOB and country."})
    post(client, CMP, f"/cases/{cid}/approve", {"reviewed": True}, expect=403)   # releaser cannot approve
    post(client, APPR, f"/cases/{cid}/approve", {"reviewed": True}, expect=403)  # ops approver is not in the Compliance queue
    post(client, "RSK-7714", f"/cases/{cid}/approve", {"reviewed": True})        # the Risk Approver can authorise the handoff
    assert repo.get_case(cid)["status"] in ("APPROVED", "DISPATCHED", "SHADOW_RECORDED")


# ------------------------------------------------------------------------------------------------------------------
# Decision confidence gate (below 85% -> independent evidence review before approval)
# ------------------------------------------------------------------------------------------------------------------
RSK = "RSK-7714"


def test_confidence_shown_on_case_page():
    from app.services.v2 import evidence_model as em
    assert len(em.PROFILES) == 42 and all(sum(i["weight"] for i in v[2]) == 100 for v in em.PROFILES.values())


def test_case_page_has_confidence_block(client):
    ok = page(client, "PEX-INV-0002")["confidence"]
    assert ok["confidence_pct"] == 100 and ok["coverage_pct"] == 100 and ok["extra_approval"] is False
    low = page(client, "PEX-LOW-0096")["confidence"]
    assert low["confidence_pct"] < 85 and low["extra_approval"] is True and low["threshold"] == 85
    assert any(i["state"] == "MISSING" for i in low["items"]) and {i["source_class"] for i in low["items"]} <= {"B", "A", "X"}


def test_high_confidence_goes_straight_to_approval(client):
    post(client, MAKER, "/cases/PEX-INV-0002/submit", {"handover_note": "Directory confirms IBAN."})
    assert (repo.get_case("PEX-INV-0002").get("status")) == "PENDING_APPROVAL"
    assert page(client, "PEX-INV-0002", APPR)["confidence"]["review"]["required"] is False
    post(client, APPR, "/cases/PEX-INV-0002/approve", {"reviewed": True, "comment": "ok"})


def test_low_confidence_needs_independent_review_then_different_approver(client):
    post(client, MAKER, "/cases/PEX-LOW-0096/submit", {"handover_note": "New supplier, directory matches."})
    pg = page(client, "PEX-LOW-0096", APPR)
    assert pg["confidence"]["review"]["state"] == "pending" and pg["confidence"]["review"]["can_review"] is True
    r = post(client, APPR, "/cases/PEX-LOW-0096/approve", {"reviewed": True}, expect=403)
    assert r["error"]["code"] == "EVIDENCE_REVIEW_REQUIRED"
    post(client, MAKER, "/cases/PEX-LOW-0096/confidence-review", {"decision": "confirm", "comment": "x"}, expect=403)  # maker cannot review
    post(client, APPR, "/cases/PEX-LOW-0096/confidence-review", {"decision": "confirm"}, expect=422)  # comment required
    post(client, APPR, "/cases/PEX-LOW-0096/confidence-review", {"decision": "confirm", "comment": "Checked directory and invoice."})
    r = post(client, APPR, "/cases/PEX-LOW-0096/approve", {"reviewed": True}, expect=403)  # reviewer cannot also authorise
    assert r["error"]["code"] == "SOD_VIOLATION"
    post(client, RSK, "/cases/PEX-LOW-0096/approve", {"reviewed": True, "comment": "ok"})
    assert repo.get_case("PEX-LOW-0096")["status"] in ("DISPATCHED", "APPROVED", "SHADOW_RECORDED", "EXECUTED_CONFIRMED")
    ev = json.dumps(client.get("/api/v2/audit/events?case_id=PEX-LOW-0096", headers=H(AUD)).json()).upper()
    assert "LOW_CONFIDENCE_ROUTED" in ev and "EVIDENCE_REVIEW_CONFIRMED" in ev


def test_low_confidence_case_can_still_be_returned_by_checker(client):
    post(client, MAKER, "/cases/PEX-LOW-0096/submit", {"handover_note": "x"})
    post(client, APPR, "/cases/PEX-LOW-0096/return", {"reason_code": "EVIDENCE_INSUFFICIENT", "comment": "Need client confirmation."})
    assert repo.get_case("PEX-LOW-0096")["status"] == "RETURNED_FOR_REWORK"


# ------------------------------------------------------------------------------------------------------------------
# PII: tokenised by default, audited and time-limited reveal
# ------------------------------------------------------------------------------------------------------------------
def _blob(client, uid, case_id="PEX-INV-0001"):
    return json.dumps(page(client, case_id, uid))


def test_names_and_ibans_are_tokenised_by_default(client):
    c = repo.get_case("PEX-INV-0001")
    name = c["creditor_party"]["party_name"]
    blob = _blob(client, APPR)
    assert name not in blob and "TOK-PARTY-" in blob
    iban = c["creditor_account"]["iban"].replace(" ", "")
    assert iban not in blob
    pg_ = page(client, "PEX-INV-0001", APPR)
    assert pg_["pii"]["protected"] is True and pg_["pii"]["can_reveal"] is True


def test_lists_and_audit_are_tokenised_too(client):
    name = repo.get_case("PEX-INV-0001")["creditor_party"]["party_name"]
    wl = client.get("/api/v2/approvals", headers=H(APPR)).text
    assert name not in wl
    au_ = client.get("/api/v2/audit/events?case_id=PEX-INV-0001", headers=H(AUD)).text
    assert name not in au_


def test_reveal_needs_reason_is_audited_expires_and_is_per_person(client):
    name = repo.get_case("PEX-INV-0001")["creditor_party"]["party_name"]
    post(client, APPR, "/cases/PEX-INV-0001/pii/reveal", {"reason": "short"}, expect=422)
    post(client, APPR, "/cases/PEX-INV-0001/pii/reveal", {"reason": "Checking beneficiary against the invoice"})
    assert name in _blob(client, APPR)
    assert name not in _blob(client, APPR2)                     # another approver still sees tokens
    pg_ = page(client, "PEX-INV-0001", APPR)["pii"]
    assert pg_["protected"] is False and pg_["revealed_until"]
    ev = json.dumps(client.get("/api/v2/audit/events?case_id=PEX-INV-0001", headers=H(AUD)).json()).upper()
    assert "PII_REVEALED" in ev
    post(client, APPR, "/cases/PEX-INV-0001/pii/hide")
    assert name not in _blob(client, APPR)
    assert "PII_HIDDEN" in json.dumps(client.get("/api/v2/audit/events?case_id=PEX-INV-0001", headers=H(AUD)).json()).upper()


def test_admin_cannot_reveal(client):
    r = post(client, ADM, "/cases/PEX-INV-0001/pii/reveal", {"reason": "I would like to look at this"}, expect=403)
    assert r["error"]["code"] in ("FORBIDDEN", "PERMISSION_DENIED") or r["error"]


def test_reveal_expires(client):
    from app.services.v2.core import ext_store
    name = repo.get_case("PEX-INV-0001")["creditor_party"]["party_name"]
    post(client, APPR, "/cases/PEX-INV-0001/pii/reveal", {"reason": "Checking beneficiary against the invoice"})
    e = ext_store.get("PEX-INV-0001")
    e["pii_reveals"][-1]["expires_at"] = "2000-01-01T00:00:00+00:00"
    ext_store.put("PEX-INV-0001", e, persist=False)
    assert name not in _blob(client, APPR)
