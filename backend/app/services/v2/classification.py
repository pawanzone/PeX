"""Data classification for payment-exception data (C1 to C5) and who may reveal what.

Basis: ISO 20022 message elements as profiled by CBPR+ (pacs.008 / pacs.009 / pacs.002 / pacs.004 / camt.056 / camt.029),
GDPR (incl. Art. 9 for free text that may carry special-category data), FATF Recommendation 16 / EU Funds Transfer Regulation
(the originator and beneficiary data that must travel with a payment). The bank's own policy replaces this when it is available.

C1 Direct identifiers   names, addresses, IBAN / account numbers, private IDs, organisation tax IDs, phone, email, KYC documents
C2 Free text            remittance text, instructions to next agent, handover notes, e-mails, invoices
C3 Restricted           sanctions / screening hits, suspicious-activity indicators (tipping-off risk)
C4 Linkable references  UETR, end-to-end id, case id
C5 Operational          BIC, currency, dates, status / reason codes, message type, charge bearer (not personal data)
Amount is not a class: exact amount stays in the zone, outside it the AI receives a band.
"""
from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Optional

CLASSES: Dict[str, str] = {
    "C1": "Direct identifiers", "C2": "Free text and documents", "C3": "Restricted (screening)",
    "C4": "Linkable references", "C5": "Operational (not personal)",
}

# vault token type -> class (token looks like TOK-<TYPE>-<hex>)
TOKEN_CLASS: Dict[str, str] = {
    "PARTY": "C1", "IBAN": "C1", "ACC": "C1", "ADDR": "C1", "DOB": "C1", "NID": "C1", "TAXID": "C1", "PHONE": "C1", "EMAIL": "C1",
    "TEXT": "C2", "SCRN": "C3", "REF": "C4",
}

# ISO 20022 element / field name fragments -> class. First match wins, most specific first.
_FIELD_RULES: List[tuple] = [
    ("sanction", "C3"), ("screening", "C3"), ("watchlist", "C3"), ("suspicious", "C3"), ("pep_", "C3"),
    ("rmtinf", "C2"), ("remittance", "C2"), ("ustrd", "C2"), ("instrfornxtagt", "C2"), ("note", "C2"), ("email_body", "C2"), ("invoice_text", "C2"),
    ("uetr", "C4"), ("endtoendid", "C4"), ("end_to_end", "C4"), ("case_id", "C4"), ("instrid", "C4"),
    ("iban", "C1"), ("account", "C1"), ("acct", "C1"), ("acc_no", "C1"), ("othr", "C1"),
    ("party", "C1"), ("name", "C1"), ("nm", "C1"), ("cdtr", "C1"), ("dbtr", "C1"), ("pstladr", "C1"), ("address", "C1"), ("addr", "C1"),
    ("birth", "C1"), ("dob", "C1"), ("national_id", "C1"), ("passport", "C1"), ("prvtid", "C1"), ("taxid", "C1"), ("tax_id", "C1"),
    ("phone", "C1"), ("email", "C1"), ("kyc", "C1"),
]


def classify_field(key: Any) -> str:
    k = str(key or "").lower().replace(" ", "_")
    for frag, cls in _FIELD_RULES:
        if frag in k:
            return cls
    return "C5"


def token_class(token: str) -> Optional[str]:
    parts = str(token).split("-")
    if len(parts) >= 3 and parts[0] == "TOK":
        return TOKEN_CLASS.get(parts[1])
    return None


# Who may reveal which class, on cases they can see. Every reveal needs a reason, is logged and expires.
ROLE_REVEAL: Dict[str, FrozenSet[str]] = {
    "OPERATOR": frozenset({"C1", "C2", "C4"}),
    "SUPERVISOR": frozenset({"C1", "C2", "C4"}),
    "OPERATIONS_APPROVER": frozenset({"C1", "C2", "C4"}),
    "RISK_APPROVER": frozenset({"C1", "C2", "C4"}),
    "COMPLIANCE_APPROVER": frozenset({"C1", "C2", "C3", "C4"}),   # only role that sees C3 (and also C1, C2)
    "AUDIT_RISK": frozenset({"C1", "C2", "C4"}),                  # with a reason, logged
    "ADMIN": frozenset(),                                        # never
}


def revealable_classes(role: str) -> FrozenSet[str]:
    return ROLE_REVEAL.get(str(role), frozenset())


def can_reveal_class(role: str, cls: Optional[str]) -> bool:
    return bool(cls) and cls in revealable_classes(role)


_BANDS = [(1_000, "under 1k"), (10_000, "1k to 10k"), (50_000, "10k to 50k"), (250_000, "50k to 250k"),
          (1_000_000, "250k to 1M")]


def amount_band(amount: Any, currency: Any = "") -> str:
    """Outside the zone the AI sees a band, not the exact amount."""
    try:
        a = abs(float(amount))
    except (TypeError, ValueError):
        return "unknown"
    ccy = str(currency or "").upper()
    for limit, label in _BANDS:
        if a < limit:
            return f"{label} {ccy}".strip()
    return f"over 1M {ccy}".strip()


_ITEM_RULES = [
    (("sanction", "screening", "watchlist", "pep", "adverse media", "disposition"), "C3"),
    (("payload", "kyc", "identity", "ubo", "beneficial", "date of birth", "passport", "tax id", "registry", "mandate", "signature"), "C1"),
    (("name", "iban", "account", "beneficiary", "creditor", "debtor", "address", "party", "customer record", "counterparty"), "C1"),
    (("invoice", "remittance", "instruction", "correspondence", "client reply", "document", "email", "note", "contract", "po "), "C2"),
]


def item_data_class(item_name: str) -> tuple:
    """(class or '', zone handling) for one evidence item of the matrix, from its name. Review with the bank's data owner."""
    n = str(item_name).lower()
    for words, cls in _ITEM_RULES:
        if any(w in n for w in words):
            how = {"C1": "Fetched and checked inside the zone; shown as a token; reveal on request (reason, logged)",
                   "C2": "Treated as an attachment; AI receives extracted fields only; reveal on request",
                   "C3": "Fetched and checked inside the zone; shown as a token; reveal for Compliance only"}[cls]
            return cls, how
    return "", "Not personal data; shown as is"
