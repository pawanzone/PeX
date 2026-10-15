"""Legal Registry & Freeze Dossier Port (SPI-LEGAL-REGISTRY-PORT).

Defines abstract SPI for querying authoritative court orders, judicial freezes, tax levies,
and restriction scope records from Core Banking / Legal Master.
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave2_schemas import (
    AccountRestrictionScope,
    LegalFreezeDossierRecord,
    RolloverMandateRecord,
)


class LegalRegistryPort(ABC):
    """Abstract port for Legal Registry, Freeze Dossiers, and Corporate Rollover Mandates."""

    @abstractmethod
    def get_restriction_scope(self, account_number: str) -> Optional[AccountRestrictionScope]:
        """Retrieves authoritative restriction scope (e.g. Post No Credits) for an account."""
        pass

    @abstractmethod
    def get_legal_freeze_dossier(self, account_number: str) -> Optional[LegalFreezeDossierRecord]:
        """Retrieves active court order/dossier associated with account restriction."""
        pass

    @abstractmethod
    def get_rollover_mandate(
        self,
        closed_account_number: str,
        entity_id_hint: Optional[str] = None
    ) -> Optional[RolloverMandateRecord]:
        """Retrieves signed, verified corporate rollover mandate authorizing successor account."""
        pass
