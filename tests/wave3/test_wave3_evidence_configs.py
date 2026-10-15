"""Tests for Wave 3 Dynamic Evidence Configurations and Sufficiency Evaluation."""
import pytest
from app.adapters.reference.reference_configuration_adapter import InMemoryConfigurationAdapter
from app.services.dynamic_config_resolver import DynamicEvidenceConfigResolver


@pytest.fixture
def resolver():
    config_adapter = InMemoryConfigurationAdapter()
    return DynamicEvidenceConfigResolver(config_adapter)


def test_wave3_evidence_config_tr02(resolver):
    reqs = resolver.resolve_requirements(
        tenant_id="DEFAULT_BANK",
        profile_id="TR-02",
        transaction_context={"amount": 5000.0, "currency": "USD"}
    )
    assert reqs is not None
    assert "CORE_DDA_BALANCE_RECORD" in reqs.active_mandatory_types
    assert "INTRADAY_RESERVATION_SCHEDULE" in reqs.active_mandatory_types


def test_wave3_evidence_config_tr03(resolver):
    reqs = resolver.resolve_requirements(
        tenant_id="DEFAULT_BANK",
        profile_id="TR-03",
        transaction_context={"amount": 10000.0, "currency": "EUR"}
    )
    assert reqs is not None
    assert "NOSTRO_POSITION_STATEMENT" in reqs.active_mandatory_types
    assert "PENDING_CORRESPONDENT_CREDITS" in reqs.active_mandatory_types


def test_wave3_evidence_config_tr04(resolver):
    reqs = resolver.resolve_requirements(
        tenant_id="DEFAULT_BANK",
        profile_id="TR-04",
        transaction_context={"amount": 7500.0, "currency": "EUR"}
    )
    assert reqs is not None
    assert "OFFICIAL_FX_RATE_FEED" in reqs.active_mandatory_types
    assert "FX_SPREAD_POLICY_MATRIX" in reqs.active_mandatory_types


def test_wave3_evidence_config_tr06(resolver):
    reqs = resolver.resolve_requirements(
        tenant_id="DEFAULT_BANK",
        profile_id="TR-06",
        transaction_context={"amount": 9000.0, "currency": "USD"}
    )
    assert reqs is not None
    assert "LIMIT_UTILIZATION_RECORD" in reqs.active_mandatory_types
    assert "CLIENT_LIMIT_AGREEMENT" in reqs.active_mandatory_types


def test_wave3_evidence_config_tr07(resolver):
    reqs = resolver.resolve_requirements(
        tenant_id="DEFAULT_BANK",
        profile_id="TR-07",
        transaction_context={"amount": 9500.0, "currency": "USD"}
    )
    assert reqs is not None
    assert "CLEARING_LIQUIDITY_RESERVE" in reqs.active_mandatory_types
    assert "SETTLEMENT_QUEUE_STATUS" in reqs.active_mandatory_types


def test_wave3_evidence_config_tr08(resolver):
    reqs = resolver.resolve_requirements(
        tenant_id="DEFAULT_BANK",
        profile_id="TR-08",
        transaction_context={"amount": 750000.0, "currency": "USD"}
    )
    assert reqs is not None
    assert "COUNTERPARTY_EXPOSURE_RECORD" in reqs.active_mandatory_types
    assert "CREDIT_FACILITY_AGREEMENT" in reqs.active_mandatory_types
    assert "ENTERPRISE_RISK_RATING" in reqs.active_mandatory_types
