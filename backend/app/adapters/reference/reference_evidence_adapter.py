"""In-Memory Reference Evidence Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements EvidencePackagePort using hermetic in-memory structures.
"""
import hashlib
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.ports.evidence_port import EvidencePackagePort
from app.schemas.contracts.evidence_schemas import (
    EvidencePackageEnvelope,
    EvidenceItem,
    TrustTier,
    EvidenceValidationStatus,
)


class InMemoryEvidenceAdapter(EvidencePackagePort):
    """Hermetic in-memory reference implementation of EvidencePackagePort."""

    def __init__(self):
        self._packages: Dict[str, EvidencePackageEnvelope] = {}

    def acquire_evidence(
        self,
        case_id: str,
        profile_id: str,
        raw_telemetry: Dict[str, Any],
        external_context: Optional[Dict[str, Any]] = None
    ) -> EvidencePackageEnvelope:
        items: List[EvidenceItem] = []
        now = datetime.now(timezone.utc)
        ext = external_context or {}

        # 1. Telemetry / Ingestion Evidence
        raw_str = json.dumps(raw_telemetry, sort_keys=True, default=str)
        prov_hash = hashlib.sha256(raw_str.encode()).hexdigest()
        items.append(
            EvidenceItem(
                evidence_id=f"EVD-TEL-{uuid.uuid4().hex[:6].upper()}",
                evidence_type="INBOUND_PAYMENT_TELEMETRY",
                source_system="INGESTION_GATEWAY",
                trust_tier=TrustTier.TIER_1_CORE_RECORD,
                validation_status=EvidenceValidationStatus.AVAILABLE,
                acquired_at=now,
                provenance_hash=prov_hash,
                raw_payload_masked={"case_id": case_id, "fields_count": len(raw_telemetry)},
                is_authoritative=True
            )
        )

        # 2. Extract external items if provided
        for k, v in ext.items():
            val_str = json.dumps(v, sort_keys=True, default=str) if isinstance(v, dict) else str(v)
            item_hash = hashlib.sha256(val_str.encode()).hexdigest()
            tier = TrustTier.TIER_1_CORE_RECORD if "DDA" in k or "CORE" in k else (
                TrustTier.TIER_2_REGULATORY_SCHEME if "DIRECTORY" in k or "WATCHLIST" in k else (
                    TrustTier.TIER_3_CLIENT_ERP if "ERP" in k or "INVOICE" in k else TrustTier.TIER_4_HISTORICAL_AI
                )
            )
            is_stale = ext.get(f"{k}_stale", False)
            is_contra = ext.get(f"{k}_contradictory", False)
            status = EvidenceValidationStatus.STALE if is_stale else (
                EvidenceValidationStatus.CONTRADICTORY if is_contra else EvidenceValidationStatus.AVAILABLE
            )

            items.append(
                EvidenceItem(
                    evidence_id=f"EVD-{k[:6].upper()}-{uuid.uuid4().hex[:6].upper()}",
                    evidence_type=k.upper(),
                    source_system=f"SIMULATED_{k.upper()}_SOURCE",
                    trust_tier=tier,
                    validation_status=status,
                    acquired_at=now,
                    provenance_hash=item_hash,
                    raw_payload_masked=v if isinstance(v, dict) else {"value": str(v)},
                    is_authoritative=(tier in [TrustTier.TIER_1_CORE_RECORD, TrustTier.TIER_2_REGULATORY_SCHEME]),
                    is_contradictory=is_contra,
                    contradiction_details="Contradiction reported by source" if is_contra else None
                )
            )

        envelope = EvidencePackageEnvelope(
            package_id=f"PKG-{case_id}-{uuid.uuid4().hex[:4].upper()}",
            case_id=case_id,
            profile_id=profile_id,
            assembled_at=now,
            items=items,
            evidence_sufficient=False,
            is_synthetic_test_fixture=True
        )
        self._packages[envelope.package_id] = envelope
        return envelope

    def evaluate_sufficiency(
        self,
        envelope: EvidencePackageEnvelope,
        mandatory_types: List[str]
    ) -> EvidencePackageEnvelope:
        present_types = {item.evidence_type for item in envelope.items if item.validation_status == EvidenceValidationStatus.AVAILABLE}
        missing = [t for t in mandatory_types if t not in present_types]
        stale = [item.evidence_type for item in envelope.items if item.validation_status == EvidenceValidationStatus.STALE]
        contradictions = [item.evidence_type for item in envelope.items if item.is_contradictory or item.validation_status == EvidenceValidationStatus.CONTRADICTORY]

        is_sufficient = (len(missing) == 0 and len(stale) == 0 and len(contradictions) == 0)
        score = 1.0 if is_sufficient else round(max(0.0, (len(mandatory_types) - len(missing)) / max(1, len(mandatory_types))), 2)

        envelope.evidence_sufficient = is_sufficient
        envelope.sufficiency_score = score
        envelope.missing_mandatory_types = missing
        envelope.stale_types = stale
        envelope.contradictions = contradictions
        return envelope
