"""Correspondent Gateway Port (SPI-CORRESPONDENT-GATEWAY).

Defines abstract SPI for parsing, verifying, and retrieving authoritative intermediary/correspondent
rejection advice and in-flight transit states.
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave2_schemas import (
    IntermediaryRejectionAdvice,
    DeterministicCorrelationMatch,
)


class CorrespondentGatewayPort(ABC):
    """Abstract port for Correspondent Gateway / Intermediary Rejection lookups."""

    @abstractmethod
    def get_rejection_advice(self, rejection_reference_or_uetr: str) -> Optional[IntermediaryRejectionAdvice]:
        """Retrieves authoritative structured rejection advice from correspondent clearing gateway."""
        pass

    @abstractmethod
    def correlate_rejection(
        self,
        rejection_advice: IntermediaryRejectionAdvice,
        payment_context: Dict[str, Any]
    ) -> DeterministicCorrelationMatch:
        """Deterministically correlates inward rejection to original outbound payment keys."""
        pass

    @abstractmethod
    def verify_rejection_authority(self, rejection_advice: IntermediaryRejectionAdvice) -> bool:
        """Verifies that the rejecting institution has sovereign authority and is not raw network telemetry."""
        pass
