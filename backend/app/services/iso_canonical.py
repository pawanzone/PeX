"""Fill the canonical model from real ISO 20022 messages (pacs.008, pacs.002, pacs.004, camt.056/029/110/111) and from the flat
payment_info form the profile pipeline uses.

Safety: input is size-limited and anything with a DOCTYPE or entity declaration is refused before parsing. Absent optional elements
become None (never an empty string). Problems that do not stop a payment being read (a bad amount, a missing name) are returned in
`problems` so the case can show them.
"""
from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.schemas.canonical import (
    CanonicalAccount, CanonicalAgent, CanonicalBankOutcome, CanonicalRoutingEntry, CanonicalCharges, CanonicalEnvelope, CanonicalInvestigation, CanonicalParty, CanonicalPayment,
    CanonicalPostalAddress, CanonicalPurpose, CanonicalRemittance, CanonicalStatusReport, ChargeInfo,
)

MAX_BYTES = 500_000


class CanonicalParseError(Exception):
    def __init__(self, problems):
        problems = [problems] if isinstance(problems, str) else list(problems)
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass
class ParsedPayment:
    payment: CanonicalPayment
    problems: List[str] = field(default_factory=list)


def _root(xml: str) -> ET.Element:
    text = (xml or "").strip()
    if not text:
        raise CanonicalParseError("The message is empty.")
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise CanonicalParseError("The message is too large.")
    low = text.lower()
    if "<!doctype" in low or "<!entity" in low:
        raise CanonicalParseError("DOCTYPE and entity declarations are not allowed in a message.")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise CanonicalParseError(f"The message is not well-formed XML ({e}).")
    ns = root.tag.split("}", 1)[0][1:] if root.tag.startswith("{") else ""
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    if root.tag != "Document":
        raise CanonicalParseError("This is not an ISO 20022 message (no Document root).")
    root.set("_ns", ns)
    return root


def _msg_type(root: ET.Element) -> Optional[str]:
    m = re.search(r"(pacs|camt|pain)\.(\d{3})", root.get("_ns", ""))
    return f"{m.group(1)}.{m.group(2)}" if m else None


def _t(el: Optional[ET.Element], path: str) -> Optional[str]:
    if el is None:
        return None
    n = el.find(path)
    if n is None or n.text is None:
        return None
    v = n.text.strip()
    return v or None


def _amt(el: Optional[ET.Element], path: str, problems: List[str], label: str):
    """(value, currency) of an amount element; records a problem for a non-numeric or non-positive value."""
    n = el.find(path) if el is not None else None
    if n is None or not (n.text or "").strip():
        return None, None
    try:
        v = float(n.text.strip())
    except ValueError:
        problems.append(f"The {label} amount is not a number.")
        return None, n.get("Ccy")
    if v <= 0:
        problems.append(f"The {label} amount must be greater than zero.")
        return None, n.get("Ccy")
    return v, n.get("Ccy")


def _agent(el: Optional[ET.Element], role: str, sequence: Optional[int] = None) -> Optional[CanonicalAgent]:
    if el is None:
        return None
    fi = el.find("FinInstnId")
    if fi is None:
        return None
    a = CanonicalAgent(role=role, bic=_t(fi, "BICFI") or _t(fi, "BIC"), name=_t(fi, "Nm"), clearing_system_id=_t(fi, "ClrSysMmbId/ClrSysId/Cd"),
                       member_id=_t(fi, "ClrSysMmbId/MmbId"), lei=_t(fi, "LEI"), sequence=sequence)
    return a if any([a.bic, a.name, a.clearing_system_id, a.member_id, a.lei]) else None


def _address(el: Optional[ET.Element]) -> Optional[CanonicalPostalAddress]:
    n = el.find("PstlAdr") if el is not None else None
    if n is None:
        return None
    lines = [x.text.strip() for x in n.findall("AdrLine") if x.text and x.text.strip()]
    a = CanonicalPostalAddress(street=_t(n, "StrtNm"), building=_t(n, "BldgNb"), post_code=_t(n, "PstCd"), town=_t(n, "TwnNm"),
                               country_sub_division=_t(n, "CtrySubDvsn"), country=_t(n, "Ctry"), address_lines=lines)
    return a if any([a.street, a.building, a.post_code, a.town, a.country_sub_division, a.country, a.address_lines]) else None


def _country_of(account_id: Optional[str], bic: Optional[str], addr: Optional[CanonicalPostalAddress]) -> str:
    if addr and addr.country:
        return addr.country
    if account_id and re.match(r"^[A-Z]{2}\d{2}", account_id):
        return account_id[:2]
    if bic and len(bic) >= 6:
        return bic[4:6]
    return "ZZ"


def _party(el: Optional[ET.Element], role: str, account_id: Optional[str], bic: Optional[str], problems: List[str], required: bool = True) -> Optional[CanonicalParty]:
    if el is None:
        if not required:
            return None
        problems.append(f"The {role.lower()} is missing.")
        return CanonicalParty(party_id=f"PARTY-{role}-{uuid.uuid4().hex[:4]}", party_name="Unknown", party_type=role, country=_country_of(account_id, bic, None))
    name = _t(el, "Nm")
    addr = _address(el)
    if not name:
        problems.append(f"The {role.lower()} name is missing.")
    return CanonicalParty(party_id=f"PARTY-{role}-{uuid.uuid4().hex[:4]}", party_name=name or "Unknown", party_type=role,
                          country=_country_of(account_id, bic, addr), address=addr)


def _account(el: Optional[ET.Element], currency: str, bic: Optional[str]) -> CanonicalAccount:
    iban = _t(el, "Id/IBAN")
    other = _t(el, "Id/Othr/Id")
    return CanonicalAccount(account_id=f"ACC-{uuid.uuid4().hex[:6]}", account_number=other or (iban[-8:] if iban else None), iban=iban,
                            currency=_t(el, "Ccy") or currency, bank_bic=bic)


def parse_pacs008(xml: str) -> ParsedPayment:
    root = _root(xml)
    if _msg_type(root) != "pacs.008":
        raise CanonicalParseError("This is not a pacs.008 message.")
    body = root.find("FIToFICstmrCdtTrf")
    tx = body.find("CdtTrfTxInf") if body is not None else None
    if body is None or tx is None:
        raise CanonicalParseError("The pacs.008 body (FIToFICstmrCdtTrf / CdtTrfTxInf) is missing.")
    problems: List[str] = []
    hdr = body.find("GrpHdr")

    uetr = _t(tx, "PmtId/UETR")
    if not uetr:
        problems.append("The UETR is missing.")
    amount, ccy = _amt(tx, "IntrBkSttlmAmt", problems, "settlement")
    if amount is None and ccy is None:
        problems.append("The settlement amount is missing.")
    ccy = ccy or "XXX"

    dbtr_agt = _agent(tx.find("DbtrAgt"), "DEBTOR_AGENT")
    cdtr_agt = _agent(tx.find("CdtrAgt"), "CREDITOR_AGENT")
    inter = [a for a in (_agent(tx.find(f"IntrmyAgt{i}"), "INTERMEDIARY", i) for i in (1, 2, 3)) if a]
    dbtr_iban = _t(tx, "DbtrAcct/Id/IBAN")
    cdtr_iban = _t(tx, "CdtrAcct/Id/IBAN")

    debtor = _party(tx.find("Dbtr"), "DEBTOR", dbtr_iban, dbtr_agt.bic if dbtr_agt else None, problems)
    creditor = _party(tx.find("Cdtr"), "CREDITOR", cdtr_iban, cdtr_agt.bic if cdtr_agt else None, problems)
    ult_d = _party(tx.find("UltmtDbtr"), "ULTIMATE_DEBTOR", None, None, problems, required=False)
    ult_c = _party(tx.find("UltmtCdtr"), "ULTIMATE_CREDITOR", None, None, problems, required=False)

    charges = None
    inst_amt, inst_ccy = _amt(tx, "InstdAmt", problems, "instructed")
    rate = None
    if _t(tx, "XchgRate"):
        try:
            rate = float(_t(tx, "XchgRate"))
        except ValueError:
            problems.append("The exchange rate is not a number.")
    items = []
    for c in tx.findall("ChrgsInf"):
        v, cc = _amt(c, "Amt", problems, "charge")
        if v is not None and cc:
            a = _agent(c.find("Agt"), "INTERMEDIARY")
            items.append(ChargeInfo(amount=v, currency=cc, agent_bic=a.bic if a else None))
    bearer = _t(tx, "ChrgBr")
    if bearer or items or inst_amt or rate:
        charges = CanonicalCharges(charge_bearer=bearer, items=items, instructed_amount=inst_amt, instructed_currency=inst_ccy, exchange_rate=rate)

    remittance = None
    ustrd = [u.text.strip() for u in tx.findall("RmtInf/Ustrd") if u.text and u.text.strip()]
    ref = _t(tx, "RmtInf/Strd/CdtrRefInf/Ref")
    rtype = _t(tx, "RmtInf/Strd/CdtrRefInf/Tp/CdOrPrtry/Cd")
    if ustrd or ref:
        remittance = CanonicalRemittance(unstructured=ustrd, structured_reference=ref, reference_type=rtype)

    purpose = None
    reg = [d.text.strip() for d in tx.findall("RgltryRptg/Dtls/Cd") if d.text and d.text.strip()]
    pcode, ccode = _t(tx, "Purp/Cd"), _t(tx, "PmtTpInf/CtgyPurp/Cd")
    if pcode or ccode or reg:
        purpose = CanonicalPurpose(code=pcode, category_code=ccode, regulatory_codes=reg)

    env = CanonicalEnvelope(
        message_type="pacs.008", message_id=_t(hdr, "MsgId"), created_at=_t(hdr, "CreDtTm"),
        number_of_transactions=int(_t(hdr, "NbOfTxs")) if (_t(hdr, "NbOfTxs") or "").isdigit() else None,
        settlement_method=_t(hdr, "SttlmInf/SttlmMtd"), clearing_system=_t(hdr, "SttlmInf/ClrSys/Cd"),
        service_level=_t(tx, "PmtTpInf/SvcLvl/Cd"), local_instrument=_t(tx, "PmtTpInf/LclInstrm/Cd"),
        instructing_agent_bic=_t(hdr, "InstgAgt/FinInstnId/BICFI"), instructed_agent_bic=_t(hdr, "InstdAgt/FinInstnId/BICFI"),
        instructions_for_next_agent=[i.text.strip() for i in tx.findall("InstrForNxtAgt/InstrInf") if i.text and i.text.strip()])

    pay = CanonicalPayment(
        payment_id=_t(tx, "PmtId/TxId") or uetr or f"PMT-{uuid.uuid4().hex[:8].upper()}", uetr=uetr or "", instruction_id=_t(tx, "PmtId/InstrId") or _t(tx, "PmtId/TxId") or _t(hdr, "MsgId") or "",
        end_to_end_id=_t(tx, "PmtId/EndToEndId"), amount=amount or 0.0, currency=ccy, payment_rail=env.clearing_system or "SWIFT",
        debtor_party=debtor, debtor_account=_account(tx.find("DbtrAcct"), ccy, dbtr_agt.bic if dbtr_agt else None),
        creditor_party=creditor, creditor_account=_account(tx.find("CdtrAcct"), ccy, cdtr_agt.bic if cdtr_agt else None),
        settlement_date=_t(tx, "IntrBkSttlmDt"), source_bank_id="ISO20022", debtor_agent=dbtr_agt, creditor_agent=cdtr_agt, intermediary_agents=inter,
        ultimate_debtor=ult_d, ultimate_creditor=ult_c, charges=charges, remittance=remittance, purpose=purpose, envelope=env)
    return ParsedPayment(pay, problems)


def parse_status_message(xml: str) -> CanonicalStatusReport:
    root = _root(xml)
    mt = _msg_type(root)
    if mt == "pacs.002":
        b = root.find("FIToFIPmtStsRpt")
        t = b.find("TxInfAndSts") if b is not None else None
        if b is None or t is None:
            raise CanonicalParseError("The pacs.002 body is missing.")
        return CanonicalStatusReport(message_type=mt, message_id=_t(b, "GrpHdr/MsgId"), kind="STATUS", uetr=_t(t, "OrgnlUETR"), status=_t(t, "TxSts"),
                                     reason_code=_t(t, "StsRsnInf/Rsn/Cd"), additional_info=_t(t, "StsRsnInf/AddtlInf"), originator=_t(t, "StsRsnInf/Orgtr/Nm"))
    if mt == "pacs.004":
        b = root.find("PmtRtr")
        t = b.find("TxInf") if b is not None else None
        if b is None or t is None:
            raise CanonicalParseError("The pacs.004 body is missing.")
        probs: List[str] = []
        v, c = _amt(t, "RtrdIntrBkSttlmAmt", probs, "returned")
        return CanonicalStatusReport(message_type=mt, message_id=_t(b, "GrpHdr/MsgId"), kind="RETURN", uetr=_t(t, "OrgnlUETR"), status="RTRN",
                                     reason_code=_t(t, "RtrRsnInf/Rsn/Cd"), additional_info=_t(t, "RtrRsnInf/AddtlInf"), originator=_t(t, "RtrRsnInf/Orgtr/Nm"),
                                     returned_amount=v, currency=c)
    raise CanonicalParseError("This is not a pacs.002 or pacs.004 message.")


_INV_KIND = {"camt.056": "RECALL", "camt.029": "RECALL_ANSWER", "camt.110": "INVESTIGATION", "camt.111": "INVESTIGATION_ANSWER"}


def parse_investigation_message(xml: str) -> CanonicalInvestigation:
    from app.services.v2 import swift_msgs as sm
    try:
        f = sm.parse(xml)
    except sm.MessageError as e:
        raise CanonicalParseError(e.problems)
    amount = None
    try:
        amount = float(f["amount"]) if f.get("amount") else None
    except ValueError:
        pass
    return CanonicalInvestigation(message_type=f["msg_type"], message_id=f.get("message_id"), kind=_INV_KIND[f["msg_type"]], case_id=f.get("case_id"),
                                  original_uetr=f.get("uetr"), reason_code=f.get("reason_code"), status_code=f.get("status_code"),
                                  narrative=f.get("narrative"), amount=amount, currency=f.get("currency"))


def from_payment_info(info: Dict[str, Any]) -> CanonicalPayment:
    """Map the flat payment_info dict used by the profile pipeline onto the canonical entities."""
    def s(k):
        v = info.get(k)
        return str(v).strip() if v not in (None, "") else None
    dba = CanonicalAgent(role="DEBTOR_AGENT", bic=s("debtor_agent_bic")) if s("debtor_agent_bic") else None
    cda = CanonicalAgent(role="CREDITOR_AGENT", bic=s("creditor_agent_bic")) if s("creditor_agent_bic") else None
    ccy = s("currency") or "XXX"
    remit = CanonicalRemittance(unstructured=[s("remittance_info")]) if s("remittance_info") else None
    purpose = CanonicalPurpose(code=s("purpose_code")) if s("purpose_code") else None
    charges = CanonicalCharges(charge_bearer=s("charge_bearer")) if s("charge_bearer") else None
    d_acc, c_acc = s("debtor_account"), s("creditor_account")
    return CanonicalPayment(
        payment_id=s("payment_id") or f"PMT-{uuid.uuid4().hex[:8].upper()}", uetr=s("uetr") or "", instruction_id=s("instruction_id") or s("payment_id") or "",
        end_to_end_id=s("end_to_end_id"), amount=float(info.get("amount") or 0), currency=ccy, payment_rail=s("clearing_rail") or "SWIFT",
        debtor_party=CanonicalParty(party_id=f"PARTY-DEBTOR-{uuid.uuid4().hex[:4]}", party_name=s("debtor_name") or "Unknown", party_type="DEBTOR", country=_country_of(d_acc, s("debtor_agent_bic"), None)),
        debtor_account=CanonicalAccount(account_id=f"ACC-{uuid.uuid4().hex[:6]}", account_number=d_acc, iban=d_acc if d_acc and re.match(r"^[A-Z]{2}\d{2}", d_acc) else None, currency=ccy, bank_bic=s("debtor_agent_bic")),
        creditor_party=CanonicalParty(party_id=f"PARTY-CREDITOR-{uuid.uuid4().hex[:4]}", party_name=s("creditor_name") or "Unknown", party_type="CREDITOR", country=_country_of(c_acc, s("creditor_agent_bic"), None)),
        creditor_account=CanonicalAccount(account_id=f"ACC-{uuid.uuid4().hex[:6]}", account_number=c_acc, iban=c_acc if c_acc and re.match(r"^[A-Z]{2}\d{2}", c_acc) else None, currency=ccy, bank_bic=s("creditor_agent_bic")),
        settlement_date=s("value_date"), source_bank_id=s("source_bank_id") or "PROFILE_PIPELINE",
        debtor_agent=dba, creditor_agent=cda, remittance=remit, purpose=purpose, charges=charges)


# ---- bank outcome ----------------------------------------------------------------------------------------------------
OUTCOMES = ("SETTLED", "EXECUTED_CONFIRMED", "REJECTED", "FAILED")
# pacs.002 TxSts -> the outcome PeX records. Anything not listed (pending, unknown, empty) yields no outcome: fail closed.
_STATUS_TO_OUTCOME = {"ACSC": "SETTLED", "ACCC": "SETTLED", "ACSP": "EXECUTED_CONFIRMED", "RJCT": "REJECTED"}


def bank_outcome_from_status(report: CanonicalStatusReport, case_id: str, bank_reference: str, clearing_system: Optional[str] = None,
                             received_at: Optional[str] = None) -> Optional[CanonicalBankOutcome]:
    """Map a pacs.002 status report to a bank outcome, or None when the status is not a final or acknowledged result.
    A parsed message is not a verified callback, so signature_verified stays False."""
    if report.message_type != "pacs.002" or report.status not in _STATUS_TO_OUTCOME:
        return None
    outcome = _STATUS_TO_OUTCOME[report.status]
    from datetime import datetime, timezone
    return CanonicalBankOutcome(idempotency_key=f"IDEMP-BANK-{case_id}-{bank_reference}-{outcome}", case_id=case_id, outcome=outcome, bank_reference=bank_reference,
                                clearing_system=clearing_system, received_at=received_at or datetime.now(timezone.utc).isoformat(), signature_verified=False,
                                uetr=report.uetr, status_code=report.status, reason_code=report.reason_code, originator=report.originator)


def bank_outcome_from_row(row: Dict[str, Any]) -> CanonicalBankOutcome:
    """Load a stored bank_outcomes row (a dict of its columns) into the canonical model."""
    return CanonicalBankOutcome(**{k: row[k] for k in CanonicalBankOutcome.model_fields if k in row and row[k] is not None})


def bank_outcome_from_callback(payload: Dict[str, Any], signature_verified: bool, received_at: Optional[str] = None) -> CanonicalBankOutcome:
    """Build the model from a bank callback payload (same keys as the /bank/outcome request). Raises ValueError for an unknown outcome."""
    outcome = str(payload.get("outcome") or "").upper().strip()
    if outcome not in OUTCOMES:
        raise ValueError(f"Invalid bank outcome '{payload.get('outcome')}'")
    ref = str(payload.get("bank_reference") or "")
    case_id = str(payload.get("case_id") or "")
    from datetime import datetime, timezone
    return CanonicalBankOutcome(idempotency_key=payload.get("idempotency_key") or f"IDEMP-BANK-{case_id}-{ref}-{outcome}", case_id=case_id, outcome=outcome,
                                bank_reference=ref, clearing_system=payload.get("clearing_system"),
                                received_at=received_at or payload.get("settlement_timestamp") or datetime.now(timezone.utc).isoformat(),
                                signature_verified=signature_verified, uetr=payload.get("uetr"), reason_code=payload.get("reason"))


# ---- routing directory ------------------------------------------------------------------------------------------------
def _iso(v: Any) -> Optional[str]:
    return v.isoformat() if hasattr(v, "isoformat") else (str(v) if v else None)


def routing_entry_from_bic_reference(ref: Any) -> CanonicalRoutingEntry:
    """Load a BIC reference directory entry (the DQ-02 BICReferenceEntry) into the canonical model."""
    status = getattr(ref.status, "value", ref.status)
    return CanonicalRoutingEntry(bic=ref.bic_code, institution_name=ref.institution_name, country=ref.country_code, status=str(status), is_head_office=ref.is_head_office,
                                 successor_bics=list(ref.successor_bics), supported_rails=list(ref.supported_rails), source=ref.provider,
                                 retrieved_at=_iso(ref.retrieved_at), effective_at=_iso(ref.effective_at), expires_at=_iso(ref.expires_at))


def routing_entry_from_identifier(member_id: str, clearing_system_id: str, institution_name: Optional[str] = None, country: Optional[str] = None,
                                  source: Optional[str] = None, status: str = "UNKNOWN", **dates: Optional[str]) -> CanonicalRoutingEntry:
    """Build an entry for a clearing member or routing number (the DQ-08 routing directory)."""
    return CanonicalRoutingEntry(member_id=member_id, clearing_system_id=clearing_system_id, institution_name=institution_name, country=country, status=status,
                                 source=source, retrieved_at=dates.get("retrieved_at"), effective_at=dates.get("effective_at"), expires_at=dates.get("expires_at"))


def routing_entry_is_current(entry: CanonicalRoutingEntry, now: Optional[Any] = None) -> bool:
    """True only when the entry has a readable expiry date that has not passed. No date, or an unreadable one, counts as not current."""
    from datetime import datetime, timezone
    if not entry.expires_at:
        return False
    try:
        exp = datetime.fromisoformat(entry.expires_at)
    except ValueError:
        return False
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) <= exp


def find_routing_entry(agent: CanonicalAgent, entries: List[CanonicalRoutingEntry]) -> Optional[CanonicalRoutingEntry]:
    """Find the directory entry for a bank in a payment: by BIC (first 8 characters decide the institution) or by clearing member id."""
    for e in entries:
        if agent.bic and e.bic and agent.bic[:8].upper() == e.bic[:8].upper():
            return e
        if agent.member_id and e.member_id and agent.member_id == e.member_id and (not agent.clearing_system_id or not e.clearing_system_id or agent.clearing_system_id == e.clearing_system_id):
            return e
    return None
