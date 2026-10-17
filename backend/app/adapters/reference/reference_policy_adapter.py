"""In-Memory Reference Bank Policy Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements BankPolicyEnvelopePort with deterministic fail-closed policy evaluation.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.ports.policy_port import BankPolicyEnvelopePort
from app.schemas.contracts.policy_schemas import (
    BankPolicyEnvelope,
    BankRiskThresholds,
    PolicyEvaluationResult,
)


class InMemoryBankPolicyAdapter(BankPolicyEnvelopePort):
    """Hermetic reference implementation of BankPolicyEnvelopePort."""

    def __init__(self, default_policy: Optional[BankPolicyEnvelope] = None):
        self._policy: Optional[BankPolicyEnvelope] = default_policy or BankPolicyEnvelope(
            policy_id="POL-DEFAULT-TEST-01",
            policy_version="v1.0.0",
            environment="TEST_ONLY",
            risk_thresholds=BankRiskThresholds(
                max_autonomous_stp_amount=10000.0,
                max_batch_fast_lane_amount=25000.0,
                dual_auth_mandatory_threshold=250000.0
            ),
            auto_stp_enabled_profiles=[
                # Phase 2 Profiles
                "INVALID_IBAN", "INVALID_ROUTING_CODE", "DUPLICATE_PAYMENT",
                "QUEUE_PROCESSING_FAILURE", "RETURNED_PAYMENT", "RESTRICTED_CORRIDOR",
                "DQ-01", "DQ-08", "PR-01", "PR-08", "ST-01", "CO-04",
                # Wave 1 Profiles
                "MISSING_BENEFICIARY_DATA", "MISSING_REMITTANCE_INFO", "INVALID_ACCOUNT_NUMBER",
                "BENEFICIARY_NAME_MISMATCH", "ROUTING_FAILURE", "CUTOFF_MISSED",
                "NETWORK_TIMEOUT", "PAYMENT_HELD_FOR_REPAIR", "REGULATORY_REPORTING_REQUIRED",
                "DQ-03", "DQ-04", "DQ-07", "DQ-09", "PR-02", "PR-04", "PR-07", "PR-09", "CO-07",
                # Wave 2 Profiles
                "INTERMEDIARY_BANK_REJECTION", "ACCOUNT_CLOSED", "BENEFICIARY_ACCOUNT_FROZEN",
                "PR-06", "ST-02", "ST-03",
                # Wave 3 Profiles (TR-08 Strictly Excluded from Auto-STP)
                "INSUFFICIENT_FUNDS", "NOSTRO_SHORTFALL", "FX_RATE_UNAVAILABLE",
                "LIMIT_BREACH", "LIQUIDITY_CONSTRAINT",
                "TR-02", "TR-03", "TR-04", "TR-06", "TR-07",
                # Wave 4 Profiles (ST-06 Strictly Excluded from Auto-STP)
                "KYC_EXPIRED", "AUTHORIZATION_MISSING",
                "TR-01", "TR-05"
            ],
            dual_auth_required_profiles=[
                "SANCTIONS_HOLD", "HIGH_VALUE_WIRE", "AML_SUSPENDED",
                "CREDIT_EXPOSURE_BREACH", "TR-08",
                "FUNDS_TRAPPED_AT_CORRESPONDENT", "ST-06"
            ]
        )

    def set_policy(self, policy: Optional[BankPolicyEnvelope]):
        """Sets or clears the active bank policy envelope."""
        self._policy = policy

    def get_active_policy(self, bank_id: Optional[str] = None) -> Optional[BankPolicyEnvelope]:
        return self._policy

    def evaluate_transaction(
        self,
        policy: Optional[BankPolicyEnvelope],
        profile_id: str,
        amount: float,
        currency: str,
        action_type: str,
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> PolicyEvaluationResult:
        now = datetime.now(timezone.utc)
        ctx = transaction_context or {}

        # 1. Fail closed on missing policy
        if policy is None:
            return PolicyEvaluationResult(
                policy_id="MISSING_POLICY",
                policy_allows_action=False,
                is_autonomous_stp_permitted=False,
                is_batch_fast_lane_permitted=False,
                requires_maker_checker=True,
                evaluated_at=now,
                denial_reasons=["Mandatory BankPolicyEnvelope is missing or unavailable (P_bank == False)."]
            )

        denial_reasons = []
        is_auto = False
        is_batch = False
        requires_mc = False
        approver_roles = []

        # 2. Dual Authorization Ceiling Check
        if profile_id in ["TR-08", "CREDIT_EXPOSURE_BREACH"] or (policy.w3_policy_thresholds.zero_auto_stp_on_credit_breach and profile_id in ["TR-08", "CREDIT_EXPOSURE_BREACH"]):
            requires_mc = True
            is_auto = False
            approver_roles = ["SENIOR_CREDIT_OFFICER", "SENIOR_RISK_CHECKER"]
            denial_reasons.append("TR-08 Credit Exposure Breach: Autonomous STP is strictly prohibited. Senior Credit Officer dual-authorization required.")

        elif profile_id in ["ST-06", "FUNDS_TRAPPED_AT_CORRESPONDENT"] or (policy.w4_policy_thresholds.zero_auto_stp_on_transit_break and profile_id in ["ST-06", "FUNDS_TRAPPED_AT_CORRESPONDENT"]):
            requires_mc = True
            is_auto = False
            approver_roles = ["OPERATIONS_MAKER", "OPERATIONS_CHECKER"]
            denial_reasons.append("ST-06 Funds Trapped at Correspondent: Autonomous STP is strictly prohibited for transit breaks. Operations dual-authorization required.")

        elif amount >= policy.risk_thresholds.dual_auth_mandatory_threshold:
            requires_mc = True
            approver_roles = ["OPERATIONS_MAKER", "SENIOR_RISK_CHECKER"]
            denial_reasons.append(f"High-value amount (${amount:,.2f}) exceeds dual-auth threshold (${policy.risk_thresholds.dual_auth_mandatory_threshold:,.2f}).")

        # 3. Monetary STP Ceiling Check (Reconciled P0-2)
        stp_limit = getattr(policy.risk_thresholds, "max_stp_amount", 100000.0)
        if amount > stp_limit:
            requires_mc = True
            approver_roles = ["OPERATIONS_MAKER", "OPERATIONS_CHECKER"]
            denial_reasons.append(f"Amount (${amount:,.2f}) exceeds bank policy STP threshold (${stp_limit:,.2f}).")

        # 4. Autonomous STP Threshold Check
        elif amount <= policy.risk_thresholds.max_autonomous_stp_amount and profile_id in policy.auto_stp_enabled_profiles:
            is_auto = True

        # 5. Batch Fast Lane Threshold Check
        elif amount <= policy.risk_thresholds.max_batch_fast_lane_amount:
            is_batch = True
            requires_mc = True
            approver_roles = ["OPERATIONS_MAKER"]

        else:
            requires_mc = True
            approver_roles = ["OPERATIONS_MAKER", "OPERATIONS_CHECKER"]
            denial_reasons.append(f"Amount (${amount:,.2f}) exceeds fast-lane batch threshold (${policy.risk_thresholds.max_batch_fast_lane_amount:,.2f}).")

        # 5. Currency Check
        if currency not in policy.risk_thresholds.allowed_currencies:
            denial_reasons.append(f"Currency {currency} is not supported by bank policy.")

        policy_allows = (len(denial_reasons) == 0 or is_batch or requires_mc) and (currency in policy.risk_thresholds.allowed_currencies)

        return PolicyEvaluationResult(
            policy_id=policy.policy_id,
            policy_allows_action=policy_allows,
            is_autonomous_stp_permitted=is_auto,
            is_batch_fast_lane_permitted=is_batch,
            requires_maker_checker=requires_mc,
            required_approver_roles=approver_roles,
            evaluated_at=now,
            denial_reasons=denial_reasons
        )
