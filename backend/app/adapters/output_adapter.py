"""Output Adapter for PeX Evidence-Driven STP Architecture.

Implements the OutputPort interface to write repaired payment instructions and handoff receipts
to the Bank Payment Hub output queue or folder.

NOTE: This is a BANK-CONTROLLED INTEGRATION BOUNDARY, not a direct settlement mechanism.
PeX hands repaired instructions back to the Bank Payment Hub; the Bank retains full execution control.
"""
import os
import json
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.schemas.resolution_contract import ResolutionCandidate
from app.schemas.policy_contract import STPEligibilityDecision


from app.schemas.canonical_envelopes import (
    CanonicalOutboundEnvelope,
    HandoffLifecycleState,
)


class BankHandoffReceipt(BaseModel):
    """Immutable receipt certifying handoff of a repaired payment instruction to the Bank Payment Hub."""
    receipt_id: str
    case_id: str
    profile_id: str
    output_destination: str                   # e.g., "BANK_OUTPUT_FOLDER", "PAYMENT_HUB_MQ_QUEUE"
    sha256_payload_hash: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_stp_dispatched: bool
    status: str = "DELIVERED_TO_BANK_HUB"
    repaired_payload_length: int
    diff_summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OutputPort:
    """Abstract port for handing repaired payment instructions to the Bank Payment Hub."""

    def emit_repaired_instruction(
        self,
        candidate: ResolutionCandidate,
        decision: STPEligibilityDecision,
        filename_prefix: Optional[str] = None
    ) -> BankHandoffReceipt:
        raise NotImplementedError


class FolderOutputAdapter(OutputPort):
    """File/Folder-based output adapter writing repaired instructions to a bank staging folder."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir
        self._emitted_receipts: Dict[str, BankHandoffReceipt] = {}
        self._outbound_envelopes: Dict[str, CanonicalOutboundEnvelope] = {}

    def emit_repaired_instruction(
        self,
        candidate: ResolutionCandidate,
        decision: STPEligibilityDecision,
        filename_prefix: Optional[str] = None,
        original_payment_info: Optional[Dict[str, Any]] = None,
        evidence_references: Optional[List[Dict[str, Any]]] = None
    ) -> BankHandoffReceipt:
        """Emits the repaired instruction and associated handoff receipt to the bank staging folder or memory."""
        repaired_text = candidate.repaired_payload
        payload_hash = hashlib.sha256(repaired_text.encode("utf-8")).hexdigest()
        receipt_id = f"RCPT-{decision.profile_id}-{payload_hash[:10]}"

        # Prevent duplicate emissions
        if receipt_id in self._emitted_receipts:
            receipt = self._emitted_receipts[receipt_id]
            receipt.metadata["is_duplicate_emission_prevented"] = True
            return receipt

        prefix = filename_prefix or f"PEX_REPAIRED_{decision.profile_id}_{decision.case_id}"

        # Construct Canonical Outbound Envelope (pex.outbound.v1)
        outbound_env = CanonicalOutboundEnvelope(
            handoff_id=receipt_id,
            case_id=decision.case_id,
            profile_id=decision.profile_id,
            original_payment_identity=original_payment_info or {"case_id": decision.case_id},
            proposed_repair={
                "repaired_payload": repaired_text,
                "diff_summary": candidate.diff_summary,
                "is_lossless": candidate.is_lossless,
                "derivation_method": candidate.derivation_method
            },
            evidence_references=evidence_references or [],
            resolution_summary={
                "candidate_id": candidate.candidate_id,
                "derivation_method": candidate.derivation_method,
                "is_lossless": candidate.is_lossless
            },
            validation_summary={
                "v_det": decision.deterministic_validation_passed,
                "v_auth": decision.authority_validation_passed
            },
            stp_predicates={
                "e_suff": decision.evidence_sufficient,
                "r_det": decision.resolution_determined,
                "r_uniq": decision.resolution_unique,
                "v_det": decision.deterministic_validation_passed,
                "v_auth": decision.authority_validation_passed,
                "p_bank": decision.bank_policy_allows,
                "c_comp": decision.compliance_gate_passed,
                "x_pre": decision.execution_preconditions_satisfied,
                "stp_eligible": decision.stp_eligible
            },
            governance_decision="BANK_HANDOFF_READY" if decision.stp_eligible else "HITL_ROUTING",
            execution_owner="BANK",
            lifecycle_state=HandoffLifecycleState.BANK_HANDOFF_READY if decision.stp_eligible else HandoffLifecycleState.HITL_WORKLIST,
            audit_references={
                "sha256_payload_hash": payload_hash,
                "receipt_id": receipt_id
            },
            handoff_timestamp=datetime.now(timezone.utc)
        )
        self._outbound_envelopes[receipt_id] = outbound_env

        # If an output directory is configured, write the file to disk
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            extension = "xml" if (repaired_text.strip().startswith("<") or "<Document" in repaired_text) else "txt"
            payload_path = os.path.join(self.output_dir, f"{prefix}_repaired.{extension}")
            receipt_path = os.path.join(self.output_dir, f"{prefix}_receipt.json")
            envelope_path = os.path.join(self.output_dir, f"{prefix}_outbound_envelope.json")

            with open(payload_path, "w", encoding="utf-8") as f:
                f.write(repaired_text)

            receipt_data = {
                "receipt_id": receipt_id,
                "case_id": decision.case_id,
                "profile_id": decision.profile_id,
                "sha256_payload_hash": payload_hash,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stp_eligible": decision.stp_eligible,
                "recommended_routing": decision.recommended_routing,
                "diff_summary": candidate.diff_summary,
                "status": "DELIVERED_TO_BANK_HUB",
                "execution_owner": "BANK"
            }
            with open(receipt_path, "w", encoding="utf-8") as f:
                json.dump(receipt_data, f, indent=2)

            with open(envelope_path, "w", encoding="utf-8") as f:
                f.write(outbound_env.model_dump_json(indent=2))

        receipt = BankHandoffReceipt(
            receipt_id=receipt_id,
            case_id=decision.case_id,
            profile_id=decision.profile_id,
            output_destination=self.output_dir or "IN_MEMORY_BANK_QUEUE",
            sha256_payload_hash=payload_hash,
            timestamp=datetime.now(timezone.utc),
            is_stp_dispatched=decision.stp_eligible,
            status="DELIVERED_TO_BANK_HUB",
            repaired_payload_length=len(repaired_text),
            diff_summary=candidate.diff_summary,
            metadata={
                "derivation_method": candidate.derivation_method,
                "is_lossless": candidate.is_lossless,
                "routing": decision.recommended_routing,
                "execution_owner": "BANK",
                "envelope_version": "pex.outbound.v1"
            }
        )

        self._emitted_receipts[receipt_id] = receipt
        return receipt

    def get_outbound_envelope(self, receipt_id: str) -> Optional[CanonicalOutboundEnvelope]:
        """Retrieves the CanonicalOutboundEnvelope for a given receipt ID."""
        return self._outbound_envelopes.get(receipt_id)

    def simulate_bank_execution_ack(self, receipt: BankHandoffReceipt) -> Dict[str, Any]:
        """Simulates Bank Payment Hub ingestion and dispatch acceptance.
        
        CRITICAL ARCHITECTURAL BOUNDARY:
        This simulation certifies handoff acceptance only. PeX NEVER moves funds or claims real settlement.
        """
        ack = {
            "ack_id": f"BANK-ACK-{receipt.receipt_id[-8:]}",
            "receipt_id": receipt.receipt_id,
            "case_id": receipt.case_id,
            "status": "BANK_EXECUTION_ACCEPTED",
            "execution_mode": "SIMULATED / DEMO",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "bank_clearing_dispatch_status": "QUEUED_FOR_BANK_DDA_POSTING",
            "disclaimer": "DEMO_ONLY: Simulated Bank Execution Acceptance. Real bank settlement confirmation required for live clearing."
        }
        if receipt.receipt_id in self._outbound_envelopes:
            self._outbound_envelopes[receipt.receipt_id].simulated_bank_execution_receipt = ack
            self._outbound_envelopes[receipt.receipt_id].lifecycle_state = HandoffLifecycleState.BANK_EXECUTION_ACCEPTED
        return ack

