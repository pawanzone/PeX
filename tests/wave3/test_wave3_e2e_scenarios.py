"""Canonical E2E Execution Tests for Wave 3 Scenarios (31A to 36B).

Hardened in accordance with Remediation Gate v0.1.4:
- Explicit business-field assertions (repaired field paths, values, pacing schedules, dossier IDs)
- Explicit predicate-failure assertions on negative paths
- Explicit fail-closed assertions (investigation status, worklist routing, zero ungrounded mutations)
- Explicit TR-08 zero-autonomous-STP invariant enforcement (MAKER_CHECKER_DUAL_AUTH, bank ownership)
"""
import os
import pytest
from pathlib import Path
from app.services.e2e_runner import e2e_runner

FIXTURES_INPUT_DIR = Path("e2e_fixtures/input")
FIXTURES_OUTPUT_DIR = Path("e2e_fixtures/output")


def test_scenario_31a_tr02_sufficient_intraday_reservation():
    in_path = FIXTURES_INPUT_DIR / "TR-02_insufficient_funds_sufficient.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-02_insufficient_funds_sufficient.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Assertions
    assert out.detected_profile_id == "TR-02"
    assert out.stp_eligible is True
    pb = out.predicate_breakdown
    assert pb.e_suff is True
    assert pb.r_det is True
    assert pb.r_uniq is True
    assert pb.v_det is True
    assert pb.v_auth is True
    assert pb.p_bank is True
    assert pb.c_comp is True
    assert pb.x_pre is True

    # Lifecycle & Ownership Assertions
    assert out.resolution_status == "RESOLVED"
    assert out.execution_owner == "BANK"
    assert out.hitl_required is False
    assert out.approval_requirement == "NONE_AUTONOMOUS_STP"
    assert out.bank_handoff_status == "BANK_HANDOFF_READY"

    # Business Field Assertions
    assert len(out.repaired_fields) == 1
    assert out.repaired_fields[0]["field_path"] == "treasury.reservation_id"
    assert str(out.repaired_fields[0]["repaired_value"]).startswith("RES-")
    assert out.resolution_recommendation is not None
    assert out.resolution_recommendation["reservation_id"] == out.repaired_fields[0]["repaired_value"]
    assert out.resolution_recommendation["resolution_action"] == "FUNDS_RESERVED_RELEASE_PAYMENT"
    assert out.resolution_recommendation["account_number"] == "ACCT-CORP-USD-001"
    assert out.resolution_recommendation["instructed_amount"] == 5000.0


def test_scenario_31b_tr02_insufficient_deficit_fail_closed():
    in_path = FIXTURES_INPUT_DIR / "TR-02_insufficient_funds_deficit.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-02_insufficient_funds_deficit.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Failure Assertions
    assert out.detected_profile_id == "TR-02"
    assert out.stp_eligible is False
    assert out.predicate_breakdown.r_det is False
    assert out.predicate_breakdown.p_bank is False
    assert out.predicate_breakdown.e_suff is True

    # Fail-Closed Lifecycle Assertions
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"
    assert out.resolution_status == "INVESTIGATION_REQUIRED"
    assert out.execution_owner == "BANK"
    assert out.next_action == "ROUTE_TO_OPERATIONS_WORKLIST"
    assert out.bank_handoff_status == "MAKER_CHECKER_PENDING"

    # Business Field Assertions: Zero ungrounded mutations
    assert out.resolution_recommendation is None
    assert len(out.repaired_fields) == 0
    assert "fails closed to hitl" in out.resolution_basis.lower() or "deficit" in out.resolution_basis.lower()


def test_scenario_32a_tr03_nostro_shortfall_rebalancing():
    in_path = FIXTURES_INPUT_DIR / "TR-03_nostro_shortfall_sufficient.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-03_nostro_shortfall_sufficient.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Assertions
    assert out.detected_profile_id == "TR-03"
    assert out.stp_eligible is True
    pb = out.predicate_breakdown
    assert pb.e_suff is True
    assert pb.r_det is True
    assert pb.r_uniq is True
    assert pb.v_det is True
    assert pb.v_auth is True
    assert pb.p_bank is True
    assert pb.c_comp is True
    assert pb.x_pre is True

    # Lifecycle & Ownership Assertions
    assert out.resolution_status == "RESOLVED"
    assert out.execution_owner == "BANK"
    assert out.hitl_required is False
    assert out.approval_requirement == "NONE_AUTONOMOUS_STP"
    assert out.bank_handoff_status == "BANK_HANDOFF_READY"

    # Business Field Assertions
    assert out.resolution_recommendation is not None
    assert out.resolution_recommendation["nostro_bic"] == "BNPAFRPPXXX"
    assert out.resolution_recommendation["instructed_amount"] == 8000.0
    assert out.resolution_recommendation["currency"] == "EUR"
    assert out.resolution_recommendation["resolution_action"] == "NOSTRO_POSITION_VERIFIED_RELEASE"


def test_scenario_32b_tr03_nostro_shortfall_unfunded_fail_closed():
    in_path = FIXTURES_INPUT_DIR / "TR-03_nostro_shortfall_unfunded.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-03_nostro_shortfall_unfunded.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Failure Assertions
    assert out.detected_profile_id == "TR-03"
    assert out.stp_eligible is False
    assert out.predicate_breakdown.r_det is False
    assert out.predicate_breakdown.p_bank is False
    assert out.predicate_breakdown.e_suff is True

    # Fail-Closed Lifecycle Assertions
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"
    assert out.resolution_status == "INVESTIGATION_REQUIRED"
    assert out.execution_owner == "BANK"
    assert out.next_action == "ROUTE_TO_OPERATIONS_WORKLIST"
    assert out.bank_handoff_status == "MAKER_CHECKER_PENDING"

    # Business Field Assertions: Zero ungrounded mutations
    assert out.resolution_recommendation is None
    assert len(out.repaired_fields) == 0
    assert "shortfall" in out.resolution_basis.lower()


def test_scenario_33a_tr04_fx_rate_fresh_market_quote():
    in_path = FIXTURES_INPUT_DIR / "TR-04_fx_rate_unavailable_sufficient.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-04_fx_rate_unavailable_sufficient.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Assertions
    assert out.detected_profile_id == "TR-04"
    assert out.stp_eligible is True
    pb = out.predicate_breakdown
    assert pb.e_suff is True
    assert pb.r_det is True
    assert pb.r_uniq is True
    assert pb.v_det is True
    assert pb.v_auth is True
    assert pb.p_bank is True
    assert pb.c_comp is True
    assert pb.x_pre is True

    # Lifecycle & Ownership Assertions
    assert out.resolution_status == "RESOLVED"
    assert out.execution_owner == "BANK"
    assert out.hitl_required is False
    assert out.approval_requirement == "NONE_AUTONOMOUS_STP"

    # Business Field Assertions: Verify FX rate and settlement amounts
    assert len(out.repaired_fields) == 2
    paths = {f["field_path"]: f["repaired_value"] for f in out.repaired_fields}
    assert "payment.fx_applied_rate" in paths
    assert "payment.settlement_amount" in paths
    assert paths["payment.fx_applied_rate"] == 1.085
    assert paths["payment.settlement_amount"] == 8137.5
    assert out.resolution_recommendation["currency_pair"] == "EUR/USD"
    assert out.resolution_recommendation["applied_rate"] == 1.085
    assert out.resolution_recommendation["settlement_amount"] == 8137.5


def test_scenario_33b_tr04_fx_rate_stale_fail_closed():
    in_path = FIXTURES_INPUT_DIR / "TR-04_fx_rate_unavailable_stale.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-04_fx_rate_unavailable_stale.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Failure Assertions
    assert out.detected_profile_id == "TR-04"
    assert out.stp_eligible is False
    assert out.predicate_breakdown.r_det is False
    assert out.predicate_breakdown.e_suff is True

    # Fail-Closed Lifecycle Assertions
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"
    assert out.resolution_status == "INVESTIGATION_REQUIRED"
    assert out.execution_owner == "BANK"
    assert out.next_action == "ROUTE_TO_OPERATIONS_WORKLIST"

    # Business Field Assertions: Zero ungrounded mutations
    assert out.resolution_recommendation is None
    assert len(out.repaired_fields) == 0
    assert "stale" in out.resolution_basis.lower() or "fails closed" in out.resolution_basis.lower()


def test_scenario_34a_tr06_limit_breach_sufficient_headroom():
    in_path = FIXTURES_INPUT_DIR / "TR-06_limit_breach_sufficient.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-06_limit_breach_sufficient.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Assertions
    assert out.detected_profile_id == "TR-06"
    assert out.stp_eligible is True
    pb = out.predicate_breakdown
    assert pb.e_suff is True
    assert pb.r_det is True
    assert pb.p_bank is True

    # Lifecycle & Ownership Assertions
    assert out.resolution_status == "RESOLVED"
    assert out.execution_owner == "BANK"
    assert out.hitl_required is False
    assert out.approval_requirement == "NONE_AUTONOMOUS_STP"

    # Business Field Assertions
    assert out.resolution_recommendation["limit_id"] == "LIM-DAILY-CORP-01"
    assert out.resolution_recommendation["resolution_action"] == "LIMIT_HEADROOM_CONFIRMED_RELEASE"


def test_scenario_34b_tr06_limit_breach_hard_waiver_dossier():
    in_path = FIXTURES_INPUT_DIR / "TR-06_limit_breach_hard_waiver.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-06_limit_breach_hard_waiver.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Failure Assertions
    assert out.detected_profile_id == "TR-06"
    assert out.stp_eligible is False
    assert out.predicate_breakdown.p_bank is False  # High value ($250k) blocks auto STP

    # Fail-Closed Lifecycle Assertions
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"
    assert out.execution_owner == "BANK"

    # Business Field Assertions: Limit Pacing Schedule & Dossier Assembly
    assert len(out.repaired_fields) == 1
    assert out.repaired_fields[0]["field_path"] == "treasury.limit_pacing"
    pacing = out.repaired_fields[0]["repaired_value"]
    assert pacing["target_profile"] == "TR-06"
    assert pacing["execution_owner"] == "BANK"
    assert str(out.resolution_recommendation["dossier_id"]).startswith("DOS-LIM-")
    assert out.resolution_recommendation["requires_credit_approver"] is True


def test_scenario_35a_tr07_liquidity_constraint_sufficient():
    in_path = FIXTURES_INPUT_DIR / "TR-07_liquidity_constraint_sufficient.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-07_liquidity_constraint_sufficient.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Assertions
    assert out.detected_profile_id == "TR-07"
    assert out.stp_eligible is True
    pb = out.predicate_breakdown
    assert pb.e_suff is True
    assert pb.r_det is True
    assert pb.p_bank is True

    # Lifecycle & Ownership Assertions
    assert out.resolution_status == "RESOLVED"
    assert out.execution_owner == "BANK"
    assert out.hitl_required is False
    assert out.approval_requirement == "NONE_AUTONOMOUS_STP"

    # Business Field Assertions
    assert out.resolution_recommendation["clearing_context"] == "FEDWIRE"
    assert out.resolution_recommendation["resolution_action"] == "LIQUIDITY_BUFFER_VERIFIED_RELEASE"


def test_scenario_35b_tr07_liquidity_constraint_exhausted():
    in_path = FIXTURES_INPUT_DIR / "TR-07_liquidity_constraint_exhausted.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-07_liquidity_constraint_exhausted.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Failure Assertions
    assert out.detected_profile_id == "TR-07"
    assert out.stp_eligible is False
    assert out.predicate_breakdown.p_bank is False  # High value ($2M) blocks auto STP

    # Fail-Closed Lifecycle Assertions
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"
    assert out.execution_owner == "BANK"

    # Business Field Assertions: Liquidity Pacing Schedule
    assert len(out.repaired_fields) == 1
    assert out.repaired_fields[0]["field_path"] == "treasury.liquidity_pacing"
    pacing = out.repaired_fields[0]["repaired_value"]
    assert pacing["target_profile"] == "TR-07"
    assert pacing["execution_owner"] == "BANK"
    assert out.resolution_recommendation["resolution_action"] == "QUEUE_FOR_LIQUIDITY_PACING_RELEASE"


def test_scenario_36a_tr08_credit_exposure_dossier_zero_auto_stp():
    in_path = FIXTURES_INPUT_DIR / "TR-08_credit_exposure_breach_dossier.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-08_credit_exposure_breach_dossier.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # STRICT MANDATORY INVARIANT: TR-08 must NEVER achieve autonomous STP
    assert out.detected_profile_id == "TR-08"
    assert out.stp_eligible is False
    assert out.predicate_breakdown.p_bank is False
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"
    assert out.execution_owner == "BANK"

    # Business Field Assertions: Credit Dossier Assembly
    assert len(out.repaired_fields) == 1
    assert out.repaired_fields[0]["field_path"] == "compliance.credit_dossier_id"
    dossier_id = out.repaired_fields[0]["repaired_value"]
    assert str(dossier_id).startswith("DOS-CREDIT-")
    assert out.resolution_recommendation["autonomous_stp_prohibited"] is True
    assert out.resolution_recommendation["facility_record"]["approval_tier_required"] == "SENIOR_CREDIT_OFFICER"
    assert "Autonomous STP is STRICTLY PROHIBITED" in out.resolution_basis


def test_scenario_36b_tr08_credit_exposure_distressed():
    in_path = FIXTURES_INPUT_DIR / "TR-08_credit_exposure_breach_distressed.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-08_credit_exposure_breach_distressed.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # STRICT MANDATORY INVARIANT: TR-08 distressed facility fails closed
    assert out.detected_profile_id == "TR-08"
    assert out.stp_eligible is False
    assert out.predicate_breakdown.p_bank is False
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"
    assert out.execution_owner == "BANK"

    # Business Field Assertions: Sub-investment distressed rating flagged
    assert len(out.repaired_fields) == 1
    assert out.repaired_fields[0]["field_path"] == "compliance.credit_dossier_id"
    exp = out.resolution_recommendation["exposure_record"]
    assert exp["credit_rating"] == "SUB_INVESTMENT"
    assert exp["is_breached"] is True
    assert out.resolution_recommendation["autonomous_stp_prohibited"] is True
    assert "distressed credit rating" in out.resolution_basis.lower()
