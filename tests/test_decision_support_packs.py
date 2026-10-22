"""The 9 decision-support profiles (CO-01, 02, 03, 05, 06, 08; ST-04, 05, 07): evidence plus a human decision, never straight-through."""
import pytest

from app.profile_packs import registry

CODES = ["CO-01", "CO-02", "CO-03", "CO-05", "CO-06", "CO-08", "ST-04", "ST-05", "ST-07"]
COMPLIANCE = {"CO-01", "CO-02", "CO-03", "CO-05", "CO-06", "CO-08"}


def case(name_prefix, variant):
    from test_profile_goldens import CASES
    key = next(k for k in CASES if k.startswith(f"input/{name_prefix}_") and k.endswith(variant))
    return CASES[key]


@pytest.mark.parametrize("code", CODES)
def test_pack_declares_a_human_decision(code):
    p = registry.get_pack(code)
    assert p is not None, code
    assert p.stp.value == "NEVER"
    assert p.outcome.value in ("DECISION_SUPPORT", "INVESTIGATION")
    assert p.resolver is None and p.decision is not None
    assert [r.type for r in p.evidence.required] == p.evidence.mandatory   # what runs equals what is declared
    assert len(p.decision.options) >= 3 and p.decision.target_field
    assert p.decision.reviewer_role == ("COMPLIANCE_APPROVER" if code in COMPLIANCE else "OPERATIONS_APPROVER")


@pytest.mark.parametrize("code", CODES)
def test_complete_evidence_gives_a_decision_request_never_a_release(code):
    from test_profile_goldens import snapshot
    s = snapshot(case(code, "sufficient"))
    p = registry.get_pack(code)
    assert s["stp_eligible"] is False and s["hitl_required"] is True
    rec = s["resolution_recommendation"]
    assert rec["action"] == "DECISION_REQUIRED"
    assert rec["options"] == p.decision.options and rec["reviewer_role"] == p.decision.reviewer_role
    assert rec["evidence_complete"] is True
    assert s["repaired_fields"] == []          # nothing is auto-repaired or auto-cleared
    assert s["evidence_missing"] == []


@pytest.mark.parametrize("code", CODES)
def test_missing_evidence_holds_and_names_what_is_missing(code):
    from test_profile_goldens import snapshot
    s = snapshot(case(code, "missing_evidence"))
    assert s["stp_eligible"] is False
    assert s["resolution_recommendation"]["action"] == "INVESTIGATION_HOLD"
    assert s["resolution_recommendation"]["missing"] and s["evidence_missing"]


def test_a_never_pack_blocks_straight_through_even_when_everything_else_passes(monkeypatch):
    """Enforcement: DQ-01 with complete evidence is normally straight-through; mark its pack NEVER and it must stop."""
    from test_profile_goldens import CASES, snapshot
    src = CASES["input/DQ-01_invalid_iban_sufficient"]
    assert snapshot(src)["stp_eligible"] is True
    pack = registry.get_pack("DQ-01")
    monkeypatch.setitem(registry.load_packs(), "DQ-01", pack.model_copy(update={"stp": "NEVER"}))
    s = snapshot(src)
    assert s["stp_eligible"] is False
    assert "never straight-through" in s["stp_decision_reason"].lower()


def test_catch_all_still_fails_closed():
    from test_profile_goldens import CASES, snapshot
    s = snapshot(CASES["nofixture/ST-08"])
    assert s["stp_eligible"] is False and s["hitl_required"] is True
