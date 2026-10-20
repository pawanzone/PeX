"""Read and write the four case-management messages Swift Case Management uses, as XML.

  camt.110  Investigation request        camt.111  Investigation response
  camt.056  Payment cancellation request  camt.029  Resolution of investigation (answer to a cancellation request)

The structures follow the ISO 20022 messages closely (Document root with the message namespace, Assgnmt / Case / underlying
transaction blocks) but are SIMPLIFIED: they are not validated against the official XSDs, and the code lists below are PeX's working
subset. Replace the code lists and add schema validation when the bank supplies the schemas it was certified against.

Safety: input is size-limited and anything with a DOCTYPE or entity declaration is refused before parsing (no entity expansion).
"""
from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

OWN_BIC = "PEXBGB2L"                                   # this bank's BIC in the demo; the bank's own replaces it
MAX_BYTES = 100_000

NS = {
    "camt.110": "urn:iso:std:iso:20022:tech:xsd:camt.110.001.01",
    "camt.111": "urn:iso:std:iso:20022:tech:xsd:camt.111.001.01",
    "camt.056": "urn:iso:std:iso:20022:tech:xsd:camt.056.001.08",
    "camt.029": "urn:iso:std:iso:20022:tech:xsd:camt.029.001.09",
}
REQUESTS = ("camt.110", "camt.056")
RESPONSES = {"camt.110": "camt.111", "camt.056": "camt.029"}
TITLES = {"camt.110": "Investigation request", "camt.111": "Investigation response", "camt.056": "Cancellation request", "camt.029": "Cancellation answer"}

INV_REASONS = {"STAT": "Status of the payment", "CRDT": "Credit not received", "AMNT": "Amount differs", "INFO": "More information needed", "BENF": "Beneficiary details"}
INV_STATUS = {"ANSW": "Answered", "WIPG": "Work in progress", "RJCT": "Cannot investigate"}
RECALL_REASONS = {"DUPL": "Duplicate payment", "TECH": "Technical problem", "FRAD": "Suspected fraud", "AM09": "Wrong amount", "CUST": "Requested by the customer", "UPAY": "Undue payment"}
RECALL_REJECT = {"ARDT": "Already returned", "AC04": "Account closed", "CUST": "Customer declined", "LEGL": "Legal decision", "NOAS": "No answer from the beneficiary", "NOOR": "Original payment not received"}
RECALL_STATUS = {"CNCL": "Cancellation accepted", "RJCR": "Cancellation rejected"}
ANSWER_REASONS = {**RECALL_REASONS, **RECALL_REJECT}

REASONS = {"camt.110": INV_REASONS, "camt.056": RECALL_REASONS, "camt.029": ANSWER_REASONS, "camt.111": {}}
STATUSES = {"camt.111": INV_STATUS, "camt.029": RECALL_STATUS}

BIC_RE = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")
UETR_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-]{7,62}$")
UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
CCY_RE = re.compile(r"^[A-Z]{3}$")


class MessageError(Exception):
    def __init__(self, problems: List[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def is_standard_uetr(u: str) -> bool:
    return bool(UUID4_RE.match(str(u or "")))


def new_uetr() -> str:
    return str(uuid.uuid4())


# (root element, header kind). Paths are relative to the root element.
_PATHS = {
    "camt.110": {"root": "InvstgtnReq", "message_id": "Hdr/MsgId", "created_at": "Hdr/CreDtTm", "case_id": "Case/Id", "sender_bic": "Case/Cretr/Agt/FinInstnId/BICFI",
                 "receiver_bic": "Assgne/Agt/FinInstnId/BICFI", "uetr": "UndrlygTx/UETR", "end_to_end_id": "UndrlygTx/EndToEndId", "amount": "UndrlygTx/IntrBkSttlmAmt",
                 "settlement_date": "UndrlygTx/IntrBkSttlmDt", "reason_code": "Rsn/Cd", "narrative": "Nrtv"},
    "camt.111": {"root": "InvstgtnRspn", "message_id": "Hdr/MsgId", "created_at": "Hdr/CreDtTm", "case_id": "Case/Id", "sender_bic": "Case/Cretr/Agt/FinInstnId/BICFI",
                 "receiver_bic": "Assgne/Agt/FinInstnId/BICFI", "uetr": "UndrlygTx/UETR", "end_to_end_id": "UndrlygTx/EndToEndId", "amount": "UndrlygTx/IntrBkSttlmAmt",
                 "settlement_date": "UndrlygTx/IntrBkSttlmDt", "status_code": "Sts/Cd", "narrative": "Nrtv"},
    "camt.056": {"root": "FIToFIPmtCxlReq", "message_id": "Assgnmt/Id", "created_at": "Assgnmt/CreDtTm", "sender_bic": "Assgnmt/Assgnr/Agt/FinInstnId/BICFI",
                 "receiver_bic": "Assgnmt/Assgne/Agt/FinInstnId/BICFI", "case_id": "Case/Id", "uetr": "Undrlyg/TxInf/OrgnlUETR", "end_to_end_id": "Undrlyg/TxInf/OrgnlEndToEndId",
                 "amount": "Undrlyg/TxInf/OrgnlIntrBkSttlmAmt", "settlement_date": "Undrlyg/TxInf/OrgnlIntrBkSttlmDt", "reason_code": "Undrlyg/TxInf/CxlRsnInf/Rsn/Cd",
                 "narrative": "Undrlyg/TxInf/CxlRsnInf/AddtlInf"},
    "camt.029": {"root": "RsltnOfInvstgtn", "message_id": "Assgnmt/Id", "created_at": "Assgnmt/CreDtTm", "sender_bic": "Assgnmt/Assgnr/Agt/FinInstnId/BICFI",
                 "receiver_bic": "Assgnmt/Assgne/Agt/FinInstnId/BICFI", "case_id": "Case/Id", "status_code": "Sts/Conf", "uetr": "CxlDtls/TxInfAndSts/OrgnlUETR",
                 "end_to_end_id": "CxlDtls/TxInfAndSts/OrgnlEndToEndId", "amount": "CxlDtls/TxInfAndSts/OrgnlIntrBkSttlmAmt", "settlement_date": "CxlDtls/TxInfAndSts/OrgnlIntrBkSttlmDt",
                 "reason_code": "CxlDtls/TxInfAndSts/CxlStsRsnInf/Rsn/Cd", "narrative": "CxlDtls/TxInfAndSts/CxlStsRsnInf/AddtlInf"},
}
_REQUIRED = {"camt.110": ["message_id", "case_id", "uetr", "reason_code"], "camt.056": ["message_id", "case_id", "uetr", "reason_code"],
             "camt.111": ["message_id", "case_id", "uetr", "status_code"], "camt.029": ["message_id", "case_id", "uetr", "status_code"]}
_LABEL = {"message_id": "Message id", "case_id": "Case id", "uetr": "UETR", "reason_code": "Reason code", "status_code": "Status code", "amount": "Amount",
          "currency": "Currency", "sender_bic": "Sender BIC", "receiver_bic": "Receiver BIC"}


def _strip_ns(root: ET.Element) -> None:
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]


def _text(root: ET.Element, path: str) -> Optional[str]:
    el = root.find(path)
    if el is None or el.text is None:
        return None
    t = el.text.strip()
    return t or None


def kind_of_namespace(ns: str) -> Optional[str]:
    for k in NS:
        if k in ns:
            return k
    return None


def parse(xml: str) -> Dict[str, Any]:
    """Return the normalised fields of one message, or raise MessageError listing every problem found."""
    text = (xml or "").strip()
    if not text:
        raise MessageError(["The message is empty."])
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise MessageError(["The message is too large."])
    low = text.lower()
    if "<!doctype" in low or "<!entity" in low:
        raise MessageError(["DOCTYPE and entity declarations are not allowed in a message."])
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise MessageError([f"The message is not well-formed XML ({e})."])
    ns = root.tag.split("}", 1)[0][1:] if root.tag.startswith("{") else ""
    kind = kind_of_namespace(ns)
    if root.tag.split("}")[-1] != "Document" or not kind:
        raise MessageError([f"This is not a supported message type. Supported: {', '.join(NS)}."])
    _strip_ns(root)
    body = root.find(_PATHS[kind]["root"])
    if body is None:
        raise MessageError([f"The {kind} body element {_PATHS[kind]['root']} is missing."])
    out: Dict[str, Any] = {"msg_type": kind}
    for field, path in _PATHS[kind].items():
        if field != "root":
            out[field] = _text(body, path)
    amt_el = body.find(_PATHS[kind]["amount"])
    out["currency"] = (amt_el.get("Ccy") if amt_el is not None else None) or None
    problems: List[str] = []
    for f in _REQUIRED[kind]:
        if not out.get(f):
            problems.append(f"{_LABEL.get(f, f)} is missing.")
    for f in ("sender_bic", "receiver_bic"):
        v = out.get(f)
        if not v:
            problems.append(f"{_LABEL[f]} is missing.")
        elif not BIC_RE.match(v):
            problems.append(f"{_LABEL[f]} '{v}' is not a valid BIC.")
    if out.get("uetr") and not UETR_RE.match(out["uetr"]):
        problems.append(f"UETR '{out['uetr']}' is not in a valid format.")
    raw_amt = out.get("amount")
    if raw_amt is None:
        problems.append("Amount is missing.")
    else:
        try:
            a = float(raw_amt)
            if not a > 0 or a != a or a in (float("inf"),):
                raise ValueError
            out["amount"] = a
        except ValueError:
            problems.append(f"Amount '{raw_amt}' must be a positive number.")
    if not out.get("currency") or not CCY_RE.match(out["currency"] or ""):
        problems.append(f"Currency '{out.get('currency') or ''}' must be a 3-letter ISO 4217 code.")
    rc = out.get("reason_code")
    if rc and kind in ("camt.110", "camt.056", "camt.029") and rc not in REASONS[kind]:
        problems.append(f"Reason code '{rc}' is not recognised for {kind}.")
    sc = out.get("status_code")
    if sc and kind in STATUSES and sc not in STATUSES[kind]:
        problems.append(f"Status code '{sc}' is not recognised for {kind}.")
    if problems:
        raise MessageError(problems)
    return out


def _put(parent: ET.Element, path: str, value: Optional[str], attrs: Optional[Dict[str, str]] = None) -> None:
    if value is None or value == "":
        if not attrs:
            return
    el = parent
    for part in path.split("/"):
        nxt = el.find(part)
        if nxt is None:
            nxt = ET.SubElement(el, part)
        el = nxt
    if value is not None:
        el.text = str(value)
    for k, v in (attrs or {}).items():
        el.set(k, v)


def build(kind: str, **f: Any) -> str:
    """Make the XML for one message from normalised fields. Text is escaped by the XML writer."""
    if kind not in NS:
        raise MessageError([f"Cannot build {kind}."])
    doc = ET.Element("Document", {"xmlns": NS[kind]})
    body = ET.SubElement(doc, _PATHS[kind]["root"])
    amount = f.get("amount")
    for field, path in _PATHS[kind].items():
        if field in ("root", "amount"):
            continue
        _put(body, path, f.get(field))
    if amount not in (None, ""):
        try:
            shown = f"{float(amount):.2f}"
        except (TypeError, ValueError):
            shown = str(amount)                  # kept as given so a bad value can be tested; parse() refuses it
        _put(body, _PATHS[kind]["amount"], shown, {"Ccy": str(f.get("currency") or "")})
    _order(body, kind)
    ET.indent(doc, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(doc, encoding="unicode")


_ORDER = {
    "camt.110": ["Hdr", "Case", "Assgne", "UndrlygTx", "Rsn", "Nrtv"],
    "camt.111": ["Hdr", "Case", "Assgne", "UndrlygTx", "Sts", "Nrtv"],
    "camt.056": ["Assgnmt", "Case", "Undrlyg"],
    "camt.029": ["Assgnmt", "Sts", "Case", "CxlDtls"],
}


def _order(body: ET.Element, kind: str) -> None:
    rank = {n: i for i, n in enumerate(_ORDER[kind])}
    body[:] = sorted(list(body), key=lambda e: rank.get(e.tag, 99))


def label_for(kind: str, field: str, code: Optional[str]) -> str:
    """Plain words for a code, for screens."""
    if not code:
        return ""
    if field == "reason_code":
        return REASONS.get(kind, {}).get(code, code)
    return STATUSES.get(kind, {}).get(code, code)
