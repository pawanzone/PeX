"""FX Pricing & Market Rate Port (SPI).

Defines abstract SPI for fetching authoritative FX market quotes, verifying spread policies,
and booking FX conversion candidates for TR-04 (FX Rate Unavailable).
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave3_schemas import (
    FXRateQuoteRecord,
    FXSpreadPolicyRecord,
    FXBookingCandidate,
)


class FXPricingPort(ABC):
    """Abstract port for FX Pricing and Market Data operations."""

    @abstractmethod
    def get_fx_rate_quote(self, currency_pair: str) -> Optional[FXRateQuoteRecord]:
        """Retrieves authoritative FX market rate quote from pricing source."""
        pass

    @abstractmethod
    def get_fx_spread_policy(self, currency_pair: str) -> Optional[FXSpreadPolicyRecord]:
        """Retrieves configured bank spread and freshness tolerances."""
        pass

    @abstractmethod
    def book_fx_rate(
        self,
        currency_pair: str,
        instructed_amount: float,
        instructed_currency: str,
        settlement_currency: str,
    ) -> Optional[FXBookingCandidate]:
        """Generates a candidate FX booking package with verified rates."""
        pass
