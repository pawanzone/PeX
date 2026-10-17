"""Governed Action Execution Endpoints."""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.action_executor import action_executor
from app.services.audit_service import audit_service
from app.services.data_loader import repo
from app.core.security import get_persona
from app.core.auth import resolve_user_id
from app.schemas.approval import UserRole

router = APIRouter()

class ExecuteActionRequest(BaseModel):
    case_id: str
    idempotency_key: Optional[str] = None
    actor_id: Optional[str] = None

@router.post("/execute")
def execute_action(req: ExecuteActionRequest, authorization: Optional[str] = Header(None)):
    user_id = resolve_user_id(authorization, fallback=req.actor_id)

    actor = get_persona(user_id)
    if not actor:
        raise HTTPException(
            status_code=401,
            detail=f"Unauthorized actor: persona '{user_id}' not found"
        )

    if actor.role == UserRole.OPERATOR:
        raise HTTPException(
            status_code=403,
            detail="Segregation of Duties (SoD) violation: Operators (Makers) cannot execute settlement dispatch. Must be authorized by an Operations Approver, Compliance Approver, Risk Officer, or System Kernel."
        )

    actor_name = actor.name
    actor_role_str = actor.role.value

    success, message, action_contract, receipt = action_executor.execute_governed_action(
        case_id=req.case_id,
        idempotency_key=req.idempotency_key
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Log audit event with actual dispatching actor
    audit_service.log_event(
        case_id=req.case_id,
        correlation_id=req.case_id,
        stage_name="ACTION_DISPATCH",
        actor_id=user_id,
        actor_role=actor_role_str,
        action_name="GOVERNED_SETTLEMENT_DISPATCHED",
        details=f"Settlement dispatch authorized and executed by {actor_name} ({actor_role_str}). Reconciled against banking ledger. Receipt: {receipt.bank_ack_reference}",
        control_tags=["Maker-Checker enforced", "SoD verified", "Idempotency key recorded", "Ledger reconciled"]
    )

    return {
        "success": True,
        "message": message,
        "case": repo.get_case(req.case_id),
        "action_contract": action_contract.model_dump() if action_contract else None,
        "delivery_receipt": receipt.model_dump() if receipt else None
    }

class PingApproverRequest(BaseModel):
    case_id: str
    actor_id: Optional[str] = None
    note: Optional[str] = None

@router.post("/ping-approver")
def ping_approver(req: PingApproverRequest, authorization: Optional[str] = Header(None)):
    user_id = resolve_user_id(authorization, fallback=req.actor_id, default="OP-9012")
        
    actor = get_persona(user_id)
    actor_name = actor.name if actor else "Payment Operator"
    actor_role_str = actor.role.value if actor else "OPERATOR"

    case = repo.get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {req.case_id} not found")

    status = case.get("status")
    if status not in ["PENDING_APPROVAL", "AWAITING_SECOND_APPROVAL", "APPROVED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot ping approver for case in {status} status. Case must be in PENDING_APPROVAL, AWAITING_SECOND_APPROVAL, or APPROVED."
        )

    # Determine target role
    target_role = "OPERATIONS_APPROVER"
    target_role_title = "Operations Approver (Tier 1)"
    if status == "APPROVED":
        target_role = "OPERATIONS_APPROVER"
        target_role_title = "Operations Approver (Dispatch Release)"
    elif case.get("queue") == "Compliance":
        target_role = "COMPLIANCE_APPROVER"
        target_role_title = "Compliance Approver"
    elif status == "AWAITING_SECOND_APPROVAL":
        target_role = "RISK_APPROVER"
        target_role_title = "Risk Officer (Tier 2 Dual-Auth)"

    from datetime import datetime
    now_iso = datetime.utcnow().isoformat()
    note_text = req.note or "Target settlement window closing soon — please prioritize authorization."

    ping_payload = {
        "sender_id": user_id,
        "sender_name": actor_name,
        "sender_role": actor_role_str,
        "target_role": target_role,
        "target_role_title": target_role_title,
        "timestamp": now_iso,
        "note": note_text,
        "status": "UNREAD"
    }

    case["expedite_ping"] = ping_payload

    # Emit audit provenance event
    action_event_name = "L1_EXPEDITE_PING" if actor_role_str == "OPERATIONS_APPROVER" else "MAKER_EXPEDITE_PING"
    audit_service.log_event(
        case_id=req.case_id,
        correlation_id=req.case_id,
        stage_name="EXPEDITE_ALERT",
        actor_id=user_id,
        actor_role=actor_role_str,
        action_name=action_event_name,
        details=f"SLA expedite chaser dispatched by {actor_name} ({actor_role_str}) to {target_role_title} for {req.case_id}. Note: '{note_text}'",
        control_tags=["SLA priority alert", "Maker chaser logged", "Clearing cutoff monitoring"]
    )

    return {
        "success": True,
        "message": f"Expedite priority alert dispatched to {target_role_title}.",
        "case": case,
        "ping": ping_payload
    }
