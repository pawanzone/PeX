"""UI v2 audit views (read only) on top of the SHA-256 chained audit_events table."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, or_, func

from app.core.hashing import calculate_event_hash, GENESIS_HASH
from app.core.security import get_persona
from app.db.models import AuditEventModel, CaseModel
from app.db.session import SessionLocal
from app.services.data_loader import repo
from app.services.v2 import logic as lg
from app.services.v2.core import (
    V2Error, invalid, not_found, now, iso, parse_ts, ROLE_LABELS, profile_code, profile_enum_name, profile_label, money, rail_obj,
)
from app.services.v2.actions import META_MARK

LABELS = {
    "MAKER_SUBMITTED_FOR_APPROVAL": "Submitted for approval", "APPROVED_FOR_BANK_HANDOFF": "Approved for bank handoff",
    "FIRST_APPROVAL_RECORDED": "First approval recorded", "BATCH_APPROVED_FOR_BANK_HANDOFF": "Batch approved for bank handoff",
    "RETURNED_TO_MAKER": "Returned to maker", "REJECTED": "Rejected", "APPROVAL_BLOCKED": "Approval blocked",
    "INFORMATION_REQUESTED": "Information requested", "INFO_REQUEST_DRAFT_SAVED": "Information request drafted",
    "CASE_REASSESSED": "Case reassessed", "CASE_ESCALATED": "Case escalated", "VERIFICATION_STARTED": "Verification started",
    "HYPOTHESIS_DISAMBIGUATION": "Candidate selected by analyst", "STATUS_CHECK_REQUESTED": "Status checked with bank",
    "BANK_STATUS_REQUESTED": "Bank status requested", "EXPEDITE_PING_SENT": "Expedite ping sent", "CASE_ASSIGNED": "Case assigned",
    "CASE_RETURNED_TO_QUEUE": "Returned to queue", "COMPLIANCE_HOLD_RELEASED": "Compliance hold released",
    "COMPLIANCE_BLOCK_FIRST_REVIEW": "Match confirmed (first review)", "COMPLIANCE_BLOCK_CONFIRMED": "Payment blocked (second review)",
    "COMPLIANCE_ESCALATED": "Escalated to Senior Compliance", "HANDOFF_REFUSED": "Handoff refused", "SHADOW_HANDOFF_RECORDED": "Shadow handoff recorded",
    "NETWORK_RECEIVED": "Network message received", "NETWORK_RAISED": "Network case raised", "NETWORK_DRAFTED": "Reply drafted", "NETWORK_AUTHORISED": "Message authorised",
    "NETWORK_SENT": "Message sent to bank (simulated)", "NETWORK_REPLY_RECEIVED": "Reply received", "NETWORK_RETURN_CONFIRMED": "Bank return confirmed", "NETWORK_CLOSED": "Network case closed",
    "STATUS_UNKNOWN": "Status unknown", "ROUTED_TO_QUEUE": "Routed to queue", "AUTONOMOUS_STP_HANDOFF": "Autonomous STP handoff",
}


def event_label(action: str) -> str:
    a = action or ""
    if a in LABELS:
        return LABELS[a]
    if a.endswith("_HANDOFF_DISPATCHED"):
        return "Handed to bank (simulated)"
    if a.startswith("BANK_") and a.endswith("_SIGNAL"):
        return "Bank " + a[5:-7].replace("_", " ").lower() + " signal"
    if a.startswith("APPROVAL_"):
        return "Approval: " + a[9:].replace("_", " ").lower()
    return a.replace("_", " ").capitalize()


def outcome_of(action: str, stage: str, tags: List[str]) -> str:
    a = (action or "").upper()
    if "BLOCKED" in a and "COMPLIANCE" not in a or "REFUSED" in a or "VIOLATION" in a:
        return "Blocked"
    if "COMPLIANCE_BLOCK_CONFIRMED" in a or a == "REJECTED" or a.startswith("APPROVAL_REJECT"):
        return "Blocked"
    if "UNKNOWN" in a:
        return "Unknown"
    if "FIRST_REVIEW" in a or "ESCALATED" in a or "HOLD" in a and "RELEASED" not in a:
        return "Held"
    if "APPROV" in a or "RELEASED" in a or "HANDOFF_DISPATCHED" in a or "BANK_" in a:
        return "Approved"
    if "SUBMIT" in a:
        return "Submitted"
    if "RETURN" in a:
        return "Returned"
    if "ROUTED" in a or "INGEST" in a or "VALID" in a or "RECOMMEND" in a or "SHADOW" in a:
        return "Passed"
    return "Recorded"


def actor_name(actor_id: str) -> str:
    p = get_persona(actor_id)
    if p:
        return p.name
    a = (actor_id or "").upper()
    if a.startswith("BANK"):
        return "Bank (external)"
    if a.startswith("SYS") or a in ("WORKFLOW_ROUTER",):
        return "PeX (system)"
    return actor_id or "Unknown"


def role_label(role: str, actor_id: str) -> str:
    if role in ROLE_LABELS:
        return ROLE_LABELS[role]
    return {"PLATFORM_GUARD": "System", "OUTBOUND_GATEWAY": "System", "SYSTEM": "System", "EXTERNAL_BANK_GATEWAY": "Bank system", "BANK_OUTCOME": "Bank system"}.get(role, (role or "").replace("_", " ").capitalize())


def split_meta(details: str) -> Tuple[str, Dict[str, Any]]:
    if META_MARK in (details or ""):
        text, _, m = details.partition(META_MARK)
        try:
            return text, json.loads(m)
        except Exception:
            return text, {}
    return details or "", {}


def _filtered(db, f: Dict[str, Any]):
    q = db.query(AuditEventModel)
    joined = False
    if f.get("exception_type") or f.get("rail"):
        q = q.join(CaseModel, CaseModel.case_id == AuditEventModel.case_id)
        joined = True
        if f.get("exception_type"):
            code = f["exception_type"]
            q = q.filter(CaseModel.profile.in_([code, profile_enum_name(code)]))
        if f.get("rail"):
            r = str(f["rail"]).upper()
            variants = {r, r.replace("_", " ")}
            if r.startswith("SWIFT"):
                variants |= {"SWIFT", "SWIFT_CBPR+", "SWIFT CBPR+"}
            if r in ("TARGET2", "T2"):
                variants |= {"TARGET2", "T2"}
            q = q.filter(CaseModel.payment_rail.in_(list(variants)))
    if f.get("date_from"):
        d = parse_ts(f["date_from"])
        if d is None:
            raise invalid("date_from must be an ISO date", "date_from")
        q = q.filter(AuditEventModel.timestamp >= d.replace(tzinfo=None).isoformat())
    if f.get("date_to"):
        d = parse_ts(f["date_to"])
        if d is None:
            raise invalid("date_to must be an ISO date", "date_to")
        if len(str(f["date_to"])) <= 10:
            d = d + timedelta(days=1)
        q = q.filter(AuditEventModel.timestamp < d.replace(tzinfo=None).isoformat())
    if f.get("event_type"):
        q = q.filter(AuditEventModel.stage_name == f["event_type"])
    if f.get("actor"):
        a = f["actor"]
        like = f"%{a}%"
        ids = [p.user_id for p in __import__("app.core.security", fromlist=["DEMO_PERSONAS"]).DEMO_PERSONAS.values() if a.lower() in p.name.lower()]
        q = q.filter(or_(AuditEventModel.actor_id == a, AuditEventModel.actor_id.like(like), AuditEventModel.actor_id.in_(ids or ["__none__"])))
    if f.get("role"):
        r = f["role"]
        keys = {r} | {k for k, v in ROLE_LABELS.items() if v.lower() == str(r).lower()}
        q = q.filter(AuditEventModel.actor_role.in_(list(keys)))
    if f.get("case_id"):
        q = q.filter(AuditEventModel.case_id == f["case_id"])
    if f.get("q"):
        like = f"%{f['q']}%"
        q = q.filter(or_(AuditEventModel.case_id.like(like), AuditEventModel.action_name.like(like), AuditEventModel.details.like(like), AuditEventModel.actor_id.like(like)))
    return q


def _row(e: AuditEventModel) -> Dict[str, Any]:
    text, meta = split_meta(e.details)
    return {"id": f"EV-{e.event_index}", "time": _ts(e.timestamp), "case_id": e.case_id, "event": event_label(e.action_name), "event_type": e.stage_name,
            "action": e.action_name, "actor": actor_name(e.actor_id), "actor_id": e.actor_id, "role": role_label(e.actor_role, e.actor_id),
            "role_key": e.actor_role, "outcome": outcome_of(e.action_name, e.stage_name, e.control_tags or []), "detail": text}


def _ts(s: str) -> str:
    d = parse_ts(s)
    return iso(d) if d else s


def events(f: Dict[str, Any], page: int, page_size: int) -> Dict[str, Any]:
    page_size = max(1, min(int(page_size or 50), 500))
    page = max(1, int(page or 1))
    db = SessionLocal()
    try:
        q = _filtered(db, f)
        total = q.count()
        rows = q.order_by(AuditEventModel.event_index.desc()).offset((page - 1) * page_size).limit(page_size).all()
        types = [r[0] for r in db.query(AuditEventModel.stage_name).distinct().all()]
        roles = [r[0] for r in db.query(AuditEventModel.actor_role).distinct().all()]
        total_all = db.query(func.count(AuditEventModel.event_index)).scalar() or 0
        return {"total": total, "page": page, "page_size": page_size, "items": [_row(e) for e in rows],
                "facets": {"event_types": sorted(types), "roles": sorted({role_label(r, "") for r in roles}), "actors": []},
                "integrity": {"chain_valid": _chain_ok(db, rows), "events": total_all}, "now": iso(now())}
    finally:
        db.close()


def case_timeline(case_id: str) -> Dict[str, Any]:
    """Events of one case, oldest first, for the case page. Same rows as the Audit screen, limited to this case."""
    db = SessionLocal()
    try:
        rows = db.query(AuditEventModel).filter(AuditEventModel.case_id == case_id).order_by(AuditEventModel.event_index.asc()).all()
        return {"case_id": case_id, "total": len(rows), "items": [_row(e) for e in rows], "now": iso(now())}
    finally:
        db.close()


def _event_hash_ok(e: AuditEventModel, prev_hash: Optional[str]) -> bool:
    h = calculate_event_hash(event_index=e.event_index, timestamp_iso=e.timestamp, case_id=e.case_id, stage_name=e.stage_name, actor_id=e.actor_id,
                             action_name=e.action_name, details=e.details, prev_hash=e.prev_hash, amount=e.amount, currency=e.currency,
                             debtor_account=e.debtor_account, creditor_account=e.creditor_account)
    return h == e.current_hash and (prev_hash is None or prev_hash == e.prev_hash)


def _chain_ok(db, rows: List[AuditEventModel]) -> bool:
    for e in rows:
        prev = db.query(AuditEventModel.current_hash).filter(AuditEventModel.event_index == e.event_index - 1).first()
        if not _event_hash_ok(e, prev[0] if prev else (GENESIS_HASH if e.event_index == 1 else None)):
            return False
    return True


def event_detail(eid: str) -> Dict[str, Any]:
    try:
        idx = int(str(eid).replace("EV-", ""))
    except ValueError:
        raise not_found(f"Audit event {eid}")
    db = SessionLocal()
    try:
        e = db.query(AuditEventModel).filter(AuditEventModel.event_index == idx).first()
        if not e:
            raise not_found(f"Audit event {eid}")
        text, meta = split_meta(e.details)
        prev = db.query(AuditEventModel.current_hash).filter(AuditEventModel.event_index == idx - 1).first()
        ok = _event_hash_ok(e, prev[0] if prev else (GENESIS_HASH if idx == 1 else None))
        case = repo.get_case(e.case_id)
        ext = lg.ext_of(case) if case else {}
        ev_n = meta.get("evidence_reviewed")
        if ev_n is None and ext.get("evidence") and "APPROV" in (e.action_name or "") :
            ev_n = len(ext["evidence"])
        p = get_persona(e.actor_id)
        return {
            "id": f"EV-{idx}", "event": event_label(e.action_name), "event_type": e.stage_name, "action": e.action_name, "case_id": e.case_id,
            "case": ({"case_id": case["case_id"], "exception": profile_label(case.get("profile")), "amount": money(case.get("amount"), case.get("currency")),
                      "rail": rail_obj(case.get("payment_rail")), "status": lg.status_of(case)} if case else None),
            "actor": {"user_id": e.actor_id, "name": actor_name(e.actor_id), "role": role_label(e.actor_role, e.actor_id)},
            "time": _ts(e.timestamp), "outcome": outcome_of(e.action_name, e.stage_name, e.control_tags or []),
            "before": meta.get("before"), "after": meta.get("after"), "evidence_reviewed": ev_n,
            "policy_version": meta.get("policy_version"), "sod": {"result": (meta.get("sod") or "Not applicable").split(" ")[0].rstrip(":,.") if meta.get("sod") else "Not applicable",
                                                               "text": meta.get("sod")},
            "reason": meta.get("reason") or text, "detail": text, "tags": e.control_tags or [],
            "integrity": {"sealed": True, "verified": ok, "hash": e.current_hash, "prev_hash": e.prev_hash, "label": "Record sealed · verified" if ok else "Integrity check FAILED"},
        }
    finally:
        db.close()


def export_csv(f: Dict[str, Any]) -> bytes:
    db = SessionLocal()
    try:
        q = _filtered(db, f).order_by(AuditEventModel.event_index.desc()).limit(50000)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id", "time", "case_id", "event", "event_type", "actor", "actor_id", "role", "outcome", "detail", "hash"])
        for e in q.all():
            r = _row(e)
            w.writerow([r["id"], r["time"], r["case_id"], r["event"], r["event_type"], r["actor"], r["actor_id"], r["role"], r["outcome"], r["detail"], e.current_hash])
        return buf.getvalue().encode("utf-8")
    finally:
        db.close()


def case_report(case_id: str, fmt: str) -> Tuple[Any, str, str]:
    case = repo.get_case(case_id)
    if not case:
        raise not_found(f"Case {case_id}")
    db = SessionLocal()
    try:
        evs = db.query(AuditEventModel).filter(AuditEventModel.case_id == case_id).order_by(AuditEventModel.event_index).all()
        rows = []
        for e in evs:
            r = _row(e)
            _, meta = split_meta(e.details)
            r.update({"before": meta.get("before"), "after": meta.get("after"), "reason": meta.get("reason"), "policy_version": meta.get("policy_version"),
                      "sod": meta.get("sod"), "hash": e.current_hash, "verified": _event_hash_ok(e, None)})
            rows.append(r)
    finally:
        db.close()
    fmt = (fmt or "json").lower()
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id", "time", "event", "actor", "role", "outcome", "before", "after", "reason", "policy_version", "sod", "detail", "hash", "verified"])
        for r in rows:
            w.writerow([r["id"], r["time"], r["event"], r["actor"], r["role"], r["outcome"], r["before"], r["after"], r["reason"], r["policy_version"], r["sod"], r["detail"], r["hash"], r["verified"]])
        return buf.getvalue().encode("utf-8"), "text/csv", f"{case_id}.audit_report.csv"
    if fmt != "json":
        raise invalid("format must be json or csv", "format")
    ext = lg.ext_of(case)
    rep = {"case_id": case_id, "generated_at": iso(now()), "exception": profile_label(case.get("profile")), "amount": money(case.get("amount"), case.get("currency")),
           "rail": rail_obj(case.get("payment_rail")), "status": lg.status_of(case), "uetr": case.get("uetr"), "maker_id": case.get("maker_id"),
           "approvals": [{k: a.get(k) for k in ("approver_id", "approver_name", "approver_role", "action", "step_number", "created_at", "comments")} for a in (case.get("approval_history") or [])],
           "evidence": [{k: r.get(k) for k in ("check", "result", "source", "authority", "status")} for r in (ext.get("evidence") or [])],
           "events": rows, "events_count": len(rows), "chain_verified": all(r["verified"] for r in rows),
           "note": "Bank communication is simulated in this build; execution confirmations come only from the bank signal."}
    return rep, "application/json", f"{case_id}.audit_report.json"


def cases_with_events(q: Optional[str], page: int, page_size: int) -> Dict[str, Any]:
    page_size = max(1, min(int(page_size or 25), 200))
    page = max(1, int(page or 1))
    db = SessionLocal()
    try:
        base = db.query(AuditEventModel.case_id, func.count(AuditEventModel.event_index), func.max(AuditEventModel.timestamp)).group_by(AuditEventModel.case_id)
        if q:
            base = base.filter(AuditEventModel.case_id.like(f"%{q}%"))
        rows = base.order_by(func.max(AuditEventModel.timestamp).desc()).all()
        total = len(rows)
        items = []
        for cid, n, last in rows[(page - 1) * page_size: page * page_size]:
            c = repo.get_case(cid)
            items.append({"case_id": cid, "exception": profile_label(c.get("profile")) if c else None, "amount": money(c.get("amount"), c.get("currency")) if c else None,
                          "status": lg.status_of(c) if c else None, "events": n, "last_event": _ts(last)})
        return {"total": total, "page": page, "page_size": page_size, "items": items}
    finally:
        db.close()


def control_reports() -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        def cnt(*conds):
            return db.query(func.count(AuditEventModel.event_index)).filter(*conds).scalar() or 0
        sod_pass = cnt(AuditEventModel.details.like("%\"sod\": \"Passed%"))
        sod_fail = cnt(AuditEventModel.action_name == "APPROVAL_BLOCKED")
        refused = cnt(AuditEventModel.action_name == "HANDOFF_REFUSED")
        handed = cnt(AuditEventModel.action_name.like("%HANDOFF_DISPATCHED"))
        comp = cnt(AuditEventModel.stage_name == "COMPLIANCE_DECISION")
        bank = cnt(AuditEventModel.stage_name == "BANK_OUTCOME")
        total = cnt()
        from app.services.audit_service import audit_service
        ver = audit_service.verify_chain()
        return [
            {"id": "SOD", "name": "Separation of duties", "passed": sod_pass, "failed": sod_fail, "period": "all recorded events", "text": "Approvals where the checker differed from the maker, and blocked attempts."},
            {"id": "HANDOFF", "name": "Handoff controls", "passed": handed, "failed": refused, "period": "all recorded events", "text": "Handoffs sent (simulated) vs handoffs refused by the outbound port."},
            {"id": "COMPLIANCE", "name": "Compliance decisions", "passed": comp, "failed": 0, "period": "all recorded events", "text": "Hold decisions recorded in PeX."},
            {"id": "BANK_SIGNALS", "name": "Bank signals verified", "passed": bank, "failed": 0, "period": "all recorded events", "text": "Inbound HMAC-verified bank outcome signals."},
            {"id": "CHAIN", "name": "Audit chain integrity", "passed": total if ver.is_intact else 0, "failed": 0 if ver.is_intact else total, "period": "full chain", "text": f"SHA-256 chain verified over {ver.total_events_checked} events."},
        ]
    finally:
        db.close()


def today_tiles() -> Dict[str, Any]:
    start = now().astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None).isoformat()
    db = SessionLocal()
    try:
        today = db.query(func.count(AuditEventModel.event_index)).filter(AuditEventModel.timestamp >= start).scalar() or 0
        blocked = db.query(func.count(AuditEventModel.event_index)).filter(AuditEventModel.timestamp >= start, or_(AuditEventModel.action_name == "APPROVAL_BLOCKED", AuditEventModel.action_name == "HANDOFF_REFUSED")).scalar() or 0
        sod = db.query(func.count(AuditEventModel.event_index)).filter(AuditEventModel.timestamp >= start, AuditEventModel.details.like("%\"sod\": \"Passed%")).scalar() or 0
        return {"events_today": today, "blocked": blocked, "sod_checks_passed": sod}
    finally:
        db.close()
