"""Bank Handoff Envelope & Execution Boundary Schemas.

Defines the contract for the terminal handoff envelope produced by PeX.
Universal Postcondition: BANK_HANDOFF_READY with execution_owner = "BANK".
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ExecutionOwner(str, Enum):
    BANK = "BANK"                                    # PeX NEVER executes ledgers or wires; owner is always BANK


class HandoffStatus(str, Enum):
    BANK_HANDOFF_READY = "BANK_HANDOFF_READY"
    MAKER_CHECKER_PENDING = "MAKER_CHECKER_PENDING"
    INVESTIGATION_SUSPENDED = "INVESTIGATION_SUSPENDED"
    REJECTED_BY_POLICY = "REJECTED_BY_POLICY"
    HANDOFF_FAILED = "HANDOFF_FAILED"


class ApprovalSignature(BaseModel):
    """Cryptographic/Audit approval signature attached to a handoff envelope."""
    approval_id: str
    approver_id: str
    approver_name: str
    approver_role: str
    action: str                                      # e.g., "APPROVE", "DUAL_AUTHORIZE", "AUTONOMOUS_POLICY_APPROVE"
    signed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    comments: Optional[str] = None


class DispatchIntent(BaseModel):
    """Sealed instruction describing the exact repair or return action the bank should execute."""
    intent_id: str
    action_type: str                                 # "REPAIR_AND_RELEASE", "RETURN_PAYMENT", "QUEUE_RESCHEDULE", "SPLIT_PAYMENT"
    target_clearing_rail: str                        # "FEDWIRE", "CHAPS", "TARGET2", "SWIFT_CBPR+", "BACS"
    repaired_fields: List[Dict[str, Any]] = Field(default_factory=list)
    outbound_message_format: str = "ISO20022_PACS008"
    estimated_fee_impact: float = 0.0
    settlement_priority: str = "NORMAL"


class BankHandoffEnvelope(BaseModel):
    """Terminal sealed handoff package delivered to bank payment gateway."""
    envelope_id: str
    case_id: str
    payment_id: str
    uetr: str
    execution_owner: ExecutionOwner = ExecutionOwner.BANK
    status: HandoffStatus = HandoffStatus.BANK_HANDOFF_READY
    dispatch_intent: DispatchIntent
    stp_eligible: bool
    stp_formula_evaluation: Dict[str, Any] = Field(default_factory=dict) # E_suff ... X_pre
    signatures: List[ApprovalSignature] = Field(default_factory=list)
    audit_chain_block_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_autonomous_zero_touch: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
