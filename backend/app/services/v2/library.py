"""Profile and control library (Admin, read only). Generated from the profile packs and the readable definitions file
(app/profile_packs/definitions/controls.json); evidence meaning comes from the semantic layer. Nothing here is typed twice."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from app.profile_packs import registry
from app.schemas.policy_contract import STPPolicyConfig
from app.services.v2 import semantic_layer as sl
from app.services.v2.core import not_found

DEFS_PATH = Path(registry.__file__).resolve().parent / "definitions" / "controls.json"
VALIDATION = "Pending expert validation"


@lru_cache(maxsize=1)
def defs() -> Dict[str, Any]:
    return json.loads(DEFS_PATH.read_text(encoding="utf-8"))


def _packs():
    return {c: registry.get_pack(c) for c in sorted(registry.load_packs())}


def _applies(ctl: Dict[str, Any], p) -> bool:
    a = ctl["applies_to"]
    return a == "all" or (a == "repair" and p.outcome.value == "REPAIR") or (a == "decision" and p.decision is not None)


def _controls_for(p) -> List[Dict[str, Any]]:
    return [{"id": c["id"], "name": c["name"], "kind": c["kind"], "configurable": c["configurable"]} for c in defs()["controls"] if _applies(c, p)]


def library() -> Dict[str, Any]:
    d = defs()
    rows = []
    for code, p in _packs().items():
        fam = code.split("-")[0]
        rows.append({"code": code, "name": p.name, "family": fam, "family_name": d["families"][fam], "outcome": p.outcome.value, "stp": p.stp.value,
                     "approval": p.approval.when_not_stp, "authority_domain": p.authority_domain, "action": p.action, "resolver": p.resolver,
                     "evidence_mandatory": len(p.evidence.mandatory_types), "evidence_total": len(p.evidence.required),
                     "decision_options": len(p.decision.options) if p.decision else 0, "version": p.version, "validation_status": VALIDATION})
    count = lambda k: {v: sum(1 for r in rows if r[k] == v) for v in sorted({r[k] for r in rows})}
    return {"profiles": rows, "summary": {"profiles": len(rows), "by_outcome": count("outcome"), "by_stp": count("stp"), "by_family": count("family"), "by_approval": count("approval")},
            "families": d["families"], "note": d["note"]}


def profile(code: str) -> Dict[str, Any]:
    packs = _packs()
    if code not in packs:
        raise not_found("Profile not found.")
    p, d = packs[code], defs()
    cat = {r["type"]: r for r in sl.evidence_catalogue()}
    ev = []
    for e in p.evidence.required:
        c = cat.get(e.type, {})
        ev.append({"type": e.type, "tier": e.tier, "tier_meaning": d["evidence_tiers"][str(e.tier)], "mandatory": e.mandatory, "proves": c.get("proves", ""),
                   "source_system": c.get("source_system", ""), "category": c.get("category", ""), "data_class": c.get("data_class", "")})
    dec = None
    if p.decision:
        dec = {"target_field": p.decision.target_field, "reviewer_role": p.decision.reviewer_role,
               "options": [{"option": o, "effect": p.decision.effects[o].value, "effect_meaning": d["effects"][p.decision.effects[o].value]} for o in p.decision.options]}
    fam = code.split("-")[0]
    return {"code": code, "name": p.name, "family": fam, "family_name": d["families"][fam], "version": p.version, "outcome": p.outcome.value,
            "outcome_meaning": d["outcomes"][p.outcome.value], "stp": p.stp.value, "stp_meaning": d["stp_rules"][p.stp.value], "approval": p.approval.when_not_stp,
            "approval_meaning": d["approval_paths"][p.approval.when_not_stp], "authority_domain": p.authority_domain,
            "authority_meaning": d["authority_domains"][p.authority_domain], "action": p.action, "resolver": p.resolver, "checks": list(p.checks),
            "min_confidence": p.evidence.min_confidence, "evidence": ev, "decision": dec, "controls": _controls_for(p), "validation_status": VALIDATION,
            "confidence_note": "AI confidence is shown to people but is not a release condition (CTL-02)." if p.evidence.min_confidence is not None else ""}


def bank_settings() -> List[Dict[str, Any]]:
    from app.config import settings
    from app.services.v2 import policy as po
    cfg = STPPolicyConfig()
    rows = [
        {"key": "max_stp_amount", "label": "Bank policy amount cap (predicate P_bank)", "default": cfg.max_stp_amount, "source": "STPPolicyConfig default", "configurable": True,
         "note": "Cap used by the P_bank predicate. This default differs from the zero-touch limit setting below. They are separate settings, so confirm with the bank which limits apply in its set-up."},
        {"key": "dual_auth_threshold", "label": "Dual authorisation from (predicate P_bank)", "default": cfg.dual_auth_threshold, "source": "STPPolicyConfig default", "configurable": True,
         "note": "At or above this amount a case needs two approvers and cannot go straight through."},
        {"key": "allowed_corridors", "label": "Currencies allowed for straight-through", "default": list(cfg.allowed_corridors), "source": "STPPolicyConfig default", "configurable": True,
         "note": "A payment in another currency is routed to a person."},
        {"key": "auto_stp_enabled", "label": "Straight-through switched on", "default": cfg.auto_stp_enabled, "source": "STPPolicyConfig default", "configurable": True,
         "note": "A bank can switch straight-through off entirely."},
        {"key": "release_mode", "label": "Release mode", "default": po.BY_KEY["release_mode"]["default"](), "value": po.get("release_mode"), "source": "Bank policy (versioned changes)", "configurable": True,
         "note": "Who releases cases that pass all 8 rules: auto-release, approve all in one click, or review each. It never loosens a rule."},
        {"key": "zero_touch_limit", "label": "Zero-touch release limit", "default": po.BY_KEY["zero_touch_limit"]["default"](), "value": po.get("zero_touch_limit"), "source": "Bank policy (versioned changes); default from PEX_STP_MAX_AMOUNT", "configurable": True,
         "note": "In auto-release mode, eligible cases up to this amount are marked for release with no person. There is no trigger yet, so nothing is released without a person. Above it, an eligible case goes to one-click batch approval."},
        {"key": "batch_limit", "label": "One-click batch approval limit", "default": po.BY_KEY["batch_limit"]["default"](), "value": po.get("batch_limit"), "source": "Bank policy (versioned changes)", "configurable": True,
         "note": "Validated micro-repairs under this amount can be approved together on the Batches screen."},
        {"key": "sanctions_mode", "label": "Sanctions mode", "default": cfg.sanctions_mode, "source": "STPPolicyConfig default", "configurable": True,
         "note": "ZERO_TOLERANCE: any screening hit stops straight-through."},
    ]
    for r in rows:
        r.setdefault("value", r["default"])
    return rows


def controls() -> Dict[str, Any]:
    d, packs = defs(), _packs()
    ctl = []
    for c in d["controls"]:
        profs = [code for code, p in packs.items() if _applies(c, p)]
        row = {**c, "profiles": profs, "profile_count": len(profs)}
        if c["id"] == "CTL-03":
            row["breakdown"] = {k: sum(1 for p in packs.values() if p.stp.value == k) for k in d["stp_rules"]}
        if c["id"] == "CTL-09":
            row["breakdown"] = {k: sum(1 for p in packs.values() if p.approval.when_not_stp == k) for k in d["approval_paths"]}
        ctl.append(row)
    can_stp = sorted(code for code, p in packs.items() if p.stp.value != "NEVER")
    preds = [{**x, "profiles": can_stp, "profile_count": len(can_stp)} for x in d["stp_predicates"]]
    return {"stp_predicates": preds, "controls": ctl, "bank_settings": bank_settings(), "stp_rules": d["stp_rules"], "note": d["note"],
            "formula": "STP eligible = E_suff AND R_det AND R_uniq AND V_det AND V_auth AND P_bank AND C_comp AND X_pre"}
