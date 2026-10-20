"""Worklist rows, tabs, filters, previews, saved views and the Approvals / Compliance queues."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db.models import V2SavedViewModel
from app.db.session import SessionLocal
from app.services.data_loader import repo
from app.services.v2 import logic as lg
from app.services.v2 import pages as pg
from app.services.v2.core import (
    now, parse_ts, iso, duration_label, role_of, has_perm, person, profile_code, profile_label, is_compliance, party_name,
    V2Error, invalid, new_id, not_found, money,
)

TABS = ("ready", "returned", "waiting", "pending", "done")


def today_utc():
    return now().astimezone(timezone.utc).date()


def last_change(case: Dict[str, Any], ext: Dict[str, Any]):
    return parse_ts(ext.get("last_change_at")) or parse_ts(case.get("handed_off_at")) or parse_ts(case.get("settled_at")) or parse_ts(case.get("created_at"))


def done_today(case, ext) -> bool:
    lc = last_change(case, ext)
    return bool(lc and lc.astimezone(timezone.utc).date() == today_utc())


def all_cases() -> List[Dict[str, Any]]:
    return list(repo._case_cache.values())


def approver_for(case: Dict[str, Any], ext: Dict[str, Any]) -> str:
    if ext.get("approver_assigned"):
        return ext["approver_assigned"]
    if float(case.get("amount") or 0) >= __import__('app.services.v2.policy', fromlist=['x']).get("dual_auth_amount"):
        return "RSK-7714"
    return "APR-3191" if int(hashlib.sha256(case["case_id"].encode()).hexdigest()[:4], 16) % 2 == 0 else "APR-3192"


def is_mine(case, ext, uid: str) -> bool:
    return ext.get("assignee") == uid or case.get("maker_id") == uid


def in_scope(case, ext, user, tab: str, scope: str) -> bool:
    if scope == "all":
        return True
    uid = user.user_id
    if tab == "ready":
        return ext.get("assignee") in (None, uid)
    return is_mine(case, ext, uid)


def default_scope(user) -> str:
    return "mine" if role_of(user) == "OPERATOR" else "all"


def matches_filters(case, ext, row, f: Dict[str, Any]) -> bool:
    if f.get("exception_type") and row["exception"]["code"] != f["exception_type"] and row["exception"]["label"] != f["exception_type"]:
        return False
    if f.get("rail") and row["rail"]["key"] != f["rail"]:
        return False
    if f.get("currency") and row["amount"]["currency"] != f["currency"]:
        return False
    if f.get("cutoff_band"):
        b = (row["cutoff"] or {}).get("band")
        if b != f["cutoff_band"] and not (f["cutoff_band"] == "under_1h" and b == "passed"):
            return False
    if f.get("evidence") and row["evidence"]["status"] != f["evidence"]:
        return False
    if f.get("assignee") == "none" and ext.get("assignee"):
        return False
    q = (f.get("q") or "").strip().lower()
    if q:
        hay = " ".join([case["case_id"], row["counterparty"], row["exception"]["label"], str(case.get("payment_ref", "")), str(case.get("uetr", ""))]).lower()
        if q not in hay:
            return False
    return True


def sort_rows(rows, sort: str, direction: str):
    rev = (direction or "asc").lower() == "desc"
    if sort == "amount":
        key = lambda r: r["amount"]["amount"]
    elif sort == "case":
        key = lambda r: r["case_id"]
    else:
        key = lambda r: (r["cutoff"] or {}).get("seconds_left", 10 ** 9)
    return sorted(rows, key=key, reverse=rev)


def build_rows(user, scope: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    scope = scope or default_scope(user)
    by_tab: Dict[str, List[Dict[str, Any]]] = {t: [] for t in TABS}
    for case in all_cases():
        ext = lg.ext_of(case)
        t = lg.tab_of(case, ext)
        if t not in by_tab:
            continue
        if t == "done" and not done_today(case, ext):
            continue
        if not in_scope(case, ext, user, t, scope):
            continue
        row = lg.row_core(case, user)
        row["selected_detail"] = None
        row["_ext"] = ext
        by_tab[t].append(row)
    return by_tab


def strip(r):
    r = dict(r)
    r.pop("_ext", None)
    r.pop("tab", None)
    return r


def facets_for(rows) -> Dict[str, Any]:
    ex, rl, cc = {}, {}, set()
    for r in rows:
        k = r["exception"]["code"]
        ex.setdefault(k, {"value": k, "label": r["exception"]["label"], "count": 0})["count"] += 1
        rl.setdefault(r["rail"]["key"], {"value": r["rail"]["key"], "label": r["rail"]["label"], "count": 0})["count"] += 1
        cc.add(r["amount"]["currency"])
    return {"exception_types": sorted(ex.values(), key=lambda x: -x["count"]), "rails": sorted(rl.values(), key=lambda x: -x["count"]),
            "currencies": sorted(cc)}


def worklist(user, tab: str, page: int, page_size: int, filters: Dict[str, Any], sort: str, direction: str, scope: Optional[str], view_id: Optional[str]):
    if tab not in TABS:
        raise invalid(f"tab must be one of {', '.join(TABS)}", "tab")
    if view_id:
        v = get_view(user, view_id)
        merged = dict(v["filters"])
        merged.update({k: val for k, val in filters.items() if val})
        filters = merged
        sort = sort or v.get("sort") or "cutoff"
        tab = filters.get("tab", tab)
    by_tab = build_rows(user, scope)
    counts = {t: len(by_tab[t]) for t in TABS}
    base = by_tab[tab]
    sel = [r for r in base if matches_filters(None or lg_case(r["case_id"]), r["_ext"], r, filters)]
    sel = sort_rows(sel, sort or "cutoff", direction or "asc")
    page_size = max(1, min(int(page_size or 25), 200))
    page = max(1, int(page or 1))
    chunk = sel[(page - 1) * page_size: page * page_size]
    return {"tab": tab, "counts": counts, "page": page, "page_size": page_size, "total": len(sel),
            "facets": facets_for(base), "items": [strip(r) for r in chunk], "now": iso(now()), "scope": scope or default_scope(user)}


def lg_case(case_id: str) -> Dict[str, Any]:
    return repo.get_case(case_id) or {"case_id": case_id}


def preview(case_id: str, user) -> Dict[str, Any]:
    case = repo.get_case(case_id)
    if not case:
        raise not_found(f"Case {case_id}")
    ext = lg.ext_of(case)
    variant = lg.derive_variant(case, ext)
    nxt = lg.next_action(case, ext, variant, user)
    rows = ext.get("evidence") or []
    es = pg.evidence_summary(rows, lg.evidence_state(ext))
    ch = ext.get("change")
    controls = [
        {"label": "Validation", "state": "passed" if (ch and lg.evidence_state(ext) == "complete") else ("blocked" if lg.evidence_state(ext) != "complete" else "pending")},
        {"label": "Approver required" if not lg.is_dual(case) else "Two approvers required (dual authorisation)", "state": "pending"},
        {"label": "Compliance", "state": "blocked" if variant == "COMPLIANCE_HOLD" else "passed"},
    ]
    return {"case_id": case_id, "variant": variant, "why_flagged": case.get("reason"),
            "change": ({"field": ch["field_label"], "original": ch["original"]["value"], "proposed": ch["proposed"]["value"]} if ch else None),
            "evidence_summary": es["label"], "controls": controls, "next_action": nxt, "actions": pg.build_actions(case, ext, variant, user),
            "header": {"amount": money(case.get("amount"), case.get("currency")), "counterparty": ext.get("counterparty")}}


# ---- saved views --------------------------------------------------------------------------------
def list_views(user) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = db.query(V2SavedViewModel).filter(V2SavedViewModel.owner_id == user.user_id).order_by(V2SavedViewModel.created_at).all()
        return [{"id": r.id, "name": r.name, "owner": r.owner_id, "filters": r.filters or {}, "sort": r.sort, "created_at": r.created_at} for r in rows]
    finally:
        db.close()


def get_view(user, view_id: str) -> Dict[str, Any]:
    for v in list_views(user):
        if v["id"] == view_id:
            return v
    raise not_found(f"Saved view {view_id}")


def create_view(user, name: str, filters: Dict[str, Any], sort: Optional[str]) -> Dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise invalid("A view name is required", "name")
    allowed = {"tab", "exception_type", "rail", "currency", "cutoff_band", "evidence", "q", "assignee"}
    clean = {k: v for k, v in (filters or {}).items() if k in allowed and v not in (None, "")}
    db = SessionLocal()
    try:
        vid = new_id("VW")[:20]
        db.add(V2SavedViewModel(id=vid, owner_id=user.user_id, name=name[:128], filters=clean, sort=sort, created_at=iso(now())))
        db.commit()
        return {"id": vid, "name": name, "owner": user.user_id, "filters": clean, "sort": sort, "created_at": iso(now())}
    finally:
        db.close()


def delete_view(user, view_id: str):
    db = SessionLocal()
    try:
        r = db.query(V2SavedViewModel).filter(V2SavedViewModel.id == view_id, V2SavedViewModel.owner_id == user.user_id).first()
        if not r:
            raise not_found(f"Saved view {view_id}")
        db.delete(r)
        db.commit()
        return {"ok": True, "deleted": view_id}
    finally:
        db.close()


# ---- approvals / compliance queues ----------------------------------------------------------------
def approvals_queue(user, page: int, page_size: int, tier: str, desk: str = "all"):
    items = []
    for case in all_cases():
        if lg.status_of(case) not in lg.PENDING or is_compliance(case):
            continue
        ext = lg.ext_of(case)
        dual = lg.is_dual(case)
        if tier == "1" and dual and lg.status_of(case) != "PENDING_APPROVAL":
            continue
        if tier == "2" and not dual:
            continue
        row = lg.row_core(case, user)
        ok, code, msg = lg.approve_gate(case, user)
        sub = parse_ts(ext.get("submitted_at")) or last_change(case, ext)
        row.update({
            "submitted_by": person(case.get("maker_id")), "submitted_at": iso(sub),
            "waiting_for": duration_label((now() - sub).total_seconds()) if sub else None,
            "approver_assigned": person(approver_for(case, ext)), "dual_auth": dual,
            "can_approve": ok, "cannot_approve_reason": None if ok else msg,
        })
        assigned = row["approver_assigned"] or {}
        row["mine"] = bool(ok or (assigned.get("user_id") and assigned.get("user_id") == getattr(user, "user_id", None)))
        if not row["mine"] and not row["cannot_approve_reason"]:
            row["cannot_approve_reason"] = f"With {assigned.get('name') or 'another approver'}"
        row.pop("tab", None)
        items.append(row)
    items.sort(key=lambda r: (r["cutoff"] or {}).get("seconds_left", 10 ** 9))
    counts = {"mine": sum(1 for r in items if r["mine"]), "others": sum(1 for r in items if not r["mine"])}
    if desk == "mine":
        items = [r for r in items if r["mine"]]
    elif desk == "others":
        items = [r for r in items if not r["mine"]]
    page_size = max(1, min(int(page_size or 25), 200))
    page = max(1, int(page or 1))
    return {"page": page, "page_size": page_size, "total": len(items), "counts": counts, "desk": desk, "items": items[(page - 1) * page_size: page * page_size], "now": iso(now())}


def compliance_queue(user, page: int, page_size: int):
    items = []
    for case in all_cases():
        if not is_compliance(case):
            continue
        st = lg.status_of(case)
        ext = lg.ext_of(case)
        if st in lg.DONE and not done_today(case, ext):
            continue
        row = lg.row_core(case, user)
        cd = pg._compliance(case, ext)
        row.update({"screening_ref": cd["alert"]["reference"], "raised_at": cd["alert"]["raised_at"],
                    "hold_status": "Released" if (ext.get("compliance") or {}).get("released") else ("Blocked" if st == "REJECTED" else
                                                                                                   ("Escalated" if (ext.get("compliance") or {}).get("escalated") else "Open hold"))})
        row.pop("tab", None)
        items.append(row)
    items.sort(key=lambda r: (r["cutoff"] or {}).get("seconds_left", 10 ** 9))
    page_size = max(1, min(int(page_size or 25), 200))
    page = max(1, int(page or 1))
    return {"page": page, "page_size": page_size, "total": len(items), "items": items[(page - 1) * page_size: page * page_size], "now": iso(now())}
