"""Rules & Policy Studio engine: the numbers the platform decides by, changed through a proposal and a second person's approval.

A rule has a default (what the code ships with) and, once a change is approved, a value in force. Every consumer asks
`policy.get(key)`; nothing else reads the constants directly. Changes are versioned rows (v2_policy_changes) and every step is audited.
The value in force is cached in the process; a change takes effect immediately in the process that approved it (single-worker demo).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from app.config import settings
from app.db.models import V2PolicyChangeModel
from app.db.session import SessionLocal
from app.services.audit_service import audit_service
from app.services.v2.core import V2Error, bad_state, iso, new_id, not_found, now, person, role_of

# key -> definition. `default` is a callable so it always reads the shipped constant.
PARAMS: List[Dict[str, Any]] = [
    {"key": "dual_auth_amount", "label": "Dual authorisation from", "group": "Approval", "unit": "payment currency", "min": 10_000, "max": 100_000_000, "step": 5_000, "kind": "amount",
     "description": "Payments at or above this amount need two different approvers.", "used_by": "Approvals queue (Level 2), case approval gate, expedite routing",
     "default": lambda: _lg().DUAL_AUTH_THRESHOLD},
    {"key": "batch_limit", "label": "One-click batch approval limit", "group": "Approval", "unit": "payment currency", "min": 1_000, "max": 1_000_000, "step": 1_000, "kind": "amount",
     "description": "Validated micro-repairs under this amount can be approved together on the batch screen. A human still approves.", "used_by": "Low-risk batch approval screen",
     "default": lambda: float(settings.BATCH_APPROVAL_MAX_AMOUNT)},
    {"key": "zero_touch_limit", "label": "Zero-touch release limit", "group": "Approval", "unit": "payment currency", "min": 1_000, "max": 1_000_000, "step": 1_000, "kind": "amount",
     "description": "In auto-release mode, a case that passes all 8 straight-through rules and is at or under this amount is eligible for release with no person. Never applies to profiles marked never straight-through.",
     "used_by": "Straight-through engine, batch screen (auto-release marker), Admin pages", "default": lambda: float(settings.STP_MAX_AMOUNT)},
    {"key": "release_mode", "label": "Release mode", "group": "Approval", "unit": "choice", "kind": "choice", "min": 0, "max": 0, "step": 0,
     "description": "Who releases cases that pass all 8 straight-through rules. It never loosens a rule: a case that fails one, or a profile marked never straight-through, always goes to a person.",
     "used_by": "Batch approval screen", "options": [
         {"value": "AUTO_RELEASE", "label": "Auto-release", "meaning": "Eligible cases at or under the zero-touch limit can be released with no person. People can still release in bulk."},
         {"value": "APPROVE_ALL", "label": "Approve all", "meaning": "A person approves all eligible cases in one click on the batch screen. Exceptions are listed with the rule that stopped them."},
         {"value": "REVIEW_EACH", "label": "Review each", "meaning": "No bulk release. A person opens and approves every case."}],
     "default": lambda: "APPROVE_ALL"},
    {"key": "confidence_threshold", "label": "Decision confidence threshold", "group": "Evidence", "unit": "percent", "min": 50, "max": 99, "step": 1, "kind": "int",
     "description": "Below this confidence a second person must review the evidence before the repair can be approved.", "used_by": "Evidence confidence gate on every case",
     "default": lambda: _em().CONFIDENCE_THRESHOLD},
    {"key": "reveal_minutes", "label": "Personal-data reveal window", "group": "Data protection", "unit": "minutes", "min": 1, "max": 60, "step": 1, "kind": "int",
     "description": "How long real values stay visible after an authorised reveal, before they hide again.", "used_by": "Reveal on case pages",
     "default": lambda: _pii().REVEAL_MINUTES},
    {"key": "expedite_cooldown_min", "label": "Expedite cooldown", "group": "SLA", "unit": "minutes", "min": 1, "max": 120, "step": 1, "kind": "int",
     "description": "The same level cannot be pinged again sooner than this.", "used_by": "Ping / escalate ladder", "default": lambda: _ex().COOLDOWN_MIN},
    {"key": "expedite_auto_escalate_min", "label": "Automatic escalation after", "group": "SLA", "unit": "minutes", "min": 5, "max": 240, "step": 1, "kind": "int",
     "description": "An unanswered expedite request climbs one level by itself after this long.", "used_by": "Ping / escalate ladder", "default": lambda: _ex().AUTO_ESCALATE_MIN},
    {"key": "network_response_hours", "label": "Network case response time", "group": "SLA", "unit": "hours", "min": 1, "max": 240, "step": 1, "kind": "int",
     "description": "How long we have to answer an investigation or recall from another bank, and how long we wait for theirs.", "used_by": "Network cases: due time and overdue flag",
     "default": lambda: _nw().RESPONSE_HOURS},
]
BY_KEY = {p["key"]: p for p in PARAMS}


def _f(v: Any) -> str:
    return f"{v:,}" if isinstance(v, (int, float)) else str(v)


def _lg():
    from app.services.v2 import logic
    return logic


def _em():
    from app.services.v2 import evidence_model
    return evidence_model


def _pii():
    from app.services.v2 import pii
    return pii


def _ex():
    from app.services.v2 import expedite
    return expedite


def _nw():
    from app.services.v2 import network
    return network


# ---- value in force -------------------------------------------------------------------------------------------
_cache: Dict[str, Any] = {}
_loaded = False


def reset_cache():
    global _loaded
    _cache.clear()
    _loaded = False


def reset_all():
    """Tests and demo reset: forget every change."""
    db = SessionLocal()
    try:
        db.query(V2PolicyChangeModel).delete()
        db.commit()
    finally:
        db.close()
    reset_cache()


def _load():
    global _loaded
    db = SessionLocal()
    try:
        _cache.clear()
        for r in db.query(V2PolicyChangeModel).filter(V2PolicyChangeModel.status == "ACTIVE").all():
            _cache[r.key] = r.value
    finally:
        db.close()
    _loaded = True


def get(key: str) -> Any:
    if not _loaded:
        _load()
    if key in _cache:
        return _cache[key]
    return BY_KEY[key]["default"]()


# ---- validation -----------------------------------------------------------------------------------------------
def _clean(key: str, value: Any) -> Any:
    p = BY_KEY.get(key)
    if not p:
        raise not_found(f"Rule {key}")
    if p["kind"] == "choice":
        if not isinstance(value, str) or value not in {o["value"] for o in p["options"]}:
            raise V2Error(422, "INVALID", f"{p['label']} must be one of: " + ", ".join(o["value"] for o in p["options"]) + ".")
        return value
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise V2Error(422, "INVALID", f"{p['label']} must be a number.")
    if v != v or v < p["min"] or v > p["max"]:
        raise V2Error(422, "INVALID", f"{p['label']} must be between {p['min']:,} and {p['max']:,} ({p['unit']}).")
    return float(v) if p["kind"] == "amount" else int(round(v))


# ---- impact on recent cases -----------------------------------------------------------------------------------
def impact(key: str, new: Any) -> Dict[str, Any]:
    from app.services.data_loader import repo
    from app.services.v2 import logic as lg
    from app.services.v2 import stp
    new = _clean(key, new)
    old = get(key)
    cases = list(repo._case_cache.values())
    hit: List[Dict[str, Any]] = []
    if key == "dual_auth_amount":
        for c in cases:
            if lg.status_of(c) not in lg.PENDING:
                continue
            forced = bool(c.get("dual_auth_required")) or lg.status_of(c) == "AWAITING_SECOND_APPROVAL"
            a = float(c.get("amount") or 0)
            if (a >= old or forced) != (a >= new or forced):
                hit.append({"case_id": c["case_id"], "amount": a, "currency": c.get("currency"), "now": "two approvers" if new > old else "one approver", "was": "one approver" if new > old else "two approvers"})
        verb = "need one approver instead of two" if new > old else "need two approvers instead of one"
        scope = "pending"
    elif key == "batch_limit":
        for c in cases:
            ext = lg.ext_of(c)
            if not stp.is_candidate(c, ext):
                continue
            a = float(c.get("amount") or 0)
            if (a < old) != (a < new):
                hit.append({"case_id": c["case_id"], "amount": a, "currency": c.get("currency"), "now": "eligible" if a < new else "not eligible", "was": "eligible" if a < old else "not eligible"})
        verb = "become eligible for batch approval" if new > old else "stop being eligible for batch approval"
        scope = "candidate"
    elif key == "confidence_threshold":
        for c in cases:
            if lg.status_of(c) in lg.DONE:
                continue
            conf = lg.confidence_of(c)
            if not conf or not conf["applies"]:
                continue
            pct = conf["confidence_pct"]
            if (pct < old) != (pct < new):
                hit.append({"case_id": c["case_id"], "amount": float(c.get("amount") or 0), "currency": c.get("currency"), "now": "extra review" if pct < new else "no extra review", "was": "extra review" if pct < old else "no extra review"})
        verb = "need an extra evidence review" if new > old else "no longer need an extra evidence review"
        scope = "open"
    elif key == "release_mode":
        label = {o["value"]: o["label"] for o in BY_KEY[key]["options"]}
        return {"cases_affected": 0, "cases": [], "old": old, "new": new,
                "summary": f"Changes how eligible cases are released: {label[old]} to {label[new]}. Takes effect on the batch screen straight away. No case changes state."}
    elif key == "zero_touch_limit":
        for c in cases:
            ext = lg.ext_of(c)
            if not stp.is_candidate(c, ext) or not stp.evaluate(c)["eligible"]:
                continue
            a = float(c.get("amount") or 0)
            if (a <= old) != (a <= new):
                hit.append({"case_id": c["case_id"], "amount": a, "currency": c.get("currency"), "now": "auto-release eligible" if a <= new else "person releases", "was": "auto-release eligible" if a <= old else "person releases"})
        verb = "become eligible for auto-release" if new > old else "stop being eligible for auto-release"
        scope = "eligible"
    else:
        nxt = {"reveal_minutes": "reveal", "network_response_hours": "network case received or raised"}.get(key, "expedite request")
        return {"cases_affected": 0, "cases": [], "summary": f"Takes effect for the next {nxt}. No case changes.", "old": old, "new": new}
    hit.sort(key=lambda h: -h["amount"])
    n = len(hit)
    summary = f"{n} {scope} case{'s' if n != 1 else ''} would {verb}." if n else f"No {scope} case changes with this value."
    return {"cases_affected": n, "cases": hit[:8], "summary": summary, "old": old, "new": new}


# ---- workflow -------------------------------------------------------------------------------------------------
def _row(r: V2PolicyChangeModel) -> Dict[str, Any]:
    p = BY_KEY.get(r.key, {})
    return {"id": r.id, "key": r.key, "label": p.get("label", r.key), "value": r.value, "prev_value": r.prev_value, "status": r.status, "reason": r.reason,
            "proposed_by": person(r.proposed_by), "proposed_at": r.proposed_at, "decided_by": person(r.decided_by) if r.decided_by else None, "decided_at": r.decided_at,
            "note": r.decision_note, "impact": r.impact or {}}


def _audit(key: str, user, action: str, text: str):
    audit_service.log_event(case_id=f"POLICY-{key}", correlation_id=f"POLICY-{key}", stage_name="POLICY_CHANGE", actor_id=user.user_id, actor_role=role_of(user),
                            action_name=action, details=text, control_tags=["Rules and policy", "Four eyes"], amount=None, currency=None)


def listing() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        rows = db.query(V2PolicyChangeModel).order_by(V2PolicyChangeModel.proposed_at.desc()).all()
        out = []
        for p in PARAMS:
            mine = [r for r in rows if r.key == p["key"]]
            pend = next((r for r in mine if r.status == "PENDING"), None)
            out.append({**{k: v for k, v in p.items() if k != "default"}, "default": p["default"](), "value": get(p["key"]),
                        "pending": _row(pend) if pend else None, "history": [_row(r) for r in mine[:8]]})
        return {"params": out, "now": iso(now()), "rule": "A change needs a reason and a second Policy Owner's approval before it takes effect."}
    finally:
        db.close()


def propose(user, key: str, value: Any, reason: str) -> Dict[str, Any]:
    v = _clean(key, value)
    why = (reason or "").strip()
    if len(why) < 3:
        raise V2Error(422, "INVALID", "A reason is required.")
    imp = impact(key, v)
    db = SessionLocal()
    try:
        if db.query(V2PolicyChangeModel).filter(V2PolicyChangeModel.key == key, V2PolicyChangeModel.status == "PENDING").first():
            raise bad_state("This rule already has a change waiting for a decision.")
        r = V2PolicyChangeModel(id=new_id("PC"), key=key, value=v, prev_value=get(key), status="PENDING", reason=why[:500], proposed_by=user.user_id, proposed_at=iso(now()), impact=imp)
        db.add(r)
        db.commit()
        out = _row(r)
    finally:
        db.close()
    _audit(key, user, "POLICY_CHANGE_PROPOSED", f"{user.name} proposed {BY_KEY[key]['label']}: {_f(out['prev_value'])} to {_f(v)}. Reason: {why[:200]}. {imp['summary']}")
    return out


def _get(db, cid: str) -> V2PolicyChangeModel:
    r = db.query(V2PolicyChangeModel).filter(V2PolicyChangeModel.id == cid).first()
    if not r:
        raise not_found("Policy change")
    if r.status != "PENDING":
        raise bad_state(f"This change was already {r.status.lower()}.")
    return r


def approve(user, cid: str, note: Optional[str]) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        r = _get(db, cid)
        if r.proposed_by == user.user_id:
            raise V2Error(403, "SOD_VIOLATION", "A different Policy Owner must approve this change (four eyes).")
        for old in db.query(V2PolicyChangeModel).filter(V2PolicyChangeModel.key == r.key, V2PolicyChangeModel.status == "ACTIVE").all():
            old.status = "SUPERSEDED"
        r.status, r.decided_by, r.decided_at, r.decision_note, r.effective_from = "ACTIVE", user.user_id, iso(now()), (note or "")[:300], iso(now())
        db.commit()
        out, key, val, prev = _row(r), r.key, r.value, r.prev_value
    finally:
        db.close()
    reset_cache()
    _audit(key, user, "POLICY_CHANGE_APPROVED", f"{user.name} approved {BY_KEY[key]['label']}: {_f(prev)} to {_f(val)}. In force now.")
    return out


def _close(user, cid: str, status: str, note: Optional[str], action: str, verb: str) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        r = _get(db, cid)
        if status == "WITHDRAWN" and r.proposed_by != user.user_id:
            raise V2Error(403, "FORBIDDEN", "Only the person who proposed a change can withdraw it.")
        if status == "REJECTED" and r.proposed_by == user.user_id:
            raise V2Error(403, "SOD_VIOLATION", "A different Policy Owner decides on this change. Use withdraw instead.")
        r.status, r.decided_by, r.decided_at, r.decision_note = status, user.user_id, iso(now()), (note or "")[:300]
        db.commit()
        out, key = _row(r), r.key
    finally:
        db.close()
    _audit(key, user, action, f"{user.name} {verb} the change to {BY_KEY[key]['label']}. The value in force is unchanged.")
    return out


def reject(user, cid: str, note: Optional[str]) -> Dict[str, Any]:
    return _close(user, cid, "REJECTED", note, "POLICY_CHANGE_REJECTED", "rejected")


def withdraw(user, cid: str, note: Optional[str]) -> Dict[str, Any]:
    return _close(user, cid, "WITHDRAWN", note, "POLICY_CHANGE_WITHDRAWN", "withdrew")
