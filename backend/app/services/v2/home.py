"""GET /api/v2/home — role-specific payloads computed from real cases, approvals, outcomes and audit data."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, List

from app.config import settings
from app.db.models import AuditEventModel, BankOutcomeModel, V2ModeChangeModel
from app.db.session import SessionLocal
from app.services.data_loader import repo
from app.services.v2 import logic as lg
from app.services.v2 import rows as rw
from app.services.v2.core import (
    now, iso, parse_ts, cutoff_obj, duration_label, role_of, person, money, rail_obj, ROLE_LABELS,
)

TEAM = ["OP-9012", "OP-9020", "OP-9021", "OP-9022"]
APPROVERS = ["APR-3191", "APR-3192"]


def _greeting(user) -> str:
    h = now().hour
    part = "Good morning" if h < 12 else ("Good afternoon" if h < 18 else "Good evening")
    return f"{part}, {user.name.split()[0]}"


def _wait_info(case, ext) -> Dict[str, Any]:
    ri = ext.get("request_info") or {}
    st = lg.status_of(case)
    if st == "STATUS_UNKNOWN":
        since = parse_ts(case.get("handed_off_at")) or parse_ts(ext.get("last_change_at"))
        return {"waiting_for": "Bank confirmation", "party": "Bank operations", "since": iso(since), "due": None,
                "overdue": bool(since and (now() - since).total_seconds() > 600)}
    due = parse_ts(ri.get("reply_due"))
    return {"waiting_for": "Client reply", "party": (ri.get("to") or {}).get("party") or ext.get("counterparty"), "since": ri.get("sent_at"),
            "due": ri.get("reply_due"), "overdue": bool(due and due < now())}


def maker_home(user) -> Dict[str, Any]:
    by = rw.build_rows(user)
    counts = {k: len(v) for k, v in by.items()}
    ready, ret = by["ready"], by["returned"]
    band = {"under_1h": 0, "1_to_3h": 0, "over_3h": 0}
    for r in ready:
        b = (r["cutoff"] or {}).get("band", "over_3h")
        band["under_1h" if b == "passed" else b] += 1
    cand = []
    for r in ret + ready + by["waiting"]:
        st_rs = (r["next_action"]["type"] in ("FOLLOW_UP",)) or r["tab"] in ("ready", "returned")
        if st_rs:
            cand.append(r)
    cand.sort(key=lambda r: (r["cutoff"] or {}).get("seconds_left", 10 ** 9))
    act = []
    for r in cand[:3]:
        why = {"returned": "Returned by approver", "waiting": "Reply overdue", "ready": "Cutoff approaching"}.get(r["tab"], "Needs action")
        if r["next_action"]["type"] == "REQUEST_INFO":
            why = "Information needed from client"
        act.append({"case_id": r["case_id"], "exception": r["exception"]["label"], "amount": r["amount"], "cutoff": r["cutoff"],
                    "next_action": r["next_action"]["text"], "next_action_type": r["next_action"]["type"], "reason": why, "link": f"/cases/{r['case_id']}"})
    waiting = []
    for r in by["waiting"]:
        case = repo.get_case(r["case_id"]) or {}
        w = _wait_info(case, r["_ext"])
        w["case_id"] = r["case_id"]
        waiting.append(w)
    returned = []
    for r in ret:
        rt = r["_ext"].get("returned") or {}
        returned.append({"case_id": r["case_id"], "returned_by": rt.get("by"), "returned_at": rt.get("at"), "comment": rt.get("comment")})
    return {"role_view": "MAKER", "now": iso(now()), "greeting": _greeting(user), "act_now": act,
            "tiles": {"ready": counts["ready"], "returned": counts["returned"], "waiting": counts["waiting"], "pending": counts["pending"], "done_today": counts["done"]},
            "ready_by_cutoff": [{"band": "under_1h", "label": "Under 1 hour", "count": band["under_1h"]},
                                {"band": "1_to_3h", "label": "1 to 3 hours", "count": band["1_to_3h"]},
                                {"band": "over_3h", "label": "Over 3 hours", "count": band["over_3h"]}],
            "waiting_on_others": waiting, "returned_to_me": returned}


def supervisor_home(user) -> Dict[str, Any]:
    t = now()
    cases = rw.all_cases()
    open_c, unassigned, under1h, wtl, pending, resolved = [], 0, 0, 0, 0, []
    risk: Dict[str, Dict[str, Any]] = {}
    exec_today = handed = auto = 0
    team = {u: {"open": 0, "under_1h": 0, "returned": 0, "oldest": None, "oldest_case_id": None} for u in TEAM}
    appr = {u: {"pending": 0, "oldest": None} for u in APPROVERS + ["RSK-7714"]}
    needs = []
    for c in cases:
        ext = lg.ext_of(c)
        st = lg.status_of(c)
        if st in lg.DONE:
            if st != "REJECTED" and st != "FAILED" and rw.done_today(c, ext):
                resolved.append(c)
                if st in lg.FINAL_OK:
                    exec_today += 1
                elif st == "DISPATCHED":
                    handed += 1
                if not c.get("maker_id") and (c.get("queue") == "STP Fast-Lane" or (ext.get("stp") or {}).get("eligible")):
                    auto += 1
            continue
        open_c.append(c)
        cut = lg.cutoff_dt(c, ext)
        left = (cut - t).total_seconds() if cut else None
        comp = lg.is_compliance(c)
        rl = rail_obj(c.get("payment_rail"))
        rr = risk.setdefault(rl["key"], {"rail": rl["label"], "rail_key": rl["key"], "next": None, "open": 0, "at_risk": 0})
        rr["open"] += 1
        if cut and left is not None and left > 0 and (rr["next"] is None or cut < rr["next"]):
            rr["next"] = cut
        if left is not None and left < 3600:
            rr["at_risk"] += 1
            under1h += 1
        tab = lg.tab_of(c, ext)
        if not comp and tab in ("ready", "returned") and not ext.get("assignee"):
            unassigned += 1
        if tab == "waiting":
            w = _wait_info(c, ext)
            since = parse_ts(w.get("since"))
            if w["overdue"] or (since and (t - since).total_seconds() > 3600):
                wtl += 1
        if tab == "pending":
            pending += 1
            a = rw.approver_for(c, ext)
            if a in appr:
                appr[a]["pending"] += 1
                sub = parse_ts(ext.get("submitted_at")) or rw.last_change(c, ext)
                if sub and (appr[a]["oldest"] is None or sub < appr[a]["oldest"]):
                    appr[a]["oldest"] = sub
        asg = ext.get("assignee")
        if asg in team:
            team[asg]["open"] += 1
            if left is not None and left < 3600:
                team[asg]["under_1h"] += 1
            if tab == "returned":
                team[asg]["returned"] += 1
            cr = parse_ts(c.get("created_at"))
            if cr and (team[asg]["oldest"] is None or cr < team[asg]["oldest"]):
                team[asg]["oldest"], team[asg]["oldest_case_id"] = cr, c["case_id"]
        # needs decision
        if lg.status_of(c) == "STATUS_UNKNOWN":
            lc = parse_ts((ext.get("last_status_check") or {}).get("at")) or parse_ts(c.get("handed_off_at")) or parse_ts(ext.get("last_change_at"))
            mins = int(((t - lc).total_seconds() // 60) if lc else 0)
            if mins >= 10:
                needs.append({"kind": "STATUS_CHECK_OVERDUE", "case_id": c["case_id"], "title": f"{c['case_id']} status check overdue {mins}m", "minutes": mins,
                              "action": {"label": "Escalate", "key": "escalate"}, "link": f"/cases/{c['case_id']}"})
        elif lg.derive_variant(c, ext) == "CONFLICT":
            lc = parse_ts(ext.get("last_change_at")) or parse_ts(c.get("created_at"))
            mins = int(((t - lc).total_seconds() // 60) if lc else 0)
            if mins >= 60:
                needs.append({"kind": "CONFLICT_UNRESOLVED", "case_id": c["case_id"], "title": f"{c['case_id']} conflict unresolved {mins}m", "minutes": mins,
                              "action": {"label": "Review", "key": "review"}, "link": f"/cases/{c['case_id']}"})
    needs.sort(key=lambda n: -n["minutes"])
    needs = needs[:4]
    if unassigned:
        needs.append({"kind": "UNASSIGNED", "case_id": None, "title": f"{unassigned} unassigned cases", "minutes": 0,
                      "action": {"label": "Assign", "key": "assign"}, "link": "/worklist?tab=ready&assignee=none"})
    cutoff_risk = []
    for k, v in sorted(risk.items(), key=lambda kv: (kv[1]["next"] is None, kv[1]["next"] or t)):
        cutoff_risk.append({"rail": v["rail"], "rail_key": k, "next_cutoff": cutoff_obj(v["next"], t), "open": v["open"], "at_risk": v["at_risk"]})
    n_res = len(resolved)
    team_rows = []
    for u, v in team.items():
        team_rows.append({"user_id": u, "name": person(u)["name"], "open": v["open"], "under_1h": v["under_1h"], "returned": v["returned"],
                          "oldest": duration_label((t - v["oldest"]).total_seconds()) if v["oldest"] else "—", "oldest_case_id": v["oldest_case_id"], "can_reassign": True})
    appr_rows = [{"user_id": u, "name": person(u)["name"], "pending": v["pending"],
                  "oldest": duration_label((t - v["oldest"]).total_seconds()) if v["oldest"] else "—"} for u, v in appr.items() if u != "RSK-7714" or v["pending"]]
    return {"role_view": "SUPERVISOR", "now": iso(t), "title": "Operations overview",
            "tiles": {"open": len(open_c), "unassigned": unassigned, "under_1h": under1h, "waiting_too_long": wtl, "pending_approval": pending, "resolved_today": n_res},
            "cutoff_risk": cutoff_risk,
            "outcomes_today": {"executed_by_bank": exec_today, "handed_to_bank_awaiting": handed, "resolved_total": n_res,
                               "resolved_without_manual_repair": auto, "policy_approved": auto,
                               "percent_without_manual_repair": round(100.0 * auto / n_res, 1) if n_res else 0.0,
                               "note": "Executed counts come only from bank confirmations. Handed-to-bank items await confirmation."},
            "team_workload": team_rows, "approver_queue": appr_rows,
            "compliance_note": "Compliance cases are managed in the Compliance workspace.", "needs_decision": needs}


def approver_home(user) -> Dict[str, Any]:
    q = rw.approvals_queue(user, 1, 10, "all")
    mine = [r for r in q["items"] if (r["approver_assigned"] or {}).get("user_id") == user.user_id]
    above = sum(1 for r in q["items"] if not r["can_approve"] and "limit" in (r["cannot_approve_reason"] or "").lower())
    from app.services.v2 import stp as sp
    rev = sp.review(user)
    return {"role_view": "APPROVER", "now": iso(now()), "greeting": _greeting(user),
            "tiles": {"pending": q["total"], "mine": len(mine), "above_my_limit": above, "batch_eligible": rev["totals"]["eligible"]},
            "queue": q["items"], "stp_batch": {"eligible": rev["totals"]["eligible"], "total_value": rev["totals"]["total_value"]}}


def compliance_home(user) -> Dict[str, Any]:
    q = rw.compliance_queue(user, 1, 10)
    t = now()
    opens = [r for r in q["items"] if r["hold_status"] in ("Open hold", "Escalated")]
    oldest = None
    for r in opens:
        d = parse_ts(r.get("raised_at"))
        if d and (oldest is None or d < oldest):
            oldest = d
    return {"role_view": "COMPLIANCE", "now": iso(t), "greeting": _greeting(user),
            "tiles": {"open_holds": len(opens), "escalated": sum(1 for r in q["items"] if r["hold_status"] == "Escalated"),
                      "oldest": duration_label((t - oldest).total_seconds()) if oldest else "—"}, "queue": q["items"]}


def audit_home(user) -> Dict[str, Any]:
    from app.services.v2 import audit as au
    return {"role_view": "AUDIT", "now": iso(now()), "greeting": _greeting(user), "tiles": au.today_tiles()}


def admin_home(user) -> Dict[str, Any]:
    from app.services.v2 import admin as ad
    integ = ad.integrations()
    db = SessionLocal()
    try:
        pend = db.query(V2ModeChangeModel).filter(V2ModeChangeModel.state == "PENDING_SECOND_ADMIN").count()
    finally:
        db.close()
    return {"role_view": "ADMIN", "now": iso(now()), "greeting": _greeting(user),
            "tiles": {"integrations": integ["tiles"]["connected"], "degraded": integ["tiles"]["degraded"], "pending_mode_changes": pend}}


def home(user) -> Dict[str, Any]:
    r = role_of(user)
    if r == "SUPERVISOR":
        return supervisor_home(user)
    if r in ("OPERATIONS_APPROVER", "RISK_APPROVER"):
        return approver_home(user)
    if r == "COMPLIANCE_APPROVER":
        return compliance_home(user)
    if r == "AUDIT_RISK":
        return audit_home(user)
    if r in ("ADMIN", "POLICY_OWNER"):
        return admin_home(user)
    return maker_home(user)
