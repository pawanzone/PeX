"""Governed Queue Processing Failure & Message Broker Reset Engine for PR-08.

PR-08: QUEUE_PROCESSING_FAILURE
Domain: Processing (BIAN Domain 2)
STP Group: Group 1 (Autonomous STP Capable)

Governed by:
- PeX_Phase2_Taxonomy_Remediation_Architecture_Decision_v0.2.md
- PeX_Phase2_DQ08_PR08_Remediation_Implementation_Contract_v0.1.md

Enforces:
1. Authoritative Broker / Message Processing State as primary authority.
2. Idempotency Lock Management & Race Condition Protection via IdempotencyLockManagerPort.
3. Strict Fail-Closed Isolation of Poison Messages (malformed/deterministic errors never enter retry loop).
4. Prevention of Duplicate Release / Financial Debit Risk via Settlement Ledger State checks.
5. Strict Retry Policy Enforcement (retry_count < max_retries is necessary but NOT sufficient for STP).
6. Controlled Subsidiary PR-05 Invocations for Character Encoding / Control-Byte Remediation.
7. Complete 8-Predicate STP Formula Evaluation.
"""
import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field

from app.schemas.resolution_contract import (
    ResolutionCandidate,
    ResolutionResult,
    ResolutionStatus,
    ResolutionUniqueness,
)
from app.adapters.message_broker_queue_reset_adapter import (
    MessageBrokerQueueResetPort,
    SyntheticMessageBrokerQueueResetAdapter,
    message_broker_adapter,
    BrokerDLQMetadata,
    ProcessingStateRecord,
    SettlementLedgerState,
    BankRetryPolicyConfig,
    MessageProcessingStatus,
)
from app.adapters.idempotency_lock_manager import (
    IdempotencyLockManagerPort,
    InMemoryIdempotencyLockManager,
    idempotency_lock_manager,
)
from app.services.pr05_transformer import pr05_transformer, PR05TransformationResult


class PR08RecoveryOutcome(str, Enum):
    """Authoritative outcome classification for PR-08 queue recovery."""
    TRANSIENT_REQUEUE_ELIGIBLE = "TRANSIENT_REQUEUE_ELIGIBLE"
    POISON_MESSAGE_HALTED = "POISON_MESSAGE_HALTED"
    ALREADY_PROCESSED_BLOCKED = "ALREADY_PROCESSED_BLOCKED"
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"
    SETTLEMENT_CONFLICT_BLOCKED = "SETTLEMENT_CONFLICT_BLOCKED"
    IDEMPOTENCY_LOCKED_RACE = "IDEMPOTENCY_LOCKED_RACE"
    IDEMPOTENCY_ALREADY_EXECUTED = "IDEMPOTENCY_ALREADY_EXECUTED"
    STALE_EVIDENCE_HALTED = "STALE_EVIDENCE_HALTED"
    MISSING_MANDATORY_EVIDENCE = "MISSING_MANDATORY_EVIDENCE"
    UNAUTHORIZED_BANK_POLICY = "UNAUTHORIZED_BANK_POLICY"
    SUBSIDIARY_CHARSET_REPAIRED = "SUBSIDIARY_CHARSET_REPAIRED"
    UNRECOVERABLE_ERROR = "UNRECOVERABLE_ERROR"


class PR08QueueRecoveryResult(BaseModel):
    """Forensic result of executing the PR-08 queue recovery engine."""
    success: bool
    outcome: PR08RecoveryOutcome
    message_id: str
    uetr: Optional[str] = None
    source_queue: str
    target_requeue_destination: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    is_poison: bool = False
    requires_subsidiary_pr05: bool = False
    pr05_transformation_result: Optional[PR05TransformationResult] = None
    candidates: List[ResolutionCandidate] = Field(default_factory=list)
    uniqueness: ResolutionUniqueness = ResolutionUniqueness.RESOLUTION_UNIQUE
    is_lossless: bool = True
    diff_summary: str
    audit_trail: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class PR08QueueRecoveryEngine:
    """Master engine executing governed queue failure classification, broker state validation, and reset determination."""

    def __init__(
        self,
        broker_adapter: Optional[MessageBrokerQueueResetPort] = None,
        lock_manager: Optional[IdempotencyLockManagerPort] = None
    ):
        self.broker_adapter = broker_adapter or message_broker_adapter
        self.lock_manager = lock_manager or idempotency_lock_manager

    def evaluate_queue_recovery(
        self,
        raw_payload: str,
        message_id: str,
        uetr: Optional[str] = None,
        broker_metadata: Optional[BrokerDLQMetadata] = None,
        processing_state: Optional[ProcessingStateRecord] = None,
        settlement_state: Optional[SettlementLedgerState] = None,
        policy_config: Optional[BankRetryPolicyConfig] = None,
        allow_stale_evidence: bool = False,
        worker_id: str = "PEX_RECOVERY_WORKER_1"
    ) -> PR08QueueRecoveryResult:
        """Deterministically evaluates broker state, idempotency lock, retry policy, and recovery candidate."""
        trail: List[str] = [f"Initiating PR-08 queue recovery evaluation for message '{message_id}'."]
        policy = policy_config or BankRetryPolicyConfig()

        # 1. Mandatory Evidence Verification (E_suff prerequisite)
        if not raw_payload:
            trail.append("Stage 1 FAILED: Missing mandatory DLQ message payload.")
            return PR08QueueRecoveryResult(
                success=False,
                outcome=PR08RecoveryOutcome.MISSING_MANDATORY_EVIDENCE,
                message_id=message_id,
                uetr=uetr,
                source_queue="UNKNOWN",
                diff_summary="Missing mandatory DLQ message payload",
                audit_trail=trail,
                error_message="DLQ message payload is required."
            )

        meta = broker_metadata or self.broker_adapter.get_dlq_metadata(message_id)
        if not meta:
            trail.append(f"Stage 1 FAILED: Missing mandatory broker DLQ metadata for '{message_id}'.")
            return PR08QueueRecoveryResult(
                success=False,
                outcome=PR08RecoveryOutcome.MISSING_MANDATORY_EVIDENCE,
                message_id=message_id,
                uetr=uetr,
                source_queue="UNKNOWN",
                diff_summary="Missing broker DLQ metadata",
                audit_trail=trail,
                error_message="Authoritative broker DLQ metadata not found."
            )

        proc_state = processing_state or self.broker_adapter.get_processing_state(message_id)
        if not proc_state:
            trail.append(f"Stage 1 FAILED: Missing mandatory processing state record for '{message_id}'.")
            return PR08QueueRecoveryResult(
                success=False,
                outcome=PR08RecoveryOutcome.MISSING_MANDATORY_EVIDENCE,
                message_id=message_id,
                uetr=uetr or meta.uetr,
                source_queue=meta.source_queue,
                diff_summary="Missing processing state record",
                audit_trail=trail,
                error_message="Authoritative downstream processing state record not found."
            )

        # 2. Freshness Validation
        if (meta.is_stale or proc_state.is_stale) and not allow_stale_evidence:
            trail.append("Stage 2 FAILED: Broker or processing state evidence is stale. TTL expired.")
            return PR08QueueRecoveryResult(
                success=False,
                outcome=PR08RecoveryOutcome.STALE_EVIDENCE_HALTED,
                message_id=message_id,
                uetr=uetr or meta.uetr,
                source_queue=meta.source_queue,
                diff_summary="Authoritative state evidence TTL expired",
                audit_trail=trail,
                error_message="Broker state evidence is stale. Real-time broker sync required."
            )

        effective_uetr = uetr or meta.uetr or proc_state.uetr

        # 3. Idempotency Lock Acquisition (Concurrency Race Protection)
        idemp_key = f"IDEMP-PR08-{message_id}"
        if self.lock_manager.is_already_executed(idemp_key):
            trail.append(f"Stage 3 FAILED: Message '{message_id}' has already been processed and executed. Duplicate replay blocked.")
            return PR08QueueRecoveryResult(
                success=False,
                outcome=PR08RecoveryOutcome.IDEMPOTENCY_ALREADY_EXECUTED,
                message_id=message_id,
                uetr=effective_uetr,
                source_queue=meta.source_queue,
                diff_summary="Message recovery already executed",
                audit_trail=trail,
                error_message="Duplicate recovery replay blocked by idempotency manager."
            )

        lock_acquired = self.lock_manager.acquire_lock(idemp_key, ttl_seconds=300, owner=worker_id)
        if not lock_acquired:
            trail.append(f"Stage 3 FAILED: Idempotency lock collision for key '{idemp_key}'. Held by another concurrent worker.")
            return PR08QueueRecoveryResult(
                success=False,
                outcome=PR08RecoveryOutcome.IDEMPOTENCY_LOCKED_RACE,
                message_id=message_id,
                uetr=effective_uetr,
                source_queue=meta.source_queue,
                diff_summary="Concurrent worker lock collision",
                audit_trail=trail,
                error_message="Exclusive idempotency lock held by another worker."
            )

        trail.append(f"Stage 3 (Idempotency): Acquired exclusive lock for key '{idemp_key}' (owner: {worker_id}).")

        # 4. Bank Policy Configuration Gating
        if not policy.is_bank_policy_configured:
            trail.append("Stage 4 FAILED: Bank Retry Policy is not configured. Fail-closed.")
            return PR08QueueRecoveryResult(
                success=False,
                outcome=PR08RecoveryOutcome.UNAUTHORIZED_BANK_POLICY,
                message_id=message_id,
                uetr=effective_uetr,
                source_queue=meta.source_queue,
                diff_summary="Bank retry policy not configured",
                audit_trail=trail,
                error_message="Bank retry policy configuration is missing (BANK_CONFIG_REQUIRED)."
            )

        # 5. Duplicate Release & Settlement Risk Check
        settle_record = settlement_state
        if not settle_record and effective_uetr:
            settle_record = self.broker_adapter.get_settlement_state(effective_uetr)

        if proc_state.debit_posted or proc_state.status == MessageProcessingStatus.SETTLED_DEBITED:
            trail.append("Stage 5 FAILED: Processing state indicates funds were already debited/posted. Re-enqueue blocked to prevent double-debit.")
            return PR08QueueRecoveryResult(
                success=False,
                outcome=PR08RecoveryOutcome.ALREADY_PROCESSED_BLOCKED,
                message_id=message_id,
                uetr=effective_uetr,
                source_queue=meta.source_queue,
                diff_summary="Funds already debited in downstream engine",
                audit_trail=trail,
                error_message="Message already completed financial debit. Re-enqueue prohibited."
            )

        if settle_record and settle_record.ledger_status == "POSTED_DEBITED":
            trail.append("Stage 5 FAILED: Settlement ledger confirms transaction is already POSTED_DEBITED. Duplicate release blocked.")
            return PR08QueueRecoveryResult(
                success=False,
                outcome=PR08RecoveryOutcome.SETTLEMENT_CONFLICT_BLOCKED,
                message_id=message_id,
                uetr=effective_uetr,
                source_queue=meta.source_queue,
                diff_summary="Settlement ledger confirms debit already posted",
                audit_trail=trail,
                error_message="Duplicate financial release blocked by settlement ledger authority."
            )

        # 6. Poison Message Classification
        if meta.is_poison or meta.error_code in policy.poison_error_codes or proc_state.status == MessageProcessingStatus.FAILED_POISON:
            trail.append(f"Stage 6 FAILED (Poison Message): Error '{meta.error_code}' is classified as POISON. Halting automatic retry loop.")
            return PR08QueueRecoveryResult(
                success=False,
                outcome=PR08RecoveryOutcome.POISON_MESSAGE_HALTED,
                message_id=message_id,
                uetr=effective_uetr,
                source_queue=meta.source_queue,
                retry_count=meta.retry_count,
                max_retries=meta.max_retries,
                is_poison=True,
                diff_summary=f"Poison message isolated: {meta.error_code}",
                audit_trail=trail,
                error_message=f"Poison message ({meta.error_code}) prohibited from entering retry loop. Preserved for operator inspection."
            )

        # 7. Max Retries Boundary
        if meta.retry_count >= policy.max_retry_count:
            trail.append(f"Stage 7 FAILED: Retry count ({meta.retry_count}) has reached policy maximum ({policy.max_retry_count}).")
            return PR08QueueRecoveryResult(
                success=False,
                outcome=PR08RecoveryOutcome.MAX_RETRIES_EXCEEDED,
                message_id=message_id,
                uetr=effective_uetr,
                source_queue=meta.source_queue,
                retry_count=meta.retry_count,
                max_retries=policy.max_retry_count,
                diff_summary=f"Max retries exceeded ({meta.retry_count}/{policy.max_retry_count})",
                audit_trail=trail,
                error_message=f"Maximum automated retries ({policy.max_retry_count}) exceeded. Escalating to Operations Desk."
            )

        # 8. Error Code Transient Eligibility Check
        if meta.error_code not in policy.allowed_transient_error_codes:
            trail.append(f"Stage 8 FAILED: Error code '{meta.error_code}' is not in policy permitted transient error classes.")
            return PR08QueueRecoveryResult(
                success=False,
                outcome=PR08RecoveryOutcome.UNRECOVERABLE_ERROR,
                message_id=message_id,
                uetr=effective_uetr,
                source_queue=meta.source_queue,
                retry_count=meta.retry_count,
                max_retries=policy.max_retry_count,
                diff_summary=f"Unrecognized error class: {meta.error_code}",
                audit_trail=trail,
                error_message=f"Error code '{meta.error_code}' is not recognized as a recoverable transient condition."
            )

        # 9. Payload Evaluation & Optional PR-05 Subsidiary Repair
        # Check if payload has unparseable control characters or charset corruption
        repaired_payload = raw_payload
        pr05_res: Optional[PR05TransformationResult] = None
        has_charset_condition = any(ord(c) < 32 and c not in '\r\n\t' for c in raw_payload)

        if has_charset_condition:
            trail.append("Stage 9 (Subsidiary PR-05): Detected unparseable control bytes in payload. Invoking PR-05 governed transformer.")
            pr05_res = pr05_transformer.transform(raw_payload)
            if pr05_res.success:
                repaired_payload = pr05_res.transformed_payload
                trail.append(f"Stage 9 (PR-05 Success): Removed {pr05_res.control_characters_removed_count} control characters via PR-05.")
            else:
                trail.append("Stage 9 FAILED: PR-05 subsidiary transformation failed. Classifying as poison.")
                return PR08QueueRecoveryResult(
                    success=False,
                    outcome=PR08RecoveryOutcome.POISON_MESSAGE_HALTED,
                    message_id=message_id,
                    uetr=effective_uetr,
                    source_queue=meta.source_queue,
                    is_poison=True,
                    diff_summary="Payload failed PR-05 transformation",
                    audit_trail=trail,
                    error_message="Subsidiary PR-05 character transformation failed on corrupt payload."
                )

        # 10. Construct Governed Re-Enqueue Candidate
        candidate_id = f"CAND-PR08-RESET-{hashlib.sha256(message_id.encode()).hexdigest()[:8]}"
        target_dest = meta.target_requeue_destination or meta.source_queue

        diff_text = (
            f"Reset message '{message_id}' (attempt {meta.retry_count + 1}/{policy.max_retry_count}) to queue '{target_dest}' after transient error '{meta.error_code}'"
        )
        if pr05_res:
            diff_text += f" [Subsidiary PR-05: {pr05_res.control_characters_removed_count} control bytes removed]"

        candidate = ResolutionCandidate(
            candidate_id=candidate_id,
            repaired_payload=repaired_payload,
            diff_summary=diff_text,
            derivation_method="MESSAGE_BROKER_GOVERNED_RECOVERY_ENGINE",
            is_lossless=True
        )

        outcome_status = PR08RecoveryOutcome.SUBSIDIARY_CHARSET_REPAIRED if pr05_res else PR08RecoveryOutcome.TRANSIENT_REQUEUE_ELIGIBLE
        trail.append(f"Stage 10 (Candidate Generation): Deterministic re-enqueue candidate generated for queue '{target_dest}'.")

        return PR08QueueRecoveryResult(
            success=True,
            outcome=outcome_status,
            message_id=message_id,
            uetr=effective_uetr,
            source_queue=meta.source_queue,
            target_requeue_destination=target_dest,
            retry_count=meta.retry_count,
            max_retries=policy.max_retry_count,
            is_poison=False,
            requires_subsidiary_pr05=(pr05_res is not None),
            pr05_transformation_result=pr05_res,
            candidates=[candidate],
            uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
            is_lossless=True,
            diff_summary=diff_text,
            audit_trail=trail
        )


# Global singleton engine instance
pr08_queue_recovery_engine = PR08QueueRecoveryEngine()
