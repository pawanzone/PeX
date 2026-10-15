"""Settlement Return Port (SPI-SETTLEMENT-RETURN-PORT).

Defines abstract SPI for generating compliant settlement return messages and ledger re-credit packages.
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave2_schemas import SettlementReturnPackage


class SettlementReturnPort(ABC):
    """Abstract port for Settlement Return package compilation and dispatch validation."""

    @abstractmethod
    def generate_return_package(
        self,
        uetr: str,
        original_payment_id: str,
        amount: float,
        currency: str,
        return_reason_code: str,
        clearing_rail: str,
        narrative: Optional[str] = None,
        debtor_account: Optional[str] = None
    ) -> SettlementReturnPackage:
        """Generates structured return package conforming to applicable clearing rail standards."""
        pass

    @abstractmethod
    def validate_return_schema(self, return_package: SettlementReturnPackage) -> bool:
        """Validates return message structure and reason code validity."""
        pass
