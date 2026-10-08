"""Evidence Store and Deduplication Engine.

Provides content-addressable storage, deduplication, trust tier reconciliation,
and Merkle-like SHA-256 dossier hashing.
Reference: PeX_Evidence_Acquisition_and_Resolution_Contract_v0.3.1.md Section 3.
"""
import hashlib
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.ports.evidence_store_port import EvidenceStorePort
from app.schemas.contracts.evidence_schemas import (
    EvidenceItem,
    TrustTier,
    EvidenceValidationStatus,
)


class EvidenceStoreService(EvidenceStorePort):
    """In-memory reference implementation of EvidenceStorePort with deduplication and contradiction analysis."""

    def __init__(self):
        # case_id -> list of EvidenceItem
        self._dossiers: Dict[str, List[EvidenceItem]] = {}

    def store_evidence_item(self, case_id: str, item: EvidenceItem) -> bool:
        """Stores an evidence item with deduplication and contradiction checking."""
        if case_id not in self._dossiers:
            self._dossiers[case_id] = []

        existing_items = self._dossiers[case_id]

        # 1. Deduplication check by provenance hash
        for idx, existing in enumerate(existing_items):
            if existing.provenance_hash == item.provenance_hash and existing.evidence_type == item.evidence_type:
                # Identical payload: update acquisition timestamp without creating duplicate entry
                existing.acquired_at = item.acquired_at
                existing.validation_status = EvidenceValidationStatus.AVAILABLE
                return True

        # 2. Contradiction & Supersession check
        # If an item of the same evidence_type exists, check trust tiers
        for existing in existing_items:
            if existing.evidence_type == item.evidence_type:
                if int(item.trust_tier.value) < int(existing.trust_tier.value):
                    # Higher trust tier (lower numeric value) supersedes lower trust tier
                    existing.validation_status = EvidenceValidationStatus.STALE
                    existing.contradiction_details = f"Superseded by higher trust tier ({item.trust_tier.name})"
                elif int(item.trust_tier.value) == int(existing.trust_tier.value):
                    # Same trust tier but different payload => Contradiction!
                    if existing.raw_payload_masked != item.raw_payload_masked:
                        existing.is_contradictory = True
                        existing.validation_status = EvidenceValidationStatus.CONTRADICTORY
                        item.is_contradictory = True
                        item.validation_status = EvidenceValidationStatus.CONTRADICTORY
                        item.contradiction_details = f"Contradicts existing evidence {existing.evidence_id} of same tier"

        existing_items.append(item)
        return True

    def get_evidence_dossier(self, case_id: str) -> List[EvidenceItem]:
        """Retrieves all evidence items for a case, checking TTL freshness."""
        now = datetime.now(timezone.utc)
        items = self._dossiers.get(case_id, [])

        for item in items:
            if item.expires_at and item.expires_at < now and item.validation_status == EvidenceValidationStatus.AVAILABLE:
                item.validation_status = EvidenceValidationStatus.STALE

        return items

    def get_evidence_by_type(self, case_id: str, evidence_type: str) -> Optional[EvidenceItem]:
        """Retrieves the highest-trust, active evidence item of the given type."""
        items = self.get_evidence_dossier(case_id)
        candidates = [
            i for i in items
            if i.evidence_type == evidence_type and i.validation_status == EvidenceValidationStatus.AVAILABLE
        ]
        if not candidates:
            return None
        # Sort by trust tier ascending (Tier 1 is best)
        candidates.sort(key=lambda x: int(x.trust_tier.value))
        return candidates[0]

    def has_evidence(self, case_id: str, evidence_type: str) -> bool:
        """Returns True if a non-stale, non-contradictory evidence item exists."""
        item = self.get_evidence_by_type(case_id, evidence_type)
        return item is not None and not item.is_contradictory

    def compute_dossier_hash(self, case_id: str) -> str:
        """Computes deterministic SHA-256 Merkle-like hash of all active evidence items."""
        items = self.get_evidence_dossier(case_id)
        if not items:
            return hashlib.sha256(f"EMPTY_DOSSIER_{case_id}".encode("utf-8")).hexdigest()

        # Sort items by evidence_type and provenance_hash for deterministic ordering
        sorted_hashes = sorted([f"{i.evidence_type}:{i.provenance_hash}:{i.trust_tier.value}" for i in items])
        combined_payload = "|".join(sorted_hashes)
        return hashlib.sha256(combined_payload.encode("utf-8")).hexdigest()

    def clear(self, case_id: Optional[str] = None) -> None:
        """Clears stored dossiers (useful for testing)."""
        if case_id:
            self._dossiers.pop(case_id, None)
        else:
            self._dossiers.clear()
