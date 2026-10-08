"""Evidence Package Port (SPI).

Defines the abstract interface for assembling, verifying freshness, and checking
sufficiency of multi-source evidence dossiers.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from app.schemas.contracts.evidence_schemas import EvidencePackageEnvelope, EvidenceItem


class EvidencePackagePort(ABC):
    """Abstract port for evidence acquisition, validation, and sufficiency evaluation."""

    @abstractmethod
    def acquire_evidence(
        self,
        case_id: str,
        profile_id: str,
        raw_telemetry: Dict[str, Any],
        external_context: Optional[Dict[str, Any]] = None
    ) -> EvidencePackageEnvelope:
        """Assembles and validates evidence items for a given exception case."""
        pass

    @abstractmethod
    def evaluate_sufficiency(
        self,
        envelope: EvidencePackageEnvelope,
        mandatory_types: List[str]
    ) -> EvidencePackageEnvelope:
        """Evaluates whether all mandatory evidence is present, fresh, and non-contradictory (E_suff)."""
        pass
