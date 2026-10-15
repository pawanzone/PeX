"""Wave 4 Domain Contract Schemas for PeX Industrialization Architecture.

Defines Pydantic data schemas for Wave 4 exception profiles:
- TR-01: KYC Expired (Client/Treasury Domain — SOP-302 Provisional Waiver Evaluation)
- TR-05: Authorization Missing (Client/Treasury Domain — Corporate Signatory Mandate & Portal Callback)
- ST-06: Funds Trapped at Correspondent (Settlement & Returns Domain — SWIFT gpi Transit Break & Inquiry Packaging)

Zero vendor SDK dependencies. Provider-neutral, cloud-neutral, model-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field


# ==============================================================================
# 1. KYC LIFECYCLE & PROVISIONAL WAIVER SCHEMAS (TR-01 — PAT-C / PAT-B)
# ==============================================================================

class CustomerKycRecord(BaseModel):
    """Authoritative client onboarding and periodic KYC master record."""
    client_id: str
    client_name: str
    kyc_status: str = "EXPIRED"  # ACTIVE / EXPIRED / REFRESH_IN_PROGRESS / SUSPENDED
    last_review_date: datetime
    expiry_date: datetime
    refresh_in_progress: bool = True
    dispute_free_months: int = 24
    is_authoritative: bool = True
    authority_source: str = "CLIENT_ONBOARDING_KYC_MASTER"


class CorporateStandingRecord(BaseModel):
    """Authoritative client corporate relationship standing and risk track record."""
    client_id: str
    tier_rating: str = "TIER_1_MULTINATIONAL"  # TIER_1_MULTINATIONAL / TIER_2_REGIONAL / RETAIL
    credit_score: int = 800
    relationship_tenure_years: int = 5
    has_active_sar_or_regulatory_query: bool = False
    clearing_corridor_risk: str = "LOW"  # LOW / MEDIUM / HIGH


class KycWaiverPolicyRecord(BaseModel):
    """SOP-302 Bank KYC Provisional Processing Policy parameters."""
    allow_provisional_waiver: bool = True
    max_waiver_days: int = 30
    max_waiver_amount: float = 50000.0
    min_clean_months: int = 24


class KycProvisionalWaiverCandidate(BaseModel):
    """Governed candidate package for provisional 30-day KYC processing waiver."""
    waiver_id: str = Field(default_factory=lambda: f"WVR-KYC-{uuid.uuid4().hex[:8].upper()}")
    client_id: str
    waiver_duration_days: int = 30
    expiry_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provisional_status: str = "WAIVER_ACTIVE_30_DAYS"
    execution_owner: str = "BANK"
    rationale: str


# ==============================================================================
# 2. CORPORATE MANDATE & DUAL-AUTHORIZATION SCHEMAS (TR-05 — PAT-C / PAT-B)
# ==============================================================================

class CorporateMandateRecord(BaseModel):
    """Authoritative corporate account signatory and delegation of authority mandate."""
    mandate_id: str
    debtor_account: str
    dual_auth_threshold: float = 250000.0
    required_signatory_count: int = 2
    allowed_signer_classes: List[str] = Field(default_factory=lambda: ["CLASS_A", "CLASS_B"])
    is_authoritative: bool = True
    authority_source: str = "CORPORATE_MANDATE_SYSTEM"


class SecondarySignatoryRecord(BaseModel):
    """Secondary corporate signatory digital sign-off record."""
    signatory_id: str
    signatory_name: str
    signer_class: str = "CLASS_A"  # CLASS_A / CLASS_B / UNAUTHORIZED
    signature_status: str = "APPROVED"  # APPROVED / PENDING / REJECTED
    mfa_verified: bool = True
    signature_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    digital_token_reference: Optional[str] = None


class PortalCallbackRecord(BaseModel):
    """Out-of-band corporate banking portal callback and verification record."""
    callback_id: str
    debtor_account: str
    callback_status: str = "VERIFIED"  # VERIFIED / UNREACHABLE / FAILED
    verification_channel: str = "CORPORATE_PORTAL_MFA"


class CorporateDualAuthorizationCandidate(BaseModel):
    """Governed candidate package confirming corporate dual-authorization clearance."""
    authorization_id: str = Field(default_factory=lambda: f"AUTH-MAND-{uuid.uuid4().hex[:8].upper()}")
    mandate_id: str
    primary_signatory_id: str
    secondary_signatory_id: str
    authorization_status: str = "DUAL_AUTHORIZATION_VERIFIED"
    execution_owner: str = "BANK"
    rationale: str


# ==============================================================================
# 3. INTERMEDIARY TRANSIT TRACKING & INQUIRY SCHEMAS (ST-06 — PAT-F / PAT-E)
# ==============================================================================

class CorrespondentTrackerHopRecord(BaseModel):
    """Authoritative SWIFT gpi tracker hop telemetry record."""
    uetr: str
    intermediary_bic: str
    hop_number: int = 2
    hold_duration_minutes: float = 180.0
    hop_status: str = "HELD_AT_INTERMEDIARY"  # HELD_AT_INTERMEDIARY / ROUTED / REJECTED
    is_authoritative: bool = True
    authority_source: str = "SWIFT_GPI_TRACKER"


class DebitConfirmationRecord(BaseModel):
    """Inward camt.054 debit confirmation record proving funds left debtor account."""
    debit_reference: str
    debtor_account: str
    amount: float
    currency: str
    debit_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_confirmed: bool = True


class TransitInquiryPolicyRecord(BaseModel):
    """Correspondent banking transit break investigation policy."""
    min_hold_minutes_for_inquiry: float = 120.0
    inquiry_message_type: str = "CAMT_056"  # CAMT_056 / CAMT_027
    target_desk: str = "CORRESPONDENT_INVESTIGATION_DESK"


class TransitInvestigationCandidate(BaseModel):
    """Governed candidate package for correspondent transit break investigation."""
    investigation_id: str = Field(default_factory=lambda: f"INV-TRAP-{uuid.uuid4().hex[:8].upper()}")
    uetr: str
    target_intermediary_bic: str
    inquiry_type: str = "CAMT_056"
    inquiry_reference: str
    status: str = "DISPATCH_CAMT056_INTERMEDIARY_INQUIRY"
    autonomous_stp_prohibited: bool = True  # MANDATORY INVARIANT: Group 4 Transit Break
    execution_owner: str = "BANK"
    rationale: str
