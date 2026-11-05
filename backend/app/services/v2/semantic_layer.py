"""Semantic layer, generated from the real models and the profile packs. Meaning is curated in semantic_data.py; everything that can
be computed (which fields exist, which profiles use which evidence at which tier, counts) is computed, so it cannot drift."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from app.schemas import canonical as cn
from app.services.v2 import classification as cls
from app.services.v2.semantic_data import ELEMENTS, ELEMENT_HOME, EVIDENCE, FIELD_ROWS

MODELS = ["CanonicalParty", "CanonicalAccount", "CanonicalPayment", "CanonicalException", "CanonicalPostalAddress", "CanonicalAgent", "ChargeInfo",
          "CanonicalCharges", "CanonicalRemittance", "CanonicalPurpose", "CanonicalEnvelope", "CanonicalStatusReport", "CanonicalInvestigation",
          "CanonicalMandate", "CanonicalScreeningAlert", "CanonicalBankOutcome", "CanonicalApprovalRecord", "CanonicalAuditEvent", "CanonicalCustomer", "CanonicalKycRecord", "CanonicalTreasuryPosition",
          "CanonicalPrecedentSummary"]
PACKS_DIR = Path(__file__).resolve().parents[2] / "profile_packs" / "packs"


@lru_cache(maxsize=1)
def _packs() -> Dict[str, Dict[str, Any]]:
    return {p["code"]: p for p in (json.loads(f.read_text(encoding="utf-8")) for f in sorted(PACKS_DIR.glob("*.json")))}


def field_mappings() -> List[Dict[str, Any]]:
    rows = []
    for m in MODELS:
        for f in getattr(cn, m).model_fields:
            key = f"{m}.{f}"
            iso, mt, validation, desc, klass = FIELD_ROWS[key]
            rows.append({"canonical": key, "iso20022": iso, "mt": mt, "validation": validation, "description": desc, "data_class": klass,
                         "pex_internal": iso.startswith("PeX:")})
    return rows


def evidence_catalogue() -> List[Dict[str, Any]]:
    uses: Dict[str, List[Dict[str, Any]]] = {}
    for code, p in _packs().items():
        for e in p["evidence"]["required"]:
            uses.setdefault(e["type"], []).append({"code": code, "name": p["name"], "tier": e["tier"]})
    rows = []
    for t in sorted(set(EVIDENCE) | set(uses)):
        cat, system, proves, iso, klass = EVIDENCE[t]
        u = sorted(uses.get(t, []), key=lambda x: x["code"])
        rows.append({"type": t, "label": t.replace("_", " ").capitalize(), "category": cat, "source_system": system, "proves": proves,
                     "iso_messages": iso, "data_class": klass, "used_by": u, "profile_count": len(u)})
    return rows


def _home_exists(path: str) -> bool:
    model, _, fld = path.partition(".")
    cls_ = getattr(cn, model, None)
    return bool(cls_) and (not fld or fld in cls_.model_fields)


def element_catalogue() -> List[Dict[str, Any]]:
    out = []
    for e, msg, mt, k, why, p in ELEMENTS:
        home = ELEMENT_HOME.get(e)
        out.append({"element": e, "message": msg, "mt": mt, "data_class": k, "why": why, "used_by": list(p),
                    "canonical_home": home if home and _home_exists(home) else None, "in_canonical_model": bool(home and _home_exists(home))})
    return out


_MSG = re.compile(r"\b(?:pacs|pain|camt|head)\.\d{3}\b")


def summary() -> Dict[str, Any]:
    fields, ev, el = field_mappings(), evidence_catalogue(), element_catalogue()
    total = sum(len(getattr(cn, m).model_fields) for m in MODELS)
    msgs = set()
    for r in fields:
        msgs |= set(_MSG.findall(r["iso20022"]))
    for r in ev:
        msgs |= set(_MSG.findall(r["iso_messages"]))
    for r in el:
        msgs |= set(_MSG.findall(r["message"]))
    cats: Dict[str, int] = {}
    for r in ev:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    classes: Dict[str, int] = {k: 0 for k in cls.CLASSES}
    for r in fields + ev + el:
        classes[r["data_class"]] += 1
    return {"canonical_fields_total": total, "canonical_fields_mapped": len(fields), "iso_mapped_fields": sum(1 for r in fields if not r["pex_internal"]),
            "evidence_types": len(ev), "profiles": len(_packs()), "element_gaps": sum(1 for r in el if not r["in_canonical_model"]), "elements_total": len(el), "elements_covered": sum(1 for r in el if r["in_canonical_model"]), "iso_messages": sorted(msgs), "categories": cats,
            "data_classes": {k: {"label": cls.CLASSES[k], "count": v} for k, v in classes.items()}}
