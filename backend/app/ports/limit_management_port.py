"""Limit Management & Operational Controls Port (SPI).

Defines abstract SPI for evaluating operational transaction limits, checking client profiles,
and compiling waiver dossiers for TR-06 (Limit Breach).
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave3_schemas import (
    LimitUtilizationRecord,
    ClientLimitProfileRecord,
    OperationalLimitWaiverDossier,
)


class LimitManagementPort(ABC):
    """Abstract port for Limit Management and Operational Controls."""

    @abstractmethod
    def get_limit_utilization(self, limit_id: str) -> Optional[LimitUtilizationRecord]:
        """Retrieves authoritative limit utilization and headroom."""
        pass

    @abstractmethod
    def get_client_limit_profile(
        self, client_id: str, account_number: str
    ) -> Optional[ClientLimitProfileRecord]:
        """Retrieves client standing limit and overdraft configuration."""
        pass

    @abstractmethod
    def assemble_limit_waiver_dossier(
        self,
        limit_id: str,
        breached_amount: float,
        currency: str,
        client_profile: Optional[ClientLimitProfileRecord] = None,
    ) -> Optional[OperationalLimitWaiverDossier]:
        """Assembles governed waiver dossier for Human-in-the-Loop review."""
        pass
