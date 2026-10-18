"""Classification logic shared by the worklist, home, case page and actions (all derived from real case state)."""
from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.core.security import check_can_approve, get_persona
from app.services.state_machine import normalize_status
from app.services.v2 import ext as xt
from app.services.v2.core import (
    now, parse_ts, iso, cutoff_obj, money, rail_obj, profile_code, profile_label, domain_of, is_compliance, party_name,
    account_str, role_of, has_perm, person, ROLE_LABELS,
)

PENDING = {"PENDING_APPROVAL", "AWAITING_SECOND_APPROVAL"}
DONE = {"DISPATCHED", "EXECUTED_CONFIRMED", "SETTLED", "REJECTED", "SHADOW_RECORDED", "FAILED"}
FINAL_OK = {"EXECUTED_CONFIRMED", "SETTLED"}
WORKABLE = {"INGESTED", "CANONICALIZED", "VALIDATED", "INVESTIGATING", "RECOMMENDED", "ESCALATED", "RETURNED_FOR_REWORK"}
DUAL_AUTH_THRESHOLD = 250000.0

VARIANTS = ("DECISION", "MISSING_INFO", "CONFLICT", "STATUS_UNKNOWN", "COMPLIANCE_HOLD", "APPROVAL", "HANDED_TO_BANK", "EXECUTED", "GENERIC")


def status_of(case: Dict[str, Any]) -> str:
    return normalize_status(case.get("status")) or "INGESTED"


def ext_of(case: Dict[str, Any]) -> Dict[str, Any]:
    return xt.get_ext(case)


def is_dual(case: Dict[str, Any]) -> bool:
    return float(case.get("amount") or 0) >= DUAL_AUTH_THRESHOLD or bool(case.get("dual_auth_required")) or status_of(case) == "AWAITING_SECOND_APPROVAL"


def evidence_state(ext: Dict[str, Any]) -> str:
    return ext.get("evidence_state") or "complete"


def request_state(ext: Dict[str, Any]) -> str:
    ri = ext.get("request_info") or {}
    st = ri.get("state") or "none"
    if st == "sent":
        due = parse_ts(ri.get("reply_due"))
        if due and due < now():
            return "overdue"
    return st


def derive_variant(case: Dict[str, Any], ext: Optional[Dict[str, Any]] = None) -> str:
    ext = ext if ext is not None else ext_of(case)
    st = status_of(case)
    if st in FINAL_OK:
        return "EXECUTED"
    if st == "DISPATCHED":
        return "HANDED_TO_BANK"
    if st == "STATUS_UNKNOWN":
        return "STATUS_UNKNOWN"
    comp_hold = is_compliance(case) or str(ext.get("compliance_status") or "").upper() in ("SANCTIONS_HOLD", "AML_SUSPENDED")
    if comp_hold and st not in ("REJECTED", "FAILED", "SHADOW_RECORDED"):
        if not (ext.get("compliance") or {}).get("released"):
            return "COMPLIANCE_HOLD"
    if st in PENDING or st == "APPROVED":
        return "APPROVAL"
    es = evidence_state(ext)
    if st in WORKABLE:
        if es == "conflict":
            return "CONFLICT"
        if es == "missing":
            return "MISSING_INFO"
        if ext.get("change"):
            return "DECISION"
    return "GENERIC"


def waiting(case: Dict[str, Any], ext: Dict[str, Any]) -> bool:
    st = status_of(case)
    if st == "STATUS_UNKNOWN":
        return True
    return st in WORKABLE and request_state(ext) in ("sent", "overdue")


def tab_of(case: Dict[str, Any], ext: Dict[str, Any]) -> Optional[str]:
    st = status_of(case)
    if st in DONE:
        return "done"
    if is_compliance(case):
        return "compliance"
    if waiting(case, ext):
        return "waiting"
    if st in PENDING or st == "APPROVED":
        return "pending"
    if st == "RETURNED_FOR_REWORK":
        return "returned"
    return "ready"


def cutoff_dt(case: Dict[str, Any], ext: Dict[str, Any]):
    return parse_ts(ext.get("cutoff_at")) or parse_ts(case.get("sla_due_at"))


def evidence_badge(case: Dict[str, Any], ext: Dict[str, Any], variant: Optional[str] = None) -> Dict[str, str]:
    variant = variant or derive_variant(case, ext)
    if variant == "COMPLIANCE_HOLD" or is_compliance(case):
        return {"status": "compliance", "label": "With Compliance"}
    es = evidence_state(ext)
    return {"status": es, "label": {"complete": "Complete", "conflict": "Conflict", "missing": "Missing"}.get(es, "Complete")}


def next_action(case: Dict[str, Any], ext: Dict[str, Any], variant: str, viewer=None) -> Dict[str, str]:
    st = status_of(case)
    code = profile_code(case.get("profile"))
    if ext.get("possible_duplicate_of") and st in WORKABLE:
        return {"text": "Review possible duplicate", "type": "REVIEW_DUPLICATE"}
    if variant == "EXECUTED":
        return {"text": "Done · confirmed by bank", "type": "NONE"}
    if variant == "HANDED_TO_BANK":
        return {"text": "Waiting for bank confirmation", "type": "AWAIT_BANK"}
    if variant == "STATUS_UNKNOWN":
        return {"text": "Check status · do not resend", "type": "CHECK_STATUS"}
    if variant == "COMPLIANCE_HOLD":
        return {"text": "Review screening alert" if viewer is not None and has_perm(viewer, "compliance.decide") else "With Compliance",
                "type": "COMPLIANCE_DECISION" if viewer is not None and has_perm(viewer, "compliance.decide") else "WITH_COMPLIANCE"}
    if variant == "APPROVAL":
        if viewer is not None and has_perm(viewer, "case.approve"):
            return {"text": "Review and approve", "type": "REVIEW_APPROVE"}
        return {"text": "Awaiting approval", "type": "AWAIT_APPROVAL"}
    if variant == "CONFLICT":
        return {"text": "Resolve conflict", "type": "RESOLVE_CONFLICT"}
    if variant == "MISSING_INFO":
        rs = request_state(ext)
        if rs == "sent":
            return {"text": "Waiting for client reply", "type": "WAIT_REPLY"}
        if rs == "overdue":
            return {"text": "Follow up · reply overdue", "type": "FOLLOW_UP"}
        return {"text": "Request information", "type": "REQUEST_INFO"}
    if st == "RETURNED_FOR_REWORK":
        return {"text": "Rework and resubmit", "type": "REWORK"}
    if code == "ST-01":
        return {"text": "Review return", "type": "REVIEW_RETURN"}
    if variant == "DECISION":
        if str(case.get("queue")) == "STP Fast-Lane":
            return {"text": "Submit for approval", "type": "SUBMIT"}
        return {"text": "Submit for approval", "type": "SUBMIT"}
    if st in DONE:
        return {"text": "Closed", "type": "NONE"}
    return {"text": "Review case", "type": "REVIEW"}


# ----------------------------------------------------------------------------------------------
# Authorisation gate for checker actions (shared by page, actions and STP)
# ----------------------------------------------------------------------------------------------
def approve_gate(case: Dict[str, Any], user) -> Tuple[bool, str, str]:
    """Returns (allowed, code, message)."""
    st = status_of(case)
    if not has_perm(user, "case.approve"):
        return False, "FORBIDDEN", f"{ROLE_LABELS.get(role_of(user), role_of(user))} cannot approve repairs."
    if st not in PENDING:
        return False, "INVALID_STATE", f"Case is {st.replace('_', ' ').lower()}, not awaiting approval."
    ok, msg = check_can_approve(role=user.role, amount=float(case.get("amount") or 0), queue=str(case.get("queue") or "Repair"),
                                user_id=user.user_id, persona=user, maker_id=case.get("maker_id"))
    if not ok:
        code = "SOD_VIOLATION" if "Segregation" in msg else ("LIMIT_EXCEEDED" if "limit" in msg.lower() else "FORBIDDEN")
        return False, code, msg
    rel = ((ext_of(case).get("compliance") or {}).get("released_by") or {}).get("user_id")
    if rel and rel == user.user_id:
        return False, "SOD_VIOLATION", "You cleared the screening hold on this case. A Risk Approver (not you) must authorise the handoff."
    if st == "AWAITING_SECOND_APPROVAL":
        l1 = [a for a in (case.get("approval_history") or []) if int((a or {}).get("step_number", 1)) == 1
              and str((a or {}).get("action")) in ("APPROVE", "ApprovalAction.APPROVE", "MODIFY")]
        if l1 and l1[-1].get("approver_id") == user.user_id:
            return False, "SOD_VIOLATION", "Dual authorisation: the second approver must be a different person from the first approver."
    return True, "OK", "Authorised"


def sod_block(case: Dict[str, Any], user) -> Dict[str, Any]:
    maker = person(case.get("maker_id"))
    viewer_is_maker = bool(maker and user and maker["user_id"] == user.user_id)
    if not maker:
        return {"status": "n/a", "text": "No maker on this case (system-routed). Approver rules still apply.", "maker": None, "viewer_is_maker": False}
    ok, msg = check_can_approve(role=user.role if role_of(user) not in ("SUPERVISOR", "AUDIT_RISK", "OPERATOR") else get_persona("APR-3191").role,
                                amount=0.0, queue="Repair", user_id=user.user_id, persona=user, maker_id=case.get("maker_id"))
    failed = ("Segregation" in msg) if not ok else False
    if viewer_is_maker:
        failed = True
    if failed:
        return {"status": "failed", "text": f"You prepared this repair ({maker['name']}). You cannot approve it.", "maker": maker, "viewer_is_maker": viewer_is_maker}
    return {"status": "passed", "text": f"You did not prepare this repair. Prepared by {maker['name']}.", "maker": maker, "viewer_is_maker": False}


def handoff_id(case: Dict[str, Any], ext: Dict[str, Any]) -> str:
    if ext.get("handoff_id"):
        return ext["handoff_id"]
    h = int(hashlib.sha256(str(case["case_id"]).encode()).hexdigest()[:8], 16) % 90000 + 10000
    return f"HND-{h}"


def bank_ref(case: Dict[str, Any], ext: Dict[str, Any]) -> Optional[str]:
    return case.get("bank_ack_reference") or ext.get("bank_reference")


def row_core(case: Dict[str, Any], viewer=None) -> Dict[str, Any]:
    ext = ext_of(case)
    variant = derive_variant(case, ext)
    cut = cutoff_dt(case, ext)
    return {
        "case_id": case["case_id"],
        "cutoff": cutoff_obj(cut),
        "exception": {"code": profile_code(case.get("profile")), "label": ext.get("exception_label") or profile_label(case.get("profile")), "domain": domain_of(case)},
        "amount": money(case.get("amount"), case.get("currency")),
        "rail": rail_obj(case.get("payment_rail")),
        "counterparty": ext.get("counterparty") or party_name(case.get("creditor_party")),
        "next_action": next_action(case, ext, variant, viewer),
        "evidence": evidence_badge(case, ext, variant),
        "status": status_of(case),
        "variant": variant,
        "assignee": person(ext.get("assignee")),
        "tab": tab_of(case, ext),
    }
