"""Canonical 8-Predicate STP Evaluator for PeX Evidence-Driven STP Architecture.

Evaluates the canonical boolean formula:
STP_ELIGIBLE = E_suff ∧ R_det ∧ R_uniq ∧ V_det ∧ V_auth ∧ P_bank ∧ C_comp ∧ X_pre

AI confidence is explicitly NOT an STP predicate and cannot override any gate.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.services.sufficiency_engine import EvidenceSufficiencyResult, EvidenceSufficiencyStatus
from app.schemas.resolution_contract import (
    ResolutionResult,
    ResolutionStatus,
    ResolutionUniqueness,
)
from app.schemas.authority_contract import (
    AuthorityValidationResult,
    AuthorityValidationStatus,
)
from app.schemas.policy_contract import (
    STPPolicyConfig,
    STPEligibilityDecision,
    ComplianceGateStatus,
    ExecutionPreconditionsStatus,
)


class EvidenceSTPEvaluator:
    """Evaluates Straight-Through Processing (STP) eligibility across all 8 architectural predicates."""

    def evaluate(
        self,
        case_id: str,
        profile_id: str,
        amount: float,
        currency: str,
        sufficiency_result: EvidenceSufficiencyResult,
        resolution_result: ResolutionResult,
        authority_result: AuthorityValidationResult,
        policy_config: Optional[STPPolicyConfig] = None,
        compliance_status: ComplianceGateStatus = ComplianceGateStatus.PASS,
        execution_preconditions_status: ExecutionPreconditionsStatus = ExecutionPreconditionsStatus.PASS,
        ai_confidence_score: Optional[float] = None
    ) -> STPEligibilityDecision:
        """Evaluates all 8 predicates deterministically and computes final STP eligibility."""
        config = policy_config or STPPolicyConfig()
        trail: List[str] = [f"Evaluating 8-predicate STP eligibility for case {case_id} (Profile: {profile_id}, Amount: {amount} {currency})"]
        denial_reasons: List[str] = []

        # 1. E_suff (Evidence Sufficiency)
        e_suff = sufficiency_result.is_sufficient and (sufficiency_result.status == EvidenceSufficiencyStatus.SUFFICIENT)
        if not e_suff:
            trail.append(f"Predicate E_suff: FAILED (Status: {sufficiency_result.status.value})")
        else:
            trail.append("Predicate E_suff: PASSED (All mandatory evidence verified fresh & complete).")

        # 2. R_det (Resolution Determined)
        r_det = (resolution_result.status == ResolutionStatus.RESOLUTION_DETERMINED) and (resolution_result.primary_candidate is not None)
        if not r_det:
            trail.append("Predicate R_det: FAILED (Resolution could not be deterministically determined).")
        else:
            trail.append("Predicate R_det: PASSED (Deterministic candidate resolution derived).")

        # 3. R_uniq (Resolution Uniqueness)
        r_uniq = (resolution_result.uniqueness == ResolutionUniqueness.RESOLUTION_UNIQUE) and (len(resolution_result.candidates) == 1)
        if not r_uniq:
            trail.append(f"Predicate R_uniq: FAILED (Candidate count: {len(resolution_result.candidates)}, Uniqueness: {resolution_result.uniqueness.value}).")
        else:
            trail.append("Predicate R_uniq: PASSED (Candidate resolution is strictly unique).")

        # 4. V_det (Deterministic Validation)
        v_det = resolution_result.is_lossless and (resolution_result.primary_candidate is not None)
        if not v_det:
            trail.append("Predicate V_det: FAILED (Candidate violated lossless integrity or format constraints).")
        else:
            trail.append("Predicate V_det: PASSED (Lossless integrity and deterministic format validated).")

        # 5. V_auth (Authority Validation)
        v_auth = (authority_result.status == AuthorityValidationStatus.PASSED) and authority_result.is_valid
        if not v_auth:
            trail.append(f"Predicate V_auth: FAILED (Authority status: {authority_result.status.value}, Error: {authority_result.error_message}).")
        else:
            trail.append(f"Predicate V_auth: PASSED (Authoritative source '{authority_result.authoritative_source}' confirmed candidate).")

        # 6. P_bank (Bank Policy Allows STP)
        is_under_amount_cap = (amount <= config.max_stp_amount)
        is_corridor_allowed = (currency in config.allowed_corridors)
        is_under_dual_auth = (amount < config.dual_auth_threshold)
        is_auto_stp_enabled = config.auto_stp_enabled

        p_bank = is_under_amount_cap and is_corridor_allowed and is_under_dual_auth and is_auto_stp_enabled
        if not p_bank:
            trail.append(
                f"Predicate P_bank: FAILED (AmountCap: {is_under_amount_cap}, Corridor: {is_corridor_allowed}, DualAuth: {is_under_dual_auth}, AutoSTP: {is_auto_stp_enabled})"
            )
            if not is_under_amount_cap:
                denial_reasons.append(f"Transaction amount {amount} {currency} exceeds Bank STP limit ({config.max_stp_amount} {currency}).")
            if not is_corridor_allowed:
                denial_reasons.append(f"Currency corridor {currency} is not in bank allowed STP corridors.")
            if not is_under_dual_auth:
                denial_reasons.append(f"Transaction amount {amount} {currency} mandates Maker-Checker Dual Authorization.")
        else:
            trail.append(f"Predicate P_bank: PASSED (Amount {amount} <= {config.max_stp_amount} {currency}, Corridor allowed).")

        # 7. C_comp (Compliance Gate Passed)
        c_comp = (compliance_status == ComplianceGateStatus.PASS)
        if not c_comp:
            trail.append(f"Predicate C_comp: FAILED (Compliance status: {compliance_status.value}).")
            denial_reasons.append(f"Compliance screening gate returned {compliance_status.value}.")
        else:
            trail.append("Predicate C_comp: PASSED (Zero sanctions/AML hits; screening cleared).")

        # 8. X_pre (Execution Preconditions Satisfied)
        x_pre = (execution_preconditions_status == ExecutionPreconditionsStatus.PASS)
        if not x_pre:
            trail.append(f"Predicate X_pre: FAILED (Execution preconditions: {execution_preconditions_status.value}).")
            denial_reasons.append("Execution preconditions failed (e.g. Cutoff missed or ledger unreachable).")
        else:
            trail.append("Predicate X_pre: PASSED (RTGS cutoff active, ledger available, idempotency secured).")

        # Note on AI confidence score:
        if ai_confidence_score is not None:
            trail.append(f"Informational: AI Confidence score was {ai_confidence_score:.4f} (NOT evaluated as an eligibility predicate).")

        return STPEligibilityDecision.evaluate(
            case_id=case_id,
            profile_id=profile_id,
            e_suff=e_suff,
            r_det=r_det,
            r_uniq=r_uniq,
            v_det=v_det,
            v_auth=v_auth,
            p_bank=p_bank,
            c_comp=c_comp,
            x_pre=x_pre,
            policy_denial_reasons=denial_reasons,
            ai_confidence=ai_confidence_score,
            audit_trail=trail
        )


# Global singleton STP evaluator
evidence_stp_evaluator = EvidenceSTPEvaluator()
