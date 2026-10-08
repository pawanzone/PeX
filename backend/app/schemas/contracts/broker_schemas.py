"""Streaming Message Broker Contract Schemas.

Defines the contract for queue transit, message envelopes, and dead-letter queue (DLQ) suspense.
"""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class TransitStatus(str, Enum):
    ENQUEUED = "ENQUEUED"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    REJECTED = "REJECTED"
    DLQ_SUSPENDED = "DLQ_SUSPENDED"
    BROKER_UNAVAILABLE = "BROKER_UNAVAILABLE"


class MessageEnvelope(BaseModel):
    """Abstract message envelope for streaming queue transit."""
    message_id: str
    correlation_id: str
    topic_or_queue: str
    payload: Dict[str, Any]
    headers: Dict[str, str] = Field(default_factory=dict)
    attempt_count: int = 1
    max_attempts: int = 3
    enqueued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BrokerReceipt(BaseModel):
    """Receipt returned by a message broker upon transit operation."""
    message_id: str
    correlation_id: str
    topic_or_queue: str
    status: TransitStatus
    partition: int = 0
    offset: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_details: Optional[str] = None
