"""End-to-End DQ-08 (INVALID_ROUTING_CODE) Evidence-Driven STP Pipeline.

Orchestrates the complete governed 12-stage lifecycle for DQ-08:
Intake -> Canonicalization -> Evidence Acquisition -> Evidence Sufficiency -> Resolution Determination
-> Authority Validation -> Bank Policy -> Compliance -> Preconditions -> STP Eligibility -> Bank Handoff -> Audit.

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
from app.adapters.routing_directory_adapter import (
    RoutingDirectoryAdapterPort,
    SyntheticRoutingDirectoryAdapter,
    RoutingDirectoryEntry,
    CentralBankMergerEntry,
    RoutingIdentifierStatus,
    BankCounterpartySSI,
    TargetRailRoutingSpec,
)
from app.services.dq08_routing_resolver import (
    GovernedRoutingCodeResolver,
    governed_routing_resolver,
    DQ08RoutingResolutionResult,
    RoutingResolutionOutcome,
)
from app.adapters.input_adapter import InboundPackage, FolderInputAdapter
from app.adapters.output_adapter import FolderOutputAdapter, BankHandoffReceipt
from app.services.audit_service import audit_service


class DQ08RoutingPipelineResult(BaseModel):
    """Complete forensic result of executing the DQ-08 Routing STP Pipeline."""
    case_id: str
    profile_id: str = "DQ-08"
    idempotency_hash: str
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Intermediate Contract Results:
    sufficiency_result: Optional[EvidenceSufficiencyResult] = None
    routing_result: Optional[DQ08RoutingResolutionResult] = None
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
    is_disambiguation_routed: bool = False
    recommended_routing: str
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)
    error_summary: Optional[str] = None


class DQ08RoutingSTPPipeline:
    """Master orchestrator for DQ-08 (INVALID_ROUTING_CODE) Straight-Through Processing."""

    def __init__(
        self,
        resolver: Optional[GovernedRoutingCodeResolver] = None,
        input_adapter: Optional[FolderInputAdapter] = None,
        output_adapter: Optional[FolderOutputAdapter] = None,
        policy_config: Optional[STPPolicyConfig] = None
    ):
        self.resolver = resolver or governed_routing_resolver
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
        amount: float = 25000.0,
        currency: str = "USD",
        clearing_system: str = "USABA",
        target_rail: str = "FEDWIRE",
        bank_ssi: Optional[BankCounterpartySSI] = None,
        compliance_status: ComplianceGateStatus = ComplianceGateStatus.PASS,
        execution_preconditions: ExecutionPreconditionsStatus = ExecutionPreconditionsStatus.PASS,
        ai_confidence: Optional[float] = None
    ) -> DQ08RoutingPipelineResult:
        """Executes the full 12-stage lifecycle for an inbound DQ-08 exception package."""
        raw_xml = package.raw_payload_str
        idemp_hash = hashlib.sha256(f"{package.package_id}:{raw_xml}".encode("utf-8")).hexdigest()
        case_id = f"CASE-DQ08-RTN-{idemp_hash[:8]}"

        # Audit Ingestion Event
        audit_service.log_event(
            case_id=case_id,
            correlation_id=idemp_hash,
            stage_name="INGESTION",
            actor_id="SYSTEM_INBOUND_WATCHER",
            actor_role="SYSTEM",
            action_name="EXCEPTION_INGESTED",
            details=f"Ingested DQ-08 package {package.package_id} for clearing system {clearing_system}",
            amount=amount,
            currency=currency
        )

        # Stage 1: Build Evidence Dossier
        dossier = EvidenceDossier(case_id=case_id, profile_id="DQ-08")
        dossier.add_item(EvidenceItem(
            item_name="RAW_PAYLOAD",
            source_name="BANK_INPUT_FOLDER",
            trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
            payload={"raw_text": raw_xml}
        ))

        extracted_rtn = package.evidence_fields.get("routing_identifier") or self.resolver._extract_routing_code_from_xml(raw_xml)
        if extracted_rtn:
            dossier.add_item(EvidenceItem(
                item_name="ROUTING_IDENTIFIER",
                source_name="PAYLOAD_EXTRACTOR",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload={"routing_identifier": extracted_rtn}
            ))

        dossier.add_item(EvidenceItem(
            item_name="CLEARING_SYSTEM",
            source_name="PAYMENT_CONTEXT",
            trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
            payload={"clearing_system": clearing_system}
        ))
        dossier.add_item(EvidenceItem(
            item_name="TARGET_RAIL",
            source_name="ROUTING_SPEC",
            trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
            payload={"target_rail": target_rail}
        ))
        dossier.add_item(EvidenceItem(
            item_name="APPLICABLE_ROUTING_DIRECTORY",
            source_name="CLEARING_DIRECTORY_CONNECTOR",
            trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
            payload={"provider": "CENTRAL_BANK_ROUTING_DIRECTORY", "clearing_system": clearing_system}
        ))

        # Check Bank SSI evidence if provided
        if bank_ssi:
            dossier.add_item(EvidenceItem(
                item_name="BANK_COUNTERPARTY_SSI",
                source_name="BANK_SSI_MASTER",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload={"counterparty_id": bank_ssi.counterparty_id, "mandated_routing_code": bank_ssi.mandated_routing_code, "is_authorized": bank_ssi.is_authorized}
            ))

        # Evaluate Sufficiency (Universal Mandatory Items Present)
        has_mandatory = all(dossier.get_item(item) is not None for item in ["RAW_PAYLOAD", "ROUTING_IDENTIFIER", "CLEARING_SYSTEM", "TARGET_RAIL", "APPLICABLE_ROUTING_DIRECTORY"])
        suff_res = EvidenceSufficiencyResult(
            case_id=case_id,
            profile_id="DQ-08",
            status=EvidenceSufficiencyStatus.SUFFICIENT if has_mandatory else EvidenceSufficiencyStatus.INSUFFICIENT,
            is_sufficient=has_mandatory,
            missing_mandatory_items=[] if has_mandatory else ["ROUTING_IDENTIFIER" if not extracted_rtn else "MANDATORY_EVIDENCE"]
        )

        if not suff_res.is_sufficient:
            return self._build_failure_result(case_id, idemp_hash, suff_res, "Prerequisite routing evidence missing. Suspended to Operations.", "OPERATIONS_DESK")

        # Stage 2: Execute Governed Routing Resolution
        rail_spec = TargetRailRoutingSpec(clearing_system=clearing_system, target_rail=target_rail)
        allow_stale = package.evidence_fields.get("allow_stale_directory", False)
        res_res = self.resolver.resolve_routing_code(
            raw_payload=raw_xml,
            routing_code=extracted_rtn,
            clearing_system=clearing_system,
            target_rail_spec=rail_spec,
            bank_ssi=bank_ssi,
            allow_stale_directory=allow_stale
        )

        # Map to Canonical Resolution Result
        canon_res_status = ResolutionStatus.RESOLUTION_DETERMINED if res_res.success else ResolutionStatus.RESOLUTION_NOT_DETERMINED
        canon_res = ResolutionResult(
            profile_id="DQ-08",
            status=canon_res_status,
            uniqueness=res_res.uniqueness,
            primary_candidate=res_res.candidates[0] if res_res.candidates else None,
            all_candidates=res_res.candidates,
            is_lossless=res_res.is_lossless,
            diff_summary=res_res.diff_summary,
            error_message=res_res.error_message
        )

        # Check Ambiguity (1:N split acquisitions)
        if res_res.outcome == RoutingResolutionOutcome.MULTIPLE_SUCCESSORS or res_res.is_ambiguous:
            return self._build_disambiguation_result(case_id, idemp_hash, suff_res, res_res, canon_res, amount, currency)

        # Check Deterministic/Authority Failures
        if not res_res.success:
            return self._build_resolution_failed_result(case_id, idemp_hash, suff_res, res_res, canon_res, amount, currency)

        # Stage 3: Authority Validation ($V_{\text{det}}, V_{\text{auth}}$)
        v_det_passed = res_res.outcome in (RoutingResolutionOutcome.ACTIVE_ROUTING_VALID, RoutingResolutionOutcome.SUCCESSOR_FOUND)
        v_auth_passed = res_res.success and (res_res.directory_entry is not None)
        auth_status = AuthorityValidationStatus.PASSED if (v_det_passed and v_auth_passed) else AuthorityValidationStatus.FAILED

        auth_res = AuthorityValidationResult(
            profile_id="DQ-08",
            status=auth_status,
            is_valid=(v_det_passed and v_auth_passed),
            is_structural_syntax_valid=v_det_passed,
            is_business_authority_confirmed=v_auth_passed,
            authoritative_source="CENTRAL_BANK_ROUTING_DIRECTORY / REG_J / BOE_ISCD",
            details={"diff_summary": res_res.diff_summary}
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
            profile_id="DQ-08",
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
            return self._build_hitl_routed_result(case_id, idemp_hash, suff_res, res_res, canon_res, auth_res, stp_dec, amount, currency, raw_xml)

        # Stage 5: Autonomous STP Execution & Bank Handoff
        original_info = {
            "case_id": case_id,
            "package_id": package.package_id,
            "amount": amount,
            "currency": currency,
            "clearing_system": clearing_system
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
            filename_prefix=f"PEX_STP_DQ08_{case_id}",
            original_payment_info=original_info,
            evidence_references=evidence_refs
        )
        outbound_env = self.output_adapter.get_outbound_envelope(handoff_rcpt.receipt_id)

        # Audit Final Resolution
        audit_service.log_event(
            case_id=case_id,
            correlation_id=idemp_hash,
            stage_name="STP_DISPATCH",
            actor_id="PEX_ROUTING_ENGINE",
            actor_role="SYSTEM",
            action_name="AUTO_STP_RESOLVED",
            details=f"Autonomous STP completed for DQ-08: {res_res.diff_summary}",
            amount=amount,
            currency=currency
        )

        return DQ08RoutingPipelineResult(
            case_id=case_id,
            profile_id="DQ-08",
            idempotency_hash=idemp_hash,
            sufficiency_result=suff_res,
            routing_result=res_res,
            resolution_result=canon_res,
            authority_result=auth_res,
            stp_decision=stp_dec,
            handoff_receipt=handoff_rcpt,
            outbound_envelope=outbound_env,
            final_lifecycle_stage="BANK_HANDOFF_READY",
            is_stp_executed=True,
            is_hitl_routed=False,
            recommended_routing="BANK_OUTBOUND_QUEUE"
        )

    def process_canonical_envelope(self, envelope: CanonicalIntakeEnvelope) -> DQ08RoutingPipelineResult:
        """Helper method executing pipeline from a CanonicalIntakeEnvelope."""
        pkg = InboundPackage(
            package_id=envelope.message_id,
            source_channel="CANONICAL_ENVELOPE",
            raw_payload_str=envelope.raw_payload,
            evidence_fields=envelope.evidence_items
        )
        return self.process_package(
            package=pkg,
            amount=envelope.amount,
            currency=envelope.currency,
            clearing_system=envelope.evidence_items.get("clearing_system", "USABA"),
            target_rail=envelope.rail or "FEDWIRE"
        )

    # =========================================================================
    # Branch Helpers
    # =========================================================================

    def _build_failure_result(self, case_id: str, idemp_hash: str, suff_res: Any, error_msg: str, routing: str) -> DQ08RoutingPipelineResult:
        return DQ08RoutingPipelineResult(
            case_id=case_id,
            profile_id="DQ-08",
            idempotency_hash=idemp_hash,
            sufficiency_result=suff_res,
            final_lifecycle_stage="SUSPENDED_TO_OPERATIONS",
            is_stp_executed=False,
            is_hitl_routed=True,
            recommended_routing=routing,
            error_summary=error_msg
        )

    def _build_disambiguation_result(self, case_id: str, idemp_hash: str, suff_res: Any, res_res: Any, canon_res: Any, amount: float, currency: str) -> DQ08RoutingPipelineResult:
        audit_service.log_event(
            case_id=case_id,
            correlation_id=idemp_hash,
            stage_name="RESOLUTION",
            actor_id="PEX_ROUTING_ENGINE",
            actor_role="SYSTEM",
            action_name="AMBIGUITY_DETECTED",
            details=f"Multiple ambiguous successors detected for {res_res.original_routing_code}",
            amount=amount,
            currency=currency
        )
        return DQ08RoutingPipelineResult(
            case_id=case_id,
            profile_id="DQ-08",
            idempotency_hash=idemp_hash,
            sufficiency_result=suff_res,
            routing_result=res_res,
            resolution_result=canon_res,
            final_lifecycle_stage="DISAMBIGUATION_REQUIRED",
            is_stp_executed=False,
            is_hitl_routed=True,
            is_disambiguation_routed=True,
            recommended_routing="DISAMBIGUATION_DESK",
            error_summary="1:N multiple ambiguous successors detected in central bank merger directory."
        )

    def _build_resolution_failed_result(self, case_id: str, idemp_hash: str, suff_res: Any, res_res: Any, canon_res: Any, amount: float, currency: str) -> DQ08RoutingPipelineResult:
        return DQ08RoutingPipelineResult(
            case_id=case_id,
            profile_id="DQ-08",
            idempotency_hash=idemp_hash,
            sufficiency_result=suff_res,
            routing_result=res_res,
            resolution_result=canon_res,
            final_lifecycle_stage="RESOLUTION_FAILED",
            is_stp_executed=False,
            is_hitl_routed=True,
            recommended_routing="OPERATIONS_SUSPENSE_QUEUE",
            error_summary=res_res.error_message
        )

    def _build_hitl_routed_result(
        self,
        case_id: str,
        idemp_hash: str,
        suff_res: Any,
        res_res: Any,
        canon_res: Any,
        auth_res: Any,
        stp_dec: Any,
        amount: float,
        currency: str,
        raw_xml: str
    ) -> DQ08RoutingPipelineResult:
        # Register case in in-memory HITL store
        self._case_store[case_id] = {
            "case_id": case_id,
            "raw_payload": raw_xml,
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
            details=f"Routing exception routed to HITL (Amount ${amount} or Policy condition)",
            amount=amount,
            currency=currency
        )

        return DQ08RoutingPipelineResult(
            case_id=case_id,
            profile_id="DQ-08",
            idempotency_hash=idemp_hash,
            sufficiency_result=suff_res,
            routing_result=res_res,
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
    ) -> DQ08RoutingPipelineResult:
        """Executes governed Maker-Checker dual authorization continuation flow."""
        if maker_id == checker_id:
            raise ValueError(f"Segregation of Duties Violation: Maker ({maker_id}) cannot be the Checker ({checker_id}).")

        case = self._case_store.get(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found in active HITL store.")

        canon_res: ResolutionResult = case["canon_res"]
        repaired_xml = canon_res.primary_candidate.repaired_payload

        # Approved decision for handoff
        approved_dec = STPEligibilityDecision(
            case_id=case_id,
            profile_id="DQ-08",
            stp_eligible=True,
            evidence_sufficient=True,
            resolution_determined=True,
            resolution_unique=True,
            deterministic_validation_passed=True,
            authority_validation_passed=True,
            bank_policy_allows=True,
            compliance_gate_passed=True,
            execution_preconditions_satisfied=True,
            recommended_routing="BANK_OUTBOUND_QUEUE",
            audit_trail=[f"Maker {maker_id} submitted", f"Checker {checker_id} dual-approved: {rationale}"]
        )

        handoff_rcpt = self.output_adapter.emit_repaired_instruction(
            candidate=canon_res.primary_candidate,
            decision=approved_dec,
            filename_prefix=f"PEX_HITL_DQ08_{case_id}",
            original_payment_info={"case_id": case_id, "amount": case.get("amount"), "currency": case.get("currency")}
        )
        outbound_env = self.output_adapter.get_outbound_envelope(handoff_rcpt.receipt_id)

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

        return DQ08RoutingPipelineResult(
            case_id=case_id,
            profile_id="DQ-08",
            idempotency_hash=hashlib.sha256(case_id.encode()).hexdigest(),
            resolution_result=canon_res,
            handoff_receipt=handoff_rcpt,
            outbound_envelope=outbound_env,
            final_lifecycle_stage="BANK_HANDOFF_READY",
            is_stp_executed=False,
            is_hitl_routed=True,
            is_hitl_approved=True,
            recommended_routing="BANK_OUTBOUND_QUEUE"
        )


# Global singleton instance
dq08_routing_pipeline = DQ08RoutingSTPPipeline()
