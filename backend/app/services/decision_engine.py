"""Decision Engine: Evaluates AI recommendations against institutional governance policies derived from SME skills."""
from typing import Dict, Any, Tuple
from app.schemas.recommendation import DecisionRecommendation, ActionType
from app.schemas.canonical import ExceptionProfile
from app.services.skill_policy_service import skill_policy_service

class DecisionEngine:
    def evaluate_governance_gate(
        self,
        recommendation: DecisionRecommendation,
        profile: ExceptionProfile,
        amount: float
    ) -> Tuple[bool, str]:
        # Dynamically retrieve parameters from active SME skill markdown playbooks
        params = skill_policy_service.get_policy_parameters()
        confidence_threshold = params.get("confidence_threshold", 0.85)
        dual_auth_threshold = params.get("dual_auth_threshold", 250000.0)

        if recommendation.action_type in [ActionType.REPAIR_IBAN, ActionType.REPAIR_BIC, ActionType.REPAIR_AND_RESUBMIT]:
            if recommendation.confidence_score < confidence_threshold:
                return False, f"Confidence score ({recommendation.confidence_score:.2f}) below SME skill threshold ({confidence_threshold:.2f}). Action routed for manual investigation."
            
            if amount >= dual_auth_threshold:
                return True, f"Passed to Human-in-the-Loop Dual-Authorization Queue (Amount >= ${dual_auth_threshold:,.0f})."
            
            return True, "Passed to Human-in-the-Loop Approval Queue."

        if recommendation.action_type == ActionType.ESCALATE:
            return True, "Escalation confirmed. Routed to Senior Tier 2 Operations Queue per SME runbook."

        if recommendation.action_type == ActionType.INSUFFICIENT_EVIDENCE:
            return True, "Safe Non-Action enforced. Case held pending missing evidence retrieval per SME SOP."

        return True, "Passed"

decision_engine = DecisionEngine()

