"""In-Memory Reference Bank Handoff Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements BankHandoffEnvelopePort.
Enforces universal postcondition: BANK_HANDOFF_READY with execution_owner = "BANK".
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from app.ports.bank_handoff_port import BankHandoffEnvelopePort
from app.schemas.contracts.bank_handoff_schemas import (
    BankHandoffEnvelope,
    ApprovalSignature,
    DispatchIntent,
    ExecutionOwner,
    HandoffStatus,
)


class InMemoryBankHandoffAdapter(BankHandoffEnvelopePort):
    """Hermetic reference implementation of BankHandoffEnvelopePort."""

    def __init__(self):
        self._envelopes: Dict[str, BankHandoffEnvelope] = {}

    def create_handoff_envelope(
        self,
        case_id: str,
        payment_id: str,
        uetr: str,
        dispatch_intent: DispatchIntent,
        stp_eligible: bool,
        stp_formula_evaluation: Dict[str, Any],
        signatures: List[ApprovalSignature],
        audit_block_hash: str,
        is_autonomous_zero_touch: bool = False
    ) -> BankHandoffEnvelope:
        envelope_id = f"ENV-PEX-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        status = HandoffStatus.BANK_HANDOFF_READY if stp_eligible or len(signatures) > 0 else HandoffStatus.MAKER_CHECKER_PENDING

        envelope = BankHandoffEnvelope(
            envelope_id=envelope_id,
            case_id=case_id,
            payment_id=payment_id,
            uetr=uetr,
            execution_owner=ExecutionOwner.BANK, # Strict invariant: execution_owner = "BANK"
            status=status,
            dispatch_intent=dispatch_intent,
            stp_eligible=stp_eligible,
            stp_formula_evaluation=stp_formula_evaluation,
            signatures=signatures,
            audit_chain_block_hash=audit_block_hash,
            created_at=now,
            is_autonomous_zero_touch=is_autonomous_zero_touch
        )
        self._envelopes[envelope_id] = envelope
        return envelope

    def validate_handoff_envelope(
        self,
        envelope: BankHandoffEnvelope
    ) -> bool:
        # 1. Verify execution owner is BANK
        if envelope.execution_owner != ExecutionOwner.BANK:
            return False

        # 2. If dual-auth was required, verify distinct identities (maker != checker)
        if len(envelope.signatures) >= 2:
            approver_ids = [s.approver_id for s in envelope.signatures]
            if len(approver_ids) != len(set(approver_ids)):
                return False # Maker == Checker violation

        # 3. Check audit block hash present
        if not envelope.audit_chain_block_hash:
            return False

        return True
