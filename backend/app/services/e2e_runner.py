"""Canonical End-to-End JSON Execution Harness for PeX.

Reads structured payment exception JSON from input, validates schema, drives processing
through real PeX domain services and provider-neutral ports, evaluates the canonical 8 predicates,
and generates validated CanonicalE2EOutput JSON.
"""
import time
import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone

from app.schemas.contracts.e2e_schemas import (
    CanonicalE2EInput,
    CanonicalE2EOutput,
    PredicateBreakdown,
    E2EProvenance,
)
from app.schemas.contracts.evidence_schemas import (
    EvidencePackageEnvelope,
    EvidenceItem,
    TrustTier,
    EvidenceValidationStatus,
)
from app.schemas.contracts.authority_schemas import (
    QuestionDomain,
    AuthorityResolutionContext,
)
from app.schemas.contracts.policy_schemas import (
    BankPolicyEnvelope,
    BankRiskThresholds,
    PolicyEvaluationResult,
)
from app.schemas.contracts.bank_handoff_schemas import (
    BankHandoffEnvelope,
    DispatchIntent,
    ApprovalSignature,
    ExecutionOwner,
    HandoffStatus,
)
from app.schemas.contracts.audit_schemas import AuditBlockPayload

from app.adapters.reference.reference_evidence_adapter import InMemoryEvidenceAdapter
from app.adapters.reference.reference_authority_adapter import InMemoryContextualAuthorityAdapter
from app.adapters.reference.reference_policy_adapter import InMemoryBankPolicyAdapter
from app.adapters.reference.reference_idempotency_adapter import InMemoryIdempotencyAdapter
from app.adapters.reference.reference_message_broker_adapter import InMemoryMessageBrokerAdapter
from app.adapters.reference.reference_core_banking_adapter import InMemoryCoreBankingDDAAdapter
from app.adapters.reference.reference_regulatory_adapter import InMemoryRegulatoryScreeningAdapter
from app.adapters.reference.reference_token_vault_adapter import InMemorySecretTokenizationVaultAdapter
from app.adapters.reference.reference_audit_adapter import InMemoryAuditLedgerAdapter
from app.adapters.reference.reference_observability_adapter import InMemoryObservabilityTraceAdapter
from app.adapters.reference.reference_bank_handoff_adapter import InMemoryBankHandoffAdapter
from app.adapters.reference.reference_configuration_adapter import InMemoryConfigurationAdapter
from app.adapters.reference.reference_health_adapter import InMemoryHealthReadinessAdapter
from app.services.dynamic_config_resolver import DynamicEvidenceConfigResolver
from app.profile_packs import registry as profile_packs
from app.profile_packs.schema import ResolutionContext
from app.services.engines import (
    account_master_engine,
    routing_clearing_engine,
    remittance_document_engine,
    settlement_reconciliation_engine,
    compliance_dossier_engine,
    treasury_exposure_engine,
    wave4_resolution_engine,
)


class E2EExecutionHarness:
    """Reusable execution engine that processes CanonicalE2EInput and produces CanonicalE2EOutput."""

    def __init__(
        self,
        evidence_port: Optional[InMemoryEvidenceAdapter] = None,
        authority_port: Optional[InMemoryContextualAuthorityAdapter] = None,
        policy_port: Optional[InMemoryBankPolicyAdapter] = None,
        idempotency_port: Optional[InMemoryIdempotencyAdapter] = None,
        broker_port: Optional[InMemoryMessageBrokerAdapter] = None,
        core_banking_port: Optional[InMemoryCoreBankingDDAAdapter] = None,
        regulatory_port: Optional[InMemoryRegulatoryScreeningAdapter] = None,
        token_vault_port: Optional[InMemorySecretTokenizationVaultAdapter] = None,
        audit_port: Optional[InMemoryAuditLedgerAdapter] = None,
        observability_port: Optional[InMemoryObservabilityTraceAdapter] = None,
        bank_handoff_port: Optional[InMemoryBankHandoffAdapter] = None,
        config_port: Optional[InMemoryConfigurationAdapter] = None,
        health_port: Optional[InMemoryHealthReadinessAdapter] = None,
    ):
        self.evidence_port = evidence_port or InMemoryEvidenceAdapter()
        self.authority_port = authority_port or InMemoryContextualAuthorityAdapter()
        self.policy_port = policy_port or InMemoryBankPolicyAdapter()
        self.idempotency_port = idempotency_port or InMemoryIdempotencyAdapter()
        self.broker_port = broker_port or InMemoryMessageBrokerAdapter()
        self.core_banking_port = core_banking_port or InMemoryCoreBankingDDAAdapter()
        self.regulatory_port = regulatory_port or InMemoryRegulatoryScreeningAdapter()
        self.token_vault_port = token_vault_port or InMemorySecretTokenizationVaultAdapter()
        self.audit_port = audit_port or InMemoryAuditLedgerAdapter()
        self.observability_port = observability_port or InMemoryObservabilityTraceAdapter()
        self.bank_handoff_port = bank_handoff_port or InMemoryBankHandoffAdapter()
        self.config_port = config_port or InMemoryConfigurationAdapter()
        self.health_port = health_port or InMemoryHealthReadinessAdapter()
        self.dynamic_config_resolver = DynamicEvidenceConfigResolver(self.config_port)

    def process_input(
        self,
        input_data: Union[str, Path, Dict[str, Any]],
        output_file_path: Optional[Union[str, Path]] = None
    ) -> CanonicalE2EOutput:
        """Executes a payment exception JSON end-to-end through the PeX pipeline."""
        start_time = time.perf_counter()

        # 1. Parse and validate input JSON against schema
        if isinstance(input_data, (str, Path)):
            raw_text = Path(input_data).read_text(encoding="utf-8")
            raw_dict = json.loads(raw_text)
            e2e_input = CanonicalE2EInput(**raw_dict)
        elif isinstance(input_data, dict):
            e2e_input = CanonicalE2EInput(**input_data)
        elif isinstance(input_data, CanonicalE2EInput):
            e2e_input = input_data
        else:
            raise TypeError(f"Unsupported input type: {type(input_data)}")

        case_id = e2e_input.exception_id
        pmt = e2e_input.payment_info
        profile = (e2e_input.profile_id or "UNKNOWN").upper()
        domain = e2e_input.domain or ("DATA_QUALITY" if "DQ" in profile else ("PROCESSING" if "PR" in profile else ("COMPLIANCE" if "CO" in profile else ("CLIENT_TREASURY" if "TR" in profile else "SETTLEMENT_RETURNS"))))
        
        # Start Observability Trace
        trace = self.observability_port.start_trace(case_id, pmt.uetr)

        # 2. Evidence Acquisition & Sufficiency Evaluation (E_suff)
        evidence_ctx = {
            **e2e_input.bank_supplied_evidence,
            **e2e_input.external_authoritative_evidence,
            **e2e_input.derived_evidence
        }
        
        # Resolve dynamic published evidence configuration
        tx_context = {
            "amount": pmt.amount,
            "currency": pmt.currency,
            "clearing_rail": pmt.clearing_rail,
            "profile_id": profile,
            "tenant_id": getattr(e2e_input, "tenant_id", "DEFAULT_BANK"),
            **evidence_ctx
        }
        resolved_reqs = self.dynamic_config_resolver.resolve_requirements(
            tenant_id=getattr(e2e_input, "tenant_id", "DEFAULT_BANK"),
            profile_id=profile,
            transaction_context=tx_context
        )
        mandatory_types = resolved_reqs.active_mandatory_types
        
        envelope = self.evidence_port.acquire_evidence(case_id, profile, pmt.model_dump(), evidence_ctx)
        envelope = self.evidence_port.evaluate_sufficiency(envelope, mandatory_types)
        e_suff = envelope.evidence_sufficient


        # Resolve Bank Policy
        active_policy = self.policy_port.get_active_policy()
        if e2e_input.bank_policy_overrides:
            active_policy = BankPolicyEnvelope(**e2e_input.bank_policy_overrides)

        # 3. Deterministic Resolution Derivation (R_det, R_uniq, V_det)
        r_det = False
        r_uniq = False
        v_det = False
        resolution_rec = None
        repaired_fields = []
        resolution_basis = ""

        # Profile packs: one resolver per profile (see app/profile_packs). A profile without a pack falls through to the
        # fail-closed default below.
        _pack_res = profile_packs.resolve_if_enabled(
            profile, ResolutionContext(profile=profile, pmt=pmt, evidence=evidence_ctx, envelope=envelope,
                                       tenant_id=getattr(e2e_input, "tenant_id", None) or "DEFAULT_BANK",
                                       policy=active_policy))
        if _pack_res is not None:
            r_det, r_uniq, v_det = _pack_res.determined, _pack_res.unique, _pack_res.validated
            repaired_fields = _pack_res.repaired_fields
            resolution_rec = _pack_res.recommendation
            resolution_basis = _pack_res.basis
        else:
            # FAIL CLOSED: a profile without registered deterministic resolution logic must not reach STP.
            # (Previously this branch set r_det = r_uniq = v_det = True, so ANY unregistered profile whose default
            # mandatory evidence was present was STP-eligible without any resolution being derived.)
            # Narrow exception that preserves the Wave0B dynamic-evidence design: the tenant has explicitly
            # PUBLISHED an evidence configuration for this profile (generic evidence-driven evaluation by choice).
            _tenant = getattr(e2e_input, "tenant_id", None) or "DEFAULT_BANK"
            _published = None
            try:
                _published = self.config_port.get_evidence_config(_tenant, profile) or self.config_port.get_evidence_config("DEFAULT_BANK", profile)
            except Exception:
                _published = None
            if _published is not None:
                resolution_basis = f"Profile {profile} evaluated under standard rules."
                r_det = True
                r_uniq = True
                v_det = True
            else:
                resolution_basis = f"No deterministic resolution logic is registered for profile {profile}; routed to human review (fail closed)."
                r_det = False
                r_uniq = False
                v_det = False

        # 3b. Eurozone rail-rules overlay (SEPA Instant, SEPA return codes, EU VoP). Only ever tightens.
        eu_block_reason = None
        _eu = None
        try:
            from app.services.eur_rail_overlay import evaluate_rail_rules
            _eu = evaluate_rail_rules(profile, pmt, evidence_ctx)
        except Exception as _eu_err:  # fail closed on overlay error for EU schemes
            if (pmt.clearing_rail or "").upper() in ("SEPA_SCT", "SEPA_INST", "T2"):
                _eu = {"block": True, "basis": f"Eurozone rail rules could not be evaluated ({_eu_err}); fail closed.", "rec": None, "notes": []}
        if _eu:
            if _eu.get("block"):
                r_det = False
                resolution_rec = _eu.get("rec") or resolution_rec
                resolution_basis = _eu["basis"]
                eu_block_reason = _eu["basis"]
            elif _eu.get("rec_action") and isinstance(resolution_rec, dict):
                resolution_rec = {**resolution_rec, "action": _eu["rec_action"], "handling": _eu.get("handling")}
                resolution_basis = (resolution_basis + " " + " ".join(_eu.get("notes", []))).strip()

        # 4. Contextual Authority Validation (V_auth)
        _pk = profile_packs.get_pack(profile) if profile_packs.is_enabled(profile) else None
        if _pk is not None:
            q_domain = QuestionDomain[_pk.authority_domain]
        elif "DQ" in profile or profile in ["ST-02", "ST-03", "TR-01", "TR-02", "TR-03", "TR-05", "TR-06", "TR-08"]:
            q_domain = QuestionDomain.ACCOUNT_OWNERSHIP_BALANCE
        elif profile in ["PR-08", "PR-07", "PR-09", "TR-07"]:
            q_domain = QuestionDomain.QUEUE_PROCESSING_STATE
        elif "CO" in profile:
            q_domain = QuestionDomain.LEGAL_PROHIBITION
        else:
            q_domain = QuestionDomain.CLEARING_SETTLEMENT_STATUS

        auth_res = self.authority_port.resolve_authority(q_domain, evidence_ctx)
        v_auth = auth_res.is_valid_authority
            
        policy_eval = self.policy_port.evaluate_transaction(
            policy=active_policy,
            profile_id=profile,
            amount=pmt.amount,
            currency=pmt.currency,
            action_type="REPAIR_AND_RELEASE"
        )
        p_bank = policy_eval.policy_allows_action and (policy_eval.is_autonomous_stp_permitted or policy_eval.is_batch_fast_lane_permitted)

        # 6. Regulatory Screening Gate (C_comp)
        screening = self.regulatory_port.screen_entity(
            entity_name=pmt.creditor_name or "Commercial Client",
            country=evidence_ctx.get("creditor_country", "US"),
            corridor=pmt.clearing_rail,
            context=evidence_ctx
        )
        c_comp = screening.compliance_gate_passed

        # 7. Execution Preconditions (X_pre)
        # Verify idempotency lock acquisition
        if evidence_ctx.get("idempotency_locked", False):
            x_pre = False
        else:
            idemp_res = self.idempotency_port.acquire_lock(f"IDEMP-{case_id}", holder_id="PEX-E2E-ENGINE")
            x_pre = (idemp_res.status.value in ["ACQUIRED", "ALREADY_EXECUTED"])

        # 8. Canonical 8-Predicate Conjunction:
        stp_eligible = bool(e_suff and r_det and r_uniq and v_det and v_auth and p_bank and c_comp and x_pre)

        # Formulate Decision Reason
        denials = []
        if not e_suff:
            denials.append(f"Evidence insufficient: missing mandatory {envelope.missing_mandatory_types} / stale {envelope.stale_types} / contradictory {envelope.contradictions}")
        if not r_det:
            denials.append("Deterministic resolution could not be derived." + (f" {eu_block_reason}" if eu_block_reason else ""))
        if not r_uniq:
            if envelope.contradictions:
                denials.append(f"Resolution is ambiguous due to contradictory evidence ({', '.join(envelope.contradictions)}).")
            else:
                denials.append("Resolution is ambiguous with multiple candidate matches.")
        if not v_det:
            denials.append("Deterministic validation / checksum failed.")
        if not v_auth:
            denials.append(f"Authoritative source validation failed: {auth_res.rejection_reason}")
        if not p_bank:
            denials.append(f"Bank policy disallows autonomous STP: {policy_eval.denial_reasons}")
        if not c_comp:
            denials.append(f"Compliance screening gate flagged entity on {screening.matched_lists}")
        if not x_pre:
            denials.append("Execution preconditions failed: idempotency lock unavailable.")

        stp_reason = "All 8 canonical predicates satisfied (E_suff ∧ R_det ∧ R_uniq ∧ V_det ∧ V_auth ∧ P_bank ∧ C_comp ∧ X_pre)." if stp_eligible else "; ".join(denials)

        # 9. Cryptographic Audit Event Logging
        audit_payload = AuditBlockPayload(
            event_id=f"AUD-{uuid.uuid4().hex[:6].upper()}",
            case_id=case_id,
            correlation_id=pmt.uetr,
            stage_name="E2E_RESOLUTION_EVALUATION",
            actor_id="PEX_E2E_CANONICAL_RUNNER",
            actor_role="SYSTEM_AUTOMATION",
            action_name="E2E_RESOLUTION_COMPLETED",
            details=f"Case {case_id} evaluated with stp_eligible={stp_eligible}. Reason: {stp_reason[:80]}",
            control_tags=["E2E_JSON", "WAVE_0A", "CANONICAL_8_PREDICATES"]
        )
        audit_receipt = self.audit_port.append_event(audit_payload)

        # 10. Bank Handoff Packaging
        intent = DispatchIntent(
            intent_id=f"INT-{uuid.uuid4().hex[:6].upper()}",
            action_type="REPAIR_AND_RELEASE" if r_det else "INVESTIGATION_HOLD",
            target_clearing_rail=pmt.clearing_rail,
            repaired_fields=repaired_fields
        )
        signatures = []
        if stp_eligible:
            signatures.append(
                ApprovalSignature(
                    approval_id=f"SIG-AUTO-{uuid.uuid4().hex[:6].upper()}",
                    approver_id="SYS-AUTONOMOUS-STP",
                    approver_name="PeX Governed Autonomous Reasoner",
                    approver_role="SYSTEM_STP_AUTONOMOUS",
                    action="AUTONOMOUS_POLICY_APPROVE"
                )
            )

        handoff_envelope = self.bank_handoff_port.create_handoff_envelope(
            case_id=case_id,
            payment_id=pmt.payment_id,
            uetr=pmt.uetr,
            dispatch_intent=intent,
            stp_eligible=stp_eligible,
            stp_formula_evaluation={
                "e_suff": e_suff, "r_det": r_det, "r_uniq": r_uniq, "v_det": v_det,
                "v_auth": v_auth, "p_bank": p_bank, "c_comp": c_comp, "x_pre": x_pre
            },
            signatures=signatures,
            audit_block_hash=audit_receipt.block_hash,
            is_autonomous_zero_touch=stp_eligible
        )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Assemble Output Schema
        output = CanonicalE2EOutput(
            exception_id=case_id,
            detected_profile_id=profile,
            domain=domain,
            evidence_status="CONTRADICTORY" if envelope.contradictions else ("STALE" if envelope.stale_types else ("SUFFICIENT" if e_suff else "INSUFFICIENT")),
            evidence_used=[item.evidence_type for item in envelope.items if item.validation_status.value == "AVAILABLE"],
            evidence_missing=envelope.missing_mandatory_types,
            evidence_contradictions=envelope.contradictions,
            resolution_status="RESOLVED" if (r_det and r_uniq) else "INVESTIGATION_REQUIRED",
            resolution_recommendation=resolution_rec,
            resolution_basis=resolution_basis,
            repaired_fields=repaired_fields,
            authority_status="AUTHORITATIVE_CONFIRMED" if v_auth else "UNAVAILABLE",
            bank_policy_status="POLICY_PERMITTED" if p_bank else "POLICY_BLOCKED",
            compliance_status="COMPLIANCE_CLEARED" if c_comp else "SANCTIONS_HOLD",
            stp_eligible=stp_eligible,
            stp_decision_reason=stp_reason,
            predicate_breakdown=PredicateBreakdown(
                e_suff=e_suff,
                r_det=r_det,
                r_uniq=r_uniq,
                v_det=v_det,
                v_auth=v_auth,
                p_bank=p_bank,
                c_comp=c_comp,
                x_pre=x_pre,
                stp_formula_result=stp_eligible
            ),
            ai_confidence_score=0.98 if stp_eligible else 0.50, # Advisory only
            hitl_required=not stp_eligible,
            approval_requirement="NONE_AUTONOMOUS_STP" if stp_eligible else "MAKER_CHECKER_DUAL_AUTH",
            next_action="DISPATCH_TO_BANK_GATEWAY" if stp_eligible else "ROUTE_TO_OPERATIONS_WORKLIST",
            bank_handoff_status=handoff_envelope.status.value,
            execution_owner="BANK", # Absolute invariant
            audit_event_id=audit_payload.event_id,
            audit_chain_block_hash=audit_receipt.block_hash,
            processing_latency_ms=elapsed_ms,
            warnings=policy_eval.policy_warnings,
            errors=denials
        )

        # Save to output file if requested
        if output_file_path:
            out_p = Path(output_file_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(output.model_dump_json(indent=2), encoding="utf-8")

        return output


# Global singleton
e2e_runner = E2EExecutionHarness()
