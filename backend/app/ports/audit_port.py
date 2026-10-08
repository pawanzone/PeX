"""Audit Ledger Port (SPI).

Defines the abstract interface for cryptographically committing audit events into
an immutable, tamper-evident hash chain.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from app.schemas.contracts.audit_schemas import (
    AuditBlockPayload,
    AuditBlockReceipt,
)


class AuditLedgerPort(ABC):
    """Abstract port for tamper-evident audit logging."""

    @abstractmethod
    def append_event(
        self,
        payload: AuditBlockPayload
    ) -> AuditBlockReceipt:
        """Appends an event to the cryptographically linked audit chain."""
        pass

    @abstractmethod
    def verify_integrity(self, case_id: Optional[str] = None) -> bool:
        """Verifies the hash chain integrity from genesis block to current head."""
        pass

    @abstractmethod
    def get_events_for_case(self, case_id: str) -> List[AuditBlockReceipt]:
        """Retrieves all immutable audit blocks recorded for a case."""
        pass
