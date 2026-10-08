"""Audit Ledger & Cryptographic Provenance Schemas.

Defines the contract for tamper-evident SHA-256 Merkle-like hash chained audit events.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class AuditBlockPayload(BaseModel):
    """Raw event payload to be cryptographically committed to the audit chain."""
    event_id: str
    case_id: str
    correlation_id: str
    stage_name: str                                  # e.g., "INGESTION", "EVALUATION", "APPROVAL", "HANDOFF"
    actor_id: str
    actor_role: str
    action_name: str
    details: str
    control_tags: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditBlockReceipt(BaseModel):
    """Immutable audit block receipt with parent hash and cryptographic signature."""
    block_index: int
    block_hash: str                                  # SHA-256(index + timestamp + payload + parent_hash)
    parent_hash: str                                 # Cryptographic link to previous block
    payload: AuditBlockPayload
    committed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_valid_chain: bool = True
