"""Unit Tests for ComplianceDossierEngine (ST-03 Supporting).

Verifies:
1. Legal freeze dossier parsing and validation across court orders, injunctions, and tax levies.
2. Conflicting judicial orders fail closed to Compliance Officer in HITL.
3. Statutory sanctions blocks are strictly detected and diverted to CO-01.
"""
import pytest
from datetime import date
from app.services.engines.compliance_dossier_engine import ComplianceDossierEngine
from app.adapters.reference.reference_legal_registry_adapter import InMemoryLegalRegistryAdapter
from app.schemas.contracts.wave2_schemas import (
    LegalFreezeDossierRecord,
    LegalFreezeType,
)


@pytest.fixture
def engine():
    return ComplianceDossierEngine()


class TestComplianceDossierEngine:
    """Unit tests for ComplianceDossierEngine."""

    def test_evaluate_valid_court_injunction_dossier(self, engine):
        is_valid, dossier, diffs, err = engine.evaluate_legal_freeze_dossier("33445566")
        assert is_valid is True
        assert dossier is not None
        assert dossier.dossier_id == "DOS-2026-NY-9912"
        assert dossier.freeze_type == LegalFreezeType.COURT_INJUNCTION
        assert err is None

    def test_evaluate_conflicting_orders_fails_closed(self, engine):
        is_valid, dossier, diffs, err = engine.evaluate_legal_freeze_dossier(
            account_number="33445566",
            evidence_context={"conflicting_legal_orders": True}
        )
        assert is_valid is False
        assert dossier is None
        assert "conflicting" in err.lower()

    def test_evaluate_statutory_sanctions_diverts_to_co01(self, engine):
        is_valid, dossier, diffs, err = engine.evaluate_legal_freeze_dossier(
            account_number="33445566",
            evidence_context={"is_statutory_sanctions": True}
        )
        assert is_valid is False
        assert dossier is None
        assert "co-01" in err.lower()

    def test_evaluate_missing_dossier_fails_closed(self, engine):
        is_valid, dossier, diffs, err = engine.evaluate_legal_freeze_dossier("00000000")
        assert is_valid is False
        assert dossier is None
        assert "missing" in err.lower()
