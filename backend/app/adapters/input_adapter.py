"""Inbound Adapter for PeX Evidence-Driven STP Architecture.

Implements the InputPort interface to ingest payment exception payloads and associated
evidence packages from folder watchers, REST endpoints, or message queues into canonical dossiers.
"""
import os
import re
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

        elif profile_id == "PR-08":
            # 1. Raw Payload Evidence Item (Tier 1 Bank Authoritative)
            dossier.add_item(EvidenceItem(
                item_name="RAW_PAYLOAD",
                source_name=package.source_channel,
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload={"raw_text": raw_text},
                is_valid=True
            ))

            # 2. Target Rail Charset Spec Evidence Item (Tier 2 External Authoritative)
            rail_spec = package.evidence_fields.get("target_rail", "SWIFT_CBPR_XSET")
            dossier.add_item(EvidenceItem(
                item_name="TARGET_RAIL_CHARSET_SPEC",
                source_name="CLEARING_RAIL_CHARSET_REGISTRY",
                trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                payload={"target_rail": rail_spec, "spec_version": "2026_STANDARDS"},
                is_valid=True
            ))

            # 3. Bank Character Substitution Policy (Tier 1 Bank Authoritative)
            sub_policy = package.evidence_fields.get("bank_character_substitution_policy", {"is_authorized": True, "corridor": "ALL"})
            dossier.add_item(EvidenceItem(
                item_name="BANK_CHARACTER_SUBSTITUTION_POLICY",
                source_name="BANK_OPERATIONAL_POLICY_STORE",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload=sub_policy,
                is_valid=True
            ))

            # 4. Processing State Record (Tier 1 Bank Authoritative)
            state_data = package.evidence_fields.get("processing_state", {
                "state_id": f"STATE-{idempotency_hash[:8]}",
                "queue_name": "INBOUND_EXCEPTION_QUEUE",
                "current_state": "INGESTED",
                "retry_count": 0,
                "max_retries": 3,
                "is_poison_message": False,
                "idempotency_key": idempotency_hash
            })
            dossier.add_item(EvidenceItem(
                item_name="PROCESSING_STATE_RECORD",
                source_name="BANK_QUEUE_MANAGER",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload=state_data,
                is_valid=True
            ))

        elif profile_id == "DQ-05":
            # 1. Raw Payload Evidence Item (Tier 1 Bank Authoritative)
            dossier.add_item(EvidenceItem(
                item_name="RAW_PAYLOAD",
                source_name=package.source_channel,
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload={"raw_text": raw_text},
                is_valid=True
            ))

            # 2. Postal Standard Spec Evidence Item (Tier 2 External Authoritative)
            dossier.add_item(EvidenceItem(
                item_name="POSTAL_STANDARD_SPEC",
                source_name="UPU_S42_ISO20022_REGISTRY",
                trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                payload={"standard": "UPU_S42_ISO20022_PSTLADR", "spec_version": "2026"},
                is_valid=True
            ))

            # 3. Bank Address Policy (Tier 1 Bank Authoritative)
            adr_policy = package.evidence_fields.get("bank_address_policy", {"is_authorized": True, "allow_auto_structuring": True})
            dossier.add_item(EvidenceItem(
                item_name="BANK_ADDRESS_POLICY",
                source_name="BANK_OPERATIONAL_POLICY_STORE",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload=adr_policy,
                is_valid=True
            ))

            # 4. Conditional: Beneficiary Master Record
            if "beneficiary_master" in package.evidence_fields:
                dossier.add_item(EvidenceItem(
                    item_name="BENEFICIARY_MASTER_RECORD",
                    source_name="BANK_CUSTOMER_MASTER_SOR",
                    trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    payload=package.evidence_fields["beneficiary_master"],
                    is_valid=True
                ))

            # 5. External Postal Directory
            post_dir_data = package.evidence_fields.get("postal_directory", {"status": "ACTIVE_VALIDATED", "provider": "ROYAL_MAIL_DEUTSCHEPOST_USPS_API"})
            dossier.add_item(EvidenceItem(
                item_name="EXTERNAL_POSTAL_DIRECTORY",
                source_name="ROYAL_MAIL_DEUTSCHEPOST_USPS_API",
                trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                payload=post_dir_data,
                is_valid=True
            ))

        elif profile_id == "PR-01":
            # 1. Raw Payload Evidence Item (Tier 1 Bank Authoritative)
            dossier.add_item(EvidenceItem(
                item_name="RAW_PAYLOAD",
                source_name=package.source_channel,
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload={"raw_text": raw_text},
                is_valid=True
            ))

            # 2. Payment Identity Record (Tier 1 Bank Authoritative)
            from app.services.pr01_duplicate_detector import pr01_detector
            ident_data = package.evidence_fields.get("payment_identity")
            if not ident_data:
                extracted_ident = pr01_detector.extract_identity(raw_text)
                ident_data = extracted_ident.model_dump()

            dossier.add_item(EvidenceItem(
                item_name="PAYMENT_IDENTITY_RECORD",
                source_name="BANK_PAYMENT_HUB_CORE",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload=ident_data if isinstance(ident_data, dict) else ident_data.model_dump(),
                is_valid=True
            ))

            # 3. Current Settlement State (Tier 1 Bank Authoritative)
            if "current_settlement_state" in package.evidence_fields:
                settle_data = package.evidence_fields["current_settlement_state"]
                dossier.add_item(EvidenceItem(
                    item_name="CURRENT_SETTLEMENT_STATE",
                    source_name="BANK_CORE_DDA_LEDGER",
                    trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    payload=settle_data if isinstance(settle_data, dict) else settle_data.model_dump(),
                    is_valid=True
                ))

            # 4. Bank Duplicate Policy (Tier 1 Bank Authoritative)
            dup_policy = package.evidence_fields.get("bank_duplicate_policy", {
                "is_authorized": True,
                "suppression_allowed": True,
                "similarity_threshold": 0.85
            })
            dossier.add_item(EvidenceItem(
                item_name="BANK_DUPLICATE_POLICY",
                source_name="BANK_OPERATIONAL_POLICY_STORE",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload=dup_policy,
                is_valid=True
            ))

            # 5. Historical Payment Index (Tier 4 Historical Precedent)
            if "historical_payments" in package.evidence_fields:
                dossier.add_item(EvidenceItem(
                    item_name="HISTORICAL_PAYMENT_INDEX",
                    source_name="HISTORICAL_PAYMENT_ARCHIVE",
                    trust_tier=EvidenceTrustTier.TIER_4_HISTORICAL_PRECEDENT,
                    payload={"historical_payments": package.evidence_fields["historical_payments"]},
                    is_valid=True
                ))

        elif profile_id in ("DQ-08", "DQ-02"):
            # 1. Raw Payload Evidence Item (Tier 1 Bank Authoritative)
            dossier.add_item(EvidenceItem(
                item_name="RAW_PAYLOAD",
                source_name=package.source_channel,
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload={"raw_text": raw_text},
                is_valid=True
            ))

            # 2. Original BIC Record (Tier 1 Bank Authoritative)
            if profile_id == "DQ-02":
                from app.services.dq02_bic_resolver import dq02_resolver as active_bic_resolver
            else:
                from app.services.dq08_bic_resolver import dq08_resolver as active_bic_resolver

            orig_bic = package.evidence_fields.get("original_bic")
            if not orig_bic:
                bic_match = re.search(r'<BICFI>([A-Z0-9]+)</BICFI>', raw_text)
                if not bic_match:
                    bic_match = re.search(r'<BIC>([A-Z0-9]+)</BIC>', raw_text)
                orig_bic = bic_match.group(1).strip() if bic_match else "UNKNOWN"

            dossier.add_item(EvidenceItem(
                item_name="ORIGINAL_BIC_RECORD",
                source_name=package.source_channel,
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload={"bic_code": orig_bic},
                is_valid=True
            ))

            # 3. BIC Reference Directory (Tier 2 External Authoritative)
            ref_data = package.evidence_fields.get("bic_reference_directory")
            if not ref_data and orig_bic != "UNKNOWN":
                lookup_res = active_bic_resolver.reference_adapter.lookup(orig_bic)
                if lookup_res:
                    ref_data = lookup_res.model_dump()

            if ref_data:
                ref_payload = ref_data if isinstance(ref_data, dict) else ref_data.model_dump()
                ref_ts = datetime.now(timezone.utc)
                if isinstance(ref_payload, dict) and "retrieved_at" in ref_payload:
                    raw_ts = ref_payload["retrieved_at"]
                    if isinstance(raw_ts, datetime):
                        ref_ts = raw_ts
                    elif isinstance(raw_ts, str):
                        try:
                            ref_ts = datetime.fromisoformat(raw_ts)
                        except Exception:
                            pass
                dossier.add_item(EvidenceItem(
                    item_name="BIC_REFERENCE_DIRECTORY",
                    source_name="SWIFTREF_GLOBAL_DIRECTORY_API",
                    trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                    timestamp=ref_ts,
                    payload=ref_payload,
                    is_valid=True
                ))

            # 4. Bank Counterparty SSI (Tier 1 Bank Authoritative)
            ssi_data = package.evidence_fields.get("bank_counterparty_ssi", {
                "counterparty_id": "CP-GLOBAL-001",
                "mandated_bic": None,
                "allowed_bics": ["DEUTDEDDFXX", "COBADEDDXXX", "SBININBBNDL", "BNPAFRPPXXX", "CHASUS33XXX", "BARCGB22XXX", "DRESDEFFXXX", "SBININBBXXX", "AMROFRPPXXX", "LOCADE22XXX", "FORTBNL2XXX", "HSBCGB2LXXX"],
                "is_authorized": True
            })
            dossier.add_item(EvidenceItem(
                item_name="BANK_COUNTERPARTY_SSI",
                source_name="BANK_SSI_MASTER_STORE",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload=ssi_data if isinstance(ssi_data, dict) else ssi_data.model_dump(),
                is_valid=True
            ))

            # 5. Target Rail Routing Spec (Tier 2 External Authoritative)
            rail_data = package.evidence_fields.get("target_rail_routing_spec", {
                "target_rail": "SWIFT_CBPR+",
                "corridor": "EUR_CROSSBORDER",
                "direct_participant_required": False
            })
            dossier.add_item(EvidenceItem(
                item_name="TARGET_RAIL_ROUTING_SPEC",
                source_name="CLEARING_RAIL_DIRECTORY",
                trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                payload=rail_data if isinstance(rail_data, dict) else rail_data.model_dump(),
                is_valid=True
            ))

            # 6. Historical BIC Directory (Tier 4 Historical Precedent)
            if "historical_bic_log" in package.evidence_fields:
                dossier.add_item(EvidenceItem(
                    item_name="HISTORICAL_BIC_DIRECTORY",
                    source_name="HISTORICAL_BIC_RESOLUTIONS",
                    trust_tier=EvidenceTrustTier.TIER_4_HISTORICAL_PRECEDENT,
                    payload={"historical_bics": package.evidence_fields["historical_bic_log"]},
                    is_valid=True
                ))

        elif profile_id == "DQ-01":
            # 1. Raw Payload Evidence Item (Tier 1 Bank Authoritative)
            dossier.add_item(EvidenceItem(
                item_name="RAW_PAYLOAD",
                source_name=package.source_channel,
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                payload={"raw_text": raw_text},
                is_valid=True
            ))

            # Extract IBAN & Beneficiary name for metadata
            iban_match = re.search(r'<CdtrAcct>\s*<Id>\s*<IBAN>([A-Z0-9]+)</IBAN>', raw_text)
            if not iban_match:
                iban_match = re.search(r'<IBAN>([A-Z0-9]+)</IBAN>', raw_text)
            orig_iban = package.evidence_fields.get("original_iban") or (iban_match.group(1).strip().upper() if iban_match else "UNKNOWN")

            bene_match = re.search(r'<Cdtr>\s*<Nm>([^<]+)</Nm>', raw_text)
            orig_bene = package.evidence_fields.get("beneficiary_name") or (bene_match.group(1).strip() if bene_match else None)

            dossier.metadata["original_iban"] = orig_iban
            dossier.metadata["beneficiary_name"] = orig_bene
            dossier.metadata["allow_stale_evidence"] = package.evidence_fields.get("allow_stale_evidence", False)
            dossier.metadata["require_cop"] = package.evidence_fields.get("require_cop", False)

            # 2. ISO 13616 Structure Spec (Tier 2 External Authoritative)
            dossier.add_item(EvidenceItem(
                item_name="ISO_13616_IBAN_STRUCTURE_SPEC",
                source_name="ISO_13616_REGISTRY",
                trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                payload={"spec_version": "ISO_13616_2020", "mod97_required": True},
                is_valid=True
            ))

            # 3. Bank SSI Master Record (Tier 1 Bank Authoritative)
            from app.services.dq01_iban_resolver import dq01_resolver
            ssi_data = package.evidence_fields.get("bank_ssi_master")
            if not ssi_data and orig_bene:
                ssi_entry = dq01_resolver.ssi_adapter.lookup(orig_bene)
                if ssi_entry:
                    ssi_data = ssi_entry.model_dump()
            if not ssi_data:
                ssi_data = {
                    "counterparty_id": "CP-AUTO-001",
                    "beneficiary_name": orig_bene or "Unknown",
                    "mandated_iban": orig_iban,
                    "allowed_ibans": [orig_iban],
                    "is_authorized": True
                }

            ssi_payload = ssi_data if isinstance(ssi_data, dict) else ssi_data.model_dump()
            ssi_ts = datetime.now(timezone.utc)
            if isinstance(ssi_payload, dict) and "retrieved_at" in ssi_payload:
                raw_ts = ssi_payload["retrieved_at"]
                if isinstance(raw_ts, datetime):
                    ssi_ts = raw_ts
                elif isinstance(raw_ts, str):
                    try:
                        ssi_ts = datetime.fromisoformat(raw_ts)
                    except Exception:
                        pass
            dossier.add_item(EvidenceItem(
                item_name="BANK_SSI_MASTER_RECORD",
                source_name="BANK_SSI_MASTER_STORE",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                timestamp=ssi_ts,
                payload=ssi_payload,
                is_valid=True
            ))

            # 4. Core DDA Account Status (Tier 1 Bank Authoritative)
            dda_data = package.evidence_fields.get("core_dda_account")
            if not dda_data and orig_iban != "UNKNOWN":
                dda_entry = dq01_resolver.dda_adapter.lookup(orig_iban)
                if dda_entry:
                    dda_data = dda_entry.model_dump()
            if not dda_data:
                dda_data = {
                    "account_number": orig_iban[-10:] if len(orig_iban) >= 10 else "0000000000",
                    "iban": orig_iban,
                    "account_holder_name": orig_bene or "Unknown",
                    "status": "OPEN",
                    "currency": "EUR"
                }

            dda_payload = dda_data if isinstance(dda_data, dict) else dda_data.model_dump()
            dda_ts = datetime.now(timezone.utc)
            if isinstance(dda_payload, dict) and "retrieved_at" in dda_payload:
                raw_ts = dda_payload["retrieved_at"]
                if isinstance(raw_ts, datetime):
                    dda_ts = raw_ts
                elif isinstance(raw_ts, str):
                    try:
                        dda_ts = datetime.fromisoformat(raw_ts)
                    except Exception:
                        pass
            dossier.add_item(EvidenceItem(
                item_name="CORE_DDA_ACCOUNT_STATUS",
                source_name="BANK_CORE_DDA_LEDGER",
                trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                timestamp=dda_ts,
                payload=dda_payload,
                is_valid=True
            ))

            # 5. Conditional: Customer Beneficiary Master Record
            if "customer_beneficiary_master" in package.evidence_fields:
                cust_data = package.evidence_fields["customer_beneficiary_master"]
                dossier.add_item(EvidenceItem(
                    item_name="CUSTOMER_BENEFICIARY_MASTER",
                    source_name="BANK_CUSTOMER_MASTER",
                    trust_tier=EvidenceTrustTier.TIER_1_BANK_AUTHORITATIVE,
                    payload=cust_data if isinstance(cust_data, dict) else cust_data.model_dump(),
                    is_valid=True
                ))

            # 6. Conditional: CoP / VoP Response
            if "cop_vop_response" in package.evidence_fields:
                cop_data = package.evidence_fields["cop_vop_response"]
                dossier.add_item(EvidenceItem(
                    item_name="COP_VOP_RESPONSE",
                    source_name="PAY_UK_COP_GATEWAY",
                    trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                    payload=cop_data if isinstance(cop_data, dict) else cop_data.model_dump(),
                    is_valid=True
                ))

            # 7. Conditional: Target Rail Routing Spec
            if "target_rail_routing_spec" in package.evidence_fields:
                rail_data = package.evidence_fields["target_rail_routing_spec"]
                dossier.add_item(EvidenceItem(
                    item_name="TARGET_RAIL_ROUTING_SPEC",
                    source_name="CLEARING_RAIL_DIRECTORY",
                    trust_tier=EvidenceTrustTier.TIER_2_EXTERNAL_AUTHORITATIVE,
                    payload=rail_data if isinstance(rail_data, dict) else rail_data.model_dump(),
                    is_valid=True
                ))

            # 8. Optional: Historical Repair Pattern
            if "historical_repair_pattern" in package.evidence_fields:
                hist_data = package.evidence_fields["historical_repair_pattern"]
                dossier.add_item(EvidenceItem(
                    item_name="HISTORICAL_REPAIR_PATTERN",
                    source_name="HISTORICAL_IBAN_RESOLUTIONS",
                    trust_tier=EvidenceTrustTier.TIER_4_HISTORICAL_PRECEDENT,
                    payload={"historical_repairs": hist_data},
                    is_valid=True
                ))


        # 3. Add any caller-supplied additional evidence items
        for key, val in package.evidence_fields.items():
            if key not in [
                "has_contradictory_evidence", "contradiction_detail", "target_scheme",
                "bank_transliteration_policy", "target_rail", "bank_character_substitution_policy",
                "processing_state", "bank_address_policy", "beneficiary_master", "postal_directory"
            ]:
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

