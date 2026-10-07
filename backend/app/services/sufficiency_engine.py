"""Evidence Sufficiency Engine for PeX Evidence-Driven STP Architecture.

Evaluates whether gathered evidence meets mandatory contract requirements, configured freshness TTLs,
and trust tier standards, producing explicit sufficiency states without probabilistic guessing.
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.schemas.evidence_contract import (
    EvidenceContract,
    EvidenceDossier,
    EvidenceItem,
    EvidenceTrustTier,
    evidence_registry,
)


class EvidenceSufficiencyStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONTRADICTORY_EVIDENCE = "CONTRADICTORY_EVIDENCE"
    STALE_EVIDENCE = "STALE_EVIDENCE"


class EvidenceSufficiencyResult(BaseModel):
    """Result of evaluating evidence sufficiency for an exception case."""
    case_id: str
    profile_id: str
    status: EvidenceSufficiencyStatus
    is_sufficient: bool
    missing_mandatory_items: List[str] = Field(default_factory=list)
    stale_items: List[str] = Field(default_factory=list)
    contradictory_items: List[str] = Field(default_factory=list)
    trust_tier_violations: List[str] = Field(default_factory=list)
    evaluated_items: List[str] = Field(default_factory=list)
    audit_trail: List[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvidenceSufficiencyEngine:
    """Evaluates evidence dossiers against registered Evidence Contracts deterministically."""

    def evaluate_sufficiency(
        self,
        dossier: EvidenceDossier,
        contract: Optional[EvidenceContract] = None,
        now: Optional[datetime] = None
    ) -> EvidenceSufficiencyResult:
        """Evaluates completeness, freshness, trust tiers, and contradictions for a given dossier."""
        current_time = now or datetime.now(timezone.utc)
        target_contract = contract or evidence_registry.get_contract(dossier.profile_id)

        trail: List[str] = []
        missing_mandatory: List[str] = []
        stale_items: List[str] = []
        contradictory_items: List[str] = []
        tier_violations: List[str] = []
        evaluated_items: List[str] = []

        if not target_contract:
            trail.append(f"No Evidence Contract registered for profile {dossier.profile_id}.")
            return EvidenceSufficiencyResult(
                case_id=dossier.case_id,
                profile_id=dossier.profile_id,
                status=EvidenceSufficiencyStatus.INSUFFICIENT_EVIDENCE,
                is_sufficient=False,
                missing_mandatory_items=["CONTRACT_NOT_FOUND"],
                audit_trail=trail,
                evaluated_at=current_time
            )

        trail.append(f"Evaluating Evidence Contract for profile: {target_contract.profile_id} ({target_contract.profile_name})")

        # 1. Check Mandatory Evidence Requirements
        for req in target_contract.mandatory_evidence:
            item = dossier.get_item(req.item_name)
            if not item:
                missing_mandatory.append(req.item_name)
                trail.append(f"Missing mandatory evidence item: {req.item_name}")
                continue

            evaluated_items.append(req.item_name)

            # Check validity
            if not item.is_valid:
                missing_mandatory.append(req.item_name)
                trail.append(f"Mandatory evidence item {req.item_name} is marked invalid: {item.validation_error}")
                continue

            # Check Trust Tier hierarchy: Item must meet or exceed required trust tier
            # Tier ordering: TIER_1 (highest) < TIER_2 < TIER_3 < TIER_4 (lowest)
            tier_ranks = {
                EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE: 1,
                EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE: 2,
                EvidenceTrustTier.TIER_3_PEX_DERIVED: 3,
                EvidenceTrustTier.TIER_4_HISTORICAL_PRECEDENT: 4,
            }
            actual_rank = tier_ranks.get(item.trust_tier, 99)
            required_rank = tier_ranks.get(req.required_trust_tier, 1)

            if actual_rank > required_rank:
                tier_violations.append(
                    f"{req.item_name}: Provided tier {item.trust_tier} does not meet required tier {req.required_trust_tier}"
                )
                trail.append(f"Trust tier violation for {req.item_name}: rank {actual_rank} > required {required_rank}")

            # Check Policy Freshness TTL
            if req.policy_freshness_seconds is not None:
                item_age_seconds = (current_time - item.timestamp).total_seconds()
                if item_age_seconds > req.policy_freshness_seconds:
                    stale_items.append(
                        f"{req.item_name} (age: {int(item_age_seconds)}s > TTL: {req.policy_freshness_seconds}s)"
                    )
                    trail.append(f"Stale evidence item: {req.item_name} exceeded TTL ({int(item_age_seconds)}s > {req.policy_freshness_seconds}s)")

        # 2. Check for Contradictory Evidence in Dossier Metadata
        if dossier.metadata.get("has_contradictory_evidence", False):
            conflict_detail = dossier.metadata.get("contradiction_detail", "Contradictory evidence sources detected.")
            contradictory_items.append(conflict_detail)
            trail.append(f"Contradiction detected: {conflict_detail}")

        # 3. Determine Overall Sufficiency Status
        if contradictory_items:
            status = EvidenceSufficiencyStatus.CONTRADICTORY_EVIDENCE
            is_sufficient = False
        elif stale_items:
            status = EvidenceSufficiencyStatus.STALE_EVIDENCE
            is_sufficient = False
        elif missing_mandatory or tier_violations:
            status = EvidenceSufficiencyStatus.INSUFFICIENT_EVIDENCE
            is_sufficient = False
        else:
            status = EvidenceSufficiencyStatus.SUFFICIENT
            is_sufficient = True
            trail.append(f"All {len(target_contract.mandatory_evidence)} mandatory evidence items validated as SUFFICIENT and FRESH.")

        return EvidenceSufficiencyResult(
            case_id=dossier.case_id,
            profile_id=dossier.profile_id,
            status=status,
            is_sufficient=is_sufficient,
            missing_mandatory_items=missing_mandatory,
            stale_items=stale_items,
            contradictory_items=contradictory_items,
            trust_tier_violations=tier_violations,
            evaluated_items=evaluated_items,
            audit_trail=trail,
            evaluated_at=current_time
        )


# Global singleton sufficiency engine
sufficiency_engine = EvidenceSufficiencyEngine()
