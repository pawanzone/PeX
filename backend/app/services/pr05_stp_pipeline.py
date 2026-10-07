"""End-to-End PR-05 (CORRUPTED_MESSAGE_FORMAT) Evidence-Driven STP Pipeline.

Orchestrates the complete governed 12-stage lifecycle for PR-05:
Intake -> Canonicalization -> Evidence Acquisition -> Evidence Sufficiency -> Resolution Determination
-> Authority Validation -> Bank Policy -> STP Eligibility -> Output / Bank Handoff -> Audit.

Supports seamless HITL continuation through the identical bank handoff path upon human approval.
"""
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.schemas.evidence_contract import EvidenceDossier, EvidenceTrustTier
from app.schemas.canonical_envelopes import (
    CanonicalIntakeEnvelope,
    CanonicalOutboundEnvelope,
    HandoffLifecycleState,
)
from app.services.sufficiency_engine import (
    sufficiency_engine,
    EvidenceSufficiencyResult,
    EvidenceSufficiencyStatus,
)
from app.services.resolution_engine import (
    resolution_engine,
    ResolutionResult,
    ResolutionStatus,
    ResolutionUniqueness,
    ResolutionCandidate,
)
from app.services.authority_validation_engine import (
    authority_validation_engine,
    AuthorityValidationResult,
    AuthorityValidationStatus,
)
from app.services.evidence_stp_evaluator import (
    evidence_stp_evaluator,
    STPEligibilityDecision,
    STPPolicyConfig,
    ComplianceGateStatus,
    ExecutionPreconditionsStatus,
)
from app.adapters.input_adapter import InboundPackage, FolderInputAdapter
from app.adapters.output_adapter import FolderOutputAdapter, BankHandoffReceipt
from app.services.audit_service import audit_service


class PR05PipelineResult(BaseModel):
    """Complete forensic result of executing the PR-05 STP Pipeline."""
    case_id: str
    profile_id: str = "PR-05"
    idempotency_hash: str
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Intermediate Contract Results:
    sufficiency_result: EvidenceSufficiencyResult
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
    recommended_routing: str
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)
    error_summary: Optional[str] = None


class PR05STPPipeline:
    """Master orchestrator for PR-05 (CORRUPTED_MESSAGE_FORMAT) Straight-Through Processing."""

    def __init__(
        self,
        input_adapter: Optional[FolderInputAdapter] = None,
        output_adapter: Optional[FolderOutputAdapter] = None,
        policy_config: Optional[STPPolicyConfig] = None
    ):
        self.input_adapter = input_adapter or FolderInputAdapter()
        self.output_adapter = output_adapter or FolderOutputAdapter()
        self.policy_config = policy_config or STPPolicyConfig()
        self._case_store: Dict[str, Dict[str, Any]] = {}

    def process_package(
        self,
        package: InboundPackage,
        amount: float = 5000.0,
        currency: str = "USD",
        compliance_status: ComplianceGateStatus = ComplianceGateStatus.PASS,
        execution_preconditions: ExecutionPreconditionsStatus = ExecutionPreconditionsStatus.PASS,
        ai_confidence: Optional[float] = None
    ) -> PR05PipelineResult:
        """Executes the full 12-stage lifecycle for an inbound PR-05 exception package."""
        audit_records: List[Dict[str, Any]] = []

        # Stage 1 & 2: Inbound Ingestion & Evidence Dossier Extraction
        case_id, dossier, idemp_hash = self.input_adapter.ingest_payload(package, profile_id="PR-05")
        
        # Log Ingestion Event
        try:
            audit_service.log_event(
                case_id=case_id,
                correlation_id=idemp_hash,
                stage_name="INGESTION",
                actor_id="SYSTEM_INBOUND_WATCHER",
                actor_role="SYSTEM",
                action_name="EXCEPTION_INGESTED",
                status="SUCCESS",
                payload_snapshot={"package_id": package.package_id, "profile_id": "PR-05", "source_channel": package.source_channel}
            )
        except Exception:
            pass

        # Stage 3: Evaluate Evidence Sufficiency (E_suff)
        sufficiency_res = sufficiency_engine.evaluate_sufficiency(dossier)

        # Stage 4: Deterministic Resolution & Governed Character/Encoding Transformation (R_det, R_uniq, V_det)
        resolution_res: Optional[ResolutionResult] = None
        authority_res: Optional[AuthorityValidationResult] = None
        stp_decision: Optional[STPEligibilityDecision] = None
        handoff_rcpt: Optional[BankHandoffReceipt] = None
        outbound_env: Optional[CanonicalOutboundEnvelope] = None

        if sufficiency_res.is_sufficient:
            resolution_res = resolution_engine.derive_resolution(dossier)

            # Stage 5: Authority & Syntax Validation (V_det, V_auth)
            if resolution_res.primary_candidate is not None:
                authority_res = authority_validation_engine.validate_candidate(
                    candidate=resolution_res.primary_candidate,
                    profile_id="PR-05",
                    dossier=dossier
                )

        # Fallback dummy results if prerequisite failed
        if resolution_res is None:
            resolution_res = ResolutionResult(
                profile_id="PR-05",
                status=ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                is_lossless=False,
                error_message="Prerequisite evidence insufficient."
            )

        if authority_res is None:
            authority_res = AuthorityValidationResult(
                profile_id="PR-05",
                status=AuthorityValidationStatus.UNAVAILABLE,
                is_valid=False,
                authoritative_source="UNAVAILABLE",
                is_structural_syntax_valid=False,
                is_business_authority_confirmed=False,
                error_message="Authority validation could not be executed."
            )

        # Stage 6, 7 & 8: 8-Predicate STP Formula Evaluation (P_bank, C_comp, X_pre -> STP_ELIGIBLE)
        stp_decision = evidence_stp_evaluator.evaluate(
            case_id=case_id,
            profile_id="PR-05",
            amount=amount,
            currency=currency,
            sufficiency_result=sufficiency_res,
            resolution_result=resolution_res,
            authority_result=authority_res,
            policy_config=self.policy_config,
            compliance_status=compliance_status,
            execution_preconditions_status=execution_preconditions,
            ai_confidence_score=ai_confidence
        )

        # Stage 9: Routing & Bank Handoff Boundary
        final_stage = "SUSPENDED"
        is_stp_executed = False
        is_hitl_routed = False

        original_info = {
            "case_id": case_id,
            "package_id": package.package_id,
            "amount": amount,
            "currency": currency,
            "uetr": package.idempotency_key
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

        # Store case context for potential HITL continuation
        self._case_store[case_id] = {
            "case_id": case_id,
            "package": package,
            "dossier": dossier,
            "amount": amount,
            "currency": currency,
            "sufficiency_res": sufficiency_res,
            "resolution_res": resolution_res,
            "authority_res": authority_res,
            "stp_decision": stp_decision,
            "original_info": original_info,
            "evidence_refs": evidence_refs
        }

        if stp_decision.stp_eligible and resolution_res.primary_candidate is not None:
            # Autonomous STP -> Emit Bank Handoff
            handoff_rcpt = self.output_adapter.emit_repaired_instruction(
                candidate=resolution_res.primary_candidate,
                decision=stp_decision,
                original_payment_info=original_info,
                evidence_references=evidence_refs
            )
            outbound_env = self.output_adapter.get_outbound_envelope(handoff_rcpt.receipt_id)
            final_stage = "BANK_HANDOFF_READY"
            is_stp_executed = True

            try:
                audit_service.log_event(
                    case_id=case_id,
                    correlation_id=idemp_hash,
                    stage_name="BANK_HANDOFF",
                    actor_id="AUTONOMOUS_STP_ENGINE",
                    actor_role="SYSTEM",
                    action_name="BANK_HANDOFF_DISPATCHED",
                    status="SUCCESS",
                    payload_snapshot={
                        "receipt_id": handoff_rcpt.receipt_id,
                        "sha256_hash": handoff_rcpt.sha256_payload_hash,
                        "routing": stp_decision.recommended_routing,
                        "execution_owner": "BANK"
                    }
                )
            except Exception:
                pass
        else:
            # Route to HITL / Suspense
            is_hitl_routed = True
            final_stage = stp_decision.recommended_routing

            try:
                audit_service.log_event(
                    case_id=case_id,
                    correlation_id=idemp_hash,
                    stage_name="HITL_ROUTING",
                    actor_id="STP_POLICY_GATE",
                    actor_role="SYSTEM",
                    action_name="ROUTED_TO_HUMAN_WORKLIST",
                    status="SUSPENDED",
                    payload_snapshot={
                        "recommended_routing": stp_decision.recommended_routing,
                        "denial_reasons": stp_decision.policy_denial_reasons
                    }
                )
            except Exception:
                pass

        return PR05PipelineResult(
            case_id=case_id,
            profile_id="PR-05",
            idempotency_hash=idemp_hash,
            sufficiency_result=sufficiency_res,
            resolution_result=resolution_res,
            authority_result=authority_res,
            stp_decision=stp_decision,
            handoff_receipt=handoff_rcpt,
            outbound_envelope=outbound_env,
            final_lifecycle_stage=final_stage,
            is_stp_executed=is_stp_executed,
            is_hitl_routed=is_hitl_routed,
            recommended_routing=stp_decision.recommended_routing,
            error_summary="; ".join(stp_decision.policy_denial_reasons) if not stp_decision.stp_eligible else None
        )

    def process_canonical_envelope(
        self,
        envelope: CanonicalIntakeEnvelope,
        compliance_status: ComplianceGateStatus = ComplianceGateStatus.PASS,
        execution_preconditions: ExecutionPreconditionsStatus = ExecutionPreconditionsStatus.PASS,
        ai_confidence: Optional[float] = None
    ) -> PR05PipelineResult:
        """Processes a transport-neutral CanonicalIntakeEnvelope (pex.intake.v1)."""
        package = InboundPackage.from_canonical_envelope(envelope)
        return self.process_package(
            package=package,
            amount=envelope.amount,
            currency=envelope.currency,
            compliance_status=compliance_status,
            execution_preconditions=execution_preconditions,
            ai_confidence=ai_confidence
        )

    def approve_and_dispatch_hitl(
        self,
        case_id: str,
        maker_user_id: str,
        checker_user_id: str,
        override_notes: str = "Approved by Operations Maker-Checker"
    ) -> Tuple[bool, Optional[BankHandoffReceipt], Optional[str]]:
        """Executes the HITL continuation path upon Maker-Checker approval.
        
        CRITICAL ARCHITECTURAL INVARIANT:
        Maker and Checker MUST be distinct individuals (Segregation of Duties).
        Human approval follows the SAME bank handoff path without separate execution logic.
        """
        if case_id not in self._case_store:
            return False, None, f"Case {case_id} not found in active pipeline store."

        # Maker-Checker Self-Approval Block (Segregation of Duties)
        if maker_user_id == checker_user_id:
            try:
                audit_service.log_event(
                    case_id=case_id,
                    correlation_id=case_id,
                    stage_name="HITL_APPROVAL",
                    actor_id=maker_user_id,
                    actor_role="OPERATOR",
                    action_name="DUAL_AUTH_VIOLATION",
                    status="FAILED",
                    payload_snapshot={"error": "Maker cannot approve own submission (Self-approval rejected)."}
                )
            except Exception:
                pass
            return False, None, "Maker-Checker violation: Maker and Checker cannot be the same user."

        case_ctx = self._case_store[case_id]
        resolution_res: Optional[ResolutionResult] = case_ctx.get("resolution_res")

        if not resolution_res or not resolution_res.primary_candidate:
            return False, None, "No valid candidate repair available to dispatch."

        candidate = resolution_res.primary_candidate
        stp_decision: STPEligibilityDecision = case_ctx["stp_decision"]

        # Emit Bank Handoff through standard output adapter
        receipt = self.output_adapter.emit_repaired_instruction(
            candidate=candidate,
            decision=stp_decision,
            filename_prefix=f"PEX_HITL_APPROVED_{case_id}",
            original_payment_info=case_ctx.get("original_info"),
            evidence_references=case_ctx.get("evidence_refs")
        )

        outbound_env = self.output_adapter.get_outbound_envelope(receipt.receipt_id)
        if outbound_env:
            outbound_env.governance_decision = "HITL_APPROVED_HANDOFF"
            outbound_env.lifecycle_state = HandoffLifecycleState.BANK_HANDOFF_READY

        # Log Dual-Authorization in Cryptographic Provenance Ledger
        try:
            audit_service.log_event(
                case_id=case_id,
                correlation_id=case_id,
                stage_name="HITL_APPROVAL",
                actor_id=f"MAKER:{maker_user_id}|CHECKER:{checker_user_id}",
                actor_role="DUAL_OPERATOR",
                action_name="MAKER_CHECKER_APPROVAL_DISPATCHED",
                status="SUCCESS",
                payload_snapshot={
                    "receipt_id": receipt.receipt_id,
                    "maker": maker_user_id,
                    "checker": checker_user_id,
                    "notes": override_notes,
                    "execution_owner": "BANK"
                }
            )
        except Exception:
            pass

        return True, receipt, None


# Global singleton PR-05 pipeline instance
pr05_pipeline = PR05STPPipeline()
