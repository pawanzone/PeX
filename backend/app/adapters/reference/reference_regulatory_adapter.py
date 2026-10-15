"""In-Memory Reference Regulatory Screening Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements RegulatoryScreeningPort with simulated watchlist matching.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from app.ports.regulatory_port import RegulatoryScreeningPort
from app.schemas.contracts.regulatory_schemas import (
    ScreeningAssessment,
    ScreeningDisposition,
)


class InMemoryRegulatoryScreeningAdapter(RegulatoryScreeningPort):
    """Hermetic reference implementation of RegulatoryScreeningPort."""

    def __init__(self):
        self._sanctioned_keywords = ["SANCTIONED", "OFAC_HIT", "BLOCKED_ENTITY", "TERRORIST", "WEAPONS_LTD"]
        self._restricted_corridors = ["NK", "IR", "SY", "CU", "RU_RESTRICTED_CORRIDOR"]

    def screen_entity(
        self,
        entity_name: str,
        country: Optional[str] = None,
        corridor: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ScreeningAssessment:
        now = datetime.now(timezone.utc)
        name_upper = entity_name.upper()
        country_upper = (country or "").upper()
        corridor_upper = (corridor or "").upper()

        ctx = context or {}
        has_license_exemption = ctx.get("ofac_license_exemption_verified", False)

        # 1. Check direct keyword match
        is_sanctioned_name = any(kw in name_upper for kw in self._sanctioned_keywords) or bool(ctx.get("ofac_sanctions_hit") or ctx.get("ofac_sdn_hit"))
        
        # Exact code match on country or tokenized corridor
        country_tokens = set(country_upper.replace("-", " ").replace("_", " ").split())
        corridor_tokens = set(corridor_upper.replace("-", " ").replace("_", " ").split())
        is_restricted_country = bool((country_tokens | corridor_tokens) & set(self._restricted_corridors)) or (country_upper in self._restricted_corridors) or bool(ctx.get("corridor_prohibited"))

        if (is_sanctioned_name or is_restricted_country) and not has_license_exemption:
            return ScreeningAssessment(
                screening_id=f"SCR-HIT-{uuid.uuid4().hex[:6].upper()}",
                target_entity_masked=f"{entity_name[:3]}****[FLAGGED]",
                disposition=ScreeningDisposition.CONFIRMED_HIT,
                compliance_gate_passed=False,         # C_comp = False
                match_score=0.99,
                matched_lists=["OFAC_SDN_LIST_2026", "EU_CONSOLIDATED_FINANCIAL_SANCTIONS"],
                hit_details={
                    "entity_match": is_sanctioned_name,
                    "corridor_match": is_restricted_country,
                    "matched_string": name_upper if is_sanctioned_name else corridor_upper
                },
                evaluated_at=now,
                requires_mandatory_legal_hold=True
            )

        if has_license_exemption:
            return ScreeningAssessment(
                screening_id=f"SCR-EXEMPT-{uuid.uuid4().hex[:6].upper()}",
                target_entity_masked=f"{entity_name[:3]}****{entity_name[-2:]}" if len(entity_name) > 5 else "ENT****MASK",
                disposition=ScreeningDisposition.CLEAR,
                compliance_gate_passed=True,          # C_comp = True under verified license exemption
                match_score=0.10,
                matched_lists=[],
                hit_details={"license_exemption": "OFAC_GL_58A_VERIFIED"},
                evaluated_at=now,
                requires_mandatory_legal_hold=False
            )

        # 2. Clean entity
        return ScreeningAssessment(
            screening_id=f"SCR-PASS-{uuid.uuid4().hex[:6].upper()}",
            target_entity_masked=f"{entity_name[:3]}****{entity_name[-2:]}" if len(entity_name) > 5 else "ENT****MASK",
            disposition=ScreeningDisposition.CLEAR,
            compliance_gate_passed=True,              # C_comp = True
            match_score=0.0,
            matched_lists=[],
            evaluated_at=now,
            requires_mandatory_legal_hold=False
        )
