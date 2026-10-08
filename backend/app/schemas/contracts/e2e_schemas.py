"""Canonical E2E JSON Foundation Schemas.

Defines the universal input and output JSON structure for driving PeX end-to-end.
Supports all 41 BIAN exception profiles across the 5 domains.
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class E2EProvenance(str, Enum):
    SYNTHETIC_TEST_FIXTURE = "SYNTHETIC_TEST_FIXTURE"
    REPLAY_RECORDING = "REPLAY_RECORDING"
    SIMULATED_CORE_BANKING = "SIMULATED_CORE_BANKING"
    NON_PRODUCTION_DEMO = "NON_PRODUCTION_DEMO"


class E2EPaymentInfo(BaseModel):
    """Core transactional payment information."""
    payment_id: str
    uetr: str
    amount: float
    currency: str
    clearing_rail: str                               # "FEDWIRE", "CHAPS", "TARGET2", "SWIFT_CBPR+", "BACS"
    value_date: Optional[str] = None
    debtor_name: Optional[str] = None
    debtor_account: Optional[str] = None
    debtor_agent_bic: Optional[str] = None
    creditor_name: Optional[str] = None
    creditor_account: Optional[str] = None
    creditor_agent_bic: Optional[str] = None
    remittance_info: Optional[str] = None
    charge_bearer: Optional[str] = None


class CanonicalE2EInput(BaseModel):
    """Universal Canonical Input Schema for Drop-in JSON Payment Exception Processing."""
    exception_id: str
    profile_id: Optional[str] = None                 # Known or suspected profile (e.g. "DQ-01", "PR-08")
    domain: Optional[str] = None                     # "DATA_QUALITY", "PROCESSING", "COMPLIANCE", "CLIENT_TREASURY", "SETTLEMENT_RETURNS"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    payment_info: E2EPaymentInfo
    raw_payload: Optional[Dict[str, Any]] = None
    
    # Evidence feeds
    bank_supplied_evidence: Dict[str, Any] = Field(default_factory=dict)
    external_authoritative_evidence: Dict[str, Any] = Field(default_factory=dict)
    derived_evidence: Dict[str, Any] = Field(default_factory=dict)
    historical_evidence: Dict[str, Any] = Field(default_factory=dict) # Tier 4 context only (0% authority)
    
    # Policy / configuration overrides
    bank_policy_overrides: Optional[Dict[str, Any]] = None
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Provenance
    evidence_provenance: E2EProvenance = E2EProvenance.SYNTHETIC_TEST_FIXTURE
    test_status: str = "TEST_ONLY"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PredicateBreakdown(BaseModel):
    """Explicit breakdown of the canonical 8-predicate formula."""
    e_suff: bool = False                             # Evidence Sufficient
    r_det: bool = False                              # Resolution Deterministic
    r_uniq: bool = False                             # Resolution Unique (unambiguous)
    v_det: bool = False                              # Deterministic Syntax Validation Passed
    v_auth: bool = False                             # Authoritative Source Validated
    p_bank: bool = False                             # Bank Policy Allows
    c_comp: bool = False                             # Compliance Gate Passed
    x_pre: bool = False                              # Preconditions Satisfied
    stp_formula_result: bool = False                 # Logical conjunction of all 8


class CanonicalE2EOutput(BaseModel):
    """Universal Canonical Output Schema produced by PeX Resolution Processing."""
    exception_id: str
    detected_profile_id: str
    domain: str
    
    # Evidence Evaluation
    evidence_status: str                             # "SUFFICIENT", "INSUFFICIENT", "CONTRADICTORY", "STALE"
    evidence_used: List[str] = Field(default_factory=list)
    evidence_missing: List[str] = Field(default_factory=list)
    evidence_contradictions: List[str] = Field(default_factory=list)
    
    # Resolution Decision
    resolution_status: str                           # "RESOLVED", "SUSPENDED", "REJECTED", "INVESTIGATION_REQUIRED"
    resolution_recommendation: Optional[Dict[str, Any]] = None
    resolution_basis: str
    repaired_fields: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Authority & Policy Status
    authority_status: str                            # "AUTHORITATIVE_CONFIRMED", "UNAVAILABLE", "UNCONFIRMED"
    bank_policy_status: str                          # "POLICY_PERMITTED", "POLICY_BLOCKED", "THRESHOLD_BREACH"
    compliance_status: str                           # "COMPLIANCE_CLEARED", "SANCTIONS_HOLD", "AML_SUSPENDED"
    
    # STP Formula Evaluation
    stp_eligible: bool = False
    stp_decision_reason: str
    predicate_breakdown: PredicateBreakdown = Field(default_factory=PredicateBreakdown)
    ai_confidence_score: Optional[float] = None      # Advisory only (0% weight)
    
    # HITL & Approval Governance
    hitl_required: bool = True
    approval_requirement: str                        # "NONE_AUTONOMOUS_STP", "MAKER_CHECKER_DUAL_AUTH", "COMPLIANCE_OFFICER_SIGN_OFF"
    next_action: str                                 # "DISPATCH_TO_BANK_GATEWAY", "ROUTE_TO_OPERATIONS_WORKLIST", "ROUTE_TO_COMPLIANCE_DESK"
    
    # Bank Execution Handoff
    bank_handoff_status: str                         # "BANK_HANDOFF_READY", "HELD_FOR_MAKER_CHECKER", "SUSPENDED_INVESTIGATION"
    execution_owner: str = "BANK"                    # Universal invariant: execution_owner is ALWAYS "BANK"
    
    # Cryptographic Provenance & Audit
    audit_event_id: str
    audit_chain_block_hash: str
    processing_latency_ms: float = 0.0
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Warnings / Errors
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
