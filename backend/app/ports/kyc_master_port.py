"""KYC Master Port (SPI-KYC-MASTER).

Defines abstract SPI for customer periodic KYC / CDD status and corporate standing evaluation.
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.schemas.contracts.wave4_schemas import (
    CustomerKycRecord,
    CorporateStandingRecord,
    KycWaiverPolicyRecord,
    KycProvisionalWaiverCandidate,
)


class KycMasterPort(ABC):
    """Abstract port for client onboarding and KYC record lookups."""

    @abstractmethod
    def get_kyc_record(self, client_id: str) -> Optional[CustomerKycRecord]:
        """Retrieves authoritative client KYC status record."""
        pass

    @abstractmethod
    def get_corporate_standing(self, client_id: str) -> Optional[CorporateStandingRecord]:
        """Retrieves client corporate relationship tier, credit score, and risk history."""
        pass

    @abstractmethod
    def get_waiver_policy(self, tenant_id: str = "DEFAULT_BANK") -> KycWaiverPolicyRecord:
        """Retrieves bank SOP-302 provisional KYC waiver policy parameters."""
        pass

    @abstractmethod
    def generate_provisional_waiver(
        self, client_id: str, waiver_days: int = 30
    ) -> KycProvisionalWaiverCandidate:
        """Generates a governed 30-day provisional processing waiver package."""
        pass
