"""In-Memory Reference Health & Readiness Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements HealthReadinessPort.
"""
from typing import Dict, Any
from datetime import datetime, timezone

from app.ports.health_port import HealthReadinessPort
from app.schemas.contracts.health_schemas import (
    HealthStatus,
    ComponentProbe,
    HealthStatusEnvelope,
)


class InMemoryHealthReadinessAdapter(HealthReadinessPort):
    """Hermetic reference implementation of HealthReadinessPort."""

    def __init__(self):
        self._circuit_open = False
        self._failures: Dict[str, str] = {}

    def check_health(self) -> HealthStatusEnvelope:
        now = datetime.now(timezone.utc)
        probes: Dict[str, ComponentProbe] = {
            "evidence_engine": ComponentProbe(component_name="evidence_engine", status=HealthStatus.HEALTHY, latency_ms=1.2),
            "authority_router": ComponentProbe(component_name="authority_router", status=HealthStatus.HEALTHY, latency_ms=0.8),
            "bank_policy_engine": ComponentProbe(component_name="bank_policy_engine", status=HealthStatus.HEALTHY, latency_ms=1.5),
            "token_vault": ComponentProbe(component_name="token_vault", status=HealthStatus.HEALTHY, latency_ms=2.1),
            "audit_ledger": ComponentProbe(component_name="audit_ledger", status=HealthStatus.HEALTHY, latency_ms=1.9),
            "stp_engine": ComponentProbe(component_name="stp_engine", status=HealthStatus.HEALTHY, latency_ms=3.4)
        }

        # Apply any recorded failures
        for comp, err in self._failures.items():
            if comp in probes:
                probes[comp].status = HealthStatus.UNHEALTHY
                probes[comp].message = err

        is_unhealthy = any(p.status == HealthStatus.UNHEALTHY for p in probes.values())
        system_status = HealthStatus.UNHEALTHY if is_unhealthy or self._circuit_open else HealthStatus.HEALTHY

        return HealthStatusEnvelope(
            system_status=system_status,
            is_ready_for_traffic=(system_status == HealthStatus.HEALTHY and not self._circuit_open),
            circuit_breaker_open=self._circuit_open,
            probes=probes,
            checked_at=now
        )

    def record_component_failure(
        self,
        component_name: str,
        error_message: str
    ) -> bool:
        self._failures[component_name] = error_message
        self._circuit_open = True # Trip circuit breaker on failure
        return True

    def reset_circuit_breaker(self, component_name: str) -> bool:
        if component_name in self._failures:
            del self._failures[component_name]
        self._circuit_open = False
        return True
