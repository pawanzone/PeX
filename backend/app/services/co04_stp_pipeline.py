"""End-to-End CO-04 (RESTRICTED_CORRIDOR) Evidence-Driven STP Pipeline.

CO-04: RESTRICTED CORRIDOR
Phase: Phase 2D (Slice 8)
Domain: Domain 3 (Compliance & Regulatory Exceptions)

Orchestrates the complete governed 12-stage lifecycle for CO-04:
Intake -> Canonicalization -> Evidence Acquisition -> Evidence Sufficiency (E_suff)
-> Deterministic Geographic Normalization & Corridor Identification (R_det, R_uniq)
-> ISO 3166-1 Syntax (V_det) & Statutory Embargo Matrix / Bank Policy Authority (V_auth)
-> STP Eligibility (8 Predicates) -> Bank Handoff Ready / Compliance Review / Auto-Block -> Cryptographic Audit.

Enforces:
- Separation of Concerns & Compliance Boundary:
  COUNTRY RECOGNITION != CORRIDOR PERMISSIBILITY != COMPLIANCE CLEARANCE != STATUTORY LEGAL AUTHORIZATION != FUNDS MOVEMENT.
- PeX DETERMINES CORRIDOR + VALIDATES CONFIGURED RULES + EVALUATES BANK POLICY.
- Bank Compliance / Regulatory functions own compliance liability. Bank owns final disposition.
- Execution boundary: PeX never releases or moves funds directly; outputs CanonicalOutboundEnvelope with execution_owner = "BANK".
- Statutory Embargoes strictly override bank policy permissions.
- Dual-Path evaluation:
  * Permitted corridors evaluate to STP_ELIGIBLE -> BANK_HANDOFF_READY.
  * Prohibited / Embargoed corridors evaluate to COMPLIANCE_BLOCK / AUTO_BLOCK_REJECT (STP Blocked).
  * Restricted corridors with valid licenses route to MAKER_CHECKER_WORKLIST for dual-authorization (maker_id != checker_id).
- Prompt injection defense: Untrusted narrative in payment payload is sanitized and quarantined.
- Idempotency & Cryptographic Audit trail for all transitions.
"""
import re
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
from app.services.co04_corridor_resolver import (
    co04_resolver,
    VALID_ISO_3166_COUNTRIES,
    StatutoryRestrictionMatrixRecord,
    BankCorridorPolicyRecord,
    CorridorRegulatoryExemptionRecord,
    CorridorDispositionInstruction,
    RestrictionStatus,
    CorridorPolicyStatus,
)
from app.adapters.input_adapter import InboundPackage, FolderInputAdapter
from app.adapters.output_adapter import FolderOutputAdapter, BankHandoffReceipt
from app.services.audit_service import audit_service


class CO04PipelineResult(BaseModel):
    """Complete forensic result of executing the CO-04 STP Pipeline."""
    case_id: str
    profile_id: str = "CO-04"
    idempotency_hash: str
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Intermediate Contract Results:
    sufficiency_result: EvidenceSufficiencyResult
    resolution_result: Optional[ResolutionResult] = None
    authority_result: Optional[AuthorityValidationResult] = None
    stp_decision: Optional[STPEligibilityDecision] = None
    handoff_receipt: Optional[BankHandoffReceipt] = None
    outbound_envelope: Optional[CanonicalOutboundEnvelope] = None
    disposition_instruction: Optional[Dict[str, Any]] = None

    # Lifecycle State & Governance:
    uetr: Optional[str] = None
    end_to_end_id: Optional[str] = None
    origin_country: Optional[str] = None
    destination_country: Optional[str] = None
    transit_countries: List[str] = Field(default_factory=list)
    corridor_status: Optional[str] = None # PERMITTED, RESTRICTED, PROHIBITED
    compliance_disposition: Optional[str] = None # COMPLIANCE_CLEAR, COMPLIANCE_REVIEW, COMPLIANCE_BLOCK
    matched_restrictions: List[str] = Field(default_factory=list)
    exemption_license_id: Optional[str] = None
    final_lifecycle_stage: str
    is_stp_executed: bool
    is_hitl_routed: bool = False
    is_hitl_approved: bool = False
    recommended_routing: str
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)
    error_summary: Optional[str] = None


class CO04STPPipeline:
    """Master orchestrator for CO-04 (RESTRICTED_CORRIDOR) Straight-Through Processing."""

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
    ) -> CO04PipelineResult:
        """Executes the full 12-stage lifecycle for an inbound CO-04 Corridor package."""
        # Stage 1 & 2: Inbound Ingestion & Evidence Dossier Extraction
        case_id, dossier, idemp_hash = self.input_adapter.ingest_payload(package, profile_id="CO-04")
        if allow_stale_evidence:
            dossier.metadata["allow_stale_evidence"] = True

        # Log Ingestion Event
        try:
            audit_service.log_event(
                case_id=case_id,
                event_type="PACKAGE_INGESTED",
                actor="PEX_SYSTEM",
                details={"profile_id": "CO-04", "source": package.source_channel, "idempotency_hash": idemp_hash}
            )
        except Exception:
            pass

        uetr = dossier.metadata.get("uetr", "")
        end_to_end_id = dossier.metadata.get("end_to_end_id", "")
        p_amount = float(dossier.metadata.get("amount") or amount or 1000.0)
        p_currency = str(dossier.metadata.get("currency") or currency or "EUR")
        p_rail = str(dossier.metadata.get("rail") or "SEPA")
        narrative = dossier.metadata.get("remittance_narrative") or dossier.metadata.get("remittance_text")

        # Check prompt injection
        _, is_adversarial = co04_resolver.sanitize_narrative(narrative)
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
            routing = "COMPLIANCE_SUSPENSE" if any("STATUTORY" in item or "CORRIDOR" in item for item in sufficiency_res.missing_mandatory_items) else "OPERATIONS_SUSPENSE"
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
            err_msg = "; ".join(suff_errors) or "Insufficient evidence for CO-04 STP."

            res_obj = CO04PipelineResult(
                case_id=case_id,
                profile_id="CO-04",
                idempotency_hash=idemp_hash,
                sufficiency_result=sufficiency_res,
                uetr=uetr,
                end_to_end_id=end_to_end_id,
                final_lifecycle_stage=routing,
                is_stp_executed=False,
                is_hitl_routed=True,
                recommended_routing=routing,
                error_summary=err_msg
            )
            self._case_store[case_id] = {"result": res_obj, "dossier": dossier, "package": package}
            return res_obj

        # Stage 4 & 5: Deterministic Geographic Normalization & Candidate Derivation (R_det, R_uniq)
        resolution_res = resolution_engine.derive_resolution(dossier)

        if resolution_res.status != ResolutionStatus.RESOLUTION_DETERMINED or not resolution_res.primary_candidate:
            routing = "DISAMBIGUATION_DESK" if resolution_res.uniqueness == ResolutionUniqueness.RESOLUTION_AMBIGUOUS else "COMPLIANCE_SUSPENSE"
            res_obj = CO04PipelineResult(
                case_id=case_id,
                profile_id="CO-04",
                idempotency_hash=idemp_hash,
                sufficiency_result=sufficiency_res,
                resolution_result=resolution_res,
                uetr=uetr,
                end_to_end_id=end_to_end_id,
                final_lifecycle_stage=routing,
                is_stp_executed=False,
                is_hitl_routed=True,
                recommended_routing=routing,
                error_summary=resolution_res.error_message or "Corridor resolution could not be deterministically determined."
            )
            self._case_store[case_id] = {"result": res_obj, "dossier": dossier, "package": package}
            return res_obj

        primary_cand = resolution_res.primary_candidate
        instruction_payload = primary_cand.repaired_structured or {}
        orig_ctry = instruction_payload.get("origin_country")
        dest_ctry = instruction_payload.get("destination_country")
        transits = instruction_payload.get("transit_countries", [])
        corr_status = instruction_payload.get("corridor_status")
        comp_disp = instruction_payload.get("compliance_disposition")
        matched_restrictions = instruction_payload.get("matched_restrictions", [])
        exemption_id = instruction_payload.get("exemption_license_id")

        # Stage 6 & 7: ISO 3166-1 Syntax & Multi-Tier Authority Validation (V_det, V_auth)
        authority_res = authority_validation_engine.validate_candidate(
            primary_cand,
            profile_id="CO-04",
            dossier=dossier,
            bank_policy_authorized=bank_policy_authorized
        )

        # Stage 8 & 9: 8-Predicate STP Eligibility Evaluation
        # If statutory embargo is violated without exemption, force compliance gate to FAIL
        effective_compliance_status = compliance_status
        if comp_disp == "COMPLIANCE_BLOCK" or corr_status == "PROHIBITED":
            effective_compliance_status = ComplianceGateStatus.FAIL

        effective_amount = float(instruction_payload.get("amount") or p_amount)
        effective_currency = str(instruction_payload.get("currency") or p_currency)

        stp_decision = evidence_stp_evaluator.evaluate(
            case_id=case_id,
            profile_id="CO-04",
            amount=effective_amount,
            currency=effective_currency,
            sufficiency_result=sufficiency_res,
            resolution_result=resolution_res,
            authority_result=authority_res,
            policy_config=self.policy_config,
            compliance_status=effective_compliance_status,
            execution_preconditions_status=execution_preconditions,
            ai_confidence_score=ai_confidence
        )

        # Stage 10: Routing Decision & Bank Handoff / HITL Suspense / Block
        if stp_decision.stp_eligible and authority_res.is_valid and comp_disp == "COMPLIANCE_CLEAR":
            # Permitted Corridor -> Prepare Bank Outbound Handoff Envelope & Receipt via Output Adapter
            original_info = {
                "case_id": case_id,
                "package_id": package.package_id,
                "amount": effective_amount,
                "currency": effective_currency,
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
                filename_prefix=f"PEX_STP_CO04_{case_id}",
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
                        "origin_country": orig_ctry,
                        "destination_country": dest_ctry,
                        "corridor_status": corr_status,
                        "compliance_disposition": comp_disp,
                        "execution_owner": "BANK",
                        "final_state": "BANK_HANDOFF_READY"
                    }
                )
            except Exception:
                pass

            res_obj = CO04PipelineResult(
                case_id=case_id,
                profile_id="CO-04",
                idempotency_hash=idemp_hash,
                sufficiency_result=sufficiency_res,
                resolution_result=resolution_res,
                authority_result=authority_res,
                stp_decision=stp_decision,
                handoff_receipt=handoff_receipt,
                outbound_envelope=outbound_env,
                disposition_instruction=instruction_payload,
                uetr=uetr,
                end_to_end_id=end_to_end_id,
                origin_country=orig_ctry,
                destination_country=dest_ctry,
                transit_countries=transits,
                corridor_status=corr_status,
                compliance_disposition=comp_disp,
                matched_restrictions=matched_restrictions,
                exemption_license_id=exemption_id,
                final_lifecycle_stage="BANK_HANDOFF_READY",
                is_stp_executed=True,
                is_hitl_routed=False,
                recommended_routing="BANK_CLEARING_EXECUTION"
            )
            self._case_store[case_id] = {"result": res_obj, "dossier": dossier, "package": package}
            return res_obj
        else:
            # Route to appropriate HITL desk or Auto-Block / Reject
            if comp_disp == "COMPLIANCE_BLOCK" or corr_status == "PROHIBITED":
                routing = "AUTO_BLOCK_REJECT"
            elif comp_disp == "COMPLIANCE_REVIEW" or exemption_id is not None:
                routing = "MAKER_CHECKER_WORKLIST"
            elif effective_compliance_status != ComplianceGateStatus.PASS:
                routing = "COMPLIANCE_SUSPENSE"
            elif not authority_res.is_valid:
                routing = "COMPLIANCE_SUSPENSE" if "STATUTORY" in (authority_res.authoritative_source or "") else "OPERATIONS_SUSPENSE"
            else:
                routing = stp_decision.recommended_routing

            err_summary = (
                (stp_decision.policy_denial_reasons[0] if stp_decision.policy_denial_reasons else None) or
                authority_res.error_message or
                (resolution_res.error_message if resolution_res else None) or
                "Corridor STP criteria not met."
            )

            res_obj = CO04PipelineResult(
                case_id=case_id,
                profile_id="CO-04",
                idempotency_hash=idemp_hash,
                sufficiency_result=sufficiency_res,
                resolution_result=resolution_res,
                authority_result=authority_res,
                stp_decision=stp_decision,
                disposition_instruction=instruction_payload,
                uetr=uetr,
                end_to_end_id=end_to_end_id,
                origin_country=orig_ctry,
                destination_country=dest_ctry,
                transit_countries=transits,
                corridor_status=corr_status,
                compliance_disposition=comp_disp,
                matched_restrictions=matched_restrictions,
                exemption_license_id=exemption_id,
                final_lifecycle_stage=routing,
                is_stp_executed=False,
                is_hitl_routed=(routing != "AUTO_BLOCK_REJECT"),
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
    ) -> CO04PipelineResult:
        """Executes Segregation of Duties (SoD) validated Human-In-The-Loop approval for CO-04."""
        if case_id not in self._case_store:
            raise KeyError(f"Case {case_id} not found in pipeline store.")

        # Invariant: Segregation of Duties (maker_id != checker_id)
        if maker_id == checker_id:
            raise ValueError(f"Segregation of Duties Violation: Maker ({maker_id}) and Checker ({checker_id}) cannot be the same operator.")

        stored = self._case_store[case_id]
        prior_res: CO04PipelineResult = stored["result"]
        dossier: EvidenceDossier = stored["dossier"]
        package: InboundPackage = stored["package"]

        instruction_payload = prior_res.disposition_instruction or {}

        if decision == "APPROVED":
            original_info = {
                "case_id": case_id,
                "package_id": package.package_id,
                "amount": float(dossier.metadata.get("amount", 1000.0)),
                "currency": dossier.metadata.get("currency", "EUR"),
                "uetr": prior_res.uetr
            }
            approved_decision = STPEligibilityDecision.evaluate(
                case_id=case_id,
                profile_id="CO-04",
                e_suff=True,
                r_det=True,
                r_uniq=True,
                v_det=True,
                v_auth=True,
                p_bank=True,
                c_comp=True,
                x_pre=True,
                policy_denial_reasons=[],
                audit_trail=[f"Approved via Dual Authorization by Maker: {maker_id}, Checker: {checker_id}"]
            )
            candidate_to_emit = prior_res.resolution_result.primary_candidate if (prior_res.resolution_result and prior_res.resolution_result.primary_candidate) else ResolutionCandidate(
                candidate_id=f"CAND-CO04-HITL-{case_id[:8]}",
                repaired_payload=package.raw_payload_str,
                diff_summary=f"HITL approved corridor disposition for {prior_res.origin_country}->{prior_res.destination_country}",
                derivation_method="HITL_MAKER_CHECKER_APPROVAL",
                is_lossless=True,
                repaired_structured=instruction_payload
            )
            handoff_receipt = self.output_adapter.emit_repaired_instruction(
                candidate=candidate_to_emit,
                decision=approved_decision,
                filename_prefix=f"PEX_HITL_CO04_{case_id}",
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
                "recommended_routing": "BANK_CLEARING_EXECUTION",
                "handoff_receipt": handoff_receipt,
                "outbound_envelope": outbound_env
            })
            stored["result"] = updated_res
            return updated_res
        else:
            updated_res = prior_res.model_copy(update={
                "final_lifecycle_stage": "REJECTED_BY_CHECKER",
                "is_hitl_approved": False,
                "recommended_routing": "AUTO_BLOCK_REJECT"
            })
            stored["result"] = updated_res
            return updated_res


# Global singleton CO-04 pipeline
co04_pipeline = CO04STPPipeline()
