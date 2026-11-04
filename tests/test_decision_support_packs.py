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
    assert p.evidence.mandatory_types   # what runs is what is declared (see test_evidence_single_source)
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


# ---- what each option does to the case (derived from the option names; to be validated by SMEs) ------------
EFFECTS = {
    "CO-01": {"FALSE_POSITIVE_HOMONYM_CLEARED": "PROCEED", "TRUE_MATCH_CONFIRMED_BLOCK": "STOP", "ESCALATE_SENIOR_COMPLIANCE": "ESCALATE"},
    "CO-02": {"EDD_VERIFIED_COMMERCIAL_TRADE": "PROCEED", "REQUEST_MORE_INFORMATION": "HOLD", "ESCALATE_FOR_SAR_REVIEW": "ESCALATE"},
    "CO-03": {"PEP_EDD_CLEARED": "PROCEED", "PEP_REJECTED": "STOP", "ESCALATE_SENIOR_COMPLIANCE": "ESCALATE"},
    "CO-05": {"ADVERSE_MEDIA_CLEARED": "PROCEED", "RESTRICT_COUNTERPARTY": "STOP", "REFER_TO_SIU": "ESCALATE"},
    "CO-06": {"FATF_ECDD_VERIFIED_TRANSACTION": "PROCEED", "RETURN_PAYMENT": "STOP", "FILE_REGULATORY_REPORT": "ESCALATE"},
    "CO-08": {"INTERNAL_WATCHLIST_WAIVER_APPROVED": "PROCEED", "BLOCK_PER_EXIT_MEMO": "STOP", "ESCALATE_CREDIT_OFFICER": "ESCALATE"},
    "ST-04": {"POST_FEE_ADJUSTMENT_WITHIN_TOLERANCE": "PROCEED", "RAISE_INVESTIGATION_WITH_CORRESPONDENT": "HOLD", "ESCALATE_TREASURY_OPERATIONS": "ESCALATE"},
    "ST-05": {"CONTINGENCY_CLEARING_WINDOW_DISPATCH": "PROCEED", "RECALL_AND_RETURN": "STOP", "ESCALATE_TO_SETTLEMENT_OPERATIONS": "ESCALATE"},
    "ST-07": {"ALLOCATE_TO_DEBTOR_RECEIVABLES_LEDGER": "PROCEED", "HOLD_IN_SUSPENSE": "HOLD", "RETURN_TO_ORDERING_BANK": "STOP"},
}


@pytest.mark.parametrize("code", CODES)
def test_every_option_declares_its_effect(code):
    d = registry.get_pack(code).decision
    assert {k: v.value for k, v in d.effects.items()} == EFFECTS[code]
    assert set(d.effects) == set(d.options)


@pytest.mark.parametrize("code", CODES)
def test_a_decision_can_both_proceed_and_not_proceed(code):
    vals = {v.value for v in registry.get_pack(code).decision.effects.values()}
    assert "PROCEED" in vals and len(vals) >= 2


def test_effects_must_cover_the_options_exactly():
    from pydantic import ValidationError
    from app.profile_packs.schema import DecisionSpec
    with pytest.raises(ValidationError):
        DecisionSpec(target_field="x.y", options=["A", "B"], reviewer_role="R", effects={"A": "PROCEED"})
    with pytest.raises(ValidationError):
        DecisionSpec(target_field="x.y", options=["A", "B"], reviewer_role="R", effects={"A": "PROCEED", "B": "MAYBE"})
    with pytest.raises(ValidationError):
        DecisionSpec(target_field="x.y", options=["A", "B"], reviewer_role="R", effects={"A": "PROCEED", "C": "STOP"})
    DecisionSpec(target_field="x.y", options=["A", "B"], reviewer_role="R", effects={"A": "PROCEED", "B": "STOP"})
