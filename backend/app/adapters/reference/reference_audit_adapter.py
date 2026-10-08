"""In-Memory Reference Audit Ledger Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements AuditLedgerPort with cryptographic SHA-256 Merkle-like hash chaining.
Detects tampering immediately.
"""
import hashlib
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone

from app.ports.audit_port import AuditLedgerPort
from app.schemas.contracts.audit_schemas import (
    AuditBlockPayload,
    AuditBlockReceipt,
)


class InMemoryAuditLedgerAdapter(AuditLedgerPort):
    """Hermetic reference implementation of AuditLedgerPort with tamper-evident chain."""

    def __init__(self, genesis_seed: str = "PEX_GENESIS_SEED_20261008"):
        self._genesis_hash = hashlib.sha256(genesis_seed.encode()).hexdigest()
        self._chain: List[AuditBlockReceipt] = []

    def append_event(
        self,
        payload: AuditBlockPayload
    ) -> AuditBlockReceipt:
        now = datetime.now(timezone.utc)
        parent_hash = self._chain[-1].block_hash if self._chain else self._genesis_hash
        block_idx = len(self._chain) + 1

        payload_str = json.dumps(payload.model_dump(), sort_keys=True, default=str)
        raw_block = f"{block_idx}:{parent_hash}:{payload_str}"
        block_hash = hashlib.sha256(raw_block.encode()).hexdigest()

        receipt = AuditBlockReceipt(
            block_index=block_idx,
            block_hash=block_hash,
            parent_hash=parent_hash,
            payload=payload,
            committed_at=now,
            is_valid_chain=True
        )
        self._chain.append(receipt)
        return receipt

    def verify_integrity(self, case_id: Optional[str] = None) -> bool:
        if not self._chain:
            return True

        expected_parent = self._genesis_hash
        for b in self._chain:
            if b.parent_hash != expected_parent:
                return False

            payload_str = json.dumps(b.payload.model_dump(), sort_keys=True, default=str)
            raw_block = f"{b.block_index}:{b.parent_hash}:{payload_str}"
            recomputed = hashlib.sha256(raw_block.encode()).hexdigest()

            if b.block_hash != recomputed:
                return False
            expected_parent = b.block_hash

        return True

    def get_events_for_case(self, case_id: str) -> List[AuditBlockReceipt]:
        return [b for b in self._chain if b.payload.case_id == case_id]
