"""Tests for GovernanceCompiler fail-closed validation."""
import pytest
from app.schemas.contracts.evidence_config_schemas import (
    BankEvidenceRequiredConfig,
    EvidenceRuleDefinition,
    EvidenceAcquisitionMode,
)
from app.schemas.contracts.evidence_schemas import TrustTier
from app.services.governance_compiler import GovernanceCompiler, GovernanceValidationError


def test_valid_bank_config_compilation():
    config = BankEvidenceRequiredConfig(
        tenant_id="CITI_CORP",
        profile_id="DQ-01",
        config_version="1.0.0",
        rules=[
            EvidenceRuleDefinition(
                rule_id="R1",
                evidence_type="CORE_DDA_ACCOUNT",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_1_CORE_RECORD
            ),
            EvidenceRuleDefinition(
                rule_id="R2",
                evidence_type="ROUTING_DIRECTORY",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME
            )
        ]
    )
    is_valid, warnings = GovernanceCompiler.compile_and_validate(config)
    assert is_valid is True
    assert len(warnings) == 0


def test_reject_missing_mandatory_sanctions_watchlist_in_co04():
    # Attempt to configure CO-04 without mandatory SANCTIONS_WATCHLIST
    config = BankEvidenceRequiredConfig(
        tenant_id="BANK_A",
        profile_id="CO-04",
        config_version="1.0.0",
        rules=[
            EvidenceRuleDefinition(
                rule_id="R1",
                evidence_type="CORRIDOR_POLICY_MATRIX",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME
            )
        ]
    )
    with pytest.raises(GovernanceValidationError) as exc:
        GovernanceCompiler.compile_and_validate(config)
    assert "REJECT_REGULATORY_RULE_DOWNGRADE" in str(exc.value)


def test_reject_downgrade_of_sanctions_mandatory_flag():
    # Attempt to mark SANCTIONS_WATCHLIST as mandatory=False
    config = BankEvidenceRequiredConfig(
        tenant_id="BANK_A",
        profile_id="CO-04",
        config_version="1.0.0",
        rules=[
            EvidenceRuleDefinition(
                rule_id="R1",
                evidence_type="SANCTIONS_WATCHLIST",
                mandatory=False,
                min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME
            )
        ]
    )
    with pytest.raises(GovernanceValidationError) as exc:
        GovernanceCompiler.compile_and_validate(config)
    assert "REJECT_REGULATORY_RULE_DOWNGRADE" in str(exc.value)


def test_reject_downgrade_of_sanctions_trust_tier():
    # Attempt to set min_trust_tier to Tier 4 (AI advisory) for Sanctions
    config = BankEvidenceRequiredConfig(
        tenant_id="BANK_A",
        profile_id="CO-04",
        config_version="1.0.0",
        rules=[
            EvidenceRuleDefinition(
                rule_id="R1",
                evidence_type="SANCTIONS_WATCHLIST",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_4_HISTORICAL_AI
            )
        ]
    )
    with pytest.raises(GovernanceValidationError) as exc:
        GovernanceCompiler.compile_and_validate(config)
    assert "REJECT_REGULATORY_TRUST_TIER_DOWNGRADE" in str(exc.value)


def test_reject_duplicate_evidence_types():
    config = BankEvidenceRequiredConfig(
        tenant_id="BANK_A",
        profile_id="DQ-01",
        config_version="1.0.0",
        rules=[
            EvidenceRuleDefinition(rule_id="R1", evidence_type="CORE_DDA_ACCOUNT", mandatory=True),
            EvidenceRuleDefinition(rule_id="R2", evidence_type="CORE_DDA_ACCOUNT", mandatory=True),
        ]
    )
    with pytest.raises(GovernanceValidationError) as exc:
        GovernanceCompiler.compile_and_validate(config)
    assert "ERR_DUPLICATE_EVIDENCE_TYPE" in str(exc.value)


def test_reject_unknown_context_variable_in_condition():
    config = BankEvidenceRequiredConfig(
        tenant_id="BANK_A",
        profile_id="DQ-01",
        config_version="1.0.0",
        rules=[
            EvidenceRuleDefinition(
                rule_id="R1",
                evidence_type="CORE_DDA_ACCOUNT",
                mandatory=True,
                condition_expression="unknown_custom_field == 'TEST'"
            ),
            EvidenceRuleDefinition(
                rule_id="R2",
                evidence_type="ROUTING_DIRECTORY",
                mandatory=True
            )
        ]
    )
    with pytest.raises(GovernanceValidationError) as exc:
        GovernanceCompiler.compile_and_validate(config)
    assert "ERR_UNKNOWN_CONTEXT_VARIABLE" in str(exc.value)
