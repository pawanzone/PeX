"""Streaming Message Broker Port (SPI).

Defines the abstract interface for streaming queue intake, dead-letter queue (DLQ) routing,
and poison message containment without vendor coupling.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.schemas.contracts.broker_schemas import (
    MessageEnvelope,
    BrokerReceipt,
)


class StreamingMessageBrokerPort(ABC):
    """Abstract port for message broker queue transit."""

    @abstractmethod
    def publish_message(
        self,
        envelope: MessageEnvelope
    ) -> BrokerReceipt:
        """Publishes a message to a queue or topic."""
        pass

    @abstractmethod
    def route_to_dlq(
        self,
        envelope: MessageEnvelope,
        reason: str
    ) -> BrokerReceipt:
        """Routes a poison or unresolvable message to Dead Letter Queue suspense."""
        pass

    @abstractmethod
    def acknowledge_message(
        self,
        message_id: str,
        topic_or_queue: str
    ) -> bool:
        """Acknowledges successful processing of a message."""
        pass
