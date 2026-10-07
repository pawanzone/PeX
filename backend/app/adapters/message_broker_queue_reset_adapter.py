"""Provider-Neutral Message Broker Queue Reset Port and Synthetic Adapter for PR-08.

Supports the provider-neutral queue recovery abstraction:
MessageBrokerState = <MessageId, SourceQueue, DLQState, RetryCount, ErrorClass, BrokerAck, ProcessingState, SettlementState>

Governed by:
- PeX_Phase2_Taxonomy_Remediation_Architecture_Decision_v0.2.md
- PeX_Phase2_DQ08_PR08_Remediation_Implementation_Contract_v0.1.md
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field


class BrokerQueueType(str, Enum):
    """Queue and topic classifications across message brokers."""
    MAIN_INGEST = "MAIN_INGEST"
    RETRY_QUEUE = "RETRY_QUEUE"
    DEAD_LETTER_QUEUE = "DEAD_LETTER_QUEUE"
    SUSPENSE_QUEUE = "SUSPENSE_QUEUE"
    MANUAL_INVESTIGATION = "MANUAL_INVESTIGATION"


class MessageProcessingStatus(str, Enum):
    """Authoritative processing state recorded in the bank execution engine."""
    UNPROCESSED = "UNPROCESSED"
    IN_PROCESSING = "IN_PROCESSING"
    FAILED_TRANSIENT = "FAILED_TRANSIENT"
    FAILED_POISON = "FAILED_POISON"
    COMPLETED_ACKNOWLEDGED = "COMPLETED_ACKNOWLEDGED"
    SETTLED_DEBITED = "SETTLED_DEBITED"
    UNKNOWN = "UNKNOWN"


class BrokerDLQMetadata(BaseModel):
    """Authoritative metadata emitted by the message broker upon DLQ dead-lettering."""
    message_id: str
    uetr: Optional[str] = None
    source_queue: str                                         # e.g., "PAYMENT_INGEST_QUEUE"
    target_requeue_destination: str                           # e.g., "PAYMENT_INGEST_QUEUE"
    retry_count: int = 0
    max_retries: int = 3                                      # DEMO_ONLY_DEFAULT: Production requires BANK_CONFIG_REQUIRED
    error_code: str                                           # e.g., "TIMEOUT_CONSUMER_INTERRUPTED", "MALFORMED_XML_SCHEMA"
    error_details: str
    is_poison: bool = False
    broker_ack_state: str = "NACK_SENT"                       # "NACK_SENT", "UNACKNOWLEDGED", "ACK_CONFIRMED"
    correlation_id: str
    provider: str = "SYNTHETIC_MESSAGE_BROKER (DEMO_ONLY_DEFAULT)"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=15))
    freshness_seconds: int = 900                              # 15 minutes TTL

    @property
    def is_stale(self) -> bool:
        now = datetime.now(timezone.utc)
        return now > self.expires_at or (now - self.retrieved_at).total_seconds() > self.freshness_seconds


class SettlementLedgerState(BaseModel):
    """Authoritative state from Core Banking / RTGS Settlement Ledger for duplicate financial risk evaluation."""
    payment_id: str
    uetr: str
    amount: float
    currency: str
    ledger_status: str                                        # "POSTED_DEBITED", "PENDING_SETTLEMENT", "CANCELLED_NO_DEBIT", "NOT_FOUND"
    settlement_timestamp: Optional[datetime] = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=15))
    freshness_seconds: int = 900

    @property
    def is_stale(self) -> bool:
        now = datetime.now(timezone.utc)
        return now > self.expires_at or (now - self.retrieved_at).total_seconds() > self.freshness_seconds


class ProcessingStateRecord(BaseModel):
    """Authoritative downstream processing state record."""
    message_id: str
    uetr: Optional[str] = None
    status: MessageProcessingStatus
    last_attempt_stage: str
    downstream_system_ack: bool = False
    debit_posted: bool = False
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=15))
    freshness_seconds: int = 900

    @property
    def is_stale(self) -> bool:
        now = datetime.now(timezone.utc)
        return now > self.expires_at or (now - self.recorded_at).total_seconds() > self.freshness_seconds


class BankRetryPolicyConfig(BaseModel):
    """Authoritative Bank Retry & Queue Recovery Policy.
    
    DEMO_ONLY_DEFAULT: Example parameters for Level-1 testing.
    Production deployments mandate explicit bank policy configuration (BANK_CONFIG_REQUIRED).
    """
    max_retry_count: int = 3
    allowed_transient_error_codes: List[str] = Field(default_factory=lambda: [
        "TIMEOUT_CONSUMER_INTERRUPTED",
        "DATABASE_CONNECTION_RESET",
        "DOWNSTREAM_HTTP_503",
        "LOCK_ACQUISITION_TIMEOUT",
        "BROKER_TEMPORARILY_UNAVAILABLE",
        "NETWORK_PARTITION_RECOVERED"
    ])
    poison_error_codes: List[str] = Field(default_factory=lambda: [
        "MALFORMED_XML_SCHEMA_VIOLATION",
        "DETERMINISTIC_DESERIALIZATION_FAILURE",
        "UNSUPPORTED_BUSINESS_FUNCTION",
        "CORRUPT_PAYLOAD_UNPARSEABLE",
        "SECURITY_SIGNATURE_INVALID"
    ])
    duplicate_check_required: bool = True
    max_auto_stp_amount: float = 25000.0                      # Configurable autonomous recovery amount ceiling
    supported_queues: List[str] = Field(default_factory=lambda: ["PAYMENT_INGEST_QUEUE", "WIRE_PROCESSING_QUEUE", "SEPA_DIRECT_QUEUE"])
    is_bank_policy_configured: bool = True                    # If False, fail-closed


class MessageBrokerQueueResetPort(ABC):
    """Provider-neutral port for querying message broker DLQ state, downstream processing status, and requeue emission."""

    @abstractmethod
    def get_dlq_metadata(self, message_id: str) -> Optional[BrokerDLQMetadata]:
        """Retrieves authoritative broker dead-letter metadata for the given message ID."""
        pass

    @abstractmethod
    def get_processing_state(self, message_id: str) -> Optional[ProcessingStateRecord]:
        """Retrieves authoritative execution engine state for the given message ID."""
        pass

    @abstractmethod
    def get_settlement_state(self, uetr: str) -> Optional[SettlementLedgerState]:
        """Retrieves settlement ledger status to detect duplicate debit or release risks."""
        pass

    @abstractmethod
    def verify_requeue_eligibility(
        self,
        metadata: BrokerDLQMetadata,
        processing_state: ProcessingStateRecord,
        policy: BankRetryPolicyConfig,
        settlement_state: Optional[SettlementLedgerState] = None
    ) -> Tuple[bool, str]:
        """Evaluates whether the message is eligible for governed re-enqueue."""
        pass

    @abstractmethod
    def emit_requeue_instruction(self, message_id: str, target_queue: str, payload: str) -> bool:
        """Emits a controlled re-enqueue instruction back to the Bank Payment Hub / Message Broker."""
        pass


class SyntheticMessageBrokerQueueResetAdapter(MessageBrokerQueueResetPort):
    """Synthetic in-memory adapter implementing MessageBrokerQueueResetPort with deterministic test fixtures.
    
    Contains test fixtures for transient failures, poison messages, duplicate processing, and stale state.
    Production deployments substitute Kafka/IBM MQ/RabbitMQ/AWS SQS connectors (BANK_CONFIG_REQUIRED).
    """

    def __init__(self):
        self._dlq_store: Dict[str, BrokerDLQMetadata] = {}
        self._processing_store: Dict[str, ProcessingStateRecord] = {}
        self._settlement_store: Dict[str, SettlementLedgerState] = {}
        self._requeued_messages: List[Dict[str, Any]] = []
        self._seed_fixtures()

    def _seed_fixtures(self):
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=15)

        # 1. Transient Recoverable Message (Retry Count 1 < 3)
        self._add_dlq(
            message_id="MSG-PR08-TRANS-01",
            uetr="11a1b2c3-44dd-55ee-66ff-778899aabbcc",
            source_queue="PAYMENT_INGEST_QUEUE",
            target_requeue="PAYMENT_INGEST_QUEUE",
            retry_count=1,
            max_retries=3,
            error_code="TIMEOUT_CONSUMER_INTERRUPTED",
            error_details="Downstream consumer timed out after 30000ms. Recoverable network interruption.",
            is_poison=False,
            ack_state="NACK_SENT"
        )
        self._add_processing(
            message_id="MSG-PR08-TRANS-01",
            uetr="11a1b2c3-44dd-55ee-66ff-778899aabbcc",
            status=MessageProcessingStatus.FAILED_TRANSIENT,
            last_stage="INGESTION_STAGE",
            downstream_ack=False,
            debit_posted=False
        )

        # 2. Max Retries Exceeded (Retry Count 3 >= 3)
        self._add_dlq(
            message_id="MSG-PR08-MAXRET-01",
            uetr="22a1b2c3-44dd-55ee-66ff-778899aabbcc",
            source_queue="PAYMENT_INGEST_QUEUE",
            target_requeue="PAYMENT_INGEST_QUEUE",
            retry_count=3,
            max_retries=3,
            error_code="TIMEOUT_CONSUMER_INTERRUPTED",
            error_details="Exceeded maximum automated retry attempts (3/3).",
            is_poison=False,
            ack_state="NACK_SENT"
        )
        self._add_processing(
            message_id="MSG-PR08-MAXRET-01",
            uetr="22a1b2c3-44dd-55ee-66ff-778899aabbcc",
            status=MessageProcessingStatus.FAILED_TRANSIENT,
            last_stage="INGESTION_STAGE",
            downstream_ack=False,
            debit_posted=False
        )

        # 3. Poison Message (Malformed Schema / Fatal Deserialization Failure)
        self._add_dlq(
            message_id="MSG-PR08-POISON-01",
            uetr="33a1b2c3-44dd-55ee-66ff-778899aabbcc",
            source_queue="PAYMENT_INGEST_QUEUE",
            target_requeue="PAYMENT_INGEST_QUEUE",
            retry_count=1,
            max_retries=3,
            error_code="MALFORMED_XML_SCHEMA_VIOLATION",
            error_details="Fatal SAX parsing error: mismatched closing tags in credit transfer document.",
            is_poison=True,
            ack_state="NACK_SENT"
        )
        self._add_processing(
            message_id="MSG-PR08-POISON-01",
            uetr="33a1b2c3-44dd-55ee-66ff-778899aabbcc",
            status=MessageProcessingStatus.FAILED_POISON,
            last_stage="XML_SCHEMA_VALIDATOR",
            downstream_ack=False,
            debit_posted=False
        )

        # 4. Already Processed / Debited Message (Duplicate Financial Release Risk)
        self._add_dlq(
            message_id="MSG-PR08-DUP-01",
            uetr="44a1b2c3-44dd-55ee-66ff-778899aabbcc",
            source_queue="WIRE_PROCESSING_QUEUE",
            target_requeue="WIRE_PROCESSING_QUEUE",
            retry_count=1,
            max_retries=3,
            error_code="TIMEOUT_CONSUMER_INTERRUPTED",
            error_details="Consumer timed out waiting for broker commit after posting debit.",
            is_poison=False,
            ack_state="UNACKNOWLEDGED"
        )
        self._add_processing(
            message_id="MSG-PR08-DUP-01",
            uetr="44a1b2c3-44dd-55ee-66ff-778899aabbcc",
            status=MessageProcessingStatus.SETTLED_DEBITED,
            last_stage="CORE_DDA_POSTING",
            downstream_ack=True,
            debit_posted=True
        )
        self._add_settlement(
            payment_id="PAY-DUP-01",
            uetr="44a1b2c3-44dd-55ee-66ff-778899aabbcc",
            amount=50000.0,
            currency="USD",
            ledger_status="POSTED_DEBITED"
        )

        # 5. Message Requiring PR-05 Subsidiary Charset Repair
        self._add_dlq(
            message_id="MSG-PR08-CHARSET-01",
            uetr="55a1b2c3-44dd-55ee-66ff-778899aabbcc",
            source_queue="PAYMENT_INGEST_QUEUE",
            target_requeue="PAYMENT_INGEST_QUEUE",
            retry_count=1,
            max_retries=3,
            error_code="TIMEOUT_CONSUMER_INTERRUPTED",
            error_details="Consumer interrupted during character sanitization stage.",
            is_poison=False,
            ack_state="NACK_SENT"
        )
        self._add_processing(
            message_id="MSG-PR08-CHARSET-01",
            uetr="55a1b2c3-44dd-55ee-66ff-778899aabbcc",
            status=MessageProcessingStatus.FAILED_TRANSIENT,
            last_stage="CHARSET_ENCODING_STAGE",
            downstream_ack=False,
            debit_posted=False
        )

    def _add_dlq(self, message_id: str, uetr: str, source_queue: str, target_requeue: str, retry_count: int, max_retries: int, error_code: str, error_details: str, is_poison: bool, ack_state: str):
        now = datetime.now(timezone.utc)
        self._dlq_store[message_id] = BrokerDLQMetadata(
            message_id=message_id,
            uetr=uetr,
            source_queue=source_queue,
            target_requeue_destination=target_requeue,
            retry_count=retry_count,
            max_retries=max_retries,
            error_code=error_code,
            error_details=error_details,
            is_poison=is_poison,
            broker_ack_state=ack_state,
            correlation_id=f"CORR-{message_id}",
            retrieved_at=now,
            expires_at=now + timedelta(minutes=15)
        )

    def _add_processing(self, message_id: str, uetr: str, status: MessageProcessingStatus, last_stage: str, downstream_ack: bool, debit_posted: bool):
        now = datetime.now(timezone.utc)
        self._processing_store[message_id] = ProcessingStateRecord(
            message_id=message_id,
            uetr=uetr,
            status=status,
            last_attempt_stage=last_stage,
            downstream_system_ack=downstream_ack,
            debit_posted=debit_posted,
            recorded_at=now,
            expires_at=now + timedelta(minutes=15)
        )

    def _add_settlement(self, payment_id: str, uetr: str, amount: float, currency: str, ledger_status: str):
        now = datetime.now(timezone.utc)
        self._settlement_store[uetr] = SettlementLedgerState(
            payment_id=payment_id,
            uetr=uetr,
            amount=amount,
            currency=currency,
            ledger_status=ledger_status,
            settlement_timestamp=now if ledger_status == "POSTED_DEBITED" else None,
            retrieved_at=now,
            expires_at=now + timedelta(minutes=15)
        )

    def get_dlq_metadata(self, message_id: str) -> Optional[BrokerDLQMetadata]:
        return self._dlq_store.get(message_id)

    def get_processing_state(self, message_id: str) -> Optional[ProcessingStateRecord]:
        return self._processing_store.get(message_id)

    def get_settlement_state(self, uetr: str) -> Optional[SettlementLedgerState]:
        return self._settlement_store.get(uetr)

    def verify_requeue_eligibility(
        self,
        metadata: BrokerDLQMetadata,
        processing_state: ProcessingStateRecord,
        policy: BankRetryPolicyConfig,
        settlement_state: Optional[SettlementLedgerState] = None
    ) -> Tuple[bool, str]:
        if not policy.is_bank_policy_configured:
            return False, "Bank Retry Policy is not configured. Fail-closed."

        if metadata.is_poison or metadata.error_code in policy.poison_error_codes:
            return False, f"Message '{metadata.message_id}' is classified as POISON ({metadata.error_code}). Automatic retry prohibited."

        if metadata.retry_count >= policy.max_retry_count:
            return False, f"Retry count ({metadata.retry_count}) exceeds policy maximum ({policy.max_retry_count})."

        if metadata.error_code not in policy.allowed_transient_error_codes:
            return False, f"Error code '{metadata.error_code}' is not in policy permitted transient error classes."

        if processing_state.debit_posted or processing_state.status == MessageProcessingStatus.SETTLED_DEBITED:
            return False, "Processing state indicates debit was already posted. Re-enqueue blocked to prevent duplicate release."

        if settlement_state and settlement_state.ledger_status == "POSTED_DEBITED":
            return False, "Settlement ledger confirms transaction was already debited/settled. Re-enqueue blocked."

        if metadata.source_queue not in policy.supported_queues:
            return False, f"Source queue '{metadata.source_queue}' is not supported by bank recovery policy."

        return True, "Message is eligible for governed re-enqueue."

    def emit_requeue_instruction(self, message_id: str, target_queue: str, payload: str) -> bool:
        self._requeued_messages.append({
            "message_id": message_id,
            "target_queue": target_queue,
            "payload_length": len(payload),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        return True


# Global singleton adapter instance
message_broker_adapter = SyntheticMessageBrokerQueueResetAdapter()
