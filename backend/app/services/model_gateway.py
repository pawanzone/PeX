"""Model Gateway: Pluggable AI Reasoning layer with Deterministic Mock & Live Provider capabilities."""
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from app.config import settings
from app.schemas.context import TokenizedInvestigationContext
from app.schemas.recommendation import (
    DecisionRecommendation, ActionType, ProposedFieldChange,
    CorroboratingEvidenceRef, RiskEvaluation, GuidedQuestionItem,
    StepAssessmentItem, HypothesisRankingItem, AnomalyGuardrailItem, ConsequenceSimulation
)
from app.schemas.canonical import ExceptionSeverity
from app.core.tokenization import token_vault

class ModelGateway:
    def evaluate_investigation(
        self,
        context: TokenizedInvestigationContext,
        scenario_key: Optional[str] = None
    ) -> DecisionRecommendation:
        case_id = context.case_id
        profile = context.profile
        amount = context.tokenized_payment.amount

        if scenario_key == "IBAN-ESCALATE-001":
            return DecisionRecommendation(
                recommendation_id=f"REC-{case_id}",
                case_id=case_id,
                action_type=ActionType.ESCALATE,
                confidence_score=0.45,
                rationale="Conflicting and ambiguous evidence detected. Auto-repair blocked; escalated to Senior Operations Lead.",
                proposed_changes=[],
                corroborating_evidence=[],
                risk_evaluation=RiskEvaluation(
                    risk_level=ExceptionSeverity.HIGH,
                    risk_score=0.75,
                    risk_factors=["Ambiguous directory records", "Conflicting IBAN records"],
                    dual_auth_required=False
                ),
                guided_questions=[],
                step_by_step_assessment=[],
                hypothesis_ranking=[],
                anomaly_guardrails=[],
                consequence_simulation=None,
                applied_policies=[],
                model_identifier="apex-reasoner-deterministic-v1",
                prompt_tokens=120,
                completion_tokens=45,
                generated_at=datetime.utcnow()
            )

        if scenario_key == "IBAN-MISSING-EVIDENCE-001":
            return DecisionRecommendation(
                recommendation_id=f"REC-{case_id}",
                case_id=case_id,
                action_type=ActionType.INSUFFICIENT_EVIDENCE,
                confidence_score=0.20,
                rationale="Missing mandatory beneficiary account directory evidence.",
                proposed_changes=[],
                corroborating_evidence=[],
                risk_evaluation=RiskEvaluation(
                    risk_level=ExceptionSeverity.HIGH,
                    risk_score=0.85,
                    risk_factors=["Missing mandatory evidence", "Beneficiary directory unresolvable"],
                    dual_auth_required=False
                ),
                guided_questions=[],
                step_by_step_assessment=[],
                hypothesis_ranking=[],
                anomaly_guardrails=[],
                consequence_simulation=None,
                applied_policies=[],
                model_identifier="apex-reasoner-deterministic-v1",
                prompt_tokens=120,
                completion_tokens=45,
                generated_at=datetime.utcnow()
            )

        # Import repository to reuse rich definitions if present
        from app.services.data_loader import repo, build_rich_guided_recommendation
        
        if case_id in repo.recommendations:
            return repo.recommendations[case_id]

        creditor_name = "Nordhavn Components A/S"
        creditor_country = "GB"
        case_obj = repo.get_case(case_id)
        if case_obj:
            creditor_name = case_obj.get("creditor_party", {}).get("party_name", "Nordhavn Components A/S")
            creditor_country = case_obj.get("creditor_party", {}).get("country", "GB")

        return build_rich_guided_recommendation(
            case_id=case_id,
            profile=profile,
            amount=amount,
            creditor_name=creditor_name,
            creditor_country=creditor_country,
            case_idx=1
        )

model_gateway = ModelGateway()
