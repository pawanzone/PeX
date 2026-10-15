"""Adversarial Single-Predicate and Compound Mutation Tests for Wave 4 Profiles.

Verifies isolated predicate-failure mechanics across all 8 canonical STP predicates:
E_suff, R_det, R_uniq, V_det, V_auth, P_bank, C_comp, X_pre
and enforces the ST-06 zero-autonomous-STP invariant under adversarial variations.
"""
import copy
import json
import pytest
from pathlib import Path
from app.services.e2e_runner import e2e_runner

FIXTURES_INPUT_DIR = Path("e2e_fixtures/input")


def load_fixture(fixture_name: str) -> dict:
    p = FIXTURES_INPUT_DIR / fixture_name
    return json.loads(p.read_text(encoding="utf-8"))


# ==============================================================================
# CATEGORY A: ISOLATED SINGLE-PREDICATE MUTATIONS
# ==============================================================================

# --- Predicate 1: E_suff (Evidence Sufficiency) ---

def test_cat_a_01_e_suff_tr01_missing_mandatory_kyc():
    data = load_fixture("TR-01_kyc_expired_sufficient.json")
    del data["bank_supplied_evidence"]["customer_kyc_record"]
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.e_suff is False
    # Other predicates remain unviolated where evaluated
    assert out.execution_owner == "BANK"
    assert out.hitl_required is True


def test_cat_a_02_e_suff_tr05_missing_mandatory_mandate():
    data = load_fixture("TR-05_authorization_missing_sufficient.json")
    del data["bank_supplied_evidence"]["corporate_mandate_record"]
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.e_suff is False
    assert out.execution_owner == "BANK"
    assert out.hitl_required is True


def test_cat_a_03_e_suff_st06_missing_mandatory_tracker():
    data = load_fixture("ST-06_funds_trapped_inquiry.json")
    del data["bank_supplied_evidence"]["tracker_hop_record"]
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.e_suff is False
    assert out.execution_owner == "BANK"


# --- Predicate 2: R_det (Deterministic Resolution Derivation) ---

def test_cat_a_04_r_det_tr01_no_refresh_in_progress():
    data = load_fixture("TR-01_kyc_expired_sufficient.json")
    data["bank_supplied_evidence"]["customer_kyc_record"]["refresh_in_progress"] = False
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.e_suff is True
    assert out.predicate_breakdown.r_det is False
    assert out.resolution_recommendation is None


def test_cat_a_05_r_det_tr05_signature_pending():
    data = load_fixture("TR-05_authorization_missing_sufficient.json")
    data["bank_supplied_evidence"]["secondary_signatory_record"]["signature_status"] = "PENDING"
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.e_suff is True
    assert out.predicate_breakdown.r_det is False
    assert out.resolution_recommendation is None


def test_cat_a_06_r_det_st06_unconfirmed_debit():
    data = load_fixture("ST-06_funds_trapped_inquiry.json")
    data["bank_supplied_evidence"]["debit_confirmation_record"]["is_confirmed"] = False
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.e_suff is True
    assert out.predicate_breakdown.r_det is False
    assert out.resolution_recommendation is None


# --- Predicate 3: R_uniq (Resolution Uniqueness) ---

def test_cat_a_07_r_uniq_tr01_ambiguous_candidates():
    data = load_fixture("TR-01_kyc_expired_sufficient.json")
    data["bank_supplied_evidence"]["ambiguous_candidates"] = True
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.r_det is True
    assert out.predicate_breakdown.r_uniq is False
    assert out.hitl_required is True


def test_cat_a_08_r_uniq_tr05_ambiguous_candidates():
    data = load_fixture("TR-05_authorization_missing_sufficient.json")
    data["bank_supplied_evidence"]["ambiguous_candidates"] = True
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.r_det is True
    assert out.predicate_breakdown.r_uniq is False
    assert out.hitl_required is True


def test_cat_a_09_r_uniq_st06_ambiguous_candidates():
    data = load_fixture("ST-06_funds_trapped_inquiry.json")
    data["bank_supplied_evidence"]["ambiguous_candidates"] = True
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.r_det is True
    assert out.predicate_breakdown.r_uniq is False


# --- Predicate 4: V_det (Deterministic Validation) ---

def test_cat_a_10_v_det_tr01_validation_failure():
    data = load_fixture("TR-01_kyc_expired_sufficient.json")
    data["bank_supplied_evidence"]["deterministic_validation_failed"] = True
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.v_det is False
    assert out.hitl_required is True


def test_cat_a_11_v_det_tr05_syntax_failure():
    data = load_fixture("TR-05_authorization_missing_sufficient.json")
    data["bank_supplied_evidence"]["syntax_validation_failed"] = True
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.v_det is False
    assert out.hitl_required is True


def test_cat_a_12_v_det_st06_validation_failure():
    data = load_fixture("ST-06_funds_trapped_inquiry.json")
    data["bank_supplied_evidence"]["deterministic_validation_failed"] = True
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.v_det is False


# --- Predicate 5: V_auth (Contextual Authority Validation) ---

def test_cat_a_13_v_auth_tr01_authority_unavailable():
    data = load_fixture("TR-01_kyc_expired_sufficient.json")
    data["bank_supplied_evidence"]["simulate_authority_unavailable"] = True
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.v_auth is False
    assert out.hitl_required is True


def test_cat_a_14_v_auth_tr05_authority_unavailable():
    data = load_fixture("TR-05_authorization_missing_sufficient.json")
    data["bank_supplied_evidence"]["simulate_authority_unavailable"] = True
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.v_auth is False
    assert out.hitl_required is True


def test_cat_a_15_v_auth_st06_authority_unavailable():
    data = load_fixture("ST-06_funds_trapped_inquiry.json")
    data["bank_supplied_evidence"]["simulate_authority_unavailable"] = True
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.v_auth is False


# --- Predicate 6: P_bank (Bank Policy Authorization) ---

def test_cat_a_16_p_bank_tr01_amount_exceeds_auto_threshold():
    data = load_fixture("TR-01_kyc_expired_sufficient.json")
    data["payment_info"]["amount"] = 35000.0  # Exceeds max_autonomous_stp_amount ($10k)
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.p_bank is False
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"


def test_cat_a_17_p_bank_tr05_amount_exceeds_auto_threshold():
    data = load_fixture("TR-05_authorization_missing_sufficient.json")
    data["payment_info"]["amount"] = 55000.0  # Exceeds max_autonomous_stp_amount ($10k)
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.p_bank is False
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"


# --- Predicate 7: C_comp (Regulatory & Sanctions Screening) ---

def test_cat_a_18_c_comp_tr01_sanctions_match():
    data = load_fixture("TR-01_kyc_expired_sufficient.json")
    data["payment_info"]["creditor_name"] = "SANCTIONED ENTITY OFAC"
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.c_comp is False
    assert out.hitl_required is True


def test_cat_a_19_c_comp_tr05_sanctions_match():
    data = load_fixture("TR-05_authorization_missing_sufficient.json")
    data["payment_info"]["creditor_name"] = "SANCTIONED ENTITY OFAC"
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.c_comp is False
    assert out.hitl_required is True


def test_cat_a_20_c_comp_st06_sanctions_match():
    data = load_fixture("ST-06_funds_trapped_inquiry.json")
    data["payment_info"]["creditor_name"] = "SANCTIONED ENTITY OFAC"
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.c_comp is False


# --- Predicate 8: X_pre (Execution Preconditions) ---

def test_cat_a_21_x_pre_tr01_idempotency_collision():
    data = load_fixture("TR-01_kyc_expired_sufficient.json")
    data["bank_supplied_evidence"]["idempotency_locked"] = True
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.x_pre is False
    assert out.hitl_required is True


def test_cat_a_22_x_pre_tr05_idempotency_collision():
    data = load_fixture("TR-05_authorization_missing_sufficient.json")
    data["bank_supplied_evidence"]["idempotency_locked"] = True
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.x_pre is False
    assert out.hitl_required is True


def test_cat_a_23_x_pre_st06_idempotency_collision():
    data = load_fixture("ST-06_funds_trapped_inquiry.json")
    data["bank_supplied_evidence"]["idempotency_locked"] = True
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.x_pre is False


# ==============================================================================
# CATEGORY B: INVARIANT & COMPOUND MUTATIONS
# ==============================================================================

def test_cat_b_01_st06_zero_auto_stp_invariant():
    """Invariant: Even with pristine telemetry and low amount, ST-06 never STPs autonomously."""
    data = load_fixture("ST-06_funds_trapped_inquiry.json")
    data["payment_info"]["amount"] = 500.0  # Even micro-amount must route to Maker-Checker
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.p_bank is False
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"
    assert out.execution_owner == "BANK"


def test_cat_b_02_compound_tr01_missing_evidence_and_sar_flag():
    """Compound: Missing mandatory evidence AND active SAR flag."""
    data = load_fixture("TR-01_kyc_expired_sufficient.json")
    del data["bank_supplied_evidence"]["corporate_standing_record"]
    data["bank_supplied_evidence"]["customer_kyc_record"]["refresh_in_progress"] = False
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.e_suff is False
    assert out.predicate_breakdown.r_det is False
    assert out.hitl_required is True
    assert out.execution_owner == "BANK"


def test_cat_b_03_compound_tr05_unauthorized_signer_and_unverified_authority():
    """Compound: Signer unauthorized AND authority unavailable."""
    data = load_fixture("TR-05_authorization_missing_sufficient.json")
    data["bank_supplied_evidence"]["secondary_signatory_record"]["signer_class"] = "CLASS_UNAUTHORIZED"
    data["bank_supplied_evidence"]["simulate_authority_unavailable"] = True
    out = e2e_runner.process_input(data)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.r_det is False
    assert out.predicate_breakdown.v_auth is False
    assert out.hitl_required is True
    assert out.execution_owner == "BANK"
