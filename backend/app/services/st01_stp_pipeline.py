"""End-to-End ST-01 (RETURNED_PAYMENT) Evidence-Driven STP Pipeline.

ST-01: RETURNED PAYMENT / RETURN_RECALL_UNMATCHED
Phase: Phase 2D (Slice 7)
Domain: Domain 5 (Settlement & Returns)

Orchestrates the complete governed 12-stage lifecycle for ST-01:
Intake -> Canonicalization -> Evidence Acquisition -> Evidence Sufficiency (E_suff)
-> Deterministic Multi-Way Reconciliation & Bank Instruction Derivation (R_det, R_uniq)
-> ISO 20022 Return Code-Set (V_det) & Bank SoR / Settlement / DDA Authority (V_auth)
-> STP Eligibility (8 Predicates) -> Bank Handoff Ready / HITL Routing -> Cryptographic Audit.

Enforces:
- Separation of Concerns:
  RETURN RECOGNITION != ACCOUNTING RELEASE != RECONCILIATION MATCH != DDA RE-CREDIT != FUNDS MOVEMENT.
- PeX RECONCILES + VALIDATES + PREPARES INSTRUCTION; BANK EXECUTES ACCOUNTING / RE-CREDIT.
- Execution boundary: PeX never credits customer accounts directly; outputs BANK_RE_CREDIT_INSTRUCTION with execution_owner = "BANK".
- Exact multi-way reconciliation: Inbound pacs.004 <-> Original pacs.008 (UETR & EndToEndId).
- Amount equation: Returned Amount + Authorized Deducted Charges == Original Settlement Amount.
- Currency strict equality (e.g. EUR == EUR).
- SoR validations: Original payment must be SETTLED; DDA must be OPEN/ACTIVE; no ALREADY_RECREDITED.
- Prompt injection defense: Untrusted narrative in return (<AddtlInf>) is sanitized.
- Segregation of Duties (SoD): For HITL continuation, maker_id != checker_id.
- Lossless financial semantic invariance across all payment fields.
"""
import re
import uuid
import hashlib
import xml.etree.ElementTree as ET
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
from app.services.st01_return_reconciler import (
    st01_reconciler,
    BankReCreditInstruction,
    OriginalPaymentRecord,
    SettlementLedgerRecord,
    CoreDDAAccountRecord,
    BankReturnDispositionPolicy,
    FeeScheduleRecord,
    CorridorReturnPolicy,
    ISO_20022_EXTERNAL_RETURN_CODES,
    SettlementLedgerState,
    CoreDDAStatus,
)
from app.adapters.input_adapter import InboundPackage, FolderInputAdapter
from app.adapters.output_adapter import FolderOutputAdapter, BankHandoffReceipt
from app.services.audit_service import audit_service


class ST01PipelineResult(BaseModel):
    """Complete forensic result of executing the ST-01 STP Pipeline."""
    case_id: str
    profile_id: str = "ST-01"
    idempotency_hash: str
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Intermediate Contract Results:
    sufficiency_result: EvidenceSufficiencyResult
    resolution_result: Optional[ResolutionResult] = None
    authority_result: Optional[AuthorityValidationResult] = None
    stp_decision: Optional[STPEligibilityDecision] = None
    handoff_receipt: Optional[BankHandoffReceipt] = None
    outbound_envelope: Optional[CanonicalOutboundEnvelope] = None
    re_credit_instruction: Optional[Dict[str, Any]] = None

    # Lifecycle State & Governance:
    uetr: Optional[str] = None
    end_to_end_id: Optional[str] = None
    return_reason_code: Optional[str] = None
    recredit_amount: Optional[float] = None
    recredit_currency: Optional[str] = None
    target_dda_account: Optional[str] = None
    final_lifecycle_stage: str
    is_stp_executed: bool
    is_hitl_routed: bool = False
    is_hitl_approved: bool = False
    recommended_routing: str
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)
    error_summary: Optional[str] = None


class ST01STPPipeline:
    """Master orchestrator for ST-01 (RETURNED_PAYMENT) Straight-Through Processing."""

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
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        compliance_status: ComplianceGateStatus = ComplianceGateStatus.PASS,
        execution_preconditions: ExecutionPreconditionsStatus = ExecutionPreconditionsStatus.PASS,
        bank_policy_authorized: Optional[bool] = None,
        allow_stale_evidence: bool = False,
        ai_confidence: Optional[float] = None
    ) -> ST01PipelineResult:
        """Executes the full 12-stage lifecycle for an inbound ST-01 Return package."""
        # Stage 1 & 2: Inbound Ingestion & Evidence Dossier Extraction
        case_id, dossier, idemp_hash = self.input_adapter.ingest_payload(package, profile_id="ST-01")
        if allow_stale_evidence:
            dossier.metadata["allow_stale_evidence"] = True

        # Log Ingestion Event
        try:
            audit_service.log_event(
                case_id=case_id,
                event_type="PACKAGE_INGESTED",
                actor="PEX_SYSTEM",
                details={"profile_id": "ST-01", "source": package.source_channel, "idempotency_hash": idemp_hash}
            )
        except Exception:
            pass

        uetr = dossier.metadata.get("uetr", "")
        end_to_end_id = dossier.metadata.get("end_to_end_id", "")
        return_amount = float(dossier.metadata.get("return_amount") or amount or 0.0)
        return_currency = str(dossier.metadata.get("currency") or currency or "EUR")
        return_reason = str(dossier.metadata.get("return_reason_code", ""))
        narrative = dossier.metadata.get("return_narrative", "")

        # Check prompt injection
        _, is_adversarial = st01_reconciler.sanitize_narrative(narrative)
        if is_adversarial:
            try:
                audit_service.log_event(
                    case_id=case_id,
                    event_type="SECURITY_ALERT_PROMPT_INJECTION",
                    actor="PEX_SYSTEM",
                    details={"narrative": narrative}
                )
            except Exception:
                pass

        # Stage 3: Evidence Sufficiency Evaluation (E_suff)
        sufficiency_res = sufficiency_engine.evaluate_sufficiency(dossier)

        if not sufficiency_res.is_sufficient:
            # Fallback based on failure reason
            routing = "COMPLIANCE_SUSPENSE" if any("SANCTIONS" in item for item in sufficiency_res.missing_mandatory_items) else "OPERATIONS_SUSPENSE"
            if sufficiency_res.contradictory_items:
                routing = "INVESTIGATION_COCKPIT"

            suff_errors = []
            if sufficiency_res.missing_mandatory_items:
                suff_errors.append(f"Missing mandatory items: {sufficiency_res.missing_mandatory_items}")
            if sufficiency_res.stale_items:
                suff_errors.append(f"Stale items: {sufficiency_res.stale_items}")
            if sufficiency_res.contradictory_items:
                suff_errors.append(f"Contradictory items: {sufficiency_res.contradictory_items}")
            if sufficiency_res.trust_tier_violations:
                suff_errors.append(f"Trust tier violations: {sufficiency_res.trust_tier_violations}")
            err_msg = "; ".join(suff_errors) or "Insufficient evidence for STP."

            res_obj = ST01PipelineResult(
                case_id=case_id,
                profile_id="ST-01",
                idempotency_hash=idemp_hash,
                sufficiency_result=sufficiency_res,
                uetr=uetr,
                end_to_end_id=end_to_end_id,
                return_reason_code=return_reason,
                recredit_amount=return_amount,
                recredit_currency=return_currency,
                final_lifecycle_stage=routing,
                is_stp_executed=False,
                is_hitl_routed=True,
                recommended_routing=routing,
                error_summary=err_msg
            )
            self._case_store[case_id] = {"result": res_obj, "dossier": dossier, "package": package}
            return res_obj

        # Stage 4 & 5: Deterministic Multi-Way Return Reconciliation (R_det, R_uniq)
        resolution_res = resolution_engine.derive_resolution(dossier)

        if resolution_res.status != ResolutionStatus.RESOLUTION_DETERMINED or not resolution_res.primary_candidate:
            routing = "DISAMBIGUATION_DESK" if resolution_res.uniqueness == ResolutionUniqueness.RESOLUTION_AMBIGUOUS else "MANUAL_REPAIR"
            res_obj = ST01PipelineResult(
                case_id=case_id,
                profile_id="ST-01",
                idempotency_hash=idemp_hash,
                sufficiency_result=sufficiency_res,
                resolution_result=resolution_res,
                uetr=uetr,
                end_to_end_id=end_to_end_id,
                return_reason_code=return_reason,
                recredit_amount=return_amount,
                recredit_currency=return_currency,
                final_lifecycle_stage=routing,
                is_stp_executed=False,
                is_hitl_routed=True,
                recommended_routing=routing,
                error_summary=resolution_res.error_message or "Reconciliation could not be deterministically determined."
            )
            self._case_store[case_id] = {"result": res_obj, "dossier": dossier, "package": package}
            return res_obj

        primary_cand = resolution_res.primary_candidate
        instruction_payload = primary_cand.repaired_structured or {}
        target_account = instruction_payload.get("target_dda_account")

        # Stage 6 & 7: ISO Return Code & Systems of Record Authority Validation (V_det, V_auth)
        authority_res = authority_validation_engine.validate_candidate(
            primary_cand,
            profile_id="ST-01",
            dossier=dossier,
            bank_policy_authorized=bank_policy_authorized
        )

        # Stage 8 & 9: 8-Predicate STP Eligibility Evaluation
        effective_amount = return_amount if return_amount > 0 else (instruction_payload.get("recredit_amount") or 1000.0)
        stp_decision = evidence_stp_evaluator.evaluate(
            case_id=case_id,
            profile_id="ST-01",
            amount=effective_amount,
            currency=return_currency,
            sufficiency_result=sufficiency_res,
            resolution_result=resolution_res,
            authority_result=authority_res,
            policy_config=self.policy_config,
            compliance_status=compliance_status,
            execution_preconditions_status=execution_preconditions,
            ai_confidence_score=ai_confidence
        )

        # Stage 10: Routing Decision & Bank Handoff / HITL Suspense
        if stp_decision.stp_eligible and authority_res.is_valid:
            # Prepare Bank Outbound Handoff Envelope & Receipt via Output Adapter
            original_info = {
                "case_id": case_id,
                "package_id": package.package_id,
                "amount": effective_amount,
                "currency": return_currency,
                "uetr": uetr
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

            handoff_receipt = self.output_adapter.emit_repaired_instruction(
                candidate=primary_cand,
                decision=stp_decision,
                filename_prefix=f"PEX_STP_ST01_{case_id}",
                original_payment_info=original_info,
                evidence_references=evidence_refs
            )
            outbound_env = self.output_adapter.get_outbound_envelope(handoff_receipt.receipt_id)

            try:
                audit_service.log_event(
                    case_id=case_id,
                    event_type="BANK_HANDOFF_PREPARED",
                    actor="PEX_SYSTEM",
                    details={
                        "instruction_id": instruction_payload.get("instruction_id"),
                        "uetr": uetr,
                        "recredit_amount": effective_amount,
                        "currency": return_currency,
                        "target_dda_account": target_account,
                        "execution_owner": "BANK",
                        "final_state": "BANK_HANDOFF_READY"
                    }
                )
            except Exception:
                pass

            res_obj = ST01PipelineResult(
                case_id=case_id,
                profile_id="ST-01",
                idempotency_hash=idemp_hash,
                sufficiency_result=sufficiency_res,
                resolution_result=resolution_res,
                authority_result=authority_res,
                stp_decision=stp_decision,
                handoff_receipt=handoff_receipt,
                outbound_envelope=outbound_env,
                re_credit_instruction=instruction_payload,
                uetr=uetr,
                end_to_end_id=end_to_end_id,
                return_reason_code=return_reason,
                recredit_amount=effective_amount,
                recredit_currency=return_currency,
                target_dda_account=target_account,
                final_lifecycle_stage="BANK_HANDOFF_READY",
                is_stp_executed=True,
                is_hitl_routed=False,
                recommended_routing="BANK_SETTLEMENT_CORE_DDA"
            )
            self._case_store[case_id] = {"result": res_obj, "dossier": dossier, "package": package}
            return res_obj
        else:
            # Route to appropriate HITL desk
            routing = stp_decision.recommended_routing
            if compliance_status != ComplianceGateStatus.PASS:
                routing = "COMPLIANCE_SUSPENSE"
            elif not authority_res.is_valid:
                routing = "OPERATIONS_SUSPENSE" if "SETTLEMENT" in (authority_res.error_message or "") or "DDA" in (authority_res.error_message or "") else "MANUAL_REPAIR"

            err_summary = (
                (stp_decision.policy_denial_reasons[0] if stp_decision.policy_denial_reasons else None) or
                authority_res.error_message or
                (resolution_res.error_message if resolution_res else None) or
                "STP criteria not met."
            )

            res_obj = ST01PipelineResult(
                case_id=case_id,
                profile_id="ST-01",
                idempotency_hash=idemp_hash,
                sufficiency_result=sufficiency_res,
                resolution_result=resolution_res,
                authority_result=authority_res,
                stp_decision=stp_decision,
                re_credit_instruction=instruction_payload,
                uetr=uetr,
                end_to_end_id=end_to_end_id,
                return_reason_code=return_reason,
                recredit_amount=effective_amount,
                recredit_currency=return_currency,
                target_dda_account=target_account,
                final_lifecycle_stage=routing,
                is_stp_executed=False,
                is_hitl_routed=True,
                recommended_routing=routing,
                error_summary=err_summary
            )
            self._case_store[case_id] = {"result": res_obj, "dossier": dossier, "package": package}
            return res_obj

    def submit_hitl_approval(
        self,
        case_id: str,
        maker_id: str,
        checker_id: str,
        decision: str = "APPROVED",
        override_reason: Optional[str] = None
    ) -> ST01PipelineResult:
        """Executes Segregation of Duties (SoD) validated Human-In-The-Loop approval for ST-01."""
        if case_id not in self._case_store:
            raise KeyError(f"Case {case_id} not found in pipeline store.")

        # Invariant: Segregation of Duties (maker_id != checker_id)
        if maker_id == checker_id:
            raise ValueError(f"Segregation of Duties Violation: Maker ({maker_id}) and Checker ({checker_id}) cannot be the same operator.")

        stored = self._case_store[case_id]
        prior_res: ST01PipelineResult = stored["result"]
        dossier: EvidenceDossier = stored["dossier"]
        package: InboundPackage = stored["package"]

        instruction_payload = prior_res.re_credit_instruction or {}

        if decision == "APPROVED":
            original_info = {
                "case_id": case_id,
                "package_id": package.package_id,
                "amount": prior_res.recredit_amount,
                "currency": prior_res.recredit_currency,
                "uetr": prior_res.uetr
            }
            approved_decision = STPEligibilityDecision.evaluate(
                case_id=case_id,
                profile_id="ST-01",
                e_suff=True,
                r_det=True,
                r_uniq=True,
                v_det=True,
                v_auth=True,
                p_bank=True,
                c_comp=True,
                x_pre=True,
                policy_denial_reasons=[],
                audit_trail=[f"Approved via Dual Authorization by {checker_id}"]
            )
            candidate_to_emit = prior_res.resolution_result.primary_candidate if (prior_res.resolution_result and prior_res.resolution_result.primary_candidate) else ResolutionCandidate(
                candidate_id=f"CAND-ST01-HITL-{case_id[:8]}",
                repaired_payload=package.raw_payload_str,
                diff_summary=f"HITL approved re-credit instruction for {prior_res.recredit_amount} {prior_res.recredit_currency}",
                derivation_method="HITL_MAKER_CHECKER_APPROVAL",
                is_lossless=True,
                repaired_structured=instruction_payload
            )
            handoff_receipt = self.output_adapter.emit_repaired_instruction(
                candidate=candidate_to_emit,
                decision=approved_decision,
                filename_prefix=f"PEX_HITL_ST01_{case_id}",
                original_payment_info=original_info
            )
            outbound_env = self.output_adapter.get_outbound_envelope(handoff_receipt.receipt_id)

            try:
                audit_service.log_event(
                    case_id=case_id,
                    event_type="HITL_DUAL_AUTHORIZATION_APPROVED",
                    actor=checker_id,
                    details={
                        "maker_id": maker_id,
                        "checker_id": checker_id,
                        "decision": decision,
                        "override_reason": override_reason,
                        "execution_owner": "BANK"
                    }
                )
            except Exception:
                pass

            updated_res = prior_res.model_copy(update={
                "final_lifecycle_stage": "BANK_HANDOFF_READY",
                "is_stp_executed": False,
                "is_hitl_routed": True,
                "is_hitl_approved": True,
                "recommended_routing": "BANK_SETTLEMENT_CORE_DDA",
                "handoff_receipt": handoff_receipt,
                "outbound_envelope": outbound_env
            })
            stored["result"] = updated_res
            return updated_res
        else:
            updated_res = prior_res.model_copy(update={
                "final_lifecycle_stage": "REJECTED_BY_CHECKER",
                "is_hitl_approved": False,
                "recommended_routing": "OPERATIONS_SUSPENSE"
            })
            stored["result"] = updated_res
            return updated_res


# Global singleton ST-01 pipeline
st01_pipeline = ST01STPPipeline()
