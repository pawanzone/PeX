"""In-Memory Reference Liquidity Reserve & Clearing Queue Adapter.

TEST / REFERENCE ONLY (NON-PRODUCTION).
Implements LiquidityReservePort (SPI-LIQUIDITY-RESERVE).
Zero vendor SDK dependencies. Provider-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from app.ports.liquidity_reserve_port import LiquidityReservePort
from app.schemas.contracts.wave3_schemas import (
    LiquidityReserveRecord,
    QueueStatusRecord,
    TreasuryPacingSchedule,
)


class InMemoryLiquidityReserveAdapter(LiquidityReservePort):
    """Hermetic reference implementation of LiquidityReservePort."""

    def __init__(
        self,
        reserves: Optional[Dict[str, LiquidityReserveRecord]] = None,
        queues: Optional[Dict[str, QueueStatusRecord]] = None,
    ):
        self._reserves: Dict[str, LiquidityReserveRecord] = reserves or {
            "FEDWIRE:USD": LiquidityReserveRecord(
                clearing_context="FEDWIRE",
                currency="USD",
                current_available_liquidity=50000000.0,
                minimum_buffer_target=10000000.0,
                headroom=40000000.0,
                is_constrained=False,
                is_authoritative=True,
                authority_source="LIQUIDITY_MANAGEMENT_SYSTEM",
            ),
            "TARGET2:EUR": LiquidityReserveRecord(
                clearing_context="TARGET2",
                currency="EUR",
                current_available_liquidity=1200000.0,
                minimum_buffer_target=2000000.0,
                headroom=-800000.0,
                is_constrained=True,
                is_authoritative=True,
                authority_source="LIQUIDITY_MANAGEMENT_SYSTEM",
            ),
            "CHAPS:GBP": LiquidityReserveRecord(
                clearing_context="CHAPS",
                currency="GBP",
                current_available_liquidity=5000000.0,
                minimum_buffer_target=1000000.0,
                headroom=4000000.0,
                is_constrained=False,
                is_authoritative=True,
                authority_source="LIQUIDITY_MANAGEMENT_SYSTEM",
            ),
        }
        self._queues: Dict[str, QueueStatusRecord] = queues or {
            "FEDWIRE": QueueStatusRecord(
                queue_id="Q-FEDWIRE-USD",
                clearing_context="FEDWIRE",
                active_queue_depth=5,
                priority_tier="STANDARD",
                estimated_release_delay_seconds=30.0,
            ),
            "TARGET2": QueueStatusRecord(
                queue_id="Q-TARGET2-EUR",
                clearing_context="TARGET2",
                active_queue_depth=42,
                priority_tier="HOLD",
                estimated_release_delay_seconds=600.0,
            ),
        }

    def get_liquidity_reserve(
        self, clearing_context: str, currency: str = "USD"
    ) -> Optional[LiquidityReserveRecord]:
        key = f"{clearing_context.strip().upper()}:{currency.strip().upper()}"
        return self._reserves.get(key)

    def register_liquidity_reserve(self, record: LiquidityReserveRecord) -> None:
        key = f"{record.clearing_context.upper()}:{record.currency.upper()}"
        self._reserves[key] = record

    def get_queue_status(self, clearing_context: str) -> Optional[QueueStatusRecord]:
        return self._queues.get(clearing_context.strip().upper())

    def evaluate_liquidity_pacing(
        self, clearing_context: str, requested_amount: float, currency: str = "USD"
    ) -> Optional[TreasuryPacingSchedule]:
        res = self.get_liquidity_reserve(clearing_context, currency)
        queue = self.get_queue_status(clearing_context)
        delay = queue.estimated_release_delay_seconds if queue else 300.0

        return TreasuryPacingSchedule(
            schedule_id=f"PACE-LIQ-{uuid.uuid4().hex[:6].upper()}",
            target_profile="TR-07",
            pacing_interval_seconds=max(delay, 180.0),
            max_retry_attempts=3,
            current_attempt=1,
            pacing_reason=f"Pacing queue delay of {delay}s for clearing context {clearing_context}",
            execution_owner="BANK",
        )
