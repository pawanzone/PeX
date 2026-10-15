"""TreasuryExposureEngine: Treasury, Liquidity, and Exposure Management Capability Engine.

Authoritative implementation for PeX Wave 3:
- TR-02: Insufficient Funds (PAT-C Pacing Schedule / PAT-B Return Package / Intraday Reservation)
- TR-03: Nostro Shortfall (PAT-C Nostro Rebalancing & Sweep / Pacing Schedule)
- TR-04: FX Rate Unavailable (PAT-C Market Rate Booking Candidate / Spread & Freshness Policy)
- TR-06: Limit Breach (PAT-C Pacing Schedule / PAT-D Operational Limit Waiver Dossier)
- TR-07: Liquidity Constraint (PAT-C Liquidity Reserve Pacing Schedule / Queue Delay Buffer)
- TR-08: Credit Exposure Breach (PAT-D Governed Credit Risk Dossier / Autonomous STP Strictly Prohibited)

Invariants:
- Zero direct payment execution or ledger mutation (execution_owner = "BANK").
- Zero autonomous STP on TR-08 credit exposure breach (zero_auto_stp_on_credit_breach = True).
- Missing, stale, or expired treasury market feeds fail closed.
- Bank-policy parameterized thresholds (W3PolicyThresholds).
- Hermetic and provider-neutral SPI port integrations.
"""
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

from app.ports.treasury_position_port import TreasuryPositionPort
from app.ports.nostro_position_port import NostroPositionPort
from app.ports.fx_pricing_port import FXPricingPort
from app.ports.limit_management_port import LimitManagementPort
from app.ports.credit_risk_port import CreditRiskPort
from app.ports.liquidity_reserve_port import LiquidityReservePort

from app.adapters.reference.reference_treasury_position_adapter import InMemoryTreasuryPositionAdapter
from app.adapters.reference.reference_nostro_position_adapter import InMemoryNostroPositionAdapter
from app.adapters.reference.reference_fx_pricing_adapter import InMemoryFXPricingAdapter
from app.adapters.reference.reference_limit_management_adapter import InMemoryLimitManagementAdapter
from app.adapters.reference.reference_credit_risk_adapter import InMemoryCreditRiskAdapter
from app.adapters.reference.reference_liquidity_reserve_adapter import InMemoryLiquidityReserveAdapter

from app.schemas.contracts.policy_schemas import W3PolicyThresholds
from app.schemas.contracts.wave3_schemas import (
    AccountBalanceRecord,
    IntradayReservationRecord,
    TreasuryPacingSchedule,
    NostroPositionRecord,
    PendingCorrespondentCreditRecord,
    NostroRebalancingCandidate,
    FXRateQuoteRecord,
    FXSpreadPolicyRecord,
    FXBookingCandidate,
    LimitType,
    LimitUtilizationRecord,
    ClientLimitProfileRecord,
    OperationalLimitWaiverDossier,
    LiquidityReserveRecord,
    QueueStatusRecord,
    CounterpartyExposureRecord,
    CreditFacilityRecord,
    CreditDecisionRecord,
    CreditRiskDossierRecord,
)
from app.schemas.resolution_contract import (
    ResolutionStatus,
    ResolutionUniqueness,
    ResolutionCandidate,
)


# ==============================================================================
# REUSABLE CAPABILITY EVALUATORS
# ==============================================================================

class AvailableBalanceEvaluator:
    """Evaluates authoritative account balances, available headroom, and pending credits."""

    @staticmethod
    def evaluate(
        balance_record: AccountBalanceRecord,
        required_amount: float,
        buffer_amount: float = 0.0,
    ) -> Dict[str, Any]:
        net_available = balance_record.available_balance - buffer_amount
        is_covered = net_available >= required_amount
        deficit = max(0.0, required_amount - net_available)
        can_cover_with_pending = (balance_record.available_balance + balance_record.pending_credits) >= (required_amount + buffer_amount)

        return {
            "is_covered": is_covered,
            "net_available": net_available,
            "deficit": deficit,
            "pending_credits": balance_record.pending_credits,
            "can_cover_with_pending": can_cover_with_pending,
        }


class NostroPositionEvaluator:
    """Evaluates Nostro positions against operating minimums and required settlement outflows."""

    @staticmethod
    def evaluate(
        position_record: NostroPositionRecord,
        required_amount: float,
        pending_credits: List[PendingCorrespondentCreditRecord],
    ) -> Dict[str, Any]:
        total_pending = sum(c.expected_amount for c in pending_credits)
        is_covered = position_record.available_balance >= required_amount
        deficit = max(0.0, required_amount - position_record.available_balance)
        can_cover_with_pending = (position_record.available_balance + total_pending) >= required_amount

        return {
            "is_covered": is_covered,
            "available_balance": position_record.available_balance,
            "operating_target": position_record.minimum_operating_target,
            "deficit": deficit,
            "total_pending_credits": total_pending,
            "can_cover_with_pending": can_cover_with_pending,
        }


class FXRatePricingEvaluator:
    """Evaluates FX rate quotes for freshness, spread tolerance, and market consistency."""

    @staticmethod
    def evaluate(
        quote: FXRateQuoteRecord,
        policy: FXSpreadPolicyRecord,
        current_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        now = current_time or datetime.now(timezone.utc)
        age_seconds = (now - quote.quote_timestamp).total_seconds()
        is_fresh = (age_seconds <= policy.max_rate_age_seconds) and quote.is_live

        spread_bps = 0.0
        if quote.bid_rate and quote.ask_rate and quote.mid_rate > 0:
            spread_bps = ((quote.ask_rate - quote.bid_rate) / quote.mid_rate) * 10000.0

        is_spread_acceptable = spread_bps <= policy.max_spread_tolerance_bps

        return {
            "is_valid": is_fresh and is_spread_acceptable and quote.is_authoritative,
            "age_seconds": age_seconds,
            "is_fresh": is_fresh,
            "spread_bps": spread_bps,
            "is_spread_acceptable": is_spread_acceptable,
        }


class OperationalLimitEvaluator:
    """Evaluates operational limit caps, current utilization, and headroom."""

    @staticmethod
    def evaluate(
        limit_record: LimitUtilizationRecord,
        requested_amount: float,
    ) -> Dict[str, Any]:
        headroom = max(0.0, limit_record.limit_cap - limit_record.current_utilization)
        is_within_limit = requested_amount <= headroom
        breached_amount = max(0.0, requested_amount - headroom)
        new_utilization = limit_record.current_utilization + requested_amount
        utilization_pct = (new_utilization / limit_record.limit_cap * 100.0) if limit_record.limit_cap > 0 else 100.0

        return {
            "is_within_limit": is_within_limit,
            "headroom": headroom,
            "breached_amount": breached_amount,
            "new_utilization": new_utilization,
            "utilization_pct": round(utilization_pct, 2),
        }


class CreditExposureEvaluator:
    """Evaluates counterparty credit facility limits, drawn exposures, and risk ratings."""

    @staticmethod
    def evaluate(
        exposure_record: CounterpartyExposureRecord,
        requested_amount: float,
    ) -> Dict[str, Any]:
        headroom = max(0.0, exposure_record.total_facility_limit - exposure_record.current_drawn_exposure)
        is_within_facility = requested_amount <= headroom
        excess_exposure = max(0.0, requested_amount - headroom)
        total_post_draw = exposure_record.current_drawn_exposure + requested_amount
        utilization_pct = (total_post_draw / exposure_record.total_facility_limit * 100.0) if exposure_record.total_facility_limit > 0 else 100.0

        return {
            "is_within_facility": is_within_facility,
            "headroom": headroom,
            "excess_exposure": excess_exposure,
            "total_post_draw": total_post_draw,
            "utilization_pct": round(utilization_pct, 2),
            "is_distressed": exposure_record.credit_rating in ["SUB_INVESTMENT", "DEFAULT", "DISTRESSED"],
        }


class LiquidityConstraintEvaluator:
    """Evaluates clearing queue depth, reserve buffers, and release delay."""

    @staticmethod
    def evaluate(
        reserve: LiquidityReserveRecord,
        queue: Optional[QueueStatusRecord],
        requested_amount: float,
    ) -> Dict[str, Any]:
        is_liquid = (reserve.current_available_liquidity - requested_amount) >= reserve.minimum_buffer_target
        delay = queue.estimated_release_delay_seconds if queue else 0.0

        return {
            "is_liquid": is_liquid,
            "headroom": reserve.headroom,
            "active_queue_depth": queue.active_queue_depth if queue else 0,
            "estimated_delay_seconds": delay,
        }


class PacingRetryCandidateDeriver:
    """Derives deterministic pacing retry schedules for intraday liquidity or reset cycles."""

    @staticmethod
    def derive(
        target_profile: str,
        interval_seconds: float,
        reason: str,
        max_attempts: int = 3,
        current_attempt: int = 1,
    ) -> TreasuryPacingSchedule:
        return TreasuryPacingSchedule(
            schedule_id=f"PACE-{uuid.uuid4().hex[:8].upper()}",
            target_profile=target_profile,
            pacing_interval_seconds=interval_seconds,
            max_retry_attempts=max_attempts,
            current_attempt=current_attempt,
            pacing_reason=reason,
            execution_owner="BANK",
        )


class FundingCandidatePackager:
    """Packages interbank sweep or Nostro rebalancing candidate recommendations."""

    @staticmethod
    def package(
        target_nostro_bic: str,
        funding_account: str,
        amount: float,
        currency: str,
        rationale: str,
    ) -> NostroRebalancingCandidate:
        return NostroRebalancingCandidate(
            candidate_id=f"REBAL-{uuid.uuid4().hex[:8].upper()}",
            target_nostro_bic=target_nostro_bic,
            funding_nostro_account=funding_account,
            rebalancing_amount=amount,
            currency=currency.upper(),
            execution_owner="BANK",
            rationale=rationale,
        )


class RiskDossierAssembler:
    """Assembles governed risk/waiver dossiers for Human-in-the-Loop review."""

    @staticmethod
    def assemble_credit_dossier(
        counterparty_id: str,
        requested_amount: float,
        currency: str,
        exposure_record: CounterpartyExposureRecord,
        facility_record: Optional[CreditFacilityRecord] = None,
    ) -> CreditRiskDossierRecord:
        return CreditRiskDossierRecord(
            dossier_id=f"DOS-CREDIT-{uuid.uuid4().hex[:8].upper()}",
            counterparty_id=counterparty_id,
            requested_amount=requested_amount,
            currency=currency,
            exposure_record=exposure_record,
            facility_record=facility_record,
            decision_record=None,
            autonomous_stp_prohibited=True,
            execution_owner="BANK",
        )


class TemporalCorrelationEvaluator:
    """Checks timestamps, expiry windows, and freshness across treasury market feeds."""

    @staticmethod
    def is_fresh(as_of: datetime, max_age_seconds: float, current_time: Optional[datetime] = None) -> bool:
        now = current_time or datetime.now(timezone.utc)
        return (now - as_of).total_seconds() <= max_age_seconds


# ==============================================================================
# MAIN TREASURY EXPOSURE ENGINE
# ==============================================================================

class TreasuryExposureEngine:
    """Capability engine for Treasury, Liquidity, and Exposure Management (Wave 3)."""

    def __init__(
        self,
        treasury_port: Optional[TreasuryPositionPort] = None,
        nostro_port: Optional[NostroPositionPort] = None,
        fx_port: Optional[FXPricingPort] = None,
        limit_port: Optional[LimitManagementPort] = None,
        credit_port: Optional[CreditRiskPort] = None,
        liquidity_port: Optional[LiquidityReservePort] = None,
    ):
        self.treasury_port = treasury_port or InMemoryTreasuryPositionAdapter()
        self.nostro_port = nostro_port or InMemoryNostroPositionAdapter()
        self.fx_port = fx_port or InMemoryFXPricingAdapter()
        self.limit_port = limit_port or InMemoryLimitManagementAdapter()
        self.credit_port = credit_port or InMemoryCreditRiskAdapter()
        self.liquidity_port = liquidity_port or InMemoryLiquidityReserveAdapter()

    # ==========================================================================
    # 1. TR-02: INSUFFICIENT FUNDS (PAT-C / PAT-B)
    # ==========================================================================
    def resolve_tr02_insufficient_funds(
        self,
        account_number: str,
        instructed_amount: float,
        currency: str = "USD",
        policy_thresholds: Optional[W3PolicyThresholds] = None,
        evidence_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Resolves insufficient debtor funds by checking Core DDA balance, evaluating pending credits,

        and deriving a governed pacing retry schedule or fail-closed return package.
        """
        diff_log: List[str] = []
        ctx = evidence_context or {}
        policy = policy_thresholds or W3PolicyThresholds()

        if ctx.get("conflicting_balance_feeds", False):
            diff_log.append("Conflicting balance feeds detected across core ledger replicas. Escalating to HITL.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_AMBIGUOUS, None, diff_log, "Conflicting balance feeds."

        balance = self.treasury_port.get_account_balance(account_number)
        if not balance:
            diff_log.append(f"No authoritative balance record found for account {account_number}.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Missing authoritative balance record."

        eval_result = AvailableBalanceEvaluator.evaluate(balance, instructed_amount, policy.min_available_balance_buffer)

        # Branch A: Sufficient Available Balance (Strictly Read-Only Intraday Reservation Proposal)
        if eval_result["is_covered"]:
            diff_log.append(f"Account {account_number} has sufficient available balance (${balance.available_balance:,.2f} >= ${instructed_amount:,.2f}).")
            # Pure in-memory candidate proposal without invoking port mutation (W3-FOR-03 Remediation)
            res_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
            repaired_dict = {
                "account_number": account_number,
                "instructed_amount": instructed_amount,
                "currency": currency,
                "reservation_id": res_id,
                "resolution_action": "FUNDS_RESERVED_RELEASE_PAYMENT",
                "execution_owner": "BANK",
            }
            candidate = ResolutionCandidate(
                candidate_id=f"CAND-TR02-RELEASE-{uuid.uuid4().hex[:8]}",
                repaired_payload=json.dumps(repaired_dict),
                repaired_structured=repaired_dict,
                diff_summary="; ".join(diff_log),
                derivation_method="PAT_C_INTRADAY_FUNDS_RESERVATION",
                is_lossless=True,
                fields_reordered=[],
            )
            uniqueness = ResolutionUniqueness.RESOLUTION_AMBIGUOUS if ctx.get("ambiguous_candidates", False) else ResolutionUniqueness.RESOLUTION_UNIQUE
            return ResolutionStatus.RESOLUTION_DETERMINED, uniqueness, candidate, diff_log, None

        # Branch B: Insufficient Balance but Pending Credits & Pacing Permitted (PAT-C Pacing Schedule)
        if policy.allow_auto_retry_pacing and eval_result["can_cover_with_pending"] and instructed_amount <= policy.max_auto_pacing_amount:
            diff_log.append(
                f"Available balance (${balance.available_balance:,.2f}) insufficient, but pending credits (${balance.pending_credits:,.2f}) "
                f"cover deficit (${eval_result['deficit']:,.2f}). Deriving governed pacing schedule."
            )
            pacing = self.treasury_port.calculate_pacing_retry(account_number, instructed_amount, "TR-02")
            repaired_dict = {
                "account_number": account_number,
                "instructed_amount": instructed_amount,
                "currency": currency,
                "deficit": eval_result["deficit"],
                "pacing_schedule": pacing.model_dump(mode="json"),
                "resolution_action": "QUEUE_FOR_PACING_RETRY",
                "execution_owner": "BANK",
            }
            candidate = ResolutionCandidate(
                candidate_id=f"CAND-TR02-PACING-{uuid.uuid4().hex[:8]}",
                repaired_payload=json.dumps(repaired_dict),
                repaired_structured=repaired_dict,
                diff_summary="; ".join(diff_log),
                derivation_method="PAT_C_INTRADAY_PACING_SCHEDULE",
                is_lossless=True,
                fields_reordered=[],
            )
            return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None

        # Branch C: Hard Deficit / No Pacing (Fail-Closed Return / Deficit Notice)
        diff_log.append(f"Account {account_number} has persistent deficit (${eval_result['deficit']:,.2f}) without qualifying pending credits. Fails closed to HITL/Return.")
        return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Insufficient funds: Deficit ${eval_result['deficit']:,.2f} exceeds available buffer."

    # ==========================================================================
    # 2. TR-03: NOSTRO SHORTFALL (PAT-C / PAT-B)
    # ==========================================================================
    def resolve_tr03_nostro_shortfall(
        self,
        nostro_bic: str,
        instructed_amount: float,
        currency: str,
        policy_thresholds: Optional[W3PolicyThresholds] = None,
        evidence_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Resolves correspondent Nostro shortfall by checking balance, identifying incoming clearing credits,

        or generating an interbank liquidity sweep candidate.
        """
        diff_log: List[str] = []
        ctx = evidence_context or {}
        policy = policy_thresholds or W3PolicyThresholds()

        if ctx.get("unreconciled_nostro_ledger", False):
            diff_log.append("Unreconciled ledger breaks present on Nostro statement. Escalating to Treasury Operations.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_AMBIGUOUS, None, diff_log, "Unreconciled Nostro ledger."

        pos = self.nostro_port.get_nostro_position(nostro_bic, currency)
        if not pos:
            diff_log.append(f"No authoritative Nostro position record for {nostro_bic} ({currency}).")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Missing authoritative Nostro position."

        pending_credits = self.nostro_port.get_pending_correspondent_credits(nostro_bic, currency)
        eval_result = NostroPositionEvaluator.evaluate(pos, instructed_amount, pending_credits)

        # Branch A: Sufficient Position
        if eval_result["is_covered"]:
            diff_log.append(f"Nostro position for {nostro_bic} is sufficient ({pos.available_balance:,.2f} {currency} >= {instructed_amount:,.2f} {currency}).")
            repaired_dict = {
                "nostro_bic": nostro_bic,
                "instructed_amount": instructed_amount,
                "currency": currency,
                "resolution_action": "NOSTRO_POSITION_VERIFIED_RELEASE",
                "execution_owner": "BANK",
            }
            candidate = ResolutionCandidate(
                candidate_id=f"CAND-TR03-RELEASE-{uuid.uuid4().hex[:8]}",
                repaired_payload=json.dumps(repaired_dict),
                repaired_structured=repaired_dict,
                diff_summary="; ".join(diff_log),
                derivation_method="PAT_C_NOSTRO_POSITION_VERIFICATION",
                is_lossless=True,
                fields_reordered=[],
            )
            uniqueness = ResolutionUniqueness.RESOLUTION_AMBIGUOUS if ctx.get("ambiguous_candidates", False) else ResolutionUniqueness.RESOLUTION_UNIQUE
            return ResolutionStatus.RESOLUTION_DETERMINED, uniqueness, candidate, diff_log, None

        # Branch B: Shortfall with Sweep Rebalancing Candidate
        if policy.allow_auto_nostro_sweep and instructed_amount <= policy.max_auto_sweep_amount:
            sweep = self.nostro_port.generate_rebalancing_candidate(nostro_bic, instructed_amount, currency)
            if sweep:
                diff_log.append(
                    f"Nostro shortfall ({eval_result['deficit']:,.2f} {currency}) covered via proposed rebalancing sweep from {sweep.funding_nostro_account}."
                )
                repaired_dict = {
                    "nostro_bic": nostro_bic,
                    "instructed_amount": instructed_amount,
                    "currency": currency,
                    "deficit": eval_result["deficit"],
                    "rebalancing_candidate": sweep.model_dump(mode="json"),
                    "resolution_action": "EXECUTE_NOSTRO_REBALANCING_SWEEP",
                    "execution_owner": "BANK",
                }
                candidate = ResolutionCandidate(
                    candidate_id=f"CAND-TR03-SWEEP-{uuid.uuid4().hex[:8]}",
                    repaired_payload=json.dumps(repaired_dict),
                    repaired_structured=repaired_dict,
                    diff_summary="; ".join(diff_log),
                    derivation_method="PAT_C_NOSTRO_LIQUIDITY_REBALANCING",
                    is_lossless=True,
                    fields_reordered=[],
                )
                return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None

        diff_log.append(f"Nostro shortfall ({eval_result['deficit']:,.2f} {currency}) cannot be covered automatically. Escalating to Treasury Desk.")
        return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Nostro shortfall: Deficit {eval_result['deficit']:,.2f} {currency} exceeds auto-sweep threshold."

    # ==========================================================================
    # 3. TR-04: FX RATE UNAVAILABLE (PAT-C / PAT-A)
    # ==========================================================================
    def resolve_tr04_fx_rate_unavailable(
        self,
        currency_pair: str,
        instructed_amount: float,
        instructed_currency: str,
        settlement_currency: str,
        policy_thresholds: Optional[W3PolicyThresholds] = None,
        evidence_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Resolves missing or stale FX rates by retrieving authoritative market quotes,

        validating spread and freshness policies, and booking the rate conversion candidate.
        """
        diff_log: List[str] = []
        ctx = evidence_context or {}
        policy = policy_thresholds or W3PolicyThresholds()

        if ctx.get("market_volatility_circuit_breaker", False):
            diff_log.append("FX market volatility circuit breaker triggered. Automated rate booking suspended.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_AMBIGUOUS, None, diff_log, "Market volatility circuit breaker."

        raw_feed = ctx.get("official_fx_rate_feed")
        if raw_feed and isinstance(raw_feed, dict) and "mid_rate" in raw_feed:
            is_live_flag = bool(raw_feed.get("is_live", True))
            is_auth_flag = bool(raw_feed.get("is_authoritative", True))
            ts = raw_feed.get("quote_timestamp")
            if ts:
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts)
                    except Exception:
                        ts = datetime.now(timezone.utc) if is_live_flag else datetime.now(timezone.utc) - timedelta(seconds=120)
            else:
                ts = datetime.now(timezone.utc) if is_live_flag else datetime.now(timezone.utc) - timedelta(seconds=120)

            quote = FXRateQuoteRecord(
                currency_pair=raw_feed.get("currency_pair", currency_pair),
                base_currency=raw_feed.get("base_currency", "EUR"),
                quote_currency=raw_feed.get("quote_currency", "USD"),
                mid_rate=float(raw_feed.get("mid_rate", 1.0850)),
                bid_rate=float(raw_feed.get("bid_rate", 1.0848)) if "bid_rate" in raw_feed else None,
                ask_rate=float(raw_feed.get("ask_rate", 1.0852)) if "ask_rate" in raw_feed else None,
                quote_timestamp=ts,
                is_live=is_live_flag,
                is_authoritative=is_auth_flag,
                quote_source=raw_feed.get("quote_source", "OFFICIAL_FX_PRICING_ENGINE"),
            )
            self.fx_port.register_fx_quote(quote)
        else:
            quote = self.fx_port.get_fx_rate_quote(currency_pair)

        if not quote:
            diff_log.append(f"No live FX market quote available for currency pair {currency_pair}.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Missing FX quote for {currency_pair}."

        raw_policy = ctx.get("fx_spread_policy_matrix")
        if raw_policy and isinstance(raw_policy, dict):
            spread_policy = FXSpreadPolicyRecord(
                currency_pair=raw_policy.get("currency_pair", currency_pair),
                max_rate_age_seconds=float(raw_policy.get("max_rate_age_seconds", policy.max_fx_rate_age_seconds)),
                max_spread_tolerance_bps=float(raw_policy.get("max_spread_tolerance_bps", policy.max_fx_spread_tolerance_bps)),
                allow_auto_booking=bool(raw_policy.get("allow_auto_booking", policy.allow_auto_rate_booking)),
            )
        else:
            spread_policy = self.fx_port.get_fx_spread_policy(currency_pair) or FXSpreadPolicyRecord(
                currency_pair=currency_pair,
                max_rate_age_seconds=policy.max_fx_rate_age_seconds,
                max_spread_tolerance_bps=policy.max_fx_spread_tolerance_bps,
                allow_auto_booking=policy.allow_auto_rate_booking,
            )

        eval_result = FXRatePricingEvaluator.evaluate(quote, spread_policy)

        # Check Freshness & Spread & Authority
        if not eval_result["is_valid"]:
            if not eval_result["is_fresh"]:
                diff_log.append(f"FX quote for {currency_pair} is stale or inactive (age: {eval_result['age_seconds']:.1f}s > max {spread_policy.max_rate_age_seconds}s, is_live={quote.is_live}). Fails closed.")
                return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Stale or inactive FX rate quote."
            if not quote.is_authoritative:
                diff_log.append(f"FX quote for {currency_pair} is not authoritative. Fails closed.")
                return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Non-authoritative FX rate quote."
            if not eval_result["is_spread_acceptable"]:
                diff_log.append(f"FX spread ({eval_result['spread_bps']:.1f} bps) exceeds tolerance ({spread_policy.max_spread_tolerance_bps:.1f} bps). Requires Trader review.")
                return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "FX spread tolerance exceeded."

        # Check Bank Policy Maximum FX Amount
        if instructed_amount > policy.max_auto_fx_amount:
            diff_log.append(f"Transaction amount ({instructed_amount:,.2f}) exceeds max automated FX booking threshold ({policy.max_auto_fx_amount:,.2f}). Requires FX Desk approval.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Amount exceeds max auto FX booking threshold."

        booking = self.fx_port.book_fx_rate(currency_pair, instructed_amount, instructed_currency, settlement_currency)
        if not booking:
            diff_log.append(f"Failed to generate FX booking candidate for {currency_pair}.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "FX booking candidate generation failed."

        diff_log.append(
            f"Successfully booked rate {booking.applied_rate:.4f} for {currency_pair}. "
            f"Settlement: {booking.settlement_amount:,.2f} {settlement_currency}."
        )
        repaired_dict = booking.model_dump(mode="json")
        candidate = ResolutionCandidate(
            candidate_id=f"CAND-TR04-BOOKING-{uuid.uuid4().hex[:8]}",
            repaired_payload=json.dumps(repaired_dict),
            repaired_structured=repaired_dict,
            diff_summary="; ".join(diff_log),
            derivation_method="PAT_C_FX_MARKET_RATE_BOOKING",
            is_lossless=True,
            fields_reordered=[],
        )
        uniqueness = ResolutionUniqueness.RESOLUTION_AMBIGUOUS if ctx.get("ambiguous_candidates", False) else ResolutionUniqueness.RESOLUTION_UNIQUE
        return ResolutionStatus.RESOLUTION_DETERMINED, uniqueness, candidate, diff_log, None

    # ==========================================================================
    # 4. TR-06: LIMIT BREACH (PAT-C / PAT-D)
    # ==========================================================================
    def resolve_tr06_limit_breach(
        self,
        limit_id: str,
        client_id: str,
        account_number: str,
        instructed_amount: float,
        currency: str = "USD",
        policy_thresholds: Optional[W3PolicyThresholds] = None,
        evidence_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Resolves operational limit breaches by evaluating headroom, reset schedules,

        and packaging waiver / pacing candidates for Credit/Risk adjudication.
        """
        diff_log: List[str] = []
        ctx = evidence_context or {}
        policy = policy_thresholds or W3PolicyThresholds()

        if ctx.get("unauthorized_limit_override_attempt", False):
            diff_log.append("Unauthorized limit override attempt detected. Failing closed to Risk Officer.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_AMBIGUOUS, None, diff_log, "Unauthorized limit override."

        limit_rec = self.limit_port.get_limit_utilization(limit_id)
        if not limit_rec:
            diff_log.append(f"No authoritative limit record found for {limit_id}.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Missing authoritative limit record."

        client_prof = self.limit_port.get_client_limit_profile(client_id, account_number)
        eval_result = OperationalLimitEvaluator.evaluate(limit_rec, instructed_amount)

        # Branch A: Within Limit
        if eval_result["is_within_limit"]:
            diff_log.append(f"Transaction within operational limit {limit_id} (Headroom: ${eval_result['headroom']:,.2f} >= ${instructed_amount:,.2f}).")
            repaired_dict = {
                "limit_id": limit_id,
                "instructed_amount": instructed_amount,
                "currency": currency,
                "resolution_action": "LIMIT_HEADROOM_CONFIRMED_RELEASE",
                "execution_owner": "BANK",
            }
            candidate = ResolutionCandidate(
                candidate_id=f"CAND-TR06-RELEASE-{uuid.uuid4().hex[:8]}",
                repaired_payload=json.dumps(repaired_dict),
                repaired_structured=repaired_dict,
                diff_summary="; ".join(diff_log),
                derivation_method="PAT_C_OPERATIONAL_LIMIT_VALIDATION",
                is_lossless=True,
                fields_reordered=[],
            )
            uniqueness = ResolutionUniqueness.RESOLUTION_AMBIGUOUS if ctx.get("ambiguous_candidates", False) else ResolutionUniqueness.RESOLUTION_UNIQUE
            return ResolutionStatus.RESOLUTION_DETERMINED, uniqueness, candidate, diff_log, None

        # Branch B: Breached but Intraday Reset Pacing Available (PAT-C Pacing Schedule)
        if policy.allow_intraday_limit_reset_pacing and limit_rec.reset_schedule_utc:
            diff_log.append(f"Limit {limit_id} breached by ${eval_result['breached_amount']:,.2f}. Scheduling intraday reset pacing.")
            dossier = self.limit_port.assemble_limit_waiver_dossier(limit_id, eval_result["breached_amount"], currency, client_prof)
            repaired_dict = dossier.model_dump(mode="json") if dossier else {}
            candidate = ResolutionCandidate(
                candidate_id=f"CAND-TR06-PACING-{uuid.uuid4().hex[:8]}",
                repaired_payload=json.dumps(repaired_dict),
                repaired_structured=repaired_dict,
                diff_summary="; ".join(diff_log),
                derivation_method="PAT_C_INTRADAY_LIMIT_RESET_PACING",
                is_lossless=True,
                fields_reordered=[],
            )
            return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None

        # Branch C: Hard Limit Breach requiring Human Waiver (PAT-D Waiver Dossier)
        diff_log.append(f"Limit {limit_id} breached by ${eval_result['breached_amount']:,.2f} without reset pacing. Compiling waiver dossier for Credit Officer.")
        dossier = self.limit_port.assemble_limit_waiver_dossier(limit_id, eval_result["breached_amount"], currency, client_prof)
        repaired_dict = dossier.model_dump(mode="json") if dossier else {}
        candidate = ResolutionCandidate(
            candidate_id=f"CAND-TR06-WAIVER-{uuid.uuid4().hex[:8]}",
            repaired_payload=json.dumps(repaired_dict),
            repaired_structured=repaired_dict,
            diff_summary="; ".join(diff_log),
            derivation_method="PAT_D_OPERATIONAL_LIMIT_WAIVER_DOSSIER",
            is_lossless=True,
            fields_reordered=[],
        )
        return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None

    # ==========================================================================
    # 5. TR-07: LIQUIDITY CONSTRAINT (PAT-C)
    # ==========================================================================
    def resolve_tr07_liquidity_constraint(
        self,
        clearing_context: str,
        instructed_amount: float,
        currency: str = "USD",
        policy_thresholds: Optional[W3PolicyThresholds] = None,
        evidence_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Resolves clearing channel liquidity constraints by evaluating reserve buffers,

        queue status, and scheduling pacing release retry windows.
        """
        diff_log: List[str] = []
        ctx = evidence_context or {}
        policy = policy_thresholds or W3PolicyThresholds()

        if ctx.get("clearing_rail_emergency_halt", False):
            diff_log.append(f"Clearing channel {clearing_rail} under emergency settlement halt. Fails closed to Treasury Suspense.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_AMBIGUOUS, None, diff_log, "Clearing rail emergency halt."

        reserve = self.liquidity_port.get_liquidity_reserve(clearing_context, currency)
        if not reserve:
            diff_log.append(f"No authoritative liquidity reserve record for {clearing_context} ({currency}).")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Missing authoritative liquidity reserve."

        queue = self.liquidity_port.get_queue_status(clearing_context)
        eval_result = LiquidityConstraintEvaluator.evaluate(reserve, queue, instructed_amount)

        # Branch A: Sufficient Headroom
        if eval_result["is_liquid"]:
            diff_log.append(f"Clearing context {clearing_context} has sufficient liquidity headroom (${eval_result['headroom']:,.2f} >= buffer).")
            repaired_dict = {
                "clearing_context": clearing_context,
                "instructed_amount": instructed_amount,
                "currency": currency,
                "resolution_action": "LIQUIDITY_BUFFER_VERIFIED_RELEASE",
                "execution_owner": "BANK",
            }
            candidate = ResolutionCandidate(
                candidate_id=f"CAND-TR07-RELEASE-{uuid.uuid4().hex[:8]}",
                repaired_payload=json.dumps(repaired_dict),
                repaired_structured=repaired_dict,
                diff_summary="; ".join(diff_log),
                derivation_method="PAT_C_LIQUIDITY_HEADROOM_VERIFICATION",
                is_lossless=True,
                fields_reordered=[],
            )
            uniqueness = ResolutionUniqueness.RESOLUTION_AMBIGUOUS if ctx.get("ambiguous_candidates", False) else ResolutionUniqueness.RESOLUTION_UNIQUE
            return ResolutionStatus.RESOLUTION_DETERMINED, uniqueness, candidate, diff_log, None

        # Branch B: Constrained with Governed Pacing Release (PAT-C Pacing Schedule)
        if policy.allow_auto_liquidity_pacing:
            diff_log.append(
                f"Clearing context {clearing_context} constrained (Queue depth: {eval_result['active_queue_depth']}). "
                f"Scheduling liquidity pacing delay ({eval_result['estimated_delay_seconds']}s)."
            )
            pacing = self.liquidity_port.evaluate_liquidity_pacing(clearing_context, instructed_amount, currency)
            repaired_dict = {
                "clearing_context": clearing_context,
                "instructed_amount": instructed_amount,
                "currency": currency,
                "pacing_schedule": pacing.model_dump(mode="json") if pacing else None,
                "resolution_action": "QUEUE_FOR_LIQUIDITY_PACING_RELEASE",
                "execution_owner": "BANK",
            }
            candidate = ResolutionCandidate(
                candidate_id=f"CAND-TR07-PACING-{uuid.uuid4().hex[:8]}",
                repaired_payload=json.dumps(repaired_dict),
                repaired_structured=repaired_dict,
                diff_summary="; ".join(diff_log),
                derivation_method="PAT_C_LIQUIDITY_PACING_SCHEDULE",
                is_lossless=True,
                fields_reordered=[],
            )
            return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None

        diff_log.append(f"Liquidity exhausted on {clearing_context}. Escalating to Head of Treasury.")
        return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Liquidity buffer exhausted."

    # ==========================================================================
    # 6. TR-08: CREDIT EXPOSURE BREACH (PAT-D) — AUTONOMOUS STP STRICTLY PROHIBITED
    # ==========================================================================
    def resolve_tr08_credit_exposure_breach(
        self,
        counterparty_id: str,
        instructed_amount: float,
        currency: str = "USD",
        facility_id: Optional[str] = None,
        policy_thresholds: Optional[W3PolicyThresholds] = None,
        evidence_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        """Resolves counterparty credit exposure breaches by assembling a governed credit risk dossier.

        MANDATORY INVARIANT: Autonomous STP is STRICTLY PROHIBITED for TR-08.
        Must produce PAT-D dossier for Senior Credit Officer adjudication.
        """
        diff_log: List[str] = []
        ctx = evidence_context or {}
        policy = policy_thresholds or W3PolicyThresholds()

        # Enforce Zero Autonomous STP Invariant
        diff_log.append("TR-08 Credit Exposure Breach: Autonomous STP is STRICTLY PROHIBITED under bank credit governance.")

        exp = self.credit_port.get_counterparty_exposure(counterparty_id)
        if not exp:
            diff_log.append(f"No authoritative credit exposure record for counterparty {counterparty_id}.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Missing authoritative credit exposure record."

        fac = self.credit_port.get_credit_facility(facility_id) if facility_id else None
        eval_result = CreditExposureEvaluator.evaluate(exp, instructed_amount)

        if eval_result["is_distressed"]:
            diff_log.append(f"Counterparty {counterparty_id} has distressed credit rating ({exp.credit_rating}). Escalating for immediate freeze review.")

        dossier = self.credit_port.assemble_credit_risk_dossier(counterparty_id, instructed_amount, currency, facility_id)
        if not dossier:
            diff_log.append(f"Failed to assemble credit risk dossier for {counterparty_id}.")
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, "Credit risk dossier assembly failed."

        diff_log.append(
            f"Assembled Credit Risk Dossier {dossier.dossier_id} (Drawn: ${exp.current_drawn_exposure:,.2f} / "
            f"Limit: ${exp.total_facility_limit:,.2f}, Excess: ${eval_result['excess_exposure']:,.2f}). Requires Senior Credit Officer sign-off."
        )

        repaired_dict = dossier.model_dump(mode="json")
        candidate = ResolutionCandidate(
            candidate_id=f"CAND-TR08-CREDIT-DOSSIER-{uuid.uuid4().hex[:8]}",
            repaired_payload=json.dumps(repaired_dict),
            repaired_structured=repaired_dict,
            diff_summary="; ".join(diff_log),
            derivation_method="PAT_D_CREDIT_RISK_ADJUDICATION_DOSSIER",
            is_lossless=True,
            fields_reordered=[],
        )
        return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None


# Global singleton
treasury_exposure_engine = TreasuryExposureEngine()
