"""Role-Gated Approvals Endpoints."""
from fastapi import APIRouter, HTTPException, Header
from typing import List, Dict, Any, Optional

from app.schemas.approval import ApprovalSubmission, ApprovalRecord
from app.services.approval_engine import approval_engine
from app.services.audit_service import audit_service
from app.services.data_loader import repo
from app.core.security import get_persona

router = APIRouter()

@router.post("/submit")
def submit_approval(submission: ApprovalSubmission, authorization: Optional[str] = Header(None)):
    user_id = "APR-3191" # Default to Daniel Osei (Operations Approver)
    if authorization and authorization.startswith("Bearer pex-token-"):
        user_id = authorization.replace("Bearer pex-token-", "").strip()
    
    approver = get_persona(user_id)
    if not approver:
        raise HTTPException(status_code=401, detail="Unauthorized approver persona")

    success, message, record, next_stage = approval_engine.process_approval_action(
        submission=submission,
        approver_id=user_id
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Log audit event
    audit_service.log_event(
        case_id=submission.case_id,
        correlation_id=submission.case_id,
        stage_name="HITL_APPROVAL",
        actor_id=approver.user_id,
        actor_role=approver.role.value,
        action_name=f"APPROVAL_{submission.action.value}",
        details=f"Approver {approver.name} submitted {submission.action.value}. Decision message: {submission.comments}. Next stage: {next_stage.value}",
        control_tags=["Maker-checker enforced", "Role entitlements verified", f"Step {record.step_number}"]
    )

    return {
        "success": True,
        "message": message,
        "approval_record": record.dict() if record else None,
        "next_stage": next_stage.value
    }
