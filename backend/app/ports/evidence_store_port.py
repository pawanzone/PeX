"""Evidence Store Port (SPI).

Defines the abstract interface for storing, retrieving, deduplicating, and computing
provenance hashes for case evidence dossiers.
Reference: PeX_Evidence_Acquisition_and_Resolution_Contract_v0.3.1.md Section 3.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from app.schemas.contracts.evidence_schemas import EvidenceItem, EvidencePackageEnvelope


class EvidenceStorePort(ABC):
    """Abstract port for case evidence storage and dossier management."""

    @abstractmethod
    def store_evidence_item(self, case_id: str, item: EvidenceItem) -> bool:
        """Stores or updates a validated evidence item for a case with SHA-256 deduplication."""
        pass

    @abstractmethod
    def get_evidence_dossier(self, case_id: str) -> List[EvidenceItem]:
        """Retrieves all evidence items currently associated with the case."""
        pass

    @abstractmethod
    def get_evidence_by_type(self, case_id: str, evidence_type: str) -> Optional[EvidenceItem]:
        """Retrieves the most recent authoritative evidence item of a specific type."""
        pass

    @abstractmethod
    def has_evidence(self, case_id: str, evidence_type: str) -> bool:
        """Checks whether a valid, non-stale evidence item of the specified type exists."""
        pass

    @abstractmethod
    def compute_dossier_hash(self, case_id: str) -> str:
        """Computes the deterministic SHA-256 Merkle-like hash of all evidence items in the dossier."""
        pass
