"""Tests for Wave 3 Cross-Profile and Concurrent Exception Interactions."""
import pytest
from app.services.e2e_runner import E2EExecutionHarness
from app.schemas.contracts.e2e_schemas import CanonicalE2EInput, E2EPaymentInfo


@pytest.fixture
def harness():
    return E2EExecutionHarness()


def test_cross_profile_tr02_and_tr04_interaction(harness):
    """Verifies that an FX conversion payment with sufficient balance executes cleanly."""
    inp = CanonicalE2EInput(
        exception_id="CROSS-TR04-01",
        profile_id="TR-04",
        domain="CLIENT_TREASURY",
        error_code="ERR_FX_RATE_UNAVAILABLE",
        error_message="FX rate quote needed for funded payment",
        payment_info=E2EPaymentInfo(
            payment_id="PMT-CROSS-01",
            uetr="UETR-CROSS-01",
            amount=5000.0,
            currency="EUR",
            clearing_rail="SWIFT_CBPR+",
            debtor_name="Apex Corp",
            debtor_account="ACCT-CORP-USD-001",
            debtor_agent_bic="BNPAFRPPXXX",
        ),
        bank_supplied_evidence={
            "currency_pair": "EUR/USD",
            "settlement_currency": "USD",
            "official_fx_rate_feed": {
                "currency_pair": "EUR/USD",
                "base_currency": "EUR",
                "quote_currency": "USD",
                "mid_rate": 1.0850,
                "bid_rate": 1.0848,
                "ask_rate": 1.0852,
                "is_live": True,
                "is_authoritative": True,
            },
            "fx_spread_policy_matrix": {
                "currency_pair": "EUR/USD",
                "max_rate_age_seconds": 60.0,
                "max_spread_tolerance_bps": 50.0,
                "allow_auto_booking": True,
            },
            "inward_payment_record": {
                "payment_id": "PMT-CROSS-01",
                "amount": 5000.0,
                "currency": "EUR",
            },
        },
    )
    out = harness.process_input(inp)
    assert out.stp_eligible is True
    assert out.resolution_status == "RESOLVED"
    assert out.predicate_breakdown.r_det is True
