"""Wave 2 Domain Contract Schemas for PeX Industrialization Architecture.

Defines Pydantic data schemas for Wave 2 capability engines:
- SettlementReconciliationEngine (PR-06, ST-02, ST-03)
- AccountMasterEngine Wave 2 Extensions (ST-02, ST-03)
- RoutingClearingEngine Wave 2 Extensions (PR-06)
- ComplianceDossierEngine (ST-03)

Zero vendor SDK dependencies. Provider-neutral, cloud-neutral, model-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timezone
from enum import Enum
from pydantic import BaseModel, Field


# ==============================================================================
# 1. INTERMEDIARY REJECTION & ROUTING SCHEMAS (PR-06 — PAT-F / PAT-A)
# ==============================================================================

class IntermediaryRejectionReasonCode(str, Enum):
    """Canonical/external rejection reason classification."""
    ROUTING_UNREACHABLE = "ROUTING_UNREACHABLE"
    SSI_MISMATCH = "SSI_MISMATCH"
    CUTOFF_EXCEEDED = "CUTOFF_EXCEEDED"
    CORRIDOR_RESTRICTED = "CORRIDOR_RESTRICTED"
    FORMAT_SYNTAX_ERROR = "FORMAT_SYNTAX_ERROR"
    COMPLIANCE_REVIEW_REQUIRED = "COMPLIANCE_REVIEW_REQUIRED"
    BENEFICIARY_BANK_UNREACHABLE = "BENEFICIARY_BANK_UNREACHABLE"
    NARRATIVE_UNMAPPED = "NARRATIVE_UNMAPPED"
    SOCKET_ERROR_TELEMETRY = "SOCKET_ERROR_TELEMETRY"  # Non-authoritative telemetry


class IntermediaryRejectionAdvice(BaseModel):
    """Authoritative structured rejection advice from Correspondent Gateway SPI."""
    rejection_reference: str
    original_uetr: str
    original_payment_id: str
    rejecting_institution_bic: str
    intermediary_role: str = "INTERMEDIARY_AGENT"
    rejection_code: str  # e.g., "AC04", "RC01", "NARR"
    rejection_category: IntermediaryRejectionReasonCode
    narrative_text: Optional[str] = None
    is_telemetry_only: bool = False  # If True, socket error only != sovereign rejection
    rejection_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: Optional[Dict[str, Any]] = None


class AlternateRerouteResult(BaseModel):
    """Outcome of alternate correspondent routing derivation from RoutingClearingEngine."""
    original_intermediary_bic: str
    selected_alternate_bic: str
    alternate_institution_name: str
    clearing_rail: str
    settlement_currency: str
    is_alternate_viable: bool = True
    reachability_confirmed: bool = True
    cutoff_active: bool = True
    routing_authority: str = "CLEARING_DIRECTORY_PORT"
    candidate_hops: List[str] = Field(default_factory=list)


# ==============================================================================
# 2. ACCOUNT CLOSED & ROLLOVER SCHEMAS (ST-02 — PAT-E / PAT-A)
# ==============================================================================

class AccountClosedRecord(BaseModel):
    """Authoritative account closure state affirmation from Core DDA SPI."""
    account_number: str
    account_title: str
    account_status: str = "CLOSED"  # CLOSED / TERMINATED / DORMANT / ACTIVE
    closed_date: Optional[date] = None
    is_closed: bool = True
    currency: str = "USD"
    bank_bic: str = ""
    has_rollover_mandate: bool = False
    rollover_target_account: Optional[str] = None
    verification_authority: str = "CORE_DDA_ACCOUNT_MASTER"
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RolloverMandateRecord(BaseModel):
    """Client corporate mandate record authorizing successor account rollover."""
    mandate_id: str
    debtor_or_creditor_entity_id: str = "CLIENT_ENTITY"
    closed_account_number: str
    successor_account_number: str
    authorized_signatory: str
    mandate_status: str = "ACTIVE"  # ACTIVE / EXPIRED / REVOKED
    signed_date: date
    dual_authorization_verified: bool = True


# ==============================================================================
# 3. BENEFICIARY ACCOUNT FROZEN & LEGAL DOSSIER SCHEMAS (ST-03 — PAT-E / PAT-D)
# ==============================================================================

class AccountRestrictionType(str, Enum):
    """Core banking restriction classification."""
    NO_RESTRICTION = "NO_RESTRICTION"
    DEBIT_ONLY = "DEBIT_ONLY"             # Debits blocked, Credits PERMITTED
    CREDIT_ONLY = "CREDIT_ONLY"           # Credits blocked, Debits PERMITTED
    POST_NO_CREDITS = "POST_NO_CREDITS"   # Credits blocked (PNC)
    TOTAL_FREEZE = "TOTAL_FREEZE"         # Both debits and credits blocked
    ADMINISTRATIVE_HOLD = "ADMINISTRATIVE_HOLD"
    STATUTORY_SANCTIONS_BLOCK = "STATUTORY_SANCTIONS_BLOCK"  # Governed by CO-01


class AccountRestrictionScope(BaseModel):
    """Authoritative restriction scope from Core Account Master / Legal Registry SPI."""
    account_number: str
    account_title: str
    restriction_type: AccountRestrictionType
    is_credit_prohibited: bool = True
    restriction_reference_id: str
    issuing_authority: str  # e.g., "US_DISTRICT_COURT", "IRS", "BANK_RISK_OPS"
    effective_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    statutory_sanctions_hit: bool = False  # If True, must divert to CO-01


class LegalFreezeType(str, Enum):
    """Classification of legal freeze dossier orders."""
    JUDICIAL_GARNISHMENT = "JUDICIAL_GARNISHMENT"
    TAX_LEVY = "TAX_LEVY"
    BANKRUPTCY_STAY = "BANKRUPTCY_STAY"
    COURT_INJUNCTION = "COURT_INJUNCTION"
    ADMINISTRATIVE_RESTRAINT = "ADMINISTRATIVE_RESTRAINT"
    FRAUD_INVESTIGATION_HOLD = "FRAUD_INVESTIGATION_HOLD"
    STATUTORY_ASSET_FREEZE = "STATUTORY_ASSET_FREEZE"


class LegalFreezeDossierRecord(BaseModel):
    """Legal/compliance freeze dossier details from SPI-LEGAL-REGISTRY-PORT."""
    dossier_id: str
    account_number: str
    case_caption: str
    court_or_agency_name: str
    docket_number: str
    freeze_type: LegalFreezeType
    freeze_scope: str = "POST_NO_CREDITS"
    is_conflicting_order: bool = False
    permitted_disposition: str = "RETURN_TO_ORDERING_INSTITUTION"  # RETURN / LEGAL_SUSPENSE_ESCROW / STATUTORY_BLOCK
    compliance_officer_signoff: bool = True
    dossier_status: str = "ACTIVE"
    issued_date: date = Field(default_factory=lambda: datetime.now(timezone.utc).date())


# ==============================================================================
# 4. SETTLEMENT RECONCILIATION SCHEMAS (PR-06, ST-02, ST-03 — PAT-E / PAT-F)
# ==============================================================================

class DeterministicCorrelationMatch(BaseModel):
    """Deterministic correlation linking exception notice to original payment keys."""
    original_uetr: str
    original_payment_id: str
    settlement_amount: float
    currency: str
    debtor_agent_bic: str
    creditor_agent_bic: str
    correlation_confidence: float = 1.0  # Deterministic = 1.0
    is_unambiguous_match: bool = True
    match_keys_used: List[str] = Field(default_factory=lambda: ["uetr", "amount", "currency", "creditor_bic"])


class SettlementReturnPackage(BaseModel):
    """Compliant return package for ledger re-credit / interbank return dispatch."""
    return_id: str
    original_uetr: str
    original_payment_id: str
    return_amount: float
    currency: str
    return_reason_code: str  # e.g., "AC04" (Closed), "PNC" / "FR01" (Frozen), "RC01" (Reroute fail)
    return_reason_narrative: str
    debtor_recredit_account: Optional[str] = None
    creditor_nostro_account: Optional[str] = None
    target_clearing_rail: str
    return_mechanism: str = "GENERIC_RETURN_DISPATCH"  # e.g., pacs.004 / FedLine Return
    is_fully_balanced: bool = True
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SettlementSuspenseBreakRecord(BaseModel):
    """Balanced double-entry journal package for bank legal suspense / escrow booking."""
    break_id: str
    uetr: str
    amount: float
    currency: str
    suspense_gl_account: str = "GL-2180-LEGAL-SUSPENSE-ESCROW"
    clearing_nostro_account: str = "GL-1010-FEDWIRE-NOSTRO"
    journal_debit_entry: Dict[str, Any]
    journal_credit_entry: Dict[str, Any]
    is_balanced: bool = True
    escrow_reference_case: str
    booked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
