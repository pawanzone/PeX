"""Regulatory Directory Port (SPI).

Defines abstract SPI for regulatory purpose code rules, central bank BoP codes,
and deriving statutory reporting declarations (CO-07).
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave1_schemas import (
    BoPReportingCodeRecord,
    RegulatoryPurposeRule,
    RegulatoryReportingDerivationResult,
)


class RegulatoryDirectoryPort(ABC):
    """Abstract port for Regulatory Directory & Balance of Payments lookups."""

    @abstractmethod
    def get_purpose_code_rules(
        self,
        destination_country: str,
        currency: str,
        amount: float
    ) -> List[RegulatoryPurposeRule]:
        """Retrieves mandatory regulatory purpose rules for corridor and amount."""
        pass

    @abstractmethod
    def resolve_bop_code(
        self,
        trade_category: str,
        corridor: str
    ) -> Optional[BoPReportingCodeRecord]:
        """Resolves central bank Balance of Payments (BoP) reporting code."""
        pass

    @abstractmethod
    def derive_regulatory_reporting(
        self,
        transaction_context: Dict[str, Any]
    ) -> RegulatoryReportingDerivationResult:
        """Deterministically derives statutory reporting tags (<RgltryRptg>) from context."""
        pass
