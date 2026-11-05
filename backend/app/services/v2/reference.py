"""Read-only reference views: payment ontology, canonical database and semantic layer, SOP list."""
from __future__ import annotations

from typing import Any, Dict, List

from app.db.base import Base
from app.db.session import SessionLocal
from app.schemas import canonical as cn
from app.services.v2 import evidence_model as em
from app.services.v2 import semantic_layer as sl
from app.services.v2.logical_model import logical_model
from app.services.v2.core import not_found

CANONICAL_MODELS = ["CanonicalParty", "CanonicalAccount", "CanonicalPayment", "CanonicalException", "CaseSummary", "PeXCase", "CanonicalPostalAddress", "CanonicalAgent",
                    "CanonicalCharges", "CanonicalRemittance", "CanonicalPurpose", "CanonicalEnvelope", "CanonicalStatusReport", "CanonicalInvestigation", "CanonicalMandate",
                    "CanonicalScreeningAlert", "CanonicalBankOutcome", "CanonicalApprovalRecord", "CanonicalAuditEvent", "CanonicalCustomer", "CanonicalKycRecord", "CanonicalTreasuryPosition",
                    "CanonicalPrecedentSummary", "CanonicalRoutingEntry"]

def ontology() -> Dict[str, Any]:
    from app.api.endpoints import ontology as o
    from app.services.v2 import ontology_map as om
    ents = [{**e, **om.describe(e["name"], e["key_fields"])} for e in o.get_canonical_entities()]
    return {"pipeline": o.get_pipeline_stages(), "entities": ents, "domains": o.get_investigation_domains_matrix(),
            "note": "Read only. Bank-agnostic entities aligned to ISO 20022 and BIAN. Each key field shows its canonical home or the canonical fields it is derived from, checked against the code."}


def _model_fields(name: str) -> List[Dict[str, Any]]:
    m = getattr(cn, name)
    out = []
    for fname, f in m.model_fields.items():
        out.append({"name": fname, "type": str(getattr(f.annotation, "__name__", f.annotation)).replace("typing.", ""), "required": f.is_required()})
    return out


def data_model() -> Dict[str, Any]:
    doc = {}
    for mapper in Base.registry.mappers:
        doc[mapper.local_table.name] = (mapper.class_.__doc__ or "").strip().split("\n")[0]
    counts: Dict[str, int] = {}
    db = SessionLocal()
    try:
        for t in Base.metadata.sorted_tables:
            try:
                counts[t.name] = db.execute(t.select().with_only_columns(t.c[list(t.c.keys())[0]])).fetchall().__len__()
            except Exception:
                counts[t.name] = -1
    finally:
        db.close()
    tables, relations = [], []
    for t in Base.metadata.sorted_tables:
        cols = []
        for c in t.columns:
            fk = next(iter(c.foreign_keys), None)
            cols.append({"name": c.name, "type": str(c.type), "nullable": bool(c.nullable), "primary_key": bool(c.primary_key), "references": fk.target_fullname if fk else None})
            if fk:
                relations.append({"from": f"{t.name}.{c.name}", "to": fk.target_fullname})
        tables.append({"name": t.name, "description": doc.get(t.name, ""), "columns": cols, "rows": counts.get(t.name, -1)})
    canonical = [{"name": n, "fields": _model_fields(n), "description": (getattr(cn, n).__doc__ or "").strip().split("\n")[0]} for n in CANONICAL_MODELS]
    return {"tables": tables, "relations": relations, "canonical": canonical, "logical_model": logical_model(), "semantic_layer": sl.field_mappings(),
            "evidence_catalogue": sl.evidence_catalogue(), "element_catalogue": sl.element_catalogue(), "semantic_summary": sl.summary(),
            "note": "Read from the live database models, canonical schemas and profile packs. Meaning is curated; coverage is computed and tested."}


def _sys_name(k: str) -> str:
    return em.SYSTEMS[k][1] if k in em.SYSTEMS else {"ISO": "Deterministic check", "IBANREG": "IBAN registry", "SWIFTREF": "SwiftRef directory", "COPVOP": "Verification of Payee", "ERP": "Customer ERP", "LISTS": "Sanctions lists", "GPI": "SWIFT gpi tracker", "STMT": "Bank statements"}.get(k, k)


def _profile(code: str):
    p = em.PROFILES.get(code)
    return p


def sops() -> Dict[str, Any]:
    rows = []
    for code, (name, standards, items) in em.PROFILES.items():
        rows.append({"code": code, "name": name.replace("_", " ").title(), "family": code.split("-")[0], "standards": standards, "evidence_items": len(items),
                     "gate_items": sum(1 for i in items if i["gate"]), "version": "Framework v1", "status": "Framework default",
                     "owner": "Not assigned", "note": "Placeholder until the bank supplies its own SOP."})
    return {"total": len(rows), "items": rows, "note": "Framework defaults seeded from the exception profiles. Replaced by the bank's signed-off SOPs during onboarding."}


def sop(code: str) -> Dict[str, Any]:
    p = _profile(code)
    if not p:
        raise not_found(f"SOP {code}")
    name, standards, items = p
    row = next(r for r in sops()["items"] if r["code"] == code)
    return {**row, "items": [{"name": i["name"], "role": i["role"], "weight": i["weight"], "pillar": i["pillar"], "pillar_name": em.PILLAR_NAMES.get(i["pillar"], i["pillar"]),
                              "system": i["system"], "system_name": _sys_name(i["system"]), "gate": bool(i["gate"])} for i in items]}
