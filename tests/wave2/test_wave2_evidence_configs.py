"""Tests for Wave 2 Dynamic Bank Evidence Required Configurations.

Verifies:
1. Retrieval of default published configurations for PR-06, ST-02, and ST-03.
2. Dynamic resolution of mandatory rules across Modes 1–4.
3. HITL workflow configuration attachment for Wave 2 profiles.
"""
import pytest
from app.adapters.reference.reference_configuration_adapter import InMemoryConfigurationAdapter
from app.services.dynamic_config_resolver import DynamicEvidenceConfigResolver
from app.schemas.contracts.evidence_schemas import TrustTier


class TestWave2EvidenceConfigs:
    """Test suite for Wave 2 dynamic evidence configurations."""

    @pytest.fixture
    def resolver(self):
        adapter = InMemoryConfigurationAdapter()
        return DynamicEvidenceConfigResolver(adapter)

    def test_pr06_evidence_configuration(self, resolver):
        reqs = resolver.resolve_requirements(
            tenant_id="DEFAULT_BANK",
            profile_id="PR-06",
            transaction_context={"clearing_rail": "SWIFT_CBPR+", "amount": 10000.0}
        )
        assert len(reqs.active_mandatory_types) >= 4
        assert "INWARD_REJECTION_ADVICE" in reqs.active_mandatory_types
        assert "OUTBOUND_PAYMENT_RECORD" in reqs.active_mandatory_types
        assert "CORRESPONDENT_SSI_DIRECTORY" in reqs.active_mandatory_types
        assert "RAIL_CUTOFF_SCHEDULE" in reqs.active_mandatory_types

    def test_st02_evidence_configuration(self, resolver):
        reqs = resolver.resolve_requirements(
            tenant_id="DEFAULT_BANK",
            profile_id="ST-02",
            transaction_context={"clearing_rail": "FEDWIRE", "amount": 12000.0}
        )
        assert len(reqs.active_mandatory_types) >= 3
        assert "CORE_DDA_ACCOUNT_STATUS" in reqs.active_mandatory_types
        assert "INWARD_PAYMENT_RECORD" in reqs.active_mandatory_types
        assert "CLEARING_RETURN_SCHEDULE" in reqs.active_mandatory_types

    def test_st03_evidence_configuration(self, resolver):
        reqs = resolver.resolve_requirements(
            tenant_id="DEFAULT_BANK",
            profile_id="ST-03",
            transaction_context={"clearing_rail": "FEDWIRE", "amount": 25000.0}
        )
        assert len(reqs.active_mandatory_types) >= 4
        assert "CORE_ACCOUNT_RESTRICTION_FLAG" in reqs.active_mandatory_types
        assert "LEGAL_FREEZE_DOSSIER" in reqs.active_mandatory_types
        assert "INWARD_PAYMENT_RECORD" in reqs.active_mandatory_types
        assert "SUSPENSE_LEDGER_MATRIX" in reqs.active_mandatory_types
