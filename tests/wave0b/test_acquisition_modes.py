"""Tests for AcquisitionGateway across Modes 1, 2, 3, and 4."""
import pytest
from app.services.evidence_store import EvidenceStoreService
from app.services.acquisition_gateway import AcquisitionGateway
from app.schemas.contracts.evidence_schemas import TrustTier, EvidenceValidationStatus
from app.schemas.contracts.evidence_config_schemas import HitlEvidenceSubmissionRequest


def test_mode_1_inbound_payload_acquisition():
    store = EvidenceStoreService()
    gateway = AcquisitionGateway(store)

    inbound_payload = {
        "core_dda_account": {"account_id": "ACC-9988", "status": "ACTIVE"},
        "routing_directory": {"bic": "CHASUS33XXX", "valid": True},
        "custom_irrelevant_field": "test_value"
    }

    items = gateway.acquire_inbound_mode1("CASE-001", "DQ-01", inbound_payload)
    assert len(items) == 2
    types = [i.evidence_type for i in items]
    assert "CORE_DDA_ACCOUNT" in types
    assert "ROUTING_DIRECTORY" in types
    assert store.has_evidence("CASE-001", "CORE_DDA_ACCOUNT") is True


def test_mode_2_api_connector_query():
    store = EvidenceStoreService()
    gateway = AcquisitionGateway(store)

    # Core Banking DDA query
    item = gateway.query_api_connector_mode2("CASE-002", "CORE_DDA_SERVICE", {"account_number": "77889900", "currency": "USD"})
    assert item is not None
    assert item.evidence_type == "CORE_DDA_ACCOUNT"
    assert item.trust_tier == TrustTier.TIER_1_CORE_RECORD
    assert store.has_evidence("CASE-002", "CORE_DDA_ACCOUNT") is True

    # Unknown source returns None safely without error
    item_unknown = gateway.query_api_connector_mode2("CASE-002", "UNKNOWN_EXT_SERVICE", {})
    assert item_unknown is None


def test_mode_3_bank_push_event():
    store = EvidenceStoreService()
    gateway = AcquisitionGateway(store)

    push_payload = {
        "certificate_id": "REG-CERT-2026-99",
        "issuing_authority": "CENTRAL_BANK_OF_BRAZIL",
        "corridor": "EUR_BRL",
        "cleared": True
    }
    item = gateway.receive_bank_push_mode3("CASE-003", "DQ-06", "REGULATORY_CERTIFICATE", push_payload)
    assert item is not None
    assert item.evidence_type == "REGULATORY_CERTIFICATE"
    assert store.has_evidence("CASE-003", "REGULATORY_CERTIFICATE") is True


def test_mode_4_hitl_operator_submission():
    store = EvidenceStoreService()
    gateway = AcquisitionGateway(store)

    sub_req = HitlEvidenceSubmissionRequest(
        case_id="CASE-004",
        tenant_id="DEFAULT_BANK",
        profile_id="DQ-01",
        operator_id="OP-MAKER-44",
        operator_role="PAYMENT_OPERATOR",
        submitted_fields={"verified_iban": "GB82WEST12345612345678"},
        notes="Verified against official customer bank statement."
    )
    items = gateway.receive_hitl_submission_mode4(sub_req)
    assert len(items) == 1
    assert items[0].evidence_type == "CORE_DDA_ACCOUNT"
    assert items[0].trust_tier == TrustTier.TIER_1_CORE_RECORD
    assert store.has_evidence("CASE-004", "CORE_DDA_ACCOUNT") is True
