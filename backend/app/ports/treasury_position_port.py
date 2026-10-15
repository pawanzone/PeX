"""Treasury Position & Balance Management Port (SPI).

Defines abstract SPI for querying core account balance, reserving intraday funds,
and generating governed pacing schedules for TR-02 (Insufficient Funds).
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave3_schemas import (
    AccountBalanceRecord,
    IntradayReservationRecord,
    TreasuryPacingSchedule,
)


class TreasuryPositionPort(ABC):
    """Abstract port for Treasury Position and Account Balance lookups."""

    @abstractmethod
    def get_account_balance(self, account_number: str) -> Optional[AccountBalanceRecord]:
        """Retrieves authoritative account balance from Core Ledger / DDA."""
        pass

    @abstractmethod
    def reserve_intraday_funds(
        self, account_number: str, amount: float, currency: str = "USD"
    ) -> Optional[IntradayReservationRecord]:
        """Places an intraday reservation hold on available funds."""
        pass

    @abstractmethod
    def release_intraday_reservation(self, reservation_id: str) -> bool:
        """Releases an active intraday reservation."""
        pass

    @abstractmethod
    def calculate_pacing_retry(
        self, account_number: str, required_amount: float, profile: str = "TR-02"
    ) -> TreasuryPacingSchedule:
        """Derives a governed pacing retry schedule when intraday cash is expected."""
        pass
