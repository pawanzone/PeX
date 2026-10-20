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
from app.core.tokenization import token_vault
from app.services.v2 import ext as xt

REVEAL_MINUTES = 10
MIN_REASON = 10
_ID = re.compile(r"PEX-[A-Z]+-\d+")


def enabled() -> bool:
    return bool(getattr(settings, "PII_MASKING", True))


def _pairs(case: Dict[str, Any]) -> List[Tuple[str, str]]:
    """(raw text as it may appear, token) for one case, longest first."""
    from app.services.v2 import logic as lg
    ext = lg.ext_of(case)
    out: Dict[str, str] = {}

    def add(raw: Any, kind: str):
        if not isinstance(raw, str):
            return
        r = raw.strip()
        if len(r) < 5:
            return
        tok = token_vault.tokenize(r, kind)
        out[r] = tok
        if kind in ("IBAN", "ACC"):
            c = xt.iban_compact(r)
            out[c] = tok
            out[xt.iban_group(c)] = tok

    for k in ("debtor_party", "creditor_party"):
        add((case.get(k) or {}).get("party_name"), "PARTY")
    for k in ("debtor_account", "creditor_account"):
        a = case.get(k) or {}
        add(a.get("iban"), "IBAN")
        add(a.get("account_number"), "ACC")
    add(ext.get("counterparty"), "PARTY")
    add(ext.get("debtor"), "PARTY")
    ch = ext.get("change") or {}
    for side in ("original", "proposed"):
        v = (ch.get(side) or {}).get("value")
        if isinstance(v, str) and xt.looks_like_iban(v):
            add(v, "IBAN")
    return sorted(out.items(), key=lambda kv: -len(kv[0]))


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
    from app.services.v2.core import has_perm
    g = active_reveal(ext, getattr(user, "user_id", None))
    return {"masking": enabled(), "protected": enabled() and not g, "can_reveal": enabled() and has_perm(user, "pii.reveal"),
            "revealed_until": g.get("expires_at") if g else None, "reveal_minutes": REVEAL_MINUTES,
            "min_reason_length": MIN_REASON,
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


def mask_payload(payload: Any, viewer_id: Optional[str], path_ids: Optional[List[str]] = None) -> Any:
    if not enabled():
        return payload
    from app.services.data_loader import repo
    from app.services.v2 import logic as lg
    ids: set = set(path_ids or [])
    _case_ids(payload, ids)
    pairs: List[Tuple[str, str]] = []
    for cid in ids:
        case = repo.get_case(cid)
        if not case:
            continue
        if active_reveal(lg.ext_of(case), viewer_id):
            continue
        pairs.extend(_pairs(case))
    if not pairs:
        return payload
    pairs.sort(key=lambda kv: -len(kv[0]))
    return _walk(payload, pairs, [False])
