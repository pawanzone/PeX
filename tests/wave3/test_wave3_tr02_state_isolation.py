"""Tests for Workstream A (W3-FOR-03 Remediation): TR-02 Candidate Derivation State Invariance.

Verifies that TreasuryExposureEngine.resolve_tr02_insufficient_funds is strictly read-only,
side-effect free, and never mutates port state, balances, or holds during candidate derivation.
"""
import pytest
from unittest.mock import MagicMock

from app.services.engines.treasury_exposure_engine import TreasuryExposureEngine
from app.adapters.reference.reference_treasury_position_adapter import InMemoryTreasuryPositionAdapter
from app.schemas.contracts.wave3_schemas import AccountBalanceRecord
from app.schemas.contracts.policy_schemas import W3PolicyThresholds
from app.schemas.resolution_contract import ResolutionStatus, ResolutionUniqueness


@pytest.fixture
def fresh_adapter():
    """Provides a fresh reference treasury position adapter with controlled balances."""
    adapter = InMemoryTreasuryPositionAdapter()
    # Explicit baseline record
    adapter.register_account_balance(
        AccountBalanceRecord(
            account_number="ACCT-TEST-ISO-001",
            currency="USD",
            ledger_balance=500000.0,
            available_balance=450000.0,
            holds_amount=50000.0,
            pending_credits=100000.0,
            is_authoritative=True,
            authority_source="CORE_BANKING_LEDGER",
        )
    )
    return adapter


@pytest.fixture
def engine(fresh_adapter):
    return TreasuryExposureEngine(treasury_port=fresh_adapter)


def test_a1_repeated_evaluation_state_invariance(engine, fresh_adapter):
    """Test A.1: Repeated Evaluation State Invariance.

    Evaluating resolve_tr02_insufficient_funds 10 consecutive times against an account
    with available balance must leave available_balance and holds_amount 100% unchanged.
    Every evaluation must deterministically return RESOLUTION_DETERMINED.
    """
    account_number = "ACCT-TEST-ISO-001"
    instructed_amount = 5000.0
    initial_balance = fresh_adapter.get_account_balance(account_number)
    initial_avail = initial_balance.available_balance
    initial_holds = initial_balance.holds_amount

    assert initial_avail == 450000.0
    assert initial_holds == 50000.0

    for i in range(10):
        status, uniq, cand, diff, err = engine.resolve_tr02_insufficient_funds(
            account_number=account_number,
            instructed_amount=instructed_amount,
            currency="USD",
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED, f"Run {i+1} failed to determine resolution"
        assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
        assert cand is not None
        assert cand.derivation_method == "PAT_C_INTRADAY_FUNDS_RESERVATION"
        assert cand.repaired_structured["resolution_action"] == "FUNDS_RESERVED_RELEASE_PAYMENT"
        assert cand.repaired_structured["execution_owner"] == "BANK"

        # Check adapter state after each iteration
        current_bal = fresh_adapter.get_account_balance(account_number)
        assert current_bal.available_balance == initial_avail, f"State mutated on iteration {i+1}"
        assert current_bal.holds_amount == initial_holds, f"Holds mutated on iteration {i+1}"


def test_a2_multi_transaction_state_independence(engine, fresh_adapter):
    """Test A.2: Multi-Transaction State Independence.

    Evaluating two independent payment candidates against an account sharing the same
    adapter instance must evaluate without the first evaluation draining funds for the second.
    """
    account_number = "ACCT-TEST-ISO-001"
    bal_before = fresh_adapter.get_account_balance(account_number)
    avail_before = bal_before.available_balance

    # Evaluation 1: $5,000
    status1, uniq1, cand1, _, _ = engine.resolve_tr02_insufficient_funds(
        account_number=account_number,
        instructed_amount=5000.0,
        currency="USD",
    )
    assert status1 == ResolutionStatus.RESOLUTION_DETERMINED
    assert cand1 is not None

    # Evaluation 2: $10,000 on shared adapter instance
    status2, uniq2, cand2, _, _ = engine.resolve_tr02_insufficient_funds(
        account_number=account_number,
        instructed_amount=10000.0,
        currency="USD",
    )
    assert status2 == ResolutionStatus.RESOLUTION_DETERMINED
    assert cand2 is not None

    # Verify adapter balance remains completely unchanged
    bal_after = fresh_adapter.get_account_balance(account_number)
    assert bal_after.available_balance == avail_before
    assert bal_after.holds_amount == bal_before.holds_amount


def test_a3_evaluation_order_invariance(engine, fresh_adapter):
    """Test A.3: Evaluation Order Invariance.

    Evaluating payment candidates of varying sizes in forward and reverse sequence
    must yield identical candidate derivation decisions and adapter balances.
    """
    account_number = "ACCT-TEST-ISO-001"
    amounts = [2000.0, 15000.0, 50000.0]

    # Forward sequence
    results_fwd = []
    for amt in amounts:
        st, uq, cd, _, _ = engine.resolve_tr02_insufficient_funds(
            account_number=account_number,
            instructed_amount=amt,
            currency="USD",
        )
        results_fwd.append((st, uq, cd.derivation_method if cd else None))

    # Reverse sequence on same adapter
    results_rev = []
    for amt in reversed(amounts):
        st, uq, cd, _, _ = engine.resolve_tr02_insufficient_funds(
            account_number=account_number,
            instructed_amount=amt,
            currency="USD",
        )
        results_rev.append((st, uq, cd.derivation_method if cd else None))

    # Assert outcomes match regardless of order
    for (fwd, rev_match) in zip(results_fwd, reversed(results_rev)):
        assert fwd == rev_match

    # Assert adapter balance is unchanged
    bal = fresh_adapter.get_account_balance(account_number)
    assert bal.available_balance == 450000.0
    assert bal.holds_amount == 50000.0


def test_a4_uninvoked_mutation_verification():
    """Test A.4: Uninvoked Mutation Verification.

    Asserts via spy/mock that reserve_intraday_funds and release_intraday_reservation
    are never invoked during candidate derivation.
    """
    mock_port = MagicMock()
    mock_port.get_account_balance.return_value = AccountBalanceRecord(
        account_number="ACCT-SPY-001",
        currency="USD",
        ledger_balance=100000.0,
        available_balance=90000.0,
        holds_amount=10000.0,
        pending_credits=0.0,
        is_authoritative=True,
        authority_source="CORE_BANKING_LEDGER",
    )

    test_engine = TreasuryExposureEngine(treasury_port=mock_port)
    status, uniq, cand, diff, err = test_engine.resolve_tr02_insufficient_funds(
        account_number="ACCT-SPY-001",
        instructed_amount=5000.0,
        currency="USD",
    )

    assert status == ResolutionStatus.RESOLUTION_DETERMINED
    assert cand is not None

    # Verified: zero invocations of state-mutating methods
    mock_port.reserve_intraday_funds.assert_not_called()
    mock_port.release_intraday_reservation.assert_not_called()
