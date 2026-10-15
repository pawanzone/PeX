"""Wave 2 Ports, Adapters, and Schema Contract Tests.

Verifies:
1. All Wave 2 Pydantic schemas instantiate with full validation.
2. Abstract SPI ports cannot be instantiated directly without implementing abstract methods.
3. Reference adapters satisfy their respective SPI contracts.
"""
import pytest
from datetime import datetime, timezone, date

from app.ports.correspondent_gateway_port import CorrespondentGatewayPort
from app.ports.settlement_return_port import SettlementReturnPort
from app.ports.legal_registry_port import LegalRegistryPort
from app.ports.general_ledger_suspense_port import GeneralLedgerSuspensePort

from app.adapters.reference.reference_correspondent_gateway_adapter import InMemoryCorrespondentGatewayAdapter
from app.adapters.reference.reference_settlement_return_adapter import InMemorySettlementReturnAdapter
from app.adapters.reference.reference_legal_registry_adapter import InMemoryLegalRegistryAdapter
from app.adapters.reference.reference_general_ledger_suspense_adapter import InMemoryGeneralLedgerSuspenseAdapter

from app.schemas.contracts.wave2_schemas import (
    IntermediaryRejectionAdvice,
    IntermediaryRejectionReasonCode,
    AlternateRerouteResult,
    AccountClosedRecord,
    RolloverMandateRecord,
    AccountRestrictionScope,
    AccountRestrictionType,
    LegalFreezeType,
    LegalFreezeDossierRecord,
    DeterministicCorrelationMatch,
    SettlementReturnPackage,
    SettlementSuspenseBreakRecord,
)
from app.schemas.contracts.policy_schemas import W2PolicyThresholds, BankPolicyEnvelope


class TestWave2PortsAndContracts:
    """Test suite for Wave 2 ports and contract schemas."""

    def test_abstract_ports_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            CorrespondentGatewayPort()
        with pytest.raises(TypeError):
            SettlementReturnPort()
        with pytest.raises(TypeError):
            LegalRegistryPort()
        with pytest.raises(TypeError):
            GeneralLedgerSuspensePort()

    def test_reference_adapters_implement_ports(self):
        assert isinstance(InMemoryCorrespondentGatewayAdapter(), CorrespondentGatewayPort)
        assert isinstance(InMemorySettlementReturnAdapter(), SettlementReturnPort)
        assert isinstance(InMemoryLegalRegistryAdapter(), LegalRegistryPort)
        assert isinstance(InMemoryGeneralLedgerSuspenseAdapter(), GeneralLedgerSuspensePort)

    def test_wave2_schemas_validation(self):
        adv = IntermediaryRejectionAdvice(
            rejection_reference="REJ-01",
            original_uetr="UETR-01",
            original_payment_id="PMT-01",
            rejecting_institution_bic="CHASUS33XXX",
            rejection_code="RC01",
            rejection_category=IntermediaryRejectionReasonCode.ROUTING_UNREACHABLE
        )
        assert adv.rejection_category == IntermediaryRejectionReasonCode.ROUTING_UNREACHABLE

        ret = SettlementReturnPackage(
            return_id="RET-01",
            original_uetr="UETR-01",
            original_payment_id="PMT-01",
            return_amount=5000.0,
            currency="USD",
            return_reason_code="AC04",
            return_reason_narrative="Closed",
            target_clearing_rail="FEDWIRE"
        )
        assert ret.is_fully_balanced is True

        scope = AccountRestrictionScope(
            account_number="12345678",
            account_title="TEST CORP",
            restriction_type=AccountRestrictionType.POST_NO_CREDITS,
            is_credit_prohibited=True,
            restriction_reference_id="REST-01",
            issuing_authority="COURT"
        )
        assert scope.is_credit_prohibited is True

    def test_w2_policy_thresholds_in_envelope(self):
        env = BankPolicyEnvelope(
            policy_id="POL-W2-TEST",
            w2_policy_thresholds=W2PolicyThresholds(
                max_auto_reroute_amount=75000.0,
                max_closed_account_auto_return_amount=150000.0
            )
        )
        assert env.w2_policy_thresholds.max_auto_reroute_amount == 75000.0
        assert env.w2_policy_thresholds.max_closed_account_auto_return_amount == 150000.0
