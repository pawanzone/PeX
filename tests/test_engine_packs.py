"""Profiles that run on the shared resolution engines (DQ-02, DQ-06, PR-03, PR-05) now have packs.
The pack must agree with the dedicated pipeline on the same payload, and must fail closed without a payload."""
import json

import pytest

from app.profile_packs import registry
from app.schemas.contracts.e2e_schemas import CanonicalE2EInput
from app.services.e2e_runner import E2EExecutionHarness

PROFILES = ["DQ-02", "DQ-06", "PR-03", "PR-05"]


def _run(prefix, variant, amount=None):
    from test_profile_goldens import CASES
    key = next(k for k in CASES if k.startswith(f"input/{prefix}_") and k.endswith("_" + variant))
    raw = json.loads(CASES[key].read_text(encoding="utf-8"))
    if amount is not None:
        raw["payment_info"]["amount"] = amount
    return E2EExecutionHarness().process_input(raw)


@pytest.mark.parametrize("code", PROFILES)
def test_pack_exists_and_is_a_repair_pack_with_an_engine_resolver(code):
    p = registry.get_pack(code)
    assert p is not None and p.outcome.value == "REPAIR" and p.resolver
    assert p.evidence.mandatory_types


# ---------------------------------------------------------------- DQ-02 behaviour through the runner
def test_dq02_inactive_bic_with_one_successor_is_repaired():
    out = _run("DQ-02", "sufficient")
    assert out.resolution_status == "RESOLVED"
    rf = out.repaired_fields[0]
    assert rf["original_value"] == "DRESDEFFXXX" and rf["repaired_value"] == "COBADEDDXXX" and rf["field_path"] == "creditor_agent.bic"
    assert out.resolution_recommendation["action"] == "SUBSTITUTE_FIELD"


def test_dq02_valid_active_bic_needs_no_change():
    out = _run("DQ-02", "valid_active")
    assert out.resolution_status == "RESOLVED" and out.repaired_fields == []
    assert out.resolution_recommendation["action"] == "VALIDATE_NO_CHANGE"


def test_dq02_multiple_successors_is_ambiguous_and_goes_to_a_person():
    out = _run("DQ-02", "ambiguous")
    assert out.stp_eligible is False and out.hitl_required is True
    assert out.resolution_recommendation["action"] == "INVESTIGATION_HOLD"
    assert set(out.resolution_recommendation["candidates"]) == {"BNPAFRPPXXX", "COBADEDDXXX"}


@pytest.mark.parametrize("variant", ["no_successor", "rail_unreachable", "stale_reference"])
def test_dq02_cases_the_engine_cannot_resolve_are_not_straight_through(variant):
    out = _run("DQ-02", variant)
    assert out.resolution_status != "RESOLVED" and out.stp_eligible is False and out.repaired_fields == []


def test_dq02_missing_directory_evidence_is_insufficient():
    out = _run("DQ-02", "missing_evidence")
    assert out.evidence_status == "INSUFFICIENT" and "BIC_REFERENCE_DIRECTORY" in out.evidence_missing and out.stp_eligible is False


def test_dq02_without_a_raw_payload_fails_closed():
    from test_profile_goldens import CASES
    key = next(k for k in CASES if k.startswith("input/DQ-02_") and k.endswith("_sufficient"))
    raw = json.loads(CASES[key].read_text(encoding="utf-8"))
    raw["raw_payload"] = None
    out = E2EExecutionHarness().process_input(raw)
    assert out.resolution_status != "RESOLVED" and out.stp_eligible is False


# ---------------------------------------------------------------- parity with the dedicated pipeline
@pytest.mark.parametrize("variant,xml_name", [("sufficient", "INACTIVE_BIC"), ("valid_active", "ACTIVE_BIC"), ("ambiguous", "MULTIPLE_SUCCESSORS"),
                                               ("no_successor", "NO_SUCCESSOR"), ("rail_unreachable", "RAIL_RESTRICTED")])
def test_dq02_pack_agrees_with_the_dedicated_pipeline(variant, xml_name):
    import test_dq02_evidence_stp_e2e as t
    from app.adapters.input_adapter import InboundPackage
    from app.services.dq02_stp_pipeline import DQ02STPPipeline
    from app.schemas.resolution_contract import ResolutionStatus, ResolutionUniqueness
    pipe = DQ02STPPipeline().process_package(InboundPackage(package_id=f"P-{variant}", source_channel="SWIFT_INBOUND",
                                                           raw_payload_str=getattr(t, "SAMPLE_DQ02_XML_" + xml_name)), amount=22000.0, currency="EUR")
    out = _run("DQ-02", variant)
    determined = pipe.resolution_result.status == ResolutionStatus.RESOLUTION_DETERMINED
    unique = pipe.resolution_result.uniqueness == ResolutionUniqueness.RESOLUTION_UNIQUE
    assert (out.resolution_status == "RESOLVED") == (determined and unique)
    if determined and not unique:
        assert out.resolution_recommendation["action"] == "INVESTIGATION_HOLD"


# ---------------------------------------------------------------- straight-through only when every predicate holds
@pytest.mark.parametrize("prefix", ["DQ-02", "DQ-06", "PR-03", "PR-05"])
def test_a_clean_case_is_straight_through_only_within_the_bank_amount_limit(prefix):
    small = _run(prefix, "sufficient", amount=5000.0)
    assert small.stp_eligible is True and small.predicate_breakdown.stp_formula_result is True
    large = _run(prefix, "sufficient", amount=500000.0)
    assert large.stp_eligible is False and large.predicate_breakdown.p_bank is False
    assert large.resolution_status == "RESOLVED"          # the repair is still proposed; the bank policy decides who releases it


@pytest.mark.parametrize("prefix,variant", [("PR-03", "missing_evidence"), ("PR-05", "missing_evidence"), ("DQ-06", "missing_evidence")])
def test_missing_mandatory_evidence_blocks_straight_through(prefix, variant):
    out = _run(prefix, variant, amount=5000.0)
    assert out.evidence_status == "INSUFFICIENT" and out.evidence_missing and out.stp_eligible is False


# ---------------------------------------------------------------- PR-03
def test_pr03_misordered_message_is_resequenced_without_changing_business_values():
    out = _run("PR-03", "sufficient")
    assert out.resolution_status == "RESOLVED" and out.resolution_recommendation["action"] == "REPLACE_PAYLOAD"
    assert out.repaired_fields[0]["field_path"] == "message.structure" and "Re-sequenced" in out.repaired_fields[0]["repaired_value"]
    fixed = out.resolution_recommendation["value"]
    assert fixed.index("<GrpHdr>") < fixed.index("<CdtTrfTxInf>")
    for kept in ("22000.00", "Originating Corp Inc", "Bavarian Industrial AG"):
        assert kept in fixed


def test_pr03_valid_message_needs_no_change():
    out = _run("PR-03", "already_valid")
    assert out.resolution_status == "RESOLVED" and out.repaired_fields == [] and out.resolution_recommendation["action"] == "VALIDATE_NO_CHANGE"


def test_pr03_unparseable_message_is_not_guessed_at():
    out = _run("PR-03", "unrepairable", amount=5000.0)
    assert out.resolution_status != "RESOLVED" and out.repaired_fields == [] and out.stp_eligible is False


# ---------------------------------------------------------------- PR-05
def test_pr05_authorised_transliteration_is_applied_and_reported():
    out = _run("PR-05", "sufficient")
    assert out.resolution_status == "RESOLVED" and out.resolution_recommendation["action"] == "REPLACE_PAYLOAD"
    assert "ü -> ue" in out.repaired_fields[0]["repaired_value"] and "Mueller GmbH" in out.resolution_recommendation["value"]


def test_pr05_already_compliant_message_needs_no_change():
    out = _run("PR-05", "already_clean")
    assert out.repaired_fields == [] and out.resolution_recommendation["action"] == "VALIDATE_NO_CHANGE"


def test_pr05_without_bank_authority_to_transliterate_it_is_not_straight_through():
    out = _run("PR-05", "policy_denied", amount=5000.0)
    assert out.stp_eligible is False and out.predicate_breakdown.v_det is False and out.repaired_fields == []


# ---------------------------------------------------------------- DQ-06
def test_dq06_purpose_code_is_inferred_from_the_remittance_and_allowed_by_the_bank():
    out = _run("DQ-06", "sufficient")
    rf = out.repaired_fields[0]
    assert rf["field_path"] == "purpose.code" and rf["original_value"] is None and rf["repaired_value"] == "GDSV"
    assert out.resolution_recommendation["action"] == "INSERT_FIELD"


def test_dq06_a_code_the_bank_prohibits_for_this_counterparty_is_never_straight_through():
    out = _run("DQ-06", "prohibited_for_counterparty", amount=5000.0)
    assert out.stp_eligible is False and out.predicate_breakdown.v_det is False


def test_dq06_remittance_with_no_signal_is_left_to_a_person():
    out = _run("DQ-06", "no_signal", amount=5000.0)
    assert out.resolution_status != "RESOLVED" and out.repaired_fields == [] and out.stp_eligible is False and out.hitl_required is True


def test_dq06_without_the_bank_purpose_policy_nothing_is_released():
    out = _run("DQ-06", "no_policy", amount=5000.0)
    assert out.stp_eligible is False and out.repaired_fields == []


# ---------------------------------------------------------------- parity with the dedicated pipelines
def test_pr03_pack_agrees_with_the_dedicated_pipeline():
    from app.adapters.input_adapter import InboundPackage
    from app.services.pr03_stp_pipeline import PR03STPPipeline
    raw = json.loads(__import__("test_profile_goldens").CASES[next(k for k in __import__("test_profile_goldens").CASES if k.startswith("input/PR-03_") and k.endswith("_sufficient"))].read_text(encoding="utf-8"))
    pipe = PR03STPPipeline().process_package(InboundPackage(package_id="P-pr03", source_channel="SWIFT_INBOUND", raw_payload_str=raw["raw_payload"]["raw_text"]), amount=22000.0, currency="EUR")
    out = _run("PR-03", "sufficient")
    assert pipe.resolution_result.primary_candidate.diff_summary == out.repaired_fields[0]["repaired_value"]
    assert pipe.resolution_result.primary_candidate.repaired_payload == out.resolution_recommendation["value"]
