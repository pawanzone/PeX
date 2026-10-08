"""Health & Readiness Contract Schemas.

Defines the contract for component health probes, liveness, and circuit breakers.
"""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class ComponentProbe(BaseModel):
    """Probe result for an individual platform component."""
    component_name: str
    status: HealthStatus
    latency_ms: float = 0.0
    message: Optional[str] = None
    last_checked: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthStatusEnvelope(BaseModel):
    """Overall system health and circuit breaker status."""
    system_status: HealthStatus
    is_ready_for_traffic: bool
    circuit_breaker_open: bool = False
    probes: Dict[str, ComponentProbe] = Field(default_factory=dict)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
