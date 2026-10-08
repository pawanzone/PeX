"""Payment Hub Repair Queue Port (SPI).

Defines abstract SPI for inspecting payment hub repair queues, syntax error tags,
and validating proposed repairs before bank handoff.
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave1_schemas import (
    PaymentHubRepairRecord,
    RepairValidationResult,
)


class PaymentHubRepairQueuePort(ABC):
    """Abstract port for Payment Hub Repair Queue interactions."""

    @abstractmethod
    def get_repair_item(self, payment_id: str) -> Optional[PaymentHubRepairRecord]:
        """Retrieves repair item and syntax error metadata from bank payment hub."""
        pass

    @abstractmethod
    def validate_repair_syntax(
        self,
        payment_id: str,
        proposed_fix: Dict[str, Any]
    ) -> RepairValidationResult:
        """Validates that proposed repair conforms to payment hub schema rules."""
        pass
