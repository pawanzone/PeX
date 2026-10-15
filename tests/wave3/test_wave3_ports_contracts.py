"""Tests for Wave 3 SPI Abstract Ports & Reference In-Memory Adapters."""
import pytest
from app.ports import (
    TreasuryPositionPort,
    NostroPositionPort,
    FXPricingPort,
    LimitManagementPort,
    CreditRiskPort,
    LiquidityReservePort,
)
from app.adapters.reference import (
    InMemoryTreasuryPositionAdapter,
    InMemoryNostroPositionAdapter,
    InMemoryFXPricingAdapter,
    InMemoryLimitManagementAdapter,
    InMemoryCreditRiskAdapter,
    InMemoryLiquidityReserveAdapter,
)


def test_treasury_position_adapter_contract():
    adapter = InMemoryTreasuryPositionAdapter()
    assert isinstance(adapter, TreasuryPositionPort)
    bal = adapter.get_account_balance("ACCT-CORP-USD-001")
    assert bal is not None
    assert bal.available_balance == 450000.0

    # Test reservation
    res = adapter.reserve_intraday_funds("ACCT-CORP-USD-001", 10000.0)
    assert res is not None
    assert res.reservation_status == "ACTIVE"
    assert bal.available_balance == 440000.0

    # Test release
    assert adapter.release_intraday_reservation(res.reservation_id) is True
    assert bal.available_balance == 450000.0


def test_nostro_position_adapter_contract():
    adapter = InMemoryNostroPositionAdapter()
    assert isinstance(adapter, NostroPositionPort)
    pos = adapter.get_nostro_position("BNPAFRPPXXX", "EUR")
    assert pos is not None
    assert pos.currency == "EUR"

    rebal = adapter.generate_rebalancing_candidate("BNPAFRPPXXX", 100000.0, "EUR")
    assert rebal is not None
    assert rebal.rebalancing_amount >= 50000.0
    assert rebal.execution_owner == "BANK"


def test_fx_pricing_adapter_contract():
    adapter = InMemoryFXPricingAdapter()
    assert isinstance(adapter, FXPricingPort)
    quote = adapter.get_fx_rate_quote("EUR/USD")
    assert quote is not None
    assert quote.mid_rate == 1.0850

    policy = adapter.get_fx_spread_policy("EUR/USD")
    assert policy is not None
    assert policy.max_spread_tolerance_bps == 50.0

    booking = adapter.book_fx_rate("EUR/USD", 1000.0, "EUR", "USD")
    assert booking is not None
    assert booking.settlement_amount == 1085.0
    assert booking.execution_owner == "BANK"


def test_limit_management_adapter_contract():
    adapter = InMemoryLimitManagementAdapter()
    assert isinstance(adapter, LimitManagementPort)
    lim = adapter.get_limit_utilization("LIM-DAILY-CORP-01")
    assert lim is not None
    assert lim.limit_cap == 1000000.0

    dossier = adapter.assemble_limit_waiver_dossier("LIM-DAILY-CORP-01", 50000.0, "USD")
    assert dossier is not None
    assert dossier.execution_owner == "BANK"


def test_credit_risk_adapter_contract():
    adapter = InMemoryCreditRiskAdapter()
    assert isinstance(adapter, CreditRiskPort)
    exp = adapter.get_counterparty_exposure("CPTY-CORP-ALPHA")
    assert exp is not None
    assert exp.credit_rating == "AA"

    dossier = adapter.assemble_credit_risk_dossier("CPTY-CORP-ALPHA", 500000.0, "USD", "FAC-ALPHA-01")
    assert dossier is not None
    assert dossier.autonomous_stp_prohibited is True
    assert dossier.execution_owner == "BANK"


def test_liquidity_reserve_adapter_contract():
    adapter = InMemoryLiquidityReserveAdapter()
    assert isinstance(adapter, LiquidityReservePort)
    res = adapter.get_liquidity_reserve("FEDWIRE", "USD")
    assert res is not None
    assert res.current_available_liquidity == 50000000.0

    queue = adapter.get_queue_status("FEDWIRE")
    assert queue is not None
    assert queue.active_queue_depth == 5

    pacing = adapter.evaluate_liquidity_pacing("FEDWIRE", 1000000.0, "USD")
    assert pacing is not None
    assert pacing.execution_owner == "BANK"
