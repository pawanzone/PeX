"""Tests for Wave 4 Evidence Configuration and Schema Contracts.

Validates that TR-01, TR-05, and ST-06 have published authoritative evidence configurations.
"""
import pytest
from app.adapters.reference.reference_configuration_adapter import InMemoryConfigurationAdapter
from app.schemas.contracts.evidence_schemas import TrustTier


def test_wave4_evidence_config_tr01():
    adapter = InMemoryConfigurationAdapter()
    cfg = adapter.get_evidence_config("DEFAULT_BANK", "TR-01")
    assert cfg is not None
    assert cfg.profile_id == "TR-01"

    rule_types = {r.evidence_type for r in cfg.rules}
    assert "CUSTOMER_KYC_RECORD" in rule_types
    assert "CORPORATE_STANDING_RECORD" in rule_types

    kyc_rule = next(r for r in cfg.rules if r.evidence_type == "CUSTOMER_KYC_RECORD")
    assert kyc_rule.mandatory is True
    assert kyc_rule.min_trust_tier == TrustTier.TIER_1_CORE_RECORD

    assert cfg.hitl_config is not None
    assert cfg.hitl_config.target_role == "COMPLIANCE_KYC_OFFICER"


def test_wave4_evidence_config_tr05():
    adapter = InMemoryConfigurationAdapter()
    cfg = adapter.get_evidence_config("DEFAULT_BANK", "TR-05")
    assert cfg is not None
    assert cfg.profile_id == "TR-05"

    rule_types = {r.evidence_type for r in cfg.rules}
    assert "CORPORATE_MANDATE_RECORD" in rule_types
    assert "SECONDARY_SIGNATORY_RECORD" in rule_types

    mandate_rule = next(r for r in cfg.rules if r.evidence_type == "CORPORATE_MANDATE_RECORD")
    assert mandate_rule.mandatory is True
    assert mandate_rule.min_trust_tier == TrustTier.TIER_1_CORE_RECORD

    assert cfg.hitl_config is not None
    assert cfg.hitl_config.target_role == "CORPORATE_MANDATE_OFFICER"


def test_wave4_evidence_config_st06():
    adapter = InMemoryConfigurationAdapter()
    cfg = adapter.get_evidence_config("DEFAULT_BANK", "ST-06")
    assert cfg is not None
    assert cfg.profile_id == "ST-06"

    rule_types = {r.evidence_type for r in cfg.rules}
    assert "TRACKER_HOP_RECORD" in rule_types
    assert "DEBIT_CONFIRMATION_RECORD" in rule_types

    hop_rule = next(r for r in cfg.rules if r.evidence_type == "TRACKER_HOP_RECORD")
    assert hop_rule.mandatory is True
    assert hop_rule.min_trust_tier == TrustTier.TIER_1_CORE_RECORD

    assert cfg.hitl_config is not None
    assert cfg.hitl_config.target_role == "CORRESPONDENT_INVESTIGATION_OPERATOR"
