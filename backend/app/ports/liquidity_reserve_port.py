"""Liquidity Reserve & Clearing Queue Port (SPI).

Defines abstract SPI for evaluating real-time clearing liquidity reserves, queue status,
and scheduling liquidity pacing for TR-07 (Liquidity Constraint).
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave3_schemas import (
    LiquidityReserveRecord,
    QueueStatusRecord,
    TreasuryPacingSchedule,
)


class LiquidityReservePort(ABC):
    """Abstract port for Liquidity Reserve and Clearing Queue Management."""

    @abstractmethod
    def get_liquidity_reserve(
        self, clearing_context: str, currency: str = "USD"
    ) -> Optional[LiquidityReserveRecord]:
        """Retrieves authoritative clearing liquidity reserve and headroom."""
        pass

    @abstractmethod
    def get_queue_status(self, clearing_context: str) -> Optional[QueueStatusRecord]:
        """Retrieves current queue depth and estimated release delay."""
        pass

    @abstractmethod
    def evaluate_liquidity_pacing(
        self, clearing_context: str, requested_amount: float, currency: str = "USD"
    ) -> Optional[TreasuryPacingSchedule]:
        """Calculates a governed liquidity pacing retry window."""
        pass
