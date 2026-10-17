"""End-to-End Dynamic Execution Tests for Wave 0B (Scenarios 13–18).

Validates dynamic configuration binding, multi-mode acquisition (Modes 1–4),
HITL closed loops, multi-tenant isolation, and fail-closed governance enforcement.
"""
import pytest
from app.services.e2e_runner import E2EExecutionHarness
from app.adapters.reference.reference_configuration_adapter import InMemoryConfigurationAdapter
from app.adapters.reference.reference_evidence_adapter import InMemoryEvidenceAdapter
from app.services.dynamic_config_resolver import DynamicEvidenceConfigResolver
from app.services.evidence_store import EvidenceStoreService
from app.services.acquisition_gateway import AcquisitionGateway
from app.services.hitl_workflow_service import HITLWorkflowService
from app.services.governance_compiler import GovernanceCompiler, GovernanceValidationError
from app.schemas.contracts.evidence_config_schemas import (
    BankEvidenceRequiredConfig,
    EvidenceRuleDefinition,
    EvidenceAcquisitionMode,
    HitlWorkflowConfig,
    HitlFieldDefinition,
    HitlFieldType,
    HitlEvidenceSubmissionRequest,
)
from app.schemas.contracts.evidence_schemas import TrustTier
from app.schemas.contracts.canonical_fixtures_wave0b import SCENARIOS_WAVE0B


def test_scenario_13_high_value_wire_dynamic_threshold():
    """Scenario 13: High-value wire ($250k) dynamically activates Tier 1 Account Statement requirement."""
    config_adapter = InMemoryConfigurationAdapter()
    
    # Configure BNP_PARIBAS with conditional high-value rule
    bnp_config = BankEvidenceRequiredConfig(
        tenant_id="BNP_PARIBAS",
        profile_id="DQ-01",
        config_version="1.0.0",
        rules=[
            EvidenceRuleDefinition(
                rule_id="BNP-R1",
                evidence_type="CORE_DDA_ACCOUNT",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_1_CORE_RECORD
            ),
            EvidenceRuleDefinition(
                rule_id="BNP-R2",
                evidence_type="ROUTING_DIRECTORY",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME
            ),
            EvidenceRuleDefinition(
                rule_id="BNP-R3",
                evidence_type="ACCOUNT_STATEMENT",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                condition_expression="amount > 100000"
            )
        ]
    )
    config_adapter.publish_evidence_config(bnp_config)

    harness = E2EExecutionHarness(config_port=config_adapter)
    fixture = SCENARIOS_WAVE0B["SCENARIO_13_HIGH_VALUE_WIRE_TIER1_STMT"]

    output = harness.process_input(fixture)

    assert output.exception_id == "EX-W0B-SC13-001"
    assert output.evidence_status == "SUFFICIENT"
    # P0.5: a $250k wire exceeds the unified STP amount limit, so evidence is sufficient but STP must NOT be granted
    assert output.stp_eligible is False
    assert output.resolution_status is not None
    assert output.execution_owner == "BANK"
    assert output.bank_handoff_status != "BANK_HANDOFF_READY"  # not handed off without STP
    assert output.predicate_breakdown.e_suff is True
    assert output.predicate_breakdown.r_det is True
    assert output.predicate_breakdown.p_bank is False
    assert output.predicate_breakdown.c_comp is True
    assert output.predicate_breakdown.x_pre is True


def test_scenario_14_corridor_regulatory_cert_mode3_push():
    """Scenario 14: Cross-border corridor EUR->BRL requires regulatory certificate supplied via Mode 3 Push."""
    config_adapter = InMemoryConfigurationAdapter()
    
    santander_config = BankEvidenceRequiredConfig(
        tenant_id="BANCO_SANTANDER",
        profile_id="DQ-06",
        config_version="1.0.0",
        rules=[
            EvidenceRuleDefinition(
                rule_id="SAN-R1",
                evidence_type="CORE_DDA_ACCOUNT",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_1_CORE_RECORD
            ),
            EvidenceRuleDefinition(
                rule_id="SAN-R2",
                evidence_type="REGULATORY_CERTIFICATE",
                mandatory=True,
                min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME
            )
        ]
    )
    config_adapter.publish_evidence_config(santander_config)

    harness = E2EExecutionHarness(config_port=config_adapter)
    fixture = dict(SCENARIOS_WAVE0B["SCENARIO_14_CORRIDOR_REGULATORY_CERT_PUSH"])

    # Pass 1: Missing REGULATORY_CERTIFICATE in initial payload
    output_pass1 = harness.process_input(fixture)
    assert output_pass1.evidence_status == "INSUFFICIENT"
    assert output_pass1.stp_eligible is False
    assert "REGULATORY_CERTIFICATE" in output_pass1.evidence_missing

    # Mode 3 Push: Bank pushes the regulatory certificate
    fixture["bank_supplied_evidence"]["regulatory_certificate"] = {
        "certificate_id": "BACEN-FX-2026-8819",
        "cleared": True
    }

    # Pass 2: Re-evaluation with Mode 3 certificate
    output_pass2 = harness.process_input(fixture)
    assert output_pass2.evidence_status == "SUFFICIENT"
    assert output_pass2.stp_eligible is True
    assert output_pass2.bank_handoff_status == "BANK_HANDOFF_READY"


def test_scenario_15_operator_iban_correction_hitl_closed_loop():
    """Scenario 15: Ambiguous routing requires operator clarification via HITL Mode 4."""
    config_adapter = InMemoryConfigurationAdapter()
    harness = E2EExecutionHarness(config_port=config_adapter)
    fixture = dict(SCENARIOS_WAVE0B["SCENARIO_15_OPERATOR_IBAN_CORRECTION_HITL"])

    # Pass 1: Ambiguous routing matches
    output_pass1 = harness.process_input(fixture)
    assert output_pass1.predicate_breakdown.r_uniq is False
    assert output_pass1.stp_eligible is False
    assert output_pass1.hitl_required is True

    # Mode 4: Operator disambiguates routing code
    fixture["bank_supplied_evidence"]["ambiguous_routing_matches"] = False
    fixture["bank_supplied_evidence"]["valid_routing_code"] = "021000021"

    # Pass 2: Re-evaluation after operator action
    output_pass2 = harness.process_input(fixture)
    assert output_pass2.predicate_breakdown.r_uniq is True
    assert output_pass2.resolution_status == "RESOLVED"
    assert output_pass2.stp_eligible is True
    assert output_pass2.bank_handoff_status == "BANK_HANDOFF_READY"


def test_scenario_16_duplicate_payment_mode2_automated():
    """Scenario 16: Duplicate payment detection and suppression with bank handoff."""
    config_adapter = InMemoryConfigurationAdapter()
    harness = E2EExecutionHarness(config_port=config_adapter)
    fixture = SCENARIOS_WAVE0B["SCENARIO_16_AUTOMATED_CORE_BANKING_MODE2"]

    output = harness.process_input(fixture)
    assert output.exception_id == "EX-W0B-SC16-001"
    assert output.evidence_status == "SUFFICIENT"
    assert output.stp_eligible is True
    assert output.resolution_status == "RESOLVED"
    assert output.resolution_recommendation["action"] == "SUPPRESS_DUPLICATE_AND_NOTIFY"
    assert output.execution_owner == "BANK"
    assert output.bank_handoff_status == "BANK_HANDOFF_READY"


def test_scenario_17_multi_tenant_isolation():
    """Scenario 17: Multi-tenant configuration isolation guarantees no cross-tenant rule leakage."""
    config_adapter = InMemoryConfigurationAdapter()
    
    # Tenant Alpha requires 3 items
    alpha_config = BankEvidenceRequiredConfig(
        tenant_id="TENANT_ALPHA",
        profile_id="DQ-01",
        config_version="1.0.0",
        rules=[
            EvidenceRuleDefinition(rule_id="A1", evidence_type="CORE_DDA_ACCOUNT", mandatory=True),
            EvidenceRuleDefinition(rule_id="A2", evidence_type="ROUTING_DIRECTORY", mandatory=True),
            EvidenceRuleDefinition(rule_id="A3", evidence_type="ALPHA_COMPLIANCE_PASS", mandatory=True)
        ]
    )
    # Tenant Beta requires default 2 items
    beta_config = BankEvidenceRequiredConfig(
        tenant_id="TENANT_BETA",
        profile_id="DQ-01",
        config_version="1.0.0",
        rules=[
            EvidenceRuleDefinition(rule_id="B1", evidence_type="CORE_DDA_ACCOUNT", mandatory=True),
            EvidenceRuleDefinition(rule_id="B2", evidence_type="ROUTING_DIRECTORY", mandatory=True)
        ]
    )
    config_adapter.publish_evidence_config(alpha_config)
    config_adapter.publish_evidence_config(beta_config)

    harness = E2EExecutionHarness(config_port=config_adapter)

    # Eval under Tenant Alpha (only 2 of 3 items present)
    alpha_fixture = dict(SCENARIOS_WAVE0B["SCENARIO_17_MULTI_TENANT_ISOLATION"])
    alpha_fixture["tenant_id"] = "TENANT_ALPHA"
    alpha_out = harness.process_input(alpha_fixture)
    assert alpha_out.evidence_status == "INSUFFICIENT"
    assert "ALPHA_COMPLIANCE_PASS" in alpha_out.evidence_missing

    # Eval under Tenant Beta (2 of 2 items present)
    beta_fixture = dict(SCENARIOS_WAVE0B["SCENARIO_17_MULTI_TENANT_ISOLATION"])
    beta_fixture["tenant_id"] = "TENANT_BETA"
    beta_out = harness.process_input(beta_fixture)
    assert beta_out.evidence_status == "SUFFICIENT"
    assert beta_out.stp_eligible is True


def test_scenario_18_governance_compiler_fail_closed():
    """Scenario 18: Erroneous candidate configuration attempting sanctions bypass is rejected fail-closed."""
    invalid_config = BankEvidenceRequiredConfig(
        tenant_id="MALICIOUS_BANK",
        profile_id="CO-04",
        config_version="1.0.0",
        rules=[
            EvidenceRuleDefinition(
                rule_id="R-SANCTIONS-WEAK",
                evidence_type="SANCTIONS_WATCHLIST",
                mandatory=False, # Illegal under PeX governance!
                min_trust_tier=TrustTier.TIER_4_HISTORICAL_AI
            )
        ]
    )
    with pytest.raises(GovernanceValidationError) as exc:
        GovernanceCompiler.compile_and_validate(invalid_config)
    
    assert "REJECT_REGULATORY_RULE_DOWNGRADE" in str(exc.value)
