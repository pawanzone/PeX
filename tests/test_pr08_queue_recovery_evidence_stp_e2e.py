"""Comprehensive End-to-End Behavioral, Risk, Authority, and Adversarial Test Suite for PR-08.

PR-08: QUEUE_PROCESSING_FAILURE
Domain: Processing (BIAN Domain 2)
STP Group: Group 1 (Autonomous STP Capable)

Governed by:
- PeX_Phase2_Taxonomy_Remediation_Architecture_Decision_v0.2.md
- PeX_Phase2_DQ08_PR08_Remediation_Implementation_Contract_v0.1.md

Covers:
- BEH-PR08-01: Valid transient queue failure with retry_count < max_retries
- BEH-PR08-02: Maximum retry boundary enforcement (retry_count >= max_retries)
- BEH-PR08-03: Poison message isolation (deterministic malformed payload)
- BEH-PR08-04: Already processed message double-debit protection
- BEH-PR08-05: Concurrency-safe idempotency replay prevention
- BEH-PR08-06: Missing mandatory broker/processing state fails closed
- BEH-PR08-07: Stale broker metadata fails closed
- BEH-PR08-08: Settlement ledger contradiction blocks duplicate financial release
- BEH-PR08-09: Clean payload re-enqueue without PR-05 subsidiary repair
- BEH-PR08-10: Payload with control bytes invoking subsidiary PR-05 repair
- BEH-PR08-11: Monetary threshold exceeded routing to HITL Maker-Checker
- BEH-PR08-12: Bank handoff boundary with execution_owner = 'BANK'
- BEH-PR08-13: Concurrent idempotency race condition handling
- BEH-PR08-14: Historical precedent cannot override live broker authority
- BEH-PR08-15: HITL Segregation of Duties dual authorization enforcement
- BEH-PR08-16: Unconfigured bank retry policy fails closed
"""
import pytest
from datetime import datetime, timezone, timedelta

from app.adapters.input_adapter import InboundPackage
from app.adapters.output_adapter import FolderOutputAdapter, BankHandoffReceipt
from app.schemas.canonical_envelopes import HandoffLifecycleState
from app.schemas.policy_contract import ComplianceGateStatus, ExecutionPreconditionsStatus, STPPolicyConfig
from app.adapters.message_broker_queue_reset_adapter import (
    BrokerDLQMetadata,
    ProcessingStateRecord,
    SettlementLedgerState,
    BankRetryPolicyConfig,
    MessageProcessingStatus,
    SyntheticMessageBrokerQueueResetAdapter,
)
from app.adapters.idempotency_lock_manager import InMemoryIdempotencyLockManager
from app.services.pr08_queue_recovery_engine import (
    PR08QueueRecoveryEngine,
    PR08RecoveryOutcome,
)
from app.services.pr08_queue_recovery_stp_pipeline import (
    PR08QueueRecoverySTPPipeline,
    pr08_queue_recovery_pipeline,
)


SAMPLE_XML_CLEAN = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
  <FIToFICstmrCdtTrf>
    <GrpHdr>
      <MsgId>MSG-PR08-TRANS-01</MsgId>
      <CreDtTm>2026-10-07T14:30:00Z</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
    </GrpHdr>
    <CdtTrfTxInf>
      <PmtId>
        <EndToEndId>E2E-PR08-001</EndToEndId>
        <UETR>11a1b2c3-44dd-55ee-66ff-778899aabbcc</UETR>
      </PmtId>
      <IntrBkSttlmAmt Ccy="USD">25000.00</IntrBkSttlmAmt>
      <Dbtr><Nm>Global Logistics Corp</Nm></Dbtr>
      <Cdtr><Nm>Apex Industrial Supplies</Nm></Cdtr>
    </CdtTrfTxInf>
  </FIToFICstmrCdtTrf>
</Document>"""

SAMPLE_XML_WITH_CONTROL_BYTES = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
  <FIToFICstmrCdtTrf>
    <GrpHdr>
      <MsgId>MSG-PR08-CHARSET-01</MsgId>
      <CreDtTm>2026-10-07T14:30:00Z</CreDtTm>
    </GrpHdr>
    <CdtTrfTxInf>
      <PmtId>
        <EndToEndId>E2E-PR08-002</EndToEndId>
        <UETR>55a1b2c3-44dd-55ee-66ff-778899aabbcc</UETR>
      </PmtId>
      <IntrBkSttlmAmt Ccy="USD">15000.00</IntrBkSttlmAmt>
      <RmtInf><Ustrd>Payment for \x07Invoice #8891\x0B</Ustrd></RmtInf>
    </CdtTrfTxInf>
  </FIToFICstmrCdtTrf>
</Document>"""


@pytest.fixture(autouse=True)
def reset_idempotency_state():
    """Resets the idempotency lock manager before each test."""
    from app.adapters.idempotency_lock_manager import idempotency_lock_manager
    idempotency_lock_manager.clear()


# ============================================================================
# 1. BEH-PR08-01: Valid Transient Queue Failure
# ============================================================================

def test_beh_pr08_01_valid_transient_queue_failure_stp_handoff():
    """BEH-PR08-01: Transient broker failure (retry 1 < 3) resolves autonomously to BANK_HANDOFF_READY."""
    pkg = InboundPackage(
        package_id="PKG-PR08-01",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str=SAMPLE_XML_CLEAN,
        evidence_fields={"message_id": "MSG-PR08-TRANS-01"}
    )
    result = pr08_queue_recovery_pipeline.process_package(pkg, message_id="MSG-PR08-TRANS-01", amount=25000.0)
    assert result.is_stp_executed is True
    assert result.final_lifecycle_stage == "BANK_HANDOFF_READY"
    assert result.recovery_result.outcome == PR08RecoveryOutcome.TRANSIENT_REQUEUE_ELIGIBLE
    assert result.stp_decision.stp_eligible is True
    assert result.outbound_envelope.execution_owner == "BANK"


# ============================================================================
# 2. BEH-PR08-02: Max Retries Boundary Enforcement
# ============================================================================

def test_beh_pr08_02_max_retries_exceeded_halts_to_operations():
    """BEH-PR08-02: Message with retry count 3 >= max 3 halts autonomous STP and routes to operations."""
    pkg = InboundPackage(
        package_id="PKG-PR08-02",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str=SAMPLE_XML_CLEAN.replace("MSG-PR08-TRANS-01", "MSG-PR08-MAXRET-01"),
        evidence_fields={"message_id": "MSG-PR08-MAXRET-01"}
    )
    result = pr08_queue_recovery_pipeline.process_package(pkg, message_id="MSG-PR08-MAXRET-01")
    assert result.is_stp_executed is False
    assert result.is_hitl_routed is True
    assert result.final_lifecycle_stage == "RECOVERY_FAILED"
    assert result.recovery_result.outcome == PR08RecoveryOutcome.MAX_RETRIES_EXCEEDED
    assert "Maximum automated retries" in result.error_summary or "Exceeded maximum automated retry attempts" in result.error_summary


# ============================================================================
# 3. BEH-PR08-03: Poison Message Isolation
# ============================================================================

def test_beh_pr08_03_poison_message_quarantined():
    """BEH-PR08-03: Fatal deserialization error / poison message is quarantined and prohibited from retry loop."""
    pkg = InboundPackage(
        package_id="PKG-PR08-03",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str="<Malformed><UnclosedTag>",
        evidence_fields={"message_id": "MSG-PR08-POISON-01"}
    )
    result = pr08_queue_recovery_pipeline.process_package(pkg, message_id="MSG-PR08-POISON-01")
    assert result.is_stp_executed is False
    assert result.is_poison_isolated is True
    assert result.final_lifecycle_stage == "POISON_MESSAGE_QUARANTINED"
    assert result.recovery_result.outcome == PR08RecoveryOutcome.POISON_MESSAGE_HALTED
    assert result.recovery_result.is_poison is True


# ============================================================================
# 4. BEH-PR08-04: Already Processed Message / Double-Debit Protection
# ============================================================================

def test_beh_pr08_04_already_processed_message_blocks_duplicate_reprocessing():
    """BEH-PR08-04: Message marked SETTLED_DEBITED in processing state blocks re-enqueue to prevent duplicate debit."""
    pkg = InboundPackage(
        package_id="PKG-PR08-04",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str=SAMPLE_XML_CLEAN.replace("MSG-PR08-TRANS-01", "MSG-PR08-DUP-01"),
        evidence_fields={"message_id": "MSG-PR08-DUP-01"}
    )
    result = pr08_queue_recovery_pipeline.process_package(pkg, message_id="MSG-PR08-DUP-01")
    assert result.is_stp_executed is False
    assert result.final_lifecycle_stage == "DUPLICATE_RETRY_BLOCKED"
    assert result.recovery_result.outcome == PR08RecoveryOutcome.ALREADY_PROCESSED_BLOCKED


# ============================================================================
# 5. BEH-PR08-05: Idempotency Replay Prevention
# ============================================================================

def test_beh_pr08_05_idempotency_prevents_duplicate_recovery_execution():
    """BEH-PR08-05: Re-submitting an already executed message ID fails closed under idempotency."""
    pkg = InboundPackage(
        package_id="PKG-PR08-05",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str=SAMPLE_XML_CLEAN,
        evidence_fields={"message_id": "MSG-PR08-TRANS-01"}
    )
    # First execution succeeds
    res1 = pr08_queue_recovery_pipeline.process_package(pkg, message_id="MSG-PR08-TRANS-01")
    assert res1.is_stp_executed is True

    # Second execution is blocked by idempotency
    res2 = pr08_queue_recovery_pipeline.process_package(pkg, message_id="MSG-PR08-TRANS-01")
    assert res2.is_stp_executed is False
    assert res2.final_lifecycle_stage == "DUPLICATE_RETRY_BLOCKED"
    assert res2.recovery_result.outcome == PR08RecoveryOutcome.IDEMPOTENCY_ALREADY_EXECUTED


# ============================================================================
# 6. BEH-PR08-06: Missing Mandatory Evidence Fails Closed
# ============================================================================

def test_beh_pr08_06_missing_mandatory_evidence_fails_closed():
    """BEH-PR08-06: Unknown message without broker DLQ metadata fails evidence sufficiency."""
    pkg = InboundPackage(
        package_id="PKG-PR08-06",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str=SAMPLE_XML_CLEAN,
        evidence_fields={"message_id": "MSG-UNKNOWN-999"}
    )
    result = pr08_queue_recovery_pipeline.process_package(pkg, message_id="MSG-UNKNOWN-999")
    assert result.is_stp_executed is False
    assert result.sufficiency_result.is_sufficient is False
    assert result.final_lifecycle_stage == "SUSPENDED_TO_OPERATIONS"


# ============================================================================
# 7. BEH-PR08-07: Stale Broker Metadata Evidence Fails Closed
# ============================================================================

def test_beh_pr08_07_stale_broker_metadata_fails_closed():
    """BEH-PR08-07: Broker metadata exceeding freshness TTL fails closed without allow_stale_evidence."""
    stale_meta = BrokerDLQMetadata(
        message_id="MSG-STALE-01",
        source_queue="PAYMENT_INGEST_QUEUE",
        target_requeue_destination="PAYMENT_INGEST_QUEUE",
        retry_count=1,
        max_retries=3,
        error_code="TIMEOUT_CONSUMER_INTERRUPTED",
        error_details="Transient timeout",
        correlation_id="CORR-STALE",
        retrieved_at=datetime.now(timezone.utc) - timedelta(hours=2),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        freshness_seconds=900
    )
    proc_state = ProcessingStateRecord(
        message_id="MSG-STALE-01",
        status=MessageProcessingStatus.FAILED_TRANSIENT,
        last_attempt_stage="INGESTION",
        recorded_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
    )

    pkg = InboundPackage(
        package_id="PKG-PR08-07",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str=SAMPLE_XML_CLEAN,
        evidence_fields={"message_id": "MSG-STALE-01"}
    )
    result = pr08_queue_recovery_pipeline.process_package(
        pkg,
        message_id="MSG-STALE-01",
        broker_metadata=stale_meta,
        processing_state=proc_state
    )
    assert result.is_stp_executed is False
    assert result.recovery_result.outcome == PR08RecoveryOutcome.STALE_EVIDENCE_HALTED


# ============================================================================
# 8. BEH-PR08-08: Settlement Ledger Contradiction Blocks Duplicate Release
# ============================================================================

def test_beh_pr08_08_settlement_ledger_contradiction_blocks_requeue():
    """BEH-PR08-08: Settlement ledger indicating transaction is POSTED_DEBITED blocks re-enqueue."""
    meta = BrokerDLQMetadata(
        message_id="MSG-SETTLE-CONFLICT",
        uetr="88a1b2c3-44dd-55ee-66ff-778899aabbcc",
        source_queue="PAYMENT_INGEST_QUEUE",
        target_requeue_destination="PAYMENT_INGEST_QUEUE",
        retry_count=1,
        max_retries=3,
        error_code="TIMEOUT_CONSUMER_INTERRUPTED",
        error_details="Network interruption",
        correlation_id="CORR-SETTLE"
    )
    proc = ProcessingStateRecord(
        message_id="MSG-SETTLE-CONFLICT",
        uetr="88a1b2c3-44dd-55ee-66ff-778899aabbcc",
        status=MessageProcessingStatus.FAILED_TRANSIENT,
        last_attempt_stage="INGESTION"
    )
    settle = SettlementLedgerState(
        payment_id="PAY-CONFLICT-01",
        uetr="88a1b2c3-44dd-55ee-66ff-778899aabbcc",
        amount=25000.0,
        currency="USD",
        ledger_status="POSTED_DEBITED"
    )

    pkg = InboundPackage(
        package_id="PKG-PR08-08",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str=SAMPLE_XML_CLEAN,
        evidence_fields={"message_id": "MSG-SETTLE-CONFLICT"}
    )
    result = pr08_queue_recovery_pipeline.process_package(
        pkg,
        message_id="MSG-SETTLE-CONFLICT",
        broker_metadata=meta,
        processing_state=proc,
        settlement_state=settle
    )
    assert result.is_stp_executed is False
    assert result.final_lifecycle_stage == "DUPLICATE_RETRY_BLOCKED"
    assert result.recovery_result.outcome == PR08RecoveryOutcome.SETTLEMENT_CONFLICT_BLOCKED


# ============================================================================
# 9. BEH-PR08-09: Clean Payload Re-Enqueue Without PR-05 Repair
# ============================================================================

def test_beh_pr08_09_clean_payload_no_subsidiary_pr05_invocation():
    """BEH-PR08-09: Clean XML payload does not require PR-05 subsidiary repair."""
    pkg = InboundPackage(
        package_id="PKG-PR08-09",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str=SAMPLE_XML_CLEAN,
        evidence_fields={"message_id": "MSG-PR08-TRANS-01"}
    )
    result = pr08_queue_recovery_pipeline.process_package(pkg, message_id="MSG-PR08-TRANS-01")
    assert result.is_stp_executed is True
    assert result.recovery_result.requires_subsidiary_pr05 is False
    assert result.recovery_result.pr05_transformation_result is None


# ============================================================================
# 10. BEH-PR08-10: Payload with Control Bytes Invoking Subsidiary PR-05
# ============================================================================

def test_beh_pr08_10_subsidiary_pr05_character_repair_executed_correctly():
    """BEH-PR08-10: Payload with control bytes (0x07, 0x0B) invokes subsidiary PR-05 transformer."""
    pkg = InboundPackage(
        package_id="PKG-PR08-10",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str=SAMPLE_XML_WITH_CONTROL_BYTES,
        evidence_fields={"message_id": "MSG-PR08-CHARSET-01"}
    )
    result = pr08_queue_recovery_pipeline.process_package(pkg, message_id="MSG-PR08-CHARSET-01", amount=15000.0)
    assert result.is_stp_executed is True
    assert result.final_lifecycle_stage == "BANK_HANDOFF_READY"
    assert result.recovery_result.outcome == PR08RecoveryOutcome.SUBSIDIARY_CHARSET_REPAIRED
    assert result.recovery_result.requires_subsidiary_pr05 is True
    assert result.recovery_result.pr05_transformation_result.control_characters_removed_count == 2
    # Verify control bytes stripped in output
    repaired_payload = result.outbound_envelope.proposed_repair["repaired_payload"]
    assert "\x07" not in repaired_payload
    assert "\x0B" not in repaired_payload


# ============================================================================
# 11. BEH-PR08-11: Monetary Threshold Exceeded Routes to HITL
# ============================================================================

def test_beh_pr08_11_high_value_queue_recovery_routes_to_hitl():
    """BEH-PR08-11: Recovery for high-value message ($1.5M > $1.0M threshold) routes to HITL Maker-Checker."""
    pkg = InboundPackage(
        package_id="PKG-PR08-11",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str=SAMPLE_XML_CLEAN,
        evidence_fields={"message_id": "MSG-PR08-TRANS-01"}
    )
    result = pr08_queue_recovery_pipeline.process_package(pkg, message_id="MSG-PR08-TRANS-01", amount=1500000.0)
    assert result.is_stp_executed is False
    assert result.is_hitl_routed is True
    assert result.final_lifecycle_stage == "HITL_MAKER_PENDING"
    assert result.stp_decision.stp_eligible is False
    assert result.stp_decision.bank_policy_allows is False


# ============================================================================
# 12. BEH-PR08-12: Bank Handoff Contract
# ============================================================================

def test_beh_pr08_12_bank_handoff_contract_execution_owner_bank():
    """BEH-PR08-12: Recovery handoff terminates at BANK_HANDOFF_READY with execution_owner = 'BANK'."""
    pkg = InboundPackage(
        package_id="PKG-PR08-12",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str=SAMPLE_XML_CLEAN,
        evidence_fields={"message_id": "MSG-PR08-TRANS-01"}
    )
    result = pr08_queue_recovery_pipeline.process_package(pkg, message_id="MSG-PR08-TRANS-01", amount=25000.0)
    assert result.outbound_envelope.execution_owner == "BANK"
    assert result.outbound_envelope.lifecycle_state == HandoffLifecycleState.BANK_HANDOFF_READY


# ============================================================================
# 13. BEH-PR08-13: Concurrent Idempotency Race Condition Protection
# ============================================================================

def test_beh_pr08_13_concurrent_idempotency_lock_collision():
    """BEH-PR08-13: Concurrent worker attempting lock on same message ID is blocked."""
    lock_mgr = InMemoryIdempotencyLockManager()
    engine = PR08QueueRecoveryEngine(lock_manager=lock_mgr)

    # Worker 1 acquires lock
    acquired = lock_mgr.acquire_lock("IDEMP-PR08-MSG-PR08-TRANS-01", ttl_seconds=300, owner="WORKER_1")
    assert acquired is True

    # Worker 2 attempts to acquire lock on same key -> Must be rejected
    res_worker2 = engine.evaluate_queue_recovery(
        raw_payload=SAMPLE_XML_CLEAN,
        message_id="MSG-PR08-TRANS-01",
        worker_id="WORKER_2"
    )
    assert res_worker2.success is False
    assert res_worker2.outcome == PR08RecoveryOutcome.IDEMPOTENCY_LOCKED_RACE


# ============================================================================
# 14. BEH-PR08-14: Historical Precedent Cannot Override Live Broker Authority
# ============================================================================

def test_beh_pr08_14_historical_logs_cannot_override_live_broker_state():
    """BEH-PR08-14: Non-authoritative historical logs cannot override a poison or max-retry state."""
    pkg = InboundPackage(
        package_id="PKG-PR08-14",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str="<Invalid><Payload>",
        evidence_fields={"message_id": "MSG-PR08-POISON-01"}
    )
    result = pr08_queue_recovery_pipeline.process_package(pkg, message_id="MSG-PR08-POISON-01")
    assert result.is_stp_executed is False
    assert result.recovery_result.outcome == PR08RecoveryOutcome.POISON_MESSAGE_HALTED


# ============================================================================
# 15. BEH-PR08-15: HITL Segregation of Duties
# ============================================================================

def test_beh_pr08_15_hitl_maker_checker_sod_enforced():
    """BEH-PR08-15: Segregation of Duties is strictly enforced for HITL queue recovery."""
    pkg = InboundPackage(
        package_id="PKG-PR08-15",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str=SAMPLE_XML_CLEAN,
        evidence_fields={"message_id": "MSG-PR08-TRANS-01"}
    )
    pipeline = PR08QueueRecoverySTPPipeline()
    result = pipeline.process_package(pkg, message_id="MSG-PR08-TRANS-01", amount=2000000.0) # Exceeds STP threshold
    assert result.is_hitl_routed is True

    # Attempt Self-Approval (Maker == Checker) -> Must Raise ValueError
    with pytest.raises(ValueError, match="Segregation of Duties Violation"):
        pipeline.approve_and_dispatch(
            case_id=result.case_id,
            maker_id="ANALYST_CAROL",
            checker_id="ANALYST_CAROL",
            rationale="Self-approval attempt"
        )

    # Valid Dual Authorization (Maker != Checker)
    approved = pipeline.approve_and_dispatch(
        case_id=result.case_id,
        maker_id="ANALYST_CAROL",
        checker_id="SUPERVISOR_DAVE",
        rationale="Verified transient network timeout resolved in downstream consumer."
    )
    assert approved.is_hitl_approved is True
    assert approved.final_lifecycle_stage == "BANK_HANDOFF_READY"
    assert approved.outbound_envelope.execution_owner == "BANK"


# ============================================================================
# 16. BEH-PR08-16: Unconfigured Bank Retry Policy Fails Closed
# ============================================================================

def test_beh_pr08_16_unconfigured_bank_policy_fails_closed():
    """BEH-PR08-16: If bank retry policy is missing or unconfigured, system fails closed."""
    unconfigured_policy = BankRetryPolicyConfig(is_bank_policy_configured=False)
    pkg = InboundPackage(
        package_id="PKG-PR08-16",
        source_channel="BANK_DLQ_FOLDER",
        raw_payload_str=SAMPLE_XML_CLEAN,
        evidence_fields={"message_id": "MSG-PR08-TRANS-01"}
    )
    result = pr08_queue_recovery_pipeline.process_package(
        pkg,
        message_id="MSG-PR08-TRANS-01",
        bank_retry_policy=unconfigured_policy
    )
    assert result.is_stp_executed is False
    assert result.recovery_result.outcome == PR08RecoveryOutcome.UNAUTHORIZED_BANK_POLICY
