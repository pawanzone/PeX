"""Observability Trace & Telemetry Schemas.

Defines the contract for distributed tracing, correlation IDs, and decision diagnostic dumps.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class SpanRecord(BaseModel):
    """Individual span recorded during resolution processing."""
    span_id: str
    span_name: str
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    status: str = "OK"
    attributes: Dict[str, Any] = Field(default_factory=dict)


class TraceContext(BaseModel):
    """Distributed trace context linking all operations for a payment exception."""
    trace_id: str
    case_id: str
    correlation_id: str                              # UETR / IMAD / Transaction ID
    spans: List[SpanRecord] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decision_dump: Dict[str, Any] = Field(default_factory=dict)
