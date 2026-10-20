"""PII protection for the v2 API: tokenised by default, audited reveal for authorised roles.

Rule: nothing leaves the API in plain text unless the viewer holds an active, audited reveal on that case.
Names, IBANs and account numbers are replaced by the vault's TOK-* surrogates (same tokens the AI context uses).
Real values stay inside the trust boundary and are only returned (a) to an authorised person who asks to reveal, with a reason,
for a short window, and (b) to the bank at hand-off inside the single outbound gate.
Admin cannot reveal (separation of duties).
"""
from __future__ import annotations

import json
import re
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.services.v2 import classification as cl
from app.services.v2 import ext as xt
from app.services.v2 import zone

REVEAL_MINUTES = 10


def reveal_minutes() -> int:
    from app.services.v2 import policy
    return int(policy.get("reveal_minutes"))
MIN_REASON = 10
_ID = re.compile(r"PEX-[A-Z]+-\d+")


def enabled() -> bool:
    return bool(getattr(settings, "PII_MASKING", True))


def _pairs(case: Dict[str, Any]) -> List[Tuple[str, str]]:
    return zone.case_pairs(case)


def active_reveal(ext: Dict[str, Any], user_id: Optional[str]) -> Optional[Dict[str, Any]]:
    from app.services.v2.core import now, parse_ts
    if not user_id:
        return None
    t = now()
    for g in ext.get("pii_reveals") or []:
        exp = parse_ts(g.get("expires_at"))
        if g.get("user_id") == user_id and exp and exp > t:
            return g
    return None


def page_block(case: Dict[str, Any], ext: Dict[str, Any], user) -> Dict[str, Any]:
    from app.services.v2.core import has_perm, role_of
    g = active_reveal(ext, getattr(user, "user_id", None))
    role = role_of(user) if user is not None else ""
    can = enabled() and has_perm(user, "pii.reveal")
    classes = sorted(cl.revealable_classes(role)) if can else []
    return {"masking": enabled(), "protected": enabled() and not g, "can_reveal": can,
            "revealed_until": g.get("expires_at") if g else None, "reveal_minutes": reveal_minutes(),
            "min_reason_length": MIN_REASON,
            "reveal_classes": [{"class": c, "name": cl.CLASSES[c]} for c in classes],
            "restricted_note": ("Screening details (C3) can be revealed by the Compliance role only." if can and "C3" not in classes else None),
            "ai_view_endpoint": f"/api/v2/cases/{case['case_id']}/ai-view",
            "reveal_endpoint": f"/api/v2/cases/{case['case_id']}/pii/reveal", "hide_endpoint": f"/api/v2/cases/{case['case_id']}/pii/hide"}


def _walk(o: Any, pairs: List[Tuple[str, str]], hit: List[bool]) -> Any:
    if isinstance(o, str):
        s = o
        for raw, tok in pairs:
            if raw in s:
                s = s.replace(raw, tok)
        if s != o:
            hit[0] = True
        return s
    if isinstance(o, list):
        return [_walk(x, pairs, hit) for x in o]
    if isinstance(o, dict):
        local = [False]
        res = {k: _walk(v, pairs, local) for k, v in o.items()}
        if local[0]:
            hit[0] = True
            if "highlight" in res:          # character positions no longer line up with a token
                res["highlight"] = None
        return res
    return o


def _case_ids(o: Any, acc: set):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "case_id" and isinstance(v, str):
                acc.add(v)
            else:
                _case_ids(v, acc)
    elif isinstance(o, list):
        for x in o:
            _case_ids(x, acc)


def mask_payload(payload: Any, viewer_id: Optional[str], path_ids: Optional[List[str]] = None, role: str = "") -> Any:
    """Everything leaving the API. Stored evidence already holds tokens; this also covers values that live in the case record.
    A viewer with an active reveal on every case in the payload gets the real values back for the classes their role may see."""
    if not enabled():
        return payload
    from app.services.data_loader import repo
    from app.services.v2 import logic as lg
    ids: set = set(path_ids or [])
    _case_ids(payload, ids)
    pairs: List[Tuple[str, str]] = []
    revealed_all = bool(ids)
    for cid in ids:
        case = repo.get_case(cid)
        if not case:
            continue
        if active_reveal(lg.ext_of(case), viewer_id):
            continue
        revealed_all = False
        pairs.extend(_pairs(case))
    if revealed_all:
        return zone.unseal_obj(payload, role)          # tokens back to real values, class by class
    if not pairs:
        return payload
    pairs.sort(key=lambda kv: -len(kv[0]))
    return _walk(payload, pairs, [False])
