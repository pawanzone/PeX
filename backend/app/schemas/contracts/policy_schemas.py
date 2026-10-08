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
    """Configurable bank monetary and exposure thresholds."""
    max_autonomous_stp_amount: float = 10000.0       # e.g., $10k default autonomous ceiling
    max_batch_fast_lane_amount: float = 25000.0     # e.g., $25k default batch release ceiling
    dual_auth_mandatory_threshold: float = 250000.0  # Amounts >= $250k require 2-level Maker-Checker
    currency: str = "USD"
    allowed_currencies: List[str] = Field(default_factory=lambda: ["USD", "EUR", "GBP", "CHF", "JPY", "SGD", "CAD", "AUD"])


class BankPolicyEnvelope(BaseModel):
    """Authoritative Bank Policy Envelope."""
    policy_id: str
    policy_version: str = "v1.0.0"
    environment: str = "TEST_ONLY"                   # Clearly marked: DEMO_ONLY / TEST_ONLY / PRODUCTION
    effective_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    risk_thresholds: BankRiskThresholds = Field(default_factory=BankRiskThresholds)
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
