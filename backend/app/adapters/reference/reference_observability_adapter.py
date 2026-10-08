"""In-Memory Reference Observability Trace Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements ObservabilityTracePort with in-memory span collections and diagnostic dumps.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from app.ports.observability_port import ObservabilityTracePort
from app.schemas.contracts.observability_schemas import (
    TraceContext,
    SpanRecord,
)


class InMemoryObservabilityTraceAdapter(ObservabilityTracePort):
    """Hermetic reference implementation of ObservabilityTracePort."""

    def __init__(self):
        self._traces: Dict[str, TraceContext] = {}

    def start_trace(
        self,
        case_id: str,
        correlation_id: str
    ) -> TraceContext:
        trace_id = f"TRC-{uuid.uuid4().hex[:8].upper()}"
        ctx = TraceContext(
            trace_id=trace_id,
            case_id=case_id,
            correlation_id=correlation_id,
            spans=[]
        )
        self._traces[trace_id] = ctx
        return ctx

    def record_span(
        self,
        trace_id: str,
        span: SpanRecord
    ) -> bool:
        if trace_id in self._traces:
            self._traces[trace_id].spans.append(span)
            self._traces[trace_id].total_duration_ms += span.duration_ms
            return True
        return False

    def record_decision_dump(
        self,
        trace_id: str,
        decision_data: Dict[str, Any]
    ) -> bool:
        if trace_id in self._traces:
            self._traces[trace_id].decision_dump = decision_data
            return True
        return False

    def get_trace(self, trace_id: str) -> Optional[TraceContext]:
        return self._traces.get(trace_id)
