"""Resolution Contract & Candidate Schemas for PeX Evidence-Driven STP Architecture.

Defines HOW candidate repairs are deterministically derived, enforcing lossless business payload
preservation and candidate uniqueness constraints.
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ResolutionStatus(str, Enum):
    RESOLUTION_DETERMINED = "RESOLUTION_DETERMINED"
    RESOLUTION_NOT_DETERMINED = "RESOLUTION_NOT_DETERMINED"


class ResolutionUniqueness(str, Enum):
    RESOLUTION_UNIQUE = "RESOLUTION_UNIQUE"
    RESOLUTION_AMBIGUOUS = "RESOLUTION_AMBIGUOUS"


class ResolutionCandidate(BaseModel):
    """A single deterministically derived candidate repair."""
    candidate_id: str
    repaired_payload: str                     # Serialized XML / JSON string
    repaired_structured: Optional[Dict[str, Any]] = None
    diff_summary: str                         # Human/machine readable summary of structural changes
    derivation_method: str                    # e.g., "DETERMINISTIC_ISO20022_XSD_RESEQUENCER"
    is_lossless: bool = True                  # Must be True; business payload values cannot be altered
    fields_reordered: List[str] = Field(default_factory=list)
    namespaces_normalized: List[str] = Field(default_factory=list)
    default_envelope_applied: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResolutionResult(BaseModel):
    """Result of evaluating the Resolution Contract against an Evidence Dossier."""
    profile_id: str
    status: ResolutionStatus
    uniqueness: ResolutionUniqueness
    candidates: List[ResolutionCandidate] = Field(default_factory=list)
    primary_candidate: Optional[ResolutionCandidate] = None
    is_lossless: bool = True
    audit_trail: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def is_deterministic_and_unique(self) -> bool:
        return (
            self.status == ResolutionStatus.RESOLUTION_DETERMINED and
            self.uniqueness == ResolutionUniqueness.RESOLUTION_UNIQUE and
            self.primary_candidate is not None and
            self.primary_candidate.is_lossless
        )
