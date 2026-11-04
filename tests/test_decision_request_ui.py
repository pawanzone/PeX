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

