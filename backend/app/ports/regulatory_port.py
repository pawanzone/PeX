"""Regulatory Screening Port (SPI).

Defines the abstract interface for screening parties and corridors against sanctions,
PEP, and adverse media registries.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from app.schemas.contracts.regulatory_schemas import (
    ScreeningAssessment,
)


class RegulatoryScreeningPort(ABC):
    """Abstract port for regulatory compliance screening."""

    @abstractmethod
    def screen_entity(
        self,
        entity_name: str,
        country: Optional[str] = None,
        corridor: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ScreeningAssessment:
        """Screens an entity against statutory watchlists (evaluates C_comp predicate)."""
        pass
