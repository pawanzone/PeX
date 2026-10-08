"""Tests for DynamicEvidenceConfigResolver and Configuration Port integration."""
import pytest
from app.adapters.reference.reference_configuration_adapter import InMemoryConfigurationAdapter
from app.services.dynamic_config_resolver import DynamicEvidenceConfigResolver
from app.schemas.contracts.evidence_config_schemas import (
    BankEvidenceRequiredConfig,
    EvidenceRuleDefinition,
    EvidenceAcquisitionMode,
)
from app.schemas.contracts.evidence_schemas import TrustTier


def test_resolve_default_bank_config():
    config_adapter = InMemoryConfigurationAdapter()
    resolver = DynamicEvidenceConfigResolver(config_adapter)

    # Resolve DQ-01 for DEFAULT_BANK
    res = resolver.resolve_requirements(
        tenant_id="DEFAULT_BANK",
        profile_id="DQ-01",
        transaction_context={"amount": 50000, "currency": "USD"}
    )
    assert res.tenant_id == "DEFAULT_BANK"
    assert res.profile_id == "DQ-01"
    assert "CORE_DDA_ACCOUNT" in res.active_mandatory_types
    assert "ROUTING_DIRECTORY" in res.active_mandatory_types
    assert res.min_trust_tiers["CORE_DDA_ACCOUNT"] == TrustTier.TIER_1_CORE_RECORD


def test_tenant_override_resolution():
    config_adapter = InMemoryConfigurationAdapter()
    # Publish custom configuration for JPMC requiring an extra compliance certificate
    custom_cfg = BankEvidenceRequiredConfig(
        tenant_id="JPMC",
        profile_id="DQ-01",
        config_version="2.0.0",
        rules=[
            EvidenceRuleDefinition(
                rule_id="JPMC-R1",
                evidence_type="CORE_DDA_ACCOUNT",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_1_CORE_RECORD
            ),
            EvidenceRuleDefinition(
                rule_id="JPMC-R2",
                evidence_type="ROUTING_DIRECTORY",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME
            ),
            EvidenceRuleDefinition(
                rule_id="JPMC-R3",
                evidence_type="JPMC_CLIENT_AUTHORIZATION_TOKEN",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_1_CORE_RECORD
            )
        ]
    )
    config_adapter.publish_evidence_config(custom_cfg)

    resolver = DynamicEvidenceConfigResolver(config_adapter)

    # Resolve for JPMC
    jpmc_res = resolver.resolve_requirements(
        tenant_id="JPMC",
        profile_id="DQ-01",
        transaction_context={"amount": 50000, "currency": "USD"}
    )
    assert jpmc_res.tenant_id == "JPMC"
    assert len(jpmc_res.active_mandatory_types) == 3
    assert "JPMC_CLIENT_AUTHORIZATION_TOKEN" in jpmc_res.active_mandatory_types

    # Resolve for DEFAULT_BANK should remain 2 items (isolation proof)
    default_res = resolver.resolve_requirements(
        tenant_id="DEFAULT_BANK",
        profile_id="DQ-01",
        transaction_context={"amount": 50000, "currency": "USD"}
    )
    assert default_res.tenant_id == "DEFAULT_BANK"
    assert len(default_res.active_mandatory_types) == 2


def test_conditional_rule_activation_by_amount():
    config_adapter = InMemoryConfigurationAdapter()
    # Publish configuration with conditional rule for high-value transactions
    custom_cfg = BankEvidenceRequiredConfig(
        tenant_id="BNP_PARIBAS",
        profile_id="DQ-01",
        config_version="1.1.0",
        rules=[
            EvidenceRuleDefinition(
                rule_id="BNP-R1",
                evidence_type="CORE_DDA_ACCOUNT",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_1_CORE_RECORD
            ),
            EvidenceRuleDefinition(
                rule_id="BNP-R2",
                evidence_type="HIGH_VALUE_TREASURY_CLEARANCE",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                condition_expression="amount > 100000"
            )
        ]
    )
    config_adapter.publish_evidence_config(custom_cfg)
    resolver = DynamicEvidenceConfigResolver(config_adapter)

    # Case 1: Low value transaction ($50k) - conditional rule should NOT be active
    res_low = resolver.resolve_requirements(
        tenant_id="BNP_PARIBAS",
        profile_id="DQ-01",
        transaction_context={"amount": 50000, "currency": "EUR"}
    )
    assert "CORE_DDA_ACCOUNT" in res_low.active_mandatory_types
    assert "HIGH_VALUE_TREASURY_CLEARANCE" not in res_low.active_mandatory_types

    # Case 2: High value transaction ($250k) - conditional rule SHOULD be active
    res_high = resolver.resolve_requirements(
        tenant_id="BNP_PARIBAS",
        profile_id="DQ-01",
        transaction_context={"amount": 250000, "currency": "EUR"}
    )
    assert "CORE_DDA_ACCOUNT" in res_high.active_mandatory_types
    assert "HIGH_VALUE_TREASURY_CLEARANCE" in res_high.active_mandatory_types
