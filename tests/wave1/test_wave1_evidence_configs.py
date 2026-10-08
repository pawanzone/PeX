"""Evidence Configuration and Governance Compiler Tests for Wave 1.

Validates that all 9 Wave 1 profiles have valid published Evidence Required JSON configurations,
pass GovernanceCompiler validation, and resolve dynamically via DynamicEvidenceConfigResolver.
"""
import pytest
from app.adapters.reference.reference_configuration_adapter import InMemoryConfigurationAdapter
from app.services.governance_compiler import GovernanceCompiler
from app.services.dynamic_config_resolver import DynamicEvidenceConfigResolver


class TestWave1EvidenceConfigs:
    """Verifies that all 9 Wave 1 published configurations pass governance validation."""

    WAVE1_PROFILES = [
        "DQ-03",
        "DQ-04",
        "DQ-07",
        "DQ-09",
        "PR-02",
        "PR-04",
        "PR-07",
        "PR-09",
        "CO-07"
    ]

    def test_all_wave1_configs_pass_governance_compiler(self):
        adapter = InMemoryConfigurationAdapter()
        for p in self.WAVE1_PROFILES:
            cfg = adapter.get_evidence_config("DEFAULT_BANK", p)
            assert cfg is not None, f"Missing published config for {p}"
            is_valid, warnings = GovernanceCompiler.compile_and_validate(cfg)
            assert is_valid is True, f"Governance validation failed for {p}"

    def test_dynamic_resolver_evaluates_wave1_profiles(self):
        adapter = InMemoryConfigurationAdapter()
        resolver = DynamicEvidenceConfigResolver(adapter)
        for p in self.WAVE1_PROFILES:
            resolved = resolver.resolve_requirements(
                tenant_id="DEFAULT_BANK",
                profile_id=p,
                transaction_context={"amount": 10000.0, "currency": "USD"}
            )
            assert len(resolved.active_mandatory_types) >= 1, f"No mandatory types for {p}"
            assert resolved.profile_id == p
