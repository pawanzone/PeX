"""AI Recommendation & Decision Contract Schemas."""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.canonical import ExceptionSeverity

class ActionType(str, Enum):
    REPAIR_IBAN = "REPAIR_IBAN"
    REPAIR_BIC = "REPAIR_BIC"
    REPAIR_DATA = "REPAIR_DATA"
    REROUTE_CLEARING = "REROUTE_CLEARING"
    RELEASE_COMPLIANCE_CLEARANCE = "RELEASE_COMPLIANCE_CLEARANCE"
    EXECUTE_TREASURY_TRANSFER = "EXECUTE_TREASURY_TRANSFER"
    RETURN_PRINCIPAL_REVERSAL = "RETURN_PRINCIPAL_REVERSAL"
    APPLY_REMITTANCE_OVERRIDE = "APPLY_REMITTANCE_OVERRIDE"
    RETRY_PROCESSING_QUEUE = "RETRY_PROCESSING_QUEUE"
    ROLL_VALUE_DATE = "ROLL_VALUE_DATE"
    ESCALATE = "ESCALATE"
    HOLD = "HOLD"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REQUEST_KYC = "REQUEST_KYC"
    REPAIR_AND_RESUBMIT = "REPAIR_AND_RESUBMIT"
    REPAIR_AND_RELEASE = "REPAIR_AND_RELEASE"
    RETURN_PAYMENT = "RETURN_PAYMENT"
    CLEAR_FALSE_POSITIVE = "CLEAR_FALSE_POSITIVE"
    GRANT_KYC_WAIVER = "GRANT_KYC_WAIVER"
    SUPPRESS_DUPLICATE = "SUPPRESS_DUPLICATE"
    REJECT = "REJECT"

class ProposedFieldChange(BaseModel):
    field_path: str  # e.g. creditor_account.iban
    original_value_masked: str  # e.g. GB82WEST12345698765432
    proposed_value_masked: str  # e.g. GB82WEST12345698765431
    raw_proposed_value: Optional[str] = None # Filled only post-detokenization in vault
    justification: str
    validation_status: str = "VALIDATED"  # MOD-97 check, Directory check

class CorroboratingEvidenceRef(BaseModel):
    evidence_id: str
    evidence_type: str
    citation: str

class RiskEvaluation(BaseModel):
    risk_level: ExceptionSeverity
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_factors: List[str]
    dual_auth_required: bool

class GuidedQuestionItem(BaseModel):
    category: str
    question: str
    investigation_tip: str
    mapped_steps: Optional[str] = "Steps 1 & 2 (Directory & Format Proofs)"

class StepAssessmentItem(BaseModel):
    step_number: int
    step_title: str
    description: str
    proof_detail: str
    badge_label: str = "VALIDATED"
    is_passed: bool = True
    mapped_checkpoint: Optional[str] = "Operator Triage Focus"

class HypothesisRankingItem(BaseModel):
    hypothesis_id: str
    title: str
    confidence: float
    status: str  # SELECTED, ELIMINATED, ELIGIBLE_CANDIDATE
    elimination_reason: Optional[str] = None
    candidate_value: Optional[str] = None
    candidate_description: Optional[str] = None

class AnomalyGuardrailItem(BaseModel):
    guardrail_name: str
    status: str  # PASS, ALERT
    details: str

class ConsequenceSimulation(BaseModel):
    estimated_settlement_velocity: str = "2.1 seconds"
    cutoff_deadline_status: str = "MEETS 16:00 EST CUTOFF"
    fee_penalty_avoidance: str = "$150.00 late inquiry avoided"
    nostro_liquidity_impact: str = "Sufficient Nostro Balance ($14.2M available)"

class DecisionRecommendation(BaseModel):
    recommendation_id: str
    case_id: str
    action_type: ActionType
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    proposed_changes: List[ProposedFieldChange] = []
    corroborating_evidence: List[CorroboratingEvidenceRef] = []
    risk_evaluation: RiskEvaluation
    
    # Rich Guided Intelligence Fields
    guided_questions: List[GuidedQuestionItem] = []
    step_by_step_assessment: List[StepAssessmentItem] = []
    hypothesis_ranking: List[HypothesisRankingItem] = []
    anomaly_guardrails: List[AnomalyGuardrailItem] = []
    consequence_simulation: Optional[ConsequenceSimulation] = None
    applied_policies: List[str] = []
    
    # Boundary Condition: Multi-Candidate Ambiguity & Human Disambiguation
    ambiguity_detected: bool = False
    ambiguity_message: Optional[str] = None
    
    model_identifier: str = "mock-governed-reasoner-v1"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def step_assessment(self) -> List[StepAssessmentItem]:
        return self.step_by_step_assessment
