"""Unit Tests for SettlementReconciliationEngine (PR-06, ST-02, ST-03).

Verifies:
1. PR-06 Intermediary Rejection resolution via alternate correspondent routing (Branch A) or outward return (Branch B).
2. Telemetry vs Rejection sovereign state separation (Network timeout != Intermediary Rejection).
3. Reusable return message compilation and suspense ledger booking.
4. Parameterized W2-BPD-01 reroute thresholds.
"""
import pytest
from app.services.engines.settlement_reconciliation_engine import SettlementReconciliationEngine
from app.schemas.contracts.policy_schemas import W2PolicyThresholds
from app.schemas.contracts.wave2_schemas import (
    IntermediaryRejectionAdvice,
    IntermediaryRejectionReasonCode,
)
from app.schemas.resolution_contract import ResolutionStatus, ResolutionUniqueness


@pytest.fixture
def engine():
    return SettlementReconciliationEngine()


class TestSettlementReconciliationEnginePR06:
    """Unit tests for PR-06: Intermediary Bank Rejection."""

    def test_pr06_happy_path_alternate_reroute(self, engine):
        policy = W2PolicyThresholds(max_auto_reroute_amount=50000.0, allow_auto_reroute=True)
        status, uniq, cand, diffs, err = engine.resolve_pr06_intermediary_rejection(
            uetr="UETR-PR06-001",
            payment_id="PMT-PR06-001",
            amount=15000.0,
            currency="USD",
            debtor_agent_bic="BNPAFRPPXXX",
            creditor_agent_bic="DEUTDEDDXXX",
            original_intermediary_bic="BNPAFRPPXXX",
            policy_thresholds=policy,
            evidence_context={
                "rejection_reference": "REJ-2026-PR06-001",
                "verified_alternate_intermediary_bic": "CHASUS33XXX"
            }
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
        assert cand is not None
        assert cand.repaired_structured["intermediary_agent_bic"] == "CHASUS33XXX"
        assert cand.repaired_structured["resolution_action"] == "REROUTE_VIA_ALTERNATE_CORRESPONDENT"
        assert err is None

    def test_pr06_telemetry_only_rejected_fail_closed(self, engine):
        """Telemetry error alone (socket drop) does not prove sovereign intermediary rejection."""
        status, uniq, cand, diffs, err = engine.resolve_pr06_intermediary_rejection(
            uetr="UETR-PR06-TEL",
            payment_id="PMT-PR06-TEL",
            amount=15000.0,
            currency="USD",
            debtor_agent_bic="CHASUS33XXX",
            creditor_agent_bic="DEUTDEDDXXX",
            evidence_context={"rejection_reference": "REJ-2026-PR06-TEL"}
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert cand is None
        assert "telemetry" in err.lower()

    def test_pr06_unmapped_narrative_routes_to_hitl(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_pr06_intermediary_rejection(
            uetr="UETR-PR06-NARR",
            payment_id="PMT-PR06-NARR",
            amount=15000.0,
            currency="USD",
            debtor_agent_bic="CHASUS33XXX",
            creditor_agent_bic="DEUTDEDDXXX",
            evidence_context={
                "unmapped_narrative": True,
                "rejection_advice": {
                    "rejection_reference": "REJ-NARR-001",
                    "original_uetr": "UETR-PR06-NARR",
                    "original_payment_id": "PMT-PR06-NARR",
                    "rejecting_institution_bic": "CHASUS33XXX",
                    "rejection_code": "NARR",
                    "rejection_category": "NARRATIVE_UNMAPPED",
                    "narrative_text": "Special correspondent instruction required"
                }
            }
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_AMBIGUOUS
        assert "narrative" in err.lower()

    def test_pr06_amount_exceeds_w2_bpd01_threshold_fails_closed(self, engine):
        policy = W2PolicyThresholds(max_auto_reroute_amount=10000.0, allow_auto_reroute=True)
        status, uniq, cand, diffs, err = engine.resolve_pr06_intermediary_rejection(
            uetr="UETR-PR06-HIGH",
            payment_id="PMT-PR06-HIGH",
            amount=25000.0, # Exceeds $10k limit
            currency="USD",
            debtor_agent_bic="BNPAFRPPXXX",
            creditor_agent_bic="DEUTDEDDXXX",
            policy_thresholds=policy,
            evidence_context={
                "rejection_reference": "REJ-2026-PR06-001",
                "verified_alternate_intermediary_bic": "CHASUS33XXX"
            }
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert "reroute limit" in err.lower()

    def test_pr06_no_alternate_hop_compiles_outward_return(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_pr06_intermediary_rejection(
            uetr="UETR-PR06-NOALT",
            payment_id="PMT-PR06-NOALT",
            amount=5000.0,
            currency="USD",
            debtor_agent_bic="BNPAFRPPXXX",
            creditor_agent_bic="DEUTDEDDXXX",
            evidence_context={
                "rejection_reference": "REJ-2026-PR06-001",
                "no_alternate_route_available": True
            }
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert cand is not None
        assert cand.repaired_structured["return_reason_code"] == "RC01"
        assert "RETURN" in cand.derivation_method


class TestSettlementReconciliationReusableCapabilities:
    """Tests for reusable return packaging and suspense break construction."""

    def test_compile_return_package_validity(self, engine):
        pkg = engine.compile_return_package(
            uetr="UETR-RET-TEST",
            original_payment_id="PMT-RET-TEST",
            amount=10000.0,
            currency="USD",
            return_reason_code="AC04",
            clearing_rail="FEDWIRE",
            narrative="Account closed in Core DDA."
        )
        assert pkg.return_id.startswith("RET-FEDWIRE")
        assert pkg.return_amount == 10000.0
        assert pkg.return_reason_code == "AC04"
        assert pkg.is_fully_balanced is True

    def test_compile_legal_suspense_booking_validity(self, engine):
        rec = engine.compile_legal_suspense_booking(
            uetr="UETR-SUSP-TEST",
            amount=25000.0,
            currency="USD",
            suspense_gl_account="GL-2180-LEGAL-SUSPENSE-ESCROW",
            escrow_reference_case="State v. Target Entity LLC"
        )
        assert rec.break_id.startswith("BRK-GL")
        assert rec.amount == 25000.0
        assert rec.is_balanced is True
        assert rec.journal_debit_entry["amount"] == 25000.0
        assert rec.journal_credit_entry["amount"] == 25000.0
