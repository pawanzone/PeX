"""Canonical Transport-Neutral Intake and Outbound Envelopes for PeX.

Defines `pex.intake.v1` and `pex.outbound.v1` canonical envelope models, providing transport neutrality
across folder drops, REST APIs, message queues (Kafka, IBM MQ), and bank integration gateways.
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HandoffLifecycleState(str, Enum):
    """Lifecycle states within the PeX-Bank Handoff Boundary."""
    STP_ELIGIBLE = "STP_ELIGIBLE"
    BANK_HANDOFF_READY = "BANK_HANDOFF_READY"
    BANK_EXECUTION_ACCEPTED = "BANK_EXECUTION_ACCEPTED"     # Simulation/Demo ACK only
    HITL_WORKLIST = "HITL_WORKLIST"
    OPERATIONS_SUSPENSE = "OPERATIONS_SUSPENSE"
    COMPLIANCE_SUSPENSE = "COMPLIANCE_SUSPENSE"
    REJECTED = "REJECTED"


class CanonicalIntakeEnvelope(BaseModel):
    """Canonical Inbound Payment Exception Envelope (pex.intake.v1).
    
    Transport-neutral envelope containing payment identity, exception classification,
    raw payload bytes/string, and associated bank evidence items.
    """
    envelope_version: str = "pex.intake.v1"
    message_id: str
    source_system: str                                      # e.g., "BANK_PAYMENT_HUB", "SWIFT_GATEWAY", "FEDWIRE_HUB"
    rail: str = "ISO20022"                                  # e.g., "SWIFT_CBPR+", "FEDWIRE", "CHAPS", "SEPA", "ACH"
    channel: str = "FILE_DROP"                              # e.g., "FILE_DROP", "REST_API", "MQ_FEED", "SFTP"
    payment_reference: str
    correlation_id: str
    uetr: Optional[str] = None
    amount: float
    currency: str = "USD"
    debtor_name: Optional[str] = None
    creditor_name: Optional[str] = None
    debtor_account: Optional[str] = None
    creditor_account: Optional[str] = None
    exception_profile: str = "PR-05"                        # Default for Phase 2A Slice 1: CORRUPTED_MESSAGE_FORMAT
    reason_code: Optional[str] = None                       # e.g., "CHAR_ENCODING_ERROR", "UNPARSEABLE_CONTROL_BYTES"
    failed_field: Optional[str] = None                      # e.g., "RmtInf/Ustrd", "Dbtr/Nm"
    message_path: Optional[str] = None
    received_value: Optional[str] = None
    hub_status: str = "SUSPENDED_FOR_REPAIR"
    narrative: Optional[str] = None
    raw_payload: str                                        # Raw XML/JSON or byte-string payload
    evidence_items: Dict[str, Any] = Field(default_factory=dict)
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CanonicalOutboundEnvelope(BaseModel):
    """Canonical Outbound Bank Payment Hub Handoff Envelope (pex.outbound.v1).
    
    Represents PeX -> Bank Payment Hub handoff. Explicitly designates BANK as the execution
    owner. Does NOT move funds, execute RTGS, or post DDA debits/credits.
    """
    envelope_version: str = "pex.outbound.v1"
    handoff_id: str
    case_id: str
    profile_id: str = "PR-05"
    
    # 1. Original Payment Identity
    original_payment_identity: Dict[str, Any] = Field(default_factory=dict)
    
    # 2. Proposed Repair Payload & Summary
    proposed_repair: Dict[str, Any] = Field(default_factory=dict)
    
    # 3. Evidence References & Provenance
    evidence_references: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 4. Resolution Contract Evaluation
    resolution_summary: Dict[str, Any] = Field(default_factory=dict)
    
    # 5. Authority / Validation Contract Evaluation
    validation_summary: Dict[str, Any] = Field(default_factory=dict)
    
    # 6. Canonical 8-Predicate STP Boolean Evaluation
    stp_predicates: Dict[str, bool] = Field(default_factory=dict)
    
    # 7. Governance Decision & Routing
    governance_decision: str                                # "BANK_HANDOFF_READY", "HITL_APPROVED_HANDOFF", "HITL_ROUTING"
    execution_owner: str = "BANK"                           # Non-negotiable: BANK owns execution
    lifecycle_state: HandoffLifecycleState = HandoffLifecycleState.BANK_HANDOFF_READY
    
    # 8. Cryptographic Provenance & Audit Digest
    audit_references: Dict[str, Any] = Field(default_factory=dict)
    
    # 9. Timestamps
    handoff_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # 10. Simulated Bank ACK (Testing/Demo Only)
    simulated_bank_execution_receipt: Optional[Dict[str, Any]] = None
