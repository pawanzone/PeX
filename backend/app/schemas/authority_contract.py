"""Authority / Validation Contract Schemas for PeX Evidence-Driven STP Architecture.

Defines HOW candidate repairs are validated against authoritative Systems of Record (SoR)
or external standards registries, strictly distinguishing structural validity from business correctness.
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class AuthorityValidationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


class AuthorityValidationResult(BaseModel):
    """Result of corroborating a candidate repair against an authoritative source."""
    profile_id: str
    status: AuthorityValidationStatus
    is_valid: bool
    authoritative_source: str                 # e.g., "ISO20022_W3C_SCHEMA_VALIDATOR", "BANK_SSI_MASTER", "SWIFTREF"
    attestation_token: Optional[str] = None   # Cryptographic digest or validation receipt
    validated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)
    audit_trail: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

    # Explicit distinction: schema structural validity != business correctness
    is_structural_syntax_valid: bool = True
    is_business_authority_confirmed: bool = False
