"""PeX-Native Human-in-the-Loop (HITL) Workflow Service.

Provides dynamic gap dossier generation, operator field validation, Mode 4 evidence ingestion,
and instant deterministic 8-predicate re-evaluation.
Reference: PeX_Evidence_Acquisition_and_Resolution_Contract_v0.3.1.md Section 5 & 6.
"""
import uuid
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.schemas.contracts.evidence_config_schemas import (
    HitlEvidenceSubmissionRequest,
    HitlEvidenceSubmissionResponse,
    HitlWorkflowConfig,
    HitlFieldDefinition,
)
from app.schemas.contracts.evidence_schemas import (
    EvidenceItem,
    EvidencePackageEnvelope,
    EvidenceValidationStatus,
)
from app.services.dynamic_config_resolver import DynamicEvidenceConfigResolver
from app.services.acquisition_gateway import AcquisitionGateway
from app.ports.evidence_store_port import EvidenceStorePort
from app.ports.configuration_port import ConfigurationSchemaPort


class HitlGapDossier:
    """Dynamic dossier presented to a human operator in the PeX resolution cockpit."""
    def __init__(
        self,
        case_id: str,
        profile_id: str,
        tenant_id: str,
        missing_evidence_types: List[str],
        fields: List[HitlFieldDefinition],
        allowed_actions: List[str],
        instructions: str
    ):
        self.case_id = case_id
        self.profile_id = profile_id
        self.tenant_id = tenant_id
        self.missing_evidence_types = missing_evidence_types
        self.fields = fields
        self.allowed_actions = allowed_actions
        self.instructions = instructions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "profile_id": self.profile_id,
            "tenant_id": self.tenant_id,
            "missing_evidence_types": self.missing_evidence_types,
            "fields": [f.model_dump() for f in self.fields],
            "allowed_actions": self.allowed_actions,
            "instructions": self.instructions,
            "created_at": datetime.now(timezone.utc).isoformat()
        }


class HITLWorkflowService:
    """Manages interactive human operator evidence acquisition and immediate re-evaluation."""

    def __init__(
        self,
        config_resolver: DynamicEvidenceConfigResolver,
        acquisition_gateway: AcquisitionGateway,
        evidence_store: EvidenceStorePort
    ):
        self._resolver = config_resolver
        self._gateway = acquisition_gateway
        self._store = evidence_store

    def generate_gap_dossier(
        self,
        case_id: str,
        profile_id: str,
        tenant_id: str,
        missing_evidence_types: List[str],
        transaction_context: Dict[str, Any]
    ) -> HitlGapDossier:
        """Generates dynamic gap requirements and interactive fields for the operator."""
        resolved = self._resolver.resolve_requirements(tenant_id, profile_id, transaction_context)
        hitl_cfg = resolved.hitl_config

        fields = hitl_cfg.fields if hitl_cfg and hitl_cfg.fields else []
        actions = hitl_cfg.actions if hitl_cfg and hitl_cfg.actions else ["SUPPLY_EVIDENCE", "CONFIRM_REPAIR", "ESCALATE", "REJECT"]

        instructions = (
            f"Case {case_id} requires human operator evidence supply for missing types: {missing_evidence_types}. "
            f"Please verify data with customer or authoritative directory before submitting."
        )

        return HitlGapDossier(
            case_id=case_id,
            profile_id=profile_id,
            tenant_id=tenant_id,
            missing_evidence_types=missing_evidence_types,
            fields=fields,
            allowed_actions=actions,
            instructions=instructions
        )

    def process_operator_submission(
        self,
        submission: HitlEvidenceSubmissionRequest,
        transaction_context: Dict[str, Any],
        re_eval_callback: Optional[Any] = None
    ) -> HitlEvidenceSubmissionResponse:
        """Processes operator submission, validates fields, saves Mode 4 evidence, and triggers re-evaluation."""
        resolved = self._resolver.resolve_requirements(submission.tenant_id, submission.profile_id, transaction_context)
        hitl_cfg = resolved.hitl_config

        # 1. Field validation
        if hitl_cfg and hitl_cfg.fields:
            for f in hitl_cfg.fields:
                if f.required and f.field_id not in submission.submitted_fields:
                    return HitlEvidenceSubmissionResponse(
                        case_id=submission.case_id,
                        submission_id=f"SUB-ERR-{uuid.uuid4().hex[:6]}",
                        is_accepted=False,
                        re_evaluation_triggered=False,
                        new_evidence_sufficient=False,
                        new_stp_eligible=False,
                        new_status="VALIDATION_FAILED",
                        message=f"Missing required field: {f.label} ({f.field_id})"
                    )

                if f.field_id in submission.submitted_fields and f.validation_regex:
                    val_str = str(submission.submitted_fields[f.field_id])
                    if not re.match(f.validation_regex, val_str):
                        return HitlEvidenceSubmissionResponse(
                            case_id=submission.case_id,
                            submission_id=f"SUB-ERR-{uuid.uuid4().hex[:6]}",
                            is_accepted=False,
                            re_evaluation_triggered=False,
                            new_evidence_sufficient=False,
                            new_stp_eligible=False,
                            new_status="VALIDATION_FAILED",
                            message=f"Field {f.label} does not match required format pattern."
                        )

        # 2. Ingest evidence items via Acquisition Gateway (Mode 4)
        new_items = self._gateway.receive_hitl_submission_mode4(submission)

        # 3. Check remaining missing evidence
        remaining_missing = []
        for req_type in resolved.active_mandatory_types:
            if not self._store.has_evidence(submission.case_id, req_type):
                remaining_missing.append(req_type)

        evidence_sufficient = (len(remaining_missing) == 0)

        # 4. Trigger Re-Evaluation if callback is provided
        new_stp_eligible = False
        new_status = "EVIDENCE_SUPPLIED"
        if re_eval_callback:
            re_eval_res = re_eval_callback(submission.case_id)
            if isinstance(re_eval_res, dict):
                new_stp_eligible = re_eval_res.get("stp_eligible", False)
                new_status = re_eval_res.get("status", "RESOLVED" if evidence_sufficient else "AWAITING_EVIDENCE")
        else:
            new_status = "RESOLVED" if evidence_sufficient else "AWAITING_ADDITIONAL_EVIDENCE"

        return HitlEvidenceSubmissionResponse(
            case_id=submission.case_id,
            submission_id=f"SUB-{uuid.uuid4().hex[:8].upper()}",
            is_accepted=True,
            re_evaluation_triggered=True,
            new_evidence_sufficient=evidence_sufficient,
            new_stp_eligible=new_stp_eligible,
            new_status=new_status,
            missing_evidence_remaining=remaining_missing,
            message=f"Operator evidence successfully recorded. Sufficiency={evidence_sufficient}."
        )
