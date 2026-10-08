"""Tests for HITLWorkflowService: gap dossier, validation, submission, and re-evaluation."""
import pytest
from app.adapters.reference.reference_configuration_adapter import InMemoryConfigurationAdapter
from app.services.dynamic_config_resolver import DynamicEvidenceConfigResolver
from app.services.evidence_store import EvidenceStoreService
from app.services.acquisition_gateway import AcquisitionGateway
from app.services.hitl_workflow_service import HITLWorkflowService
from app.schemas.contracts.evidence_config_schemas import (
    HitlEvidenceSubmissionRequest,
    BankEvidenceRequiredConfig,
    EvidenceRuleDefinition,
    HitlWorkflowConfig,
    HitlFieldDefinition,
    HitlFieldType,
)
from app.schemas.contracts.evidence_schemas import TrustTier


def test_generate_gap_dossier():
    config_adapter = InMemoryConfigurationAdapter()
    resolver = DynamicEvidenceConfigResolver(config_adapter)
    store = EvidenceStoreService()
    gateway = AcquisitionGateway(store)
    hitl_service = HITLWorkflowService(resolver, gateway, store)

    dossier = hitl_service.generate_gap_dossier(
        case_id="CASE-500",
        profile_id="DQ-01",
        tenant_id="DEFAULT_BANK",
        missing_evidence_types=["CORE_DDA_ACCOUNT"],
        transaction_context={"amount": 10000, "currency": "GBP"}
    )
    assert dossier.case_id == "CASE-500"
    assert "CORE_DDA_ACCOUNT" in dossier.missing_evidence_types
    assert len(dossier.fields) >= 1
    assert dossier.fields[0].field_id == "verified_iban"


def test_hitl_operator_submission_validation_and_re_evaluation():
    config_adapter = InMemoryConfigurationAdapter()
    resolver = DynamicEvidenceConfigResolver(config_adapter)
    store = EvidenceStoreService()
    gateway = AcquisitionGateway(store)
    hitl_service = HITLWorkflowService(resolver, gateway, store)

    # Pre-populate 1 of 2 mandatory items
    gateway.acquire_inbound_mode1(
        "CASE-501", "DQ-01",
        {"routing_directory": {"bic": "CHASGB2LXXX", "valid": True}}
    )
    assert store.has_evidence("CASE-501", "ROUTING_DIRECTORY") is True
    assert store.has_evidence("CASE-501", "CORE_DDA_ACCOUNT") is False

    # Simulate re-evaluation callback
    re_eval_called = False
    def mock_re_eval(case_id):
        nonlocal re_eval_called
        re_eval_called = True
        return {"stp_eligible": True, "status": "RESOLVED"}

    # Operator supplies missing verified IBAN via Mode 4
    sub_req = HitlEvidenceSubmissionRequest(
        case_id="CASE-501",
        tenant_id="DEFAULT_BANK",
        profile_id="DQ-01",
        operator_id="OP-MAKER-01",
        operator_role="PAYMENT_OPERATOR",
        submitted_fields={"verified_iban": "GB82WEST12345612345678"},
        notes="Customer verified account."
    )

    resp = hitl_service.process_operator_submission(
        submission=sub_req,
        transaction_context={"amount": 10000, "currency": "GBP"},
        re_eval_callback=mock_re_eval
    )

    assert resp.is_accepted is True
    assert resp.re_evaluation_triggered is True
    assert resp.new_evidence_sufficient is True
    assert resp.new_stp_eligible is True
    assert resp.new_status == "RESOLVED"
    assert re_eval_called is True
    assert store.has_evidence("CASE-501", "CORE_DDA_ACCOUNT") is True


def test_hitl_submission_validation_failure_on_missing_required_field():
    config_adapter = InMemoryConfigurationAdapter()
    resolver = DynamicEvidenceConfigResolver(config_adapter)
    store = EvidenceStoreService()
    gateway = AcquisitionGateway(store)
    hitl_service = HITLWorkflowService(resolver, gateway, store)

    # Operator submits without providing required 'verified_iban'
    sub_req = HitlEvidenceSubmissionRequest(
        case_id="CASE-502",
        tenant_id="DEFAULT_BANK",
        profile_id="DQ-01",
        operator_id="OP-MAKER-01",
        operator_role="PAYMENT_OPERATOR",
        submitted_fields={"repair_notes": "Only wrote a note without IBAN"}
    )

    resp = hitl_service.process_operator_submission(
        submission=sub_req,
        transaction_context={"amount": 10000, "currency": "GBP"}
    )

    assert resp.is_accepted is False
    assert resp.new_status == "VALIDATION_FAILED"
    assert "Missing required field" in resp.message
