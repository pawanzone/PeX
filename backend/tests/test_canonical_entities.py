"""Canonical model v2: the entities profiles rely on (agents, charges, remittance, purpose, address, envelope, status, investigation,
mandate, screening alert) exist as real models, are filled from real ISO 20022 messages, and the logical model on the Admin screen is
computed from the code so it cannot overstate what exists.

  C1  The new models exist; old constructions still work; new payment fields default to None (golden tests unaffected).
  C2  A full pacs.008 yields agents (debtor, intermediaries, creditor with clearing member), charges, remittance, purpose, structured
      address, ultimate parties, envelope, amounts.
  C3  pacs.002 and pacs.004 yield status reports; camt.056 / camt.029 / camt.110 / camt.111 yield investigations.
  C4  Every pacs.008 in the e2e fixtures parses, and amount and currency agree with the fixture's payment_info.
  C5  The flat payment_info form fills the same entities.
  C6  The bank-event canonicalizer fills purpose, remittance and address when the bank supplies them.
  C7  Unsafe or broken input fails closed (DOCTYPE, empty, wrong type, bad amount); absent optional elements are None, never "".
  C8  The logical model lists every canonical class, marks each in code / database only / planned from the code itself, and links resolve.
"""
import json
from pathlib import Path

import pytest

from app.core.auth import create_token
from app.schemas import canonical as cn

FIX = Path(__file__).resolve().parents[1].parent / "e2e_fixtures"
if not FIX.exists():
    FIX = Path(__file__).resolve().parents[1] / "e2e_fixtures"

PACS008 = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"><FIToFICstmrCdtTrf>
<GrpHdr><MsgId>MSG-77</MsgId><CreDtTm>2026-11-05T09:30:00Z</CreDtTm><NbOfTxs>1</NbOfTxs>
 <SttlmInf><SttlmMtd>CLRG</SttlmMtd><ClrSys><Cd>CHAPS</Cd></ClrSys></SttlmInf>
 <InstgAgt><FinInstnId><BICFI>WESTGB2LXXX</BICFI></FinInstnId></InstgAgt>
 <InstdAgt><FinInstnId><BICFI>COBADEFFXXX</BICFI></FinInstnId></InstdAgt></GrpHdr>
<CdtTrfTxInf>
 <PmtId><InstrId>INSTR-1</InstrId><EndToEndId>E2E-1</EndToEndId><TxId>TX-1</TxId><UETR>dd11ee22-33ff-44aa-55bb-66cc77889900</UETR></PmtId>
 <PmtTpInf><SvcLvl><Cd>URGP</Cd></SvcLvl><LclInstrm><Cd>CHAPS</Cd></LclInstrm><CtgyPurp><Cd>SUPP</Cd></CtgyPurp></PmtTpInf>
 <IntrBkSttlmAmt Ccy="EUR">22000.00</IntrBkSttlmAmt><IntrBkSttlmDt>2026-11-06</IntrBkSttlmDt>
 <InstdAmt Ccy="USD">24000.00</InstdAmt><XchgRate>1.0909</XchgRate><ChrgBr>SHAR</ChrgBr>
 <ChrgsInf><Amt Ccy="EUR">15.00</Amt><Agt><FinInstnId><BICFI>CITIGB2LXXX</BICFI></FinInstnId></Agt></ChrgsInf>
 <IntrmyAgt1><FinInstnId><BICFI>CITIGB2LXXX</BICFI></FinInstnId></IntrmyAgt1>
 <IntrmyAgt2><FinInstnId><BICFI>DEUTDEFFXXX</BICFI></FinInstnId></IntrmyAgt2>
 <UltmtDbtr><Nm>Parent Holdings Plc</Nm></UltmtDbtr>
 <Dbtr><Nm>Originating Corp Inc</Nm><PstlAdr><Ctry>GB</Ctry></PstlAdr></Dbtr>
 <DbtrAcct><Id><IBAN>GB82WEST12345698765432</IBAN></Id><Ccy>EUR</Ccy></DbtrAcct>
 <DbtrAgt><FinInstnId><BICFI>WESTGB2LXXX</BICFI></FinInstnId></DbtrAgt>
 <CdtrAgt><FinInstnId><BICFI>COBADEFFXXX</BICFI><ClrSysMmbId><ClrSysId><Cd>DEBLZ</Cd></ClrSysId><MmbId>37040044</MmbId></ClrSysMmbId><Nm>Commerzbank AG</Nm></FinInstnId></CdtrAgt>
 <Cdtr><Nm>Bavarian Industrial AG</Nm><PstlAdr><StrtNm>Kaiserstrasse</StrtNm><BldgNb>16</BldgNb><PstCd>60311</PstCd><TwnNm>Frankfurt</TwnNm><Ctry>DE</Ctry></PstlAdr></Cdtr>
 <CdtrAcct><Id><IBAN>DE89370400440532013000</IBAN></Id></CdtrAcct>
 <UltmtCdtr><Nm>Bavarian Holding GmbH</Nm></UltmtCdtr>
 <InstrForNxtAgt><InstrInf>Pay on receipt of docs</InstrInf></InstrForNxtAgt>
 <Purp><Cd>SUPP</Cd></Purp>
 <RgltryRptg><Dtls><Cd>BOP100</Cd></Dtls></RgltryRptg>
 <RmtInf><Ustrd>Invoice 4410 October</Ustrd><Strd><CdtrRefInf><Tp><CdOrPrtry><Cd>SCOR</Cd></CdOrPrtry></Tp><Ref>RF18539007547034</Ref></CdtrRefInf></Strd></RmtInf>
</CdtTrfTxInf></FIToFICstmrCdtTrf></Document>"""

PACS002 = """<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.002.001.10"><FIToFIPmtStsRpt>
<GrpHdr><MsgId>ST-1</MsgId><CreDtTm>2026-11-05T10:00:00Z</CreDtTm></GrpHdr>
<TxInfAndSts><OrgnlUETR>dd11ee22-33ff-44aa-55bb-66cc77889900</OrgnlUETR><TxSts>RJCT</TxSts>
<StsRsnInf><Orgtr><Nm>Deutsche Bank</Nm></Orgtr><Rsn><Cd>AC04</Cd></Rsn><AddtlInf>Account closed</AddtlInf></StsRsnInf></TxInfAndSts></FIToFIPmtStsRpt></Document>"""

PACS004 = """<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.004.001.09"><PmtRtr>
<GrpHdr><MsgId>RT-1</MsgId><CreDtTm>2026-11-05T11:00:00Z</CreDtTm></GrpHdr>
<TxInf><OrgnlUETR>dd11ee22-33ff-44aa-55bb-66cc77889900</OrgnlUETR><RtrdIntrBkSttlmAmt Ccy="EUR">22000.00</RtrdIntrBkSttlmAmt>
<RtrRsnInf><Rsn><Cd>AC01</Cd></Rsn><AddtlInf>Incorrect account number</AddtlInf></RtrRsnInf></TxInf></PmtRtr></Document>"""


def parse():
    from app.services import iso_canonical as ic
    return ic


def test_c1_new_models_exist_and_old_payments_still_build():
    for name in ("CanonicalAgent", "ChargeInfo", "CanonicalCharges", "CanonicalRemittance", "CanonicalPurpose", "CanonicalPostalAddress",
                 "CanonicalEnvelope", "CanonicalStatusReport", "CanonicalInvestigation", "CanonicalMandate", "CanonicalScreeningAlert"):
        assert hasattr(cn, name), name
    p = cn.CanonicalPayment(payment_id="P", uetr="U", instruction_id="I", amount=1.0, currency="EUR", payment_rail="SWIFT",
                            debtor_party=cn.CanonicalParty(party_id="a", party_name="a", party_type="DEBTOR", country="GB"),
                            debtor_account=cn.CanonicalAccount(account_id="a", currency="EUR"),
                            creditor_party=cn.CanonicalParty(party_id="b", party_name="b", party_type="CREDITOR", country="DE"),
                            creditor_account=cn.CanonicalAccount(account_id="b", currency="EUR"), source_bank_id="BANK_A")
    d = p.model_dump()
    for f in ("debtor_agent", "creditor_agent", "intermediary_agents", "charges", "remittance", "purpose", "envelope", "ultimate_debtor", "ultimate_creditor"):
        assert f in d, f
    assert d["debtor_agent"] is None and d["charges"] is None and d["intermediary_agents"] == []


def test_c2_full_pacs008_fills_every_entity():
    r = parse().parse_pacs008(PACS008)
    p = r.payment
    assert (p.uetr, p.instruction_id, p.end_to_end_id, p.amount, p.currency, p.settlement_date) == ("dd11ee22-33ff-44aa-55bb-66cc77889900", "INSTR-1", "E2E-1", 22000.0, "EUR", "2026-11-06")
    assert p.debtor_agent.bic == "WESTGB2LXXX" and p.debtor_agent.role == "DEBTOR_AGENT"
    assert p.creditor_agent.bic == "COBADEFFXXX" and p.creditor_agent.clearing_system_id == "DEBLZ" and p.creditor_agent.member_id == "37040044" and p.creditor_agent.name == "Commerzbank AG"
    assert [a.bic for a in p.intermediary_agents] == ["CITIGB2LXXX", "DEUTDEFFXXX"] and [a.sequence for a in p.intermediary_agents] == [1, 2]
    assert p.charges.charge_bearer == "SHAR" and p.charges.items[0].amount == 15.0 and p.charges.items[0].agent_bic == "CITIGB2LXXX"
    assert p.charges.instructed_amount == 24000.0 and p.charges.instructed_currency == "USD" and p.charges.exchange_rate == 1.0909
    assert p.remittance.unstructured == ["Invoice 4410 October"] and p.remittance.structured_reference == "RF18539007547034" and p.remittance.reference_type == "SCOR"
    assert p.purpose.code == "SUPP" and p.purpose.category_code == "SUPP" and p.purpose.regulatory_codes == ["BOP100"]
    a = p.creditor_party.address
    assert (a.street, a.building, a.post_code, a.town, a.country) == ("Kaiserstrasse", "16", "60311", "Frankfurt", "DE")
    assert p.ultimate_debtor.party_name == "Parent Holdings Plc" and p.ultimate_debtor.party_type == "ULTIMATE_DEBTOR"
    assert p.ultimate_creditor.party_name == "Bavarian Holding GmbH" and p.ultimate_creditor.party_type == "ULTIMATE_CREDITOR"
    e = p.envelope
    assert (e.message_type, e.message_id, e.settlement_method, e.clearing_system, e.service_level, e.local_instrument) == ("pacs.008", "MSG-77", "CLRG", "CHAPS", "URGP", "CHAPS")
    assert e.instructing_agent_bic == "WESTGB2LXXX" and e.instructed_agent_bic == "COBADEFFXXX" and e.instructions_for_next_agent == ["Pay on receipt of docs"]
    assert r.problems == []


def test_c3_status_return_and_investigation_messages():
    ic = parse()
    s = ic.parse_status_message(PACS002)
    assert (s.message_type, s.status, s.reason_code, s.additional_info, s.originator, s.uetr) == ("pacs.002", "RJCT", "AC04", "Account closed", "Deutsche Bank", "dd11ee22-33ff-44aa-55bb-66cc77889900")
    r = ic.parse_status_message(PACS004)
    assert (r.message_type, r.kind, r.reason_code, r.returned_amount, r.currency) == ("pacs.004", "RETURN", "AC01", 22000.0, "EUR")
    from app.services.v2 import swift_msgs as sm
    xml = sm.build("camt.056", uetr="dd11ee22-33ff-44aa-55bb-66cc77889900", amount=22000.0, currency="EUR", sender_bic="WESTGB2LXXX", receiver_bic="COBADEFFXXX",
                   message_id="M-9", case_id="CASE-9", reason_code="DUPL", narrative="Duplicate")
    inv = ic.parse_investigation_message(xml)
    assert inv.message_type == "camt.056" and inv.kind == "RECALL" and inv.original_uetr == "dd11ee22-33ff-44aa-55bb-66cc77889900" and inv.reason_code == "DUPL"


def fixture_pairs():
    out = []
    for f in sorted(FIX.rglob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        rp = d.get("raw_payload") or (d.get("bank_supplied_evidence") or {}).get("RAW_PAYLOAD")
        txt = rp.get("raw_text") if isinstance(rp, dict) else None
        if txt and "pacs.008" in txt and isinstance(d.get("payment_info"), dict):
            out.append((f.name, txt, d["payment_info"]))
    return out


def test_c4_every_fixture_pacs008_parses_and_agrees_on_amount_and_currency():
    pairs = fixture_pairs()
    assert len(pairs) >= 10, "fixtures with real pacs.008 text expected"
    ic = parse()
    for name, txt, info in pairs:
        r = ic.parse_pacs008(txt)
        assert r.payment is not None, name
        if info.get("amount") is not None and r.payment.amount:
            assert r.payment.amount == float(info["amount"]), name
        if info.get("currency") and r.payment.amount:  # some fixtures are deliberately partial messages with no amount
            assert r.payment.currency == info["currency"], name


def test_c5_flat_payment_info_fills_agents_remittance_and_dates():
    ic = parse()
    x = ic.from_payment_info({"payment_id": "PMT-1", "uetr": "U-1", "amount": 10.5, "currency": "EUR", "clearing_rail": "SWIFT_CBPR+", "value_date": "2026-10-08",
                              "debtor_name": "A", "debtor_account": "GB82WEST12345678901234", "debtor_agent_bic": "WESTGB2LXXX",
                              "creditor_name": "B", "creditor_account": "DE89370400440532013000", "creditor_agent_bic": "COBADEFFXXX",
                              "remittance_info": "Invoice 1", "purpose_code": "SUPP", "charge_bearer": "SHAR"})
    assert x.debtor_agent.bic == "WESTGB2LXXX" and x.creditor_agent.bic == "COBADEFFXXX"
    assert x.remittance.unstructured == ["Invoice 1"] and x.purpose.code == "SUPP" and x.charges.charge_bearer == "SHAR" and x.settlement_date == "2026-10-08"
    bare = ic.from_payment_info({"payment_id": "P", "uetr": "U", "amount": 1, "currency": "EUR"})
    assert bare.debtor_agent is None and bare.remittance is None and bare.purpose is None and bare.charges is None


def test_c6_bank_event_canonicalizer_fills_purpose_remittance_address():
    from app.schemas.bank_events import RawBankEvent
    from app.services.canonicalizer import canonicalizer
    ev = RawBankEvent(event_id="E1", source_bank_id="BANK_A", event_type="PAYMENT_EXCEPTION", raw_payload={
        "payment_reference": "R1", "uetr": "U1", "amount": 100.0, "currency": "EUR", "debtor_name": "D", "debtor_account": "GB82WEST12345698765432",
        "creditor_name": "C", "creditor_iban": "DE89370400440532013000", "creditor_bic": "COBADEFF", "error_code": "X", "error_message": "m",
        "purpose_code": "SUPP", "remittance_info": "Inv 9", "creditor_address": {"street": "Kaiserstrasse", "building": "16", "post_code": "60311", "town": "Frankfurt", "country": "DE"}})
    pay, _ = canonicalizer.canonicalize_bank_event(ev)
    assert pay.purpose.code == "SUPP" and pay.remittance.unstructured == ["Inv 9"] and pay.creditor_party.address.town == "Frankfurt"
    assert pay.creditor_agent.bic == "COBADEFF"


@pytest.mark.parametrize("bad", ["", "   ", "<Document/>", "not xml",
                                 '<!DOCTYPE x [<!ENTITY a "b">]><Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"/>'])
def test_c7_unsafe_or_broken_input_fails_closed(bad):
    ic = parse()
    with pytest.raises(ic.CanonicalParseError):
        ic.parse_pacs008(bad)


def test_c7_bad_amount_is_reported_and_absent_elements_are_none():
    ic = parse()
    r = ic.parse_pacs008(PACS008.replace("22000.00", "-5"))
    assert any("amount" in p.lower() for p in r.problems)
    minimal = """<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"><FIToFICstmrCdtTrf><GrpHdr><MsgId>M</MsgId></GrpHdr><CdtTrfTxInf><PmtId><UETR>dd11ee22-33ff-44aa-55bb-66cc77889900</UETR></PmtId><IntrBkSttlmAmt Ccy="EUR">5.00</IntrBkSttlmAmt></CdtTrfTxInf></FIToFICstmrCdtTrf></Document>"""
    p = ic.parse_pacs008(minimal).payment
    assert p.charges is None and p.remittance is None and p.purpose is None and p.creditor_agent is None and p.intermediary_agents == []
    assert p.end_to_end_id is None and p.settlement_date is None


def H(uid="ADM-0002"):
    return {"Authorization": "Bearer " + create_token(uid)}


def test_c8_logical_model_is_computed_from_the_code(client):
    d = client.get("/api/v2/reference/data-model", headers=H()).json()
    lm = d["logical_model"]
    ents = {e["name"]: e for e in lm["entities"]}
    assert len(ents) >= 15 and set(lm["domains"]) >= {"Payment", "Parties and accounts", "Banks and routing", "Message and status", "Compliance", "PeX workflow"}
    for e in ents.values():
        assert e["status"] in ("in code", "database only", "planned") and e["description"] and e["domain"] in lm["domains"]
        if e["status"] == "in code":
            assert e["canonical_class"] and hasattr(cn, e["canonical_class"]) and e["fields"] > 0
        else:
            assert not e["canonical_class"] or not hasattr(cn, e["canonical_class"]) or e["status"] == "database only"
        for rel in e["links"]:
            assert rel["to"] in ents, (e["name"], rel)
    in_code = {e["canonical_class"] for e in ents.values() if e["canonical_class"]}
    for cls_name, obj in vars(cn).items():
        if isinstance(obj, type) and issubclass(obj, cn.BaseModel) and obj is not cn.BaseModel and obj.__module__ == cn.__name__:
            assert cls_name in in_code or cls_name in lm["supporting_classes"], f"{cls_name} not represented in the logical model"
    assert lm["summary"]["in_code"] + lm["summary"]["database_only"] + lm["summary"]["planned"] == len(ents)
    assert lm["summary"]["planned"] == 0 or all(e["status"] != "in code" for e in ents.values() if e["name"] in lm["planned_names"])
