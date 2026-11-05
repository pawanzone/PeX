"""Shadow scorecard: what PeX would have done on a case, against what the bank's analyst actually did.

The bank loads one row per case it already worked: the analyst's action and, for a fix, the value applied. PeX compares that with its own
proposal and with whether the case passes the 8 straight-through rules. Nothing is released and no case changes; the only writes are the loaded
rows and one audit event per load or clear. Verdicts are computed when read, so a rule change shows up in the next view.
"""
from __future__ import annotations

import csv
import io
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from app.db.models import V2ShadowRowModel
from app.db.session import SessionLocal
from app.services.audit_service import audit_service
from app.services.v2 import logic as lg
from app.services.v2 import stp
from app.services.v2.core import HARD_BLOCK_STP, V2Error, invalid, iso, now, profile_code, role_of

ACTIONS = ("FIXED", "REJECTED", "ESCALATED", "RETURNED")
CASE_ID = "SHADOW-COMPARISON"
COLUMNS = [
    {"name": "case_id", "required": True, "meaning": "The PeX case id (or the exception id the bank sent in the event)."},
    {"name": "action", "required": True, "meaning": "What the analyst did: FIXED, REJECTED, ESCALATED or RETURNED."},
    {"name": "value", "required": False, "meaning": "For FIXED: the corrected value the analyst applied. Needed for a fix."},
    {"name": "minutes", "required": False, "meaning": "Minutes the analyst spent on the case. Used for the time-saved figure."},
    {"name": "analyst_ref", "required": False, "meaning": "Who did it (an id, not a name). Shown only to Administrators."},
    {"name": "resolved_at", "required": False, "meaning": "When the analyst finished (ISO date and time)."},
]
VERDICT_TEXT = {
    "AGREE": "Same fix as PeX proposed",
    "DIFFER": "Analyst applied a different value",
    "PEX_NO_PROPOSAL": "PeX had no proposal; the analyst fixed it",
    "ANALYST_NO_FIX": "PeX proposed a fix; the analyst did not fix it",
    "BOTH_NO_FIX": "Neither PeX nor the analyst fixed it",
}


def _norm(v: Any) -> str:
    return " ".join(str(v if v is not None else "").split()).casefold()


def _audit(user, action: str, text: str):
    audit_service.log_event(case_id=CASE_ID, correlation_id=CASE_ID, stage_name="SHADOW", actor_id=user.user_id, actor_role=role_of(user),
                            action_name=action, details=text, control_tags=["Shadow comparison"], amount=None, currency=None)


def _case_index() -> Dict[str, Dict[str, Any]]:
    from app.services.v2.rows import all_cases
    return {c["case_id"]: c for c in all_cases()}


def _clean(i: int, raw: Any, cases: Dict[str, Any]) -> Dict[str, Any]:
    """One loaded row, or {"error": reason}."""
    if not isinstance(raw, dict):
        return {"error": "Row is not an object"}
    cid = str(raw.get("case_id") or "").strip()
    act = str(raw.get("action") or "").strip().upper()
    val = raw.get("value")
    val = None if val is None or str(val).strip() == "" else str(val).strip()
    if not cid:
        return {"error": "case_id is missing"}
    if cid not in cases:
        return {"error": f"Case {cid} is not in PeX"}
    if act not in ACTIONS:
        return {"error": f"action must be one of {', '.join(ACTIONS)}"}
    if act == "FIXED" and val is None:
        return {"error": "A FIXED row needs the value the analyst applied"}
    mins = raw.get("minutes")
    if mins is None or str(mins).strip() == "":
        mins = None
    else:
        try:
            mins = float(mins)
        except (TypeError, ValueError):
            return {"error": "minutes must be a number"}
        if isinstance(raw.get("minutes"), bool) or mins < 0 or mins != mins or mins > 100_000:
            return {"error": "minutes must be zero or more"}
    return {"case_id": cid, "action": act, "value": val if act == "FIXED" else None, "minutes": mins,
            "analyst_ref": (str(raw.get("analyst_ref")).strip()[:64] or None) if raw.get("analyst_ref") else None,
            "resolved_at": (str(raw.get("resolved_at")).strip()[:64] or None) if raw.get("resolved_at") else None}


def load_rows(user, rows: List[Any]) -> Dict[str, Any]:
    cases = _case_index()
    good: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    rejected: List[Dict[str, Any]] = []
    for i, raw in enumerate(rows or [], start=1):
        c = _clean(i, raw, cases)
        if "error" in c:
            rejected.append({"row": i, "case_id": str(raw.get("case_id") or "") if isinstance(raw, dict) else "", "reason": c["error"]})
        elif c["case_id"] in good:
            rejected.append({"row": i, "case_id": c["case_id"], "reason": "The case appears twice in this file; the first row was kept"})
        else:
            good[c["case_id"]] = c
    replaced = 0
    db = SessionLocal()
    try:
        stamp = iso(now())
        for cid, c in good.items():
            r = db.query(V2ShadowRowModel).filter(V2ShadowRowModel.case_id == cid).first()
            if r:
                replaced += 1
            else:
                r = V2ShadowRowModel(case_id=cid)
                db.add(r)
            r.action, r.value, r.minutes, r.analyst_ref, r.resolved_at = c["action"], c["value"], c["minutes"], c["analyst_ref"], c["resolved_at"]
            r.loaded_by, r.loaded_at = user.user_id, stamp
        db.commit()
    finally:
        db.close()
    _audit(user, "SHADOW_COMPARISON_LOADED", f"Loaded {len(good)} analyst result(s) for comparison ({replaced} replaced, {len(rejected)} rejected). No case was changed and nothing was released.")
    return {"accepted": len(good), "replaced": replaced, "rejected": rejected}


def load_csv(user, data: bytes) -> Dict[str, Any]:
    text = data.decode("utf-8-sig", errors="replace")
    rd = csv.DictReader(io.StringIO(text))
    heads = [h.strip().lower() for h in (rd.fieldnames or [])]
    missing = [c["name"] for c in COLUMNS if c["required"] and c["name"] not in heads]
    if missing:
        raise V2Error(400, "INVALID", "The file needs these columns: " + ", ".join(missing))
    rows = [{(k or "").strip().lower(): v for k, v in r.items()} for r in rd]
    return load_rows(user, rows)


def clear(user) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        n = db.query(V2ShadowRowModel).delete()
        db.commit()
    finally:
        db.close()
    _audit(user, "SHADOW_COMPARISON_CLEARED", f"Cleared {n} loaded analyst result(s).")
    return {"cleared": n}


def _stored() -> List[V2ShadowRowModel]:
    db = SessionLocal()
    try:
        rows = db.query(V2ShadowRowModel).order_by(V2ShadowRowModel.case_id).all()
        for r in rows:
            db.expunge(r)
        return rows
    finally:
        db.close()


def _compare(r: V2ShadowRowModel, case: Dict[str, Any]) -> Dict[str, Any]:
    ev = stp.evaluate(case)
    ext = lg.ext_of(case)
    ch = ext.get("change") or {}
    pv = (ch.get("proposed") or {}).get("value")
    code = profile_code(case.get("profile"))
    would = bool(ev["eligible"]) and pv is not None and code not in HARD_BLOCK_STP
    if r.action == "FIXED":
        v = "PEX_NO_PROPOSAL" if pv is None else ("AGREE" if _norm(pv) == _norm(r.value) else "DIFFER")
    else:
        v = "ANALYST_NO_FIX" if pv is not None else "BOTH_NO_FIX"
    blocked = None
    if not would:
        blocked = (ev.get("reason_label") or "Not permitted for straight-through") if not ev["eligible"] else ("No proposal" if pv is None else "Not permitted for straight-through")
    return {"case_id": r.case_id, "profile": code, "amount": case.get("amount"), "currency": case.get("currency"), "field": ch.get("field_label"),
            "pex_would_release": would, "blocked_by": blocked, "rule": stp.RULE_OF.get(ev.get("code")) if blocked else None,
            "pex_value": pv, "analyst_action": r.action, "analyst_value": r.value, "verdict": v, "verdict_text": VERDICT_TEXT[v],
            "minutes": r.minutes, "resolved_at": r.resolved_at}


def _all() -> List[Dict[str, Any]]:
    cases = _case_index()
    return [_compare(r, cases[r.case_id]) for r in _stored() if r.case_id in cases]


def cases(verdict: Optional[str] = None, release: Optional[str] = None) -> Dict[str, Any]:
    items = _all()
    if verdict:
        items = [x for x in items if x["verdict"] == verdict.upper()]
    if release:
        items = [x for x in items if _bucket(x) == release.lower()]
    return {"items": items, "total": len(items), "verdict_text": VERDICT_TEXT}


def _bucket(x: Dict[str, Any]) -> str:
    if not x["pex_would_release"]:
        return "sent_to_person"
    return "released_correctly" if x["verdict"] == "AGREE" else "released_wrongly"


def _rate(n: int, d: int) -> Optional[float]:
    return round(n / d, 4) if d else None


def scorecard() -> Dict[str, Any]:
    items = _all()
    stored = _stored()
    c = {"released_correctly": 0, "differ": 0, "analyst_no_fix": 0, "sent_to_person": 0}
    verdict_counts = {k: 0 for k in VERDICT_TEXT}
    prof: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    mins_released = mins_all = 0.0
    with_minutes = 0
    for x in items:
        verdict_counts[x["verdict"]] += 1
        b = _bucket(x)
        p = prof.setdefault(x["profile"], {"profile": x["profile"], "compared": 0, "agree": 0, "released_correctly": 0, "released_wrongly": 0, "sent_to_person": 0})
        p["compared"] += 1
        p["agree"] += x["verdict"] == "AGREE"
        if b == "released_correctly":
            c["released_correctly"] += 1
            p["released_correctly"] += 1
            mins_released += x["minutes"] or 0
        elif b == "released_wrongly":
            c["differ" if x["verdict"] == "DIFFER" else "analyst_no_fix"] += 1
            p["released_wrongly"] += 1
        else:
            c["sent_to_person"] += 1
            p["sent_to_person"] += 1
        if x["minutes"] is not None:
            with_minutes += 1
            mins_all += x["minutes"]
    wrong = c["differ"] + c["analyst_no_fix"]
    would = c["released_correctly"] + wrong
    both = verdict_counts["AGREE"] + verdict_counts["DIFFER"]
    compared = len(items)
    loaded_at = max((r.loaded_at for r in stored), default=None)
    return {
        "compared": compared, "loaded_at": loaded_at,
        "release": {"would_release": would, "released_correctly": c["released_correctly"],
                    "released_wrongly": {"count": wrong, "differ": c["differ"], "analyst_no_fix": c["analyst_no_fix"]}, "sent_to_person": c["sent_to_person"]},
        "verdicts": [{"verdict": k, "text": VERDICT_TEXT[k], "count": verdict_counts[k]} for k in VERDICT_TEXT],
        "rates": {"agree_rate": _rate(verdict_counts["AGREE"], both), "safe_release_rate": _rate(c["released_correctly"], would)},
        "time": {"minutes_on_released": round(mins_released, 1), "released_cases": c["released_correctly"], "cases_with_minutes": with_minutes, "minutes_all": round(mins_all, 1)},
        "by_profile": sorted(prof.values(), key=lambda p: p["profile"]),
        "columns": COLUMNS,
        "note": ("Load the cases your analysts already worked (CSV or JSON) to compare PeX's proposals with what was actually done. Nothing is released and no case changes."
                 if not compared else
                 "Compared against PeX's proposal and the 8 straight-through rules as they stand now. A wrong release is a case PeX would have let through that the analyst handled differently: the number to bring to zero before any live release."),
    }
