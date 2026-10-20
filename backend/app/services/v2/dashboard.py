"""GET /api/v2/dashboard: the bank-wide picture, the same numbers for every role, plus a few extras per role.

Answers three questions: what is going on, where is something stuck (and with whom), and which cases may breach their SLA.
All numbers are computed from the case store; nothing here is typed in.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.db.models import AuditEventModel, V2ModeChangeModel
from app.db.session import SessionLocal
from app.services.data_loader import repo
from app.services.v2 import logic as lg
from app.services.v2 import rows as rw
from app.services.v2.core import cutoff_obj, duration_label, iso, now, parse_ts, person, rail_obj, role_of

FINAL = lg.DONE - {"DISPATCHED"}        # a case handed to the bank is still in flight until the bank confirms

STAGES = [
    ("with_maker", "With maker", "Being worked or waiting to be picked up"),
    ("waiting_client", "Waiting on client", "Information requested, reply not in yet"),
    ("evidence_conflict", "Evidence conflict", "Sources disagree; a person must decide"),
    ("pending_approval", "Pending approval", "Submitted, waiting for an approver"),
    ("compliance_hold", "Compliance hold", "Sanctions or screening review"),
    ("status_unknown", "Status unknown", "No answer from the bank after hand-off"),
    ("with_bank", "Handed to bank", "Waiting for the bank's signed confirmation"),
]
STAGE_LABEL = {k: label for k, label, _ in STAGES}

STUCK_AFTER_MIN = {"pending_approval": 60, "evidence_conflict": 60, "compliance_hold": 120, "status_unknown": 10, "with_maker": 45,
                   "waiting_client": 0, "with_bank": 15}


def _stage(case: Dict[str, Any], ext: Dict[str, Any]) -> str:
    v = lg.derive_variant(case, ext)
    st = lg.status_of(case)
    if st == "DISPATCHED" or v == "HANDED_TO_BANK":
        return "with_bank"
    return {"COMPLIANCE_HOLD": "compliance_hold", "STATUS_UNKNOWN": "status_unknown", "APPROVAL": "pending_approval",
            "MISSING_INFO": "waiting_client", "CONFLICT": "evidence_conflict"}.get(v, "with_maker")


def _owner(case: Dict[str, Any], ext: Dict[str, Any], stage: str) -> Dict[str, Any]:
    if stage in ("status_unknown", "with_bank"):
        return {"user_id": None, "name": "Bank operations", "role": "Bank"}
    if stage == "compliance_hold":
        return {"user_id": None, "name": "Compliance", "role": "Compliance"}
    if stage == "pending_approval":
        p = person(rw.approver_for(case, ext)) or {"name": "Approver"}
        return {"user_id": p.get("user_id"), "name": p["name"], "role": "Approver"}
    asg = person(ext.get("assignee"))
    if stage == "waiting_client" and not asg:
        return {"user_id": None, "name": "Client", "role": "Client"}
    if asg:
        return {"user_id": asg["user_id"], "name": asg["name"], "role": "Maker"}
    return {"user_id": None, "name": "Unassigned", "role": "Maker"}


def _since(case: Dict[str, Any], ext: Dict[str, Any], stage: str):
    if stage == "pending_approval":
        return parse_ts(ext.get("submitted_at")) or rw.last_change(case, ext)
    if stage in ("status_unknown", "with_bank"):
        lc = parse_ts((ext.get("last_status_check") or {}).get("at"))
        return lc or parse_ts(case.get("handed_off_at")) or rw.last_change(case, ext)
    return rw.last_change(case, ext)


def _reason(stage: str, owner: Dict[str, Any], mins: int) -> str:
    d = duration_label(mins * 60)
    return {
        "pending_approval": f"Waiting {d} for approver {owner['name']}",
        "evidence_conflict": f"Evidence conflict open for {d} with {owner['name']}",
        "compliance_hold": f"Compliance hold open for {d}",
        "status_unknown": f"No bank confirmation for {d}; check status, do not resend",
        "with_bank": f"Handed to bank {d} ago, no confirmation yet",
        "waiting_client": f"Waiting {d} for the client's reply",
        "with_maker": (f"Unassigned for {d}" if owner["name"] == "Unassigned" else f"With {owner['name']} for {d} without a change"),
    }[stage]


def _cutoff_band(left: Optional[float]) -> str:
    if left is None:
        return "none"
    if left <= 0:
        return "passed"
    return "under_1h" if left < 3600 else ("1_to_3h" if left <= 10800 else "over_3h")


def dashboard(user, stuck_limit: int = 10) -> Dict[str, Any]:
    t = now()
    open_cases: List[Dict[str, Any]] = []
    stage_ct = {k: {"count": 0, "oldest": None, "oldest_case_id": None} for k, _, _ in STAGES}
    bands = {"passed": 0, "under_1h": 0, "1_to_3h": 0, "over_3h": 0, "none": 0}
    ageing = {"under_1h": 0, "1_to_4h": 0, "4_to_24h": 0, "over_24h": 0}
    at_risk: List[Dict[str, Any]] = []
    stuck: List[Dict[str, Any]] = []
    rails: Dict[str, Dict[str, Any]] = {}
    people: Dict[str, Dict[str, Any]] = {}
    done_exec = done_handed = done_failed = 0
    conflicts = missing = low_conf = pings = unassigned = 0
    mine = {"open": 0, "returned": 0, "ready": 0, "pending_mine": 0, "dual": 0}
    uid = getattr(user, "user_id", None)

    for c in rw.all_cases():
        ext = lg.ext_of(c)
        st = lg.status_of(c)
        if st in FINAL:
            if rw.done_today(c, ext):
                if st in lg.FINAL_OK:
                    done_exec += 1
                else:
                    done_failed += 1
            continue
        stage = _stage(c, ext)
        owner = _owner(c, ext, stage)
        since = _since(c, ext, stage)
        mins = int((t - since).total_seconds() // 60) if since else 0
        if stage == "with_bank":
            done_handed += 1
        cut = lg.cutoff_dt(c, ext)
        left = (cut - t).total_seconds() if cut else None
        sc = stage_ct[stage]
        sc["count"] += 1
        if since and (sc["oldest"] is None or since < sc["oldest"]):
            sc["oldest"], sc["oldest_case_id"] = since, c["case_id"]
        if stage == "with_bank":
            continue                                    # in flight at the bank: counted as a stage, not as open work for SLA and ageing
        open_cases.append(c)
        bands[_cutoff_band(left)] += 1
        cr = parse_ts(c.get("created_at"))
        age_h = (t - cr).total_seconds() / 3600 if cr else 0
        ageing["under_1h" if age_h < 1 else "1_to_4h" if age_h < 4 else "4_to_24h" if age_h < 24 else "over_24h"] += 1
        rl = rail_obj(c.get("payment_rail"))
        rr = rails.setdefault(rl["key"], {"rail": rl["label"], "open": 0, "at_risk": 0, "next": None})
        rr["open"] += 1
        if left is not None and left < 3600:
            rr["at_risk"] += 1
        if left is not None and left > 0 and (rr["next"] is None or cut < rr["next"]):
            rr["next"] = cut
        if stage == "evidence_conflict":
            conflicts += 1
        if ext.get("evidence_state") == "missing":
            missing += 1
        if lg.review_pending(ext):
            low_conf += 1
        if (c.get("expedite_ping") or {}).get("status") == "UNREAD":
            pings += 1
        if stage == "with_maker" and owner["name"] == "Unassigned":
            unassigned += 1
        key = owner["user_id"] or owner["name"]
        pw = people.setdefault(key, {"user_id": owner["user_id"], "name": owner["name"], "role": owner["role"], "open": 0, "at_risk": 0})
        pw["open"] += 1
        if left is not None and left < 3600:
            pw["at_risk"] += 1
        row = {"case_id": c["case_id"], "exception": (c.get("profile") or "").replace("_", " ").title(), "amount": c.get("amount"),
               "currency": c.get("currency"), "stage": STAGE_LABEL[stage], "stage_key": stage, "with": owner,
               "cutoff": cutoff_obj(cut, t) if cut else None, "link": f"/cases/{c['case_id']}"}
        if left is not None and left < 3600:
            at_risk.append(row)
        limit = STUCK_AFTER_MIN.get(stage, 60)
        is_stuck = mins >= limit and (stage != "waiting_client" or (lg.request_state(ext) == "overdue"))
        if is_stuck:
            stuck.append({**row, "minutes": mins, "waiting": duration_label(mins * 60), "reason": _reason(stage, owner, mins)})
        if uid:
            if ext.get("assignee") == uid:
                mine["open"] += 1
                tab = lg.tab_of(c, ext)
                mine["returned"] += 1 if tab == "returned" else 0
                mine["ready"] += 1 if tab == "ready" else 0
            if stage == "pending_approval" and owner["user_id"] == uid:
                mine["pending_mine"] += 1
            if lg.is_dual(c) and stage == "pending_approval":
                mine["dual"] += 1

    at_risk.sort(key=lambda r: (r["cutoff"] or {}).get("seconds_left", 10 ** 9))
    stuck.sort(key=lambda r: -r["minutes"])
    open_n = len(open_cases)
    n = stage_ct

    headline = [
        {"key": "open", "label": "Open work", "value": open_n, "tone": "neutral", "hint": "Cases being worked, excluding handed to bank"},
        {"key": "awaiting_approval", "label": "Awaiting approval", "value": n["pending_approval"]["count"], "tone": "info", "hint": "Submitted by a maker"},
        {"key": "compliance_holds", "label": "Compliance holds", "value": n["compliance_hold"]["count"], "tone": "warn", "hint": "Sanctions or screening"},
        {"key": "with_bank", "label": "With the bank", "value": n["with_bank"]["count"] + n["status_unknown"]["count"], "tone": "neutral", "hint": "Handed over or status unknown"},
        {"key": "sla_breached", "label": "SLA breached", "value": bands["passed"], "tone": "danger", "hint": "Cutoff already passed"},
        {"key": "sla_under_1h", "label": "May breach within 1 hour", "value": bands["under_1h"], "tone": "warn", "hint": "Cutoff in under an hour"},
        {"key": "stuck", "label": "Stuck", "value": len(stuck), "tone": "danger" if stuck else "success", "hint": "No movement beyond the stage's normal wait"},
    ]
    sla_bands = [{"band": "passed", "label": "Breached", "count": bands["passed"]}, {"band": "under_1h", "label": "Under 1 hour", "count": bands["under_1h"]},
                 {"band": "1_to_3h", "label": "1 to 3 hours", "count": bands["1_to_3h"]}, {"band": "over_3h", "label": "Over 3 hours", "count": bands["over_3h"]},
                 {"band": "none", "label": "No cutoff", "count": bands["none"]}]
    stages = [{"key": k, "label": lab, "hint": hint, "count": n[k]["count"],
               "oldest": duration_label((t - n[k]["oldest"]).total_seconds()) if n[k]["oldest"] else "—", "oldest_case_id": n[k]["oldest_case_id"]}
              for k, lab, hint in STAGES]
    workload = sorted(people.values(), key=lambda p: (-p["at_risk"], -p["open"]))[:12]
    rail_rows = [{"rail": v["rail"], "open": v["open"], "at_risk": v["at_risk"], "next_cutoff": cutoff_obj(v["next"], t) if v["next"] else None}
                 for v in sorted(rails.values(), key=lambda r: (-r["at_risk"], -r["open"]))]
    resolved = done_exec
    out = {
        "now": iso(t), "scope": {"label": "Bank-wide", "note": "The same picture for every role. Extras below are for your role."},
        "headline": headline, "sla": {"bands": sla_bands, "breached": bands["passed"], "under_1h": bands["under_1h"]},
        "at_risk": at_risk[:8], "stuck": stuck[:max(1, min(int(stuck_limit), 200))], "stuck_total": len(stuck), "stages": stages,
        "ageing": [{"band": "under_1h", "label": "Under 1 hour", "count": ageing["under_1h"]}, {"band": "1_to_4h", "label": "1 to 4 hours", "count": ageing["1_to_4h"]},
                   {"band": "4_to_24h", "label": "4 to 24 hours", "count": ageing["4_to_24h"]}, {"band": "over_24h", "label": "Over 24 hours", "count": ageing["over_24h"]}],
        "rails": rail_rows, "workload": workload,
        "outcomes_today": {"executed_by_bank": done_exec, "awaiting_bank_confirmation": done_handed, "rejected_or_failed": done_failed, "resolved": resolved,
                           "note": "Executed counts come only from signed bank confirmations."},
        "attention": {"evidence_conflicts": conflicts, "evidence_missing": missing, "independent_review_pending": low_conf,
                      "expedite_pings_active": pings, "unassigned": unassigned},
    }
    out["role_extras"] = _extras(user, mine, out)
    return out


def _extras(user, mine: Dict[str, int], d: Dict[str, Any]) -> Dict[str, Any]:
    r = role_of(user)
    att = d["attention"]
    if r == "OPERATOR":
        return {"title": "Your work", "items": [{"label": "Assigned to you", "value": mine["open"]}, {"label": "Returned to you", "value": mine["returned"]},
                                                  {"label": "Ready to work", "value": mine["ready"]}], "link": "/worklist"}
    if r == "SUPERVISOR":
        return {"title": "Team control", "items": [{"label": "Unassigned cases", "value": att["unassigned"]}, {"label": "Expedite pings active", "value": att["expedite_pings_active"]},
                                                     {"label": "People with cases at risk", "value": sum(1 for w in d["workload"] if w["at_risk"])}], "link": "/worklist"}
    if r in ("OPERATIONS_APPROVER", "RISK_APPROVER"):
        return {"title": "Your approvals", "items": [{"label": "Waiting for you", "value": mine["pending_mine"]}, {"label": "Dual authorisation waiting", "value": mine["dual"]},
                                                      {"label": "Independent evidence reviews pending", "value": att["independent_review_pending"]}], "link": "/approvals"}
    if r == "COMPLIANCE_APPROVER":
        holds = next((s["count"] for s in d["stages"] if s["key"] == "compliance_hold"), 0)
        return {"title": "Compliance", "items": [{"label": "Open holds", "value": holds}, {"label": "Evidence conflicts bank-wide", "value": att["evidence_conflicts"]}], "link": "/compliance"}
    if r == "POLICY_OWNER":
        from app.db.models import V2PolicyChangeModel
        db = SessionLocal()
        try:
            pending = db.query(V2PolicyChangeModel).filter(V2PolicyChangeModel.status == "PENDING").count()
            active = db.query(V2PolicyChangeModel).filter(V2PolicyChangeModel.status == "ACTIVE").count()
        finally:
            db.close()
        return {"title": "Rules and policy", "items": [{"label": "Changes waiting for a decision", "value": pending}, {"label": "Rules changed from the default", "value": active}], "link": "/policy"}
    if r == "AUDIT_RISK":
        since = iso(now() - timedelta(hours=24))
        db = SessionLocal()
        try:
            reveals = db.query(AuditEventModel).filter(AuditEventModel.action_name == "PII_REVEALED").count()
            sod = db.query(AuditEventModel).filter(AuditEventModel.action_name.like("%SOD%")).count()
        finally:
            db.close()
        return {"title": "Audit and risk", "items": [{"label": "Personal-data reveals recorded", "value": reveals}, {"label": "Separation-of-duties blocks recorded", "value": sod},
                                                     {"label": "Low-confidence cases routed for review", "value": att["independent_review_pending"]}], "link": "/audit"}
    from app.services.v2 import admin as ad
    from app.services.v2 import zone
    integ = ad.integrations()
    db = SessionLocal()
    try:
        pend = db.query(V2ModeChangeModel).filter(V2ModeChangeModel.state == "PENDING_SECOND_ADMIN").count()
    finally:
        db.close()
    real = sum(1 for c in zone.connector_status() if c["mode"] == "real")
    return {"title": "Platform", "items": [{"label": "Integrations connected", "value": integ["tiles"]["connected"]}, {"label": "Integrations degraded", "value": integ["tiles"]["degraded"]},
                                           {"label": "Evidence connectors set to real", "value": real}, {"label": "Mode changes awaiting a second admin", "value": pend}], "link": "/admin/integrations"}
