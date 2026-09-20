"""Tokenized Investigation Context & Evidence Schemas."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.canonical import ExceptionProfile

class EvidenceItem(BaseModel):
    evidence_id: str
    evidence_type: str  # BENEFICIARY_PROFILE, ACCOUNT_DIRECTORY, HISTORICAL_CASE, POLICY_RULE, SCREENING_HIT, KYC_RECORD
    source_connector: str
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    provenance_id: str
    is_mandatory: bool = False
    data: Dict[str, Any]
    relevance_score: float = 1.0

class PolicyRule(BaseModel):
    policy_id: str
    profile: ExceptionProfile
    rule_code: str
    rule_description: str
    mandatory_evidence: List[str]
    auto_repair_eligible: bool
    max_amount_threshold: float
    required_confidence_threshold: float

class HistoricalPrecedent(BaseModel):
    precedent_case_id: str
    profile: ExceptionProfile
    similarity_score: float
    applied_action: str
    outcome: str
    rationale: str

class TokenizedParty(BaseModel):
    token_id: str
    party_role: str
    country: str

class TokenizedAccount(BaseModel):
    token_id: str
    currency: str
    masked_identifier: str
    bank_bic: Optional[str] = None

class TokenizedPaymentContext(BaseModel):
    payment_id: str
    uetr: str
    amount: float
    currency: str
    debtor_party: TokenizedParty
    debtor_account: TokenizedAccount
    creditor_party: TokenizedParty
    creditor_account: TokenizedAccount
    payment_rail: str

class TokenizedInvestigationContext(BaseModel):
    context_id: str
    case_id: str
    profile: ExceptionProfile
    tokenized_payment: TokenizedPaymentContext
    evidence_items: List[EvidenceItem]
    policies: List[PolicyRule]
    historical_cases: List[HistoricalPrecedent]
    screening_matches: List[Dict[str, Any]] = []
    kyc_summary: Optional[Dict[str, Any]] = None
    assembled_at: datetime = Field(default_factory=datetime.utcnow)
    token_usage_estimated: int = 0
