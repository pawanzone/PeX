"""Controls & Governance Endpoints."""
from fastapi import APIRouter
from typing import Dict, Any
from app.services.audit_service import audit_service
from app.schemas.audit import HashVerificationResult

router = APIRouter()

@router.get("/controls")
def get_operational_controls() -> Dict[str, Any]:
    audit_res = audit_service.verify_chain()
    return {
        "controls": [
            {
                "name": "Identity & entitlements",
                "status": "DEMO MODE",
                "description": "Open demo: server-assigned demo operator is used. Set PEX_ENFORCE_AUTH=true for production posture."
            },
            {
                "name": "Bank isolation",
                "status": "ENFORCED",
                "description": "All queries and decisions are scoped to the operator's bank/tenant."
            },
            {
                "name": "Segregation of duties",
                "status": "ENFORCED",
                "description": "Server blocks maker self-approval; config proposers cannot approve their own changes."
            },
            {
                "name": "Dual authorization",
                "status": "ENFORCED",
                "description": "Repairs at or above $250,000 require two distinct approvers."
            },
            {
                "name": "Sensitive-data boundary",
                "status": "ENFORCED",
                "description": "Cases use payment tokens; raw account details are never exposed to AI models."
            }
        ],
        "ai_model_posture": {
            "boundary": "Evidence-grounded recommendations only; all payment-changing actions require human approval.",
            "mode": "Governed Deterministic Planner + Multi-Model Gateway"
        },
        "continuous_audit": {
            "latest_head_hash": audit_res.chain_head,
            "total_events": audit_res.total_events_checked,
            "chain_verified_intact": audit_res.is_intact
        }
    }

@router.get("/audit-chain/verify", response_model=HashVerificationResult)
def verify_audit_chain_endpoint():
    return audit_service.verify_chain()
