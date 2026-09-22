"""End-to-End tests for Multi-Hypothesis Disambiguation & Governed Rule Editing Workflow."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.data_loader import repo

client = TestClient(app)

def test_multi_hypothesis_ambiguity_and_disambiguation_e2e():
    """Verify boundary condition where 2 high-confidence hypotheses exist and human operator applies disambiguation."""
    from app.services.data_loader import build_rich_guided_recommendation
    from app.schemas.canonical import ExceptionProfile

    # 1. Fetch cases to locate a BENEFICIARY_NAME_MISMATCH case
    cases_resp = client.get("/api/cases")
    assert cases_resp.status_code == 200
    cases = cases_resp.json()
    
    ben_case = next((c for c in cases if c.get("profile") == "BENEFICIARY_NAME_MISMATCH"), None)
    assert ben_case is not None, "BENEFICIARY_NAME_MISMATCH case must exist"
    case_id = ben_case["case_id"]

    # Reset recommendation to initial multi-candidate state for test repeatability
    clean_rec = build_rich_guided_recommendation(
        case_id=case_id,
        profile=ExceptionProfile.BENEFICIARY_NAME_MISMATCH,
        amount=ben_case.get("amount", 75000.0),
        creditor_name="Nordhavn Components A/S",
        creditor_country="GB",
        case_idx=1
    )
    repo.save_recommendation(clean_rec)

    # 2. Query case details and recommendations
    rec_resp = client.get(f"/api/cases/{case_id}")
    assert rec_resp.status_code == 200
    data = rec_resp.json()
    
    rec = data.get("recommendation")
    assert rec is not None
    assert rec.get("ambiguity_detected") is True, "Ambiguity must be detected for multi-candidate case"
    assert "Two eligible active accounts" in rec.get("ambiguity_message", "")

    # Hypotheses check
    ranking = rec.get("hypothesis_ranking", [])
    eligible = [h for h in ranking if h.get("status") == "ELIGIBLE_CANDIDATE"]
    assert len(eligible) >= 2, "Must have at least 2 eligible candidates"
    hyp1 = eligible[0]
    hyp2 = eligible[1]
    assert hyp1["candidate_value"] is not None
    assert hyp2["candidate_value"] is not None

    # 3. Apply Human Operator Disambiguation selecting HYP-2
    selected_hyp = hyp2["hypothesis_id"]
    selected_val = hyp2["candidate_value"]
    rationale = "Verified against trade invoice INV-2026-88 and Companies House registry."
    
    disambig_resp = client.post(
        f"/api/cases/{case_id}/disambiguate-hypothesis",
        json={
            "selected_hypothesis_id": selected_hyp,
            "candidate_value": selected_val,
            "rationale": rationale,
            "operator_id": "OP-9012"
        }
    )
    assert disambig_resp.status_code == 200
    res_data = disambig_resp.json()
    assert res_data["success"] is True

    # 4. Verify recommendation state after disambiguation
    updated_rec = res_data["recommendation"]
    assert updated_rec["ambiguity_detected"] is False
    assert "Human Disambiguation Applied" in updated_rec["rationale"]

    updated_ranking = updated_rec["hypothesis_ranking"]
    selected_items = [h for h in updated_ranking if h["status"] == "SELECTED"]
    assert len(selected_items) == 1
    assert selected_items[0]["hypothesis_id"] == selected_hyp

    # 5. Verify Cryptographic Audit Trail
    audit_resp = client.get(f"/api/audit/case/{case_id}")
    assert audit_resp.status_code == 200
    chain = audit_resp.json()
    events = chain.get("events", [])
    disambig_event = next((e for e in events if e.get("action_name") == "HUMAN_DISAMBIGUATION_APPLIED"), None)
    assert disambig_event is not None, "HUMAN_DISAMBIGUATION_APPLIED audit event must be logged"
    assert "Human tie-breaker enforced" in disambig_event.get("control_tags", [])


def test_rule_edit_and_maker_checker_approval_workflow():
    """Verify that editing an active rule submits it as PENDING_APPROVAL and requires Checker sign-off."""
    # 1. Fetch active rules
    rules_resp = client.get("/api/rules")
    assert rules_resp.status_code == 200
    rules = rules_resp.json()
    assert len(rules) > 0
    target_rule = rules[0]
    rule_id = target_rule["rule_id"]

    # 2. Maker edits the rule prompt and submits for approval
    modified_prompt = target_rule["natural_language_prompt"] + " [Updated threshold by Maker]"
    edit_resp = client.post(
        "/api/rules/submit",
        json={
            "rule_id": rule_id,
            "name": target_rule["name"],
            "natural_language_prompt": modified_prompt,
            "category": target_rule["category"],
            "domain": target_rule["domain"],
            "conditions": target_rule["conditions"],
            "actions": target_rule["actions"],
            "maker_id": "OP-9012",
            "maker_name": "Priya Nair",
            "maker_notes": "Modified approval gating parameters for Q4 compliance.",
            "auto_approve": False
        }
    )
    assert edit_resp.status_code == 201
    edited_rule = edit_resp.json()
    assert edited_rule["rule_id"] == rule_id
    assert edited_rule["status"] == "PENDING_APPROVAL"
    assert edited_rule["natural_language_prompt"] == modified_prompt

    # 3. Segregation of Duties: Maker cannot approve their own rule
    sod_resp = client.post(
        f"/api/rules/{rule_id}/approve",
        json={
            "checker_id": "OP-9012",
            "checker_name": "Priya Nair",
            "comments": "Self approval attempt"
        }
    )
    assert sod_resp.status_code == 403
    assert "Segregation of Duties" in sod_resp.json()["detail"]

    # 4. Checker signs off and activates modified rule
    checker_resp = client.post(
        f"/api/rules/{rule_id}/approve",
        json={
            "checker_id": "APR-3191",
            "checker_name": "Daniel Osei",
            "comments": "Modifications reviewed and authorized for production activation."
        }
    )
    assert checker_resp.status_code == 200
    activated_rule = checker_resp.json()
    assert activated_rule["status"] == "ACTIVE"
    assert activated_rule["checker_id"] == "APR-3191"
    assert activated_rule["approved_at"] is not None
