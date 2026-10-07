"""STP Policy Contract & 8-Predicate Eligibility Schemas for PeX Evidence-Driven STP Architecture.

Enforces bank-defined risk, governance, compliance, and dual-authorization rules governing execution,
strictly executing the canonical 8-predicate boolean formula.
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ComplianceGateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SUSPENDED = "SUSPENDED"


class ExecutionPreconditionsStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class STPPolicyConfig(BaseModel):
    """Bank-configurable risk and execution policy parameters."""
    max_stp_amount: float = 25000.0           # Configurable ceiling (e.g. $25k USD)
    dual_auth_threshold: float = 250000.0     # Amounts >= this threshold mandate Maker-Checker Dual Auth
    allowed_corridors: List[str] = Field(default_factory=lambda: ["USD", "EUR", "GBP", "CHF", "JPY", "SGD", "CAD", "AUD"])
    auto_stp_enabled: bool = True
    sanctions_mode: str = "ZERO_TOLERANCE"    # Configurable compliance policy


class STPEligibilityDecision(BaseModel):
    """Authoritative decision object evaluating the canonical 8-predicate STP formula.
    
    Formula: STP_ELIGIBLE = E_suff ∧ R_det ∧ R_uniq ∧ V_det ∧ V_auth ∧ P_bank ∧ C_comp ∧ X_pre
    """
    case_id: str
    profile_id: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # The 8 Explicit Predicates:
    evidence_sufficient: bool                 # E_suff
    resolution_determined: bool               # R_det
    resolution_unique: bool                   # R_uniq
    deterministic_validation_passed: bool     # V_det
    authority_validation_passed: bool         # V_auth
    bank_policy_allows: bool                  # P_bank
    compliance_gate_passed: bool              # C_comp
    execution_preconditions_satisfied: bool   # X_pre

    # Final Combined Boolean:
    stp_eligible: bool

    # Routing & Governance:
    recommended_routing: str                  # "AUTO_STP_DISPATCH", "MAKER_CHECKER_WORKLIST", "OPERATIONS_SUSPENSE", "INVESTIGATION_DESK"
    policy_denial_reasons: List[str] = Field(default_factory=list)
    audit_trail: List[str] = Field(default_factory=list)

    # Optional informational attributes (Explicitly NOT predicates):
    ai_confidence_score: Optional[float] = None # Informational only; NEVER an eligibility predicate
    historical_match_count: int = 0             # Contextual only

    @classmethod
    def evaluate(
        cls,
        case_id: str,
        profile_id: str,
        e_suff: bool,
        r_det: bool,
        r_uniq: bool,
        v_det: bool,
        v_auth: bool,
        p_bank: bool,
        c_comp: bool,
        x_pre: bool,
        policy_denial_reasons: Optional[List[str]] = None,
        ai_confidence: Optional[float] = None,
        audit_trail: Optional[List[str]] = None
    ) -> "STPEligibilityDecision":
        """Deterministic evaluation of the 8-predicate boolean formula."""
        denial_reasons = policy_denial_reasons or []
        trail = audit_trail or []

        # Canonical Boolean Conjunction:
        is_eligible = (
            e_suff and
            r_det and
            r_uniq and
            v_det and
            v_auth and
            p_bank and
            c_comp and
            x_pre
        )

        if not e_suff:
            denial_reasons.append("Evidence is insufficient or stale (E_suff == False).")
        if not r_det:
            denial_reasons.append("Deterministic resolution could not be derived (R_det == False).")
        if not r_uniq:
            denial_reasons.append("Resolution is ambiguous with multiple candidates (R_uniq == False).")
        if not v_det:
            denial_reasons.append("Deterministic syntax/schema validation failed (V_det == False).")
        if not v_auth:
            denial_reasons.append("Authoritative validation failed or unconfirmed (V_auth == False).")
        if not p_bank:
            denial_reasons.append("Bank risk policy disallows autonomous STP for this transaction (P_bank == False).")
        if not c_comp:
            denial_reasons.append("Compliance screening gate did not return PASS (C_comp == False).")
        if not x_pre:
            denial_reasons.append("Execution preconditions not satisfied (X_pre == False).")

        routing = "AUTO_STP_DISPATCH" if is_eligible else "MAKER_CHECKER_WORKLIST" if (v_auth and not c_comp) else "OPERATIONS_SUSPENSE"

        return cls(
            case_id=case_id,
            profile_id=profile_id,
            evidence_sufficient=e_suff,
            resolution_determined=r_det,
            resolution_unique=r_uniq,
            deterministic_validation_passed=v_det,
            authority_validation_passed=v_auth,
            bank_policy_allows=p_bank,
            compliance_gate_passed=c_comp,
            execution_preconditions_satisfied=x_pre,
            stp_eligible=is_eligible,
            recommended_routing=routing,
            policy_denial_reasons=denial_reasons,
            audit_trail=trail,
            ai_confidence_score=ai_confidence
        )
