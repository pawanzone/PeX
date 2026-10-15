"""Wave 3 Domain Contract Schemas for PeX Industrialization Architecture.

Defines Pydantic data schemas for Treasury, Liquidity, and Exposure Management profiles:
- TR-02: Insufficient Funds
- TR-03: Nostro Shortfall
- TR-04: FX Rate Unavailable
- TR-06: Limit Breach
- TR-07: Liquidity Constraint
- TR-08: Credit Exposure Breach

Zero vendor SDK dependencies. Provider-neutral, cloud-neutral, model-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


# ==============================================================================
# 1. BALANCE & INSUFFICIENT FUNDS SCHEMAS (TR-02 — PAT-C / PAT-B)
# ==============================================================================

class AccountBalanceRecord(BaseModel):
    """Authoritative account balance and position record."""
    account_number: str
    currency: str = "USD"
    ledger_balance: float
    available_balance: float
    as_of_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_authoritative: bool = True
    authority_source: str = "CORE_BANKING_LEDGER"
    holds_amount: float = 0.0
    pending_credits: float = 0.0


class IntradayReservationRecord(BaseModel):
    """Intraday funds reservation and headroom tracking record."""
    reservation_id: str
    account_number: str
    reserved_amount: float
    currency: str = "USD"
    reservation_status: str = "ACTIVE"  # ACTIVE / RELEASED / EXPIRED
    expires_at: Optional[datetime] = None


class TreasuryPacingSchedule(BaseModel):
    """Governed pacing retry candidate for intraday liquidity or limit reset cycles."""
    schedule_id: str
    target_profile: str
    pacing_interval_seconds: float
    max_retry_attempts: int = 3
    current_attempt: int = 0
    next_evaluation_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pacing_reason: str
    execution_owner: str = "BANK"


# ==============================================================================
# 2. NOSTRO POSITION & REBALANCING SCHEMAS (TR-03 — PAT-C / PAT-B)
# ==============================================================================

class NostroPositionRecord(BaseModel):
    """Authoritative correspondent Nostro account position."""
    nostro_bic: str
    currency: str
    available_balance: float
    ledger_balance: float
    minimum_operating_target: float = 0.0
    as_of_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_authoritative: bool = True
    authority_source: str = "TREASURY_MANAGEMENT_SYSTEM"


class PendingCorrespondentCreditRecord(BaseModel):
    """Expected correspondent clearing credit feed."""
    credit_reference: str
    target_nostro_bic: str
    currency: str
    expected_amount: float
    expected_arrival_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    clearing_rail: str = "SWIFT_CBPR+"
    confidence_score: float = 1.0


class NostroRebalancingCandidate(BaseModel):
    """Governed candidate package for interbank liquidity rebalancing."""
    candidate_id: str
    target_nostro_bic: str
    funding_nostro_account: str
    rebalancing_amount: float
    currency: str
    recommended_pacing_seconds: float = 0.0
    execution_owner: str = "BANK"
    rationale: str


# ==============================================================================
# 3. FX PRICING & MARKET DATA SCHEMAS (TR-04 — PAT-C / PAT-A)
# ==============================================================================

class FXRateQuoteRecord(BaseModel):
    """Authoritative FX market rate quote record."""
    currency_pair: str  # e.g., "EUR/USD", "GBP/USD"
    base_currency: str
    quote_currency: str
    mid_rate: float
    bid_rate: Optional[float] = None
    ask_rate: Optional[float] = None
    quote_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    quote_source: str = "OFFICIAL_FX_PRICING_ENGINE"
    is_live: bool = True
    is_authoritative: bool = True


class FXSpreadPolicyRecord(BaseModel):
    """Configured bank spread and freshness policy for cross-currency instructions."""
    currency_pair: str
    max_rate_age_seconds: float = 60.0
    max_spread_tolerance_bps: float = 50.0  # 0.50%
    allow_auto_booking: bool = True


class FXBookingCandidate(BaseModel):
    """Governed FX pricing booking candidate."""
    booking_id: str
    currency_pair: str
    applied_rate: float
    instructed_amount: float
    instructed_currency: str
    settlement_amount: float
    settlement_currency: str
    quote_timestamp: datetime
    execution_owner: str = "BANK"


# ==============================================================================
# 4. OPERATIONAL LIMIT SCHEMAS (TR-06 — PAT-C / PAT-D)
# ==============================================================================

class LimitType(str, Enum):
    DAILY_ACCOUNT_LIMIT = "DAILY_ACCOUNT_LIMIT"
    CORRIDOR_VELOCITY_LIMIT = "CORRIDOR_VELOCITY_LIMIT"
    TRANSACTION_CAP = "TRANSACTION_CAP"
    PRODUCT_LIMIT = "PRODUCT_LIMIT"
    CHANNEL_LIMIT = "CHANNEL_LIMIT"


class LimitUtilizationRecord(BaseModel):
    """Authoritative limit utilization and headroom record."""
    limit_id: str
    limit_type: LimitType
    limit_cap: float
    current_utilization: float
    currency: str = "USD"
    reset_schedule_utc: Optional[datetime] = None
    is_breached: bool = False
    is_authoritative: bool = True
    authority_source: str = "BANK_LIMIT_ENGINE"


class ClientLimitProfileRecord(BaseModel):
    """Client operational limit governance profile."""
    client_id: str
    account_number: str
    approved_overdraft_facility: float = 0.0
    preauthorized_waiver_cap: float = 0.0
    waiver_requires_dual_auth: bool = True


class OperationalLimitWaiverDossier(BaseModel):
    """Governed waiver package for human Credit/Risk Officer adjudication."""
    dossier_id: str
    limit_id: str
    breached_amount: float
    currency: str
    utilization_percentage: float
    requires_credit_approver: bool = True
    pacing_schedule: Optional[TreasuryPacingSchedule] = None
    execution_owner: str = "BANK"


# ==============================================================================
# 5. LIQUIDITY CONSTRAINT SCHEMAS (TR-07 — PAT-C / PAT-B)
# ==============================================================================

class LiquidityReserveRecord(BaseModel):
    """Authoritative liquidity position across applicable clearing context."""
    clearing_context: str  # e.g., "FEDWIRE", "TARGET2", "CHAPS", "PORTFOLIO_USD"
    currency: str
    current_available_liquidity: float
    minimum_buffer_target: float
    headroom: float
    as_of_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_constrained: bool = False
    is_authoritative: bool = True
    authority_source: str = "LIQUIDITY_MANAGEMENT_SYSTEM"


class QueueStatusRecord(BaseModel):
    """Status of clearing channel or settlement priority queues."""
    queue_id: str
    clearing_context: str
    active_queue_depth: int
    priority_tier: str = "STANDARD"
    estimated_release_delay_seconds: float = 0.0


# ==============================================================================
# 6. CREDIT EXPOSURE BREACH SCHEMAS (TR-08 — PAT-D / PAT-C)
# ==============================================================================

class CounterpartyExposureRecord(BaseModel):
    """Authoritative counterparty / borrower credit exposure record."""
    counterparty_id: str
    counterparty_bic: Optional[str] = None
    credit_rating: str = "INVESTMENT_GRADE"  # e.g. AAA, AA, BBB, SUB_INVESTMENT
    total_facility_limit: float
    current_drawn_exposure: float
    currency: str = "USD"
    is_breached: bool = False
    is_authoritative: bool = True
    authority_source: str = "ENTERPRISE_CREDIT_RISK_SYSTEM"


class CreditFacilityRecord(BaseModel):
    """Credit facility agreement metadata."""
    facility_id: str
    borrower_entity: str
    facility_type: str = "REVOLVING_CREDIT"
    collateral_coverage_ratio: float = 1.0
    expiry_date: Optional[datetime] = None
    approval_tier_required: str = "SENIOR_CREDIT_OFFICER"


class CreditDecisionRecord(BaseModel):
    """Human Credit Officer adjudication decision token."""
    decision_id: str
    counterparty_id: str
    decision: str  # "APPROVED_WITH_WAIVER", "REJECTED_CREDIT_HOLD"
    approver_id: str
    approver_role: str = "SENIOR_CREDIT_OFFICER"
    dual_auth_approver_id: Optional[str] = None
    waiver_amount: float = 0.0
    approved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approval_token_verified: bool = True


class CreditRiskDossierRecord(BaseModel):
    """Assembled credit risk dossier for governed human review."""
    dossier_id: str
    counterparty_id: str
    requested_amount: float
    currency: str
    exposure_record: CounterpartyExposureRecord
    facility_record: Optional[CreditFacilityRecord] = None
    decision_record: Optional[CreditDecisionRecord] = None
    autonomous_stp_prohibited: bool = True
    execution_owner: str = "BANK"
