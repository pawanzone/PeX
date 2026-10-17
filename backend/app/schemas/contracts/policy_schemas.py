"""Bank Policy Envelope Contract Schemas.

Defines the bank-configurable risk, compliance, threshold, and dual-authorization policy envelopes.
Missing or stale bank policies fail closed.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class PolicyEnvironment(str):
    PRODUCTION = "PRODUCTION"
    STAGING = "STAGING"
    DEMO_ONLY = "DEMO_ONLY"
    TEST_ONLY = "TEST_ONLY"


class BankRiskThresholds(BaseModel):
    """Configurable bank monetary and exposure thresholds.
    
    Reconciled P0-2: Unified threshold of $100,000.0 replaces divergent values:
    - Previous file_watcher autonomous ceiling: $10,000.0
    - Previous API batch fast-lane ceiling: $25,000.0
    - Previous A_limit evaluation: $100,000.0
    """
    max_stp_amount: float = 100000.0                 # Unified STP threshold ($100k)
    max_autonomous_stp_amount: float = 100000.0      # Unified autonomous ceiling (was $10k)
    max_batch_fast_lane_amount: float = 100000.0     # Unified batch release ceiling (was $25k)
    dual_auth_mandatory_threshold: float = 250000.0  # Amounts >= $250k require 2-level Maker-Checker
    currency: str = "USD"
    allowed_currencies: List[str] = Field(default_factory=lambda: ["USD", "EUR", "GBP", "CHF", "JPY", "SGD", "CAD", "AUD"])


class W1PolicyMatchingThresholds(BaseModel):
    """W1-POL-01: Bank-configurable Verification of Payee / Beneficiary Name Matching Threshold Bands."""
    exact_match_threshold: float = 1.0
    close_match_threshold: float = 0.85
    reject_threshold: float = 0.70
    allow_close_match_stp: bool = True


class W1PolicyCutoffBuffer(BaseModel):
    """W1-POL-02: Bank-configurable Cutoff Missed Buffer and Value-Date Roll Policy."""
    cutoff_buffer_minutes: int = 15
    allow_auto_value_date_roll: bool = True
    max_value_date_roll_days: int = 3
    require_client_roll_authorization: bool = False


class W2PolicyThresholds(BaseModel):
    """Wave 2 Bank Policy Decisions:
    - W2-BPD-01: Automated Correspondent Reroute Thresholds (PR-06)
    - W2-BPD-02: Closed Account Return vs. Rollover Policy (ST-02)
    - W2-BPD-03: Frozen Account Return vs. Legal Suspense Escrow (ST-03)
    """
    # W2-BPD-01: Correspondent Reroute Parameters
    max_auto_reroute_amount: float = 50000.0
    allowed_correspondent_tiers: List[str] = Field(default_factory=lambda: ["TIER_1_NOSTRO", "PRIMARY_CORRESPONDENT", "SWIFT_CBPR_MEMBER"])
    allow_auto_reroute: bool = True

    # W2-BPD-02: Closed Account Parameters
    allow_closed_account_auto_return: bool = True
    max_closed_account_auto_return_amount: float = 100000.0
    allow_mandate_rollover: bool = False
    require_dual_auth_for_rollover: bool = True

    # W2-BPD-03: Frozen Account Parameters
    allow_frozen_account_auto_return: bool = True
    allow_legal_suspense_booking: bool = True
    max_frozen_account_auto_return_amount: float = 100000.0
    require_legal_officer_signoff_for_suspense: bool = False


class W3PolicyThresholds(BaseModel):
    """Wave 3 Bank Policy Decisions:
    - W3-BPD-01: TR-02 Insufficient Funds Pacing Policy
    - W3-BPD-02: TR-03 Nostro Rebalancing Policy
    - W3-BPD-03: TR-04 FX Rate & Spread Tolerance Policy
    - W3-BPD-04: TR-06 Limit Reset & Waiver Policy
    - W3-BPD-05: TR-07 Liquidity Pacing Policy
    - W3-BPD-06: TR-08 Credit Exposure Policy (Autonomous STP Prohibited)
    """
    # W3-BPD-01: TR-02 Insufficient Funds Pacing
    allow_auto_retry_pacing: bool = True
    max_pacing_retry_seconds: float = 1800.0
    min_available_balance_buffer: float = 0.0
    max_auto_pacing_amount: float = 100000.0

    # W3-BPD-02: TR-03 Nostro Rebalancing Policy
    allow_auto_nostro_sweep: bool = True
    min_nostro_operating_balance: float = 1000000.0
    max_auto_sweep_amount: float = 500000.0
    allowed_sweep_funding_accounts: List[str] = Field(default_factory=lambda: ["NOSTRO-MASTER-EUR", "NOSTRO-CENTRAL-USD"])

    # W3-BPD-03: TR-04 FX Rate & Spread Tolerance
    allow_auto_rate_booking: bool = True
    max_fx_rate_age_seconds: float = 60.0
    max_fx_spread_tolerance_bps: float = 50.0
    max_auto_fx_amount: float = 250000.0

    # W3-BPD-04: TR-06 Limit Reset & Waiver Policy
    allow_intraday_limit_reset_pacing: bool = True
    max_limit_reset_pacing_seconds: float = 3600.0
    max_limit_waiver_threshold: float = 500000.0
    require_credit_officer_dual_auth: bool = True

    # W3-BPD-05: TR-07 Liquidity Pacing Policy
    allow_auto_liquidity_pacing: bool = True
    min_liquidity_buffer: float = 5000000.0
    max_liquidity_hold_seconds: float = 7200.0
    priority_release_tier: str = "STANDARD_COMMERCIAL"

    # W3-BPD-06: TR-08 Credit Exposure Policy
    zero_auto_stp_on_credit_breach: bool = True  # MANDATORY INVARIANT: Autonomous STP Prohibited
    require_senior_risk_approver: bool = True
    max_dossier_compilation_seconds: float = 300.0


class W4PolicyThresholds(BaseModel):
    """Wave 4 Bank Policy Decisions:
    - W4-BPD-01: TR-01 KYC Expired Provisional Waiver Policy
    - W4-BPD-02: TR-05 Authorization Missing Dual-Auth & Mandate Policy
    - W4-BPD-03: ST-06 Funds Trapped at Correspondent Policy (Autonomous STP Prohibited)
    """
    # W4-BPD-01: TR-01 KYC Expired Policy
    allow_provisional_kyc_waiver: bool = True
    max_provisional_waiver_days: int = 30
    max_provisional_waiver_amount: float = 50000.0
    require_refresh_in_progress: bool = True
    min_clean_dispute_months: int = 24

    # W4-BPD-02: TR-05 Authorization Missing Policy
    allow_portal_dual_auth_release: bool = True
    max_auto_portal_auth_amount: float = 250000.0
    require_class_a_signatory: bool = True
    require_mfa_callback_verified: bool = True

    # W4-BPD-03: ST-06 Funds Trapped at Correspondent Policy
    zero_auto_stp_on_transit_break: bool = True  # MANDATORY INVARIANT: ST-06 is Group 4 Transit Break
    min_transit_hold_minutes_for_inquiry: float = 120.0
    allowed_inquiry_message_types: List[str] = Field(default_factory=lambda: ["CAMT_056", "CAMT_027"])
    require_operations_maker_checker: bool = True


class BankPolicyEnvelope(BaseModel):
    """Authoritative Bank Policy Envelope."""
    policy_id: str
    policy_version: str = "v1.0.0"
    environment: str = "TEST_ONLY"                   # Clearly marked: DEMO_ONLY / TEST_ONLY / PRODUCTION
    effective_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    risk_thresholds: BankRiskThresholds = Field(default_factory=BankRiskThresholds)
    w1_matching_thresholds: W1PolicyMatchingThresholds = Field(default_factory=W1PolicyMatchingThresholds)
    w1_cutoff_buffer: W1PolicyCutoffBuffer = Field(default_factory=W1PolicyCutoffBuffer)
    w2_policy_thresholds: W2PolicyThresholds = Field(default_factory=W2PolicyThresholds)
    w3_policy_thresholds: W3PolicyThresholds = Field(default_factory=W3PolicyThresholds)
    w4_policy_thresholds: W4PolicyThresholds = Field(default_factory=W4PolicyThresholds)
    auto_stp_enabled_profiles: List[str] = Field(default_factory=list)
    dual_auth_required_profiles: List[str] = Field(default_factory=list)
    sanctions_zero_tolerance: bool = True
    maker_checker_distinct_identity_enforced: bool = True
    fail_closed_on_missing_policy: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationResult(BaseModel):
    """Outcome of evaluating a transaction against the BankPolicyEnvelope."""
    policy_id: str
    policy_allows_action: bool                       # P_bank predicate
    is_autonomous_stp_permitted: bool
    is_batch_fast_lane_permitted: bool
    requires_maker_checker: bool
    required_approver_roles: List[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    denial_reasons: List[str] = Field(default_factory=list)
    policy_warnings: List[str] = Field(default_factory=list)
