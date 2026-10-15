"""Credit Risk & Counterparty Exposure Port (SPI).

Defines abstract SPI for retrieving counterparty exposure records, facility agreements,
and assembling credit risk dossiers for TR-08 (Credit Exposure Breach).
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave3_schemas import (
    CounterpartyExposureRecord,
    CreditFacilityRecord,
    CreditRiskDossierRecord,
    CreditDecisionRecord,
)


class CreditRiskPort(ABC):
    """Abstract port for Credit Risk and Exposure Management."""

    @abstractmethod
    def get_counterparty_exposure(
        self, counterparty_id: str
    ) -> Optional[CounterpartyExposureRecord]:
        """Retrieves authoritative counterparty exposure from enterprise risk system."""
        pass

    @abstractmethod
    def get_credit_facility(self, facility_id: str) -> Optional[CreditFacilityRecord]:
        """Retrieves credit facility parameters and collateral terms."""
        pass

    @abstractmethod
    def assemble_credit_risk_dossier(
        self,
        counterparty_id: str,
        requested_amount: float,
        currency: str,
        facility_id: Optional[str] = None,
    ) -> Optional[CreditRiskDossierRecord]:
        """Assembles governed credit risk dossier for mandatory human officer adjudication."""
        pass
