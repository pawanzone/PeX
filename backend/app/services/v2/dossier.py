"""Evidence dossier: five steps for one evidence check, read from what the evidence zone already recorded.

1 System of record   2 Data sought   3 Data received   4 Governance rule   5 Latency and trace

Everything shown is a token or a derived fact. Revealing real values stays a separate, logged act on the case.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from app.services.v2 import classification as cl
from app.services.v2 import zone
from app.services.v2.evidence_model import SYSTEMS

# kind -> (system key, rule id, rule text, what it asks)
CATALOG: Dict[str, Dict[str, str]] = {
    "checksum": {"system": "ISO", "rule": "EV-CHK-01", "text": "An IBAN must pass the mod-97 structure check before any repair is proposed.",
                 "asked": "Is the account number well formed?"},
    "directory": {"system": "CUSTM", "rule": "EV-DIR-01", "text": "The customer and beneficiary master is the authoritative source. A different account in the master blocks auto-repair and needs a human decision.",
                  "asked": "Which account does the master hold for this beneficiary?"},
    "vop": {"system": "COPVOP", "rule": "EV-VOP-01", "text": "The account holder name returned by the bank must match the instruction (name similarity at or above the policy threshold), otherwise a human reviews.",
            "asked": "Does the account holder name match the payee on the instruction?"},
    "history": {"system": "ARCH", "rule": "EV-HIS-01", "text": "Earlier payments to the same account support a repair but never decide it alone.",
                "asked": "Have earlier payments to this beneficiary used this account?"},
    "invoice": {"system": "ERP", "rule": "EV-INV-01", "text": "The account on the supporting invoice must match the proposed account.",
                "asked": "Which account does the supporting invoice show?"},
    "screening": {"system": "LISTS", "rule": "EV-SCR-01", "text": "A possible sanctions match stops the repair and routes the case to Compliance. Details are Compliance-only.",
                  "asked": "Does the payee match any sanctions or watch list?"},
    "other": {"system": "EVENT", "rule": "EV-GEN-01", "text": "Evidence taken from the payment instruction itself is accepted as supplied and checked against other sources.",
              "asked": "What does the payment instruction say?"},
}
_NAMES = [("checksum", "checksum"), ("master directory", "directory"), ("account holder", "vop"), ("prior payments", "history"),
          ("invoice", "invoice"), ("sanction", "screening"), ("screening", "screening")]


def kind_of(row: Dict[str, Any]) -> str:
    n = str(row.get("check") or "").lower()
    for frag, k in _NAMES:
        if frag in n:
            return k
    return "other"


def _sys_name(key: str) -> str:
    if key in SYSTEMS:
        return SYSTEMS[key][1]
    return {"ISO": "Deterministic check (no outside system)", "COPVOP": "Verification of Payee / Confirmation of Payee scheme",
            "ERP": "Customer ERP / invoice store", "LISTS": "Sanctions and watch lists"}.get(key, key)


def _query(kind: str, case: Dict[str, Any]) -> Dict[str, Any]:
    party, iban = zone.tok(zone._party(case, "creditor"), "PARTY"), zone.tok(zone._iban(case), "IBAN")
    ref = zone.tok(case.get("uetr") or case.get("case_id"), "REF")
    return {"checksum": {"iban": iban}, "directory": {"name": party, "iban": iban}, "vop": {"name": party, "iban": iban},
            "history": {"iban": iban}, "invoice": {"reference": ref}, "screening": {"name": party}}.get(kind, {"reference": ref})


def _latency(rid: str, kind: str) -> int:
    h = int(hashlib.sha256(f"{rid}|{kind}".encode()).hexdigest()[:6], 16)
    return 8 if kind == "checksum" else 40 + h % 380          # simulated: deterministic so the screen is stable


def _verdict(status: str) -> str:
    if status in ("pass", "agree"):
        return "pass"
    if status in ("fail", "differs"):
        return "review" if status == "differs" else "fail"
    return "info"


def build(case: Dict[str, Any], rows: List[Dict[str, Any]], evidence_id: str) -> Optional[Dict[str, Any]]:
    ids = [r["id"] for r in rows]
    if evidence_id not in ids:
        return None
    i = ids.index(evidence_id)
    r = rows[i]
    kind = kind_of(r)
    cat = CATALOG[kind]
    mode = r.get("mode") or (zone.connector_mode(cat["system"]) if cat["system"] in zone.SIMULATED else "zone")
    q = _query(kind, case)
    raw = r.get("raw") or {}
    trace = hashlib.sha256(json.dumps(raw, sort_keys=True, default=str).encode()).hexdigest()
    fields = [{"label": f.get("label"), "token": f.get("token"), "class": f.get("class"), "class_name": cl.CLASSES.get(f.get("class"), "")} for f in (r.get("fields") or [])]
    status = r.get("status") or "info"
    verdict = _verdict(status)
    steps = [
        {"n": 1, "title": "System of record", "system": cat["system"], "system_name": _sys_name(cat["system"]), "mode": mode,
         "authority": r.get("authority") or "", "source": r.get("source") or "",
         "note": {"simulated": "Simulated connector returning ISO 20022-shaped data. Switches to the bank's real system when the bank connects it.",
                  "real": "Live bank connector.", "zone": "Computed inside the evidence zone."}.get(mode, "")},
        {"n": 2, "title": "Data sought", "asked": cat["asked"], "query": q,
         "call": f"{cat['system']}.fetch({', '.join(f'{k}={v}' for k, v in q.items())})",
         "note": "Values are tokens. The real values never leave the evidence zone."},
        {"n": 3, "title": "Data received", "result": r.get("result") or "", "status": status, "status_label": r.get("status_label") or status,
         "fields": fields, "facts": r.get("facts") or {}},
        {"n": 4, "title": "Governance rule", "rule_id": cat["rule"], "rule": cat["text"], "verdict": verdict,
         "verdict_label": {"pass": "Rule satisfied", "review": "Rule not satisfied: human review", "fail": "Rule failed", "info": "Informational: no rule outcome"}[verdict]},
        {"n": 5, "title": "Latency and trace", "checked_at": r.get("checked_at") or "", "latency_ms": _latency(r["id"], kind),
         "latency_simulated": mode != "real", "trace_hash": trace[:16], "trace_note": "Fingerprint of the connector response kept for audit."},
    ]
    return {"case_id": case.get("case_id"), "evidence_id": evidence_id, "check": r.get("check"), "kind": kind, "position": i + 1, "total": len(rows),
            "prev_id": ids[i - 1] if i > 0 else None, "next_id": ids[i + 1] if i + 1 < len(ids) else None,
            "steps": steps, "summary": [{"id": x["id"], "check": x.get("check"), "status": x.get("status")} for x in rows]}
