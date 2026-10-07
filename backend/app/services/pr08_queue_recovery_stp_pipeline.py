"""End-to-End PR-08 (QUEUE_PROCESSING_FAILURE) Evidence-Driven STP Recovery Pipeline.

Orchestrates the complete governed 12-stage lifecycle for PR-08 queue recovery:
Intake -> Dossier Assembly -> Evidence Sufficiency -> Queue Recovery Engine (Idempotency & Broker State)
-> Resolution Determination -> Authority Validation -> Bank Policy -> Compliance -> Preconditions
-> STP Eligibility -> Bank Handoff -> Audit Logging.

Governed by:
- PeX_Phase2_Taxonomy_Remediation_Architecture_Decision_v0.2.md
- PeX_Phase2_DQ08_PR08_Remediation_Implementation_Contract_v0.1.md
"""
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.schemas.evidence_contract import EvidenceDossier, EvidenceItem, EvidenceTrustTier
from app.schemas.canonical_envelopes import (
    CanonicalIntakeEnvelope,
    CanonicalOutboundEnvelope,
    HandoffLifecycleState,
)
from app.schemas.policy_contract import (
    STPPolicyConfig,
    ComplianceGateStatus,
    ExecutionPreconditionsStatus,
)
from app.schemas.resolution_contract import (
    ResolutionCandidate,
    ResolutionResult,
    ResolutionStatus,
    ResolutionUniqueness,
)
from app.schemas.authority_contract import (
    AuthorityValidationResult,
    AuthorityValidationStatus,
)
from app.services.sufficiency_engine import (
    sufficiency_engine,
    EvidenceSufficiencyResult,
    EvidenceSufficiencyStatus,
)
from app.services.evidence_stp_evaluator import (
    evidence_stp_evaluator,
    STPEligibilityDecision,
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
from app.services.pr08_queue_recovery_engine import (
    PR08QueueRecoveryEngine,
    pr08_queue_recovery_engine,
    PR08QueueRecoveryResult,
    PR08RecoveryOutcome,
)
from app.adapters.input_adapter import InboundPackage, FolderInputAdapter
from app.adapters.output_adapter import FolderOutputAdapter, BankHandoffReceipt
from app.services.audit_service import audit_service


class PR08QueueRecoveryPipelineResult(BaseModel):
    """Complete forensic result of executing the PR-08 Queue Recovery STP Pipeline."""
    case_id: str
    profile_id: str = "PR-08"
    idempotency_hash: str
    message_id: str
    uetr: Optional[str] = None
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Evidence & Engines:
    sufficiency_result: Optional[EvidenceSufficiencyResult] = None
    recovery_result: Optional[PR08QueueRecoveryResult] = None
    resolution_result: Optional[ResolutionResult] = None
    authority_result: Optional[AuthorityValidationResult] = None
    stp_decision: Optional[STPEligibilityDecision] = None
    handoff_receipt: Optional[BankHandoffReceipt] = None
    outbound_envelope: Optional[CanonicalOutboundEnvelope] = None

    # Lifecycle State & Governance:
    final_lifecycle_stage: str
    is_stp_executed: bool
    is_hitl_routed: bool = False
    is_hitl_approved: bool = False
    is_poison_isolated: bool = False
    recommended_routing: str
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)
    error_summary: Optional[str] = None


class PR08QueueRecoverySTPPipeline:
    """Master orchestrator for PR-08 (QUEUE_PROCESSING_FAILURE) Straight-Through Processing."""

    def __init__(
        self,
        recovery_engine: Optional[PR08QueueRecoveryEngine] = None,
        input_adapter: Optional[FolderInputAdapter] = None,
        output_adapter: Optional[FolderOutputAdapter] = None,
        policy_config: Optional[STPPolicyConfig] = None
    ):
        self.recovery_engine = recovery_engine or pr08_queue_recovery_engine
        self.input_adapter = input_adapter or FolderInputAdapter()
        self.output_adapter = output_adapter or FolderOutputAdapter()
        self.policy_config = policy_config or STPPolicyConfig(
            max_stp_amount=1000000.0,
            dual_auth_threshold=1000000.0
        )
        self._case_store: Dict[str, Dict[str, Any]] = {}

    def process_package(
        self,
        package: InboundPackage,
        message_id: Optional[str] = None,
        uetr: Optional[str] = None,
        amount: float = 25000.0,
        currency: str = "USD",
        broker_metadata: Optional[BrokerDLQMetadata] = None,
        processing_state: Optional[ProcessingStateRecord] = None,
        settlement_state: Optional[SettlementLedgerState] = None,
        bank_retry_policy: Optional[BankRetryPolicyConfig] = None,
        compliance_status: ComplianceGateStatus = ComplianceGateStatus.PASS,
        execution_preconditions: ExecutionPreconditionsStatus = ExecutionPreconditionsStatus.PASS,
        allow_stale_evidence: bool = False,
        worker_id: str = "PEX_WORKER_1"
    ) -> PR08QueueRecoveryPipelineResult:
        """Executes the full 12-stage lifecycle for an inbound PR-08 DLQ exception package."""
        raw_payload = package.raw_payload_str
        msg_id = message_id or package.evidence_fields.get("message_id") or package.package_id
        idemp_hash = hashlib.sha256(f"{msg_id}:{raw_payload}".encode("utf-8")).hexdigest()
        case_id = f"CASE-PR08-QREC-{idemp_hash[:8]}"

        # Audit Ingestion Event
        audit_service.log_event(
            case_id=case_id,
            correlation_id=idemp_hash,
            stage_name="INGESTION",
            actor_id="SYSTEM_DLQ_WATCHER",
            actor_role="SYSTEM",
            action_name="DLQ_EXCEPTION_INGESTED",
            details=f"Ingested PR-08 DLQ package {package.package_id} for message {msg_id}",
            amount=amount,
            currency=currency
        )

        # Stage 1: Build Evidence Dossier
        dossier = EvidenceDossier(case_id=case_id, profile_id="PR-08")
        dossier.add_item(EvidenceItem(
            item_name="DLQ_MESSAGE_PAYLOAD",
            source_name="BANK_DLQ_FOLDER",
            trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
            payload={"raw_text": raw_payload}
        ))

        meta = broker_metadata or self.recovery_engine.broker_adapter.get_dlq_metadata(msg_id)
        if meta:
            dossier.add_item(EvidenceItem(
                item_name="BROKER_DLQ_METADATA",
                source_name="MESSAGE_BROKER_CONNECTOR",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload=meta.model_dump()
            ))

        proc_state = processing_state or self.recovery_engine.broker_adapter.get_processing_state(msg_id)
        if proc_state:
            dossier.add_item(EvidenceItem(
                item_name="PROCESSING_STATE_RECORD",
                source_name="CORE_PAYMENT_ENGINE",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload=proc_state.model_dump()
            ))

        effective_uetr = uetr or (meta.uetr if meta else None) or (proc_state.uetr if proc_state else None)
        settle_rec = settlement_state or (self.recovery_engine.broker_adapter.get_settlement_state(effective_uetr) if effective_uetr else None)
        if settle_rec:
            dossier.add_item(EvidenceItem(
                item_name="SETTLEMENT_LEDGER_STATE",
                source_name="RTGS_SETTLEMENT_LEDGER",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload=settle_rec.model_dump()
            ))

        # Evaluate Evidence Sufficiency
        has_mandatory = (
            dossier.get_item("DLQ_MESSAGE_PAYLOAD") is not None and
            dossier.get_item("BROKER_DLQ_METADATA") is not None and
            dossier.get_item("PROCESSING_STATE_RECORD") is not None
        )
        suff_res = EvidenceSufficiencyResult(
            case_id=case_id,
            profile_id="PR-08",
            status=EvidenceSufficiencyStatus.SUFFICIENT if has_mandatory else EvidenceSufficiencyStatus.INSUFFICIENT_EVIDENCE,
            is_sufficient=has_mandatory,
            missing_mandatory_items=[] if has_mandatory else ["MANDATORY_BROKER_EVIDENCE_MISSING"]
        )

        if not suff_res.is_sufficient:
            return self._build_failure_result(case_id, idemp_hash, msg_id, effective_uetr, suff_res, "Prerequisite broker evidence missing. Suspended to Operations.", "OPERATIONS_DESK")

        # Stage 2: Execute Governed Queue Recovery Engine
        rec_res = self.recovery_engine.evaluate_queue_recovery(
            raw_payload=raw_payload,
            message_id=msg_id,
            uetr=effective_uetr,
            broker_metadata=meta,
            processing_state=proc_state,
            settlement_state=settle_rec,
            policy_config=bank_retry_policy,
            allow_stale_evidence=allow_stale_evidence,
            worker_id=worker_id
        )

        # Map to Canonical Resolution Result
        canon_res_status = ResolutionStatus.RESOLUTION_DETERMINED if rec_res.success else ResolutionStatus.RESOLUTION_NOT_DETERMINED
        canon_res = ResolutionResult(
            profile_id="PR-08",
            status=canon_res_status,
            uniqueness=rec_res.uniqueness,
            primary_candidate=rec_res.candidates[0] if rec_res.candidates else None,
            all_candidates=rec_res.candidates,
            is_lossless=rec_res.is_lossless,
            diff_summary=rec_res.diff_summary,
            error_message=rec_res.error_message
        )

        # Check Fail-Closed Branch Conditions:
        # 1. Poison Message
        if rec_res.outcome == PR08RecoveryOutcome.POISON_MESSAGE_HALTED:
            return self._build_poison_isolated_result(case_id, idemp_hash, msg_id, effective_uetr, suff_res, rec_res, canon_res, amount, currency)

        # 2. Duplicate / Already Processed / Double-Debit Risk
        if rec_res.outcome in (PR08RecoveryOutcome.ALREADY_PROCESSED_BLOCKED, PR08RecoveryOutcome.SETTLEMENT_CONFLICT_BLOCKED, PR08RecoveryOutcome.IDEMPOTENCY_ALREADY_EXECUTED):
            return self._build_duplicate_blocked_result(case_id, idemp_hash, msg_id, effective_uetr, suff_res, rec_res, canon_res, amount, currency)

        # 3. Max Retries or Unrecoverable Failure
        if not rec_res.success:
            return self._build_unrecoverable_result(case_id, idemp_hash, msg_id, effective_uetr, suff_res, rec_res, canon_res, amount, currency)

        # Stage 3: Authority Validation ($V_{\text{det}}, V_{\text{auth}}$)
        v_det_passed = rec_res.success and (canon_res.primary_candidate is not None)
        v_auth_passed = rec_res.success and (meta is not None) and (proc_state is not None)
        auth_status = AuthorityValidationStatus.PASSED if (v_det_passed and v_auth_passed) else AuthorityValidationStatus.FAILED

        auth_res = AuthorityValidationResult(
            profile_id="PR-08",
            status=auth_status,
            is_valid=(v_det_passed and v_auth_passed),
            is_structural_syntax_valid=v_det_passed,
            is_business_authority_confirmed=v_auth_passed,
            authoritative_source="MESSAGE_BROKER_STATE / EXECUTION_ENGINE_LEDGER",
            details={"diff_summary": rec_res.diff_summary}
        )

        # Stage 4: Evaluate 8-Predicate STP Policy
        is_under_amount_cap = (amount <= self.policy_config.max_stp_amount)
        is_corridor_allowed = (currency.upper() in [c.upper() for c in self.policy_config.allowed_corridors])
        is_under_dual_auth = (amount < self.policy_config.dual_auth_threshold)
        is_auto_stp_enabled = self.policy_config.auto_stp_enabled
        p_bank_passed = is_under_amount_cap and is_corridor_allowed and is_under_dual_auth and is_auto_stp_enabled

        c_comp_passed = compliance_status == ComplianceGateStatus.PASS
        x_pre_passed = execution_preconditions == ExecutionPreconditionsStatus.PASS

        # Evaluate exact 8-predicate formula
        is_stp_eligible = (
            suff_res.is_sufficient and
            (canon_res.status == ResolutionStatus.RESOLUTION_DETERMINED) and
            (canon_res.uniqueness == ResolutionUniqueness.RESOLUTION_UNIQUE) and
            auth_res.is_structural_syntax_valid and
            auth_res.is_business_authority_confirmed and
            p_bank_passed and
            c_comp_passed and
            x_pre_passed
        )

        stp_dec = STPEligibilityDecision(
            case_id=case_id,
            profile_id="PR-08",
            stp_eligible=is_stp_eligible,
            evidence_sufficient=suff_res.is_sufficient,
            resolution_determined=(canon_res.status == ResolutionStatus.RESOLUTION_DETERMINED),
            resolution_unique=(canon_res.uniqueness == ResolutionUniqueness.RESOLUTION_UNIQUE),
            deterministic_validation_passed=auth_res.is_structural_syntax_valid,
            authority_validation_passed=auth_res.is_business_authority_confirmed,
            bank_policy_allows=p_bank_passed,
            compliance_gate_passed=c_comp_passed,
            execution_preconditions_satisfied=x_pre_passed,
            recommended_routing="AUTO_STP_DISPATCH" if is_stp_eligible else "MAKER_CHECKER_WORKLIST",
            audit_trail=[f"8-predicate evaluation completed: STP={'ELIGIBLE' if is_stp_eligible else 'HALTED'}"]
        )

        # If Policy Amount Ceiling Exceeded -> Route to HITL Maker-Checker
        if not p_bank_passed or not is_stp_eligible:
            return self._build_hitl_routed_result(case_id, idemp_hash, msg_id, effective_uetr, suff_res, rec_res, canon_res, auth_res, stp_dec, amount, currency, raw_payload)

        # Stage 5: Autonomous STP Execution & Bank Handoff
        repaired_text = canon_res.primary_candidate.repaired_payload
        original_info = {
            "case_id": case_id,
            "package_id": package.package_id,
            "message_id": msg_id,
            "uetr": effective_uetr,
            "amount": amount,
            "currency": currency,
            "target_queue": rec_res.target_requeue_destination
        }
        evidence_refs = [
            {
                "item_name": item.item_name,
                "trust_tier": item.trust_tier.value,
                "source": item.source_name,
                "is_valid": item.is_valid
            }
            for item in dossier.items.values()
        ]

        handoff_rcpt = self.output_adapter.emit_repaired_instruction(
            candidate=canon_res.primary_candidate,
            decision=stp_dec,
            filename_prefix=f"PEX_STP_PR08_{case_id}",
            original_payment_info=original_info,
            evidence_references=evidence_refs
        )
        outbound_env = self.output_adapter.get_outbound_envelope(handoff_rcpt.receipt_id)

        # Record Permanent Execution in Idempotency Manager
        self.recovery_engine.lock_manager.record_execution(f"IDEMP-PR08-{msg_id}", hashlib.sha256(repaired_text.encode()).hexdigest())

        # Audit Final Resolution
        audit_service.log_event(
            case_id=case_id,
            correlation_id=idemp_hash,
            stage_name="STP_DISPATCH",
            actor_id="PEX_QUEUE_RECOVERY_ENGINE",
            actor_role="SYSTEM",
            action_name="AUTO_STP_REQUEUE_RESOLVED",
            details=f"Autonomous queue reset completed for PR-08: {rec_res.diff_summary}",
            amount=amount,
            currency=currency
        )

        return PR08QueueRecoveryPipelineResult(
            case_id=case_id,
            profile_id="PR-08",
            idempotency_hash=idemp_hash,
            message_id=msg_id,
            uetr=effective_uetr,
            sufficiency_result=suff_res,
            recovery_result=rec_res,
            resolution_result=canon_res,
            authority_result=auth_res,
            stp_decision=stp_dec,
            handoff_receipt=handoff_rcpt,
            outbound_envelope=outbound_env,
            final_lifecycle_stage="BANK_HANDOFF_READY",
            is_stp_executed=True,
            is_hitl_routed=False,
            recommended_routing="BANK_RETRY_QUEUE"
        )

    def process_canonical_envelope(self, envelope: CanonicalIntakeEnvelope) -> PR08QueueRecoveryPipelineResult:
        """Helper method executing pipeline from a CanonicalIntakeEnvelope."""
        pkg = InboundPackage(
            package_id=envelope.message_id,
            source_channel="CANONICAL_ENVELOPE",
            raw_payload_str=envelope.raw_payload,
            evidence_fields=envelope.evidence_items
        )
        return self.process_package(
            package=pkg,
            message_id=envelope.message_id,
            uetr=envelope.uetr,
            amount=envelope.amount,
            currency=envelope.currency
        )

    # =========================================================================
    # Branch Helpers
    # =========================================================================

    def _build_failure_result(self, case_id: str, idemp_hash: str, msg_id: str, uetr: Optional[str], suff_res: Any, error_msg: str, routing: str) -> PR08QueueRecoveryPipelineResult:
        return PR08QueueRecoveryPipelineResult(
            case_id=case_id,
            profile_id="PR-08",
            idempotency_hash=idemp_hash,
            message_id=msg_id,
            uetr=uetr,
            sufficiency_result=suff_res,
            final_lifecycle_stage="SUSPENDED_TO_OPERATIONS",
            is_stp_executed=False,
            is_hitl_routed=True,
            recommended_routing=routing,
            error_summary=error_msg
        )

    def _build_poison_isolated_result(
        self,
        case_id: str,
        idemp_hash: str,
        msg_id: str,
        uetr: Optional[str],
        suff_res: Any,
        rec_res: Any,
        canon_res: Any,
        amount: float,
        currency: str
    ) -> PR08QueueRecoveryPipelineResult:
        audit_service.log_event(
            case_id=case_id,
            correlation_id=idemp_hash,
            stage_name="POISON_ISOLATION",
            actor_id="PEX_QUEUE_RECOVERY_ENGINE",
            actor_role="SYSTEM",
            action_name="POISON_MESSAGE_QUARANTINED",
            details=f"Poison message isolated to prevent retry loop: {rec_res.error_message}",
            amount=amount,
            currency=currency
        )
        return PR08QueueRecoveryPipelineResult(
            case_id=case_id,
            profile_id="PR-08",
            idempotency_hash=idemp_hash,
            message_id=msg_id,
            uetr=uetr,
            sufficiency_result=suff_res,
            recovery_result=rec_res,
            resolution_result=canon_res,
            final_lifecycle_stage="POISON_MESSAGE_QUARANTINED",
            is_stp_executed=False,
            is_hitl_routed=True,
            is_poison_isolated=True,
            recommended_routing="POISON_INVESTIGATION_DESK",
            error_summary=rec_res.error_message
        )

    def _build_duplicate_blocked_result(
        self,
        case_id: str,
        idemp_hash: str,
        msg_id: str,
        uetr: Optional[str],
        suff_res: Any,
        rec_res: Any,
        canon_res: Any,
        amount: float,
        currency: str
    ) -> PR08QueueRecoveryPipelineResult:
        audit_service.log_event(
            case_id=case_id,
            correlation_id=idemp_hash,
            stage_name="DUPLICATE_PROTECTION",
            actor_id="PEX_QUEUE_RECOVERY_ENGINE",
            actor_role="SYSTEM",
            action_name="DUPLICATE_RETRY_BLOCKED",
            details=f"Blocked duplicate re-enqueue due to prior execution or settlement: {rec_res.error_message}",
            amount=amount,
            currency=currency
        )
        return PR08QueueRecoveryPipelineResult(
            case_id=case_id,
            profile_id="PR-08",
            idempotency_hash=idemp_hash,
            message_id=msg_id,
            uetr=uetr,
            sufficiency_result=suff_res,
            recovery_result=rec_res,
            resolution_result=canon_res,
            final_lifecycle_stage="DUPLICATE_RETRY_BLOCKED",
            is_stp_executed=False,
            is_hitl_routed=True,
            recommended_routing="FINANCIAL_RECONCILIATION_DESK",
            error_summary=rec_res.error_message
        )

    def _build_unrecoverable_result(
        self,
        case_id: str,
        idemp_hash: str,
        msg_id: str,
        uetr: Optional[str],
        suff_res: Any,
        rec_res: Any,
        canon_res: Any,
        amount: float,
        currency: str
    ) -> PR08QueueRecoveryPipelineResult:
        return PR08QueueRecoveryPipelineResult(
            case_id=case_id,
            profile_id="PR-08",
            idempotency_hash=idemp_hash,
            message_id=msg_id,
            uetr=uetr,
            sufficiency_result=suff_res,
            recovery_result=rec_res,
            resolution_result=canon_res,
            final_lifecycle_stage="RECOVERY_FAILED",
            is_stp_executed=False,
            is_hitl_routed=True,
            recommended_routing="OPERATIONS_SUSPENSE_QUEUE",
            error_summary=rec_res.error_message
        )

    def _build_hitl_routed_result(
        self,
        case_id: str,
        idemp_hash: str,
        msg_id: str,
        uetr: Optional[str],
        suff_res: Any,
        rec_res: Any,
        canon_res: Any,
        auth_res: Any,
        stp_dec: Any,
        amount: float,
        currency: str,
        raw_payload: str
    ) -> PR08QueueRecoveryPipelineResult:
        self._case_store[case_id] = {
            "case_id": case_id,
            "message_id": msg_id,
            "uetr": uetr,
            "raw_payload": raw_payload,
            "canon_res": canon_res,
            "amount": amount,
            "currency": currency,
            "status": "PENDING_MAKER"
        }

        audit_service.log_event(
            case_id=case_id,
            correlation_id=idemp_hash,
            stage_name="HITL_ROUTING",
            actor_id="PEX_POLICY_ENGINE",
            actor_role="SYSTEM",
            action_name="ROUTED_TO_MAKER_CHECKER",
            details=f"Queue recovery exception routed to HITL (Amount ${amount} or Policy condition)",
            amount=amount,
            currency=currency
        )

        return PR08QueueRecoveryPipelineResult(
            case_id=case_id,
            profile_id="PR-08",
            idempotency_hash=idemp_hash,
            message_id=msg_id,
            uetr=uetr,
            sufficiency_result=suff_res,
            recovery_result=rec_res,
            resolution_result=canon_res,
            authority_result=auth_res,
            stp_decision=stp_dec,
            final_lifecycle_stage="HITL_MAKER_PENDING",
            is_stp_executed=False,
            is_hitl_routed=True,
            recommended_routing="MAKER_CHECKER_APPROVALS_DESK",
            error_summary="Monetary policy threshold exceeded or secondary policy gate requires operator review."
        )

    def approve_and_dispatch(
        self,
        case_id: str,
        maker_id: str,
        checker_id: str,
        rationale: str
    ) -> PR08QueueRecoveryPipelineResult:
        """Executes governed Maker-Checker dual authorization continuation flow."""
        if maker_id == checker_id:
            raise ValueError(f"Segregation of Duties Violation: Maker ({maker_id}) cannot be the Checker ({checker_id}).")

        case = self._case_store.get(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found in active HITL store.")

        canon_res: ResolutionResult = case["canon_res"]
        repaired_text = canon_res.primary_candidate.repaired_payload

        # Approved decision for handoff
        approved_dec = STPEligibilityDecision(
            case_id=case_id,
            profile_id="PR-08",
            stp_eligible=True,
            evidence_sufficient=True,
            resolution_determined=True,
            resolution_unique=True,
            deterministic_validation_passed=True,
            authority_validation_passed=True,
            bank_policy_allows=True,
            compliance_gate_passed=True,
            execution_preconditions_satisfied=True,
            recommended_routing="BANK_RETRY_QUEUE",
            audit_trail=[f"Maker {maker_id} submitted", f"Checker {checker_id} dual-approved: {rationale}"]
        )

        handoff_rcpt = self.output_adapter.emit_repaired_instruction(
            candidate=canon_res.primary_candidate,
            decision=approved_dec,
            filename_prefix=f"PEX_HITL_PR08_{case_id}",
            original_payment_info={"case_id": case_id, "amount": case.get("amount"), "currency": case.get("currency")}
        )
        outbound_env = self.output_adapter.get_outbound_envelope(handoff_rcpt.receipt_id)

        # Record Permanent Execution in Idempotency Manager
        msg_id = case.get("message_id", case_id)
        self.recovery_engine.lock_manager.record_execution(f"IDEMP-PR08-{msg_id}", hashlib.sha256(repaired_text.encode()).hexdigest())

        audit_service.log_event(
            case_id=case_id,
            correlation_id=case_id,
            stage_name="HITL_APPROVAL",
            actor_id=checker_id,
            actor_role="CHECKER",
            action_name="DUAL_AUTHORIZATION_APPROVED",
            details=f"Checker approved case {case_id}. Maker: {maker_id}. Rationale: {rationale}",
            amount=case["amount"],
            currency=case["currency"]
        )

        return PR08QueueRecoveryPipelineResult(
            case_id=case_id,
            profile_id="PR-08",
            idempotency_hash=hashlib.sha256(case_id.encode()).hexdigest(),
            message_id=msg_id,
            uetr=case.get("uetr"),
            resolution_result=canon_res,
            handoff_receipt=handoff_rcpt,
            outbound_envelope=outbound_env,
            final_lifecycle_stage="BANK_HANDOFF_READY",
            is_stp_executed=False,
            is_hitl_routed=True,
            is_hitl_approved=True,
            recommended_routing="BANK_RETRY_QUEUE"
        )


# Global singleton instance
pr08_queue_recovery_pipeline = PR08QueueRecoverySTPPipeline()
