"""Schemas and data contracts for Governed Policy Rules & ICD Configurations."""
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field

class RuleCategory(str, Enum):
    APPROVAL_GATING = "APPROVAL_GATING"
    STP_FAST_LANE = "STP_FAST_LANE"
    ROUTING = "ROUTING"
    SLA_URGENCY = "SLA_URGENCY"

class RuleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    DRAFT = "DRAFT"
    REJECTED = "REJECTED"
    RETIRED = "RETIRED"

class RuleClause(BaseModel):
    field: str
    operator: str  # ">=", "<=", ">", "<", "==", "!=", "in", "contains"
    value: Union[float, int, str, List[Union[str, int, float]], bool]

class RuleConditions(BaseModel):
    logic: str = "AND"  # "AND" or "OR"
    clauses: List[RuleClause] = []

class RuleActions(BaseModel):
    set_dual_auth_required: Optional[bool] = None
    required_tiers: Optional[int] = None
    tier_1_role: Optional[str] = None
    tier_2_role: Optional[str] = None
    auto_qualify_fast_lane: Optional[bool] = None
    one_click_eligible: Optional[bool] = None
    target_queue: Optional[str] = None
    override_priority: Optional[str] = None
    notify_parties: Optional[List[str]] = None

class PolicyRule(BaseModel):
    rule_id: str
    name: str
    natural_language_prompt: str
    category: RuleCategory = RuleCategory.APPROVAL_GATING
    domain: str = "ALL"
    conditions: Dict[str, Any] = Field(default_factory=dict)
    actions: Dict[str, Any] = Field(default_factory=dict)
    status: RuleStatus = RuleStatus.ACTIVE
    version: str = "1.0"
    impact_summary: Optional[str] = None
    maker_id: Optional[str] = None
    maker_name: Optional[str] = None
    maker_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    checker_id: Optional[str] = None
    checker_name: Optional[str] = None
    checker_comments: Optional[str] = None
    approved_at: Optional[datetime] = None

class SynthesizeRuleRequest(BaseModel):
    prompt: str
    category: Optional[str] = None
    domain: Optional[str] = None

class SynthesizeRuleResponse(BaseModel):
    rule_id: str
    name: str
    natural_language_prompt: str
    category: str
    domain: str
    conditions: Dict[str, Any]
    actions: Dict[str, Any]
    explanation: str

class SimulateRuleRequest(BaseModel):
    conditions: Dict[str, Any]
    actions: Optional[Dict[str, Any]] = None
    domain: Optional[str] = "ALL"

class MatchedCaseSample(BaseModel):
    case_id: str
    payment_id: str
    amount: float
    currency: str
    profile: str
    domain: str
    reason: str
    queue: str
    confidence: Optional[float] = None

class SimulateRuleResponse(BaseModel):
    total_cases_evaluated: int
    matched_cases_count: int
    match_percentage: float
    total_dollar_volume_affected: float
    matched_by_domain: Dict[str, int]
    matched_by_queue: Dict[str, int]
    sample_matched_cases: List[MatchedCaseSample]
    action_preview: Dict[str, Any]

class SubmitRuleRequest(BaseModel):
    rule_id: Optional[str] = None
    name: str
    natural_language_prompt: str
    category: str = "APPROVAL_GATING"
    domain: str = "ALL"
    conditions: Dict[str, Any]
    actions: Dict[str, Any]
    maker_id: str
    maker_name: str
    maker_notes: Optional[str] = None

class CheckerDecisionRequest(BaseModel):
    checker_id: str
    checker_name: str
    comments: Optional[str] = None

class ICDConfiguration(BaseModel):
    icd_id: str
    name: str
    institution_name: str
    bic: str
    rail: str = "SWIFT_CBPR+"
    adapter_type: str = "DIRECTORY_LOOKUP"
    endpoint_url: str
    latency_ms: int = 12
    status: str = "ACTIVE"
    config_payload: Dict[str, Any] = Field(default_factory=dict)
    maker_id: Optional[str] = None
    maker_name: Optional[str] = None
    maker_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    checker_id: Optional[str] = None
    checker_name: Optional[str] = None
    checker_comments: Optional[str] = None
    approved_at: Optional[datetime] = None

class SubmitICDConfigRequest(BaseModel):
    icd_id: Optional[str] = None
    name: str
    institution_name: str
    bic: str
    rail: str = "SWIFT_CBPR+"
    adapter_type: str = "DIRECTORY_LOOKUP"
    endpoint_url: str
    latency_ms: int = 15
    config_payload: Dict[str, Any] = Field(default_factory=dict)
    maker_id: str
    maker_name: str
    maker_notes: Optional[str] = None
