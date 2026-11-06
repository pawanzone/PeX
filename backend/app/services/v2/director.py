"""Operations director view: the questions an ops director asks first, answered from data PeX already holds. Read only.

How much of the queue passes the 8 rules, what stops the rest, which rules are in force and who changed them, how far the bank's experts have
validated the content, and what the shadow comparison shows. Nothing here changes a case, a rule or a score.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.config import settings
from app.services.v2 import dashboard as dash
from app.services.v2 import library, policy, review, shadow, stp
from app.services.v2 import logic as lg
from app.services.v2.core import iso, now, profile_code
from app.services.v2.rows import all_cases

MODE_MEANING = {
    "SHADOW": "PeX recommends and records what it would have done. Nothing is sent to the bank.",
    "ASSISTED": "PeX prepares each instruction and a named person approves it before it is handed to the bank.",
    "LIVE": "Approved instructions are handed to the bank's systems, under the rules below.",
}
BUCKETS = {
    "pass_within_zero_touch": ("Passes all 8 rules, within the zero-touch limit", "These could be released without a person looking at each one, if the bank chooses auto-release. Today a person still approves."),
    "pass_needs_approval": ("Passes all 8 rules, above the zero-touch limit", "Eligible for batch approval by a person; too large to be considered for zero-touch release."),
    "no_proposal": ("No fix proposed", "PeX could not prepare a fix, or the case is a decision or investigation type. A person decides."),
}
BLOCKED_LABEL = {"COMPLIANCE_HOLD": "Compliance hold", "EVIDENCE_CONFLICT": "Evidence conflict", "EVIDENCE_MISSING": "Evidence incomplete", "VALIDATION_FAILED": "Validation failed",
                 "HARD_BLOCK": "Never straight-through", "ABOVE_LIMIT": "Above the bank's limit"}
RULE_NAME = {"C_comp": "Compliance gate passed", "E_suff": "Evidence is sufficient", "V_det": "Deterministic validation passed", "P_bank": "Bank policy allows", "Profile ceiling": "Exception type is never straight-through"}
SHOWN_RULES = ["dual_auth_amount", "batch_limit", "zero_touch_limit", "release_mode", "confidence_threshold"]


def _family(case: Dict[str, Any]) -> str:
    return profile_code(case.get("profile")).split("-")[0]


def _automation() -> Dict[str, Any]:
    zt = stp.zero_touch_limit()
    counts: Dict[str, int] = {"pass_within_zero_touch": 0, "pass_needs_approval": 0, "no_proposal": 0}
    blocked: Dict[str, int] = {}
    fam: Dict[str, Dict[str, int]] = {}
    open_n = 0
    for c in all_cases():
        if lg.status_of(c) in dash.FINAL:
            continue
        open_n += 1
        f = fam.setdefault(_family(c), {"open": 0, "pass_rules": 0, "blocked": 0, "no_proposal": 0})
        f["open"] += 1
        if not lg.ext_of(c).get("change"):
            counts["no_proposal"] += 1
            f["no_proposal"] += 1
            continue
        ev = stp.evaluate(c)
        if ev["eligible"]:
            counts["pass_within_zero_touch" if float(c.get("amount") or 0) <= zt else "pass_needs_approval"] += 1
            f["pass_rules"] += 1
        else:
            blocked[ev["code"]] = blocked.get(ev["code"], 0) + 1
            f["blocked"] += 1
    buckets = [{"key": k, "label": BUCKETS[k][0], "meaning": BUCKETS[k][1], "count": counts[k], "rule": None} for k in ("pass_within_zero_touch", "pass_needs_approval")]
    for code, n in sorted(blocked.items(), key=lambda kv: -kv[1]):
        rule = stp.RULE_OF.get(code)
        buckets.append({"key": f"blocked_{code.lower()}", "label": f"Stopped: {BLOCKED_LABEL.get(code, code)}", "meaning": f"Failed the rule: {RULE_NAME.get(rule, rule)}. A person decides.", "count": n, "rule": rule})
    buckets.append({"key": "no_proposal", "label": BUCKETS["no_proposal"][0], "meaning": BUCKETS["no_proposal"][1], "count": counts["no_proposal"], "rule": None})
    names = library.defs()["families"]
    by_family = [{"family": k, "name": names.get(k, k), **v} for k, v in sorted(fam.items())]
    mode = stp.mode_block()
    opts = {o["value"]: o["label"] for o in next(p for p in policy.PARAMS if p["key"] == "release_mode")["options"]}
    return {"open": open_n, "buckets": buckets, "blocked_total": sum(blocked.values()), "by_family": by_family, "zero_touch_limit": zt,
            "release_mode": {"value": mode["value"], "label": opts.get(mode["value"], mode["value"]), "note": mode["note"]}}


def _control() -> Dict[str, Any]:
    lst = policy.listing()["params"]
    rules, recent, pending = [], [], 0
    for p in lst:
        if p["pending"]:
            pending += 1
        if p["key"] in SHOWN_RULES:
            rules.append({"key": p["key"], "label": p["label"], "value": p["value"], "default": p["default"], "changed": p["value"] != p["default"], "pending": bool(p["pending"])})
        for h in p["history"]:
            if h["status"] in ("ACTIVE", "SUPERSEDED"):  # approved changes: in force now, or replaced by a later one
                recent.append({"key": p["key"], "label": p["label"], "value": h["value"], "prev_value": h["prev_value"], "reason": h["reason"], "proposed_by": h["proposed_by"],
                               "decided_by": h["decided_by"], "decided_at": h["decided_at"]})
    recent.sort(key=lambda r: r["decided_at"] or "", reverse=True)
    profiles = library.library()["profiles"]
    rv = review.summary()
    return {"operation_mode": settings.PEX_OPERATION_MODE, "operation_mode_meaning": MODE_MEANING.get(settings.PEX_OPERATION_MODE, ""),
            "rules": rules, "recent_changes": recent[:5], "pending_changes": pending,
            "never_straight_through": sum(1 for p in profiles if p["stp"] == "NEVER"), "profiles_total": len(profiles),
            "sme_review": {"profiles_signed_off": rv["profiles"]["SIGNED_OFF"], "profiles_total": rv["profiles"]["total"], "controls_signed_off": rv["controls"]["SIGNED_OFF"],
                           "controls_total": rv["controls"]["total"], "open_comments": rv["open_comments"]}}


def _proof() -> Dict[str, Any]:
    s = shadow.scorecard()
    r = s["release"]
    return {"loaded": s["compared"] > 0, "compared": s["compared"], "would_release": r["would_release"], "released_correctly": r["released_correctly"],
            "released_wrongly": r["released_wrongly"]["count"], "sent_to_person": r["sent_to_person"], "safe_release_rate": s["rates"]["safe_release_rate"],
            "agree_rate": s["rates"]["agree_rate"], "minutes_on_released": s["time"]["minutes_on_released"]}


def view() -> Dict[str, Any]:
    a, c, p = _automation(), _control(), _proof()
    by = {b["key"]: b["count"] for b in a["buckets"]}
    passing = by["pass_within_zero_touch"] + by["pass_needs_approval"]
    head = [f"{a['open']} exceptions are open. {passing} pass all 8 rules, {a['blocked_total']} are stopped by a named rule, and {by['no_proposal']} have no proposed fix and go to a person.",
            f"PeX is in {c['operation_mode'].title()} mode: {c['operation_mode_meaning']}",
            f"Release mode is \"{a['release_mode']['label']}\", with a zero-touch limit of {a['zero_touch_limit']:,.0f}."]
    sm = c["sme_review"]
    head.append(f"The bank's experts have signed off {sm['profiles_signed_off']} of {sm['profiles_total']} exception types and {sm['controls_signed_off']} of {sm['controls_total']} controls.")
    head.append(f"Shadow comparison: {p['compared']} cases compared, {p['released_wrongly']} PeX would have released wrongly." if p["loaded"] else "Shadow comparison: no analyst results loaded yet, so there is no proof figure.")
    return {"as_of": iso(now()), "headline": head, "automation": a, "control": c, "proof": p,
            "data_note": "Demo data: synthetic cases, simulated bank and directory connections. The structure is real; the numbers are not a bank's."}
