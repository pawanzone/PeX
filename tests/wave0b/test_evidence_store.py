"""Tests for EvidenceStoreService: content-addressability, deduplication, trust tiers, and Merkle hashing."""
import pytest
from datetime import datetime, timezone, timedelta
from app.services.evidence_store import EvidenceStoreService
from app.schemas.contracts.evidence_schemas import (
    EvidenceItem,
    TrustTier,
    EvidenceValidationStatus,
)


def test_evidence_storage_and_retrieval():
    store = EvidenceStoreService()
    item = EvidenceItem(
        evidence_id="EV-01",
        evidence_type="CORE_DDA_ACCOUNT",
        source_system="CORE_DDA",
        trust_tier=TrustTier.TIER_1_CORE_RECORD,
        validation_status=EvidenceValidationStatus.AVAILABLE,
        provenance_hash="hash_12345",
        raw_payload_masked={"account": "12345678", "status": "ACTIVE"}
    )
    store.store_evidence_item("CASE-100", item)

    dossier = store.get_evidence_dossier("CASE-100")
    assert len(dossier) == 1
    assert dossier[0].evidence_type == "CORE_DDA_ACCOUNT"
    assert store.has_evidence("CASE-100", "CORE_DDA_ACCOUNT") is True
    assert store.has_evidence("CASE-100", "ROUTING_DIRECTORY") is False


def test_evidence_deduplication():
    store = EvidenceStoreService()
    item1 = EvidenceItem(
        evidence_id="EV-01",
        evidence_type="CORE_DDA_ACCOUNT",
        source_system="CORE_DDA",
        trust_tier=TrustTier.TIER_1_CORE_RECORD,
        validation_status=EvidenceValidationStatus.AVAILABLE,
        provenance_hash="hash_identical",
        raw_payload_masked={"account": "12345678"}
    )
    item2 = EvidenceItem(
        evidence_id="EV-02",
        evidence_type="CORE_DDA_ACCOUNT",
        source_system="CORE_DDA",
        trust_tier=TrustTier.TIER_1_CORE_RECORD,
        validation_status=EvidenceValidationStatus.AVAILABLE,
        provenance_hash="hash_identical",
        raw_payload_masked={"account": "12345678"}
    )
    store.store_evidence_item("CASE-100", item1)
    store.store_evidence_item("CASE-100", item2)

    dossier = store.get_evidence_dossier("CASE-100")
    # Should deduplicate and keep exactly 1 item
    assert len(dossier) == 1


def test_trust_tier_supersession():
    store = EvidenceStoreService()
    # Lower trust tier (Tier 3) added first
    item_tier3 = EvidenceItem(
        evidence_id="EV-ERP",
        evidence_type="CORE_DDA_ACCOUNT",
        source_system="CLIENT_ERP_INVOICE",
        trust_tier=TrustTier.TIER_3_CLIENT_ERP,
        validation_status=EvidenceValidationStatus.AVAILABLE,
        provenance_hash="hash_erp",
        raw_payload_masked={"account": "12345678_OLD"}
    )
    # Higher trust tier (Tier 1) arrives later
    item_tier1 = EvidenceItem(
        evidence_id="EV-CORE",
        evidence_type="CORE_DDA_ACCOUNT",
        source_system="CORE_DDA_DDA",
        trust_tier=TrustTier.TIER_1_CORE_RECORD,
        validation_status=EvidenceValidationStatus.AVAILABLE,
        provenance_hash="hash_core",
        raw_payload_masked={"account": "12345678_OFFICIAL"}
    )
    store.store_evidence_item("CASE-100", item_tier3)
    store.store_evidence_item("CASE-100", item_tier1)

    # get_evidence_by_type should return Tier 1
    best_item = store.get_evidence_by_type("CASE-100", "CORE_DDA_ACCOUNT")
    assert best_item is not None
    assert best_item.trust_tier == TrustTier.TIER_1_CORE_RECORD
    assert best_item.evidence_id == "EV-CORE"


def test_dossier_hash_immutability():
    store = EvidenceStoreService()
    item = EvidenceItem(
        evidence_id="EV-01",
        evidence_type="CORE_DDA_ACCOUNT",
        source_system="CORE_DDA",
        trust_tier=TrustTier.TIER_1_CORE_RECORD,
        validation_status=EvidenceValidationStatus.AVAILABLE,
        provenance_hash="hash_abc",
        raw_payload_masked={"account": "123"}
    )
    store.store_evidence_item("CASE-100", item)
    hash1 = store.compute_dossier_hash("CASE-100")
    assert len(hash1) == 64 # SHA-256 length

    hash2 = store.compute_dossier_hash("CASE-100")
    assert hash1 == hash2
