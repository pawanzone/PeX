"""End-to-End Execution Tests for Wave 2 Scenarios.

Executes all 6 Wave 2 Canonical JSON Fixtures (Positive & Negative paths for all 3 profiles):
- Scenario 28: PR-06 Intermediary Bank Rejection (Scenario 28A: Sufficient Reroute vs Scenario 28B: Unverified Telemetry)
- Scenario 29: ST-02 Account Closed (Scenario 29A: Sufficient Return vs Scenario 29B: Contradictory Status)
- Scenario 30: ST-03 Beneficiary Account Frozen (Scenario 30A: Sufficient Return vs Scenario 30B: Conflicting Order)

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


class TestWave2E2EScenarios:
    """Canonical E2E JSON execution tests for Wave 2 Scenarios 28–30 (6 positive and negative fixtures).

    Lineage:
    - Scenarios 1–12: Wave 0A Canonical Baseline (tests/contracts/test_e2e_json_execution.py)
    - Scenarios 13–18: Wave 0B Dynamic Engine & Governance (tests/wave0b/test_e2e_dynamic_execution.py)
    - Scenarios 19–27: Wave 1 Industrialization Profiles (tests/wave1/test_wave1_e2e_scenarios.py)
    - Scenarios 28–30: Wave 2 Industrialization Profiles (tests/wave2/test_wave2_e2e_scenarios.py)
    """

    WAVE2_SUFFICIENT_SCENARIOS = [
        ("Scenario 28A: PR-06 Intermediary Bank Rejection [STP Reroute Path]", "PR-06_intermediary_bank_rejection_sufficient.json", "PR-06"),
        ("Scenario 29A: ST-02 Account Closed [STP Governed Return Path]", "ST-02_account_closed_sufficient.json", "ST-02"),
        ("Scenario 30A: ST-03 Beneficiary Account Frozen [STP Governed Return Path]", "ST-03_account_frozen_sufficient.json", "ST-03"),
    ]

    WAVE2_NEGATIVE_SCENARIOS = [
        ("Scenario 28B: PR-06 Unverified Telemetry [Fail-Closed / HITL]", "PR-06_intermediary_bank_rejection_unverified_telemetry.json", "PR-06"),
        ("Scenario 29B: ST-02 Contradictory Account Status [Fail-Closed / HITL]", "ST-02_account_closed_contradictory.json", "ST-02"),
        ("Scenario 30B: ST-03 Conflicting Judicial Orders [Fail-Closed / Compliance Hold]", "ST-03_account_frozen_conflicting_order.json", "ST-03"),
    ]

    @pytest.mark.parametrize("scenario_title, filename, expected_profile", WAVE2_SUFFICIENT_SCENARIOS)
    def test_positive_wave2_fixtures(self, harness, scenario_title, filename, expected_profile):
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

    @pytest.mark.parametrize("scenario_title, filename, expected_profile", WAVE2_NEGATIVE_SCENARIOS)
    def test_negative_wave2_fixtures(self, harness, scenario_title, filename, expected_profile):
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
