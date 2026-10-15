"""Canonical E2E Execution Tests for Wave 4 Scenarios (37A to 39B).

Validates:
- Explicit business-field assertions (provisional waiver, dual-auth clearance, camt.056 inquiry dossier)
- Explicit predicate-failure assertions on negative paths
- Explicit fail-closed assertions (investigation status, worklist routing, zero ungrounded mutations)
- Explicit ST-06 zero-autonomous-STP invariant enforcement (MAKER_CHECKER_DUAL_AUTH, bank ownership)
"""
import os
import pytest
from pathlib import Path
from app.services.e2e_runner import e2e_runner

FIXTURES_INPUT_DIR = Path("e2e_fixtures/input")
FIXTURES_OUTPUT_DIR = Path("e2e_fixtures/output")


# ==============================================================================
# SCENARIOS 37A & 37B: TR-01 (KYC EXPIRED)
# ==============================================================================

def test_scenario_37a_tr01_kyc_expired_provisional_waiver():
    in_path = FIXTURES_INPUT_DIR / "TR-01_kyc_expired_sufficient.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-01_kyc_expired_sufficient.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Breakdown
    assert out.detected_profile_id == "TR-01"
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
    assert out.repaired_fields[0]["field_path"] == "customer_kyc.provisional_status"
    assert out.repaired_fields[0]["repaired_value"] == "WAIVER_ACTIVE_30_DAYS"
    assert out.resolution_recommendation is not None
    assert out.resolution_recommendation["provisional_status"] == "WAIVER_ACTIVE_30_DAYS"
    assert out.resolution_recommendation["waiver_duration_days"] == 30
    assert out.resolution_recommendation["execution_owner"] == "BANK"


def test_scenario_37b_tr01_kyc_expired_distressed_fail_closed():
    in_path = FIXTURES_INPUT_DIR / "TR-01_kyc_expired_distressed.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-01_kyc_expired_distressed.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Failure Assertions
    assert out.detected_profile_id == "TR-01"
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


# ==============================================================================
# SCENARIOS 38A & 38B: TR-05 (AUTHORIZATION MISSING)
# ==============================================================================

def test_scenario_38a_tr05_authorization_missing_dual_auth_verified():
    in_path = FIXTURES_INPUT_DIR / "TR-05_authorization_missing_sufficient.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-05_authorization_missing_sufficient.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Breakdown
    assert out.detected_profile_id == "TR-05"
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
    assert out.repaired_fields[0]["field_path"] == "mandate_authorization.status"
    assert out.repaired_fields[0]["repaired_value"] == "DUAL_AUTHORIZATION_VERIFIED"
    assert out.resolution_recommendation is not None
    assert out.resolution_recommendation["authorization_status"] == "DUAL_AUTHORIZATION_VERIFIED"
    assert out.resolution_recommendation["execution_owner"] == "BANK"


def test_scenario_38b_tr05_authorization_missing_unapproved_fail_closed():
    in_path = FIXTURES_INPUT_DIR / "TR-05_authorization_missing_unapproved.json"
    out_path = FIXTURES_OUTPUT_DIR / "TR-05_authorization_missing_unapproved.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Failure Assertions
    assert out.detected_profile_id == "TR-05"
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


# ==============================================================================
# SCENARIOS 39A & 39B: ST-06 (FUNDS TRAPPED AT CORRESPONDENT)
# ==============================================================================

def test_scenario_39a_st06_funds_trapped_camt056_inquiry_zero_auto_stp():
    """Mandatory Invariant: ST-06 is Group 4 Transit Break. Autonomous STP is strictly prohibited."""
    in_path = FIXTURES_INPUT_DIR / "ST-06_funds_trapped_inquiry.json"
    out_path = FIXTURES_OUTPUT_DIR / "ST-06_funds_trapped_inquiry.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Breakdown
    assert out.detected_profile_id == "ST-06"
    assert out.stp_eligible is False  # MANDATORY INVARIANT: Never autonomous STP
    pb = out.predicate_breakdown
    assert pb.e_suff is True
    assert pb.r_det is True
    assert pb.r_uniq is True
    assert pb.v_det is True
    assert pb.v_auth is True
    assert pb.p_bank is False  # Policy strictly disallows autonomous STP on transit breaks
    assert pb.c_comp is True
    assert pb.x_pre is True

    # Lifecycle & Ownership Assertions: Routes to Operations Dual-Auth
    assert out.resolution_status == "RESOLVED"
    assert out.execution_owner == "BANK"
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"
    assert out.next_action == "ROUTE_TO_OPERATIONS_WORKLIST"
    assert out.bank_handoff_status == "MAKER_CHECKER_PENDING"

    # Business Field Assertions: camt.056 inquiry dossier prepared
    assert len(out.repaired_fields) == 1
    assert out.repaired_fields[0]["field_path"] == "transit_investigation.status"
    assert out.repaired_fields[0]["repaired_value"] == "DISPATCH_CAMT_056_INTERMEDIARY_INQUIRY"
    assert out.resolution_recommendation is not None
    assert out.resolution_recommendation["autonomous_stp_prohibited"] is True
    assert out.resolution_recommendation["target_intermediary_bic"] == "DEUTDEDDXXX"
    assert out.resolution_recommendation["inquiry_type"] == "CAMT_056"
    assert out.resolution_recommendation["execution_owner"] == "BANK"


def test_scenario_39b_st06_funds_trapped_telemetry_missing_fail_closed():
    in_path = FIXTURES_INPUT_DIR / "ST-06_funds_trapped_telemetry_missing.json"
    out_path = FIXTURES_OUTPUT_DIR / "ST-06_funds_trapped_telemetry_missing.output.json"
    out = e2e_runner.process_input(in_path, out_path)

    # Classification & Predicate Failure Assertions
    assert out.detected_profile_id == "ST-06"
    assert out.stp_eligible is False
    assert out.predicate_breakdown.r_det is False
    assert out.predicate_breakdown.e_suff is False  # Stale telemetry

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
