"""End-to-End PR-03 (ISO20022_ERROR) Evidence-Driven STP Pipeline.

Orchestrates the complete 12-stage lifecycle for PR-03:
Input -> Parse -> Normalize -> Evidence Contract -> Evidence Sufficiency -> Resolution Determination
-> Authority Validation -> Bank Policy -> STP Eligibility -> Repair Output -> Bank Handoff -> Audit.
"""
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.schemas.evidence_contract import EvidenceDossier, EvidenceTrustTier
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


class PR03PipelineResult(BaseModel):
    """Complete forensic result of executing the PR-03 STP Pipeline."""
    case_id: str
    profile_id: str = "PR-03"
    idempotency_hash: str
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Intermediate Contract Results:
    sufficiency_result: EvidenceSufficiencyResult
    resolution_result: Optional[ResolutionResult] = None
    authority_result: Optional[AuthorityValidationResult] = None
    stp_decision: Optional[STPEligibilityDecision] = None
    handoff_receipt: Optional[BankHandoffReceipt] = None

    # Lifecycle State & Routing:
    final_lifecycle_stage: str
    is_stp_executed: bool
    recommended_routing: str
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)
    error_summary: Optional[str] = None


class PR03STPPipeline:
    """Master orchestrator for PR-03 (ISO20022_ERROR) Straight-Through Processing."""

    def __init__(
        self,
        input_adapter: Optional[FolderInputAdapter] = None,
        output_adapter: Optional[FolderOutputAdapter] = None,
        policy_config: Optional[STPPolicyConfig] = None
    ):
        self.input_adapter = input_adapter or FolderInputAdapter()
        self.output_adapter = output_adapter or FolderOutputAdapter()
        self.policy_config = policy_config or STPPolicyConfig()

    def process_package(
        self,
        package: InboundPackage,
        amount: float = 5000.0,
        currency: str = "USD",
        compliance_status: ComplianceGateStatus = ComplianceGateStatus.PASS,
        execution_preconditions: ExecutionPreconditionsStatus = ExecutionPreconditionsStatus.PASS,
        ai_confidence: Optional[float] = None
    ) -> PR03PipelineResult:
        """Executes the full 12-stage lifecycle for an inbound PR-03 exception package."""
        audit_records: List[Dict[str, Any]] = []

        # Stage 1 & 2: Inbound Ingestion & Evidence Dossier Extraction
        case_id, dossier, idemp_hash = self.input_adapter.ingest_payload(package, profile_id="PR-03")
        
        # Log Ingestion Event
        try:
            audit_service.log_event(
                case_id=case_id,
                correlation_id=idemp_hash,
                stage_name="INGESTION",
                actor_id="SYSTEM_INBOUND_WATCHER",
                actor_role="SYSTEM",
                action_name="EXCEPTION_INGESTED",
                details=f"Ingested PR-03 exception package {package.package_id} (Channel: {package.source_channel})"
            )
        except Exception:
            pass

        # Stage 3 & 4: Evidence Sufficiency Evaluation
        sufficiency_res = sufficiency_engine.evaluate_sufficiency(dossier)
        try:
            audit_service.log_event(
                case_id=case_id,
                correlation_id=idemp_hash,
                stage_name="EVIDENCE_SUFFICIENCY",
                actor_id="EVIDENCE_SUFFICIENCY_ENGINE",
                actor_role="SYSTEM",
                action_name="EVIDENCE_SUFFICIENCY_EVALUATED",
                details=f"Evidence sufficiency status: {sufficiency_res.status.value} (Sufficient: {sufficiency_res.is_sufficient})"
            )
        except Exception:
            pass

        if not sufficiency_res.is_sufficient:
            # Short-circuit to human operations without guessing
            decision = STPEligibilityDecision.evaluate(
                case_id=case_id,
                profile_id="PR-03",
                e_suff=False,
                r_det=False,
                r_uniq=False,
                v_det=False,
                v_auth=False,
                p_bank=True,
                c_comp=(compliance_status == ComplianceGateStatus.PASS),
                x_pre=(execution_preconditions == ExecutionPreconditionsStatus.PASS),
                policy_denial_reasons=[f"Evidence insufficient: {sufficiency_res.status.value}"]
            )
            return PR03PipelineResult(
                case_id=case_id,
                profile_id="PR-03",
                idempotency_hash=idemp_hash,
                sufficiency_result=sufficiency_res,
                stp_decision=decision,
                final_lifecycle_stage="SUSPENDED_INSUFFICIENT_EVIDENCE",
                is_stp_executed=False,
                recommended_routing="OPERATIONS_SUSPENSE",
                error_summary=f"Evidence Sufficiency Failed: {sufficiency_res.status.value}"
            )

        # Stage 5: Resolution Determination
        resolution_res = resolution_engine.derive_resolution(dossier)
        try:
            audit_service.log_event(
                case_id=case_id,
                correlation_id=idemp_hash,
                stage_name="RESOLUTION_DETERMINATION",
                actor_id="RESOLUTION_ENGINE",
                actor_role="SYSTEM",
                action_name="RESOLUTION_DERIVED",
                details=f"Resolution status: {resolution_res.status.value}, Uniqueness: {resolution_res.uniqueness.value}"
            )
        except Exception:
            pass

        if not resolution_res.is_deterministic_and_unique or not resolution_res.primary_candidate:
            decision = STPEligibilityDecision.evaluate(
                case_id=case_id,
                profile_id="PR-03",
                e_suff=True,
                r_det=(resolution_res.status == ResolutionStatus.RESOLUTION_DETERMINED),
                r_uniq=(resolution_res.uniqueness == ResolutionUniqueness.RESOLUTION_UNIQUE),
                v_det=False,
                v_auth=False,
                p_bank=True,
                c_comp=(compliance_status == ComplianceGateStatus.PASS),
                x_pre=(execution_preconditions == ExecutionPreconditionsStatus.PASS),
                policy_denial_reasons=[f"Resolution failed: {resolution_res.error_message}"]
            )
            return PR03PipelineResult(
                case_id=case_id,
                profile_id="PR-03",
                idempotency_hash=idemp_hash,
                sufficiency_result=sufficiency_res,
                resolution_result=resolution_res,
                stp_decision=decision,
                final_lifecycle_stage="SUSPENDED_RESOLUTION_FAILED",
                is_stp_executed=False,
                recommended_routing="DISAMBIGUATION_WORKLIST" if resolution_res.uniqueness == ResolutionUniqueness.RESOLUTION_AMBIGUOUS else "OPERATIONS_SUSPENSE",
                error_summary=resolution_res.error_message or "Deterministic resolution could not be derived."
            )

        candidate = resolution_res.primary_candidate

        # Stage 6: Authority Validation
        authority_res = authority_validation_engine.validate_candidate(candidate, profile_id="PR-03")
        try:
            audit_service.log_event(
                case_id=case_id,
                correlation_id=idemp_hash,
                stage_name="AUTHORITY_VALIDATION",
                actor_id="AUTHORITY_VALIDATION_ENGINE",
                actor_role="SYSTEM",
                action_name="AUTHORITY_VALIDATED",
                details=f"Authority validation status: {authority_res.status.value} (Source: {authority_res.authoritative_source})"
            )
        except Exception:
            pass

        # Stage 7 & 8: Bank Policy & STP Eligibility Gate
        stp_decision = evidence_stp_evaluator.evaluate(
            case_id=case_id,
            profile_id="PR-03",
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

        try:
            audit_service.log_event(
                case_id=case_id,
                correlation_id=idemp_hash,
                stage_name="STP_POLICY_EVALUATION",
                actor_id="STP_POLICY_ENGINE",
                actor_role="SYSTEM",
                action_name="STP_ELIGIBILITY_EVALUATED",
                details=f"STP eligibility decision: {stp_decision.stp_eligible} (Routing: {stp_decision.recommended_routing})"
            )
        except Exception:
            pass

        handoff_receipt = None
        final_stage = "PENDING_MAKER_CHECKER"

        # Stage 9 & 10: Output Serialization & Bank-Controlled Handoff
        if stp_decision.stp_eligible:
            handoff_receipt = self.output_adapter.emit_repaired_instruction(candidate, stp_decision)
            final_stage = "AUTO_STP_DISPATCHED_TO_BANK_HUB"
            try:
                audit_service.log_event(
                    case_id=case_id,
                    correlation_id=idemp_hash,
                    stage_name="EXECUTION_HANDOFF",
                    actor_id="SYSTEM_AUTO_STP",
                    actor_role="SYSTEM",
                    action_name="PAYMENT_DISPATCHED",
                    details=f"Repaired pacs.008 XML instruction handed off to Bank Payment Hub (Receipt: {handoff_receipt.receipt_id})"
                )
            except Exception:
                pass
        else:
            final_stage = "ROUTED_TO_MAKER_CHECKER" if ("Dual Authorization" in str(stp_decision.policy_denial_reasons) or amount >= self.policy_config.max_stp_amount) else "SUSPENDED_POLICY_REJECTED"

        return PR03PipelineResult(
            case_id=case_id,
            profile_id="PR-03",
            idempotency_hash=idemp_hash,
            sufficiency_result=sufficiency_res,
            resolution_result=resolution_res,
            authority_result=authority_res,
            stp_decision=stp_decision,
            handoff_receipt=handoff_receipt,
            final_lifecycle_stage=final_stage,
            is_stp_executed=stp_decision.stp_eligible,
            recommended_routing=stp_decision.recommended_routing
        )


# Global singleton pipeline
pr03_pipeline = PR03STPPipeline()
