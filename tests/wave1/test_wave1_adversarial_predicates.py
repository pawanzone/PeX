"""Adversarial 8-Predicate Conjunction Tests for Wave 1 Profiles.

Verifies the immutable 8-predicate formula:
STP_ELIGIBLE = E_suff ∧ R_det ∧ R_uniq ∧ V_det ∧ V_auth ∧ P_bank ∧ C_comp ∧ X_pre

Asserts that if ANY single predicate evaluates to FALSE while all other 7 are TRUE,
STP_ELIGIBLE MUST evaluate strictly to FALSE.
"""
import pytest
from app.services.stp_engine import STPEngine
from app.schemas.policy_contract import STPEligibilityDecision

WAVE1_PROFILES = [
    "DQ-03",
    "DQ-04",
    "DQ-07",
    "DQ-09",
    "PR-02",
    "PR-04",
    "PR-07",
    "PR-09",
    "CO-07"
]

PREDICATES = [
    "e_suff",
    "r_det",
    "r_uniq",
    "v_det",
    "v_auth",
    "p_bank",
    "c_comp",
    "x_pre"
]


class TestWave1AdversarialPredicates:
    """Rigorous failure matrix testing across all 8 predicates for all 9 Wave 1 profiles."""

    @pytest.mark.parametrize("profile", WAVE1_PROFILES)
    @pytest.mark.parametrize("failing_predicate", PREDICATES)
    def test_single_predicate_failure_forces_stp_ineligible(self, profile, failing_predicate):
        engine = STPEngine()
        kwargs = {p: True for p in PREDICATES}
        kwargs[failing_predicate] = False

        decision: STPEligibilityDecision = engine.evaluate_canonical_8_predicates(
            case_id=f"EX-ADV-{profile}-{failing_predicate}",
            profile_id=profile,
            **kwargs,
            ai_confidence=0.99 # AI confidence must have 0% bypass authority
        )

        assert decision.stp_eligible is False, f"Formula breached: {profile} evaluated to STP_ELIGIBLE=True with {failing_predicate}=False"
        assert len(decision.policy_denial_reasons) >= 1
        assert any(failing_predicate.upper() in r.upper() for r in decision.policy_denial_reasons)

    @pytest.mark.parametrize("profile", WAVE1_PROFILES)
    def test_all_8_predicates_true_yields_stp_eligible(self, profile):
        engine = STPEngine()
        kwargs = {p: True for p in PREDICATES}

        decision: STPEligibilityDecision = engine.evaluate_canonical_8_predicates(
            case_id=f"EX-POS-{profile}",
            profile_id=profile,
            **kwargs,
            ai_confidence=0.50
        )

        assert decision.stp_eligible is True
        assert len(decision.policy_denial_reasons) == 0
