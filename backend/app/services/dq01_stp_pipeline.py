"""End-to-End DQ-01 (INVALID_IBAN) Evidence-Driven STP Pipeline.

DQ-01: INVALID_IBAN
Phase: Phase 2C (Slice 5)

Orchestrates the complete governed 12-stage lifecycle for DQ-01:
Intake -> Canonicalization -> Evidence Acquisition -> Evidence Sufficiency (E_suff)
-> IBAN Structure (ISO 13616) & MOD-97-10 (ISO 7064) Resolution (R_det, R_uniq)
-> Bank System-of-Record (SSI Master / Core DDA Ledger / CoP) Authority (V_det, V_auth)
-> STP Eligibility (8 Predicates) -> Bank Handoff Ready / HITL Routing -> Audit Provenance.

Enforces:
- Structural validation (ISO 13616 country formats & BBAN regex)
- Mathematical check digit verification (ISO 7064 MOD-97-10, remainder == 1)
- Bounded candidate permutation solving (check-digit mistype, single transposition, single substitution)
- Bank SSI Master Record corroboration ($V_{auth}$)
- Bank Core DDA Ledger account status (OPEN required; CLOSED / FROZEN / RESTRICTED fail closed)
- Ambiguity detection (Multiple candidates without authoritative disambiguation force R_uniq=False -> DISAMBIGUATION_DESK)
- Contradictory authority fail-closed behavior
- Maker-Checker Segregation of Duties (SoD) for HITL continuation
- Bank handoff boundary (execution_owner = "BANK", BANK_HANDOFF_READY)
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
from app.services.dq01_iban_resolver import (
    dq01_resolver,
    IBANResolutionOutcome,
    AccountLedgerStatus,
    CoPMatchResult,
    BankSSIMasterEntry,
    CoreDDAAccountRecord,
    CoPResponse,
)
from app.adapters.input_adapter import InboundPackage, FolderInputAdapter
from app.adapters.output_adapter import FolderOutputAdapter, BankHandoffReceipt
from app.services.audit_service import audit_service


class DQ01PipelineResult(BaseModel):
    """Complete forensic result of executing the DQ-01 STP Pipeline."""
    case_id: str
    profile_id: str = "DQ-01"
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
    original_iban: Optional[str] = None
    repaired_iban: Optional[str] = None
    beneficiary_name: Optional[str] = None
    iban_outcome: Optional[str] = None
    final_lifecycle_stage: str
    is_stp_executed: bool
    is_hitl_routed: bool = False
    is_hitl_approved: bool = False
    recommended_routing: str
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)
    error_summary: Optional[str] = None


class DQ01STPPipeline:
    """Master orchestrator for DQ-01 (INVALID_IBAN) Straight-Through Processing."""

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
        currency: str = "EUR",
        compliance_status: ComplianceGateStatus = ComplianceGateStatus.PASS,
        execution_preconditions: ExecutionPreconditionsStatus = ExecutionPreconditionsStatus.PASS,
        ai_confidence: Optional[float] = None
    ) -> DQ01PipelineResult:
        """Executes the full 12-stage lifecycle for an inbound DQ-01 IBAN exception package."""
        # Stage 1 & 2: Inbound Ingestion & Evidence Dossier Extraction
        case_id, dossier, idemp_hash = self.input_adapter.ingest_payload(package, profile_id="DQ-01")

        # Log Ingestion Event
        try:
            audit_service.log_event(
                case_id=case_id,
                correlation_id=idemp_hash,
                stage_name="INGESTION",
                actor_id="SYSTEM_INBOUND_WATCHER",
                actor_role="SYSTEM",
                action_name="EXCEPTION_INGESTED",
                details=f"Ingested DQ-01 package {package.package_id}",
                amount=amount,
                currency=currency
            )
        except Exception:
            pass

        # Stage 3: Evaluate Evidence Sufficiency (E_suff)
        sufficiency_res = sufficiency_engine.evaluate_sufficiency(dossier)

        # Stage 4: Deterministic Resolution & MOD-97 Candidate Solving (R_det, R_uniq)
        resolution_res: Optional[ResolutionResult] = None
        authority_res: Optional[AuthorityValidationResult] = None
        stp_decision: Optional[STPEligibilityDecision] = None
        handoff_rcpt: Optional[BankHandoffReceipt] = None
        outbound_env: Optional[CanonicalOutboundEnvelope] = None

        if sufficiency_res.is_sufficient:
            resolution_res = resolution_engine.derive_resolution(dossier)

            # Stage 5: Authority & Bank SoR Corroboration Validation (V_det, V_auth)
            if resolution_res.primary_candidate is not None:
                authority_res = authority_validation_engine.validate_candidate(
                    candidate=resolution_res.primary_candidate,
                    profile_id="DQ-01",
                    dossier=dossier
                )

        if resolution_res is None:
            resolution_res = ResolutionResult(
                profile_id="DQ-01",
                status=ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                is_lossless=False,
                error_message="Prerequisite evidence insufficient."
            )

        if authority_res is None:
            authority_res = AuthorityValidationResult(
                profile_id="DQ-01",
                status=AuthorityValidationStatus.UNAVAILABLE,
                is_valid=False,
                authoritative_source="UNAVAILABLE",
                is_structural_syntax_valid=False,
                is_business_authority_confirmed=False,
                error_message="Authority validation could not be executed."
            )

        # Stage 6: Evaluate 8-Predicate STP Policy Decision
        stp_decision = evidence_stp_evaluator.evaluate(
            case_id=case_id,
            profile_id="DQ-01",
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

        # Stage 7: Routing & Execution Decision
        final_stage = "OPERATIONS_SUSPENSE"
        is_stp_executed = False
        is_hitl_routed = False

        orig_iban_val = dossier.metadata.get("original_iban")
        repaired_iban_val = None
        bene_name_val = dossier.metadata.get("beneficiary_name")
        outcome_val = None

        if resolution_res and resolution_res.primary_candidate:
            diff_text = resolution_res.primary_candidate.diff_summary
            if "Repaired IBAN" in diff_text:
                outcome_val = "SINGLE_CANDIDATE_REPAIRED"
                # Extract repaired IBAN
                import re
                ib_m = re.search(r'<IBAN>([A-Z0-9]+)</IBAN>', resolution_res.primary_candidate.repaired_payload)
                if ib_m:
                    repaired_iban_val = ib_m.group(1)
            elif "mathematically valid" in diff_text:
                outcome_val = "VALID_NO_REPAIR"
                repaired_iban_val = orig_iban_val

        if stp_decision.stp_eligible and resolution_res.primary_candidate is not None:
            final_stage = "BANK_HANDOFF_READY"
            is_stp_executed = True

            # Stage 8: Generate Outbound Canonical Envelope & Bank Handoff
            original_info = {
                "case_id": case_id,
                "package_id": package.package_id,
                "amount": amount,
                "currency": currency,
                "uetr": dossier.metadata.get("uetr", "55a8e123-44bb-4e2b-8a55-112233445566")
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
                candidate=resolution_res.primary_candidate,
                decision=stp_decision,
                filename_prefix=f"PEX_STP_DQ01_{case_id}",
                original_payment_info=original_info,
                evidence_references=evidence_refs
            )
            outbound_env = self.output_adapter.get_outbound_envelope(handoff_rcpt.receipt_id)

            # Log STP Execution Event
            try:
                audit_service.log_event(
                    case_id=case_id,
                    correlation_id=idemp_hash,
                    stage_name="BANK_HANDOFF",
                    actor_id="SYSTEM_PEX_AUTONOMOUS_STP",
                    actor_role="SYSTEM",
                    action_name="AUTONOMOUS_STP_DISPATCH",
                    details=f"Autonomous STP bank handoff generated for DQ-01 case {case_id}",
                    amount=amount,
                    currency=currency
                )
            except Exception:
                pass

        else:
            is_hitl_routed = True
            if compliance_status != ComplianceGateStatus.PASS or not stp_decision.compliance_gate_passed:
                final_stage = "COMPLIANCE_SUSPENSE"
            elif resolution_res and resolution_res.uniqueness == ResolutionUniqueness.RESOLUTION_AMBIGUOUS:
                final_stage = "DISAMBIGUATION_DESK"
            elif (authority_res and authority_res.status == AuthorityValidationStatus.FAILED) or \
                 (resolution_res and resolution_res.error_message and any(k in resolution_res.error_message for k in ("CLOSED", "FROZEN", "RESTRICTED", "CoP", "Confirmation of Payee"))):
                final_stage = "INVESTIGATION_COCKPIT"
            elif not sufficiency_res.is_sufficient:
                final_stage = "OPERATIONS_SUSPENSE"
            else:
                final_stage = stp_decision.recommended_routing or "OPERATIONS_SUSPENSE"



            # Save case state for potential HITL continuation
            self._case_store[case_id] = {
                "case_id": case_id,
                "package": package,
                "dossier": dossier,
                "idemp_hash": idemp_hash,
                "amount": amount,
                "currency": currency,
                "sufficiency_res": sufficiency_res,
                "resolution_res": resolution_res,
                "authority_res": authority_res,
                "stp_decision": stp_decision,
                "final_stage": final_stage,
                "maker_submission": None,
                "checker_approval": None
            }

            try:
                denial_summary = "; ".join(stp_decision.policy_denial_reasons) if stp_decision.policy_denial_reasons else "Policy / Predicate failure"
                audit_service.log_event(
                    case_id=case_id,
                    correlation_id=idemp_hash,
                    stage_name="HITL_ROUTING",
                    actor_id="SYSTEM_EVIDENCE_EVALUATOR",
                    actor_role="SYSTEM",
                    action_name="SUSPENDED_FOR_HUMAN_REVIEW",
                    details=f"DQ-01 routed to {final_stage}: {denial_summary}",
                    amount=amount,
                    currency=currency
                )
            except Exception:
                pass

        denial_reasons = list(stp_decision.policy_denial_reasons) if stp_decision.policy_denial_reasons else []
        if authority_res and not authority_res.is_valid and authority_res.error_message and authority_res.error_message not in denial_reasons:
            denial_reasons.append(authority_res.error_message)

        return DQ01PipelineResult(
            case_id=case_id,
            profile_id="DQ-01",
            idempotency_hash=idemp_hash,
            sufficiency_result=sufficiency_res,
            resolution_result=resolution_res,
            authority_result=authority_res,
            stp_decision=stp_decision,
            handoff_receipt=handoff_rcpt,
            outbound_envelope=outbound_env,
            original_iban=orig_iban_val,
            repaired_iban=repaired_iban_val,
            beneficiary_name=bene_name_val,
            iban_outcome=outcome_val,
            final_lifecycle_stage=final_stage,
            is_stp_executed=is_stp_executed,
            is_hitl_routed=is_hitl_routed,
            recommended_routing=final_stage,
            error_summary="; ".join(denial_reasons) if denial_reasons else None
        )

    def process_canonical_envelope(
        self,
        envelope: CanonicalIntakeEnvelope,
        compliance_status: ComplianceGateStatus = ComplianceGateStatus.PASS,
        execution_preconditions: ExecutionPreconditionsStatus = ExecutionPreconditionsStatus.PASS,
        ai_confidence: Optional[float] = None
    ) -> DQ01PipelineResult:
        """Processes a transport-neutral CanonicalIntakeEnvelope through DQ-01 STP pipeline."""
        package = InboundPackage(
            package_id=envelope.message_id,
            source_channel=envelope.channel or "REST_API",
            raw_payload_str=envelope.raw_payload,
            evidence_fields=envelope.evidence_items,
            metadata={"uetr": envelope.uetr, "amount": envelope.amount, "currency": envelope.currency}
        )
        return self.process_package(
            package=package,
            amount=envelope.amount,
            currency=envelope.currency,
            compliance_status=compliance_status,
            execution_preconditions=execution_preconditions,
            ai_confidence=ai_confidence
        )

    def submit_maker(
        self,
        case_id: str,
        maker_id: str,
        selected_candidate_id: str,
        rationale: str
    ) -> Dict[str, Any]:
        """Maker submits human investigation and IBAN repair recommendation."""
        case_data = self._case_store.get(case_id)
        if not case_data:
            raise ValueError(f"Case {case_id} not found.")

        case_data["maker_submission"] = {
            "maker_id": maker_id,
            "selected_candidate_id": selected_candidate_id,
            "rationale": rationale,
            "submitted_at": datetime.now(timezone.utc).isoformat()
        }
        case_data["final_stage"] = "PENDING_CHECKER_APPROVAL"

        try:
            audit_service.log_event(
                case_id=case_id,
                correlation_id=case_data["idemp_hash"],
                stage_name="HITL_MAKER",
                actor_id=maker_id,
                actor_role="OPERATIONS_MAKER",
                action_name="MAKER_SUBMITTED",
                details=f"Maker submitted IBAN repair '{selected_candidate_id}': {rationale}",
                amount=case_data["amount"],
                currency=case_data["currency"]
            )
        except Exception:
            pass

        return {"case_id": case_id, "status": "PENDING_CHECKER_APPROVAL", "maker_id": maker_id}

    def approve_checker(
        self,
        case_id: str,
        checker_id: str,
        notes: str = "Approved"
    ) -> DQ01PipelineResult:
        """Checker dual-authorizes repair and releases outbound handoff to bank."""
        case_data = self._case_store.get(case_id)
        if not case_data:
            raise ValueError(f"Case {case_id} not found.")

        maker_sub = case_data.get("maker_submission")
        if not maker_sub:
            raise ValueError("Cannot approve case without Maker submission.")

        # Enforce Segregation of Duties (SoD): Maker != Checker
        if maker_sub["maker_id"] == checker_id:
            raise PermissionError(f"Segregation of Duties Violation: Checker '{checker_id}' cannot be the same persona as Maker.")

        case_data["checker_approval"] = {
            "checker_id": checker_id,
            "notes": notes,
            "approved_at": datetime.now(timezone.utc).isoformat()
        }
        case_data["final_stage"] = "BANK_HANDOFF_READY"

        package = case_data["package"]
        res_res = case_data["resolution_res"]
        selected_cand = None
        if res_res and res_res.candidates:
            for c in res_res.candidates:
                if c.candidate_id == maker_sub["selected_candidate_id"]:
                    selected_cand = c
                    break
            if not selected_cand:
                selected_cand = res_res.candidates[0]

        handoff_rcpt = self.output_adapter.emit_repaired_instruction(
            candidate=selected_cand,
            decision=case_data["stp_decision"],
            filename_prefix=f"PEX_HITL_APPROVED_DQ01_{case_id}",
            original_payment_info={
                "case_id": case_id,
                "package_id": package.package_id,
                "amount": case_data["amount"],
                "currency": case_data["currency"],
                "uetr": case_data["dossier"].metadata.get("uetr", "55a8e123-44bb-4e2b-8a55-112233445566")
            },
            evidence_references=[
                {
                    "item_name": item.item_name,
                    "trust_tier": item.trust_tier.value,
                    "source": item.source_name,
                    "is_valid": item.is_valid
                }
                for item in case_data["dossier"].items.values()
            ]
        )
        outbound_env = self.output_adapter.get_outbound_envelope(handoff_rcpt.receipt_id)
        if outbound_env:
            outbound_env.governance_decision = "HITL_APPROVED_HANDOFF"
            outbound_env.lifecycle_state = HandoffLifecycleState.BANK_HANDOFF_READY

        try:
            audit_service.log_event(
                case_id=case_id,
                correlation_id=case_data["idemp_hash"],
                stage_name="HITL_CHECKER",
                actor_id=checker_id,
                actor_role="OPERATIONS_CHECKER",
                action_name="CHECKER_APPROVED",
                details=f"Checker approved DQ-01 IBAN resolution. Handoff to bank complete: {notes}",
                amount=case_data["amount"],
                currency=case_data["currency"]
            )
        except Exception:
            pass

        return DQ01PipelineResult(
            case_id=case_id,
            profile_id="DQ-01",
            idempotency_hash=case_data["idemp_hash"],
            sufficiency_result=case_data["sufficiency_res"],
            resolution_result=case_data["resolution_res"],
            authority_result=case_data["authority_res"],
            stp_decision=case_data["stp_decision"],
            handoff_receipt=handoff_rcpt,
            outbound_envelope=outbound_env,
            final_lifecycle_stage="BANK_HANDOFF_READY",
            is_stp_executed=False,
            is_hitl_routed=False,
            is_hitl_approved=True,
            recommended_routing="BANK_HANDOFF_READY"
        )


# Global singleton pipeline instance for DQ-01
dq01_pipeline = DQ01STPPipeline()
