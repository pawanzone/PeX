"""Unit Tests for TreasuryExposureEngine and Capability Evaluators (Wave 3)."""
import pytest
from datetime import datetime, timezone, timedelta

from app.services.engines.treasury_exposure_engine import (
    TreasuryExposureEngine,
    AvailableBalanceEvaluator,
    NostroPositionEvaluator,
    FXRatePricingEvaluator,
    OperationalLimitEvaluator,
    CreditExposureEvaluator,
    LiquidityConstraintEvaluator,
    PacingRetryCandidateDeriver,
    FundingCandidatePackager,
    RiskDossierAssembler,
    TemporalCorrelationEvaluator,
)
from app.schemas.contracts.policy_schemas import W3PolicyThresholds
from app.schemas.contracts.wave3_schemas import (
    AccountBalanceRecord,
    NostroPositionRecord,
    PendingCorrespondentCreditRecord,
    FXRateQuoteRecord,
    FXSpreadPolicyRecord,
    LimitUtilizationRecord,
    LimitType,
    LiquidityReserveRecord,
    QueueStatusRecord,
    CounterpartyExposureRecord,
    CreditFacilityRecord,
)
from app.schemas.resolution_contract import ResolutionStatus, ResolutionUniqueness


@pytest.fixture
def engine():
    return TreasuryExposureEngine()


# ==============================================================================
# 1. CAPABILITY EVALUATOR UNIT TESTS
# ==============================================================================

def test_available_balance_evaluator():
    rec = AccountBalanceRecord(
        account_number="ACCT-TEST-01",
        ledger_balance=100000.0,
        available_balance=80000.0,
        pending_credits=30000.0,
    )
    # Covered
    res1 = AvailableBalanceEvaluator.evaluate(rec, 50000.0)
    assert res1["is_covered"] is True
    assert res1["deficit"] == 0.0

    # Deficit but covered with pending
    res2 = AvailableBalanceEvaluator.evaluate(rec, 95000.0)
    assert res2["is_covered"] is False
    assert res2["deficit"] == 15000.0
    assert res2["can_cover_with_pending"] is True


def test_nostro_position_evaluator():
    pos = NostroPositionRecord(
        nostro_bic="BNPAFRPPXXX",
        currency="EUR",
        available_balance=50000.0,
        ledger_balance=100000.0,
        minimum_operating_target=20000.0,
    )
    pending = [
        PendingCorrespondentCreditRecord(
            credit_reference="CR-01",
            target_nostro_bic="BNPAFRPPXXX",
            currency="EUR",
            expected_amount=200000.0,
        )
    ]
    res = NostroPositionEvaluator.evaluate(pos, 150000.0, pending)
    assert res["is_covered"] is False
    assert res["deficit"] == 100000.0
    assert res["can_cover_with_pending"] is True


def test_fx_rate_pricing_evaluator():
    now = datetime.now(timezone.utc)
    quote = FXRateQuoteRecord(
        currency_pair="EUR/USD",
        base_currency="EUR",
        quote_currency="USD",
        mid_rate=1.0850,
        bid_rate=1.0848,
        ask_rate=1.0852,
        quote_timestamp=now,
    )
    policy = FXSpreadPolicyRecord(
        currency_pair="EUR/USD",
        max_rate_age_seconds=60.0,
        max_spread_tolerance_bps=50.0,
    )
    res = FXRatePricingEvaluator.evaluate(quote, policy, now)
    assert res["is_valid"] is True
    assert res["is_fresh"] is True
    assert res["is_spread_acceptable"] is True

    # Stale quote
    stale_quote = quote.model_copy(update={"quote_timestamp": now - timedelta(seconds=120)})
    res_stale = FXRatePricingEvaluator.evaluate(stale_quote, policy, now)
    assert res_stale["is_fresh"] is False
    assert res_stale["is_valid"] is False


def test_operational_limit_evaluator():
    lim = LimitUtilizationRecord(
        limit_id="LIM-01",
        limit_type=LimitType.DAILY_ACCOUNT_LIMIT,
        limit_cap=1000000.0,
        current_utilization=900000.0,
    )
    res_ok = OperationalLimitEvaluator.evaluate(lim, 50000.0)
    assert res_ok["is_within_limit"] is True
    assert res_ok["headroom"] == 100000.0

    res_breach = OperationalLimitEvaluator.evaluate(lim, 150000.0)
    assert res_breach["is_within_limit"] is False
    assert res_breach["breached_amount"] == 50000.0


def test_credit_exposure_evaluator():
    exp = CounterpartyExposureRecord(
        counterparty_id="CPTY-01",
        credit_rating="AA",
        total_facility_limit=5000000.0,
        current_drawn_exposure=4800000.0,
    )
    res = CreditExposureEvaluator.evaluate(exp, 400000.0)
    assert res["is_within_facility"] is False
    assert res["excess_exposure"] == 200000.0
    assert res["is_distressed"] is False


def test_liquidity_constraint_evaluator():
    reserve = LiquidityReserveRecord(
        clearing_context="FEDWIRE",
        currency="USD",
        current_available_liquidity=20000000.0,
        minimum_buffer_target=5000000.0,
        headroom=15000000.0,
    )
    queue = QueueStatusRecord(
        queue_id="Q-FEDWIRE",
        clearing_context="FEDWIRE",
        active_queue_depth=3,
        estimated_release_delay_seconds=15.0,
    )
    res = LiquidityConstraintEvaluator.evaluate(reserve, queue, 1000000.0)
    assert res["is_liquid"] is True
    assert res["active_queue_depth"] == 3


# ==============================================================================
# 2. PROFILE RESOLUTION UNIT TESTS
# ==============================================================================

def test_resolve_tr02_insufficient_funds_release(engine):
    status, uniq, cand, diff, err = engine.resolve_tr02_insufficient_funds(
        account_number="ACCT-CORP-USD-001",
        instructed_amount=5000.0,
        currency="USD",
    )
    assert status == ResolutionStatus.RESOLUTION_DETERMINED
    assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
    assert cand is not None
    assert cand.derivation_method == "PAT_C_INTRADAY_FUNDS_RESERVATION"


def test_resolve_tr02_insufficient_funds_pacing(engine):
    status, uniq, cand, diff, err = engine.resolve_tr02_insufficient_funds(
        account_number="ACCT-PACING-USD-003",
        instructed_amount=25000.0,
        currency="USD",
    )
    assert status == ResolutionStatus.RESOLUTION_DETERMINED
    assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
    assert cand is not None
    assert cand.derivation_method == "PAT_C_INTRADAY_PACING_SCHEDULE"


def test_resolve_tr02_insufficient_funds_deficit_fail_closed(engine):
    status, uniq, cand, diff, err = engine.resolve_tr02_insufficient_funds(
        account_number="ACCT-DEFICIT-USD-002",
        instructed_amount=50000.0,
        currency="USD",
    )
    assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
    assert cand is None


def test_resolve_tr03_nostro_shortfall_sweep(engine):
    status, uniq, cand, diff, err = engine.resolve_tr03_nostro_shortfall(
        nostro_bic="BNPAFRPPXXX",
        instructed_amount=100000.0,
        currency="EUR",
    )
    assert status == ResolutionStatus.RESOLUTION_DETERMINED
    assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
    assert cand is not None
    assert cand.derivation_method == "PAT_C_NOSTRO_LIQUIDITY_REBALANCING"


def test_resolve_tr04_fx_rate_unavailable_booking(engine):
    status, uniq, cand, diff, err = engine.resolve_tr04_fx_rate_unavailable(
        currency_pair="EUR/USD",
        instructed_amount=10000.0,
        instructed_currency="EUR",
        settlement_currency="USD",
    )
    assert status == ResolutionStatus.RESOLUTION_DETERMINED
    assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
    assert cand is not None
    assert cand.derivation_method == "PAT_C_FX_MARKET_RATE_BOOKING"


def test_resolve_tr06_limit_breach_pacing(engine):
    status, uniq, cand, diff, err = engine.resolve_tr06_limit_breach(
        limit_id="LIM-BREACHED-01",
        client_id="CLI-CORP-001",
        account_number="ACCT-CORP-USD-001",
        instructed_amount=25000.0,
        currency="USD",
    )
    assert status == ResolutionStatus.RESOLUTION_DETERMINED
    assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
    assert cand is not None
    assert cand.derivation_method == "PAT_C_INTRADAY_LIMIT_RESET_PACING"


def test_resolve_tr07_liquidity_constraint_pacing(engine):
    status, uniq, cand, diff, err = engine.resolve_tr07_liquidity_constraint(
        clearing_context="TARGET2",
        instructed_amount=500000.0,
        currency="EUR",
    )
    assert status == ResolutionStatus.RESOLUTION_DETERMINED
    assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
    assert cand is not None
    assert cand.derivation_method == "PAT_C_LIQUIDITY_PACING_SCHEDULE"


def test_resolve_tr08_credit_exposure_breach_dossier(engine):
    status, uniq, cand, diff, err = engine.resolve_tr08_credit_exposure_breach(
        counterparty_id="CPTY-CORP-ALPHA",
        instructed_amount=750000.0,
        currency="USD",
    )
    assert status == ResolutionStatus.RESOLUTION_DETERMINED
    assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
    assert cand is not None
    assert cand.derivation_method == "PAT_D_CREDIT_RISK_ADJUDICATION_DOSSIER"
    # Strict Invariant: Autonomous STP is prohibited
    assert cand.repaired_structured.get("autonomous_stp_prohibited") is True
    assert cand.repaired_structured.get("execution_owner") == "BANK"
