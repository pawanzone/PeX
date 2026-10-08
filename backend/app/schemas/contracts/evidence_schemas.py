"""Evidence Package Contract Schemas.

Defines the multi-source evidence package model with explicit trust tiers, provenance,
validation status, and contradiction tracking.
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class TrustTier(int, Enum):
    """Evidence Trust Tiers (Tier 1 = highest sovereign trust, Tier 4 = advisory context)."""
    TIER_1_CORE_RECORD = 1       # Authoritative core banking DDA, payment gateway logs, SWIFT/RTGS receipts
    TIER_2_REGULATORY_SCHEME = 2 # National directory (SWIFTRef, FedLine, Sort Codes, Watchlists)
    TIER_3_CLIENT_ERP = 3        # Client Master, ERP invoice, EDI remittance payload
    TIER_4_HISTORICAL_AI = 4     # Historical repair precedent, AI statistical similarity (0% authority)


class EvidenceValidationStatus(str, Enum):
    """Validation status for an evidence item."""
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    STALE = "STALE"
    INVALID = "INVALID"
    CONTRADICTORY = "CONTRADICTORY"
    UNAVAILABLE = "UNAVAILABLE"


class EvidenceItem(BaseModel):
    """Individual evidence item attached to an exception dossier."""
    evidence_id: str
    evidence_type: str                   # e.g., "CORE_DDA_ACCOUNT", "ROUTING_DIRECTORY", "SANCTIONS_WATCHLIST"
    source_system: str                   # e.g., "CORE_DDA", "FEDLINE_DIRECTORY", "OFAC_SDN_FEED"
    trust_tier: TrustTier
    validation_status: EvidenceValidationStatus
    acquired_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    provenance_hash: str                 # SHA-256 hash of raw payload
    raw_payload_masked: Dict[str, Any] = Field(default_factory=dict)
    is_authoritative: bool = False
    is_contradictory: bool = False
    contradiction_details: Optional[str] = None


class EvidencePackageEnvelope(BaseModel):
    """Sealed evidence package dossier for an exception case."""
    package_id: str
    case_id: str
    profile_id: str
    assembled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    items: List[EvidenceItem] = Field(default_factory=list)
    evidence_sufficient: bool = False    # E_suff
    sufficiency_score: float = 0.0
    missing_mandatory_types: List[str] = Field(default_factory=list)
    stale_types: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    provenance: str = "PEX_CANONICAL_DOSSIER"
    is_synthetic_test_fixture: bool = False
