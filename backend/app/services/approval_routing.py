"""Who must authorise a case, as declared by its profile pack (shared by the approval engine and the workflow layer).

The amount rule (dual authorisation from the policy threshold) lives elsewhere and only ever adds to this.
"""
from typing import Any, Optional

from app.profile_packs import registry

TWO_STEP = "COMPLIANCE_THEN_RISK_SIGN_OFF"
_STEP_ROLE = {1: ("COMPLIANCE_APPROVER", "Compliance Approver"), 2: ("RISK_APPROVER", "Risk Approver")}


def profile_code_of(case: dict) -> str:
    """Canonical code (DQ-01...) for a case whose profile may be a code, an enum, or an enum name."""
    from app.services.file_watcher import PROFILE_CODE_TO_ENUM
    raw = case.get("profile")
    text = str(getattr(raw, "value", raw) or "").upper()
    if text in PROFILE_CODE_TO_ENUM:
        return text
    for code, enum in PROFILE_CODE_TO_ENUM.items():
        if text in (enum.value.upper(), enum.name.upper()):
            return code
    return text


def requirement_for(case: dict) -> str:
    return registry.approval_requirement_for(profile_code_of(case), stp_eligible=False)


def compliance_released(case: dict) -> bool:
    """True once a Compliance Approver has cleared the screening hold through the workflow layer (that is step one)."""
    try:
        from app.services.v2 import ext as xt
        ext = xt.ext_store.get(case.get("case_id")) or {}
    except Exception:
        return False
    return bool((ext.get("compliance") or {}).get("released_by"))


def pack_requires_two_steps(case: dict) -> bool:
    """Two approvals still needed: the pack demands compliance-then-risk and compliance has not signed off yet."""
    return requirement_for(case) == TWO_STEP and not compliance_released(case)


def step_role_violation(case: dict, role: Any, step: int) -> Optional[str]:
    """None when the approver may sign this step; otherwise the reason. Only compliance-then-risk profiles restrict roles."""
    if requirement_for(case) != TWO_STEP:
        return None
    released = compliance_released(case)
    final = released or step >= 2
    need, label = _STEP_ROLE[2 if final else 1]
    if str(getattr(role, "value", role)) == need:
        return None
    if released:
        return "Compliance has cleared this exception. Final authorisation must come from a Risk Approver."
    ordinal = "Second" if step >= 2 else "First"
    return f"{ordinal} approval on this exception must come from a {label} (compliance sign-off, then risk sign-off)."
