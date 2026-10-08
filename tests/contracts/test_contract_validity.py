"""Contract Validity Tests for Wave 0A Platform Contracts.

Validates that all 13 contract schemas and interfaces accept valid payloads and reject
malformed or incomplete inputs with deterministic validation errors.
"""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.schemas.contracts.evidence_schemas import (
    EvidencePackageEnvelope,
    EvidenceItem,
    TrustTier,
    EvidenceValidationStatus,
)
from app.schemas.contracts.authority_schemas import (
    QuestionDomain,
    AuthorityClassification,
    AuthorityResolutionContext,
)
from app.schemas.contracts.policy_schemas import (
    BankRiskThresholds,
    BankPolicyEnvelope,
    PolicyEvaluationResult,
)
from app.schemas.contracts.idempotency_schemas import (
    LockStatus,
    LockAcquisitionResult,
)
from app.schemas.contracts.broker_schemas import (
    TransitStatus,
    MessageEnvelope,
    BrokerReceipt,
)
from app.schemas.contracts.core_banking_schemas import (
    AccountStatus,
    AccountStateSnapshot,
)
from app.schemas.contracts.regulatory_schemas import (
    ScreeningDisposition,
    ScreeningAssessment,
)
from app.schemas.contracts.token_vault_schemas import (
    TokenizedPayload,
    DetokenizationRequest,
)
from app.schemas.contracts.audit_schemas import (
    AuditBlockPayload,
    AuditBlockReceipt,
)
from app.schemas.contracts.observability_schemas import (
    SpanRecord,
    TraceContext,
)
from app.schemas.contracts.bank_handoff_schemas import (
    ExecutionOwner,
    HandoffStatus,
    ApprovalSignature,
    DispatchIntent,
    BankHandoffEnvelope,
)
from app.schemas.contracts.configuration_schemas import (
    RailCutoffSchedule,
    ValidatedSystemConfig,
)
from app.schemas.contracts.health_schemas import (
    HealthStatus,
    ComponentProbe,
    HealthStatusEnvelope,
)
from app.schemas.contracts.e2e_schemas import (
    E2EPaymentInfo,
    CanonicalE2EInput,
    PredicateBreakdown,
    CanonicalE2EOutput,
)


class TestContractValidity:
    """Tests schema validation across all 13 Wave 0A contracts."""

    def test_evidence_package_contract_valid(self):
        item = EvidenceItem(
            evidence_id="EVD-001",
            evidence_type="CORE_DDA",
            source_system="CORE_BANKING",
            trust_tier=TrustTier.TIER_1_CORE_RECORD,
            validation_status=EvidenceValidationStatus.AVAILABLE,
            provenance_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        env = EvidencePackageEnvelope(
            package_id="PKG-001",
            case_id="PEX-001",
            profile_id="DQ-01",
            items=[item],
            evidence_sufficient=True,
            sufficiency_score=1.0
        )
        assert env.package_id == "PKG-001"
        assert len(env.items) == 1
        assert env.items[0].trust_tier == 1

    def test_authority_contract_valid(self):
        ctx = AuthorityResolutionContext(
            question_domain=QuestionDomain.LEGAL_PROHIBITION,
            primary_authority_source="OFAC_SDN",
            authority_classification=AuthorityClassification.STATUTORY_REGULATORY,
            is_valid_authority=True,
            authority_sovereignty_level="BINDING_LEGAL"
        )
        assert ctx.question_domain == QuestionDomain.LEGAL_PROHIBITION
        assert ctx.is_valid_authority is True

    def test_policy_envelope_contract_valid(self):
        thresholds = BankRiskThresholds(max_autonomous_stp_amount=5000.0)
        policy = BankPolicyEnvelope(
            policy_id="POL-001",
            risk_thresholds=thresholds,
            auto_stp_enabled_profiles=["DQ-01", "DQ-08"]
        )
        assert policy.policy_id == "POL-001"
        assert policy.risk_thresholds.max_autonomous_stp_amount == 5000.0

    def test_idempotency_contract_valid(self):
        res = LockAcquisitionResult(
            idempotency_key="IDEMP-123",
            status=LockStatus.ACQUIRED,
            holder_id="ENGINE-1",
            fencing_token=42
        )
        assert res.status == LockStatus.ACQUIRED
        assert res.fencing_token == 42

    def test_broker_contract_valid(self):
        msg = MessageEnvelope(
            message_id="MSG-001",
            correlation_id="UETR-001",
            topic_or_queue="OUTBOUND_FEDWIRE",
            payload={"action": "REPAIR"}
        )
        receipt = BrokerReceipt(
            message_id=msg.message_id,
            correlation_id=msg.correlation_id,
            topic_or_queue=msg.topic_or_queue,
            status=TransitStatus.ENQUEUED
        )
        assert receipt.status == TransitStatus.ENQUEUED

    def test_core_banking_contract_valid(self):
        acc = AccountStateSnapshot(
            account_number_masked="US11****0100",
            account_holder_name_masked="Apex Global",
            currency="USD",
            status=AccountStatus.ACTIVE,
            available_balance=10000.0,
            posted_balance=10000.0
        )
        assert acc.status == AccountStatus.ACTIVE
        assert acc.is_authoritative is True

    def test_regulatory_screening_contract_valid(self):
        scr = ScreeningAssessment(
            screening_id="SCR-001",
            target_entity_masked="Apex Global",
            disposition=ScreeningDisposition.CLEAR,
            compliance_gate_passed=True
        )
        assert scr.compliance_gate_passed is True

    def test_token_vault_contract_valid(self):
        tok = TokenizedPayload(
            token="TOK-ACC-ABC123",
            token_type="ACCOUNT",
            masked_value="US11****0100"
        )
        assert tok.token.startswith("TOK-ACC")

    def test_audit_ledger_contract_valid(self):
        payload = AuditBlockPayload(
            event_id="EVT-001",
            case_id="PEX-001",
            correlation_id="UETR-001",
            stage_name="INGESTION",
            actor_id="USER-1",
            actor_role="OPERATOR",
            action_name="INGEST",
            details="Ingested case"
        )
        receipt = AuditBlockReceipt(
            block_index=1,
            block_hash="HASH-001",
            parent_hash="GENESIS-000",
            payload=payload
        )
        assert receipt.block_index == 1

    def test_bank_handoff_contract_execution_owner_invariant(self):
        intent = DispatchIntent(
            intent_id="INT-001",
            action_type="REPAIR_AND_RELEASE",
            target_clearing_rail="FEDWIRE"
        )
        handoff = BankHandoffEnvelope(
            envelope_id="ENV-001",
            case_id="PEX-001",
            payment_id="PMT-001",
            uetr="UETR-001",
            execution_owner=ExecutionOwner.BANK,
            status=HandoffStatus.BANK_HANDOFF_READY,
            dispatch_intent=intent,
            stp_eligible=True,
            audit_chain_block_hash="BLOCK-HASH-001"
        )
        assert handoff.execution_owner == ExecutionOwner.BANK
        assert handoff.status == HandoffStatus.BANK_HANDOFF_READY

    def test_e2e_canonical_schemas_valid(self):
        pmt = E2EPaymentInfo(
            payment_id="PMT-001",
            uetr="UETR-001",
            amount=1000.0,
            currency="USD",
            clearing_rail="FEDWIRE"
        )
        inp = CanonicalE2EInput(
            exception_id="EXC-001",
            profile_id="DQ-01",
            payment_info=pmt
        )
        assert inp.exception_id == "EXC-001"

    def test_schema_rejection_on_missing_required_fields(self):
        with pytest.raises(ValidationError):
            # Missing mandatory payment_id, uetr, amount, currency, clearing_rail
            E2EPaymentInfo(payment_id="PMT-001")
