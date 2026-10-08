"""Unit Tests for RoutingClearingEngine (PR-02, PR-04, PR-07, PR-09).

Verifies routing path resolution, rail cutoff temporal recalculation,
safe retry idempotency bounds, and repair queue syntax validations.
"""
import pytest
from datetime import date, timedelta
from app.services.engines.routing_clearing_engine import RoutingClearingEngine
from app.schemas.contracts.policy_schemas import W1PolicyCutoffBuffer
from app.schemas.resolution_contract import ResolutionStatus, ResolutionUniqueness


@pytest.fixture
def engine():
    return RoutingClearingEngine()


class TestRoutingClearingEnginePR02:
    """Tests for PR-02: Routing Failure."""

    def test_pr02_happy_path_route_resolution(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_pr02_routing_failure(
            debtor_agent_bic="BNPAFRPPXXX",
            creditor_agent_bic="CHASUS33XXX",
            currency="USD",
            clearing_rail="FEDWIRE"
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_UNIQUE
        assert cand is not None
        assert cand.repaired_structured["clearing_rail"] == "FEDWIRE"
        assert cand.repaired_structured["settlement_account"] == "FED-021000021-MAIN"

    def test_pr02_unreachable_bic_fails_closed(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_pr02_routing_failure(
            debtor_agent_bic="SANUESMMXXX",
            creditor_agent_bic="CORRUPTED_BIC",
            currency="EUR",
            clearing_rail="TARGET2"
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert cand is None
        assert err is not None

    def test_pr02_ambiguous_routes_routes_to_hitl(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_pr02_routing_failure(
            debtor_agent_bic="BNPAFRPPXXX",
            creditor_agent_bic="CHASUS33XXX",
            currency="USD",
            clearing_rail="FEDWIRE",
            evidence_context={"ambiguous_routing_paths": True}
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert uniq == ResolutionUniqueness.RESOLUTION_AMBIGUOUS


class TestRoutingClearingEnginePR04:
    """Tests for PR-04: Cutoff Missed."""

    def test_pr04_happy_path_value_date_roll(self, engine):
        policy = W1PolicyCutoffBuffer(cutoff_buffer_minutes=15, allow_auto_value_date_roll=True, max_value_date_roll_days=3)
        today = date(2026, 10, 8) # Thursday
        status, uniq, cand, diffs, err = engine.resolve_pr04_cutoff_missed(
            clearing_rail="FEDWIRE",
            currency="USD",
            current_value_date=today,
            policy_buffer=policy
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert cand is not None
        assert cand.repaired_structured["value_date"] == "2026-10-09" # Friday
        assert cand.repaired_structured["days_rolled"] == 1

    def test_pr04_weekend_value_date_skip(self, engine):
        policy = W1PolicyCutoffBuffer(cutoff_buffer_minutes=15, allow_auto_value_date_roll=True, max_value_date_roll_days=5)
        friday = date(2026, 10, 9) # Friday
        status, uniq, cand, diffs, err = engine.resolve_pr04_cutoff_missed(
            clearing_rail="FEDWIRE",
            currency="USD",
            current_value_date=friday,
            policy_buffer=policy
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        # Next operating day is Monday 2026-10-12
        assert cand.repaired_structured["value_date"] == "2026-10-12"
        assert cand.repaired_structured["days_rolled"] == 3

    def test_pr04_policy_prohibits_auto_roll(self, engine):
        policy = W1PolicyCutoffBuffer(allow_auto_value_date_roll=False)
        today = date(2026, 10, 8)
        status, uniq, cand, diffs, err = engine.resolve_pr04_cutoff_missed(
            clearing_rail="FEDWIRE",
            currency="USD",
            current_value_date=today,
            policy_buffer=policy
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert cand is None
        assert "prohibits" in err.lower() or "policy" in err.lower()


class TestRoutingClearingEnginePR07:
    """Tests for PR-07: Network Timeout."""

    def test_pr07_happy_path_safe_retry(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_pr07_network_timeout(
            payment_id="PMT-PR07-001",
            payment_uetr="9f1e2d3c-4b5a-6789-0123-abcdef070001",
            rail_code="FEDWIRE"
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert cand is not None
        assert cand.repaired_structured["action"] == "IDEMPOTENT_GATEWAY_RETRY"
        assert cand.repaired_structured["retry_attempt"] == 1

    def test_pr07_already_settled_prevents_duplicate(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_pr07_network_timeout(
            payment_id="PMT-PR07-002",
            payment_uetr="9f1e2d3c-4b5a-6789-0123-abcdef070002", # Confirmed settled
            rail_code="FEDWIRE"
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert cand is None
        assert "already settled" in err.lower()

    def test_pr07_retry_budget_exhausted_routes_to_hitl(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_pr07_network_timeout(
            payment_id="PMT-PR07-EXHAUSTED",
            payment_uetr="9f1e2d3c-4b5a-6789-0123-abcdef070003",
            rail_code="FEDWIRE"
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert cand is None
        assert "exhausted" in err.lower()


class TestRoutingClearingEnginePR09:
    """Tests for PR-09: Payment Held for Repair."""

    def test_pr09_happy_path_repair_validation(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_pr09_held_for_repair(
            payment_id="PMT-PR09-001",
            payment_uetr="9f1e2d3c-4b5a-6789-0123-abcdef090001"
        )
        assert status == ResolutionStatus.RESOLUTION_DETERMINED
        assert cand is not None
        assert "repaired_payload" in cand.repaired_structured or "repaired_fields" in cand.repaired_structured

    def test_pr09_unresolved_syntax_fails_closed(self, engine):
        status, uniq, cand, diffs, err = engine.resolve_pr09_held_for_repair(
            payment_id="PMT-PR09-001",
            payment_uetr="9f1e2d3c-4b5a-6789-0123-abcdef090001",
            evidence_context={"unresolved_syntax_error": True}
        )
        assert status == ResolutionStatus.RESOLUTION_NOT_DETERMINED
        assert cand is None
        assert "unresolved" in err.lower()
