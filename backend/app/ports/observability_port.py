"""Observability Trace Port (SPI).

Defines the abstract interface for recording distributed trace spans, telemetry,
and decision diagnostic dumps.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.schemas.contracts.observability_schemas import (
    TraceContext,
    SpanRecord,
)


class ObservabilityTracePort(ABC):
    """Abstract port for telemetry and distributed tracing."""

    @abstractmethod
    def start_trace(
        self,
        case_id: str,
        correlation_id: str
    ) -> TraceContext:
        """Starts a distributed trace context for an exception resolution."""
        pass

    @abstractmethod
    def record_span(
        self,
        trace_id: str,
        span: SpanRecord
    ) -> bool:
        """Records an execution span within an active trace."""
        pass

    @abstractmethod
    def record_decision_dump(
        self,
        trace_id: str,
        decision_data: Dict[str, Any]
    ) -> bool:
        """Records full diagnostic rationale for resolution and STP decisions."""
        pass
