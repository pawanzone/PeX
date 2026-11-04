"""A decision-support case shows the reviewer what is being decided, the options, and who decides; PeX never picks."""
import json

import pytest

from app.profile_packs import registry
from app.schemas.contracts.e2e_schemas import CanonicalE2EInput
from app.services.e2e_runner import E2EExecutionHarness

DECISION_CODES = ["CO-01", "CO-02", "CO-03", "CO-05", "CO-06", "CO-08", "ST-04", "ST-05", "ST-07"]


def _ext(prefix, variant):
    from test_profile_goldens import CASES
    from app.services.v2.ext import ext_from_e2e
    key = next(k for k in CASES if k.startswith(f"input/{prefix}_") and k.endswith(variant))
    raw = json.loads(CASES[key].read_text(encoding="utf-8"))
    out = E2EExecutionHarness().process_input(raw)
    case = {"case_id": out.exception_id, "amount": 40_000.0, "sla_due_at": None}
    return ext_from_e2e(case, CanonicalE2EInput(**raw), out), case


@pytest.mark.parametrize("code", DECISION_CODES)
def test_complete_evidence_stores_the_decision_request(code):
    ext, _ = _ext(code, "sufficient")
    d = ext["decision_request"]
    pack = registry.get_pack(code)
    assert d["action"] == "DECISION_REQUIRED" and d["evidence_complete"] is True
    assert d["options"] == list(pack.decision.options) and d["reviewer_role"] == pack.decision.reviewer_role
    assert d["target"] == pack.decision.target_field and d["missing"] == []


@pytest.mark.parametrize("code", DECISION_CODES)
def test_missing_evidence_stores_a_hold_naming_the_gaps(code):
    ext, _ = _ext(code, "missing_evidence")
    d = ext["decision_request"]
    assert d["action"] == "INVESTIGATION_HOLD" and d["evidence_complete"] is False
    assert d["missing"] and d["options"] == [] and d["reviewer_role"] == registry.get_pack(code).decision.reviewer_role


def test_repair_profiles_have_no_decision_request():
    ext, _ = _ext("DQ-03", "sufficient")
    assert ext.get("decision_request") is None


def test_page_block_is_human_readable_and_does_not_choose():
    from app.services.v2 import pages
    ext, case = _ext("CO-01", "sufficient")
    blk = pages.decision_request_block(ext)
    assert blk["title"] == "Decision required"
    assert blk["decided_by"] == "Compliance Officer"
    assert blk["target_label"] == "Compliance screening disposition"
    assert [o["code"] for o in blk["options"]] == list(registry.get_pack("CO-01").decision.options)
    assert blk["options"][0]["label"] == "False positive homonym cleared"
    assert "does not choose" in blk["note"].lower()
    assert "selected" not in blk and "recommended_option" not in blk


def test_page_block_for_hold_lists_what_is_missing():
    from app.services.v2 import pages
    ext, _ = _ext("ST-05", "missing_evidence")
    blk = pages.decision_request_block(ext)
    assert blk["title"] == "Waiting for evidence" and blk["options"] == [] and blk["missing"]
    assert blk["decided_by"] == "Operations Approver"


def test_no_block_when_there_is_no_request():
    from app.services.v2 import pages
    assert pages.decision_request_block({}) is None
    assert pages.decision_request_block({"decision_request": None}) is None


def test_case_page_carries_the_block():
    from app.core.security import get_persona
    from app.services.data_loader import repo
    from app.services.v2 import pages
    from app.services.v2.core import ext_store
    ext, _ = _ext("CO-02", "sufficient")
    cid = list(repo.cases)[5]
    base = pages.lg.ext_of(repo.cases[cid])
    ext_store.put(cid, {**base, "decision_request": ext["decision_request"]}, persist=False)
    page = pages.case_page(cid, get_persona("CMP-4420"))
    assert page["decision_request"]["title"] == "Decision required"
    assert page["decision_request"]["options"][0]["code"] == registry.get_pack("CO-02").decision.options[0]
    ext_store.put(cid, base, persist=False)
    assert pages.case_page(cid, get_persona("CMP-4420"))["decision_request"] is None



# ---- recording: the block tells the viewer whether they can decide, and shows what was recorded ----------
def _stored(code="CO-02", complete=True):
    import test_decision_record as tdr
    cid, pack = tdr._case(code, complete)
    return cid, pack, tdr


def test_block_tells_the_right_role_it_can_decide():
    from app.services.v2 import pages
    from app.services.data_loader import repo
    cid, pack, tdr = _stored("CO-02")
    ext = pages.lg.ext_of(repo.cases[cid])
    ok = pages.decision_request_block(ext, tdr.CMP1, repo.cases[cid])
    assert ok["can_decide"] is True and ok["cannot_decide_reason"] is None and ok["endpoint"] == f"/api/v2/cases/{cid}/decision"
    no = pages.decision_request_block(ext, tdr.RSK, repo.cases[cid])
    assert no["can_decide"] is False and "Compliance Officer" in no["cannot_decide_reason"]


def test_block_without_complete_evidence_cannot_be_decided():
    from app.services.v2 import pages
    from app.services.data_loader import repo
    cid, pack, tdr = _stored("CO-02", complete=False)
    blk = pages.decision_request_block(pages.lg.ext_of(repo.cases[cid]), tdr.CMP1, repo.cases[cid])
    assert blk["can_decide"] is False and "evidence" in blk["cannot_decide_reason"].lower()


def test_block_shows_the_recorded_decision():
    from app.services.v2 import pages
    from app.services.data_loader import repo
    cid, pack, tdr = _stored("ST-04")
    tdr._decide(cid, tdr.OPS1, tdr._opt(pack, "PROCEED"), "Within tolerance.")
    blk = pages.decision_request_block(pages.lg.ext_of(repo.cases[cid]), tdr.OPS1, repo.cases[cid])
    assert blk["title"] == "Decision recorded" and blk["can_decide"] is False
    r = blk["recorded"]
    assert r["option_label"] == "Post fee adjustment within tolerance" and r["by_name"] == tdr.OPS1.name and r["comment"] == "Within tolerance."
    assert r["state_label"] == "Cleared for approval"


def test_hold_still_allows_a_new_decision():
    from app.services.v2 import pages
    from app.services.data_loader import repo
    cid, pack, tdr = _stored("ST-07")
    tdr._decide(cid, tdr.OPS1, tdr._opt(pack, "HOLD"), "Waiting for the bank.")
    blk = pages.decision_request_block(pages.lg.ext_of(repo.cases[cid]), tdr.OPS1, repo.cases[cid])
    assert blk["can_decide"] is True and blk["recorded"]["state_label"] == "On hold" and blk["title"] == "Decision required"


def test_decision_endpoint_is_registered():
    from app.api.endpoints import v2
    paths = {r.path for r in v2.router.routes}
    assert any(p.endswith("/cases/{case_id}/decision") for p in paths)
