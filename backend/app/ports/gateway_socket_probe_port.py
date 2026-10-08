"""Gateway Socket Probe Port (SPI).

Defines abstract SPI for probing message gateway socket health, verifying network
transmission status, and checking retry budgets.
Zero vendor SDK dependencies. Provider-neutral.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.contracts.wave1_schemas import (
    GatewayProbeResult,
    TransmissionStateResult,
    RetryBudgetResult,
)


class GatewaySocketProbePort(ABC):
    """Abstract port for Gateway Socket Probe & Retry management."""

    @abstractmethod
    def probe_gateway_socket(
        self,
        gateway_id: str,
        rail_code: str
    ) -> GatewayProbeResult:
        """Probes live connection status of message gateway / socket."""
        pass

    @abstractmethod
    def check_transmission_state(
        self,
        payment_uetr: str
    ) -> TransmissionStateResult:
        """Determines whether a timed-out message reached the network or was lost in transit."""
        pass

    @abstractmethod
    def get_retry_budget(
        self,
        payment_id: str
    ) -> RetryBudgetResult:
        """Checks if retry attempt budget has been exceeded for the payment."""
        pass
