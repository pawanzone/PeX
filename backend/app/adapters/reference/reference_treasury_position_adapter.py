"""In-Memory Reference Treasury Position & Balance Adapter.

TEST / REFERENCE ONLY (NON-PRODUCTION).
Implements TreasuryPositionPort (SPI-TREASURY-POSITION).
Zero vendor SDK dependencies. Provider-neutral.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from app.ports.treasury_position_port import TreasuryPositionPort
from app.schemas.contracts.wave3_schemas import (
    AccountBalanceRecord,
    IntradayReservationRecord,
    TreasuryPacingSchedule,
)


class InMemoryTreasuryPositionAdapter(TreasuryPositionPort):
    """Hermetic reference implementation of TreasuryPositionPort."""

    def __init__(
        self,
        balances: Optional[Dict[str, AccountBalanceRecord]] = None,
        reservations: Optional[Dict[str, IntradayReservationRecord]] = None,
    ):
        self._balances: Dict[str, AccountBalanceRecord] = balances or {
            "ACCT-CORP-USD-001": AccountBalanceRecord(
                account_number="ACCT-CORP-USD-001",
                currency="USD",
                ledger_balance=500000.0,
                available_balance=450000.0,
                holds_amount=50000.0,
                pending_credits=100000.0,
                is_authoritative=True,
                authority_source="CORE_BANKING_LEDGER",
            ),
            "ACCT-DEFICIT-USD-002": AccountBalanceRecord(
                account_number="ACCT-DEFICIT-USD-002",
                currency="USD",
                ledger_balance=2500.0,
                available_balance=500.0,
                holds_amount=2000.0,
                pending_credits=0.0,
                is_authoritative=True,
                authority_source="CORE_BANKING_LEDGER",
            ),
            "ACCT-PACING-USD-003": AccountBalanceRecord(
                account_number="ACCT-PACING-USD-003",
                currency="USD",
                ledger_balance=10000.0,
                available_balance=2000.0,
                holds_amount=8000.0,
                pending_credits=50000.0,  # Expected clearing credit
                is_authoritative=True,
                authority_source="CORE_BANKING_LEDGER",
            ),
        }
        self._reservations: Dict[str, IntradayReservationRecord] = reservations or {}

    def get_account_balance(self, account_number: str) -> Optional[AccountBalanceRecord]:
        acct = account_number.strip()
        return self._balances.get(acct)

    def register_account_balance(self, record: AccountBalanceRecord) -> None:
        self._balances[record.account_number] = record

    def reserve_intraday_funds(
        self, account_number: str, amount: float, currency: str = "USD"
    ) -> Optional[IntradayReservationRecord]:
        bal = self.get_account_balance(account_number)
        if not bal or bal.available_balance < amount:
            return None
        res_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
        res = IntradayReservationRecord(
            reservation_id=res_id,
            account_number=account_number,
            reserved_amount=amount,
            currency=currency,
            reservation_status="ACTIVE",
        )
        self._reservations[res_id] = res
        bal.available_balance -= amount
        bal.holds_amount += amount
        return res

    def release_intraday_reservation(self, reservation_id: str) -> bool:
        if reservation_id in self._reservations:
            res = self._reservations[reservation_id]
            res.reservation_status = "RELEASED"
            bal = self.get_account_balance(res.account_number)
            if bal:
                bal.available_balance += res.reserved_amount
                bal.holds_amount -= res.reserved_amount
            return True
        return False

    def calculate_pacing_retry(
        self, account_number: str, required_amount: float, profile: str = "TR-02"
    ) -> TreasuryPacingSchedule:
        bal = self.get_account_balance(account_number)
        pacing_interval = 300.0  # Default 5 minutes
        if bal and bal.pending_credits >= required_amount:
            pacing_interval = 180.0  # Accelerated retry if pending credits cover required amount

        return TreasuryPacingSchedule(
            schedule_id=f"PACE-{uuid.uuid4().hex[:8].upper()}",
            target_profile=profile,
            pacing_interval_seconds=pacing_interval,
            max_retry_attempts=3,
            current_attempt=1,
            pacing_reason="Intraday pacing schedule for pending credit settlement",
            execution_owner="BANK",
        )
