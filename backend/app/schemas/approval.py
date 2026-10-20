"""Role-Gated Human Approval Schemas & Contracts."""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.recommendation import ActionType, ProposedFieldChange

class UserRole(str, Enum):
    OPERATOR = "OPERATOR"
    OPERATIONS_APPROVER = "OPERATIONS_APPROVER"
    COMPLIANCE_APPROVER = "COMPLIANCE_APPROVER"
    RISK_APPROVER = "RISK_APPROVER"
    ADMIN = "ADMIN"
    SUPERVISOR = "SUPERVISOR"
    AUDIT_RISK = "AUDIT_RISK"
    POLICY_OWNER = "POLICY_OWNER"

class ApprovalAction(str, Enum):
    APPROVE = "APPROVE"
    MODIFY = "MODIFY"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"
    RETURN_TO_MAKER = "RETURN_TO_MAKER"
    CLEAR_FALSE_POSITIVE = "CLEAR_FALSE_POSITIVE"
    GRANT_KYC_WAIVER = "GRANT_KYC_WAIVER"

class ApprovalSubmission(BaseModel):
    case_id: str
    action: ApprovalAction
    comments: str
    override_changes: Optional[List[ProposedFieldChange]] = None

class ApprovalRecord(BaseModel):
    approval_id: str
    case_id: str
    recommendation_id: str
    approver_id: str
    approver_name: str
    approver_role: UserRole
    action: ApprovalAction
    comments: str
    approved_changes: List[ProposedFieldChange] = []
    step_number: int = 1  # 1 for Primary, 2 for Dual
    created_at: datetime = Field(default_factory=datetime.utcnow)
