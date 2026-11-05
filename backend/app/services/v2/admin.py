"""UI v2 admin: simulated integrations, two-administrator mode changes, roles, policies, exception types."""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.security import DEMO_PERSONAS
from app.db.models import V2IntegrationModel, V2ModeChangeModel, AuditEventModel
from app.db.session import SessionLocal
from app.services.audit_service import audit_service
from app.services.data_loader import repo
from app.services.outbound_port import operation_mode
from app.services.v2 import logic as lg
from app.services.v2.core import (
    V2Error, bad_state, invalid, not_found, now, iso, parse_ts, require, role_of, new_id, ROLE_LABELS, PERMISSIONS, SHORT_LABELS,
    profile_code, profile_spec, HARD_BLOCK_STP, _maps,
)

MODES = ("SHADOW", "ASSISTED", "LIVE")
MODE_TEXT = {"SHADOW": "Read only. PeX reads and recommends. Nothing is sent to the bank system.",
             "ASSISTED": "PeX prepares each action. A named person approves every handoff. The bank executes.",
             "LIVE": "Approved policy may hand off without a person for each item. The bank still executes and confirms."}

INTEGRATIONS = [
    {"id": "payment_engine", "name": "Payment engine", "purpose": "Exception events and status", "type": "Payment engine", "direction": "Read and handoff", "mode": "ASSISTED", "write": True},
    {"id": "message_gateway", "name": "Message network gateway", "purpose": "Status tracking", "type": "Message network gateway", "direction": "Read", "mode": "SHADOW", "write": False},
    {"id": "sanctions_screening", "name": "Sanctions screening system", "purpose": "Alerts and dispositions", "type": "Screening system", "direction": "Read and disposition", "mode": "ASSISTED", "write": True},
    {"id": "core_ledger", "name": "Core ledger", "purpose": "Balances and postings", "type": "Core ledger", "direction": "Read", "mode": "SHADOW", "write": False,
     "health": "degraded", "health_note": "Slow responses", "queue": 3},
    {"id": "party_directory", "name": "Party directory", "purpose": "Standing instructions", "type": "Party directory", "direction": "Read", "mode": "LIVE", "write": False},
    {"id": "bic_iban_directory", "name": "BIC and IBAN directory", "purpose": "Reference data", "type": "Reference data", "direction": "Read", "mode": "LIVE", "write": False},
]
_BY_ID = {i["id"]: i for i in INTEGRATIONS}


def ensure_integrations(db=None):
    own = db is None
    db = db or SessionLocal()
    try:
        have = {r.id for r in db.query(V2IntegrationModel.id).all()}
        t = now()
        for k, spec in enumerate(INTEGRATIONS):
            if spec["id"] in have:
                continue
            db.add(V2IntegrationModel(id=spec["id"], mode=spec["mode"], health=spec.get("health", "healthy"), health_note=spec.get("health_note"),
                                      queue=spec.get("queue", 0), last_event_at=iso(t - timedelta(seconds=40 + 70 * k))))
        db.commit()
    finally:
        if own:
            db.close()


def _handoffs(hours: int = 24) -> List[Dict[str, Any]]:
    cut = now() - timedelta(hours=hours)
    out = []
    for c in repo._case_cache.values():
        h = parse_ts(c.get("handed_off_at"))
        if h and h >= cut:
            st = lg.status_of(c)
            ack = bool(c.get("bank_ack_reference")) or st in ("EXECUTED_CONFIRMED", "SETTLED") or str(c.get("dispatch_status", "")).startswith("BANK_")
            out.append({"case_id": c["case_id"], "sent_at": iso(h), "status": st, "acknowledged": ack, "bank_reference": c.get("bank_ack_reference"),
                        "amount": c.get("amount"), "currency": c.get("currency"), "mode": operation_mode()})
    out.sort(key=lambda r: r["sent_at"], reverse=True)
    return out


def _pending_by_integration(db) -> Dict[str, Dict[str, Any]]:
    out = {}
    for r in db.query(V2ModeChangeModel).filter(V2ModeChangeModel.state == "PENDING_SECOND_ADMIN").all():
        out[r.integration_id] = _mc(r)
    return out


def _mc(r: V2ModeChangeModel) -> Dict[str, Any]:
    from app.services.v2.core import person
    return {"id": r.id, "integration_id": r.integration_id, "from_mode": r.from_mode, "to_mode": r.to_mode, "reason": r.reason, "state": r.state,
            "requested_by": person(r.requested_by), "requested_at": r.requested_at, "decided_by": person(r.decided_by) if r.decided_by else None, "decided_at": r.decided_at}


def integrations() -> Dict[str, Any]:
    ensure_integrations()
    hand = _handoffs(24)
    awaiting_n = sum(1 for h in hand if not h["acknowledged"])
    open_holds = sum(1 for c in repo._case_cache.values() if lg.is_compliance(c) and lg.status_of(c) not in lg.DONE)
    db = SessionLocal()
    try:
        rows = {r.id: r for r in db.query(V2IntegrationModel).all()}
        pend = _pending_by_integration(db)
    finally:
        db.close()
    items = []
    live_w = 0
    live_any = 0
    for spec in INTEGRATIONS:
        r = rows[spec["id"]]
        mode = operation_mode() if spec["id"] == "payment_engine" else r.mode
        queue = {"payment_engine": awaiting_n, "sanctions_screening": open_holds}.get(spec["id"], r.queue)
        if mode == "LIVE":
            live_any += 1
            if spec["write"]:
                live_w += 1
        items.append({"id": spec["id"], "name": spec["name"], "purpose": spec["purpose"], "type": spec["type"], "direction": spec["direction"], "mode": mode,
                      "health": r.health, "health_note": r.health_note, "last_event": r.last_event_at, "queue": queue, "simulated": True,
                      "pending_mode_change": pend.get(spec["id"]),
                      "action": {"label": "View issue" if r.health != "healthy" else "View", "kind": "issue" if r.health != "healthy" else "view"}})
    healthy = sum(1 for i in items if i["health"] == "healthy")
    return {"simulated": True, "banner": "All integrations are simulated in this build. No real bank system is contacted.",
            "tiles": {"connected": len(items), "healthy": healthy, "degraded": len(items) - healthy,
                      "live_writeback_enabled": {"count": live_w, "of": len(items)}, "live_mode": {"count": live_any, "of": len(items)}},
            "items": items,
            "modes": [{"mode": m, "text": MODE_TEXT[m]} for m in MODES],
            "never_executes": "PeX never executes payments. The bank executes and confirms.",
            "handoffs_24h": {"sent": len(hand), "acknowledged": len(hand) - awaiting_n, "awaiting": awaiting_n, "source": "computed from real handoffs in the last 24 hours"}}


def handoffs(hours: int) -> Dict[str, Any]:
    h = _handoffs(max(1, min(int(hours or 24), 720)))
    return {"hours": hours, "total": len(h), "items": h[:500]}


# ---- two-administrator mode change --------------------------------------------------------------
def request_mode_change(user, integration_id: Optional[str], to_mode: Optional[str], reason: Optional[str]) -> Dict[str, Any]:
    require(user, "admin.mode_change")
    if integration_id not in _BY_ID:
        raise invalid(f"Unknown integration '{integration_id}'", "integration_id")
    tm = (to_mode or "").upper()
    if tm not in MODES:
        raise invalid("to_mode must be SHADOW, ASSISTED or LIVE", "to_mode")
    why = (reason or "").strip()
    if not why:
        raise invalid("A reason is required", "reason")
    ensure_integrations()
    cur = operation_mode() if integration_id == "payment_engine" else None
    db = SessionLocal()
    try:
        row = db.query(V2IntegrationModel).filter(V2IntegrationModel.id == integration_id).first()
        cur = cur or row.mode
        if tm == cur:
            raise bad_state(f"{_BY_ID[integration_id]['name']} is already in {tm} mode.")
        if tm == "LIVE" and not _BY_ID[integration_id]["write"] and False:
            pass
        if db.query(V2ModeChangeModel).filter(V2ModeChangeModel.integration_id == integration_id, V2ModeChangeModel.state == "PENDING_SECOND_ADMIN").first():
            raise V2Error(409, "CONFLICT", "A mode change for this integration is already waiting for a second administrator.")
        r = V2ModeChangeModel(id=new_id("MC"), integration_id=integration_id, from_mode=cur, to_mode=tm, reason=why, state="PENDING_SECOND_ADMIN",
                              requested_by=user.user_id, requested_at=iso(now()))
        db.add(r)
        db.commit()
        out = _mc(r)
    finally:
        db.close()
    _audit(user, "MODE_CHANGE_REQUESTED", f"{user.name} requested {integration_id} mode {cur} -> {tm}. Waiting for a second administrator.", before=cur, after=tm, reason=why)
    out["message"] = "Mode change requested. A second administrator must approve it before it takes effect."
    return out


def list_mode_changes() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        rows = db.query(V2ModeChangeModel).order_by(V2ModeChangeModel.requested_at.desc()).limit(100).all()
        return {"items": [_mc(r) for r in rows]}
    finally:
        db.close()


def _decide(user, mc_id: str, approve: bool) -> Dict[str, Any]:
    require(user, "admin.mode_approve")
    db = SessionLocal()
    try:
        r = db.query(V2ModeChangeModel).filter(V2ModeChangeModel.id == mc_id).first()
        if not r:
            raise not_found("Mode change request")
        if r.state != "PENDING_SECOND_ADMIN":
            raise bad_state(f"This request is already {r.state.lower().replace('_', ' ')}.")
        if approve and r.requested_by == user.user_id:
            raise V2Error(403, "SECOND_ADMIN_REQUIRED", "A different administrator must approve this change. You requested it.")
        r.state = "APPROVED" if approve else ("REJECTED" if r.requested_by != user.user_id else "WITHDRAWN")
        r.decided_by = user.user_id
        r.decided_at = iso(now())
        if approve:
            row = db.query(V2IntegrationModel).filter(V2IntegrationModel.id == r.integration_id).first()
            row.mode = r.to_mode
            row.last_event_at = iso(now())
            if r.integration_id == "payment_engine":
                settings.PEX_OPERATION_MODE = r.to_mode
        db.commit()
        out = _mc(r)
        frm, to, integ, state = r.from_mode, r.to_mode, r.integration_id, r.state
    finally:
        db.close()
    _audit(user, "MODE_CHANGE_APPROVED" if approve else "MODE_CHANGE_REJECTED",
           f"{user.name} {state.lower()} the {integ} mode change {frm} -> {to}." + (" The change is now in effect." if approve else ""),
           before=frm, after=to if approve else frm, sod="Passed (second administrator)" if approve else None)
    out["message"] = "Mode change approved and applied." if approve else "Mode change request closed without applying."
    return out


def approve_mode_change(user, mc_id: str):
    return _decide(user, mc_id, True)


def reject_mode_change(user, mc_id: str):
    return _decide(user, mc_id, False)


def _audit(user, action: str, text: str, before=None, after=None, reason=None, sod=None):
    import json
    from app.services.v2.actions import META_MARK
    meta = {k: v for k, v in {"before": before, "after": after, "reason": reason, "sod": sod, "policy_version": "Mode governance v1.0"}.items() if v}
    audit_service.log_event(case_id="SYSTEM", correlation_id="MODE-GOVERNANCE", stage_name="ADMIN_CONFIG", actor_id=user.user_id, actor_role=role_of(user),
                            action_name=action, details=text + META_MARK + json.dumps(meta), control_tags=["Two-administrator rule", "Configuration change"])


# ---- roles / policies / exception types ----------------------------------------------------------
CAN = {
    "OPERATOR": ["Work assigned cases", "Submit repairs for approval", "Request information", "Escalate", "Check status (simulated)"],
    "SUPERVISOR": ["Everything a Maker can do", "Reassign cases", "View team workload", "Read audit"],
    "OPERATIONS_APPROVER": ["Approve, return or reject repairs up to their limit", "Approve low-risk repairs in a batch"],
    "COMPLIANCE_APPROVER": ["Decide on compliance holds", "Confirm a match (needs second reviewer)", "Read audit"],
    "RISK_APPROVER": ["Tier-2 approval for dual-authorisation amounts", "Senior compliance decisions"],
    "AUDIT_RISK": ["Read audit events and reports", "Export audit data"],
    "ADMIN": ["View integrations and policies", "Request and approve mode changes (two administrators)"],
}


def roles() -> Dict[str, Any]:
    users: Dict[str, List[Dict[str, Any]]] = {}
    limits: Dict[str, float] = {}
    for p in DEMO_PERSONAS.values():
        r = role_of(p)
        users.setdefault(r, []).append({"user_id": p.user_id, "name": p.name, "title": p.title})
        limits[r] = max(limits.get(r, 0.0), float(p.max_approval_amount))
    order = ["OPERATOR", "SUPERVISOR", "OPERATIONS_APPROVER", "RISK_APPROVER", "COMPLIANCE_APPROVER", "AUDIT_RISK", "ADMIN"]
    out = [{"role": r, "label": ROLE_LABELS[r], "permissions": PERMISSIONS.get(r, []), "approval_limit": limits.get(r, 0.0), "users": users.get(r, [])} for r in order]
    matrix = [{"role": r, "label": ROLE_LABELS[r], "limit": limits.get(r, 0.0), "can": CAN[r],
               "cannot": ["Approve own work (separation of duties)"] if r in ("OPERATIONS_APPROVER", "RISK_APPROVER", "COMPLIANCE_APPROVER", "ADMIN") else ["Approve repairs"]} for r in order]
    return {"roles": out, "authority_matrix": matrix, "note": "Personas are demo identities. Production identity comes from the bank's identity provider."}


def policies() -> Dict[str, Any]:
    from app.services.v2.stp import limit_amount, policy_text
    thresholds = [
        {"key": "stp_limit", "label": "Autonomous STP limit", "value": __import__("app.services.v2.policy", fromlist=["x"]).get("zero_touch_limit"), "currency": "payment currency", "editable": False,
         "note": "Zero-touch release limit (Rules and policy: zero_touch_limit). Never applies to compliance, returns or high-value payments."},
        {"key": "batch_limit", "label": "One-click batch approval limit", "value": limit_amount(), "currency": "payment currency", "editable": False, "note": "Human approves; PEX_BATCH_APPROVAL_MAX."},
        {"key": "dual_auth_threshold", "label": "Dual authorisation from", "value": __import__("app.services.v2.policy", fromlist=["x"]).get("dual_auth_amount"), "currency": "payment currency", "editable": False, "note": "Two different approvers required."},
        {"key": "micro_repair_rule", "label": "Micro-repair rule", "value": policy_text(), "editable": False, "note": "Eligibility for the batch approval screen."},
        {"key": "operation_mode", "label": "Operation mode", "value": operation_mode(), "editable": False, "note": "Changed only through a two-administrator mode change."},
    ]
    return {"thresholds": thresholds, "rules": repo.get_policy_rules(), "rules_endpoint": "/api/rules"}


def exception_types() -> Dict[str, Any]:
    c2e, _ = _maps()
    from app.services.profile_engine import PROFILE_SPECS
    from app.services.v2.core import pack_mandatory_evidence
    counts: Dict[str, int] = {}
    for c in repo._case_cache.values():
        if lg.status_of(c) not in lg.DONE:
            k = profile_code(c.get("profile"))
            counts[k] = counts.get(k, 0) + 1
    items = []
    for code, enum in c2e.items():
        spec = PROFILE_SPECS.get(enum, {})
        dom = str(getattr(spec.get("domain"), "value", spec.get("domain")) or "")
        ok, note = True, None
        if code in HARD_BLOCK_STP:
            ok, note = False, "Hard-blocked: can never be released straight through."
        elif dom == "COMPLIANCE":
            ok, note = False, "Compliance exceptions always need a named compliance decision."
        elif dom == "SETTLEMENT_RETURNS":
            ok, note = False, "Returns and recalls need investigator review."
        items.append({"code": code, "label": SHORT_LABELS.get(enum.value, enum.value), "title": spec.get("title"), "domain": dom, "queue": spec.get("default_queue"),
                      "stp_permissible": ok, "stp_note": note, "mandatory_evidence": (pack_mandatory_evidence(code) if pack_mandatory_evidence(code) is not None else spec.get("mandatory_evidence", [])), "open_cases": counts.get(code, 0)})
    items.sort(key=lambda i: i["code"])
    return {"total": len(items), "items": items}
