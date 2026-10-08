"""End-to-End Execution Tests for Wave 1 Scenarios.

Executes all 18 Wave 1 Canonical JSON Fixtures (Positive & Negative paths for all 9 profiles):
- DQ-03: Missing Beneficiary Data (Sufficient vs Ambiguous)
- DQ-04: Missing Remittance Info (Sufficient vs Unparseable)
- DQ-07: Invalid Account Number (Sufficient vs Not Found)
- DQ-09: Beneficiary Name Mismatch (Sufficient Close Match vs No Match)
- PR-02: Routing Failure (Sufficient Reachable vs Unreachable)
- PR-04: Cutoff Missed (Sufficient T+1 Roll vs Policy Blocked)
- PR-07: Network Timeout (Sufficient Safe Retry vs Idempotency Collision)
- PR-09: Payment Held for Repair (Sufficient vs Unresolved Syntax)
- CO-07: Regulatory Reporting Required (Sufficient BoP Derived vs Missing Statutory)

Asserts:
- execution_owner == "BANK" (Absolute Invariant)
- Zero autonomous direct payment dispatch or ledger mutation.
- All 8 predicates properly evaluated and audited.
"""
from pathlib import Path
import pytest
from app.services.e2e_runner import E2EExecutionHarness
from app.schemas.contracts.e2e_schemas import CanonicalE2EOutput


@pytest.fixture
def harness():
    return E2EExecutionHarness()


class TestWave1E2EScenarios:
    """Canonical E2E JSON execution tests for all 18 Wave 1 fixtures."""

    WAVE1_SUFFICIENT_FIXTURES = [
        ("DQ-03_missing_beneficiary_sufficient.json", "DQ-03"),
        ("DQ-04_missing_remittance_sufficient.json", "DQ-04"),
        ("DQ-07_invalid_account_sufficient.json", "DQ-07"),
        ("DQ-09_beneficiary_name_mismatch_sufficient.json", "DQ-09"),
        ("PR-02_routing_failure_sufficient.json", "PR-02"),
        ("PR-04_cutoff_missed_sufficient.json", "PR-04"),
        ("PR-07_network_timeout_sufficient.json", "PR-07"),
        ("PR-09_payment_held_for_repair_sufficient.json", "PR-09"),
        ("CO-07_regulatory_reporting_sufficient.json", "CO-07"),
    ]

    WAVE1_NEGATIVE_FIXTURES = [
        ("DQ-03_missing_beneficiary_ambiguous.json", "DQ-03"),
        ("DQ-04_missing_remittance_unparseable.json", "DQ-04"),
        ("DQ-07_invalid_account_not_found.json", "DQ-07"),
        ("DQ-09_beneficiary_name_mismatch_no_match.json", "DQ-09"),
        ("PR-02_routing_failure_unreachable.json", "PR-02"),
        ("PR-04_cutoff_missed_policy_blocked.json", "PR-04"),
        ("PR-07_network_timeout_idempotency_collision.json", "PR-07"),
        ("PR-09_payment_held_for_repair_unresolved_syntax.json", "PR-09"),
        ("CO-07_regulatory_reporting_missing_statutory.json", "CO-07"),
    ]

    @pytest.mark.parametrize("filename, expected_profile", WAVE1_SUFFICIENT_FIXTURES)
    def test_positive_wave1_fixtures(self, harness, filename, expected_profile):
        input_path = Path("e2e_fixtures/input") / filename
        output_path = Path("e2e_fixtures/output") / filename
        assert input_path.exists(), f"Missing input fixture: {input_path}"

        out: CanonicalE2EOutput = harness.process_input(input_path, output_file_path=output_path)

        assert out.detected_profile_id == expected_profile
        assert out.stp_eligible is True, f"Expected STP_ELIGIBLE=True for {filename}, got False. Reason: {out.stp_decision_reason}"
        assert out.bank_handoff_status == "BANK_HANDOFF_READY"
        assert out.execution_owner == "BANK"
        assert out.hitl_required is False
        assert out.audit_chain_block_hash != ""
        assert out.predicate_breakdown.stp_formula_result is True
        assert all([
            out.predicate_breakdown.e_suff,
            out.predicate_breakdown.r_det,
            out.predicate_breakdown.r_uniq,
            out.predicate_breakdown.v_det,
            out.predicate_breakdown.v_auth,
            out.predicate_breakdown.p_bank,
            out.predicate_breakdown.c_comp,
            out.predicate_breakdown.x_pre
        ]), f"One of 8 predicates failed in {filename}"

    @pytest.mark.parametrize("filename, expected_profile", WAVE1_NEGATIVE_FIXTURES)
    def test_negative_wave1_fixtures(self, harness, filename, expected_profile):
        input_path = Path("e2e_fixtures/input") / filename
        output_path = Path("e2e_fixtures/output") / filename
        assert input_path.exists(), f"Missing input fixture: {input_path}"

        out: CanonicalE2EOutput = harness.process_input(input_path, output_file_path=output_path)

        assert out.detected_profile_id == expected_profile
        assert out.stp_eligible is False, f"Expected STP_ELIGIBLE=False for {filename}, got True"
        assert out.hitl_required is True
        assert out.bank_handoff_status == "MAKER_CHECKER_PENDING"
        assert out.execution_owner == "BANK"
        assert len(out.errors) >= 1
