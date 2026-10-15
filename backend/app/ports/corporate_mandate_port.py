"""Corporate Mandate Port (SPI-CORPORATE-MANDATE).

Defines abstract SPI for retrieving corporate account signature mandates, secondary digital signatures,
and out-of-band portal callback records.
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.schemas.contracts.wave4_schemas import (
    CorporateMandateRecord,
    SecondarySignatoryRecord,
    PortalCallbackRecord,
    CorporateDualAuthorizationCandidate,
)


class CorporateMandatePort(ABC):
    """Abstract port for corporate signatory and dual-authorization lookups."""

    @abstractmethod
    def get_mandate_record(self, debtor_account: str) -> Optional[CorporateMandateRecord]:
        """Retrieves authoritative signatory mandate for the account."""
        pass

    @abstractmethod
    def get_secondary_signatory(self, debtor_account: str) -> Optional[SecondarySignatoryRecord]:
        """Retrieves secondary digital sign-off from corporate banking portal queue."""
        pass

    @abstractmethod
    def get_portal_callback(self, debtor_account: str) -> Optional[PortalCallbackRecord]:
        """Retrieves out-of-band portal callback and MFA verification status."""
        pass

    @abstractmethod
    def generate_dual_auth_clearance(
        self, mandate_id: str, primary_signer: str, secondary_signer: str
    ) -> CorporateDualAuthorizationCandidate:
        """Generates a governed dual-authorization clearance package."""
        pass
