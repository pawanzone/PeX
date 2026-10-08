"""Core Banking DDA & Ledger Port (SPI).

Defines the abstract interface for querying real-time account balances, freeze status,
and account ownership. Read-only queries; PeX never directly mutates core banking ledgers.
"""
from abc import ABC, abstractmethod
from typing import Optional
from app.schemas.contracts.core_banking_schemas import AccountStateSnapshot


class CoreBankingDDAPort(ABC):
    """Abstract port for Core Banking DDA lookups."""

    @abstractmethod
    def get_account_state(
        self,
        account_number_or_iban: str,
        currency: Optional[str] = None
    ) -> AccountStateSnapshot:
        """Retrieves authoritative real-time account status and balance from Core DDA."""
        pass

    @abstractmethod
    def verify_account_exists(
        self,
        account_number_or_iban: str
    ) -> bool:
        """Verifies if an account number exists in Core Banking."""
        pass
