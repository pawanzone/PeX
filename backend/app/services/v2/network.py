"""Network cases: investigations (camt.110 / camt.111) and recalls (camt.056 / camt.029) exchanged with other banks.

Rules this module enforces
  - A person drafts; a different approver authorises. At or above the dual-authorisation amount (policy) two different approvers are needed.
  - Raising or answering an investigation, and anything about a cancellation, leaves PeX only after authorisation, except a plain
    outbound investigation request (an information request), which goes out when raised.
  - PeX never moves money. An accepted recall only asks the bank system to return the funds (hand-off); a person records the bank's confirmation.
  - The network is simulated: "sending" records the XML; a counterparty reply is fed back through the same inbox a real one would use.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.db.models import V2NetworkCaseModel as M
from app.db.session import SessionLocal
from app.services.audit_service import audit_service
from app.services.data_loader import repo
from app.services.v2 import logic as lg
from app.services.v2 import swift_msgs as sm
from app.services.v2.core import V2Error, bad_state, has_perm, iso, not_found, now, person, require, role_of

RESPONSE_HOURS = 48
KINDS = ("INVESTIGATION", "RECALL")
OPEN_WAITING_US = ("NEW", "DRAFTED", "PART_APPROVED")
LABELS = {"NEW": "New", "DRAFTED": "Awaiting authorisation", "PART_APPROVED": "Second approval needed", "SENT": "Sent", "REPLY_RECEIVED": "Reply received",
          "AWAITING_BANK_RETURN": "Waiting for the bank to return funds", "CLOSED": "Closed"}


def response_hours() -> int:
    from app.services.v2 import policy
    return int(policy.get("network_response_hours"))


def _dual_amount() -> float:
    from app.services.v2 import policy
    return float(policy.get("dual_auth_amount"))


def reset_all() -> None:
    db = SessionLocal()
    try:
        db.query(M).delete()
        db.commit()
    finally:
        db.close()


# ---- helpers ------------------------------------------------------------------------------------------------------
def _case_by_uetr(uetr: str) -> Optional[Dict[str, Any]]:
    for c in repo._case_cache.values():
        if c.get("uetr") == uetr:
            return c
    return None


def _linked(uetr: str) -> Optional[Dict[str, Any]]:
    c = _case_by_uetr(uetr)
    if not c:
        return None
    return {"case_id": c["case_id"], "status": lg.status_of(c), "amount": c.get("amount"), "currency": c.get("currency"), "rail": c.get("payment_rail"), "link": f"/cases/{c['case_id']}"}


def _new_id(db, kind: str) -> str:
    tag = "INV" if kind == "INVESTIGATION" else "RCL"
    n = db.query(M).filter(M.kind == kind).count() + 1
    while db.query(M).filter(M.id == f"NET-{tag}-{n:04d}").first():
        n += 1
    return f"NET-{tag}-{n:04d}"


def _audit(row: M, user, action: str, text: str) -> None:
    audit_service.log_event(case_id=row.id, correlation_id=row.id, stage_name="NETWORK_CASE", actor_id=user.user_id, actor_role=role_of(user), action_name=action,
                            details=text, control_tags=["Network case", row.kind.title()], amount=row.amount, currency=row.currency)


def _tl(row: M, user, action: str, text: str) -> None:
    row.timeline = list(row.timeline or []) + [{"at": iso(now()), "actor": (person(user.user_id) or {}).get("name", user.user_id) if user else "System", "action": action, "text": text}]


def _needed(row: M) -> int:
    return 2 if float(row.amount or 0) >= _dual_amount() else 1


def _overdue(row: M) -> bool:
    if not row.due_at:
        return False
    waiting = row.status in OPEN_WAITING_US or (row.direction == "OUTBOUND" and row.status == "SENT")
    return bool(waiting and row.due_at < iso(now()))


def _get(db, nid: str) -> M:
    r = db.query(M).filter(M.id == nid).first()
    if not r:
        raise not_found("Network case")
    return r


def _row(r: M) -> Dict[str, Any]:
    return {"id": r.id, "kind": r.kind, "direction": r.direction, "status": r.status, "status_label": LABELS.get(r.status, r.status), "uetr": r.uetr,
            "counterparty_bic": r.counterparty_bic, "amount": r.amount, "currency": r.currency, "reason_code": r.reason_code,
            "reason_label": sm.label_for("camt.110" if r.kind == "INVESTIGATION" else "camt.056", "reason_code", r.reason_code), "created_at": r.created_at,
            "due_at": r.due_at, "overdue": _overdue(r), "linked_case_id": r.linked_case_id}


def detail(user, r: M) -> Dict[str, Any]:
    req_kind = "camt.110" if r.kind == "INVESTIGATION" else "camt.056"
    rsp_kind = sm.RESPONSES[req_kind]
    work, appr = has_perm(user, "network.work"), has_perm(user, "network.approve")
    approvals = list(r.approvals or [])
    can_auth = bool(appr and r.status in ("DRAFTED", "PART_APPROVED") and r.drafted_by != user.user_id and user.user_id not in [a["user_id"] for a in approvals])
    response = None
    if r.response_xml:
        f = sm.parse(r.response_xml)
        response = {"msg_type": rsp_kind, "title": sm.TITLES[rsp_kind], "xml": r.response_xml, "fields": f, "outcome": r.response_outcome,
                    "outcome_label": sm.label_for(rsp_kind, "status_code", r.response_outcome), "drafted_by": person(r.drafted_by) if r.drafted_by else None}
    elif r.response_outcome:
        response = {"msg_type": rsp_kind, "title": sm.TITLES[rsp_kind], "xml": None, "fields": None, "outcome": r.response_outcome, "draft": True,
                    "outcome_label": sm.label_for(rsp_kind, "status_code", r.response_outcome), "reason_code": r.response_reason, "text": r.response_text,
                    "drafted_by": person(r.drafted_by) if r.drafted_by else None}
    return {
        **_row(r), "uetr_standard": sm.is_standard_uetr(r.uetr), "case_ref": r.case_ref, "message_id": r.message_id, "narrative": r.narrative, "warnings": list(r.warnings or []),
        "linked_case": _linked(r.uetr),
        "request": {"msg_type": req_kind, "title": sm.TITLES[req_kind], "xml": r.request_xml, "fields": sm.parse(r.request_xml)},
        "response": response,
        "approvals": approvals, "approvals_needed": _needed(r), "dual_amount": _dual_amount(),
        "handoff": r.handoff, "timeline": list(r.timeline or []), "money_moved": False,
        "codes": {"outcomes": sm.INV_STATUS if r.kind == "INVESTIGATION" else sm.RECALL_STATUS,
                  "reject_reasons": sm.RECALL_REJECT, "accept_reasons": sm.RECALL_REASONS},
        "actions": {"can_draft": bool(work and r.direction == "INBOUND" and r.status in ("NEW", "DRAFTED")), "can_authorise": can_auth,
                    "can_simulate_reply": bool(work and r.direction == "OUTBOUND" and r.status == "SENT"),
                    "can_record_return": bool(work and r.status == "AWAITING_BANK_RETURN"),
                    "can_close": bool(work and (r.status == "REPLY_RECEIVED" or (r.direction == "INBOUND" and r.status == "SENT")))},
    }


# ---- reads --------------------------------------------------------------------------------------------------------
def listing(user, kind: Optional[str] = None, direction: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
    require(user, "network.read", "Your role cannot see network cases.")
    db = SessionLocal()
    try:
        rows = db.query(M).order_by(M.created_at.desc(), M.id.desc()).all()
        items = [r for r in rows if (not kind or r.kind == kind) and (not direction or r.direction == direction) and (not status or r.status == status)]
        c = {"open": sum(1 for r in rows if r.status != "CLOSED"), "overdue": sum(1 for r in rows if _overdue(r)), "investigations": sum(1 for r in rows if r.kind == "INVESTIGATION"),
             "recalls": sum(1 for r in rows if r.kind == "RECALL"), "inbound": sum(1 for r in rows if r.direction == "INBOUND"), "outbound": sum(1 for r in rows if r.direction == "OUTBOUND"),
             "awaiting_bank": sum(1 for r in rows if r.status == "AWAITING_BANK_RETURN")}
        return {"items": [_row(r) for r in items], "counts": c, "own_bic": sm.OWN_BIC, "response_hours": response_hours(),
                "codes": {"investigation_reasons": sm.INV_REASONS, "recall_reasons": sm.RECALL_REASONS},
                "rule": "A person drafts, a different approver authorises. PeX never moves money; accepted recalls are handed to the bank system."}
    finally:
        db.close()


def get_detail(user, nid: str) -> Dict[str, Any]:
    require(user, "network.read", "Your role cannot see network cases.")
    db = SessionLocal()
    try:
        return detail(user, _get(db, nid))
    finally:
        db.close()


# ---- inbound ------------------------------------------------------------------------------------------------------
def receive(user, xml: str) -> Dict[str, Any]:
    """A message arrives. Requests open a case; a response is matched to the request we sent."""
    require(user, "network.work", "Only the operations team can receive messages into PeX.")
    try:
        p = sm.parse(xml)
    except sm.MessageError as e:
        raise V2Error(422, "INVALID_MESSAGE", "The message was refused: " + "; ".join(e.problems), problems=e.problems)
    problems: List[str] = []
    if p["receiver_bic"] != sm.OWN_BIC:
        problems.append(f"Receiver BIC {p['receiver_bic']} is not this bank ({sm.OWN_BIC}).")
    if problems:
        raise V2Error(422, "INVALID_MESSAGE", "The message was refused: " + "; ".join(problems), problems=problems)
    db = SessionLocal()
    try:
        if db.query(M).filter((M.message_id == p["message_id"]) | (M.response_message_id == p["message_id"])).first():
            raise V2Error(409, "DUPLICATE_MESSAGE", f"Message {p['message_id']} was already received.")
        if p["msg_type"] in sm.RESPONSES.values():
            return _receive_response(db, user, p, xml)
        kind = "INVESTIGATION" if p["msg_type"] == "camt.110" else "RECALL"
        warnings: List[str] = []
        link = _linked(p["uetr"])
        if not link:
            warnings.append("No matching payment case for this UETR. It may not be a payment PeX has handled.")
        if kind == "RECALL":
            other = db.query(M).filter(M.kind == "RECALL", M.uetr == p["uetr"], M.status != "CLOSED").first()
            if other:
                warnings.append(f"A recall for this payment is already open ({other.id}).")
        row = M(id=_new_id(db, kind), kind=kind, direction="INBOUND", status="NEW", uetr=p["uetr"], counterparty_bic=p["sender_bic"], case_ref=p["case_id"],
                message_id=p["message_id"], amount=p["amount"], currency=p["currency"], reason_code=p.get("reason_code"), narrative=p.get("narrative") or "",
                created_at=iso(now()), due_at=iso(now() + timedelta(hours=response_hours())), request_xml=xml.strip(), approvals=[], timeline=[], warnings=warnings,
                linked_case_id=link["case_id"] if link else None)
        _tl(row, user, "RECEIVED", f"{sm.TITLES[p['msg_type']]} {p['message_id']} received from {p['sender_bic']}.")
        db.add(row)
        db.commit()
        _audit(row, user, "NETWORK_RECEIVED", f"{user.name} received {p['msg_type']} {p['message_id']} from {p['sender_bic']} for UETR {p['uetr']}.")
        db.refresh(row)
        return detail(user, row)
    finally:
        db.close()


def _receive_response(db, user, p: Dict[str, Any], xml: str) -> Dict[str, Any]:
    row = db.query(M).filter(M.id == p["case_id"], M.direction == "OUTBOUND", M.status == "SENT").first()
    want = "camt.111" if row is not None and row.kind == "INVESTIGATION" else "camt.029"
    if row is None or row.uetr != p["uetr"] or p["msg_type"] != want:
        msg = "No open request of ours matches this response (case id, UETR and message type must all match)."
        raise V2Error(422, "INVALID_MESSAGE", "The message was refused: " + msg, problems=[msg])
    row.response_xml = xml.strip()
    row.response_message_id = p["message_id"]
    row.response_outcome = p["status_code"]
    row.response_reason = p.get("reason_code")
    row.response_text = p.get("narrative") or ""
    row.status = "REPLY_RECEIVED"
    _tl(row, user, "REPLY_RECEIVED", f"{sm.TITLES[p['msg_type']]} received from {p['sender_bic']}: {sm.label_for(p['msg_type'], 'status_code', p['status_code'])}.")
    db.commit()
    _audit(row, user, "NETWORK_REPLY_RECEIVED", f"Reply {p['msg_type']} {p['message_id']} received from {p['sender_bic']}: {p['status_code']}.")
    db.refresh(row)
    return detail(user, row)


def sample(user, kind: str, case_id: Optional[str]) -> Dict[str, Any]:
    """Demo only: build a realistic request from a real payment case and receive it."""
    require(user, "network.work", "Only the operations team can receive messages into PeX.")
    if kind not in KINDS:
        raise V2Error(422, "INVALID", "kind must be INVESTIGATION or RECALL.")
    c = repo.get_case(case_id) if case_id else next((x for x in repo._case_cache.values() if x.get("uetr")), None)
    if not c:
        raise not_found("Payment case")
    import uuid
    mt = "camt.110" if kind == "INVESTIGATION" else "camt.056"
    xml = sm.build(mt, message_id="SMP-" + uuid.uuid4().hex[:10].upper(), created_at=iso(now()), case_id="CNT-" + uuid.uuid4().hex[:6].upper(), sender_bic="CNTPDEFF", receiver_bic=sm.OWN_BIC,
                   uetr=c["uetr"], end_to_end_id=str(c.get("payment_ref") or c["case_id"]), amount=c.get("amount") or 1, currency=c.get("currency") or "EUR",
                   settlement_date=iso(now())[:10], reason_code="CRDT" if kind == "INVESTIGATION" else "DUPL",
                   narrative="Beneficiary says the credit has not arrived." if kind == "INVESTIGATION" else "Payment was sent twice by mistake.")
    return receive(user, xml)


# ---- drafting and authorising ------------------------------------------------------------------------------------
def draft(user, nid: str, outcome: str, reason_code: Optional[str], text: Optional[str]) -> Dict[str, Any]:
    require(user, "network.work", "Only the operations team can draft a reply.")
    db = SessionLocal()
    try:
        r = _get(db, nid)
        if r.direction != "INBOUND":
            raise bad_state("Outbound cases are drafted when they are raised.")
        if r.status not in ("NEW", "DRAFTED") or (r.approvals or []):
            raise bad_state(f"This case is {LABELS.get(r.status, r.status).lower()}; the reply can no longer be changed.")
        body = (text or "").strip()
        if r.kind == "INVESTIGATION":
            if outcome not in sm.INV_STATUS:
                raise V2Error(422, "INVALID", "Outcome must be one of: " + ", ".join(sm.INV_STATUS) + ".")
            if len(body) < 3:
                raise V2Error(422, "INVALID", "Say what you found, in a sentence.")
            reason_code = None
        else:
            if outcome not in sm.RECALL_STATUS:
                raise V2Error(422, "INVALID", "Outcome must be CNCL (accept) or RJCR (reject).")
            if outcome == "RJCR" and reason_code not in sm.RECALL_REJECT:
                raise V2Error(422, "INVALID", "A rejection needs a reason code: " + ", ".join(sm.RECALL_REJECT) + ".")
            if outcome == "CNCL" and reason_code and reason_code not in sm.ANSWER_REASONS:
                raise V2Error(422, "INVALID", "Unknown reason code.")
        r.response_outcome, r.response_reason, r.response_text = outcome, reason_code, body
        r.drafted_by = user.user_id
        r.status = "DRAFTED"
        _tl(r, user, "DRAFTED", f"Reply drafted: {outcome}{(' (' + reason_code + ')') if reason_code else ''}.")
        db.commit()
        _audit(r, user, "NETWORK_DRAFTED", f"{user.name} drafted the reply: {outcome}{(' ' + reason_code) if reason_code else ''}. {body[:160]}")
        db.refresh(r)
        return detail(user, r)
    finally:
        db.close()


def _reply_xml(r: M) -> str:
    rsp = sm.RESPONSES["camt.110" if r.kind == "INVESTIGATION" else "camt.056"]
    return sm.build(rsp, message_id="PEX-" + r.id + "-R", created_at=iso(now()), case_id=r.case_ref, sender_bic=sm.OWN_BIC, receiver_bic=r.counterparty_bic, uetr=r.uetr,
                    amount=r.amount, currency=r.currency, settlement_date=iso(now())[:10], reason_code=r.response_reason, narrative=r.response_text, status_code=r.response_outcome)


def authorise(user, nid: str, note: Optional[str]) -> Dict[str, Any]:
    require(user, "network.approve", "Only an approver can authorise a message to leave PeX.")
    db = SessionLocal()
    try:
        r = _get(db, nid)
        if r.status not in ("DRAFTED", "PART_APPROVED"):
            raise bad_state("There is nothing waiting for authorisation on this case.")
        if r.drafted_by == user.user_id:
            raise V2Error(403, "SOD_VIOLATION", "The person who drafted this cannot authorise it (four eyes).")
        approvals = list(r.approvals or [])
        if user.user_id in [a["user_id"] for a in approvals]:
            raise bad_state("You have already approved this; a different approver must give the second approval.")
        approvals.append({"user_id": user.user_id, "name": user.name, "role": role_of(user), "at": iso(now()), "note": (note or "").strip()})
        r.approvals = approvals
        needed = _needed(r)
        if len(approvals) < needed:
            r.status = "PART_APPROVED"
            _tl(r, user, "APPROVED", f"First of {needed} approvals given.")
            db.commit()
            _audit(r, user, "NETWORK_AUTHORISED", f"{user.name} gave approval {len(approvals)} of {needed}.")
            db.refresh(r)
            return detail(user, r)
        _tl(r, user, "APPROVED", f"Authorised ({len(approvals)} of {needed}).")
        _audit(r, user, "NETWORK_AUTHORISED", f"{user.name} gave the final approval ({len(approvals)} of {needed}).")
        if r.direction == "INBOUND":
            r.response_xml = _reply_xml(r)
            r.response_message_id = "PEX-" + r.id + "-R"
            if r.kind == "RECALL" and r.response_outcome == "CNCL":
                r.status = "AWAITING_BANK_RETURN"
                r.handoff = {"state": "RETURN_REQUESTED", "requested_at": iso(now()), "reference": None,
                             "note": "PeX has asked the bank system to return the funds. PeX does not move money; record the bank's confirmation when it arrives."}
                _tl(r, user, "SENT", f"Cancellation accepted and {sm.TITLES['camt.029']} sent. Return of funds requested from the bank system.")
            elif r.kind == "RECALL":
                r.status, r.closed_at = "CLOSED", iso(now())
                _tl(r, user, "SENT", f"Cancellation rejected and {sm.TITLES['camt.029']} sent. Case closed.")
            else:
                r.status = "SENT"
                _tl(r, user, "SENT", f"{sm.TITLES['camt.111']} sent to {r.counterparty_bic}.")
            _audit(r, user, "NETWORK_SENT", f"Reply {r.response_outcome} sent to {r.counterparty_bic} for UETR {r.uetr}.")
        else:
            r.status = "SENT"
            _tl(r, user, "SENT", f"{sm.TITLES['camt.056']} sent to {r.counterparty_bic}.")
            _audit(r, user, "NETWORK_SENT", f"Cancellation request sent to {r.counterparty_bic} for UETR {r.uetr}.")
        db.commit()
        db.refresh(r)
        return detail(user, r)
    finally:
        db.close()


# ---- outbound ----------------------------------------------------------------------------------------------------
def raise_outbound(user, kind: str, uetr: str, reason_code: str, narrative: str, counterparty_bic: str, case_id: Optional[str] = None) -> Dict[str, Any]:
    require(user, "network.work", "Only the operations team can raise a network case.")
    kind = (kind or "").upper()
    if kind not in KINDS:
        raise V2Error(422, "INVALID", "kind must be INVESTIGATION or RECALL.")
    problems: List[str] = []
    mt = "camt.110" if kind == "INVESTIGATION" else "camt.056"
    if reason_code not in sm.REASONS[mt]:
        problems.append(f"Reason code '{reason_code}' is not recognised for {mt}.")
    if not sm.BIC_RE.match(counterparty_bic or ""):
        problems.append(f"Counterparty BIC '{counterparty_bic}' is not a valid BIC.")
    if len((narrative or "").strip()) < 3:
        problems.append("Say why, in a sentence.")
    if problems:
        raise V2Error(422, "INVALID", " ".join(problems), problems=problems)
    c = repo.get_case(case_id) if (case_id and not uetr) else _case_by_uetr(uetr)
    if not c or not c.get("uetr"):
        raise not_found("Payment case")
    uetr = c["uetr"]
    db = SessionLocal()
    try:
        nid = _new_id(db, kind)
        xml = sm.build(mt, message_id="PEX-" + nid, created_at=iso(now()), case_id=nid, sender_bic=sm.OWN_BIC, receiver_bic=counterparty_bic, uetr=uetr,
                       end_to_end_id=str(c.get("payment_ref") or c["case_id"]), amount=c.get("amount") or 1, currency=c.get("currency") or "EUR",
                       settlement_date=iso(now())[:10], reason_code=reason_code, narrative=narrative.strip())
        row = M(id=nid, kind=kind, direction="OUTBOUND", status="SENT" if kind == "INVESTIGATION" else "DRAFTED", uetr=uetr, counterparty_bic=counterparty_bic, case_ref=nid,
                message_id="PEX-" + nid, amount=float(c.get("amount") or 1), currency=c.get("currency") or "EUR", reason_code=reason_code, narrative=narrative.strip(),
                created_at=iso(now()), due_at=iso(now() + timedelta(hours=response_hours())), request_xml=xml, approvals=[], timeline=[], warnings=[],
                linked_case_id=c["case_id"], drafted_by=user.user_id if kind == "RECALL" else None)
        if kind == "INVESTIGATION":
            _tl(row, user, "RAISED", f"{sm.TITLES[mt]} raised and sent to {counterparty_bic}.")
        else:
            _tl(row, user, "RAISED", f"{sm.TITLES[mt]} drafted for {counterparty_bic}; it needs an approver before it leaves PeX.")
        db.add(row)
        db.commit()
        _audit(row, user, "NETWORK_RAISED", f"{user.name} raised a {mt} to {counterparty_bic} for UETR {uetr} ({reason_code}).")
        if kind == "INVESTIGATION":
            _audit(row, user, "NETWORK_SENT", f"{mt} sent to {counterparty_bic}.")
        db.refresh(row)
        return detail(user, row)
    finally:
        db.close()


def simulate_reply(user, nid: str, outcome: Optional[str]) -> Dict[str, Any]:
    """Demo only: the counterparty answers. The reply comes back through the same inbox as a real one."""
    require(user, "network.work", "Only the operations team can work network cases.")
    db = SessionLocal()
    try:
        r = _get(db, nid)
        if r.direction != "OUTBOUND" or r.status != "SENT":
            raise bad_state("A simulated reply only applies to an outbound case that has been sent.")
        mt = "camt.111" if r.kind == "INVESTIGATION" else "camt.029"
        code = outcome or ("ANSW" if r.kind == "INVESTIGATION" else "CNCL")
        text = {"ANSW": "Funds were credited on the settlement date.", "WIPG": "We are looking into it.", "RJCT": "We cannot investigate this payment.",
                "CNCL": "Cancellation accepted; funds will be returned.", "RJCR": "Cancellation rejected."}.get(code, "")
        xml = sm.build(mt, message_id="CNT-RSP-" + r.id, created_at=iso(now()), case_id=r.id, sender_bic=r.counterparty_bic, receiver_bic=sm.OWN_BIC, uetr=r.uetr,
                       end_to_end_id=None, amount=r.amount, currency=r.currency, settlement_date=iso(now())[:10], status_code=code,
                       reason_code="ARDT" if code == "RJCR" else None, narrative=text)
    finally:
        db.close()
    return receive(user, xml)


def bank_return(user, nid: str, reference: str) -> Dict[str, Any]:
    require(user, "network.work", "Only the operations team can record the bank's confirmation.")
    db = SessionLocal()
    try:
        r = _get(db, nid)
        if r.status != "AWAITING_BANK_RETURN":
            raise bad_state("Only an accepted recall waits for the bank to return funds.")
        ref = (reference or "").strip()
        if len(ref) < 3:
            raise V2Error(422, "INVALID", "Enter the bank's reference for the return (for example its pacs.004 id).")
        h = dict(r.handoff or {})
        h.update({"state": "RETURN_CONFIRMED", "reference": ref, "confirmed_at": iso(now()), "confirmed_by": user.user_id})
        r.handoff = h
        r.status, r.closed_at = "CLOSED", iso(now())
        _tl(r, user, "RETURN_CONFIRMED", f"Bank confirmed the return ({ref}). Case closed.")
        db.commit()
        _audit(r, user, "NETWORK_RETURN_CONFIRMED", f"{user.name} recorded the bank's return confirmation {ref}.")
        db.refresh(r)
        return detail(user, r)
    finally:
        db.close()


def close(user, nid: str, note: Optional[str]) -> Dict[str, Any]:
    require(user, "network.work", "Only the operations team can close network cases.")
    db = SessionLocal()
    try:
        r = _get(db, nid)
        if not (r.status == "REPLY_RECEIVED" or (r.direction == "INBOUND" and r.status == "SENT")):
            raise bad_state("This case is not ready to close.")
        r.status, r.closed_at = "CLOSED", iso(now())
        _tl(r, user, "CLOSED", (note or "Closed.").strip())
        db.commit()
        _audit(r, user, "NETWORK_CLOSED", f"{user.name} closed the case. {(note or '').strip()[:160]}")
        db.refresh(r)
        return detail(user, r)
    finally:
        db.close()
