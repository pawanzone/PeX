"""In-Memory Reference FX Pricing & Market Rate Adapter.

TEST / REFERENCE ONLY (NON-PRODUCTION).
Implements FXPricingPort (SPI-FX-PRICING).
Zero vendor SDK dependencies. Provider-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid

from app.ports.fx_pricing_port import FXPricingPort
from app.schemas.contracts.wave3_schemas import (
    FXRateQuoteRecord,
    FXSpreadPolicyRecord,
    FXBookingCandidate,
)


class InMemoryFXPricingAdapter(FXPricingPort):
    """Hermetic reference implementation of FXPricingPort."""

    def __init__(
        self,
        quotes: Optional[Dict[str, FXRateQuoteRecord]] = None,
        policies: Optional[Dict[str, FXSpreadPolicyRecord]] = None,
    ):
        now = datetime.now(timezone.utc)
        self._quotes: Dict[str, FXRateQuoteRecord] = quotes or {
            "EUR/USD": FXRateQuoteRecord(
                currency_pair="EUR/USD",
                base_currency="EUR",
                quote_currency="USD",
                mid_rate=1.0850,
                bid_rate=1.0848,
                ask_rate=1.0852,
                quote_timestamp=now,
                is_live=True,
                is_authoritative=True,
                quote_source="OFFICIAL_FX_PRICING_ENGINE",
            ),
            "GBP/USD": FXRateQuoteRecord(
                currency_pair="GBP/USD",
                base_currency="GBP",
                quote_currency="USD",
                mid_rate=1.2750,
                bid_rate=1.2747,
                ask_rate=1.2753,
                quote_timestamp=now,
                is_live=True,
                is_authoritative=True,
                quote_source="OFFICIAL_FX_PRICING_ENGINE",
            ),
            "USD/JPY": FXRateQuoteRecord(
                currency_pair="USD/JPY",
                base_currency="USD",
                quote_currency="JPY",
                mid_rate=155.20,
                bid_rate=155.18,
                ask_rate=155.22,
                quote_timestamp=now - timedelta(seconds=120),  # Stale rate fixture
                is_live=True,
                is_authoritative=True,
                quote_source="OFFICIAL_FX_PRICING_ENGINE",
            ),
        }
        self._policies: Dict[str, FXSpreadPolicyRecord] = policies or {
            "EUR/USD": FXSpreadPolicyRecord(
                currency_pair="EUR/USD",
                max_rate_age_seconds=60.0,
                max_spread_tolerance_bps=50.0,
                allow_auto_booking=True,
            ),
            "GBP/USD": FXSpreadPolicyRecord(
                currency_pair="GBP/USD",
                max_rate_age_seconds=60.0,
                max_spread_tolerance_bps=50.0,
                allow_auto_booking=True,
            ),
            "USD/JPY": FXSpreadPolicyRecord(
                currency_pair="USD/JPY",
                max_rate_age_seconds=60.0,
                max_spread_tolerance_bps=50.0,
                allow_auto_booking=True,
            ),
        }

    def get_fx_rate_quote(self, currency_pair: str) -> Optional[FXRateQuoteRecord]:
        pair = currency_pair.strip().upper()
        quote = self._quotes.get(pair)
        if quote and quote.is_live and quote.currency_pair in ["EUR/USD", "GBP/USD"]:
            # Keep simulated live feed fresh for long test runs unless deliberately made stale
            if (datetime.now(timezone.utc) - quote.quote_timestamp).total_seconds() > 30.0:
                quote = quote.model_copy(update={"quote_timestamp": datetime.now(timezone.utc)})
                self._quotes[pair] = quote
        return quote

    def register_fx_quote(self, quote: FXRateQuoteRecord) -> None:
        self._quotes[quote.currency_pair.upper()] = quote

    def get_fx_spread_policy(self, currency_pair: str) -> Optional[FXSpreadPolicyRecord]:
        pair = currency_pair.strip().upper()
        return self._policies.get(pair)

    def book_fx_rate(
        self,
        currency_pair: str,
        instructed_amount: float,
        instructed_currency: str,
        settlement_currency: str,
    ) -> Optional[FXBookingCandidate]:
        quote = self.get_fx_rate_quote(currency_pair)
        policy = self.get_fx_spread_policy(currency_pair)
        if not quote or not policy:
            return None

        # Check freshness
        age_seconds = (datetime.now(timezone.utc) - quote.quote_timestamp).total_seconds()
        if age_seconds > policy.max_rate_age_seconds:
            return None  # Stale rate fails closed

        # Settlement calculation
        applied_rate = quote.mid_rate
        if instructed_currency.upper() == quote.base_currency:
            settlement_amount = round(instructed_amount * applied_rate, 2)
        else:
            settlement_amount = round(instructed_amount / applied_rate, 2)

        return FXBookingCandidate(
            booking_id=f"FXBOOK-{uuid.uuid4().hex[:8].upper()}",
            currency_pair=currency_pair.upper(),
            applied_rate=applied_rate,
            instructed_amount=instructed_amount,
            instructed_currency=instructed_currency.upper(),
            settlement_amount=settlement_amount,
            settlement_currency=settlement_currency.upper(),
            quote_timestamp=quote.quote_timestamp,
            execution_owner="BANK",
        )
