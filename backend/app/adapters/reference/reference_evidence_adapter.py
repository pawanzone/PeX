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
        # Canonical Contradiction Analysis:
        # Check for package-level contradiction indicators and cross-source conflicts.
        package_has_contradiction = False
        contradiction_reasons: List[str] = []

        # (a) Canonical boolean flags
        canonical_contra_flags = [
            "contradictory_evidence_flag",
            "contradiction_detected",
            "has_contradictory_evidence",
            "contradictory_account_status",
            "conflicting_legal_orders",
            "auxiliary_directory_active_conflict",
        ]
        for c_flag in canonical_contra_flags:
            if bool(ext.get(c_flag, False)):
                package_has_contradiction = True
                contradiction_reasons.append(f"Canonical flag {c_flag}=True")

        # (b) Generic boolean pattern match: any boolean key with 'contradict' or 'conflict'
        for k_ext, v_ext in ext.items():
            k_lower = k_ext.lower()
            if ("contradict" in k_lower or "conflict" in k_lower) and isinstance(v_ext, bool) and v_ext:
                package_has_contradiction = True
                flag_str = f"Pattern match {k_ext}=True"
                if flag_str not in contradiction_reasons:
                    contradiction_reasons.append(flag_str)

        # (c) Authoritative cross-source account contradiction (Core DDA vs SSI Directory)
        core_dda = ext.get("core_dda_account") or ext.get("verified_iban")
        ssi_acct = ext.get("ssi_directory_account") or ext.get("ssi_account")
        cross_source_acct_conflict = False
        if isinstance(core_dda, str) and isinstance(ssi_acct, str):
            c_clean = "".join(core_dda.split()).upper()
            s_clean = "".join(ssi_acct.split()).upper()
            if c_clean and s_clean and c_clean != s_clean:
                cross_source_acct_conflict = True
                package_has_contradiction = True
                contradiction_reasons.append(f"Core DDA account ({core_dda}) contradicts SSI directory ({ssi_acct})")

        for k, v in ext.items():
            val_str = json.dumps(v, sort_keys=True, default=str) if isinstance(v, dict) else str(v)
            item_hash = hashlib.sha256(val_str.encode()).hexdigest()
            tier = TrustTier.TIER_1_CORE_RECORD if "DDA" in k or "CORE" in k else (
                TrustTier.TIER_2_REGULATORY_SCHEME if "DIRECTORY" in k or "WATCHLIST" in k else (
                    TrustTier.TIER_3_CLIENT_ERP if "ERP" in k or "INVOICE" in k else TrustTier.TIER_4_HISTORICAL_AI
                )
            )
            is_stale = bool(ext.get(f"{k}_stale", False))

            # Determine if this item is in contradiction
            is_contra = bool(
                ext.get(f"{k}_contradictory", False)
                or ext.get(f"{k}_conflict", False)
                or ext.get(f"{k}_contradiction", False)
            )

            # Check dict payload for contradiction fields
            if isinstance(v, dict):
                if any(bool(v.get(ck, False)) for ck in ["is_contradictory", "contradiction_detected", "is_conflicting_order", "conflict"]):
                    is_contra = True

            # If cross-source conflict exists, mark participating account items
            if cross_source_acct_conflict and k in ["core_dda_account", "verified_iban", "ssi_directory_account", "ssi_account"]:
                is_contra = True

            # If item itself is a contradiction flag with truthy value, mark it contradictory
            if ("contradict" in k.lower() or "conflict" in k.lower()) and bool(v):
                is_contra = True

            # If package-level contradiction is present and item is an authoritative source involved in resolution
            if package_has_contradiction and ("DDA" in k.upper() or "CORE" in k.upper() or "SSI" in k.upper() or "DIRECTORY" in k.upper()):
                is_contra = True

            status = EvidenceValidationStatus.STALE if is_stale else (
                EvidenceValidationStatus.CONTRADICTORY if is_contra else EvidenceValidationStatus.AVAILABLE
            )

            contra_detail = "; ".join(contradiction_reasons) if is_contra and contradiction_reasons else (
                "Contradiction reported by source" if is_contra else None
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
                    contradiction_details=contra_detail
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
