"""Audited case actions for UI v2. Every state change goes through transition_case / the approval engine / the outbound port."""
from __future__ import annotations

import json
import hashlib
from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.security import DEMO_PERSONAS, get_persona
from app.db.models import V2NotificationModel, V2IdempotencyModel
from app.db.session import SessionLocal
from app.schemas.approval import ApprovalAction, ApprovalSubmission
from app.services.action_executor import action_executor
from app.services.approval_engine import approval_engine
from app.services.audit_service import audit_service
from app.services.data_loader import repo
from app.services.outbound_port import operation_mode
from app.services.state_machine import IllegalTransition, transition_case
from app.services.v2 import ext as xt
from app.services.v2 import logic as lg
from app.services.v2 import pages as pg
from app.services.v2 import pii
from app.services.v2.core import (
    V2Error, bad_state, invalid, not_found, now, iso, parse_ts, role_of, has_perm, require, person, ext_store, new_id,
    is_compliance, party_name, money, ROLE_LABELS,
)

POLICY_VERSION = "Approval policy v2.1"
MICRO_POLICY_VERSION = "Micro-repair policy v3.2"
META_MARK = " ||meta="


# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------
def _load(case_id: str) -> Dict[str, Any]:
    c = repo.get_case(case_id)
    if not c:
        raise not_found(f"Case {case_id}")
    return c


def actor_label(user) -> str:
    return f"{user.name} ({role_of(user)})"


def audit(case: Dict[str, Any], user, stage: str, action: str, text: str, tags: Optional[List[str]] = None,
          before: Optional[str] = None, after: Optional[str] = None, reason: Optional[str] = None,
          evidence_reviewed: Optional[int] = None, policy_version: Optional[str] = None, sod: Optional[str] = None,
          actor_id: Optional[str] = None, actor_role: Optional[str] = None):
    meta = {"before": before, "after": after, "reason": reason, "evidence_reviewed": evidence_reviewed,
            "policy_version": policy_version, "sod": sod}
    meta = {k: v for k, v in meta.items() if v is not None}
    details = text + (META_MARK + json.dumps(meta) if meta else "")
    audit_service.log_event(
        case_id=case["case_id"], correlation_id=case.get("uetr") or case["case_id"], stage_name=stage,
        actor_id=actor_id or user.user_id, actor_role=actor_role or role_of(user), action_name=action, details=details,
        control_tags=tags or [], amount=case.get("amount"), currency=case.get("currency"))


def touch(case: Dict[str, Any], ext: Dict[str, Any]):
    ext["last_change_at"] = iso(now())


def move(case: Dict[str, Any], to: str, user, reason: str, **kw):
    try:
        transition_case(case, to, actor=actor_label(user), reason=reason, **kw)
    except IllegalTransition as e:
        raise bad_state(str(e))


def notify(kind: str, title: str, text: str, case_id: Optional[str] = None, target_user: Optional[str] = None,
           target_role: Optional[str] = None):
    db = SessionLocal()
    try:
        db.add(V2NotificationModel(id=new_id("N"), target_user_id=target_user, target_role=target_role, kind=kind, case_id=case_id,
                                   title=title, text=text, created_at=iso(now()), read_by=[]))
        db.commit()
    finally:
        db.close()


def result(case_id: str, user, message: str, **extra) -> Dict[str, Any]:
    case = _load(case_id)
    ext = lg.ext_of(case)
    variant = lg.derive_variant(case, ext)
    out = {"ok": True, "case_id": case_id, "status": lg.status_of(case), "variant": variant, "message": message,
           "next": lg.next_action(case, ext, variant, user), "page_url": f"/api/v2/cases/{case_id}/page"}
    out.update(extra)
    return out


def _require_open(case: Dict[str, Any], what: str):
    st = lg.status_of(case)
    if st in lg.DONE:
        raise bad_state(f"Case is {st.replace('_', ' ').lower()}; cannot {what}.")


def _need(value: Optional[str], field: str, label: str) -> str:
    v = (value or "").strip()
    if not v:
        raise invalid(f"{label} is required", field)
    return v


def _map_engine_error(msg: str) -> V2Error:
    m = msg or ""
    if "Segregation of Duties" in m or "Dual Authorization violation" in m:
        return V2Error(403, "SOD_VIOLATION", m)
    if "Approval limit exceeded" in m:
        return V2Error(403, "LIMIT_EXCEEDED", m)
    if "not awaiting approval" in m:
        return bad_state(m)
    if "not found" in m:
        return not_found("Case")
    return V2Error(403, "FORBIDDEN", m)


def _least_loaded_approver(case: Dict[str, Any]) -> str:
    from app.services.v2.rows import all_cases, approver_for
    if float(case.get("amount") or 0) >= lg.DUAL_AUTH_THRESHOLD:
        return "RSK-7714"
    load = {"APR-3191": 0, "APR-3192": 0}
    for c in all_cases():
        if lg.status_of(c) in lg.PENDING:
            a = approver_for(c, lg.ext_of(c))
            if a in load:
                load[a] += 1
    return min(load, key=lambda k: (load[k], k))


# ----------------------------------------------------------------------------------------------
# assign
# ----------------------------------------------------------------------------------------------
def assign(case_id: str, user, assignee: Optional[str]) -> Dict[str, Any]:
    case = _load(case_id)
    ext = lg.ext_of(case)
    st = lg.status_of(case)
    if st in lg.DONE or st in lg.PENDING:
        raise bad_state(f"Case is {st.replace('_', ' ').lower()}; it cannot be assigned.")
    if is_compliance(case):
        raise bad_state("Compliance cases are managed in the Compliance workspace.")
    target = (assignee or "").strip()
    if target in ("", "queue", "none"):
        target = None
        require(user, "case.assign")
    elif target == "me" or target == user.user_id:
        require(user, "case.assign")
        target = user.user_id
    else:
        require(user, "case.reassign", "Only a Supervisor can reassign a case to someone else.")
        p = get_persona(target)
        if not p or role_of(p) not in ("OPERATOR", "SUPERVISOR"):
            raise invalid(f"'{target}' is not a Maker who can work this case", "assignee")
    previous = person(ext.get("assignee"))
    ext["assignee"] = target
    touch(case, ext)
    xt.persist_ext(case_id, ext)
    audit(case, user, "ASSIGNMENT", "CASE_ASSIGNED" if target else "CASE_RETURNED_TO_QUEUE",
          f"{user.name} {'assigned the case to ' + person(target)['name'] if target else 'returned the case to the queue'}.",
          ["Assignment recorded"], before=(previous or {}).get("name", "Unassigned"), after=(person(target) or {}).get("name", "Unassigned"))
    if target and target != user.user_id:
        notify("ASSIGNED", f"{case_id} assigned to you", f"{user.name} assigned {case_id} to you.", case_id, target_user=target)
    return result(case_id, user, "Case assigned." if target else "Case returned to the queue.", assignee=person(target), previous=previous)


# ----------------------------------------------------------------------------------------------
# maker actions
# ----------------------------------------------------------------------------------------------
def submit(case_id: str, user, handover_note: Optional[str], attachment_name: Optional[str]) -> Dict[str, Any]:
    require(user, "case.work")
    case = _load(case_id)
    ext = lg.ext_of(case)
    note = _need(handover_note, "handover_note", "Handover note")
    variant = lg.derive_variant(case, ext)
    if variant != "DECISION":
        raise bad_state(f"This case cannot be submitted for approval right now (it is in the '{variant.replace('_', ' ').lower()}' state).")
    t = iso(now())
    case["maker_id"] = user.user_id
    ext["handover"] = {"note": note, "by": person(user.user_id), "at": t, "attachment": ({"name": attachment_name.strip()} if attachment_name and attachment_name.strip() else None)}
    ext["submitted_at"] = t
    ext["approver_assigned"] = _least_loaded_approver(case)
    ext["returned"] = None
    ext["assignee"] = ext.get("assignee") or user.user_id
    conf = lg.confidence_of(case, ext)
    low = bool(conf and conf["applies"] and conf["extra_approval"])
    ext["confidence_review"] = ({"required": True, "state": "pending", "confidence_pct": conf["confidence_pct"], "coverage_pct": conf["coverage_pct"],
                                 "reasons": conf["reasons"], "routed_at": t} if low else {"required": False, "state": "none"})
    touch(case, ext)
    move(case, "PENDING_APPROVAL", user, f"Maker {user.name} submitted the repair for approval with a handover note.")
    case["expedite_ping"] = None
    repo.save_case(case)
    xt.persist_ext(case_id, ext)
    audit(case, user, "MAKER_SUBMIT", "MAKER_SUBMITTED_FOR_APPROVAL", f"{user.name} submitted {case_id} for approval. Handover note recorded.",
          ["Maker-Checker", "Handover note recorded"], before="VALIDATED", after="PENDING_APPROVAL", reason=note[:300],
          evidence_reviewed=len(ext.get("evidence") or []), policy_version=POLICY_VERSION, sod="Pending (checker must differ from maker)")
    if low:
        audit(case, user, "CONFIDENCE_GATE", "LOW_CONFIDENCE_ROUTED_FOR_EVIDENCE_REVIEW",
              f"Decision confidence {conf['confidence_pct']}% is below {conf['threshold']}%. {case_id} needs an independent evidence review before approval.",
              ["Confidence gate", "Extra approval required"], before="PENDING_APPROVAL", after="PENDING_APPROVAL", reason="; ".join(conf["reasons"])[:300],
              policy_version=POLICY_VERSION)
    ap = ext["approver_assigned"]
    notify("SUBMITTED", f"{case_id} awaiting your approval" + (" (evidence review needed)" if low else ""), f"{user.name} submitted {case_id} ({money(case['amount'], case['currency'])['display']}).", case_id, target_user=ap)
    return result(case_id, user, "Submitted for approval.")


def request_information(case_id: str, user, to: Any, method: Optional[str], message: Optional[str], draft: bool,
                        reply_due: Optional[str], escalate_at: Optional[str]) -> Dict[str, Any]:
    require(user, "case.work")
    case = _load(case_id)
    ext = lg.ext_of(case)
    st = lg.status_of(case)
    variant = lg.derive_variant(case, ext)
    if variant in ("APPROVAL", "HANDED_TO_BANK", "EXECUTED", "COMPLIANCE_HOLD") or st in lg.DONE:
        raise bad_state("Information cannot be requested in this state." + (" Do not contact the customer about a compliance alert." if variant == "COMPLIANCE_HOLD" else ""))
    msg = (message or "").strip()
    cp = ext.get("counterparty") or party_name(case.get("creditor_party"))
    to_obj = to if isinstance(to, dict) else {"party": (to or cp), "contact": ext.get("contact") or "Relationship manager", "role": "Relationship manager"}
    ri = dict(ext.get("request_info") or {})
    ri.update({"to": to_obj, "method": method or ri.get("method") or "Email", "message": msg or ri.get("message")})
    t = now()
    if draft:
        ri["state"] = "draft"
        ri["draft_saved_at"] = iso(t)
        ext["request_info"] = ri
        touch(case, ext)
        xt.persist_ext(case_id, ext)
        audit(case, user, "INFO_REQUEST", "INFO_REQUEST_DRAFT_SAVED", f"{user.name} saved a draft information request for {case_id}.", ["Draft only, nothing sent"])
        return result(case_id, user, "Draft saved. Nothing was sent.", request_information=pg._request_info(case, ext))
    _need(msg, "message", "Message")
    rd = parse_ts(reply_due) if reply_due else None
    if reply_due and rd is None:
        raise invalid("reply_due must be an ISO timestamp", "reply_due")
    rd = rd or (t + timedelta(hours=2))
    ea = parse_ts(escalate_at) if escalate_at else None
    ea = ea or (rd + timedelta(minutes=15))
    if ea <= t:
        raise invalid("escalate_at must be in the future", "escalate_at")
    ri.update({"state": "sent", "sent_at": iso(t), "reply_due": iso(rd), "escalate_at": iso(ea), "sent_by": user.user_id, "message": msg})
    ext["request_info"] = ri
    ext["assignee"] = ext.get("assignee") or user.user_id
    touch(case, ext)
    if st in ("INGESTED", "CANONICALIZED", "VALIDATED", "RECOMMENDED", "RETURNED_FOR_REWORK") and st != "INVESTIGATING":
        move(case, "INVESTIGATING", user, "Information requested from the client; waiting for reply.")
        repo.save_case(case)
    xt.persist_ext(case_id, ext)
    audit(case, user, "INFO_REQUEST", "INFORMATION_REQUESTED", f"{user.name} requested information from {to_obj.get('party')} by {ri['method']} (simulated; nothing was actually sent).",
          ["Client contact simulated"], after=f"Reply due {iso(rd)}", reason=msg[:300])
    return result(case_id, user, "Request sent (simulated). Waiting for the reply.", request_information=pg._request_info(case, ext))


def reassess(case_id: str, user, note: Optional[str], provided: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    require(user, "case.work")
    case = _load(case_id)
    ext = lg.ext_of(case)
    _require_open(case, "reassess")
    if lg.status_of(case) in lg.PENDING:
        raise bad_state("The case is with an approver and cannot be reassessed.")
    rows = list(ext.get("evidence") or [])
    changed = False
    msgs = []
    provided = provided or {}
    for k, v in provided.items():
        sv = str(v or "").strip()
        if not sv:
            continue
        key = k.lower()
        for r in rows:
            if r["status"] == "missing" and (key in r["check"].lower().replace(" ", "_") or key.replace("_", " ") in r["check"].lower() or key in ("iban", "bic") and key in r["check"].lower()):
                if key == "iban" and not xt.iban_valid(sv):
                    msgs.append("The IBAN provided fails the mod-97 check; still missing.")
                    continue
                r.update({"status": "agree", "status_label": "Agree", "result": f"Provided by client: {sv}", "source": "Client reply",
                          "authority": "Client supplied", "checked_at": iso(now())})
                changed = True
                if key == "iban":
                    ext["change"] = xt.build_change("creditor_account.iban", "", sv, source="Client reply, checksum validated", risk="Low",
                                                    policy_basis="One approver", what_changes="Beneficiary IBAN supplied by client")
    missing = [r for r in rows if r["status"] == "missing"]
    ext["evidence"] = rows
    new_state = xt.evidence_state_from_rows(rows, None if (changed or not missing) else "missing")
    if not missing and not any(r["status"] == "differs" for r in rows):
        new_state = "complete"
    ext["evidence_state"] = new_state
    ri = ext.get("request_info") or {}
    if changed and ri:
        ri["state"] = "replied"
        ext["request_info"] = ri
    touch(case, ext)
    xt.persist_ext(case_id, ext)
    msg = "; ".join(msgs) if msgs else ("New information applied. Evidence is now complete." if new_state == "complete" and changed else
                                         "Reassessed. No new information found: required items are still missing." if new_state == "missing" else "Reassessed.")
    audit(case, user, "REASSESS", "CASE_REASSESSED", f"{user.name} reassessed {case_id}: {msg}", ["Evidence sufficiency re-evaluated"],
          after=new_state, reason=(note or None))
    return result(case_id, user, msg)


def escalate(case_id: str, user, to: Optional[str], reason: Optional[str]) -> Dict[str, Any]:
    require(user, "case.work")
    case = _load(case_id)
    ext = lg.ext_of(case)
    _require_open(case, "escalate")
    to = (to or "SENIOR_ANALYST").upper()
    if to not in ("SENIOR_ANALYST", "SUPERVISOR", "APPROVER"):
        raise invalid("to must be SENIOR_ANALYST, SUPERVISOR or APPROVER", "to")
    st = lg.status_of(case)
    reason = (reason or "").strip() or "Escalated by analyst"
    ext["escalation"] = {"to": to, "by": user.user_id, "at": iso(now()), "reason": reason}
    touch(case, ext)
    from app.services.state_machine import ALLOWED_TRANSITIONS
    if "ESCALATED" in ALLOWED_TRANSITIONS.get(st, frozenset()) and st != "ESCALATED":
        move(case, "ESCALATED", user, f"Escalated to {to.replace('_', ' ').lower()}: {reason}")
        repo.save_case(case)
    xt.persist_ext(case_id, ext)
    audit(case, user, "ESCALATION", "CASE_ESCALATED", f"{user.name} escalated {case_id} to {to.replace('_', ' ').lower()}.", ["Escalation recorded"],
          before=st, after=lg.status_of(case), reason=reason)
    role = {"SENIOR_ANALYST": "SUPERVISOR", "SUPERVISOR": "SUPERVISOR", "APPROVER": "OPERATIONS_APPROVER"}[to]
    notify("ESCALATED", f"{case_id} escalated", f"{user.name}: {reason}", case_id, target_role=role)
    return result(case_id, user, f"Escalated to {to.replace('_', ' ').lower()}.")


def start_verification(case_id: str, user, note: Optional[str]) -> Dict[str, Any]:
    require(user, "case.work")
    case = _load(case_id)
    ext = lg.ext_of(case)
    _require_open(case, "start verification")
    st = lg.status_of(case)
    if st in lg.PENDING or st in ("STATUS_UNKNOWN", "APPROVED"):
        raise bad_state("Verification can only start on a case that is being worked.")
    if st != "INVESTIGATING":
        move(case, "INVESTIGATING", user, "Verification started by analyst.")
        repo.save_case(case)
    ext["verification"] = {"started_by": user.user_id, "at": iso(now()), "note": note}
    ext["assignee"] = ext.get("assignee") or user.user_id
    touch(case, ext)
    xt.persist_ext(case_id, ext)
    audit(case, user, "VERIFICATION", "VERIFICATION_STARTED", f"{user.name} started verification on {case_id}.", ["Verification opened"], before=st, after="INVESTIGATING", reason=note)
    return result(case_id, user, "Verification started.")


def disambiguate(case_id: str, user, candidate_id: Optional[str], rationale: Optional[str]) -> Dict[str, Any]:
    require(user, "case.work")
    case = _load(case_id)
    ext = lg.ext_of(case)
    _require_open(case, "disambiguate")
    why = _need(rationale, "rationale", "Rationale")
    cid = _need(candidate_id, "candidate_id", "Candidate")
    cands = list((ext.get("conflict") or {}).get("candidates") or [])
    rec = repo.recommendations.get(case_id)
    if not cands and rec is not None:
        cands = [{"id": h.hypothesis_id, "title": h.title, "value": h.candidate_value} for h in (rec.hypothesis_ranking or [])]
    pick = next((c for c in cands if c.get("id") == cid), None)
    if pick is None:
        raise invalid(f"Unknown candidate '{cid}'", "candidate_id")
    ext["disambiguation"] = {"candidate_id": cid, "value": pick.get("value"), "rationale": why, "by": user.user_id, "at": iso(now())}
    if pick.get("value"):
        old = account_or(case)
        ext["change"] = xt.build_change("creditor_account.iban", old, pick["value"], source="Analyst disambiguation", risk="Medium",
                                        policy_basis="One approver; analyst chose between conflicting sources", what_changes="Beneficiary account confirmed by analyst")
        ext["evidence_state"] = "complete"
        for r in ext.get("evidence") or []:
            if r["status"] == "differs":
                r["status"], r["status_label"] = "info", "Resolved by analyst"
    touch(case, ext)
    xt.persist_ext(case_id, ext)
    audit(case, user, "HITL_DISAMBIGUATION", "HYPOTHESIS_DISAMBIGUATION", f"{user.name} selected candidate {cid} for {case_id}.", ["Human disambiguation"], after=str(pick.get("value")), reason=why)
    return result(case_id, user, "Candidate recorded. The case is ready for a decision.")


def account_or(case):
    a = case.get("creditor_account") or {}
    return str(a.get("iban") or a.get("account_number") or "") if isinstance(a, dict) else str(a)


# ----------------------------------------------------------------------------------------------
# status checks (simulated) / ping
# ----------------------------------------------------------------------------------------------
def check_status(case_id: str, user) -> Dict[str, Any]:
    require(user, "case.work")
    case = _load(case_id)
    ext = lg.ext_of(case)
    st = lg.status_of(case)
    if st not in ("STATUS_UNKNOWN", "DISPATCHED"):
        raise bad_state("Status checks apply to payments handed to the bank.")
    n = int(ext.get("status_checks") or 0)
    script = ext.get("sim_script")
    if script:
        res = script[min(n, len(script) - 1)]
    else:
        from app.services.simulated_bank import _behaviour
        res = "STILL_UNKNOWN" if _behaviour(case_id) == "SILENT" or st == "DISPATCHED" else "ACCEPTED"
    ext["status_checks"] = n + 1
    ext["last_status_check"] = {"at": iso(now()), "result": res, "by": user.user_id, "simulated": True,
                                "text": {"STILL_UNKNOWN": "Simulated bank: no answer yet. Still unknown. Do not resend.",
                                         "ACCEPTED": "Simulated bank: payment was accepted by the network."}.get(res, res)}
    touch(case, ext)
    xt.persist_ext(case_id, ext)
    audit(case, user, "STATUS_CHECK", "STATUS_CHECK_REQUESTED", f"{user.name} checked the status of {case_id} with the bank (simulated). Result: {res}. Nothing was resent.",
          ["Simulated bank", "No resend"], before=st, after=res)
    moved = False
    if res == "ACCEPTED" and st == "STATUS_UNKNOWN" and settings.PEX_DEMO and settings.BANK_COMM_MODE == "SIMULATED":
        # The simulated bank answers through the same signed inbound path a real bank would use.
        from app.services.simulated_bank import _send
        ref = "SIMACK-" + hashlib.sha256(case_id.encode()).hexdigest()[:10].upper()
        _send(case_id, "EXECUTED_CONFIRMED", ref)
        moved = True
    return result(case_id, user, ext["last_status_check"]["text"] + (" The bank then confirmed execution (signed bank signal)." if moved else ""),
                  check={"result": res, "checked_at": ext["last_status_check"]["at"], "simulated": True}, resend="blocked")


def request_bank_status(case_id: str, user, note: Optional[str]) -> Dict[str, Any]:
    require(user, "case.work")
    case = _load(case_id)
    ext = lg.ext_of(case)
    if lg.status_of(case) not in ("STATUS_UNKNOWN", "DISPATCHED"):
        raise bad_state("A bank status request applies to payments handed to the bank.")
    reqs = list(ext.get("bank_status_requests") or [])
    reqs.append({"at": iso(now()), "by": user.user_id, "note": note})
    ext["bank_status_requests"] = reqs
    touch(case, ext)
    xt.persist_ext(case_id, ext)
    audit(case, user, "STATUS_CHECK", "BANK_STATUS_REQUESTED", f"{user.name} asked bank operations for the status of {case_id} (simulated message).", ["Simulated bank", "No resend"], reason=note)
    notify("STATUS", f"Status requested for {case_id}", f"{user.name} requested status from bank operations (simulated).", case_id, target_role="SUPERVISOR")
    return result(case_id, user, "Status request sent to bank operations (simulated).")


def ping(case_id: str, user, note: Optional[str]) -> Dict[str, Any]:
    require(user, "case.work")
    case = _load(case_id)
    ext = lg.ext_of(case)
    st = lg.status_of(case)
    if st not in ("PENDING_APPROVAL", "AWAITING_SECOND_APPROVAL", "APPROVED"):
        raise bad_state(f"Cannot ping an approver for a case in {st.replace('_', ' ').lower()}.")
    if st == "APPROVED":
        role, title = "OPERATIONS_APPROVER", "Operations Approver (dispatch release)"
    elif is_compliance(case):
        role, title = "COMPLIANCE_APPROVER", "Compliance Officer"
    elif float(case.get("amount") or 0) >= lg.DUAL_AUTH_THRESHOLD or st == "AWAITING_SECOND_APPROVAL":
        role, title = "RISK_APPROVER", "Risk Approver (tier 2)"
    else:
        role, title = "OPERATIONS_APPROVER", "Operations Approver (tier 1)"
    text = (note or "").strip() or "Cutoff approaching. Please prioritise approval."
    case["expedite_ping"] = {"sender_id": user.user_id, "sender_name": user.name, "sender_role": role_of(user), "target_role": role,
                             "target_role_title": title, "timestamp": iso(now()), "note": text, "status": "UNREAD"}
    repo.save_case(case)
    touch(case, ext)
    xt.persist_ext(case_id, ext)
    audit(case, user, "SLA_EXPEDITE_ESCALATION", "EXPEDITE_PING_SENT", f"{user.name} pinged {title} to expedite {case_id}.", ["Expedite ping"], reason=text)
    target_user = ext.get("approver_assigned") if role in ("OPERATIONS_APPROVER", "RISK_APPROVER") else None
    notify("PING", f"Expedite: {case_id}", f"{user.name}: {text}", case_id, target_user=target_user, target_role=None if target_user else role)
    return result(case_id, user, f"{title} notified.", ping=case["expedite_ping"])


# ----------------------------------------------------------------------------------------------
# checker actions
# ----------------------------------------------------------------------------------------------
def _gate_or_raise(case, user, for_decline: bool = False):
    ok, code, msg = lg.approve_gate(case, user, for_decline)
    if not ok:
        status = 409 if code == "INVALID_STATE" else 403
        if code in ("SOD_VIOLATION", "LIMIT_EXCEEDED"):
            try:
                audit(case, user, "HITL_APPROVAL", "APPROVAL_BLOCKED", f"Approval of {case['case_id']} by {user.name} was blocked: {msg}",
                      ["Control blocked the action", code], before=lg.status_of(case), after=lg.status_of(case), reason=msg,
                      sod=("Failed: " + msg) if code == "SOD_VIOLATION" else None)
            except Exception:  # pragma: no cover
                pass
        raise V2Error(status, code, msg)


def pii_reveal(case_id: str, user, reason: Optional[str]) -> Dict[str, Any]:
    """Show real names, IBANs and accounts on this case to the caller for a short window. Reason required; always audited."""
    require(user, "pii.reveal")
    if not pii.enabled():
        raise bad_state("Personal-data masking is switched off, so there is nothing to reveal.")
    case = _load(case_id)
    ext = lg.ext_of(case)
    r = _need(reason, "reason", "Reason")
    if len(r) < pii.MIN_REASON:
        raise invalid(f"Please give a reason of at least {pii.MIN_REASON} characters.", "reason")
    t = now()
    grants = list(ext.get("pii_reveals") or [])
    grants.append({"user_id": user.user_id, "name": user.name, "reason": r[:300], "at": iso(t), "expires_at": iso(t + timedelta(minutes=pii.REVEAL_MINUTES))})
    ext["pii_reveals"] = grants[-50:]
    touch(case, ext)
    xt.persist_ext(case_id, ext)
    audit(case, user, "PII_ACCESS", "PII_REVEALED", f"{user.name} ({ROLE_LABELS.get(role_of(user), role_of(user))}) revealed personal data on {case_id} for {pii.REVEAL_MINUTES} minutes.",
          ["PII reveal", "Reason recorded", "Time-limited"], before=lg.status_of(case), after=lg.status_of(case), reason=r[:300])
    return result(case_id, user, f"Real values are shown to you for {pii.REVEAL_MINUTES} minutes. This access is logged.")


def pii_hide(case_id: str, user) -> Dict[str, Any]:
    require(user, "pii.reveal")
    case = _load(case_id)
    ext = lg.ext_of(case)
    t = iso(now())
    changed = False
    for g in ext.get("pii_reveals") or []:
        if g.get("user_id") == user.user_id and (parse_ts(g.get("expires_at")) or now()) > now():
            g["expires_at"] = t
            g["hidden_at"] = t
            changed = True
    if changed:
        xt.persist_ext(case_id, ext)
        audit(case, user, "PII_ACCESS", "PII_HIDDEN", f"{user.name} hid personal data on {case_id}.", ["PII reveal ended"], before=lg.status_of(case), after=lg.status_of(case))
    return result(case_id, user, "Personal data is hidden again.")


def confidence_review(case_id: str, user, decision: Optional[str], comment: Optional[str]) -> Dict[str, Any]:
    """Independent evidence review for a low-confidence case (same idea as the compliance second review).
    Confirming does NOT approve: it unlocks the normal approval, which must be done by a different person."""
    require(user, "case.approve")
    case = _load(case_id)
    ext = lg.ext_of(case)
    if lg.status_of(case) not in lg.PENDING or not lg.review_pending(ext):
        raise bad_state("This case has no open evidence review.")
    if case.get("maker_id") and case["maker_id"] == user.user_id:
        raise V2Error(403, "SOD_VIOLATION", "You prepared this repair. Someone else must review its evidence.")
    d = (decision or "").strip().lower()
    if d != "confirm":
        raise invalid("decision must be 'confirm'. To send it back, use Return to Maker.", "decision")
    cm = _need(comment, "comment", "Review comment")
    cr = dict(ext.get("confidence_review") or {})
    cr.update({"state": "confirmed", "reviewed_by": person(user.user_id), "reviewed_at": iso(now()), "comment": cm})
    ext["confidence_review"] = cr
    touch(case, ext)
    xt.persist_ext(case_id, ext)
    audit(case, user, "CONFIDENCE_GATE", "EVIDENCE_REVIEW_CONFIRMED",
          f"{user.name} reviewed the evidence on {case_id} (confidence {cr.get('confidence_pct')}%). A different approver must now authorise the handoff.",
          ["Confidence gate", "Independent evidence review", "Segregation of duties"], before=lg.status_of(case), after=lg.status_of(case), reason=cm[:300],
          policy_version=POLICY_VERSION, sod="Reviewer must differ from maker and from the final approver")
    notify("SUBMITTED", f"{case_id} ready for approval", f"{user.name} completed the evidence review. Awaiting a different approver.", case_id, target_role="RISK_APPROVER")
    notify("SUBMITTED", f"{case_id} ready for approval", f"{user.name} completed the evidence review. Awaiting a different approver.", case_id, target_role="OPERATIONS_APPROVER")
    return result(case_id, user, "Evidence review recorded. The case still needs approval from a different approver.")


def _handoff(case_id: str, user, ext: Dict[str, Any]) -> Dict[str, Any]:
    ok, msg, contract, receipt = action_executor.execute_governed_action(case_id=case_id, idempotency_key=None)
    case = _load(case_id)
    if not ok:
        raise bad_state(msg)
    ext["handoff_id"] = f"HND-{int(hashlib.sha256((case_id + str(iso(now()))).encode()).hexdigest()[:8], 16) % 90000 + 10000}"
    return {"message": msg, "mode": operation_mode()}


def approve(case_id: str, user, reviewed: Any, comment: Optional[str]) -> Dict[str, Any]:
    case = _load(case_id)
    if reviewed is not True:
        raise invalid("You must confirm you reviewed the change summary and evidence (reviewed=true).", "reviewed")
    _gate_or_raise(case, user)
    ext = lg.ext_of(case)
    before = lg.status_of(case)
    ok, msg, record, nxt = approval_engine.process_approval_action(
        ApprovalSubmission(case_id=case_id, action=ApprovalAction.APPROVE, comments=(comment or "").strip() or "Reviewed change summary and evidence; approved."),
        approver_id=user.user_id)
    if not ok:
        raise _map_engine_error(msg)
    case = _load(case_id)
    nxt_v = lg.status_of(case)
    step = record.step_number if record else 1
    audit(case, user, "HITL_APPROVAL", "APPROVED_FOR_BANK_HANDOFF" if nxt_v == "APPROVED" else "FIRST_APPROVAL_RECORDED",
          f"{user.name} reviewed the change summary and evidence and approved {case_id} (level {step}).",
          ["Segregation of duties verified", "Review acknowledged", "Governance gate cleared"], before=before, after=nxt_v,
          reason=(comment or None), evidence_reviewed=len(ext.get("evidence") or []), policy_version=POLICY_VERSION,
          sod=lg.sod_block(case, user)["text"] if case.get("maker_id") else "No maker (system-routed)")
    ext["last_approver"] = user.user_id
    touch(case, ext)
    info: Dict[str, Any] = {}
    if nxt_v == "APPROVED":
        info = _handoff(case_id, user, ext)
    xt.persist_ext(case_id, ext)
    case = _load(case_id)
    st = lg.status_of(case)
    if st == "AWAITING_SECOND_APPROVAL":
        m = "First approval recorded. A different tier-2 approver must sign (dual authorisation)."
        notify("SUBMITTED", f"{case_id} awaiting second approval", f"{user.name} gave first approval.", case_id, target_role="RISK_APPROVER")
    elif st == "DISPATCHED":
        m = "Approved. Handed to the bank system (simulated); waiting for bank confirmation. Not yet executed."
    elif st == "SHADOW_RECORDED":
        m = "Approved. Shadow mode: recorded only, nothing was sent to the bank."
    else:
        m = info.get("message") or "Approved."
    if case.get("maker_id") and case["maker_id"] != user.user_id:
        notify("APPROVED", f"{case_id} approved", m, case_id, target_user=case["maker_id"])
    return result(case_id, user, m, mode=operation_mode(), handoff=({"handoff_id": ext.get("handoff_id")} if st == "DISPATCHED" else None))


def _checker_decline(case_id: str, user, action: ApprovalAction, reason_code: Optional[str], comment: Optional[str], label: str) -> Dict[str, Any]:
    case = _load(case_id)
    rc = _need(reason_code, "reason_code", "Reason code")
    cm = _need(comment, "comment", "Comment")
    _gate_or_raise(case, user, for_decline=True)
    ext = lg.ext_of(case)
    before = lg.status_of(case)
    ok, msg, record, nxt = approval_engine.process_approval_action(
        ApprovalSubmission(case_id=case_id, action=action, comments=f"[{rc}] {cm}"), approver_id=user.user_id)
    if not ok:
        raise _map_engine_error(msg)
    case = _load(case_id)
    if action == ApprovalAction.RETURN_TO_MAKER:
        ext["returned"] = {"by": user.name, "by_id": user.user_id, "at": iso(now()), "comment": cm, "reason_code": rc}
        if case.get("maker_id"):
            ext["assignee"] = case["maker_id"]
    touch(case, ext)
    xt.persist_ext(case_id, ext)
    audit(case, user, "HITL_APPROVAL", f"{label.upper().replace(' ', '_')}", f"{user.name} {label} {case_id}.", ["Segregation of duties verified"],
          before=before, after=lg.status_of(case), reason=f"[{rc}] {cm}", evidence_reviewed=len(ext.get("evidence") or []),
          policy_version=POLICY_VERSION, sod="Passed")
    if action == ApprovalAction.RETURN_TO_MAKER and case.get("maker_id"):
        notify("RETURNED", f"{case_id} returned to you", f"{user.name}: {cm}", case_id, target_user=case["maker_id"])
    return result(case_id, user, "Returned to the Maker." if action == ApprovalAction.RETURN_TO_MAKER else "Rejected. The case will not be released.")


def return_to_maker(case_id: str, user, reason_code, comment):
    return _checker_decline(case_id, user, ApprovalAction.RETURN_TO_MAKER, reason_code, comment, "returned to maker")


def reject(case_id: str, user, reason_code, comment):
    return _checker_decline(case_id, user, ApprovalAction.REJECT, reason_code, comment, "rejected")


# ----------------------------------------------------------------------------------------------
# compliance
# ----------------------------------------------------------------------------------------------
def _ensure_pending(case, user, ext):
    st = lg.status_of(case)
    if st in lg.PENDING:
        return
    if st not in lg.WORKABLE:
        raise bad_state(f"Case is {st.replace('_', ' ').lower()}; a compliance decision is not possible.")
    move(case, "PENDING_APPROVAL", user, "Compliance decision requested on this case.")
    repo.save_case(case)


def compliance_decision(case_id: str, user, decision: Optional[str], reason_code: Optional[str], comment: Optional[str]) -> Dict[str, Any]:
    require(user, "compliance.decide")
    case = _load(case_id)
    ext = lg.ext_of(case)
    if lg.derive_variant(case, ext) != "COMPLIANCE_HOLD":
        raise bad_state("This case has no open compliance hold.")
    d = (decision or "").strip().lower()
    if d not in ("release", "confirm_block", "escalate"):
        raise invalid("decision must be release, confirm_block or escalate", "decision")
    rc = _need(reason_code, "reason_code", "Reason code")
    cm = _need(comment, "comment", "Comment")
    cd = dict(ext.get("compliance") or {})
    notes = list(cd.get("notes") or [])
    notes.append({"by": user.name, "at": iso(now()), "text": f"[{rc}] {cm}"})
    cd["notes"] = notes
    before = lg.status_of(case)
    sr = dict(cd.get("second_review") or {"required": False, "state": "none", "first_reviewer": None})

    if d == "escalate":
        cd["escalated"] = True
        cd["decision"] = {"decision": "escalate", "by": user.user_id, "at": iso(now()), "reason_code": rc}
        ext["compliance"] = cd
        st = lg.status_of(case)
        from app.services.state_machine import ALLOWED_TRANSITIONS
        if "ESCALATED" in ALLOWED_TRANSITIONS.get(st, frozenset()) and st != "ESCALATED":
            move(case, "ESCALATED", user, "Escalated to Senior Compliance.")
            repo.save_case(case)
        touch(case, ext)
        xt.persist_ext(case_id, ext)
        audit(case, user, "COMPLIANCE_DECISION", "COMPLIANCE_ESCALATED", f"{user.name} escalated {case_id} to Senior Compliance.", ["Compliance decision"], before=before, after=lg.status_of(case), reason=f"[{rc}] {cm}")
        notify("ESCALATED", f"{case_id} escalated to Senior Compliance", cm, case_id, target_role="RISK_APPROVER")
        return result(case_id, user, "Escalated to Senior Compliance.", second_review=sr)

    if d == "confirm_block":
        if sr.get("state") != "pending":
            sr = {"required": True, "state": "pending", "first_reviewer": person(user.user_id), "first_at": iso(now()), "reason_code": rc, "comment": cm}
            cd["second_review"] = sr
            ext["compliance"] = cd
            touch(case, ext)
            xt.persist_ext(case_id, ext)
            audit(case, user, "COMPLIANCE_DECISION", "COMPLIANCE_BLOCK_FIRST_REVIEW", f"{user.name} confirmed the match on {case_id}; a second reviewer must confirm before the payment is blocked.",
                  ["Four-eyes", "Second reviewer required"], before=before, after="Awaiting second reviewer", reason=f"[{rc}] {cm}")
            notify("PING", f"Second review needed: {case_id}", f"{user.name} confirmed a sanctions match. A second reviewer must confirm.", case_id, target_role="COMPLIANCE_APPROVER")
            return result(case_id, user, "First review recorded. A second reviewer must confirm before the payment is blocked.", second_review=sr)
        if (sr.get("first_reviewer") or {}).get("user_id") == user.user_id:
            raise V2Error(403, "SOD_VIOLATION", "The second reviewer must be a different person from the first reviewer.")
        _ensure_pending(case, user, ext)
        ok, msg, record, nxt = approval_engine.process_approval_action(
            ApprovalSubmission(case_id=case_id, action=ApprovalAction.REJECT, comments=f"[{rc}] {cm} (second review)"), approver_id=user.user_id)
        if not ok:
            raise _map_engine_error(msg)
        sr.update({"state": "done", "second_reviewer": person(user.user_id), "second_at": iso(now())})
        cd["second_review"] = sr
        cd["decision"] = {"decision": "confirm_block", "by": user.user_id, "at": iso(now()), "reason_code": rc}
        ext["compliance"] = cd
        case = _load(case_id)
        touch(case, ext)
        xt.persist_ext(case_id, ext)
        audit(case, user, "COMPLIANCE_DECISION", "COMPLIANCE_BLOCK_CONFIRMED", f"{user.name} confirmed the block on {case_id} as second reviewer. Payment will not be released.",
              ["Four-eyes", "Compliance decision"], before=before, after=lg.status_of(case), reason=f"[{rc}] {cm}", policy_version=POLICY_VERSION, sod="Passed (two different reviewers)")
        return result(case_id, user, "Match confirmed by a second reviewer. The payment is blocked and will not be released.", second_review=sr)

    # release: the compliance officer clears the screening hold only. The payment then goes back
    # through the normal approval queue; compliance never hands a payment to the bank itself.
    _ensure_pending(case, user, ext)
    case = _load(case_id)
    cd["released"] = True
    cd["decision"] = {"decision": "release", "by": user.user_id, "at": iso(now()), "reason_code": rc}
    cd["released_by"] = person(user.user_id)
    cd["released_at"] = iso(now())
    ext["compliance"] = cd
    touch(case, ext)
    xt.persist_ext(case_id, ext)
    audit(case, user, "COMPLIANCE_DECISION", "COMPLIANCE_HOLD_RELEASED", f"{user.name} cleared the screening hold on {case_id} (false match). The payment returns to the approval queue; nothing was handed to the bank.",
          ["Compliance decision", "False positive cleared", "Returned to approval"], before=before, after=lg.status_of(case), reason=f"[{rc}] {cm}", policy_version=POLICY_VERSION, sod="Passed")
    notify("APPROVAL", f"{case_id} ready for approval", f"{user.name} cleared the sanctions hold. A Risk Approver must authorise before any bank handoff.", case_id, target_role="RISK_APPROVER")
    return result(case_id, user, "Hold released. The payment is back in the approval queue; it is not handed to the bank until an approver authorises it.")


# ----------------------------------------------------------------------------------------------
# notifications
# ----------------------------------------------------------------------------------------------
def list_notifications(user) -> Dict[str, Any]:
    r = role_of(user)
    db = SessionLocal()
    try:
        rows = db.query(V2NotificationModel).order_by(V2NotificationModel.created_at.desc()).limit(300).all()
        items = []
        for n in rows:
            if (n.target_user_id and n.target_user_id == user.user_id) or (n.target_role and n.target_role == r):
                items.append({"id": n.id, "at": n.created_at, "kind": n.kind, "case_id": n.case_id, "title": n.title, "text": n.text,
                              "read": user.user_id in (n.read_by or [])})
        return {"unread": sum(1 for i in items if not i["read"]), "items": items[:50]}
    finally:
        db.close()


def mark_read(user, nid: str) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        n = db.query(V2NotificationModel).filter(V2NotificationModel.id == nid).first()
        if not n:
            raise not_found("Notification")
        rb = list(n.read_by or [])
        if user.user_id not in rb:
            rb.append(user.user_id)
            n.read_by = rb
            db.commit()
        return {"ok": True, "id": nid}
    finally:
        db.close()


# ----------------------------------------------------------------------------------------------
# idempotency (header based)
# ----------------------------------------------------------------------------------------------
def with_idempotency(key: Optional[str], user, fn):
    if not key:
        return fn()
    k = f"{user.user_id}:{key}"[:190]
    db = SessionLocal()
    try:
        row = db.query(V2IdempotencyModel).filter(V2IdempotencyModel.key == k).first()
        if row:
            out = dict(row.response or {})
            out["replayed"] = True
            return out
    finally:
        db.close()
    out = fn()
    db = SessionLocal()
    try:
        db.add(V2IdempotencyModel(key=k, response=json.loads(json.dumps(out, default=str)), created_at=iso(now())))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    return out
