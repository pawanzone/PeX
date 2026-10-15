"""Transit Tracker Port (SPI-TRANSIT-TRACKER).

Defines abstract SPI for SWIFT gpi transit break telemetry and correspondent inquiry packaging.
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.schemas.contracts.wave4_schemas import (
    CorrespondentTrackerHopRecord,
    DebitConfirmationRecord,
    TransitInquiryPolicyRecord,
    TransitInvestigationCandidate,
)


class TransitTrackerPort(ABC):
    """Abstract port for correspondent transit tracking and inquiry generation."""

    @abstractmethod
    def get_tracker_hop(self, uetr: str) -> Optional[CorrespondentTrackerHopRecord]:
        """Retrieves authoritative SWIFT gpi tracker hop telemetry."""
        pass

    @abstractmethod
    def get_debit_confirmation(self, uetr: str) -> Optional[DebitConfirmationRecord]:
        """Retrieves camt.054 debit confirmation record."""
        pass

    @abstractmethod
    def get_inquiry_policy(self, tenant_id: str = "DEFAULT_BANK") -> TransitInquiryPolicyRecord:
        """Retrieves correspondent inquiry trigger thresholds."""
        pass

    @abstractmethod
    def generate_investigation_candidate(
        self, uetr: str, intermediary_bic: str, inquiry_type: str = "CAMT_056"
    ) -> TransitInvestigationCandidate:
        """Generates a governed correspondent transit investigation candidate package."""
        pass
