"""Inbound Adapter for PeX Evidence-Driven STP Architecture.

Implements the InputPort interface to ingest payment exception payloads and associated
evidence packages from folder watchers, REST endpoints, or message queues into canonical dossiers.
"""
import os
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.schemas.evidence_contract import (
    EvidenceDossier,
    EvidenceItem,
    EvidenceTrustTier,
)


from app.schemas.canonical_envelopes import CanonicalIntakeEnvelope


class InboundPackage(BaseModel):
    """Raw inbound payload container before canonical normalization."""
    package_id: str
    source_channel: str                       # e.g., "BANK_INPUT_FOLDER", "REST_INGEST", "MQ_FEED"
    raw_payload_str: str                      # Raw XML or JSON payload string
    evidence_fields: Dict[str, Any] = Field(default_factory=dict)
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    idempotency_key: Optional[str] = None

    @classmethod
    def from_canonical_envelope(cls, env: CanonicalIntakeEnvelope) -> "InboundPackage":
        """Creates an InboundPackage from a CanonicalIntakeEnvelope (pex.intake.v1)."""
        return cls(
            package_id=env.message_id,
            source_channel=f"{env.source_system}:{env.channel}",
            raw_payload_str=env.raw_payload,
            evidence_fields=env.evidence_items,
            idempotency_key=env.correlation_id or env.uetr
        )


class InputPort:
    """Abstract port for exception payload ingestion."""

    def ingest_payload(self, package: InboundPackage, profile_id: str = "PR-03") -> Tuple[str, EvidenceDossier, str]:
        raise NotImplementedError


class FolderInputAdapter(InputPort):
    """File/Folder-based input adapter reading exception packages from an input folder or memory."""

    def __init__(self, input_dir: Optional[str] = None):
        self.input_dir = input_dir
        self._processed_hashes: set = set()

    def calculate_idempotency_hash(self, raw_content: str) -> str:
        """Calculates a deterministic SHA-256 hash over raw inbound content to ensure idempotency."""
        return hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

    def ingest_payload(
        self,
        package: InboundPackage,
        profile_id: str = "PR-03"
    ) -> Tuple[str, EvidenceDossier, str]:
        """Ingests a raw inbound package, extracts evidence items, and creates an EvidenceDossier."""
        raw_text = package.raw_payload_str
        idempotency_hash = package.idempotency_key or self.calculate_idempotency_hash(raw_text)

        case_id = f"CASE-{profile_id}-{idempotency_hash[:8]}"
        is_duplicate = idempotency_hash in self._processed_hashes
        self._processed_hashes.add(idempotency_hash)

        dossier = EvidenceDossier(
            case_id=case_id,
            profile_id=profile_id,
            collected_at=datetime.now(timezone.utc),
            metadata={
                "source_channel": package.source_channel,
                "idempotency_hash": idempotency_hash,
                "is_duplicate_ingestion": is_duplicate,
                "package_id": package.package_id,
                "has_contradictory_evidence": package.evidence_fields.get("has_contradictory_evidence", False),
                "contradiction_detail": package.evidence_fields.get("contradiction_detail")
            }
        )

        if profile_id == "PR-03":
            # 1. Primary Raw Payload Evidence Item (Tier 1 Bank Authoritative)
            dossier.add_item(EvidenceItem(
                item_name="RAW_PAYLOAD",
                source_name=package.source_channel,
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload={"raw_text": raw_text},
                is_valid=True
            ))

            # 2. ISO 20022 Schema Spec Evidence Item (Tier 2 External Authoritative)
            dossier.add_item(EvidenceItem(
                item_name="ISO20022_SCHEMA_SPEC",
                source_name="ISO_W3C_SCHEMA_REGISTRY",
                trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                payload={
                    "spec_version": "pacs.008.001.08",
                    "ruleset": "CBPR+_2026_STRICT"
                },
                is_valid=True
            ))

        elif profile_id == "PR-05":
            # 1. Raw Payload Bytes Evidence Item (Tier 1 Bank Authoritative)
            dossier.add_item(EvidenceItem(
                item_name="RAW_PAYLOAD_BYTES",
                source_name=package.source_channel,
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload={"raw_text": raw_text, "raw_bytes": raw_text.encode("utf-8", errors="surrogateescape")},
                is_valid=True
            ))

            # 2. Target Scheme Charset Spec Evidence Item (Tier 2 External Authoritative)
            scheme_spec = package.evidence_fields.get("target_scheme", "ISO20022_UTF8")
            dossier.add_item(EvidenceItem(
                item_name="TARGET_SCHEME_CHARSET_SPEC",
                source_name="SWIFT_CBPR_CHARSET_REGISTRY",
                trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                payload={"target_scheme": scheme_spec, "spec_version": "CBPR+_XSET_ZSET_2026"},
                is_valid=True
            ))

            # 3. Bank Transliteration Policy (Tier 1 Bank Authoritative)
            policy_data = package.evidence_fields.get("bank_transliteration_policy", {"is_authorized": True, "corridor": "ALL"})
            dossier.add_item(EvidenceItem(
                item_name="BANK_TRANSLITERATION_POLICY",
                source_name="BANK_OPERATIONAL_POLICY_STORE",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload=policy_data,
                is_valid=True
            ))

        # 3. Add any caller-supplied additional evidence items
        for key, val in package.evidence_fields.items():
            if key not in ["has_contradictory_evidence", "contradiction_detail", "target_scheme", "bank_transliteration_policy"]:
                tier = EvidenceTrustTier.TIER_4_HISTORICAL_PRECEDENT if "HISTORICAL" in key else EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE
                dossier.add_item(EvidenceItem(
                    item_name=key,
                    source_name="BANK_EVIDENCE_PACKAGE",
                    trust_tier=tier,
                    payload={"value": val} if not isinstance(val, dict) else val,
                    is_valid=True
                ))

        return case_id, dossier, idempotency_hash

    def read_file_and_ingest(self, file_path: str, profile_id: str = "PR-03") -> Tuple[str, EvidenceDossier, str]:
        """Reads a file from disk and parses it into an EvidenceDossier."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        evidence_data = {}
        # If the file is JSON, it might contain raw_xml / raw_payload + evidence fields
        if content.strip().startswith("{"):
            try:
                parsed_json = json.loads(content)
                raw_payload = parsed_json.get("raw_payload") or parsed_json.get("raw_xml") or content
                evidence_data = parsed_json.get("evidence", {})
                content = raw_payload
            except Exception:
                pass

        package = InboundPackage(
            package_id=os.path.basename(file_path),
            source_channel="BANK_INPUT_FOLDER",
            raw_payload_str=content,
            evidence_fields=evidence_data
        )

        return self.ingest_payload(package, profile_id=profile_id)

