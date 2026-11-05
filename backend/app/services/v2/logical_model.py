"""The logical canonical model: the business entities PeX reasons about, grouped by domain. Curated here: the entity, its meaning, its
ISO 20022 anchor and how it relates to others. Computed from the code: whether it exists ("in code" when the class is in
app.schemas.canonical, "database only" when only a table holds it, otherwise "planned") and its field count. Nothing here can claim an
entity exists that the code does not have."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

from app.schemas import canonical as cn

DOMAINS = ["Payment", "Parties and accounts", "Banks and routing", "Message and status", "Compliance", "PeX workflow"]

# name -> (domain, description, ISO 20022 anchor, canonical class or None, database table or None, links [(target, label)])
ENTITIES: Dict[str, Tuple[str, str, str, Optional[str], Optional[str], List[Tuple[str, str]]]] = {
    "Payment": ("Payment", "The instruction being moved: ids, amount, currency, rail, dates, and the parties and banks around it.", "pacs.008 CdtTrfTxInf", "CanonicalPayment", None,
                [("Party", "debtor and creditor"), ("Account", "debits and credits"), ("Bank", "debtor, creditor and intermediary banks"), ("Charges and FX", "has"),
                 ("Remittance", "carries"), ("Purpose", "states"), ("Message envelope", "arrived in")]),
    "Message envelope": ("Payment", "How the message itself travels: type, id, settlement method, clearing system, service level, sender and receiver.", "pacs.008 GrpHdr, PmtTpInf", "CanonicalEnvelope", None, []),
    "Charges and FX": ("Payment", "Who pays the fees, the charges taken on the way, and the original amount and rate when the payment was converted.", "pacs.008 ChrgBr, ChrgsInf, InstdAmt, XchgRate", "CanonicalCharges", None, []),
    "Remittance": ("Payment", "What the payment is for, as the sender wrote it: free text and a structured reference.", "pacs.008 RmtInf", "CanonicalRemittance", None, []),
    "Purpose": ("Payment", "Why the payment is made: purpose, category purpose and regulatory reporting codes.", "pacs.008 Purp, CtgyPurp, RgltryRptg", "CanonicalPurpose", None, []),
    "Party": ("Parties and accounts", "A debtor, creditor or ultimate party: name, country, identifier and address.", "pacs.008 Dbtr, Cdtr, UltmtDbtr, UltmtCdtr", "CanonicalParty", None,
              [("Postal address", "has"), ("Account", "holds")]),
    "Postal address": ("Parties and accounts", "Where a party is: structured street, town, post code and country, or free address lines.", "PstlAdr", "CanonicalPostalAddress", None, []),
    "Account": ("Parties and accounts", "A debit or credit account: IBAN or account number, currency and the bank that holds it.", "pacs.008 DbtrAcct, CdtrAcct", "CanonicalAccount", None, [("Bank", "held at")]),
    "Mandate": ("Parties and accounts", "A direct-debit mandate: id, creditor scheme id, signature date and sequence.", "pain.009 Mndt", "CanonicalMandate", None, [("Account", "debits")]),
    "Bank": ("Banks and routing", "A bank in the chain: debtor bank, creditor bank, intermediaries, with BIC and clearing member id.", "pacs.008 DbtrAgt, CdtrAgt, IntrmyAgt1..3", "CanonicalAgent", None, []),
    "Routing directory entry": ("Banks and routing", "A bank's reachability by rail: BIC, clearing member id, successor BIC and validity dates, from the bank's directory.", "SwiftRef / clearing directories", None, None, [("Bank", "describes")]),
    "Correspondent position": ("Banks and routing", "The bank's nostro and vostro balances and limits per correspondent and currency.", "camt.053 / camt.052 statements", None, None, [("Bank", "held with")]),
    "Status report": ("Message and status", "What a bank reported about a payment (accepted, rejected, returned) and why.", "pacs.002, pacs.004", "CanonicalStatusReport", None, [("Payment", "reports on")]),
    "Investigation": ("Message and status", "A recall, investigation request or their answers, tied to the payment by UETR.", "camt.056, camt.029, camt.110, camt.111", "CanonicalInvestigation", None, [("Payment", "concerns")]),
    "Bank outcome": ("Message and status", "The bank's final word on an action PeX handed over: executed, rejected or still unknown.", "pacs.002 / bank callback", "CanonicalBankOutcome", "bank_outcomes", [("Case", "settles")]),
    "Screening alert": ("Compliance", "A sanctions, PEP or watch-list hit raised against a party, with its score and the screening team's decision.", "Bank screening system", "CanonicalScreeningAlert", None, [("Party", "raised against")]),
    "Customer KYC record": ("Compliance", "The customer's KYC status, expiry and risk rating, held by the bank.", "Bank KYC system", None, None, [("Party", "describes")]),
    "Exception": ("PeX workflow", "Why a payment stopped: profile, error code, severity, SLA and the amount at risk.", "PeX", "CanonicalException", None, [("Payment", "stopped")]),
    "Case": ("PeX workflow", "The unit of work a person handles: status, queue, evidence, recommendation, approvals and audit.", "PeX", "PeXCase", "cases", [("Exception", "opened for"), ("Payment", "about"), ("Approval", "gated by"), ("Audit event", "recorded in")]),
    "Approval": ("PeX workflow", "A person's decision on a case: who, role, when, comment, and the second approver where required.", "PeX", "CanonicalApprovalRecord", "approval_records", [("Case", "decides")]),
    "Audit event": ("PeX workflow", "A tamper-evident record of each step on a case.", "PeX", "CanonicalAuditEvent", "audit_events", [("Case", "belongs to")]),
}

SUPPORTING = {"ChargeInfo": "One charge line inside Charges and FX.", "CaseSummary": "The list view of a case (a projection of Case)."}


def _fields(cls_name: str) -> int:
    return len(getattr(cn, cls_name).model_fields)


def logical_model() -> Dict[str, Any]:
    ents: List[Dict[str, Any]] = []
    for name, (domain, desc, iso, klass, table, links) in ENTITIES.items():
        in_code = bool(klass and isinstance(getattr(cn, klass, None), type) and issubclass(getattr(cn, klass), BaseModel))  # aliases resolve through cn.__getattr__
        status = "in code" if in_code else ("database only" if table else "planned")
        ents.append({"name": name, "domain": domain, "description": desc, "iso_anchor": iso, "status": status,
                     "canonical_class": klass if in_code else None, "db_table": table,
                     "fields": _fields(klass) if in_code else 0, "links": [{"to": t, "label": lbl} for t, lbl in links]})
    summary = {"entities": len(ents), "in_code": sum(e["status"] == "in code" for e in ents), "database_only": sum(e["status"] == "database only" for e in ents),
               "planned": sum(e["status"] == "planned" for e in ents)}
    return {"domains": DOMAINS, "entities": ents, "summary": summary, "planned_names": [e["name"] for e in ents if e["status"] == "planned"],
            "supporting_classes": SUPPORTING}
