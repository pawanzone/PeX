"""Fail-Closed Behavior Contract Tests for Wave 0A.

Verifies that any failure mode (missing evidence, missing policy, unavailable authority,
stale data, contradictory evidence, screening hit) deterministically fails closed to NO STP.
"""
import pytest

from app.schemas.contracts.authority_schemas import QuestionDomain
from app.schemas.contracts.policy_schemas import BankPolicyEnvelope, BankRiskThresholds
from app.schemas.contracts.evidence_schemas import EvidenceValidationStatus
from app.adapters.reference.reference_evidence_adapter import InMemoryEvidenceAdapter
from app.adapters.reference.reference_authority_adapter import InMemoryContextualAuthorityAdapter
from app.adapters.reference.reference_policy_adapter import InMemoryBankPolicyAdapter
from app.adapters.reference.reference_regulatory_adapter import InMemoryRegulatoryScreeningAdapter
from app.services.e2e_runner import E2EExecutionHarness


class TestFailClosedBehavior:
    """Tests deterministic fail-closed safety invariants."""

    def test_missing_mandatory_evidence_fails_closed(self):
        adapter = InMemoryEvidenceAdapter()
        envelope = adapter.acquire_evidence("PEX-FAIL-01", "DQ-01", {"amount": 1000.0}, {})
        envelope = adapter.evaluate_sufficiency(envelope, mandatory_types=["CORE_DDA_ACCOUNT", "ROUTING_DIRECTORY"])
        
        assert envelope.evidence_sufficient is False
        assert "CORE_DDA_ACCOUNT" in envelope.missing_mandatory_types
        assert "ROUTING_DIRECTORY" in envelope.missing_mandatory_types

    def test_stale_evidence_fails_closed(self):
        adapter = InMemoryEvidenceAdapter()
        ctx = {
            "core_dda_account": "GB29MIDL40051512345679",
            "core_dda_account_stale": True
        }
        envelope = adapter.acquire_evidence("PEX-FAIL-02", "DQ-01", {"amount": 1000.0}, ctx)
        envelope = adapter.evaluate_sufficiency(envelope, mandatory_types=["CORE_DDA_ACCOUNT"])

        assert envelope.evidence_sufficient is False
        assert "CORE_DDA_ACCOUNT" in envelope.stale_types

    def test_contradictory_evidence_fails_closed(self):
        adapter = InMemoryEvidenceAdapter()
        ctx = {
            "core_dda_account": "GB29MIDL40051512345679",
            "core_dda_account_contradictory": True
        }
        envelope = adapter.acquire_evidence("PEX-FAIL-03", "DQ-01", {"amount": 1000.0}, ctx)
        envelope = adapter.evaluate_sufficiency(envelope, mandatory_types=["CORE_DDA_ACCOUNT"])

        assert envelope.evidence_sufficient is False
        assert "CORE_DDA_ACCOUNT" in envelope.contradictions

    def test_missing_bank_policy_fails_closed(self):
        adapter = InMemoryBankPolicyAdapter()
        # Set policy to None (missing/unconfigured)
        adapter.set_policy(None)
        
        result = adapter.evaluate_transaction(
            policy=None,
            profile_id="DQ-01",
            amount=500.0,
            currency="USD",
            action_type="REPAIR_AND_RELEASE"
        )
        assert result.policy_allows_action is False
        assert result.is_autonomous_stp_permitted is False
        assert "Mandatory BankPolicyEnvelope is missing" in result.denial_reasons[0]

    def test_authority_unavailable_fails_closed(self):
        adapter = InMemoryContextualAuthorityAdapter()
        res = adapter.resolve_authority(
            question_domain=QuestionDomain.ACCOUNT_OWNERSHIP_BALANCE,
            context_payload={"simulate_authority_unavailable": True}
        )
        assert res.is_valid_authority is False
        assert res.authority_sovereignty_level == "UNAVAILABLE"

    def test_regulatory_sanctions_hit_fails_closed(self):
        adapter = InMemoryRegulatoryScreeningAdapter()
        res = adapter.screen_entity(entity_name="SANCTIONED_ENTERPRISE_LTD", country="US")
        
        assert res.compliance_gate_passed is False
        assert res.requires_mandatory_legal_hold is True

    def test_e2e_harness_fails_closed_when_any_predicate_false(self):
        harness = E2EExecutionHarness()
        # Fixture with missing mandatory evidence
        res = harness.process_input("e2e_fixtures/input/DQ-01_invalid_iban_missing_evidence.json")
        
        assert res.stp_eligible is False
        assert res.predicate_breakdown.e_suff is False
        assert res.hitl_required is True
        assert res.bank_handoff_status != "BANK_HANDOFF_READY" or res.hitl_required is True
        assert res.execution_owner == "BANK"
