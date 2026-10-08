"""Unit Tests for AccountMasterEngine (DQ-03, DQ-07, DQ-09).

Verifies deterministic master resolution, account validation, and Verification of Payee
under W1-POL-01 threshold bands with zero autonomous synthetic data invention.
"""
import pytest
from app.services.engines.account_master_engine import AccountMasterEngine
from app.adapters.reference.reference_account_master_adapter import InMemoryAccountMasterAdapter
from app.schemas.contracts.policy_schemas import W1PolicyMatchingThresholds
from app.schemas.resolution_contract import ResolutionStatus, ResolutionUniqueness


@pytest.fixture
def engine():
    return AccountMasterEngine()


class TestAccountMasterEngineDQ03:
    """Tests for DQ-03: Missing Beneficiary Data."""

    def test_dq03_happy_path_dda_lookup(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_dq03_missing_beneficiary(
            debtor_id="DEBTOR-001",
            account_number="12345678",
            creditor_hint="ACME"
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
        assert cand is not None
        assert cand.repaired_structured["creditor_name"] == "ACME INDUSTRIAL SUPPLIES LTD"
        assert cand.repaired_structured["tax_id"] == "GB123456789"
        assert err is None

    def test_dq03_happy_path_client_master_profile(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_dq03_missing_beneficiary(
            debtor_id="DEBTOR-002",
            account_number="11223344",
            creditor_hint="SIEMENS"
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert cand.repaired_structured["creditor_name"] == "SIEMENS AG INDUSTRIAL POWER"

    def test_dq03_ambiguous_profiles_routes_to_hitl(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_dq03_missing_beneficiary(
            debtor_id="DEBTOR-001",
            account_number="12345678",
            evidence_context={"ambiguous_beneficiary_matches": True}
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_AMBIGUOUS
        assert cand is None
        assert "Ambiguous" in err

    def test_dq03_missing_account_record_fails_closed(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_dq03_missing_beneficiary(
            debtor_id="UNKNOWN_DEBTOR",
            account_number="99999999",
            creditor_hint="NONEXISTENT"
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert cand is None
        assert "Missing" in err


class TestAccountMasterEngineDQ07:
    """Tests for DQ-07: Invalid Account Number."""

    def test_dq07_valid_account_resolution(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_dq07_invalid_account_number(
            inbound_account_number="87654321",
            clearing_rail="TARGET2",
            currency="EUR"
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
        assert cand is not None
        assert cand.repaired_structured["account_number"] == "87654321"
        assert cand.repaired_structured["account_title"] == "GLOBAL LOGISTICS GMBH"

    def test_dq07_account_not_found_fails_closed(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_dq07_invalid_account_number(
            inbound_account_number="00000000",
            clearing_rail="TARGET2",
            currency="EUR"
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert cand is None
        assert "not found" in err.lower()

    def test_dq07_currency_mismatch_fails_closed(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_dq07_invalid_account_number(
            inbound_account_number="87654321", # EUR account
            clearing_rail="FEDWIRE",
            currency="USD"
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert "mismatch" in err.lower()

    def test_dq07_ambiguous_candidates_routes_to_hitl(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_dq07_invalid_account_number(
            inbound_account_number="87654321",
            clearing_rail="TARGET2",
            currency="EUR",
            evidence_context={"ambiguous_account_candidates": True}
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_AMBIGUOUS


class TestAccountMasterEngineDQ09:
    """Tests for DQ-09: Beneficiary Name Mismatch / Confirmation of Payee."""

    def test_dq09_exact_match(self, engine):
        policy = W1PolicyMatchingThresholds(exact_match_threshold=1.0, close_match_threshold=0.85)
        status, uniq, cand, diffs, err = engine.resolve_dq09_beneficiary_name_mismatch(
            account_number="12345678",
            inbound_payee_name="ACME INDUSTRIAL SUPPLIES LTD",
            policy_thresholds=policy
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
        assert cand.repaired_structured["vop_score"] == 1.0

    def test_dq09_close_match_allowed_by_policy(self, engine):
        policy = W1PolicyMatchingThresholds(exact_match_threshold=1.0, close_match_threshold=0.80, allow_close_match_stp=True)
        status, uniq, cand, diffs, err = engine.resolve_dq09_beneficiary_name_mismatch(
            account_number="11223344", # Title: "SIEMENS AG INDUSTRIAL POWER"
            inbound_payee_name="SIEMENS INDUSTRIAL POWER",
            policy_thresholds=policy
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert cand.repaired_structured["creditor_name"] == "SIEMENS AG INDUSTRIAL POWER"
        assert cand.repaired_structured["vop_score"] >= 0.80

    def test_dq09_no_match_routes_to_hitl(self, engine):
        policy = W1PolicyMatchingThresholds(close_match_threshold=0.85)
        status, uniq, cand, diffs, err = engine.resolve_dq09_beneficiary_name_mismatch(
            account_number="11223344",
            inbound_payee_name="COMPLETELY DIFFERENT COMPANY",
            policy_thresholds=policy
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert cand is None
        assert "mismatch" in err.lower()

    def test_dq09_account_not_found(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_dq09_beneficiary_name_mismatch(
            account_number="99999999",
            inbound_payee_name="ANY NAME"
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert "not found" in err.lower()
