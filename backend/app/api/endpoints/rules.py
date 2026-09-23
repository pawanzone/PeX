"""REST API Endpoints for Dynamic Governed Rules & ICD Registry."""
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.rules import (
    PolicyRule,
    SynthesizeRuleRequest,
    SynthesizeRuleResponse,
    SimulateRuleRequest,
    SimulateRuleResponse,
    SubmitRuleRequest,
    CheckerDecisionRequest,
    ICDConfiguration,
    SubmitICDConfigRequest,
)
from app.services.rule_engine import rule_engine
from app.services.data_loader import repo
from app.core.security import get_persona
from app.schemas.approval import UserRole

router = APIRouter(prefix="/rules", tags=["Governed Rules & Policies"])

@router.get("", response_model=List[Dict[str, Any]])
def list_rules(status: Optional[str] = Query(None, description="Filter rules by status (ACTIVE, PENDING_APPROVAL, DRAFT, REJECTED, RETIRED)")):
    """Returns all governed business policy rules."""
    return repo.get_policy_rules(status=status)

@router.get("/{rule_id}", response_model=Dict[str, Any])
def get_rule(rule_id: str):
    """Returns a specific policy rule by ID."""
    rule = repo.get_policy_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return rule

@router.post("/synthesize", response_model=SynthesizeRuleResponse)
def synthesize_rule_from_nlp(payload: SynthesizeRuleRequest):
    """Translates a natural language governance policy into an executable JSON AST."""
    if not payload.prompt or not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Natural language prompt cannot be empty")
    return rule_engine.synthesize_rule(
        prompt=payload.prompt.strip(),
        category_hint=payload.category,
        domain_hint=payload.domain
    )

@router.post("/simulate", response_model=SimulateRuleResponse)
def simulate_rule_impact(payload: SimulateRuleRequest):
    """Simulates the impact of a candidate rule across all live benchmark cases."""
    all_cases = list(repo._case_cache.values())
    rule_dict = {
        "domain": payload.domain or "ALL",
        "conditions": payload.conditions,
        "actions": payload.actions or {}
    }
    return rule_engine.simulate_impact(rule_dict, all_cases)

@router.post("/submit", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def submit_rule_for_approval(payload: SubmitRuleRequest):
    """Maker drafts or updates a business rule and submits it for Checker approval."""
    if not payload.name or not payload.natural_language_prompt:
        raise HTTPException(status_code=400, detail="Rule name and natural language prompt are required")

    rule_id = payload.rule_id
    if not rule_id:
        rule_slug = payload.category.replace("_", "-").lower()
        rule_id = f"RULE-{rule_slug.upper()}-{uuid.uuid4().hex[:6].upper()}"

    # Calculate impact preview for metadata summary
    all_cases = list(repo._case_cache.values())
    impact = rule_engine.simulate_impact({
        "domain": payload.domain,
        "conditions": payload.conditions,
        "actions": payload.actions
    }, all_cases)
    
    impact_summary = (
        f"Affects {impact.matched_cases_count} of {impact.total_cases_evaluated} live cases "
        f"({impact.match_percentage}%) with ${impact.total_dollar_volume_affected:,.2f} aggregate exposure."
    )

    if payload.auto_approve:
        if not payload.checker_id:
            raise HTTPException(
                status_code=403,
                detail="Checker role required for rule activation: checker_id must be provided when auto_approve is True"
            )
        if payload.maker_id and payload.checker_id == payload.maker_id:
            raise HTTPException(
                status_code=403,
                detail=f"Segregation of Duties Violation: Maker ({payload.maker_id}) cannot approve their own rule."
            )
        checker = get_persona(payload.checker_id)
        if not checker or checker.role == UserRole.OPERATOR:
            raise HTTPException(
                status_code=403,
                detail="Checker role required for rule activation: operators cannot activate rules without approver sign-off"
            )

    status_val = "ACTIVE" if payload.auto_approve else "PENDING_APPROVAL"
    approved_at_val = datetime.utcnow() if payload.auto_approve else None

    rule_data = {
        "rule_id": rule_id,
        "name": payload.name,
        "natural_language_prompt": payload.natural_language_prompt,
        "category": payload.category,
        "domain": payload.domain,
        "conditions": payload.conditions,
        "actions": payload.actions,
        "status": status_val,
        "version": "1.0",
        "impact_summary": impact_summary,
        "maker_id": payload.maker_id,
        "maker_name": payload.maker_name,
        "maker_notes": payload.maker_notes or f"Draft submitted by {payload.maker_name} via Policy Studio.",
        "checker_id": payload.checker_id if payload.auto_approve else None,
        "checker_name": payload.checker_name if payload.auto_approve else None,
        "checker_comments": payload.checker_comments or ("Directly authorized and implemented into production" if payload.auto_approve else None),
        "approved_at": approved_at_val,
    }

    saved = repo.save_policy_rule(rule_data)
    return saved

@router.post("/{rule_id}/approve", response_model=Dict[str, Any])
def approve_rule(rule_id: str, payload: CheckerDecisionRequest):
    """Checker reviews, signs off, and immediately activates the rule in production with zero downtime."""
    rule = repo.get_policy_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    # Segregation of Duties enforcement
    if rule.get("maker_id") and rule.get("maker_id") == payload.checker_id:
        raise HTTPException(
            status_code=403,
            detail=f"Segregation of Duties Violation: Maker ({rule.get('maker_name')}) cannot approve their own rule."
        )

    approved = repo.approve_policy_rule(
        rule_id=rule_id,
        checker_id=payload.checker_id,
        checker_name=payload.checker_name,
        comments=payload.comments
    )
    if not approved:
        raise HTTPException(status_code=500, detail="Failed to approve rule")
    return approved

@router.post("/{rule_id}/reject", response_model=Dict[str, Any])
def reject_rule(rule_id: str, payload: CheckerDecisionRequest):
    """Checker returns or rejects a rule proposal with explanatory comments."""
    rule = repo.get_policy_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    if not payload.comments or not payload.comments.strip():
        raise HTTPException(status_code=400, detail="Mandatory comments required when rejecting a policy rule")

    rejected = repo.reject_policy_rule(
        rule_id=rule_id,
        checker_id=payload.checker_id,
        checker_name=payload.checker_name,
        comments=payload.comments
    )
    if not rejected:
        raise HTTPException(status_code=500, detail="Failed to reject rule")
    return rejected

@router.post("/{rule_id}/toggle-status", response_model=Dict[str, Any])
def toggle_rule_status(rule_id: str):
    """Toggles rule status between ACTIVE and RETIRED."""
    rule = repo.get_policy_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    new_status = "RETIRED" if rule.get("status") == "ACTIVE" else "ACTIVE"
    rule["status"] = new_status
    saved = repo.save_policy_rule(rule)
    return saved

# =========================================================================
# ICD CONFIGURATION REGISTRY ENDPOINTS
# =========================================================================

@router.get("/icd-configs/list", response_model=List[Dict[str, Any]])
def list_icd_configs(status: Optional[str] = Query(None, description="Filter ICD configs by status")):
    """Returns all external bank and clearing adapter configurations."""
    return repo.get_icd_configs(status=status)

@router.get("/icd-configs/{icd_id}", response_model=Dict[str, Any])
def get_icd_config(icd_id: str):
    """Returns a specific ICD configuration node by ID."""
    config = repo.get_icd_config(icd_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"ICD node {icd_id} not found")
    return config

@router.post("/icd-configs/submit", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def submit_icd_config(payload: SubmitICDConfigRequest):
    """Maker drafts a new external bank / clearing integration for Checker governance."""
    icd_id = payload.icd_id
    if not icd_id:
        bic_prefix = (payload.bic[:4] if len(payload.bic) >= 4 else "NODE").upper()
        icd_id = f"ICD-{bic_prefix}-{uuid.uuid4().hex[:4].upper()}"

    if payload.auto_approve:
        if not payload.checker_id:
            raise HTTPException(
                status_code=403,
                detail="Checker role required for ICD configuration activation: checker_id must be provided when auto_approve is True"
            )
        if payload.maker_id and payload.checker_id == payload.maker_id:
            raise HTTPException(
                status_code=403,
                detail=f"Segregation of Duties Violation: Maker ({payload.maker_id}) cannot approve their own ICD node."
            )
        checker = get_persona(payload.checker_id)
        if not checker or checker.role == UserRole.OPERATOR:
            raise HTTPException(
                status_code=403,
                detail="Checker role required for ICD configuration activation: operators cannot activate clearing adapters without approver sign-off"
            )

    status_val = "ACTIVE" if payload.auto_approve else "PENDING_APPROVAL"
    approved_at_val = datetime.utcnow() if payload.auto_approve else None

    config_data = {
        "icd_id": icd_id,
        "name": payload.name,
        "institution_name": payload.institution_name,
        "bic": payload.bic.upper(),
        "rail": payload.rail,
        "adapter_type": payload.adapter_type,
        "endpoint_url": payload.endpoint_url,
        "latency_ms": payload.latency_ms,
        "status": status_val,
        "config_payload": payload.config_payload,
        "maker_id": payload.maker_id,
        "maker_name": payload.maker_name,
        "maker_notes": payload.maker_notes or f"ICD node submitted by {payload.maker_name}.",
        "checker_id": payload.checker_id if payload.auto_approve else None,
        "checker_name": payload.checker_name if payload.auto_approve else None,
        "checker_comments": payload.checker_comments or ("Directly authorized and connected into clearing network" if payload.auto_approve else None),
        "approved_at": approved_at_val,
    }

    saved = repo.save_icd_config(config_data)
    return saved

@router.post("/icd-configs/{icd_id}/approve", response_model=Dict[str, Any])
def approve_icd_config(icd_id: str, payload: CheckerDecisionRequest):
    """Checker reviews and activates the external clearing integration node."""
    config = repo.get_icd_config(icd_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"ICD node {icd_id} not found")

    if config.get("maker_id") and config.get("maker_id") == payload.checker_id:
        raise HTTPException(
            status_code=403,
            detail=f"Segregation of Duties Violation: Maker ({config.get('maker_name')}) cannot approve their own ICD node."
        )

    approved = repo.approve_icd_config(
        icd_id=icd_id,
        checker_id=payload.checker_id,
        checker_name=payload.checker_name,
        comments=payload.comments
    )
    if not approved:
        raise HTTPException(status_code=500, detail="Failed to approve ICD configuration")
    return approved
