"""Wave 1 Domain Contract Schemas for PeX Industrialization Architecture.

Defines Pydantic data schemas for Wave 1 capability engines:
- AccountMasterEngine (DQ-03, DQ-07, DQ-09, PR-09)
- RoutingClearingEngine (PR-02, PR-04, PR-07, PR-09)
- RemittanceDocumentEngine (DQ-04, CO-07, DQ-03)

Zero vendor SDK dependencies. Provider-neutral, cloud-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timezone
from enum import Enum
from pydantic import BaseModel, Field


# ==============================================================================
# 1. ACCOUNT MASTER & VERIFICATION OF PAYEE SCHEMAS (DQ-03, DQ-07, DQ-09)
# ==============================================================================

class PayeeMatchStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    CLOSE_MATCH = "CLOSE_MATCH"
    NO_MATCH = "NO_MATCH"
    ACCOUNT_NOT_FOUND = "ACCOUNT_NOT_FOUND"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class AccountMasterRecord(BaseModel):
    """Authoritative Core DDA / Account Master entity record."""
    account_number: str
    account_title: str
    account_status: str = "ACTIVE"
    currency: str = "USD"
    bank_id_or_bic: str = ""
    country: str = "US"
    entity_legal_name: Optional[str] = None
    postal_address: Optional[Dict[str, str]] = None
    tax_identifier: Optional[str] = None
    is_frozen: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BeneficiaryProfileRecord(BaseModel):
    """Client Master / Standing Settlement beneficiary directory record."""
    debtor_id: str
    creditor_id: str
    creditor_name: str
    creditor_account: str
    creditor_agent_bic: str
    postal_address: Dict[str, str] = Field(default_factory=dict)
    tax_identifier: Optional[str] = None
    verified_status: str = "VERIFIED"
    effective_date: Optional[str] = None


class PayeeVerificationResult(BaseModel):
    """Outcome of Verification of Payee (VoP) / Confirmation of Payee (CoP) lookup."""
    account_number: str
    queried_name: str
    authoritative_name: str
    match_status: PayeeMatchStatus
    match_score: float = Field(ge=0.0, le=1.0)
    matched_entity_id: Optional[str] = None
    reason: str = ""
    verification_authority: str = "CORE_DDA_MASTER"
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==============================================================================
# 2. ROUTING & CLEARING SCHEMAS (PR-02, PR-04, PR-07, PR-09)
# ==============================================================================

class RouteResolutionRecord(BaseModel):
    """Authoritative routing path and clearing instructions."""
    debtor_agent_bic: str
    creditor_agent_bic: str
    clearing_rail: str
    currency: str
    intermediary_agent_bic: Optional[str] = None
    clearing_system_member_id: Optional[str] = None
    is_reachable: bool = True
    reachability_status: str = "REACHABLE"
    routing_authority: str = "SWIFT_REF_FEDLINE_DIRECTORY"


class SSIRecord(BaseModel):
    """Standard Settlement Instructions (SSI) authoritative record."""
    counterparty_bic: str
    currency: str
    clearing_rail: str
    settlement_account: str
    intermediary_bic: Optional[str] = None
    effective_from: Optional[str] = None
    is_active: bool = True


class RailCutoffInfo(BaseModel):
    """Rail operating calendar and cutoff specifications."""
    rail_code: str
    currency: str
    operating_start_utc: str = "00:00"
    cutoff_utc: str = "22:00"
    is_open_today: bool = True
    next_operating_date: date = Field(default_factory=lambda: datetime.now(timezone.utc).date())
    timezone_name: str = "UTC"


class GatewayProbeResult(BaseModel):
    """Gateway socket probe and network transmission health state."""
    gateway_id: str
    rail_code: str
    socket_status: str = "HEALTHY"  # HEALTHY / TIMEOUT_RECOVERED / UNREACHABLE / DEADLOCKED
    is_socket_connected: bool = True
    latency_ms: float = 0.0
    last_heartbeat_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TransmissionStateResult(BaseModel):
    """Network transmission and settlement state for a specific payment."""
    payment_uetr: str
    transmission_status: str = "TIMED_OUT"  # TIMED_OUT / ACK_RECEIVED / NACK_RECEIVED / SETTLED / UNKNOWN
    is_execution_settled: bool = False
    can_safely_retry: bool = True
    gateway_reference_id: Optional[str] = None


class RetryBudgetResult(BaseModel):
    """Retry budget and rate control record."""
    payment_id: str
    max_retries: int = 3
    retries_exhausted: int = 0
    can_retry: bool = True
    cooldown_seconds: int = 30


class PaymentHubRepairRecord(BaseModel):
    """Payment hub repair queue status and pending repair item."""
    payment_id: str
    uetr: str
    current_queue_status: str = "HELD_IN_REPAIR"  # HELD_IN_REPAIR / RELEASE_ELIGIBLE / SYNTAX_CORRUPTED
    syntax_error_code: Optional[str] = None
    syntax_error_tag: Optional[str] = None
    repair_instruction: Optional[str] = None
    lock_owner: Optional[str] = None


class RepairValidationResult(BaseModel):
    """Validation result for proposed repair fix."""
    payment_id: str
    is_valid_repair: bool
    repaired_xml_or_json: Optional[str] = None
    validation_errors: List[str] = Field(default_factory=list)


# ==============================================================================
# 3. REMITTANCE & REGULATORY SCHEMAS (DQ-04, CO-07)
# ==============================================================================

class StructuredRemittanceRecord(BaseModel):
    """Structured Remittance Information (<Strd>) derived from invoice/ERP."""
    referred_document_number: str
    referred_document_date: Optional[str] = None
    referred_document_amount: Optional[float] = None
    referred_document_currency: Optional[str] = None
    debtor_reference: Optional[str] = None
    creditor_reference: Optional[str] = None
    remittance_narrative: Optional[str] = None
    document_type_code: str = "CINV"  # Commercial Invoice


class InvoiceDocumentRecord(BaseModel):
    """Authoritative commercial invoice / ERP document."""
    invoice_id: str
    debtor_tax_id: Optional[str] = None
    creditor_tax_id: Optional[str] = None
    invoice_date: str
    total_amount: float
    currency: str
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    structured_remittance: Optional[StructuredRemittanceRecord] = None
    raw_document_text: Optional[str] = None


class RemittanceParseResult(BaseModel):
    """Outcome of parsing unstructured or semi-structured remittance text."""
    success: bool
    extracted_invoice_id: Optional[str] = None
    extracted_amount: Optional[float] = None
    structured_remittance: Optional[StructuredRemittanceRecord] = None
    parsing_notes: List[str] = Field(default_factory=list)


class BoPReportingCodeRecord(BaseModel):
    """Balance of Payments (BoP) and statutory reporting code definition."""
    bop_code: str
    description: str
    category: str
    reporting_authority: str = "CENTRAL_BANK"
    corridor_applicability: List[str] = Field(default_factory=lambda: ["ALL"])
    threshold_amount: float = 0.0


class RegulatoryPurposeRule(BaseModel):
    """Regulatory purpose code derivation rule."""
    destination_country: str
    currency: str
    mandatory_purpose_code: str
    regulatory_statute: str
    authority_name: str
    details_description: str


class RegulatoryReportingDerivationResult(BaseModel):
    """Outcome of deriving statutory regulatory reporting tags (CO-07)."""
    success: bool
    authority_code: str = ""
    reporting_code: str = ""
    details_text: str = ""
    statute_reference: str = ""
    derivation_method: str = "DETERMINISTIC_REGULATORY_PURPOSE_DIRECTORY"
    is_mandatory: bool = True
