"""Expedite ladder: chase a pending case up three levels, and let the system climb it when nobody answers.

Level 1  the person holding the case (approver, tier-2 approver, compliance officer)
Level 2  Supervisor, Payment Operations
Level 3  Head of Payment Operations (a supervisor-role seat; becomes its own role once the bank names one)

All state lives on the case (`expedite_log`); `expedite_ping` always holds the latest entry for older screens.
Nothing here moves a payment: it only asks a person to look.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.services.data_loader import repo
from app.services.v2 import actions as ac
from app.services.v2 import logic as lg
from app.services.v2 import rows as rw
from app.services.v2 import ext as xt
from app.services.v2 import zone
from app.services.v2.core import V2Error, bad_state, has_perm, iso, is_compliance, not_found, now, parse_ts, person, require, role_of

COOLDOWN_MIN = 10          # same level cannot be pinged again sooner than this
AUTO_ESCALATE_MIN = 15     # an unanswered ping climbs one level by itself after this
PENDING = ("PENDING_APPROVAL", "AWAITING_SECOND_APPROVAL", "APPROVED")
SYSTEM_NAME = "PeX SLA watch"
L2_TITLE, L3_TITLE = "Supervisor, Payment Operations", "Head of Payment Operations"


def _log(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    return case.setdefault("expedite_log", [])


def _target(case: Dict[str, Any], ext: Dict[str, Any], level: int) -> Dict[str, Any]:
    if level == 2:
        return {"target_role": "SUPERVISOR", "target_user": None, "target_title": L2_TITLE}
    if level == 3:
        return {"target_role": "SUPERVISOR", "target_user": None, "target_title": L3_TITLE}
    st = lg.status_of(case)
    if st == "APPROVED":
        return {"target_role": "OPERATIONS_APPROVER", "target_user": None, "target_title": "Operations Approver (dispatch release)"}
    if is_compliance(case):
        return {"target_role": "COMPLIANCE_APPROVER", "target_user": None, "target_title": "Compliance Officer"}
    if float(case.get("amount") or 0) >= lg.DUAL_AUTH_THRESHOLD or st == "AWAITING_SECOND_APPROVAL":
        return {"target_role": "RISK_APPROVER", "target_user": ext.get("approver_assigned"), "target_title": "Risk Approver (tier 2)"}
    return {"target_role": "OPERATIONS_APPROVER", "target_user": ext.get("approver_assigned"), "target_title": "Operations Approver (tier 1)"}


def _age_min(entry: Dict[str, Any]) -> float:
    t = parse_ts(entry.get("at"))
    return (now() - t).total_seconds() / 60 if t else 0.0


def _minutes_text(m: float) -> str:
    m = max(1, int(round(m)))
    return f"{m} minute{'s' if m != 1 else ''}"


def next_level(case: Dict[str, Any]) -> int:
    log = _log(case)
    if not log:
        return 1
    last = log[-1]
    return last["level"] if last["status"] == "ACKNOWLEDGED" else min(3, last["level"] + 1)


def _add(case: Dict[str, Any], ext: Dict[str, Any], level: int, sender: Dict[str, Any], note: str, auto: bool) -> Dict[str, Any]:
    log = _log(case)
    pairs = zone.case_pairs(case)
    entry = {"id": f"EXP-{case['case_id']}-{len(log) + 1}", "case_id": case["case_id"], "level": level, "at": iso(now()), "status": "UNREAD", "auto": auto,
             "sender_id": sender.get("user_id"), "sender_name": sender["name"], "sender_role": sender["role"],
             "note": zone.seal_text(note, None, pairs), "ack_by": None, "ack_at": None, **_target(case, ext, level)}
    log.append(entry)
    case["expedite_ping"] = entry
    repo.save_case(case)
    ext["last_change_at"] = iso(now())
    xt.persist_ext(case["case_id"], ext)
    return entry


def ping(case_id: str, user, note: Optional[str], level: Optional[int] = None) -> Dict[str, Any]:
    require(user, "case.work")
    case = ac._load(case_id)
    ext = lg.ext_of(case)
    st = lg.status_of(case)
    if st not in PENDING:
        raise bad_state(f"Cannot expedite a case in {st.replace('_', ' ').lower()}.")
    log = _log(case)
    lvl = int(level) if level else next_level(case)
    if lvl < 1 or lvl > 3:
        raise V2Error(422, "INVALID", "Level must be 1, 2 or 3.")
    sent = {e["level"] for e in log}
    if lvl > 1 and (lvl - 1) not in sent:
        raise bad_state(f"Escalate one level at a time: level {lvl - 1} has not been pinged yet.")
    same = [e for e in log if e["level"] == lvl]
    if same and _age_min(same[-1]) < COOLDOWN_MIN:
        wait = COOLDOWN_MIN - _age_min(same[-1])
        raise bad_state(f"Level {lvl} was pinged {_minutes_text(_age_min(same[-1]))} ago. Try again in {_minutes_text(wait)}.")
    text = (note or "").strip() or "Cutoff approaching. Please prioritise."
    entry = _add(case, ext, lvl, {"user_id": user.user_id, "name": user.name, "role": role_of(user)}, text, auto=False)
    ac.audit(case, user, "SLA_EXPEDITE_ESCALATION", "EXPEDITE_PING_SENT",
             f"{user.name} {'pinged' if lvl == 1 else 'escalated to'} {entry['target_title']} (level {lvl}) to expedite {case_id}.", ["Expedite ping", f"Level {lvl}"], reason=text)
    ac.notify("PING", f"Expedite: {case_id}", f"{user.name}: {text}", case_id, target_user=entry["target_user"], target_role=None if entry["target_user"] else entry["target_role"])
    return ac.result(case_id, user, f"{entry['target_title']} notified (level {lvl}).", ping=entry)


def sweep() -> int:
    """Climb the ladder for pings nobody answered. Safe to call often: it only acts on the latest, still unread, overdue entry."""
    n = 0
    for case in rw.all_cases():
        log = case.get("expedite_log") or []
        if not log:
            continue
        last = log[-1]
        if last["status"] != "UNREAD" or last["level"] >= 3 or _age_min(last) < AUTO_ESCALATE_MIN:
            continue
        if lg.status_of(case) not in PENDING:
            continue
        ext = lg.ext_of(case)
        lvl = last["level"] + 1
        entry = _add(case, ext, lvl, {"user_id": None, "name": SYSTEM_NAME, "role": "SYSTEM"},
                     f"No answer to the level {last['level']} ping after {AUTO_ESCALATE_MIN} minutes. Escalated automatically.", auto=True)
        ac.audit(case, None, "SLA_EXPEDITE_ESCALATION", "EXPEDITE_AUTO_ESCALATED",
                 f"No answer for {AUTO_ESCALATE_MIN} minutes. {case['case_id']} was escalated automatically to {entry['target_title']} (level {lvl}).",
                 ["Expedite ping", f"Level {lvl}", "Automatic"], actor_id="SYS-SLA", actor_role="SYSTEM")
        ac.notify("PING", f"Escalated: {case['case_id']}", entry["note"], case["case_id"], target_role="SUPERVISOR")
        n += 1
    return n


def _mine(entry: Dict[str, Any], user) -> bool:
    if entry.get("target_user"):
        return entry["target_user"] == user.user_id
    return entry.get("target_role") == role_of(user)


def _view(case: Dict[str, Any], entry: Dict[str, Any], user) -> Dict[str, Any]:
    row = lg.row_core(case, user)
    return {"id": entry["id"], "case_id": case["case_id"], "level": entry["level"], "level_title": entry["target_title"], "status": entry["status"], "auto": bool(entry.get("auto")),
            "at": entry["at"], "age_minutes": int(_age_min(entry)), "note": entry["note"],
            "sender": {"user_id": entry.get("sender_id"), "name": entry["sender_name"], "role": entry["sender_role"]},
            "ack_by": person(entry["ack_by"]) if entry.get("ack_by") else None, "ack_at": entry.get("ack_at"),
            "exception": row["exception"], "amount": row["amount"], "cutoff": row["cutoff"], "rail": row["rail"], "link": f"/cases/{case['case_id']}"}


def inbox(user) -> Dict[str, Any]:
    sweep()
    received, sent = [], []
    for case in rw.all_cases():
        for e in case.get("expedite_log") or []:
            if _mine(e, user):
                received.append(_view(case, e, user))
            if e.get("sender_id") == user.user_id:
                sent.append(_view(case, e, user))
    order = {"UNREAD": 0, "ACKNOWLEDGED": 1}
    received.sort(key=lambda i: (order.get(i["status"], 2), (i["cutoff"] or {}).get("seconds_left", 10 ** 9)))
    sent.sort(key=lambda i: i["at"], reverse=True)
    return {"unread": sum(1 for i in received if i["status"] == "UNREAD"), "items": received[:50], "sent": sent[:30], "now": iso(now()),
            "policy": {"cooldown_minutes": COOLDOWN_MIN, "auto_escalate_minutes": AUTO_ESCALATE_MIN}}


def acknowledge(entry_id: str, user) -> Dict[str, Any]:
    for case in rw.all_cases():
        for e in case.get("expedite_log") or []:
            if e["id"] != entry_id:
                continue
            if not _mine(e, user):
                raise V2Error(403, "FORBIDDEN", "Only the person this was sent to can acknowledge it.")
            if e["status"] != "ACKNOWLEDGED":
                e["status"], e["ack_by"], e["ack_at"] = "ACKNOWLEDGED", user.user_id, iso(now())
                if (case.get("expedite_ping") or {}).get("id") == e["id"]:
                    case["expedite_ping"] = e
                repo.save_case(case)
                ac.audit(case, user, "SLA_EXPEDITE_ESCALATION", "EXPEDITE_PING_ACKNOWLEDGED", f"{user.name} acknowledged the level {e['level']} expedite request on {case['case_id']}.",
                         ["Expedite ping", f"Level {e['level']}"])
                if e.get("sender_id"):
                    ac.notify("PING", f"Acknowledged: {case['case_id']}", f"{user.name} acknowledged your level {e['level']} expedite request.", case["case_id"], target_user=e["sender_id"])
            return {"ok": True, "id": entry_id, "status": "ACKNOWLEDGED"}
    raise not_found("Expedite request")


def case_state(case_id: str, user) -> Dict[str, Any]:
    require(user, "case.read")
    case = ac._load(case_id)
    log = _log(case)
    st = lg.status_of(case)
    levels = []
    for lvl in (1, 2, 3):
        es = [e for e in log if e["level"] == lvl]
        t = _target(case, lg.ext_of(case), lvl)
        last = es[-1] if es else None
        levels.append({"level": lvl, "title": t["target_title"], "sent": bool(es), "at": last["at"] if last else None, "status": last["status"] if last else None,
                       "auto": bool(last and last.get("auto")), "ack_by": person(last["ack_by"]) if last and last.get("ack_by") else None,
                       "cooldown_minutes_left": max(0, int(COOLDOWN_MIN - _age_min(last))) if last else 0})
    nl = next_level(case)
    can = has_perm(user, "case.work") and st in PENDING and levels[nl - 1]["cooldown_minutes_left"] == 0
    return {"case_id": case_id, "levels": levels, "next_level": nl, "can_ping": bool(can),
            "reason": None if can else ("Not a pending case" if st not in PENDING else "You cannot chase cases" if not has_perm(user, "case.work") else "Wait for the cooldown")}
