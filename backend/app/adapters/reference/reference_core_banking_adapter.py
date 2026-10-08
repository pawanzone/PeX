"""In-Memory Reference Core Banking DDA Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements CoreBankingDDAPort with simulated account database and freeze ledgers.
Read-only queries; PeX never directly mutates core banking ledgers.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.ports.core_banking_port import CoreBankingDDAPort
from app.schemas.contracts.core_banking_schemas import (
    AccountStateSnapshot,
    AccountStatus,
)


class InMemoryCoreBankingDDAAdapter(CoreBankingDDAPort):
    """Hermetic reference implementation of CoreBankingDDAPort."""

    def __init__(self):
        self._accounts: Dict[str, AccountStateSnapshot] = {
            "US11APEX9988770100": AccountStateSnapshot(
                account_number_masked="US11****0100",
                iban_masked="US11APEX9988770100",
                account_holder_name_masked="Apex Global Treasury (US)",
                currency="USD",
                status=AccountStatus.ACTIVE,
                available_balance=5000000.0,
                posted_balance=5000000.0,
                credit_limit=1000000.0
            ),
            "GB82WEST12345698760100": AccountStateSnapshot(
                account_number_masked="GB82****0100",
                iban_masked="GB82WEST12345698760100",
                account_holder_name_masked="HarborView Supplier Ltd",
                currency="GBP",
                status=AccountStatus.ACTIVE,
                available_balance=750000.0,
                posted_balance=750000.0
            ),
            "FROZEN_ACCOUNT_999": AccountStateSnapshot(
                account_number_masked="FROZ****0999",
                account_holder_name_masked="Sanctioned Counterparty Corp",
                currency="USD",
                status=AccountStatus.FROZEN_SANCTIONS,
                available_balance=0.0,
                posted_balance=120000.0,
                is_frozen=True,
                freeze_reason="OFAC SDN List Match 2026-03"
            ),
            "CLOSED_ACCOUNT_888": AccountStateSnapshot(
                account_number_masked="CLOS****0888",
                account_holder_name_masked="Defunct Commercial Client",
                currency="USD",
                status=AccountStatus.CLOSED,
                available_balance=0.0,
                posted_balance=0.0
            )
        }

    def register_account(self, key: str, snapshot: AccountStateSnapshot):
        self._accounts[key] = snapshot

    def get_account_state(
        self,
        account_number_or_iban: str,
        currency: Optional[str] = None
    ) -> AccountStateSnapshot:
        if account_number_or_iban in self._accounts:
            return self._accounts[account_number_or_iban]
        
        # Default mock active account for test suite
        return AccountStateSnapshot(
            account_number_masked=f"{account_number_or_iban[:4]}****{account_number_or_iban[-4:]}" if len(account_number_or_iban) >= 8 else "ACCT****MASK",
            account_holder_name_masked="Standard Commercial Entity",
            currency=currency or "USD",
            status=AccountStatus.ACTIVE,
            available_balance=100000.0,
            posted_balance=100000.0
        )

    def verify_account_exists(
        self,
        account_number_or_iban: str
    ) -> bool:
        if account_number_or_iban in self._accounts:
            return self._accounts[account_number_or_iban].status != AccountStatus.NOT_FOUND
        return True
