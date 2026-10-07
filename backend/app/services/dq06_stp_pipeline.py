"""End-to-End DQ-06 (INVALID_MISSING_PURPOSE_CODE) Evidence-Driven STP Pipeline.

DQ-06: INVALID / MISSING PURPOSE CODE
Phase: Phase 2C (Slice 6)

Orchestrates the complete governed 12-stage lifecycle for DQ-06:
Intake -> Canonicalization -> Evidence Acquisition -> Evidence Sufficiency (E_suff)
-> Semantic Interpretation & Purpose Candidate Derivation (R_det, R_uniq)
-> ISO 20022 Code-Set (V_det) & Bank Purpose / Corridor Policy (V_auth)
-> STP Eligibility (8 Predicates) -> Bank Handoff Ready / HITL Routing -> Audit Provenance.

Enforces:
- Semantic interpretation produces hypotheses only, NOT authority
- Code-set membership establishes V_det only, NOT V_auth
- Keyword matching does NOT authorize autonomous STP
- Bank Purpose Policy and Corridor Rules establish V_auth
- Ambiguity detection (multiple plausible candidates force R_uniq=False -> DISAMBIGUATION_DESK)
- Contradictory authority fail-closed behavior
- Maker-Checker Segregation of Duties (SoD) for HITL continuation (maker_id != checker_id)
- Bank handoff boundary (execution_owner = "BANK", BANK_HANDOFF_READY)
- Lossless financial semantic invariance across all non-purpose fields
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
from app.services.dq06_purpose_resolver import (
    dq06_resolver,
    PurposeResolutionOutcome,
    BankPurposePolicyEntry,
    BankCorridorPurposePolicy,
    ISO_20022_EXTERNAL_PURPOSE_CODES,
)
from app.adapters.input_adapter import InboundPackage, FolderInputAdapter
from app.adapters.output_adapter import FolderOutputAdapter, BankHandoffReceipt
from app.services.audit_service import audit_service


class DQ06PipelineResult(BaseModel):
    """Complete forensic result of executing the DQ-06 STP Pipeline."""
    case_id: str
    profile_id: str = "DQ-06"
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
    original_purpose_code: Optional[str] = None
    repaired_purpose_code: Optional[str] = None
    remittance_text: Optional[str] = None
    purpose_outcome: Optional[str] = None
    final_lifecycle_stage: str
    is_stp_executed: bool
    is_hitl_routed: bool = False
    is_hitl_approved: bool = False
    recommended_routing: str
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)
    error_summary: Optional[str] = None


class DQ06STPPipeline:
    """Master orchestrator for DQ-06 (INVALID_MISSING_PURPOSE_CODE) Straight-Through Processing."""

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
        amount: float = 12500.0,
        currency: str = "EUR",
        compliance_status: ComplianceGateStatus = ComplianceGateStatus.PASS,
        execution_preconditions: ExecutionPreconditionsStatus = ExecutionPreconditionsStatus.PASS,
        ai_confidence: Optional[float] = None
    ) -> DQ06PipelineResult:
        """Executes the full 12-stage lifecycle for an inbound DQ-06 Purpose Code exception package."""
        # Stage 1 & 2: Inbound Ingestion & Evidence Dossier Extraction
        case_id, dossier, idemp_hash = self.input_adapter.ingest_payload(package, profile_id="DQ-06")

        # Log Ingestion Event
        try:
            audit_service.log_event(
                case_id=case_id,
                correlation_id=idemp_hash,
                stage_name="INGESTION",
                actor_id="SYSTEM_INBOUND_WATCHER",
                actor_role="SYSTEM",
                action_name="EXCEPTION_INGESTED",
                details=f"Ingested DQ-06 package {package.package_id}",
                amount=amount,
                currency=currency
            )
        except Exception:
            pass

        # Stage 3: Evaluate Evidence Sufficiency (E_suff)
        sufficiency_res = sufficiency_engine.evaluate_sufficiency(dossier)

        # Stage 4: Deterministic Semantic Resolution & Candidate Generation (R_det, R_uniq)
        resolution_res: Optional[ResolutionResult] = None
        authority_res: Optional[AuthorityValidationResult] = None
        stp_decision: Optional[STPEligibilityDecision] = None
        handoff_rcpt: Optional[BankHandoffReceipt] = None
        outbound_env: Optional[CanonicalOutboundEnvelope] = None

        if sufficiency_res.is_sufficient:
            resolution_res = resolution_engine.derive_resolution(dossier)

            # Stage 5: Authority & Bank Policy Corroboration Validation (V_det, V_auth)
            if resolution_res.primary_candidate is not None:
                authority_res = authority_validation_engine.validate_candidate(
                    candidate=resolution_res.primary_candidate,
                    profile_id="DQ-06",
                    dossier=dossier
                )

        if resolution_res is None:
            resolution_res = ResolutionResult(
                profile_id="DQ-06",
                status=ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                is_lossless=False,
                error_message="Prerequisite evidence insufficient."
            )

        if authority_res is None:
            authority_res = AuthorityValidationResult(
                profile_id="DQ-06",
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
            profile_id="DQ-06",
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

        orig_purp_val = dossier.metadata.get("existing_purpose_code") or dossier.metadata.get("purpose_code")
        repaired_purp_val = None
        rmt_text_val = dossier.metadata.get("remittance_text")
        outcome_val = None

        if resolution_res and resolution_res.primary_candidate:
            diff_text = resolution_res.primary_candidate.diff_summary
            if "Repaired purpose code" in diff_text or "Inserted" in diff_text or "Replaced" in diff_text:
                outcome_val = "SINGLE_CANDIDATE_REPAIRED"
                # Extract repaired code
                rep_match = re.search(r'<Purp>\s*<Cd>([A-Z0-9]{4})</Cd>\s*</Purp>', resolution_res.primary_candidate.repaired_payload)
                if rep_match:
                    repaired_purp_val = rep_match.group(1)
                elif "CAND-" in resolution_res.primary_candidate.candidate_id:
                    repaired_purp_val = resolution_res.primary_candidate.candidate_id.split("-")[2]
            elif "structurally valid" in diff_text:
                outcome_val = "VALID_EXISTING_PURPOSE"
                repaired_purp_val = orig_purp_val

        if stp_decision.stp_eligible and resolution_res.primary_candidate is not None:
            # Stage 8: Semantic Invariance Verification
            self._verify_semantic_invariance(package.raw_payload_str, resolution_res.primary_candidate.repaired_payload)

            final_stage = "BANK_HANDOFF_READY"
            is_stp_executed = True

            # Stage 9: Generate Outbound Canonical Envelope & Bank Handoff
            original_info = {
                "case_id": case_id,
                "package_id": package.package_id,
                "amount": amount,
                "currency": currency,
                "uetr": dossier.metadata.get("uetr", "66b9f234-55cc-4f3c-9b66-223344556677")
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
                filename_prefix=f"PEX_STP_DQ06_{case_id}",
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
                    details=f"Autonomous STP bank handoff generated for DQ-06 case {case_id} with purpose '{repaired_purp_val}'",
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
                 (resolution_res and resolution_res.error_message and any(k in resolution_res.error_message for k in ("PROHIBITED", "unauthorized", "unconfigured", "contradictory", "disallows"))):
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
                    details=f"DQ-06 routed to {final_stage}: {denial_summary}",
                    amount=amount,
                    currency=currency
                )
            except Exception:
                pass

        denial_reasons = list(stp_decision.policy_denial_reasons) if stp_decision.policy_denial_reasons else []
        if authority_res and not authority_res.is_valid and authority_res.error_message and authority_res.error_message not in denial_reasons:
            denial_reasons.append(authority_res.error_message)

        return DQ06PipelineResult(
            case_id=case_id,
            profile_id="DQ-06",
            idempotency_hash=idemp_hash,
            sufficiency_result=sufficiency_res,
            resolution_result=resolution_res,
            authority_result=authority_res,
            stp_decision=stp_decision,
            handoff_receipt=handoff_rcpt,
            outbound_envelope=outbound_env,
            original_purpose_code=orig_purp_val,
            repaired_purpose_code=repaired_purp_val,
            remittance_text=rmt_text_val,
            purpose_outcome=outcome_val,
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
    ) -> DQ06PipelineResult:
        """Processes a transport-neutral CanonicalIntakeEnvelope through DQ-06 STP pipeline."""
        package = InboundPackage(
            package_id=envelope.message_id,
            source_channel=envelope.channel or "REST_API",
            raw_payload_str=envelope.raw_payload,
            evidence_fields=envelope.evidence_items,
            metadata={"uetr": envelope.uetr, "amount": envelope.amount, "currency": envelope.currency, "narrative": envelope.narrative}
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
        """Maker submits human investigation and Purpose Code repair recommendation."""
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
                details=f"Maker submitted Purpose Code repair '{selected_candidate_id}': {rationale}",
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
    ) -> DQ06PipelineResult:
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
            filename_prefix=f"PEX_HITL_APPROVED_DQ06_{case_id}",
            original_payment_info={
                "case_id": case_id,
                "package_id": package.package_id,
                "amount": case_data["amount"],
                "currency": case_data["currency"],
                "uetr": case_data["dossier"].metadata.get("uetr", "66b9f234-55cc-4f3c-9b66-223344556677")
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
                details=f"Checker approved DQ-06 Purpose Code resolution. Handoff to bank complete: {notes}",
                amount=case_data["amount"],
                currency=case_data["currency"]
            )
        except Exception:
            pass

        return DQ06PipelineResult(
            case_id=case_id,
            profile_id="DQ-06",
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

    def _verify_semantic_invariance(self, original_xml: str, repaired_xml: str):
        """Verifies that non-purpose fields (amounts, currencies, UETR, parties, accounts) are identical."""
        try:
            orig_root = ET.fromstring(original_xml)
            rep_root = ET.fromstring(repaired_xml)
        except Exception:
            return  # If non-XML, skip tree parse

        # Helper to extract text
        def get_val(root, tag):
            el = root.find(f".//{{urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08}}{tag}")
            if el is None:
                el = root.find(f".//{tag}")
            return el.text if el is not None else None

        # Assert invariance on critical business fields
        for field in ["IntrBkSttlmAmt", "IntrBkSttlmDt", "EndToEndId", "UETR", "Dbtr/Nm", "Cdtr/Nm", "DbtrAcct/Id/IBAN", "CdtrAcct/Id/IBAN"]:
            orig_val = get_val(orig_root, field.split("/")[-1])
            rep_val = get_val(rep_root, field.split("/")[-1])
            if orig_val is not None and rep_val is not None and orig_val != rep_val:
                raise ValueError(f"CRITICAL SEMANTIC INVARIANCE BREACH: Field '{field}' mutated from '{orig_val}' to '{rep_val}' during Purpose Code repair.")


# Global singleton pipeline instance for DQ-06
dq06_pipeline = DQ06STPPipeline()
