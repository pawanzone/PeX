"""Read-only reference views: payment ontology, canonical database and semantic layer, SOP list."""
from __future__ import annotations

from typing import Any, Dict, List

from app.db.base import Base
from app.db.session import SessionLocal
from app.schemas import canonical as cn
from app.services.v2 import evidence_model as em
from app.services.v2.core import not_found

CANONICAL_MODELS = ["CanonicalParty", "CanonicalAccount", "CanonicalPayment", "CanonicalException", "CaseSummary", "PeXCase"]

# canonical field -> ISO 20022 element (CBPR+ pacs.008 / pacs.002 unless noted). Curated; the test proves every canonical field exists.
SEMANTIC_LAYER: List[Dict[str, str]] = [
    {"canonical": "CanonicalPayment.payment_id", "iso20022": "pacs.008 CdtTrfTxInf/PmtId/TxId", "description": "Transaction identifier assigned by the instructing bank."},
    {"canonical": "CanonicalPayment.uetr", "iso20022": "pacs.008 CdtTrfTxInf/PmtId/UETR", "description": "Unique end-to-end transaction reference. Links every message and status for the payment."},
    {"canonical": "CanonicalPayment.instruction_id", "iso20022": "pacs.008 CdtTrfTxInf/PmtId/InstrId", "description": "Instruction identifier between instructing and instructed agent."},
    {"canonical": "CanonicalPayment.end_to_end_id", "iso20022": "pacs.008 CdtTrfTxInf/PmtId/EndToEndId", "description": "Reference passed unchanged from debtor to creditor."},
    {"canonical": "CanonicalPayment.amount", "iso20022": "pacs.008 CdtTrfTxInf/IntrBkSttlmAmt", "description": "Interbank settlement amount."},
    {"canonical": "CanonicalPayment.currency", "iso20022": "pacs.008 CdtTrfTxInf/IntrBkSttlmAmt/@Ccy", "description": "Settlement currency (ISO 4217)."},
    {"canonical": "CanonicalPayment.settlement_date", "iso20022": "pacs.008 CdtTrfTxInf/IntrBkSttlmDt", "description": "Interbank settlement date."},
    {"canonical": "CanonicalPayment.payment_rail", "iso20022": "pacs.008 GrpHdr/SttlmInf/SttlmMtd (derived)", "description": "Rail or scheme the payment travels on; derived from message type and settlement method."},
    {"canonical": "CanonicalParty.party_name", "iso20022": "pacs.008 Dbtr/Nm and Cdtr/Nm", "description": "Party name as instructed. Personal data (class C1); tokenised outside the evidence zone."},
    {"canonical": "CanonicalParty.country", "iso20022": "pacs.008 Dbtr/PstlAdr/Ctry and Cdtr/PstlAdr/Ctry", "description": "Party country code."},
    {"canonical": "CanonicalParty.identifier_value", "iso20022": "pacs.008 Cdtr/Id/OrgId or PrvtId", "description": "Organisation or private identifier of the party. Personal data (C1)."},
    {"canonical": "CanonicalAccount.iban", "iso20022": "pacs.008 DbtrAcct/Id/IBAN and CdtrAcct/Id/IBAN", "description": "IBAN of the account (ISO 13616). Personal data (C1)."},
    {"canonical": "CanonicalAccount.account_number", "iso20022": "pacs.008 CdtrAcct/Id/Othr/Id", "description": "Account number where no IBAN exists. Personal data (C1)."},
    {"canonical": "CanonicalAccount.currency", "iso20022": "pacs.008 CdtrAcct/Ccy", "description": "Currency of the account."},
    {"canonical": "CanonicalAccount.bank_bic", "iso20022": "pacs.008 CdtrAgt/FinInstnId/BICFI", "description": "BIC of the account servicing bank (ISO 9362)."},
    {"canonical": "CanonicalAccount.bank_name", "iso20022": "pacs.008 CdtrAgt/FinInstnId/Nm", "description": "Name of the account servicing bank."},
    {"canonical": "CanonicalException.error_code", "iso20022": "pacs.002 TxInfAndSts/StsRsnInf/Rsn/Cd", "description": "Status reason code that raised the exception (ISO external reason code)."},
    {"canonical": "CanonicalException.reason", "iso20022": "pacs.002 TxInfAndSts/StsRsnInf/AddtlInf", "description": "Additional information on the reason."},
    {"canonical": "CanonicalException.sla_due_at", "iso20022": "PeX: payment cutoff time (no ISO element)", "description": "When the payment must be resolved to meet its cutoff."},
    {"canonical": "CanonicalException.at_risk_amount", "iso20022": "PeX: derived from IntrBkSttlmAmt", "description": "Amount held up by the exception."},
]


def ontology() -> Dict[str, Any]:
    from app.api.endpoints import ontology as o
    return {"pipeline": o.get_pipeline_stages(), "entities": [{**e} for e in o.get_canonical_entities()], "domains": o.get_investigation_domains_matrix(),
            "note": "Read only. Bank-agnostic canonical entities aligned to ISO 20022 and BIAN."}


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
    return {"tables": tables, "relations": relations, "canonical": canonical, "semantic_layer": SEMANTIC_LAYER,
            "note": "Read from the live database models and canonical schemas. The semantic layer is curated and checked against the schemas."}


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
