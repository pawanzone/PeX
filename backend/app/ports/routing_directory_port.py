"""Routing Directory & SSI Port (SPI).

Defines abstract SPI for resolving reachable clearing routes, correspondent paths,
and Standard Settlement Instructions (SSI).
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave1_schemas import (
    RouteResolutionRecord,
    SSIRecord,
)


class RoutingDirectoryPort(ABC):
    """Abstract port for Routing Directory and SSI lookups."""

    @abstractmethod
    def resolve_route(
        self,
        debtor_agent_bic: str,
        creditor_agent_bic: str,
        currency: str,
        clearing_rail: str
    ) -> Optional[RouteResolutionRecord]:
        """Resolves authoritative routing route and correspondent intermediary BIC."""
        pass

    @abstractmethod
    def get_ssi(
        self,
        bic_or_clearing_id: str,
        currency: str
    ) -> Optional[SSIRecord]:
        """Retrieves authoritative Standard Settlement Instructions (SSI)."""
        pass

    @abstractmethod
    def validate_clearing_identifier(
        self,
        routing_code: str,
        rail: str
    ) -> bool:
        """Validates clearing routing identifier syntax and active directory presence."""
        pass
