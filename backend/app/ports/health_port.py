"""Health & Readiness Port (SPI).

Defines the abstract interface for liveness, readiness, and circuit-breaker status probes.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from app.schemas.contracts.health_schemas import HealthStatusEnvelope


class HealthReadinessPort(ABC):
    """Abstract port for health probes and circuit breaker inspection."""

    @abstractmethod
    def check_health(self) -> HealthStatusEnvelope:
        """Runs component probes and evaluates overall readiness for exception traffic."""
        pass

    @abstractmethod
    def record_component_failure(
        self,
        component_name: str,
        error_message: str
    ) -> bool:
        """Records a component failure and potentially trips circuit breaker."""
        pass

    @abstractmethod
    def reset_circuit_breaker(self, component_name: str) -> bool:
        """Resets a tripped circuit breaker after recovery."""
        pass
