"""Cryptographic Provenance & Continuous Audit Schemas."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class AuditEvent(BaseModel):
    event_index: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    case_id: str
    correlation_id: str
    stage_name: str  # e.g. INTAKE, CANONICALIZATION, TOKENIZATION, EVIDENCE_GATHERING, AI_REASONING, HITL_APPROVAL, ACTION_DISPATCH, SETTLEMENT
    actor_id: str
    actor_role: str
    action_name: str
    details: str
    control_tags: List[str] = []
    prev_hash: str
    current_hash: str

class ProvenanceChain(BaseModel):
    case_id: str
    chain_head_hash: str
    total_events: int
    is_valid: bool = True
    events: List[AuditEvent]

class HashVerificationResult(BaseModel):
    chain_head: str
    total_events_checked: int
    is_intact: bool
    verified_at: datetime = Field(default_factory=datetime.utcnow)
