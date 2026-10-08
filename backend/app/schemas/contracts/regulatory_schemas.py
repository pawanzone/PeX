"""Regulatory Screening & Sanctions Contract Schemas.

Defines the contract for screening entities against statutory sanctions lists, PEP databases,
and adverse media registers. Evaluation only; unfreezing funds requires sovereign bank compliance action.
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ScreeningDisposition(str, Enum):
    CLEAR = "CLEAR"
    POTENTIAL_HIT = "POTENTIAL_HIT"
    CONFIRMED_HIT = "CONFIRMED_HIT"
    ERROR_UNAVAILABLE = "ERROR_UNAVAILABLE"


class ScreeningAssessment(BaseModel):
    """Result of screening an entity or transaction corridor against regulatory registries."""
    screening_id: str
    target_entity_masked: str
    disposition: ScreeningDisposition
    compliance_gate_passed: bool                     # C_comp predicate
    match_score: float = 0.0                         # 0.0 to 1.0 (fuzzy match)
    matched_lists: List[str] = Field(default_factory=list) # e.g., ["OFAC_SDN", "EU_FSF", "UN_CONSOLIDATED"]
    hit_details: Optional[Dict[str, Any]] = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    statutory_authority_source: str = "STATUTORY_WATCHLIST_PROVIDER"
    requires_mandatory_legal_hold: bool = False
