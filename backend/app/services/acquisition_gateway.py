"""Evidence Acquisition Gateway.

Coordinates multi-mode evidence ingestion across Mode 1 (Inbound), Mode 2 (API Connector),
Mode 3 (Bank Push), and Mode 4 (HITL Operator).
Reference: PeX_Evidence_Acquisition_and_Resolution_Contract_v0.3.1.md Section 2 & 5.
"""
import uuid
import hashlib
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta

from app.ports.acquisition_port import EvidenceAcquisitionPort
from app.ports.evidence_store_port import EvidenceStorePort
from app.schemas.contracts.evidence_schemas import (
    EvidenceItem,
    TrustTier,
    EvidenceValidationStatus,
)
from app.schemas.contracts.evidence_config_schemas import HitlEvidenceSubmissionRequest


class AcquisitionGateway(EvidenceAcquisitionPort):
    """Gateway coordinating evidence intake from all supported channels into the EvidenceStore."""

    def __init__(self, evidence_store: EvidenceStorePort):
        self._store = evidence_store

    def acquire_inbound_mode1(
        self,
        case_id: str,
        profile_id: str,
        payload_data: Dict[str, Any]
    ) -> List[EvidenceItem]:
        """Processes pre-gathered evidence bundled inside the inbound exception payload."""
        items: List[EvidenceItem] = []
        now = datetime.now(timezone.utc)

        # Mapping of common payload evidence keys to canonical evidence types & trust tiers
        type_mapping = {
            "core_dda_account": ("CORE_DDA_ACCOUNT", TrustTier.TIER_1_CORE_RECORD),
            "routing_directory": ("ROUTING_DIRECTORY", TrustTier.TIER_2_REGULATORY_SCHEME),
            "fedline_routing_directory": ("FEDLINE_ROUTING_DIRECTORY", TrustTier.TIER_2_REGULATORY_SCHEME),
            "routing_syntax_master": ("ROUTING_SYNTAX_MASTER", TrustTier.TIER_2_REGULATORY_SCHEME),
            "historical_payment_journal": ("HISTORICAL_PAYMENT_JOURNAL", TrustTier.TIER_1_CORE_RECORD),
            "settlement_ledger": ("SETTLEMENT_LEDGER", TrustTier.TIER_1_CORE_RECORD),
            "streaming_broker_journal": ("STREAMING_BROKER_JOURNAL", TrustTier.TIER_1_CORE_RECORD),
            "dlq_record": ("DLQ_RECORD", TrustTier.TIER_1_CORE_RECORD),
            "inward_pacs004_return": ("INWARD_PACS004_RETURN", TrustTier.TIER_1_CORE_RECORD),
            "original_debit_record": ("ORIGINAL_DEBIT_RECORD", TrustTier.TIER_1_CORE_RECORD),
            "sanctions_watchlist": ("SANCTIONS_WATCHLIST", TrustTier.TIER_2_REGULATORY_SCHEME),
            "corridor_policy_matrix": ("CORRIDOR_POLICY_MATRIX", TrustTier.TIER_2_REGULATORY_SCHEME),
            "verified_iban": ("VERIFIED_IBAN_RECORD", TrustTier.TIER_1_CORE_RECORD),
            "account_statement": ("ACCOUNT_STATEMENT", TrustTier.TIER_1_CORE_RECORD),
            "regulatory_certificate": ("REGULATORY_CERTIFICATE", TrustTier.TIER_2_REGULATORY_SCHEME),
        }

        for key, val in payload_data.items():
            key_lower = key.lower()
            if key_lower in type_mapping and val:
                ev_type, tier = type_mapping[key_lower]
                val_dict = val if isinstance(val, dict) else {"value": str(val)}
                raw_hash = hashlib.sha256(json.dumps(val_dict, sort_keys=True).encode("utf-8")).hexdigest()

                item = EvidenceItem(
                    evidence_id=f"EV-M1-{uuid.uuid4().hex[:8].upper()}",
                    evidence_type=ev_type,
                    source_system="INBOUND_PAYLOAD_MODE_1",
                    trust_tier=tier,
                    validation_status=EvidenceValidationStatus.AVAILABLE,
                    acquired_at=now,
                    expires_at=now + timedelta(days=1),
                    provenance_hash=raw_hash,
                    raw_payload_masked=val_dict,
                    is_authoritative=(tier in [TrustTier.TIER_1_CORE_RECORD, TrustTier.TIER_2_REGULATORY_SCHEME])
                )
                self._store.store_evidence_item(case_id, item)
                items.append(item)

        return items

    def query_api_connector_mode2(
        self,
        case_id: str,
        source_id: str,
        query_params: Dict[str, Any]
    ) -> Optional[EvidenceItem]:
        """Simulates automated outbound query via Port adapter (Progressive Mode 2)."""
        now = datetime.now(timezone.utc)
        source_upper = source_id.upper()

        if "CORE_DDA" in source_upper:
            account = query_params.get("account_number") or query_params.get("iban")
            if account:
                payload = {
                    "account_number": account,
                    "status": "ACTIVE",
                    "currency": query_params.get("currency", "USD"),
                    "holder_name": "ACME CORP LOGISTICS",
                    "inquiry_timestamp": now.isoformat()
                }
                raw_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
                item = EvidenceItem(
                    evidence_id=f"EV-M2-{uuid.uuid4().hex[:8].upper()}",
                    evidence_type="CORE_DDA_ACCOUNT",
                    source_system="CORE_BANKING_API_MODE_2",
                    trust_tier=TrustTier.TIER_1_CORE_RECORD,
                    validation_status=EvidenceValidationStatus.AVAILABLE,
                    acquired_at=now,
                    expires_at=now + timedelta(hours=12),
                    provenance_hash=raw_hash,
                    raw_payload_masked=payload,
                    is_authoritative=True
                )
                self._store.store_evidence_item(case_id, item)
                return item

        elif "ROUTING" in source_upper or "SWIFTREF" in source_upper:
            bic = query_params.get("bic") or query_params.get("routing_code")
            if bic:
                payload = {
                    "routing_code": bic,
                    "institution_name": "CITIBANK N.A. LONDON",
                    "status": "VALID_CONNECTED",
                    "inquiry_timestamp": now.isoformat()
                }
                raw_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
                item = EvidenceItem(
                    evidence_id=f"EV-M2-{uuid.uuid4().hex[:8].upper()}",
                    evidence_type="ROUTING_DIRECTORY",
                    source_system="SWIFTREF_DIRECTORY_API_MODE_2",
                    trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                    validation_status=EvidenceValidationStatus.AVAILABLE,
                    acquired_at=now,
                    expires_at=now + timedelta(days=1),
                    provenance_hash=raw_hash,
                    raw_payload_masked=payload,
                    is_authoritative=True
                )
                self._store.store_evidence_item(case_id, item)
                return item

        return None

    def receive_bank_push_mode3(
        self,
        case_id: str,
        profile_id: str,
        event_type: str,
        push_payload: Dict[str, Any]
    ) -> EvidenceItem:
        """Processes an asynchronous event pushed by a bank system."""
        now = datetime.now(timezone.utc)
        raw_hash = hashlib.sha256(json.dumps(push_payload, sort_keys=True).encode("utf-8")).hexdigest()

        tier = TrustTier.TIER_1_CORE_RECORD if "STATEMENT" in event_type or "LEDGER" in event_type else TrustTier.TIER_2_REGULATORY_SCHEME

        item = EvidenceItem(
            evidence_id=f"EV-M3-{uuid.uuid4().hex[:8].upper()}",
            evidence_type=event_type,
            source_system="BANK_ASYNC_PUSH_MODE_3",
            trust_tier=tier,
            validation_status=EvidenceValidationStatus.AVAILABLE,
            acquired_at=now,
            expires_at=now + timedelta(days=2),
            provenance_hash=raw_hash,
            raw_payload_masked=push_payload,
            is_authoritative=True
        )
        self._store.store_evidence_item(case_id, item)
        return item

    def receive_hitl_submission_mode4(
        self,
        submission: HitlEvidenceSubmissionRequest
    ) -> List[EvidenceItem]:
        """Converts human operator input from the resolution workspace into structured evidence items."""
        now = datetime.now(timezone.utc)
        items: List[EvidenceItem] = []

        for field_key, field_val in submission.submitted_fields.items():
            payload = {
                "field_key": field_key,
                "field_value": str(field_val),
                "operator_id": submission.operator_id,
                "operator_role": submission.operator_role,
                "notes": submission.notes,
                "action": submission.action,
                "submitted_at": now.isoformat()
            }
            raw_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

            # Map field key to evidence type
            ev_type = "OPERATOR_CORRECTION"
            if "iban" in field_key.lower():
                ev_type = "CORE_DDA_ACCOUNT"
            elif "routing" in field_key.lower() or "bic" in field_key.lower():
                ev_type = "FEDLINE_ROUTING_DIRECTORY"
            elif "purpose" in field_key.lower():
                ev_type = "REGULATORY_CERTIFICATE"

            item = EvidenceItem(
                evidence_id=f"EV-M4-{uuid.uuid4().hex[:8].upper()}",
                evidence_type=ev_type,
                source_system=f"HITL_OPERATOR_{submission.operator_role}",
                trust_tier=TrustTier.TIER_1_CORE_RECORD, # Operator Maker input validated by system
                validation_status=EvidenceValidationStatus.AVAILABLE,
                acquired_at=now,
                expires_at=now + timedelta(days=7),
                provenance_hash=raw_hash,
                raw_payload_masked=payload,
                is_authoritative=True
            )
            self._store.store_evidence_item(submission.case_id, item)
            items.append(item)

        return items
