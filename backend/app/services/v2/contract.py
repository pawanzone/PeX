"""Integration contract (Admin, read only): what a bank's event must carry for each profile, and how PeX gets each item.

Everything is read from the live code: the profile packs (evidence rules), the input schema (envelope fields), the evidence
catalogue (meaning and source), the reference-lookup registry (what PeX can fetch itself) and the e2e fixtures (sample events).
Only the meaning text for the envelope fields is written here, and it is marked for the bank's SMEs to validate."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.profile_packs import registry
from app.schemas.contracts.e2e_schemas import CanonicalE2EInput, E2EPaymentInfo
from app.schemas.contracts.evidence_config_schemas import EvidenceAcquisitionMode, EvidenceRuleDefinition
from app.services import reference_connectors as rc
from app.services.v2 import library as lb
from app.services.v2 import semantic_layer as sl
from app.services.v2.core import not_found

VALIDATION = lb.VALIDATION
ROOT = Path(registry.__file__).resolve().parents[3]
FIXTURE_DIRS = [ROOT / "e2e_fixtures" / "input", ROOT / "e2e_fixtures" / "eur"]
GROUPS = ("bank_supplied_evidence", "external_authoritative_evidence", "derived_evidence", "historical_evidence")
BANK_OWNED = {"BANK_COUNTERPARTY_SSI", "BANK_DESIGNATED_SSI", "CORRESPONDENT_SSI_DIRECTORY", "SYNTAX_ERROR_SPECIFICATION"}
REFERENCE = "Reference data"

PAYMENT_MEANING = {
    "payment_id": "The bank's own identifier for the payment.", "uetr": "End-to-end transaction reference (a UUID) that follows the payment across banks.",
    "amount": "Instructed amount.", "currency": "Three-letter ISO currency code.", "clearing_rail": "The scheme or rail, for example FEDWIRE, CHAPS, TARGET2, SWIFT_CBPR+ or BACS.",
    "value_date": "Requested settlement date.", "debtor_name": "Name of the paying party (personal data, tokenised by PeX).", "debtor_account": "Debtor account or IBAN (tokenised by PeX).",
    "debtor_agent_bic": "BIC of the debtor's bank.", "creditor_name": "Name of the receiving party (personal data, tokenised by PeX).", "creditor_account": "Creditor account or IBAN (tokenised by PeX).",
    "creditor_agent_bic": "BIC of the creditor's bank.", "remittance_info": "Payment details text from the sender.", "charge_bearer": "Who pays the charges (for example DEBT, CRED, SHAR).",
}
TOP_MEANING = {
    "exception_id": "The bank's identifier for this exception.", "tenant_id": "Which bank configuration applies. Defaults to DEFAULT_BANK.",
    "profile_id": "The exception type if the bank already knows it (for example DQ-01). PeX classifies it when absent.", "domain": "Exception family (data quality, processing, compliance, ...).",
    "error_code": "The error code the bank's system raised.", "error_message": "The error text the bank's system raised.", "payment_info": "The payment itself. See the payment fields.",
    "raw_payload": "The original message, kept for reference.", "bank_supplied_evidence": "Evidence from the bank's own systems.",
    "external_authoritative_evidence": "Evidence from a regulator, scheme or directory.", "derived_evidence": "Values calculated from other fields.",
    "historical_evidence": "Context from past cases. Informs a person and never proves anything on its own.", "bank_policy_overrides": "Bank-specific limits for this event, if any.",
    "processing_metadata": "Free-form notes from the sending system.", "secondary_profile_ids": "Other exception types that apply to the same payment.",
    "evidence_provenance": "Whether the evidence is real or a synthetic test fixture.", "test_status": "Marks test events.", "created_at": "When the event was created.",
}
GROUP_MEANING = {
    "bank_supplied_evidence": "From the bank's own systems, usually core records (trust tier 1).",
    "external_authoritative_evidence": "From a regulator, scheme or directory (trust tier 2).",
    "derived_evidence": "Calculated by the bank or PeX from other fields, such as a recalculated check digit.",
    "historical_evidence": "From past cases. Context only: it informs a person and has no authority.",
}
MODE_MEANING = {
    "MODE_1_INBOUND_PAYLOAD": "The bank sends the evidence inside the event.",
    "MODE_2_API_CONNECTOR": "PeX looks it up itself through a connector.",
    "MODE_3_BANK_PUSH": "The bank sends it later by webhook or event.",
    "MODE_4_HITL_OPERATOR": "A person types it in on the case screen.",
}
HOW_LABEL = {
    "BANK_SENDS": "Sent by the bank",
    "PEX_LOOKUP_COMPUTED": "PeX looks it up (computed from published rules)",
    "PEX_LOOKUP_SIMULATED": "PeX looks it up (simulated directory)",
    "COULD_LOOK_UP": "Could be looked up (connector not built)",
}
RULE = ("This is the format contract: what a bank's event must carry for each exception type, and how PeX gets each item. "
        "Lookups marked simulated answer from seeded sample tables, not from the real directory. Nothing in the live case flow uses a lookup yet. "
        "Evidence names in events are lower case.")
DELIVERY = {
    "single": {"title": "One event at a time", "shape": "CanonicalE2EInput (one JSON per exception)",
               "channels": ["Drop the JSON file in the watched input folder", "POST /api/events/ingest for a raw bank event, which PeX converts to a case"],
               "answer": "A case with a recommendation, an eligibility result and an output file for the event."},
    "batch": {"title": "Many events together", "shape": "CanonicalE2EBatchInput (batch_id plus records) or a .jsonl, .ndjson or .json.gz file",
              "channels": ["Drop the file in the watched input folder", "POST /api/batch/upload (processed asynchronously)"],
              "outcomes": ["PROCESSED", "SKIPPED_EXISTING_CASE", "SKIPPED_DUPLICATE_IN_BATCH", "FAILED_SCHEMA", "FAILED_PROCESSING"],
              "answer": "A reconciliation report with one outcome per record. Each record is accepted, a duplicate, rejected or needs review."},
}


def _default_modes() -> List[str]:
    return [m.value for m in EvidenceRuleDefinition.model_fields["acquisition_modes"].default_factory()]


def _freshness_hours() -> int:
    return EvidenceRuleDefinition.model_fields["freshness_ttl_seconds"].default // 3600


def _how(etype: str, category: str) -> str:
    c = rc.REGISTRY.get(etype)
    if c:
        return "PEX_LOOKUP_COMPUTED" if c.kind == "COMPUTED" else "PEX_LOOKUP_SIMULATED"
    if category == REFERENCE and etype not in BANK_OWNED:
        return "COULD_LOOK_UP"
    return "BANK_SENDS"


def _modes(etype: str) -> List[str]:
    m = _default_modes()
    if etype in rc.REGISTRY:
        m.insert(1, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR.value)
    return m


TIER_NAME = {1: "Core record", 2: "Authoritative", 3: "Corroborating", 4: "Advisory"}


def _tier_name(tier: int) -> str:
    return TIER_NAME.get(tier, f"Tier {tier}")


def _evidence_rows(pack) -> List[Dict[str, Any]]:
    cat = {r["type"]: r for r in sl.evidence_catalogue()}
    rows = []
    for e in pack.evidence.required:
        c = cat.get(e.type, {})
        how = _how(e.type, c.get("category", ""))
        conn = rc.REGISTRY.get(e.type)
        rows.append({"type": e.type, "event_key": e.type.lower(), "mandatory": e.mandatory, "tier": e.tier, "tier_name": _tier_name(e.tier), "meaning": c.get("proves", ""),
                     "source_system": c.get("source_system", ""), "category": c.get("category", ""), "how": how, "how_label": HOW_LABEL[how], "modes": _modes(e.type),
                     "freshness_hours": _freshness_hours(),
                     "lookup": ({"kind": conn.kind, "source": conn.source, "as_of": conn.as_of, "name": conn.name, "params": list(conn.params)} if conn else None)})
    rows.sort(key=lambda r: (not r["mandatory"], r["type"]))
    return rows


def _event_keys(ev: Dict[str, Any]) -> set:
    return {k.lower() for g in GROUPS for k in (ev.get(g) or {})}


@lru_cache(maxsize=None)
def _fixtures_for(code: str) -> List[Dict[str, Any]]:
    out = []
    for d in FIXTURE_DIRS:
        for f in sorted(d.glob(f"{code}_*.json")):
            if f.name.endswith((".output.json", ".reconciliation.json")):
                continue
            try:
                ev = json.loads(f.read_text(encoding="utf-8"))
                CanonicalE2EInput.model_validate(ev)
            except Exception:
                continue
            out.append({"file": f.name, "event": ev})
    return out


def _sample(code: str, pack) -> Optional[Dict[str, Any]]:
    mand = {e.type.lower() for e in pack.evidence.required if e.mandatory}
    full = [f for f in _fixtures_for(code) if mand <= _event_keys(f["event"]) and f["event"].get("profile_id") == code]
    if not full:
        return None
    full.sort(key=lambda f: ("sufficient" not in f["file"], f["file"]))
    return {"file": full[0]["file"], "event": full[0]["event"], "synthetic": True}


def _envelope() -> Dict[str, Any]:
    top = [{"field": n, "required": f.is_required(), "meaning": TOP_MEANING.get(n, "")} for n, f in CanonicalE2EInput.model_fields.items()]
    pay = [{"field": n, "required": f.is_required(), "meaning": PAYMENT_MEANING.get(n, "")} for n, f in E2EPaymentInfo.model_fields.items()]
    return {"top_fields": top, "payment_fields": pay, "evidence_groups": [{"field": g, "meaning": GROUP_MEANING[g]} for g in GROUPS]}


def _always_required() -> List[str]:
    return [n for n, f in E2EPaymentInfo.model_fields.items() if f.is_required()]


def profile_contract(code: str) -> Dict[str, Any]:
    pack = registry.get_pack(code)
    if pack is None or code not in registry.load_packs():
        raise not_found("Profile not found.")
    rows = _evidence_rows(pack)
    s = _sample(code, pack)
    used = [k for k, v in ((s or {}).get("event", {}).get("payment_info") or {}).items() if v not in (None, "") and k not in _always_required()]
    return {
        "code": code, "name": pack.name, "validation_status": VALIDATION, "envelope_required": [e for e in _envelope()["payment_fields"] if e["required"]],
        "payment_fields": {"always_required": _always_required(), "used_in_sample": used,
                           "note": "Fields beyond the always-required ones are those the reference sample carries. The bank's SMEs should validate them against their process."},
        "evidence": rows,
        "counts": {"total": len(rows), "mandatory": sum(r["mandatory"] for r in rows), "optional": sum(not r["mandatory"] for r in rows),
                   "lookups_built": sum(r["how"] in ("PEX_LOOKUP_COMPUTED", "PEX_LOOKUP_SIMULATED") for r in rows),
                   "could_look_up": sum(r["how"] == "COULD_LOOK_UP" for r in rows), "bank_sends": sum(r["how"] == "BANK_SENDS" for r in rows)},
        "sample": s,
        "sample_note": "" if s else "No reference sample event exists for this profile yet.",
    }


def overview() -> Dict[str, Any]:
    packs = {c: registry.get_pack(c) for c in sorted(registry.load_packs())}
    cov, types = [], {}
    for code, p in packs.items():
        rows = _evidence_rows(p)
        for r in rows:
            types.setdefault(r["type"], {"how": r["how"], "profiles": []})["profiles"].append(code)
        cov.append({"code": code, "name": p.name, "total": len(rows), "mandatory": sum(r["mandatory"] for r in rows),
                    "lookups_built": sum(r["how"] in ("PEX_LOOKUP_COMPUTED", "PEX_LOOKUP_SIMULATED") for r in rows), "could_look_up": sum(r["how"] == "COULD_LOOK_UP" for r in rows),
                    "bank_sends": sum(r["how"] == "BANK_SENDS" for r in rows), "has_sample": _sample(code, p) is not None})
    lookups = [{"evidence_type": c.evidence_type, "name": c.name, "kind": c.kind, "source": c.source, "as_of": c.as_of, "params": list(c.params),
                "used_by_profiles": len(types.get(c.evidence_type, {}).get("profiles", []))} for c in rc.REGISTRY.values()]
    by_how: Dict[str, int] = {}
    for t in types.values():
        by_how[t["how"]] = by_how.get(t["how"], 0) + 1
    modes = [{"mode": m.value, "meaning": MODE_MEANING[m.value]} for m in EvidenceAcquisitionMode]
    return {"profiles": len(packs), "rule": RULE, "validation_status": VALIDATION, "envelope": _envelope(), "modes": modes, "delivery": DELIVERY, "lookups": lookups, "coverage": cov,
            "evidence_summary": {"distinct_types": len(types), "shared_by_two_or_more": sum(1 for t in types.values() if len(t["profiles"]) >= 2), "by_how": by_how},
            "how_labels": HOW_LABEL}
