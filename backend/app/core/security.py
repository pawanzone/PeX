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
    ),
    "SUP-2001": UserPersona(user_id="SUP-2001", name="Elena Marsh", email="e.marsh@pexbank.internal", role=UserRole.SUPERVISOR,
        title="Supervisor — Payment Operations", department="Payment Repair Operations", avatar_initials="EM", badge_color="indigo", max_approval_amount=0.0),
    "OP-9020": UserPersona(user_id="OP-9020", name="Marcus Lee", email="m.lee@pexbank.internal", role=UserRole.OPERATOR,
        title="Payments Analyst", department="Payment Repair Operations", avatar_initials="ML", badge_color="blue", max_approval_amount=0.0),
    "OP-9021": UserPersona(user_id="OP-9021", name="Sofia Rossi", email="s.rossi@pexbank.internal", role=UserRole.OPERATOR,
        title="Payments Analyst", department="Payment Repair Operations", avatar_initials="SR", badge_color="blue", max_approval_amount=0.0),
    "OP-9022": UserPersona(user_id="OP-9022", name="Chen Wei", email="c.wei@pexbank.internal", role=UserRole.OPERATOR,
        title="Payments Analyst", department="Payment Repair Operations", avatar_initials="CW", badge_color="blue", max_approval_amount=0.0),
    "APR-3192": UserPersona(user_id="APR-3192", name="Mei Tan", email="m.tan@pexbank.internal", role=UserRole.OPERATIONS_APPROVER,
        title="Operations Approver", department="Payment Exceptions", avatar_initials="MT", badge_color="emerald", max_approval_amount=250000.0),
    "CMP-6001": UserPersona(user_id="CMP-6001", name="Amara Okafor", email="am.okafor@pexbank.internal", role=UserRole.COMPLIANCE_APPROVER,
        title="Compliance Officer", department="Financial Crime Compliance", avatar_initials="AO", badge_color="amber", max_approval_amount=5000000.0),
    "AUD-5001": UserPersona(user_id="AUD-5001", name="Rhea Kapoor", email="r.kapoor@pexbank.internal", role=UserRole.AUDIT_RISK,
        title="Audit and Risk (read only)", department="Internal Audit and Risk", avatar_initials="RK", badge_color="slate", max_approval_amount=0.0),
    "ADM-0002": UserPersona(user_id="ADM-0002", name="Tomas Berg", email="t.berg@pexbank.internal", role=UserRole.ADMIN,
        title="Administrator", department="Platform Governance", avatar_initials="TB", badge_color="slate", max_approval_amount=0.0),
}

ROLE_MAX_APPROVAL_LIMITS: Dict[UserRole, float] = {
    UserRole.OPERATOR: 0.0,
    UserRole.OPERATIONS_APPROVER: 250000.0,
    UserRole.COMPLIANCE_APPROVER: 5000000.0,
    UserRole.RISK_APPROVER: 10000000.0,
    UserRole.ADMIN: 10000000.0,
    UserRole.SUPERVISOR: 0.0,
    UserRole.AUDIT_RISK: 0.0,
}

def get_persona(user_id: str) -> Optional[UserPersona]:
    return DEMO_PERSONAS.get(user_id)

def check_can_approve(
    role: UserRole,
    amount: float,
    queue: str,
    user_id: Optional[str] = None,
    persona: Optional[UserPersona] = None,
    maker_id: Optional[str] = None
) -> Tuple[bool, str]:
    if role in (UserRole.OPERATOR, UserRole.SUPERVISOR, UserRole.AUDIT_RISK):
        return False, "This role cannot approve repairs (Maker-Checker policy: only approvers authorise)."
    
    # Enforce Segregation of Duties (Maker != Approver)
    if user_id and maker_id:
        if user_id == maker_id:
            return False, f"Segregation of Duties violation: Approver ({user_id}) cannot approve their own case (Maker-Checker policy violation)."
        maker_persona = get_persona(maker_id)
        approver_persona = persona or get_persona(user_id)
        if maker_persona and approver_persona:
            if (maker_persona.email and approver_persona.email and maker_persona.email == approver_persona.email) or \
               (maker_persona.name and approver_persona.name and maker_persona.name.strip().lower() == approver_persona.name.strip().lower()):
                return False, f"Segregation of Duties violation: Approver ({approver_persona.name}) cannot approve own case created under Maker identity ({maker_persona.name})."

    if queue == "Compliance" and role not in [UserRole.COMPLIANCE_APPROVER, UserRole.ADMIN, UserRole.RISK_APPROVER]:
        return False, "Only Compliance & Risk Approvers can clear Compliance queue exceptions."

    # Enforce monetary approval limits
    if not persona and user_id:
        persona = get_persona(user_id)

    max_limit = persona.max_approval_amount if persona else ROLE_MAX_APPROVAL_LIMITS.get(role, 0.0)
    if amount > max_limit:
        return False, f"Approval limit exceeded: Transaction amount (${amount:,.2f}) exceeds {role.value}'s maximum authorized approval limit (${max_limit:,.2f}). Escalation required."
        
    return True, "Authorized"


