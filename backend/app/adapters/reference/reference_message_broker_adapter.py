"""In-Memory Reference Streaming Message Broker Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements StreamingMessageBrokerPort using in-memory queues and DLQ tables.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.ports.message_broker_port import StreamingMessageBrokerPort
from app.schemas.contracts.broker_schemas import (
    MessageEnvelope,
    BrokerReceipt,
    TransitStatus,
)


class InMemoryMessageBrokerAdapter(StreamingMessageBrokerPort):
    """Hermetic reference implementation of StreamingMessageBrokerPort."""

    def __init__(self):
        self._queues: Dict[str, List[MessageEnvelope]] = {}
        self._dlq: List[Dict[str, Any]] = []
        self._offset_counter = 0

    def publish_message(
        self,
        envelope: MessageEnvelope
    ) -> BrokerReceipt:
        q = envelope.topic_or_queue
        if q not in self._queues:
            self._queues[q] = []
        self._queues[q].append(envelope)
        self._offset_counter += 1

        return BrokerReceipt(
            message_id=envelope.message_id,
            correlation_id=envelope.correlation_id,
            topic_or_queue=q,
            status=TransitStatus.ENQUEUED,
            partition=0,
            offset=self._offset_counter
        )

    def route_to_dlq(
        self,
        envelope: MessageEnvelope,
        reason: str
    ) -> BrokerReceipt:
        self._offset_counter += 1
        record = {
            "message": envelope.model_dump(),
            "reason": reason,
            "suspended_at": datetime.now(timezone.utc).isoformat()
        }
        self._dlq.append(record)

        return BrokerReceipt(
            message_id=envelope.message_id,
            correlation_id=envelope.correlation_id,
            topic_or_queue="PEX_DEAD_LETTER_SUSPENSE_QUEUE",
            status=TransitStatus.DLQ_SUSPENDED,
            partition=0,
            offset=self._offset_counter,
            error_details=reason
        )

    def acknowledge_message(
        self,
        message_id: str,
        topic_or_queue: str
    ) -> bool:
        if topic_or_queue in self._queues:
            self._queues[topic_or_queue] = [
                m for m in self._queues[topic_or_queue] if m.message_id != message_id
            ]
            return True
        return False
