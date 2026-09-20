"""RBAC Roles, Personas & Authorization Logic."""
from typing import Tuple, List, Dict, Optional
from app.schemas.approval import UserRole
from app.schemas.auth import UserPersona

DEMO_PERSONAS: Dict[str, UserPersona] = {
    "OP-9012": UserPersona(
        user_id="OP-9012",
        name="Priya Nair",
        email="p.nair@pexbank.internal",
        role=UserRole.OPERATOR,
        title="Operator — Payments",
        department="Payment Repair Operations",
        avatar_initials="PN",
        badge_color="blue",
        max_approval_amount=0.0
    ),
    "OP-1001": UserPersona(
        user_id="OP-1001",
        name="Priya Nair",
        email="p.nair@pexbank.internal",
        role=UserRole.OPERATOR,
        title="Senior Payment Analyst",
        department="Payment Repair Operations",
        avatar_initials="PN",
        badge_color="blue",
        max_approval_amount=0.0
    ),
    "OP-9013": UserPersona(
        user_id="OP-9013",
        name="Amina Okafor",
        email="a.okafor@pexbank.internal",
        role=UserRole.OPERATOR,
        title="Operator — Payments",
        department="Triage & Investigation",
        avatar_initials="AO",
        badge_color="blue",
        max_approval_amount=0.0
    ),
    "OP-8472": UserPersona(
        user_id="OP-8472",
        name="Amina Okafor",
        email="a.okafor@pexbank.internal",
        role=UserRole.OPERATOR,
        title="Payment Operations Analyst",
        department="Triage & Investigation",
        avatar_initials="AO",
        badge_color="blue",
        max_approval_amount=0.0,
        is_demo_active=True
    ),
    "APR-3191": UserPersona(
        user_id="APR-3191",
        name="Daniel Osei",
        email="d.osei@pexbank.internal",
        role=UserRole.OPERATIONS_APPROVER,
        title="Approver — Operations",
        department="Payment Exceptions",
        avatar_initials="DO",
        badge_color="emerald",
        max_approval_amount=250000.0
    ),
    "CMP-4420": UserPersona(
        user_id="CMP-4420",
        name="Marisol Vega",
        email="m.vega@pexbank.internal",
        role=UserRole.COMPLIANCE_APPROVER,
        title="Approver — Compliance",
        department="Financial Crime Compliance",
        avatar_initials="MV",
        badge_color="amber",
        max_approval_amount=5000000.0
    ),
    "CMP-5502": UserPersona(
        user_id="CMP-5502",
        name="Marisol Vega",
        email="m.vega@pexbank.internal",
        role=UserRole.COMPLIANCE_APPROVER,
        title="Sanctions & AML Officer",
        department="Financial Crime Compliance",
        avatar_initials="MV",
        badge_color="amber",
        max_approval_amount=5000000.0
    ),
    "RSK-7714": UserPersona(
        user_id="RSK-7714",
        name="Kenji Watanabe",
        email="k.watanabe@pexbank.internal",
        role=UserRole.RISK_APPROVER,
        title="Approver — Risk",
        department="Enterprise Risk Management",
        avatar_initials="KW",
        badge_color="purple",
        max_approval_amount=10000000.0
    ),
    "ADM-0001": UserPersona(
        user_id="ADM-0001",
        name="Alex Whitfield",
        email="a.whitfield@pexbank.internal",
        role=UserRole.ADMIN,
        title="Admin",
        department="Platform Governance",
        avatar_initials="AW",
        badge_color="slate",
        max_approval_amount=10000000.0
    )
}

def get_persona(user_id: str) -> Optional[UserPersona]:
    return DEMO_PERSONAS.get(user_id)

def check_can_approve(role: UserRole, amount: float, queue: str) -> Tuple[bool, str]:
    if role == UserRole.OPERATOR:
        return False, "Operators cannot approve repairs (Maker-Checker policy violation)."
    
    if queue == "Compliance" and role not in [UserRole.COMPLIANCE_APPROVER, UserRole.ADMIN, UserRole.RISK_APPROVER]:
        return False, "Only Compliance & Risk Approvers can clear Compliance queue exceptions."
        
    # All designated approver roles (OPERATIONS_APPROVER, COMPLIANCE_APPROVER, RISK_APPROVER, ADMIN) are authorized for level 1 and dual-auth level 2 approvals
    return True, "Authorized"
