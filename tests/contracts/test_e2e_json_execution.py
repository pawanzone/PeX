"""E2E JSON Execution Harness Tests for Wave 0A.

Executes all 12 canonical initial fixtures through the E2EExecutionHarness, validates
schema output, verifies the 8-predicate evaluation, and ensures bank execution boundaries.
"""
from pathlib import Path
import pytest

from app.services.e2e_runner import E2EExecutionHarness
from app.schemas.contracts.e2e_schemas import CanonicalE2EOutput


class TestE2EJsonExecution:
    """Executes the representative initial fixtures and asserts architectural invariants."""

    @pytest.fixture
    def harness(self):
        return E2EExecutionHarness()

    def test_dq01_sufficient_achieves_stp(self, harness):
        out = harness.process_input(
            "e2e_fixtures/input/DQ-01_invalid_iban_sufficient.json",
            "e2e_fixtures/output/DQ-01_invalid_iban_sufficient.json"
        )
        assert isinstance(out, CanonicalE2EOutput)
        assert out.detected_profile_id == "DQ-01"
        assert out.stp_eligible is True
        assert out.predicate_breakdown.e_suff is True
        assert out.predicate_breakdown.r_det is True
        assert out.predicate_breakdown.v_auth is True
        assert out.predicate_breakdown.p_bank is True
        assert out.predicate_breakdown.c_comp is True
        assert len(out.repaired_fields) == 1
        assert out.execution_owner == "BANK"
        assert out.audit_chain_block_hash != ""

    def test_dq01_missing_evidence_fails_closed(self, harness):
        out = harness.process_input(
            "e2e_fixtures/input/DQ-01_invalid_iban_missing_evidence.json",
            "e2e_fixtures/output/DQ-01_invalid_iban_missing_evidence.json"
        )
        assert out.stp_eligible is False
        assert out.predicate_breakdown.e_suff is False
        assert out.hitl_required is True
        assert "CORE_DDA_ACCOUNT" in out.evidence_missing
        assert out.execution_owner == "BANK"

    def test_dq08_sufficient_achieves_stp(self, harness):
        out = harness.process_input(
            "e2e_fixtures/input/DQ-08_invalid_routing_sufficient.json",
            "e2e_fixtures/output/DQ-08_invalid_routing_sufficient.json"
        )
        assert out.detected_profile_id == "DQ-08"
        assert out.stp_eligible is True
        assert out.predicate_breakdown.r_det is True
        assert len(out.repaired_fields) == 1
        assert out.repaired_fields[0]["repaired_value"] == "021000021"
        assert out.execution_owner == "BANK"

    def test_dq08_ambiguous_matches_fails_closed(self, harness):
        out = harness.process_input(
            "e2e_fixtures/input/DQ-08_invalid_routing_contradictory.json",
            "e2e_fixtures/output/DQ-08_invalid_routing_contradictory.json"
        )
        assert out.stp_eligible is False
        assert out.predicate_breakdown.r_uniq is False # Ambiguous candidate matches
        assert out.hitl_required is True
        assert out.execution_owner == "BANK"

    def test_pr01_duplicate_sufficient_suppresses_and_stps(self, harness):
        out = harness.process_input(
            "e2e_fixtures/input/PR-01_duplicate_payment_sufficient.json",
            "e2e_fixtures/output/PR-01_duplicate_payment_sufficient.json"
        )
        assert out.detected_profile_id == "PR-01"
        assert out.stp_eligible is True
        assert out.resolution_recommendation["action"] == "SUPPRESS_DUPLICATE_AND_NOTIFY"
        assert out.execution_owner == "BANK"

    def test_pr01_missing_history_fails_closed(self, harness):
        out = harness.process_input(
            "e2e_fixtures/input/PR-01_duplicate_payment_missing_history.json",
            "e2e_fixtures/output/PR-01_duplicate_payment_missing_history.json"
        )
        assert out.stp_eligible is False
        assert out.predicate_breakdown.e_suff is False
        assert out.hitl_required is True
        assert out.execution_owner == "BANK"

    def test_pr08_queue_failure_sufficient_recovers_stp(self, harness):
        out = harness.process_input(
            "e2e_fixtures/input/PR-08_queue_failure_sufficient.json",
            "e2e_fixtures/output/PR-08_queue_failure_sufficient.json"
        )
        assert out.detected_profile_id == "PR-08"
        assert out.stp_eligible is True
        assert out.predicate_breakdown.v_auth is True
        assert out.resolution_recommendation["action"] == "RESET_BROKER_PARTITION_AND_RETRY"
        assert out.execution_owner == "BANK"

    def test_pr08_broker_unreachable_fails_closed(self, harness):
        out = harness.process_input(
            "e2e_fixtures/input/PR-08_queue_failure_broker_unreachable.json",
            "e2e_fixtures/output/PR-08_queue_failure_broker_unreachable.json"
        )
        assert out.stp_eligible is False
        assert out.predicate_breakdown.v_auth is False
        assert out.hitl_required is True
        assert out.execution_owner == "BANK"

    def test_st01_returned_payment_sufficient_recredits_stp(self, harness):
        out = harness.process_input(
            "e2e_fixtures/input/ST-01_returned_payment_sufficient.json",
            "e2e_fixtures/output/ST-01_returned_payment_sufficient.json"
        )
        assert out.detected_profile_id == "ST-01"
        assert out.stp_eligible is True
        assert out.resolution_recommendation["action"] == "RECREDIT_DEBTOR_LEDGER"
        assert out.execution_owner == "BANK"

    def test_st01_missing_original_debit_fails_closed(self, harness):
        out = harness.process_input(
            "e2e_fixtures/input/ST-01_returned_payment_missing_original.json",
            "e2e_fixtures/output/ST-01_returned_payment_missing_original.json"
        )
        assert out.stp_eligible is False
        assert out.predicate_breakdown.e_suff is False
        assert out.hitl_required is True
        assert out.execution_owner == "BANK"

    def test_co04_license_exemption_sufficient_achieves_stp(self, harness):
        out = harness.process_input(
            "e2e_fixtures/input/CO-04_restricted_corridor_sufficient.json",
            "e2e_fixtures/output/CO-04_restricted_corridor_sufficient.json"
        )
        assert out.detected_profile_id == "CO-04"
        assert out.stp_eligible is True
        assert out.resolution_recommendation["action"] == "RELEASE_CORRIDOR_HOLD"
        assert out.execution_owner == "BANK"

    def test_co04_prohibited_corridor_fails_closed(self, harness):
        out = harness.process_input(
            "e2e_fixtures/input/CO-04_restricted_corridor_prohibited.json",
            "e2e_fixtures/output/CO-04_restricted_corridor_prohibited.json"
        )
        assert out.detected_profile_id == "CO-04"
        assert out.stp_eligible is False
        assert out.predicate_breakdown.c_comp is False
        assert out.compliance_status == "SANCTIONS_HOLD"
        assert out.hitl_required is True
        assert out.execution_owner == "BANK"
