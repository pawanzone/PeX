"""Unit & Integration Tests for Governed Business Rules and ICD Registry."""
import pytest
from app.db.init_db import init_db
from app.services.data_loader import repo
from app.services.rule_engine import rule_engine
from app.schemas.rules import RuleCategory

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    repo.sync_from_db()

def test_rule_synthesis_dual_auth():
    prompt = "Anything more than $250,000 will go to 2-level approvals"
    syn = rule_engine.synthesize_rule(prompt)
    assert syn.category == RuleCategory.APPROVAL_GATING.value
    assert syn.conditions["logic"] == "AND"
    clauses = syn.conditions["clauses"]
    assert len(clauses) >= 1
    assert clauses[0]["field"] == "amount"
    assert clauses[0]["operator"] == ">="
    assert clauses[0]["value"] == 250000.0
    assert syn.actions.get("set_dual_auth_required") is True
    assert syn.actions.get("required_tiers") == 2

def test_rule_synthesis_fastlane():
    prompt = "Auto-qualify INVALID_IBAN under $25,000 with >95% confidence for 1-click fast-lane"
    syn = rule_engine.synthesize_rule(prompt)
    assert syn.category == RuleCategory.STP_FAST_LANE.value
    assert syn.actions.get("auto_qualify_fast_lane") is True
    fields = [c["field"] for c in syn.conditions["clauses"]]
    assert "amount" in fields
    assert "confidence" in fields or "profile" in fields

def test_rule_synthesis_routing():
    prompt = "Route EUR wires over €1M to Treasury Desk"
    syn = rule_engine.synthesize_rule(prompt)
    assert syn.category == RuleCategory.ROUTING.value
    assert syn.actions.get("target_queue") == "Treasury"
    fields = [c["field"] for c in syn.conditions["clauses"]]
    assert "amount" in fields
    assert "currency" in fields

def test_rule_simulation_live_cases():
    all_cases = list(repo._case_cache.values())
    rule_dict = {
        "domain": "ALL",
        "conditions": {
            "logic": "AND",
            "clauses": [{"field": "amount", "operator": ">=", "value": 250000.0}]
        },
        "actions": {"set_dual_auth_required": True}
    }
    sim = rule_engine.simulate_impact(rule_dict, all_cases)
    assert sim.total_cases_evaluated == len(all_cases)
    assert sim.matched_cases_count > 0
    assert sim.total_dollar_volume_affected > 0
    assert len(sim.sample_matched_cases) > 0

def test_maker_checker_rule_lifecycle():
    # 1. Maker submits rule
    rule_id = f"RULE-TEST-AUTHTEST-01"
    rule_data = {
        "rule_id": rule_id,
        "name": "Test High Value Policy",
        "natural_language_prompt": "Payments >= $1,000,000 need dual authorization",
        "category": "APPROVAL_GATING",
        "domain": "ALL",
        "conditions": {"logic": "AND", "clauses": [{"field": "amount", "operator": ">=", "value": 1000000.0}]},
        "actions": {"set_dual_auth_required": True, "required_tiers": 2},
        "status": "PENDING_APPROVAL",
        "maker_id": "OP-8821",
        "maker_name": "Priya Sharma",
        "maker_notes": "Test draft submission"
    }
    saved = repo.save_policy_rule(rule_data)
    assert saved["status"] == "PENDING_APPROVAL"
    assert saved["rule_id"] == rule_id

    # 2. Checker approves rule
    approved = repo.approve_policy_rule(
        rule_id=rule_id,
        checker_id="RSK-7714",
        checker_name="Kenji Watanabe",
        comments="Approved in test suite"
    )
    assert approved is not None
    assert approved["status"] == "ACTIVE"
    assert approved["checker_id"] == "RSK-7714"

    # 3. Verify in repository
    fetched = repo.get_policy_rule(rule_id)
    assert fetched["status"] == "ACTIVE"

def test_icd_registry_baseline():
    icds = repo.get_icd_configs()
    assert len(icds) >= 4
    bics = [icd["bic"] for icd in icds]
    assert "CHASUS33" in bics
    assert "DEUTDEDD" in bics
    assert "BARCGB22" in bics
