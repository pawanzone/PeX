"""General Ledger Suspense Port (SPI-GENERAL-LEDGER-SUSPENSE).

Defines abstract SPI for booking balanced internal settlement suspense and legal escrow journal breaks.
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave2_schemas import SettlementSuspenseBreakRecord


class GeneralLedgerSuspensePort(ABC):
    """Abstract port for internal Bank General Ledger Suspense / Escrow booking."""

    @abstractmethod
    def create_suspense_break(
        self,
        uetr: str,
        amount: float,
        currency: str,
        suspense_gl_account: str,
        escrow_reference_case: str,
        source_nostro_account: Optional[str] = None
    ) -> SettlementSuspenseBreakRecord:
        """Constructs balanced double-entry journal break for internal bank suspense booking."""
        pass

    @abstractmethod
    def validate_journal_balance(self, record: SettlementSuspenseBreakRecord) -> bool:
        """Verifies that debits equal credits in the journal break."""
        pass
