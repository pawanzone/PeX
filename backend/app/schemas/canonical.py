"""Canonical ISO 20022 / SWIFT / BIAN Data Models for PeX across all 5 Market Domains."""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class LifecycleStage(str, Enum):
    INGESTED = "INGESTED"
    CANONICALIZED = "CANONICALIZED"
    VALIDATED = "VALIDATED"
    INVESTIGATING = "INVESTIGATING"
    RECOMMENDED = "RECOMMENDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    AWAITING_SECOND_APPROVAL = "AWAITING_SECOND_APPROVAL"
    RETURNED_FOR_REWORK = "RETURNED_FOR_REWORK"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    HANDED_TO_BANK = "DISPATCHED"
    DISPATCHED = "DISPATCHED"
    EXECUTED_CONFIRMED = "EXECUTED_CONFIRMED"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    STATUS_UNKNOWN = "STATUS_UNKNOWN"
    SHADOW_RECORDED = "SHADOW_RECORDED"

class ExceptionDomain(str, Enum):
    DATA_QUALITY = "DATA_QUALITY"
    PROCESSING = "PROCESSING"
    COMPLIANCE = "COMPLIANCE"
    CLIENT_TREASURY = "CLIENT_TREASURY"
    SETTLEMENT_RETURNS = "SETTLEMENT_RETURNS"

class ExceptionProfile(str, Enum):
    # Domain 1: Data Quality (9 Profiles)
    INVALID_IBAN = "INVALID_IBAN"
    INVALID_BIC = "INVALID_BIC"
    MISSING_BENEFICIARY_DATA = "MISSING_BENEFICIARY_DATA"
    MISSING_REMITTANCE_INFO = "MISSING_REMITTANCE_INFO"
    INVALID_ADDRESS_FORMAT = "INVALID_ADDRESS_FORMAT"
    MISSING_PURPOSE_CODE = "MISSING_PURPOSE_CODE"
    INVALID_ACCOUNT_NUMBER = "INVALID_ACCOUNT_NUMBER"
    INVALID_ROUTING_CODE = "INVALID_ROUTING_CODE"
    BENEFICIARY_NAME_MISMATCH = "BENEFICIARY_NAME_MISMATCH"

    # Domain 2: Processing (9 Profiles)
    DUPLICATE_PAYMENT = "DUPLICATE_PAYMENT"
    ROUTING_FAILURE = "ROUTING_FAILURE"
    ISO20022_VALIDATION_ERROR = "ISO20022_VALIDATION_ERROR"
    CUTOFF_MISSED = "CUTOFF_MISSED"
    CORRUPTED_MESSAGE_FORMAT = "CORRUPTED_MESSAGE_FORMAT"
    INTERMEDIARY_BANK_REJECTION = "INTERMEDIARY_BANK_REJECTION"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    QUEUE_PROCESSING_FAILURE = "QUEUE_PROCESSING_FAILURE"
    PAYMENT_HELD_FOR_REPAIR = "PAYMENT_HELD_FOR_REPAIR"

    # Domain 3: Compliance (8 Profiles)
    SANCTIONS_SUSPECTED = "SANCTIONS_SUSPECTED"
    AML_ALERT = "AML_ALERT"
    PEP_MATCH = "PEP_MATCH"
    RESTRICTED_CORRIDOR = "RESTRICTED_CORRIDOR"
    ADVERSE_MEDIA_MATCH = "ADVERSE_MEDIA_MATCH"
    HIGH_RISK_JURISDICTION = "HIGH_RISK_JURISDICTION"
    REGULATORY_REPORTING_REQUIRED = "REGULATORY_REPORTING_REQUIRED"
    CUSTOMER_WATCHLIST_MATCH = "CUSTOMER_WATCHLIST_MATCH"

    # Domain 4: Client / Treasury (8 Profiles)
    KYC_EXPIRED = "KYC_EXPIRED"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    NOSTRO_SHORTFALL = "NOSTRO_SHORTFALL"
    FX_RATE_UNAVAILABLE = "FX_RATE_UNAVAILABLE"
    AUTHORIZATION_MISSING = "AUTHORIZATION_MISSING"
    LIMIT_BREACH = "LIMIT_BREACH"
    LIQUIDITY_CONSTRAINT = "LIQUIDITY_CONSTRAINT"
    CREDIT_EXPOSURE_BREACH = "CREDIT_EXPOSURE_BREACH"

    # Domain 5: Settlement / Returns (7 Profiles)
    RETURNED_PAYMENT = "RETURNED_PAYMENT"
    ACCOUNT_CLOSED = "ACCOUNT_CLOSED"
    BENEFICIARY_ACCOUNT_FROZEN = "BENEFICIARY_ACCOUNT_FROZEN"
    RECONCILIATION_BREAK = "RECONCILIATION_BREAK"
    SETTLEMENT_FAILURE = "SETTLEMENT_FAILURE"
    FUNDS_TRAPPED_AT_CORRESPONDENT = "FUNDS_TRAPPED_AT_CORRESPONDENT"
    UNMATCHED_CREDIT = "UNMATCHED_CREDIT"

    # Fallback
    GENERAL_EXCEPTION = "GENERAL_EXCEPTION"

def get_domain_for_profile(profile: ExceptionProfile) -> ExceptionDomain:
    data_quality_profiles = {
        ExceptionProfile.INVALID_IBAN, ExceptionProfile.INVALID_BIC,
        ExceptionProfile.MISSING_BENEFICIARY_DATA, ExceptionProfile.MISSING_REMITTANCE_INFO,
        ExceptionProfile.INVALID_ADDRESS_FORMAT, ExceptionProfile.MISSING_PURPOSE_CODE,
        ExceptionProfile.INVALID_ACCOUNT_NUMBER, ExceptionProfile.INVALID_ROUTING_CODE,
        ExceptionProfile.BENEFICIARY_NAME_MISMATCH
    }
    processing_profiles = {
        ExceptionProfile.DUPLICATE_PAYMENT, ExceptionProfile.ROUTING_FAILURE,
        ExceptionProfile.ISO20022_VALIDATION_ERROR, ExceptionProfile.CUTOFF_MISSED,
        ExceptionProfile.CORRUPTED_MESSAGE_FORMAT, ExceptionProfile.INTERMEDIARY_BANK_REJECTION,
        ExceptionProfile.NETWORK_TIMEOUT, ExceptionProfile.QUEUE_PROCESSING_FAILURE,
        ExceptionProfile.PAYMENT_HELD_FOR_REPAIR
    }
    compliance_profiles = {
        ExceptionProfile.SANCTIONS_SUSPECTED, ExceptionProfile.AML_ALERT,
        ExceptionProfile.PEP_MATCH, ExceptionProfile.RESTRICTED_CORRIDOR,
        ExceptionProfile.ADVERSE_MEDIA_MATCH, ExceptionProfile.HIGH_RISK_JURISDICTION,
        ExceptionProfile.REGULATORY_REPORTING_REQUIRED, ExceptionProfile.CUSTOMER_WATCHLIST_MATCH
    }
    treasury_profiles = {
        ExceptionProfile.KYC_EXPIRED, ExceptionProfile.INSUFFICIENT_FUNDS,
        ExceptionProfile.NOSTRO_SHORTFALL, ExceptionProfile.FX_RATE_UNAVAILABLE,
        ExceptionProfile.AUTHORIZATION_MISSING, ExceptionProfile.LIMIT_BREACH,
        ExceptionProfile.LIQUIDITY_CONSTRAINT, ExceptionProfile.CREDIT_EXPOSURE_BREACH
    }
    
    if profile in data_quality_profiles:
        return ExceptionDomain.DATA_QUALITY
    if profile in processing_profiles:
        return ExceptionDomain.PROCESSING
    if profile in compliance_profiles:
        return ExceptionDomain.COMPLIANCE
    if profile in treasury_profiles:
        return ExceptionDomain.CLIENT_TREASURY
    return ExceptionDomain.SETTLEMENT_RETURNS

class ExceptionSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ExceptionPriority(str, Enum):
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class CanonicalPostalAddress(BaseModel):
    """ISO 20022 PostalAddress: structured fields, or free address lines when the sender did not structure it."""
    street: Optional[str] = None
    building: Optional[str] = None
    post_code: Optional[str] = None
    town: Optional[str] = None
    country_sub_division: Optional[str] = None
    country: Optional[str] = None
    address_lines: List[str] = []


class CanonicalAgent(BaseModel):
    """A bank in the payment chain (debtor agent, creditor agent, intermediary 1..3, instructing or instructed agent)."""
    role: str  # DEBTOR_AGENT, CREDITOR_AGENT, INTERMEDIARY, INSTRUCTING_AGENT, INSTRUCTED_AGENT
    bic: Optional[str] = None
    name: Optional[str] = None
    clearing_system_id: Optional[str] = None
    member_id: Optional[str] = None
    lei: Optional[str] = None
    sequence: Optional[int] = None  # position among intermediaries


class ChargeInfo(BaseModel):
    amount: float
    currency: str
    agent_bic: Optional[str] = None


class CanonicalCharges(BaseModel):
    """Who pays the fees (ChrgBr), the charges taken on the way, and the original instructed amount and rate when the payment was converted."""
    charge_bearer: Optional[str] = None  # DEBT, CRED, SHAR, SLEV
    items: List[ChargeInfo] = []
    instructed_amount: Optional[float] = None
    instructed_currency: Optional[str] = None
    exchange_rate: Optional[float] = None


class CanonicalRemittance(BaseModel):
    unstructured: List[str] = []
    structured_reference: Optional[str] = None
    reference_type: Optional[str] = None  # SCOR (creditor reference), etc.


class CanonicalPurpose(BaseModel):
    code: Optional[str] = None  # ExternalPurpose1Code
    category_code: Optional[str] = None  # ExternalCategoryPurpose1Code
    regulatory_codes: List[str] = []


class CanonicalEnvelope(BaseModel):
    """What the message itself says about how it travels: type, ids, settlement method, clearing system, service level, agents, instructions."""
    message_type: Optional[str] = None
    message_id: Optional[str] = None
    created_at: Optional[str] = None
    number_of_transactions: Optional[int] = None
    settlement_method: Optional[str] = None
    clearing_system: Optional[str] = None
    service_level: Optional[str] = None
    local_instrument: Optional[str] = None
    instructing_agent_bic: Optional[str] = None
    instructed_agent_bic: Optional[str] = None
    instructions_for_next_agent: List[str] = []


class CanonicalStatusReport(BaseModel):
    """pacs.002 status report or pacs.004 return: what happened to a payment and why."""
    message_type: str
    message_id: Optional[str] = None
    kind: str = "STATUS"  # STATUS | RETURN
    uetr: Optional[str] = None
    status: Optional[str] = None
    reason_code: Optional[str] = None
    additional_info: Optional[str] = None
    originator: Optional[str] = None
    returned_amount: Optional[float] = None
    currency: Optional[str] = None


class CanonicalInvestigation(BaseModel):
    """camt.056 recall, camt.029 answer, camt.110 investigation request, camt.111 response."""
    message_type: str
    message_id: Optional[str] = None
    kind: str  # RECALL | RECALL_ANSWER | INVESTIGATION | INVESTIGATION_ANSWER
    case_id: Optional[str] = None
    original_uetr: Optional[str] = None
    reason_code: Optional[str] = None
    status_code: Optional[str] = None
    narrative: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None


class CanonicalMandate(BaseModel):
    """A direct-debit mandate (pain.009 family). Defined for the mandate profiles; filled when a bank sends mandate data."""
    mandate_id: str
    creditor_scheme_id: Optional[str] = None
    signature_date: Optional[str] = None
    sequence_type: Optional[str] = None  # FRST, RCUR, FNAL, OOFF
    debtor_account_iban: Optional[str] = None


class CanonicalScreeningAlert(BaseModel):
    """A sanctions, PEP or watch-list hit raised against a party on a payment."""
    alert_id: str
    party_role: Optional[str] = None
    list_name: Optional[str] = None
    matched_name: Optional[str] = None
    match_score: Optional[float] = None
    disposition: Optional[str] = None


class CanonicalParty(BaseModel):
    party_id: str
    party_name: str
    party_type: str  # DEBTOR, CREDITOR, INTERMEDIARY, INSTRUCTING_AGENT
    country: str
    identifier_type: Optional[str] = "NAME"
    identifier_value: Optional[str] = None
    token_ref: Optional[str] = None
    address: Optional[CanonicalPostalAddress] = None

class CanonicalAccount(BaseModel):
    account_id: str
    account_number: Optional[str] = None
    iban: Optional[str] = None
    currency: str
    bank_bic: Optional[str] = None
    bank_name: Optional[str] = None
    token_ref: Optional[str] = None

class CanonicalPayment(BaseModel):
    payment_id: str
    uetr: str
    instruction_id: str
    end_to_end_id: Optional[str] = None
    amount: float
    currency: str
    payment_rail: str  # SWIFT, CBPR+, FEDWIRE, SEPA, TARGET2
    debtor_party: CanonicalParty
    debtor_account: CanonicalAccount
    creditor_party: CanonicalParty
    creditor_account: CanonicalAccount
    settlement_date: Optional[str] = None
    source_bank_id: str
    raw_source_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Message detail the profiles rely on. All optional, so earlier constructions keep working.
    debtor_agent: Optional[CanonicalAgent] = None
    creditor_agent: Optional[CanonicalAgent] = None
    intermediary_agents: List[CanonicalAgent] = []
    ultimate_debtor: Optional[CanonicalParty] = None
    ultimate_creditor: Optional[CanonicalParty] = None
    charges: Optional[CanonicalCharges] = None
    remittance: Optional[CanonicalRemittance] = None
    purpose: Optional[CanonicalPurpose] = None
    envelope: Optional[CanonicalEnvelope] = None

class CanonicalException(BaseModel):
    exception_id: str
    case_id: str
    profile: ExceptionProfile
    domain: ExceptionDomain = ExceptionDomain.DATA_QUALITY
    secondary_profiles: List[ExceptionProfile] = []
    error_code: str
    reason: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    severity: ExceptionSeverity = ExceptionSeverity.MEDIUM
    priority: ExceptionPriority = ExceptionPriority.NORMAL
    sla_due_at: datetime
    at_risk_amount: float
    assigned_queue: str = "Repair"  # Repair, Compliance, Investigation, Treasury

class CaseSummary(BaseModel):
    case_id: str
    payment_ref: str
    uetr: str
    profile: ExceptionProfile
    domain: ExceptionDomain = ExceptionDomain.DATA_QUALITY
    secondary_profiles: List[ExceptionProfile] = []
    error_code: str
    reason: str
    amount: float
    currency: str
    counterparty: str
    queue: str
    status: LifecycleStage
    severity: ExceptionSeverity
    priority: ExceptionPriority
    sla_due_at: datetime
    dual_auth_required: bool = False
    ai_confidence: Optional[float] = None
    created_at: datetime

class PeXCase(BaseModel):
    case_id: str
    payment_id: str
    uetr: str
    payment_ref: str
    profile: ExceptionProfile
    domain: ExceptionDomain = ExceptionDomain.DATA_QUALITY
    secondary_profiles: List[ExceptionProfile] = []
    error_code: str
    reason: str
    amount: float
    currency: str
    payment_rail: str
    debtor_party: Dict[str, Any]
    debtor_account: Dict[str, Any]
    creditor_party: Dict[str, Any]
    creditor_account: Dict[str, Any]
    queue: str
    status: LifecycleStage
    severity: ExceptionSeverity
    priority: ExceptionPriority
    sla_due_at: datetime
    dual_auth_required: bool = False
    ai_confidence: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approval_history: List[Dict[str, Any]] = []
    settled_at: Optional[str] = None
    audit_timeline: List[Dict[str, Any]] = []


class CanonicalBankOutcome(BaseModel):
    """The bank's final word on an action PeX handed over (a signed callback, or a pacs.002 status mapped to one)."""
    idempotency_key: str
    case_id: str
    outcome: str  # SETTLED | EXECUTED_CONFIRMED | REJECTED | FAILED
    bank_reference: str
    clearing_system: Optional[str] = None
    received_at: str
    signature_verified: bool = False
    uetr: Optional[str] = None
    status_code: Optional[str] = None  # pacs.002 TxSts when the outcome came from a status report
    reason_code: Optional[str] = None
    originator: Optional[str] = None


class CanonicalCustomer(BaseModel):
    """The bank's view of the instructing customer (BIAN Customer Management). Comes from the bank's customer system."""
    client_id: str
    name: str
    client_type: Optional[str] = None  # CORPORATE, FINANCIAL_INSTITUTION, PRIVATE
    segment: Optional[str] = None
    country: Optional[str] = None
    risk_rating: Optional[str] = None  # LOW, MEDIUM, HIGH
    service_tier: Optional[str] = None
    historical_exception_rate: Optional[float] = None
    stp_repair_eligible: Optional[bool] = None


class CanonicalKycRecord(BaseModel):
    """The customer's KYC standing, from the bank's KYC system."""
    client_id: str
    status: str  # ACTIVE, EXPIRED, UNDER_REVIEW
    risk_classification: Optional[str] = None
    expired_documents: List[str] = []
    missing_documents: List[str] = []
    payment_restriction: bool = False


class CanonicalTreasuryPosition(BaseModel):
    """Nostro position per correspondent and currency (BIAN Treasury Management), from the bank's treasury system."""
    correspondent_bic: str
    currency: str
    nostro_balance: float
    liquidity_threshold: Optional[float] = None
    currency_shortfall: Optional[float] = None
    funding_route_available: Optional[bool] = None


class CanonicalPrecedentSummary(BaseModel):
    """What PeX's precedent memory knows about similar earlier cases."""
    case_match_count: int = 0
    average_similarity: Optional[float] = None
    last_resolution_action: Optional[str] = None
    settlement_success_rate: Optional[float] = None


class CanonicalRoutingEntry(BaseModel):
    """One entry from a bank directory: a BIC (SwiftRef) or a clearing member / routing number (central bank directory), with its status,
    successors, rails it can be reached on, where it came from and how long it can be trusted."""
    bic: Optional[str] = None
    clearing_system_id: Optional[str] = None
    member_id: Optional[str] = None
    institution_name: Optional[str] = None
    country: Optional[str] = None
    status: str  # ACTIVE, INACTIVE, DEPRECATED, REPLACED, MERGED, UNKNOWN, NOT_FOUND
    is_head_office: Optional[bool] = None
    successor_bics: List[str] = []
    supported_rails: List[str] = []
    source: Optional[str] = None
    retrieved_at: Optional[str] = None
    effective_at: Optional[str] = None
    expires_at: Optional[str] = None


def __getattr__(name: str):
    """CanonicalApprovalRecord and CanonicalAuditEvent are the workflow's own classes, exposed here so there is one definition.
    Loaded on first use because the approval schema imports this module."""
    if name == "CanonicalApprovalRecord":
        from app.schemas.approval import ApprovalRecord
        return ApprovalRecord
    if name == "CanonicalAuditEvent":
        from app.schemas.audit import AuditEvent
        return AuditEvent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
