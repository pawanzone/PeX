"""GET /api/v2/cases/{id}/page — one payload, variant derived from real case state."""
from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.data_loader import repo
from app.services.outbound_port import operation_mode
from app.services.v2 import logic as lg
from app.services.v2 import ext as xt
from app.services.v2 import pii
from app.services.v2.core import (
    now, parse_ts, iso, hhmm, cutoff_obj, money, rail_obj, profile_code, profile_label, domain_of, is_compliance, party_name,
    account_str, role_of, has_perm, person, ROLE_LABELS, role_label_for, not_found, ext_store,
)

RETURN_REASONS = [
    {"code": "EVIDENCE_INSUFFICIENT", "label": "Evidence is not sufficient"},
    {"code": "WRONG_PROPOSED_VALUE", "label": "Proposed value looks wrong"},
    {"code": "HANDOVER_INCOMPLETE", "label": "Handover note incomplete"},
    {"code": "NEEDS_CLIENT_CONFIRMATION", "label": "Needs client confirmation first"},
    {"code": "OTHER", "label": "Other (explain in comment)"},
]
REJECT_REASONS = [
    {"code": "NOT_A_VALID_REPAIR", "label": "Not a valid repair"},
    {"code": "POLICY_BREACH", "label": "Breaches policy"},
    {"code": "SUSPECTED_FRAUD", "label": "Suspected fraud or error"},
    {"code": "DUPLICATE", "label": "Duplicate of another payment"},
    {"code": "OTHER", "label": "Other (explain in comment)"},
]
COMPLIANCE_REASONS = [
    {"code": "FALSE_MATCH_NAME", "label": "False match: different entity"},
    {"code": "FALSE_MATCH_IDENTIFIERS", "label": "False match: identifiers differ"},
    {"code": "TRUE_MATCH", "label": "Confirmed match with listed entity"},
    {"code": "NEEDS_SENIOR_REVIEW", "label": "Needs senior compliance review"},
    {"code": "OTHER", "label": "Other (explain in comment)"},
]


def viewer_mode(user) -> str:
    r = role_of(user)
    return {"OPERATOR": "maker", "SUPERVISOR": "supervisor", "COMPLIANCE_APPROVER": "compliance", "AUDIT_RISK": "read_only"}.get(r, "checker")


def _chip(label, tone="neutral"):
    return {"label": label, "tone": tone}


def evidence_summary(rows: List[Dict[str, Any]], state: str) -> Dict[str, Any]:
    total = len(rows)
    agree = sum(1 for r in rows if r["status"] in ("pass", "agree", "info"))
    if state == "complete":
        label = f"{agree} of {total} sources agree" if total else "No evidence rows"
    elif state == "conflict":
        label = f"{agree} of {total} sources agree · {sum(1 for r in rows if r['status'] == 'differs')} differ"
    else:
        label = f"{agree} of {total} items found · {sum(1 for r in rows if r['status'] == 'missing')} missing"
    return {"agree": agree, "total": total, "label": label, "status": state}


def _step(key, label, actor, role, at, state, note=None):
    return {"key": key, "label": label, "actor": actor, "role": role, "at": at, "state": state, "note": note}


def build_journey(case: Dict[str, Any], ext: Dict[str, Any], variant: str) -> Dict[str, Any]:
    st = lg.status_of(case)
    created = case.get("created_at")
    jt = ext.get("journey_times") or {}
    es = lg.evidence_state(ext)
    hist = case.get("approval_history") or []

    def appr(step):
        for a in reversed(hist):
            if int((a or {}).get("step_number", 1)) == step and str(a.get("action")).split(".")[-1] in ("APPROVE", "MODIFY", "CLEAR_FALSE_POSITIVE", "GRANT_KYC_WAIVER"):
                return a
        return None

    early = st in lg.WORKABLE
    blocked = variant in ("CONFLICT", "MISSING_INFO", "COMPLIANCE_HOLD", "STATUS_UNKNOWN")
    has_change = bool(ext.get("change"))
    dual = lg.is_dual(case)
    steps = []
    steps.append(_step("detected", "Detected", "PeX", "System", jt.get("detected") or created, "done"))
    ev_state = "done"
    ev_note = None
    if early and es in ("conflict", "missing"):
        ev_state, ev_note = "blocked", ("Evidence conflicts" if es == "conflict" else "Required information missing")
    steps.append(_step("evidence", "Evidence gathered", "PeX", "System", jt.get("evidence") or created, ev_state, ev_note))
    rec_done = has_change or st not in ("INGESTED", "CANONICALIZED", "INVESTIGATING") or bool(ext.get("recommended_action"))
    if early and es in ("conflict", "missing") and not has_change:
        rec_done = False
    steps.append(_step("recommendation", "Recommendation made", "PeX", "System (advisory)", jt.get("recommendation") or created if rec_done else None,
                       "done" if rec_done else ("blocked" if blocked else "pending"),
                       None if rec_done else ("PeX has not proposed a repair" if es == "missing" else None)))
    val_done = rec_done and (st not in ("INGESTED", "CANONICALIZED", "INVESTIGATING")) and not (early and blocked)
    steps.append(_step("validated", "Validated", "PeX controls", "System", jt.get("validated") or created if val_done else None,
                       "done" if val_done else ("blocked" if (blocked and variant == "COMPLIANCE_HOLD") else "pending"),
                       "Compliance hold open" if variant == "COMPLIANCE_HOLD" else None))
    maker = person(case.get("maker_id"))
    submitted = bool(ext.get("handover")) or (maker and st in (lg.PENDING | {"APPROVED"} | lg.DONE))
    if submitted:
        mr = _step("maker_review", "Maker review", (maker or {}).get("name", "Maker"), "Maker",
                   (ext.get("handover") or {}).get("at") or ext.get("submitted_at"), "done")
    elif early and not blocked and has_change:
        mr = _step("maker_review", "Maker review", (person(ext.get("assignee")) or {}).get("name", "Unassigned"), "Maker", None, "current")
    else:
        mr = _step("maker_review", "Maker review", "—", "Maker", None, "blocked" if (blocked and early) else "pending")
    steps.append(mr)
    a1 = appr(1)
    if st == "PENDING_APPROVAL":
        s1 = _step("approval_1", "Approval level 1", "Awaiting approver", "Approver", None, "current")
    elif a1 or st in ("AWAITING_SECOND_APPROVAL", "APPROVED") or st in lg.DONE and a1:
        s1 = _step("approval_1", "Approval level 1", (a1 or {}).get("approver_name", "Approver"), role_label_for((a1 or {}).get("approver_id"), "Approver"),
                   (a1 or {}).get("created_at"), "done")
    elif st in lg.DONE and not a1:
        s1 = _step("approval_1", "Approval level 1", "Policy", "Policy-approved", None, "done", "Approved under policy; no manual approver")
    else:
        s1 = _step("approval_1", "Approval level 1", "—", "Approver", None, "pending")
    steps.append(s1)
    a2 = appr(2)
    if not dual:
        s2 = _step("approval_2", "Approval level 2", "—", "Approver", None, "not_required", "Policy: one approver under 250,000")
    elif st == "AWAITING_SECOND_APPROVAL":
        s2 = _step("approval_2", "Approval level 2", "Awaiting second approver", "Tier 2 approver", None, "current", "Dual authorisation: a different approver must sign")
    elif a2:
        s2 = _step("approval_2", "Approval level 2", a2.get("approver_name", "Approver"), role_label_for(a2.get("approver_id"), "Approver"), a2.get("created_at"), "done")
    else:
        s2 = _step("approval_2", "Approval level 2", "—", "Tier 2 approver", None, "pending", "Required: amount 250,000 or more")
    steps.append(s2)
    if st == "DISPATCHED" or st in lg.FINAL_OK:
        h = _step("handed_to_bank", "Handed to bank", "PeX", "Outbound gateway (simulated)", case.get("handed_off_at"), "done",
                  f"Handoff {lg.handoff_id(case, ext)} sent (simulated)")
    elif st == "SHADOW_RECORDED":
        h = _step("handed_to_bank", "Handed to bank", "PeX", "Shadow mode", None, "not_required", "Shadow mode: recorded, nothing sent")
    elif st == "APPROVED":
        h = _step("handed_to_bank", "Handed to bank", "PeX", "Outbound gateway (simulated)", None, "current", "Handoff in progress")
    elif st == "STATUS_UNKNOWN":
        h = _step("handed_to_bank", "Handed to bank", "PeX", "Outbound gateway (simulated)", case.get("handed_off_at"), "done", "Handed off; bank status unknown")
    else:
        h = _step("handed_to_bank", "Handed to bank", "PeX", "Outbound gateway (simulated)", None, "pending")
    steps.append(h)
    if st in lg.FINAL_OK:
        e = _step("executed", "Executed by bank", "Bank", "Bank system", case.get("settled_at") or ext.get("executed_at"), "done",
                  f"Bank ref {lg.bank_ref(case, ext)}" if lg.bank_ref(case, ext) else "Confirmed by bank")
    elif st == "DISPATCHED":
        e = _step("executed", "Executed by bank", "Bank", "Bank system", None, "current", "Waiting for bank confirmation")
    elif st == "STATUS_UNKNOWN":
        e = _step("executed", "Executed by bank", "Bank", "Bank system", None, "blocked", "Status unknown: do not resend")
    elif st in ("REJECTED", "FAILED"):
        e = _step("executed", "Executed by bank", "Bank", "Bank system", None, "blocked", "Case closed without execution")
    else:
        e = _step("executed", "Executed by bank", "Bank", "Bank system", None, "pending")
    steps.append(e)

    # next-action card
    amt = money(case.get("amount"), case.get("currency"))["display"]
    if variant == "EXECUTED":
        card = {"tone": "success", "title": "Executed by bank (confirmed)", "text": "The bank confirmed execution. PeX never executes: this confirmation came from the bank signal.", "owner": "Bank"}
    elif variant == "HANDED_TO_BANK":
        card = {"tone": "warn", "title": "Approved · handed to bank", "text": "Handoff sent (simulated). Waiting for bank confirmation. Not yet executed.", "owner": "Bank"}
    elif variant == "APPROVAL":
        card = {"tone": "info", "title": "Awaiting approval",
                "text": "A second approver must sign (dual authorisation)." if st == "AWAITING_SECOND_APPROVAL" else "One approver is required before the bank handoff.",
                "owner": "Approver"}
    elif variant == "STATUS_UNKNOWN":
        card = {"tone": "danger", "title": "Status unknown · do not resend", "text": "Check status with the bank. Resending could duplicate the payment.", "owner": "Maker"}
    elif variant == "COMPLIANCE_HOLD":
        card = {"tone": "danger", "title": "Compliance hold", "text": "Repair actions are unavailable while the hold is open.", "owner": "Compliance"}
    elif variant == "CONFLICT":
        card = {"tone": "danger", "title": "Conflicting evidence", "text": "Resolve the conflict before any repair can be prepared.", "owner": "Maker"}
    elif variant == "MISSING_INFO":
        card = {"tone": "warn", "title": "Information needed", "text": "Required information is missing. Request it from the client.", "owner": "Maker"}
    elif variant == "DECISION":
        card = {"tone": "info", "title": "Ready for your decision", "text": "Review the proposed change and submit for approval with a handover note.", "owner": "Maker"}
    else:
        card = {"tone": "info", "title": "Review case", "text": "Review the case details.", "owner": "Maker"}
    from app.db.repository import PeXDBRepository  # noqa
    n_events = len(repo.case_audit_events(case["case_id"]))
    return {"steps": steps, "next_action": card, "audit_events": n_events, "audit_link": f"/audit?case={case['case_id']}"}


def _action(case_id, key, label, kind="secondary", enabled=True, reason=None, path=None):
    return {"key": key, "label": label, "kind": kind, "enabled": bool(enabled), "disabled_reason": None if enabled else reason,
            "endpoint": f"/api/v2/cases/{case_id}/{path or key.replace('_', '-')}"}


def build_actions(case: Dict[str, Any], ext: Dict[str, Any], variant: str, user) -> List[Dict[str, Any]]:
    cid = case["case_id"]
    st = lg.status_of(case)
    vm = viewer_mode(user)
    can_work = has_perm(user, "case.work")
    ro = vm == "read_only"
    acts: List[Dict[str, Any]] = []
    no_work = "Your role cannot work this case." if not ro else "Read-only role."

    if variant == "APPROVAL":
        ok, code, msg = lg.approve_gate(case, user)
        if has_perm(user, "case.approve"):
            acts.append(_action(cid, "approve", "Approve for bank handoff", "primary", ok, msg))
            acts.append(_action(cid, "return", "Return to Maker", "secondary", st in lg.PENDING, "Case is not awaiting approval."))
            acts.append(_action(cid, "reject", "Reject", "danger", st in lg.PENDING, "Case is not awaiting approval."))
        else:
            acts.append(_action(cid, "ping", "Ping approver", "secondary", can_work, no_work))
    elif variant == "DECISION":
        can_submit = can_work and bool(ext.get("change"))
        acts.append(_action(cid, "submit", "Submit for approval", "primary", can_submit,
                            no_work if not can_work else "No validated repair to submit."))
        acts.append(_action(cid, "request_information", "Request information", "secondary", can_work, no_work))
        acts.append(_action(cid, "escalate", "Escalate", "secondary", can_work, no_work))
    elif variant == "MISSING_INFO":
        acts.append(_action(cid, "request_information", "Send request", "primary", can_work, no_work))
        acts.append(_action(cid, "reassess", "Reassess case", "secondary", can_work, no_work))
        acts.append(_action(cid, "escalate", "Escalate", "secondary", can_work, no_work))
        acts.append(_action(cid, "return_to_queue", "Return to queue", "secondary", can_work, no_work, path="assign"))
    elif variant == "CONFLICT":
        acts.append(_action(cid, "start_verification", "Start verification", "primary", can_work, no_work))
        acts.append(_action(cid, "request_information", "Request information", "secondary", can_work, no_work))
        acts.append(_action(cid, "escalate", "Escalate to Senior Analyst", "secondary", can_work, no_work))
        acts.append(_action(cid, "prepare_repair", "Prepare repair", "secondary", False, "Locked until the conflict is resolved."))
    elif variant == "STATUS_UNKNOWN":
        acts.append(_action(cid, "check_status", "Check status now", "primary", can_work, no_work))
        acts.append(_action(cid, "request_bank_status", "Request status from bank operations", "secondary", can_work, no_work))
        acts.append(_action(cid, "escalate", "Escalate", "secondary", can_work, no_work))
    elif variant == "COMPLIANCE_HOLD":
        if has_perm(user, "compliance.decide"):
            cd = ext.get("compliance") or {}
            sr = (cd.get("second_review") or {})
            acts.append(_action(cid, "compliance_release", "Clear hold · false match (returns to approval)", "primary", True, None, path="compliance/decision"))
            acts.append(_action(cid, "compliance_confirm_block", "Confirm match · block payment", "danger", True, None, path="compliance/decision"))
            acts.append(_action(cid, "compliance_escalate", "Escalate to Senior Compliance", "secondary", True, None, path="compliance/decision"))
        else:
            for k, lab in (("submit", "Submit for approval"), ("request_information", "Request information")):
                acts.append(_action(cid, k, lab, "secondary", False, "Repair actions are unavailable while the compliance hold is open."))
    elif variant == "HANDED_TO_BANK":
        acts.append(_action(cid, "check_status", "Check status with bank", "secondary", can_work, no_work))
        acts.append(_action(cid, "ping", "Ping settlement operations", "secondary", can_work, no_work))
    elif variant == "EXECUTED":
        pass
    else:
        acts.append(_action(cid, "request_information", "Request information", "secondary", can_work, no_work))
        acts.append(_action(cid, "escalate", "Escalate", "secondary", can_work, no_work))
    if st in lg.WORKABLE and has_perm(user, "case.assign") and variant != "COMPLIANCE_HOLD":
        a = ext.get("assignee")
        acts.append(_action(cid, "assign_to_me", "Assign to me", "secondary", a != user.user_id, "Already assigned to you.", path="assign"))
    return acts


def _banner(case, ext, variant, user):
    if ext.get("possible_duplicate_of") and variant not in ("EXECUTED", "HANDED_TO_BANK"):
        return {"tone": "warn", "title": "Possible duplicate · not identical",
                "text": f"This record matches existing case {ext['possible_duplicate_of']} on payment reference, amount and creditor but has a different id/UETR. Review before any repair."}
    if variant == "MISSING_INFO":
        return {"tone": "warn", "title": "Required information is missing", "text": "Required information is missing. PeX has not proposed a repair."}
    if variant == "CONFLICT":
        return {"tone": "danger", "title": "Conflicting evidence · STP blocked", "text": "Sources disagree on a key field. PeX cannot choose between them, and straight-through processing is blocked."}
    if variant == "STATUS_UNKNOWN":
        return {"tone": "danger", "title": "Do not resend", "text": "The bank has not confirmed this payment. Do not resend: resending could duplicate it. Check status first."}
    if variant == "COMPLIANCE_HOLD":
        return {"tone": "danger", "title": "Compliance hold",
                "text": "Repair actions are unavailable while the hold is open. Do not contact the customer about this alert."}
    if variant == "HANDED_TO_BANK":
        return {"tone": "info", "title": "Handed to bank · waiting for bank confirmation",
                "text": f"Handoff {lg.handoff_id(case, ext)} was sent to the bank payment system (simulated). The payment is not executed until the bank confirms."}
    if variant == "EXECUTED":
        return {"tone": "success", "title": "Executed by bank", "text": "The bank confirmed execution."}
    if variant == "APPROVAL" and lg.status_of(case) == "AWAITING_SECOND_APPROVAL":
        return {"tone": "info", "title": "Awaiting second approval", "text": "First approval recorded. A different tier-2 approver must sign."}
    if variant == "APPROVAL" and role_of(user) in ("OPERATOR", "SUPERVISOR"):
        return {"tone": "info", "title": "Awaiting approval", "text": "Submitted for approval. You cannot approve your own repair."}
    if lg.status_of(case) == "SHADOW_RECORDED":
        return {"tone": "info", "title": "Shadow mode", "text": "Recorded for the agreement metric. Nothing was sent to the bank."}
    if lg.status_of(case) == "REJECTED":
        return {"tone": "danger", "title": "Rejected", "text": "This case was rejected and will not be repaired or released."}
    return None


def _chips(case, ext, variant):
    dom = domain_of(case).replace("_", " ").capitalize()
    chips = [_chip(dom), _chip(ext.get("exception_label") or profile_label(case.get("profile")))]
    label = {"DECISION": ("Validated · not yet approved", "info"), "MISSING_INFO": ("Waiting for information", "warn"),
             "CONFLICT": ("Conflict · STP blocked", "danger"), "STATUS_UNKNOWN": ("Status unknown · do not resend", "danger"),
             "COMPLIANCE_HOLD": ("Compliance hold", "danger"), "APPROVAL": ("Pending approval", "info"),
             "HANDED_TO_BANK": ("Handed to bank", "info"), "EXECUTED": ("Executed by bank", "success")}.get(variant)
    if label:
        chips.append(_chip(*label))
    elif lg.status_of(case) == "SHADOW_RECORDED":
        chips.append(_chip("Shadow recorded", "info"))
    elif lg.status_of(case) == "REJECTED":
        chips.append(_chip("Rejected", "danger"))
    if ext.get("possible_duplicate_of"):
        chips.append(_chip("Possible duplicate", "warn"))
    return chips


def _brief(case, ext, variant, nxt):
    ch = ext.get("change")
    es = xt_summary = evidence_summary(ext.get("evidence") or [], lg.evidence_state(ext))
    if ch:
        pc = f"{ch['field_label']}: replace {ch['original']['value'] or '(empty)'} with {ch['proposed']['value']}"
    else:
        pc = "No repair proposed."
    st = lg.status_of(case)
    ctrl = "Validation passed" if (ch and lg.evidence_state(ext) == "complete") else "Validation not complete"
    ctrl += " · two approvers required (dual authorisation)" if lg.is_dual(case) else " · one approver required"
    return {"what_happened": case.get("reason") or "Payment exception detected.", "proposed_change": pc, "evidence": es["label"],
            "controls": ctrl, "next": nxt["text"]}


def _needed(case, ext):
    rows = []
    for r in (ext.get("evidence") or []):
        if r["status"] == "missing":
            rows.append({"item": r["check"], "status": "missing", "note": r.get("result")})
        else:
            rows.append({"item": r["check"], "status": "found", "note": r.get("result")})
    if ext.get("needed"):
        return ext["needed"]
    searched = [{"source": s, "result": "No record"} for s in (xt.profile_spec(case.get("profile")).get("mandatory_evidence") or [])[:2]]
    searched.append({"source": "Prior payments", "result": "None found"})
    return {"rows": rows, "searched": searched}


def _request_info(case, ext):
    ri = dict(ext.get("request_info") or {})
    cp = ext.get("counterparty") or party_name(case.get("creditor_party"))
    t = now()
    out = {
        "to": ri.get("to") or {"party": cp, "contact": ext.get("contact") or "Relationship manager", "role": "Relationship manager"},
        "methods": ["Email", "Phone", "Portal"], "method": ri.get("method") or "Email",
        "message": ri.get("message") or f"Please confirm the missing beneficiary details for payment {case.get('payment_ref')} ({money(case.get('amount'), case.get('currency'))['display']}).",
        "draft_saved_at": ri.get("draft_saved_at"),
        "reply_due": ri.get("reply_due") or iso(t + timedelta(hours=2)),
        "escalate_at": ri.get("escalate_at") or iso(t + timedelta(hours=2, minutes=15)),
        "state": lg.request_state(ext), "sent_at": ri.get("sent_at"),
    }
    return out


def _status_unknown(case, ext):
    su = ext.get("status_unknown") or {}
    t = parse_ts(case.get("handed_off_at")) or parse_ts(case.get("created_at")) or now()
    known = su.get("known") or [
        {"system": "Bank payment engine", "says": "Instruction sent; no acknowledgement received", "as_of": iso(t), "state": "unknown"},
        {"system": "Network status tracker", "says": "No status report received", "as_of": iso(t), "state": "unknown"},
        {"system": "Ledger", "says": "Debit posted; no credit confirmation", "as_of": iso(t), "state": "warn"},
        {"system": "Correspondent bank", "says": "No response yet", "as_of": iso(t), "state": "unknown"},
    ]
    nxt = su.get("next") or [
        {"outcome": "Not sent", "what_happens": "Safe to repair and release once the bank confirms nothing left the bank."},
        {"outcome": "Accepted by network", "what_happens": "Payment proceeds. Case closes after the bank confirms execution."},
        {"outcome": "Rejected", "what_happens": "A reject reason arrives. The case returns to a repair decision."},
        {"outcome": "Delivered but misapplied", "what_happens": "An investigation case is opened. Do not resend."},
    ]
    last = ext.get("last_status_check")
    overdue = su.get("check_overdue_minutes")
    if overdue is None:
        lc = parse_ts((last or {}).get("at")) or t
        overdue = max(0, int((now() - lc).total_seconds() // 60) - 5)
    return {"uetr": case.get("uetr"), "do_not_resend": True, "known": known, "next": nxt, "last_check": last, "check_overdue_minutes": overdue}


def _compliance(case, ext):
    cd = dict(ext.get("compliance") or {})
    ref = cd.get("alert", {}).get("reference") or f"SCR-{int(hashlib.sha256(case['case_id'].encode()).hexdigest()[:8], 16) % 90000 + 10000}"
    alert = {"reference": ref, "source": "Bank screening system", "list": "Sanctions list (bank-configured)", "match_type": "Name potential match",
             "raised_at": case.get("created_at"), "open_url": None, "note": "Simulated: no link to a real screening system in this build."}
    alert.update(cd.get("alert") or {})
    cmp_rows = cd.get("party_comparison") or [
        {"attribute": "Name", "payment_party": party_name(case.get("creditor_party")), "listed_entity": "Not available (simulated screening)", "result": "not_comparable", "label": "Not comparable"},
        {"attribute": "Country", "payment_party": (case.get("creditor_party") or {}).get("country", "—"), "listed_entity": "—", "result": "not_comparable", "label": "Not comparable"},
    ]
    sr = cd.get("second_review") or {"required": False, "state": "none", "first_reviewer": None}
    return {
        "alert": alert, "party_comparison": cmp_rows, "notes": cd.get("notes") or [], "attachments": cd.get("attachments") or [],
        "decisions": [{"key": "release", "label": "Clear hold · false match (returns to approval)", "needs_second_reviewer": False},
                      {"key": "confirm_block", "label": "Confirm match · block payment", "needs_second_reviewer": True},
                      {"key": "escalate", "label": "Escalate to Senior Compliance", "needs_second_reviewer": False}],
        "reason_codes": COMPLIANCE_REASONS, "second_review": sr, "decision": cd.get("decision"),
        "footer": "The decision is recorded in PeX and passed to the bank. The bank screening system remains the system of record.",
    }


def _conflict(case, ext):
    c = ext.get("conflict")
    if not c:
        c = {"field": "Evidence under review", "sources": [], "note": "Sources disagree."}
    c = dict(c)
    st = lg.status_of(case)
    can_work = True
    c.setdefault("why_blocked", [
        "Sources disagree on a field that decides where the money goes.",
        "PeX will not pick a source on its own: authority and recency must be confirmed by a person.",
        "Straight-through processing is blocked until the conflict is resolved.",
    ])
    c["next_steps"] = [
        {"key": "start_verification", "label": "Start verification", "enabled": True},
        {"key": "request_information", "label": "Request information", "enabled": True},
        {"key": "escalate", "label": "Escalate to Senior Analyst", "enabled": True},
        {"key": "prepare_repair", "label": "Prepare repair", "enabled": False, "disabled_reason": "Locked until the conflict is resolved"},
    ]
    rec = repo.recommendations.get(case["case_id"])
    dis = ext.get("disambiguation")
    cands = list((ext.get("conflict") or {}).get("candidates") or [])
    if not cands and rec is not None and rec.ambiguity_detected:
        cands = [{"id": h.hypothesis_id, "title": h.title, "value": h.candidate_value, "confidence": h.confidence, "source": h.source or "DETERMINISTIC"}
                 for h in (rec.hypothesis_ranking or []) if h.status in ("ELIGIBLE_CANDIDATE", "SELECTED")]
    c["disambiguation"] = ({"candidates": cands, "endpoint": f"/api/v2/cases/{case['case_id']}/disambiguate", "chosen": dis} if cands or dis else None)
    return c


def case_page(case_id: str, user) -> Dict[str, Any]:
    case = repo.get_case(case_id)
    if not case:
        raise not_found(f"Case {case_id}")
    ext = lg.ext_of(case)
    variant = lg.derive_variant(case, ext)
    st = lg.status_of(case)
    cut = lg.cutoff_dt(case, ext)
    nxt = lg.next_action(case, ext, variant, user)
    rows = ext.get("evidence") or []
    es = lg.evidence_state(ext)
    mode = operation_mode()
    ch = ext.get("change")
    maker = person(case.get("maker_id"))
    page = {
        "case_id": case_id, "variant": variant, "viewer_mode": viewer_mode(user), "now": iso(now()),
        "header": {
            "title": ext.get("exception_label") or profile_label(case.get("profile")), "chips": _chips(case, ext, variant),
            "amount": money(case.get("amount"), case.get("currency")), "cutoff": cutoff_obj(cut), "uetr": case.get("uetr"),
            "rail": rail_obj(case.get("payment_rail")), "creditor": ext.get("counterparty") or party_name(case.get("creditor_party")),
            "debtor": ext.get("debtor") or party_name(case.get("debtor_party")), "status": st,
            "assignee": person(ext.get("assignee")), "opened_at": case.get("created_at"), "payment_ref": case.get("payment_ref"),
            "exception": {"code": profile_code(case.get("profile")), "label": ext.get("exception_label") or profile_label(case.get("profile")), "domain": domain_of(case)},
        },
        "banner": _banner(case, ext, variant, user),
        "decision_brief": _brief(case, ext, variant, nxt),
        "change_summary": ch if (ch and variant in ("DECISION", "APPROVAL", "HANDED_TO_BANK", "EXECUTED", "GENERIC")) else None,
        "sod": lg.sod_block(case, user) if variant == "APPROVAL" else {"status": "n/a", "text": "", "maker": maker, "viewer_is_maker": bool(maker and maker["user_id"] == user.user_id)},
        "handover": ext.get("handover"),
        "evidence_table": rows,
        "evidence_summary": evidence_summary(rows, es),
        "needed": _needed(case, ext) if variant == "MISSING_INFO" else None,
        "conflict": _conflict(case, ext) if variant == "CONFLICT" else None,
        "status_unknown": _status_unknown(case, ext) if variant == "STATUS_UNKNOWN" else None,
        "compliance": _compliance(case, ext) if variant == "COMPLIANCE_HOLD" else None,
        "request_information": _request_info(case, ext) if variant in ("MISSING_INFO", "CONFLICT", "DECISION") else None,
        "recommendation": _recommendation(case, ext),
        "confidence": _confidence(case, ext, variant, user),
        "pii": pii.page_block(case, ext, user),
        "journey": build_journey(case, ext, variant),
        "actions": build_actions(case, ext, variant, user),
        "blocked_actions": [],
        "decision_form": None, "handoff": None, "bank": None, "possible_duplicate_of": ext.get("possible_duplicate_of"),
        "expedite_ping": case.get("expedite_ping"), "mode": mode, "bank_comm": settings.BANK_COMM_MODE,
    }
    if variant == "STATUS_UNKNOWN":
        page["blocked_actions"] = [{"label": "Resend payment", "reason": "Locked: status unknown. Resending could duplicate the payment."}]
    if variant in ("APPROVAL",):
        ok, code, msg = lg.approve_gate(case, user)
        page["decision_form"] = {"requires_review_ack": True, "return_reason_codes": RETURN_REASONS, "reject_reason_codes": REJECT_REASONS,
                                 "footnote": "Next: handed to bank system. Not yet executed.", "level": 2 if st == "AWAITING_SECOND_APPROVAL" else 1,
                                 "dual_auth": lg.is_dual(case), "limit_ok": code != "LIMIT_EXCEEDED", "can_approve": ok, "cannot_approve_reason": None if ok else msg}
    if variant in ("HANDED_TO_BANK", "EXECUTED") or st == "STATUS_UNKNOWN":
        page["handoff"] = {"handoff_id": lg.handoff_id(case, ext), "sent_at": case.get("handed_off_at"), "mode": mode,
                           "bank_comm": settings.BANK_COMM_MODE, "awaiting": "Bank confirmation" if variant != "EXECUTED" else None}
    if variant == "EXECUTED":
        page["bank"] = {"reference": lg.bank_ref(case, ext), "confirmed_at": case.get("settled_at") or ext.get("executed_at"),
                        "clearing_system": case.get("bank_clearing_system")}
    return page


def _confidence(case, ext, variant, user):
    conf = lg.confidence_of(case, ext)
    if not conf:
        return None
    cr = ext.get("confidence_review") or {}
    maker = case.get("maker_id")
    pending = lg.review_pending(ext) and lg.status_of(case) in lg.PENDING
    conf["review"] = {"required": bool(cr.get("required")), "state": cr.get("state", "none"), "reviewed_by": cr.get("reviewed_by"),
                      "reviewed_at": cr.get("reviewed_at"), "comment": cr.get("comment"),
                      "can_review": bool(pending and has_perm(user, "case.approve") and maker != user.user_id),
                      "endpoint": f"/api/v2/cases/{case['case_id']}/confidence-review"}
    conf["label"] = "High" if conf["confidence_pct"] >= 95 else ("Sufficient" if conf["confidence_pct"] >= conf["threshold"] else "Below threshold")
    return conf


def _recommendation(case, ext):
    rec = repo.recommendations.get(case["case_id"])
    stp = ext.get("stp") or {}
    if rec is None and not ext.get("resolution_basis"):
        return None
    reasoning: List[str] = []
    summary = ext.get("resolution_basis") or (rec.rationale if rec else "")
    if rec is not None:
        reasoning = [f"{s.step_title}: {s.proof_detail}" for s in (rec.step_by_step_assessment or [])][:8]
    return {"summary": summary, "reasoning": reasoning, "confidence_label": "Model text is advisory. Decision confidence % above is computed by rules and is used by controls",
            "predicates": stp.get("predicates"), "source": "DETERMINISTIC" if ext.get("source") == "e2e" else "DEMO_FIXTURE"}
