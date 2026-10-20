"""Network cases (camt.110/111 investigations, camt.056/029 recalls): acceptance tests written from the requirements.

Requirements (product owner, with Swift Case Management dates in mind)
  R1  PeX reads real XML for camt.110, camt.111, camt.056, camt.029; bad, unknown or unsafe messages are refused with reasons.
  R2  Every network case is tied to the payment by UETR; a message for a payment we do not hold is flagged, not lost.
  R3  Investigations both ways: answer a request we receive, raise one ourselves and read the reply.
  R4  Recalls both ways: decide a request we receive, raise one ourselves and read the answer.
  R5  A person drafts, a different approver authorises; payments at or above the dual-authorisation amount need two approvers.
  R6  PeX never moves money: accepting a recall only asks the bank system to return funds, and a person records the bank's confirmation.
  R7  Due time comes from policy; overdue cases are flagged.
  R8  Every step is in the audit trail; Audit and Risk can read but not write; Admin and Policy Owner have no access.
  R9  Everyone who works cases finds Network cases in the menu.

Run:  DATABASE_URL=sqlite:////tmp/net.db python3 -m pytest tests/test_network_cases.py -q
"""
import uuid
from datetime import timedelta

import pytest

from app.core.auth import create_token
from app.services.data_loader import repo
from app.services.v2 import seed as v2seed
from app.services.v2 import swift_msgs as sm
from app.services.v2.core import iso, now

MAKER, SUP, APPR, RSK, CMP, AUD, ADM, POL = "OP-9012", "SUP-2001", "APR-3192", "RSK-7714", "CMP-6001", "AUD-5001", "ADM-0002", "POL-8001"
CASE = "PEX-INV-0001"
BIG = "PEX-BEN-0050"


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def seeded():
    v2seed.seed_v2()
    from app.services.v2 import network as nw
    from app.services.v2 import policy
    policy.reset_all()
    nw.reset_all()
    yield
    policy.reset_all()


def uetr_of(cid=CASE):
    return repo.get_case(cid)["uetr"]


def msg(kind, **o):
    base = dict(message_id="M-" + uuid.uuid4().hex[:10], created_at="2026-10-20T08:00:00Z", case_id="CNT-" + uuid.uuid4().hex[:6], sender_bic="CNTPDEFF",
                receiver_bic=sm.OWN_BIC, uetr=uetr_of(), end_to_end_id="E2E-1", amount="1250.00", currency="EUR", settlement_date="2026-10-19",
                reason_code="CRDT" if kind == "camt.110" else "DUPL", narrative="Please check")
    base.update(o)
    return sm.build(kind, **base)


def receive(xml, uid=MAKER):
    return client_.post("/api/v2/network/inbound", json={"xml": xml}, headers=H(uid))


@pytest.fixture(autouse=True)
def _client(client):
    global client_
    client_ = client


def get(nid, uid=SUP):
    r = client_.get(f"/api/v2/network/cases/{nid}", headers=H(uid))
    assert r.status_code == 200, r.text
    return r.json()


def post(path, body=None, uid=MAKER):
    return client_.post(f"/api/v2/network/{path}", json=body or {}, headers=H(uid))


def inbound(kind="camt.110", **o):
    r = receive(msg(kind, **o))
    assert r.status_code == 201, r.text
    return r.json()


# R1 ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("kind", ["camt.110", "camt.111", "camt.056", "camt.029"])
def test_codec_round_trip(kind):
    f = dict(message_id="M1", created_at="2026-10-20T08:00:00Z", case_id="C-1", sender_bic="CNTPDEFF", receiver_bic=sm.OWN_BIC, uetr=str(uuid.uuid4()),
             end_to_end_id="E2E", amount="10.50", currency="USD", settlement_date="2026-10-19", reason_code={"camt.110": "STAT", "camt.111": None, "camt.056": "DUPL", "camt.029": "ARDT"}[kind], narrative="a < b & c", status_code="ANSW" if kind == "camt.111" else "CNCL")
    p = sm.parse(sm.build(kind, **f))
    assert p["msg_type"] == kind
    for k in ("message_id", "case_id", "sender_bic", "receiver_bic", "uetr", "currency"):
        assert p[k] == f[k], k
    assert p["amount"] == 10.5
    assert p["narrative"] == "a < b & c"


def test_hand_written_camt110_is_understood():
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.110.001.01"><InvstgtnReq>
<Hdr><MsgId>HW-1</MsgId><CreDtTm>2026-10-20T08:00:00Z</CreDtTm></Hdr>
<Case><Id>CNT-77</Id><Cretr><Agt><FinInstnId><BICFI>CNTPDEFF</BICFI></FinInstnId></Agt></Cretr></Case>
<Assgne><Agt><FinInstnId><BICFI>{sm.OWN_BIC}</BICFI></FinInstnId></Agt></Assgne>
<UndrlygTx><UETR>{uetr_of()}</UETR><EndToEndId>E2E-9</EndToEndId><IntrBkSttlmAmt Ccy="EUR">99.00</IntrBkSttlmAmt><IntrBkSttlmDt>2026-10-19</IntrBkSttlmDt></UndrlygTx>
<Rsn><Cd>STAT</Cd></Rsn><Nrtv>Where is it?</Nrtv></InvstgtnReq></Document>"""
    r = receive(xml)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["kind"] == "INVESTIGATION" and d["direction"] == "INBOUND" and d["counterparty_bic"] == "CNTPDEFF" and d["amount"] == 99.0 and d["reason_code"] == "STAT"


BAD = {
    "not-xml": (lambda: "<not xml", "well-formed"),
    "empty": (lambda: "", "empty"),
    "wrong-type": (lambda: msg("camt.110").replace("camt.110.001.01", "pacs.008.001.08"), "supported"),
    "no-uetr": (lambda: msg("camt.110").replace(uetr_of(), ""), "UETR"),
    "negative": (lambda: msg("camt.110", amount="-5"), "amount"),
    "not-number": (lambda: msg("camt.110", amount="abc"), "amount"),
    "currency": (lambda: msg("camt.110", currency="EURO"), "currency"),
    "reason": (lambda: msg("camt.110", reason_code="ZZZZ"), "reason"),
    "bic": (lambda: msg("camt.110", sender_bic="x"), "BIC"),
}


@pytest.mark.parametrize("name", list(BAD))
def test_bad_messages_are_refused_with_a_reason(name):
    build, why = BAD[name]
    r = receive(build())
    assert r.status_code == 422, r.text
    j = r.json()
    assert j["error"]["code"] == "INVALID_MESSAGE"
    assert why.lower() in " ".join(j.get("problems", []) + [j["error"]["message"]]).lower()


def test_doctype_and_entities_are_refused():
    evil = '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY x "boom">]>' + msg("camt.110")
    r = receive(evil)
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_MESSAGE"


def test_a_message_we_are_not_the_receiver_of_is_refused():
    r = receive(msg("camt.110", receiver_bic="OTHRUS33"))
    assert r.status_code == 422 and "receiver" in " ".join(r.json()["problems"]).lower()


def test_same_message_id_twice_is_a_conflict():
    x = msg("camt.110", message_id="DUP-1")
    assert receive(x).status_code == 201
    r = receive(x)
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_MESSAGE"


def test_responses_are_not_inbound_requests():
    r = receive(msg("camt.111", status_code="ANSW"))
    assert r.status_code == 422 and "request" in " ".join(r.json()["problems"]).lower()


# R2 ------------------------------------------------------------------------------------------------------------
def test_linked_to_the_payment_case_by_uetr():
    d = inbound()
    assert d["linked_case"]["case_id"] == CASE and d["linked_case"]["link"] == f"/cases/{CASE}"


def test_unknown_uetr_is_kept_and_flagged():
    d = inbound(uetr=str(uuid.uuid4()))
    assert d["linked_case"] is None and d["uetr_standard"] is True
    assert any("no matching" in w.lower() for w in d["warnings"])


def test_demo_style_uetr_is_accepted_but_marked_non_standard():
    d = inbound()
    assert d["uetr_standard"] is False


def test_open_recall_for_the_same_payment_is_warned():
    inbound("camt.056")
    d = inbound("camt.056")
    assert any("already" in w.lower() for w in d["warnings"])


# R3 ------------------------------------------------------------------------------------------------------------
def test_inbound_investigation_is_answered_after_a_different_person_authorises():
    d = inbound(uetr=str(uuid.uuid4()), amount="500.00")
    nid = d["id"]
    assert d["status"] == "NEW" and d["actions"]["can_draft"] is True
    r = post(f"cases/{nid}/draft", {"outcome": "ANSW", "text": "Credited to the beneficiary on 19 Oct."}, MAKER)
    assert r.status_code == 200 and r.json()["status"] == "DRAFTED"
    assert post(f"cases/{nid}/authorise", {}, MAKER).status_code == 403                      # drafter cannot authorise
    assert post(f"cases/{nid}/authorise", {}, SUP).status_code == 403                        # not an approver
    ok = post(f"cases/{nid}/authorise", {"note": "Checked"}, APPR)
    assert ok.status_code == 200, ok.text
    j = ok.json()
    assert j["status"] == "SENT" and j["response"]["msg_type"] == "camt.111"
    p = sm.parse(j["response"]["xml"])
    assert p["msg_type"] == "camt.111" and p["status_code"] == "ANSW" and p["case_id"] == d["case_ref"] and p["receiver_bic"] == "CNTPDEFF"
    assert j["money_moved"] is False


def test_answer_needs_text_and_a_valid_outcome():
    nid = inbound(uetr=str(uuid.uuid4()))["id"]
    assert post(f"cases/{nid}/draft", {"outcome": "NOPE", "text": "x"}).status_code == 422
    assert post(f"cases/{nid}/draft", {"outcome": "ANSW", "text": ""}).status_code == 422


def test_outbound_investigation_goes_out_at_once_and_the_reply_is_read():
    r = post("outbound", {"kind": "INVESTIGATION", "uetr": uetr_of(), "reason_code": "STAT", "narrative": "Please confirm status", "counterparty_bic": "CNTPDEFF"}, MAKER)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["direction"] == "OUTBOUND" and d["status"] == "SENT" and d["request"]["msg_type"] == "camt.110"
    assert sm.parse(d["request"]["xml"])["uetr"] == uetr_of() and d["linked_case"]["case_id"] == CASE
    s = post(f"cases/{d['id']}/simulate-reply", {"outcome": "ANSW"}, MAKER)
    assert s.status_code == 200 and s.json()["status"] == "REPLY_RECEIVED" and s.json()["response"]["msg_type"] == "camt.111"
    c = post(f"cases/{d['id']}/close", {"note": "Read and filed"}, MAKER)
    assert c.status_code == 200 and c.json()["status"] == "CLOSED"


def test_outbound_for_an_unknown_payment_is_refused():
    r = post("outbound", {"kind": "INVESTIGATION", "uetr": "NO-SUCH-PAYMENT-0000", "reason_code": "STAT", "narrative": "Please check", "counterparty_bic": "CNTPDEFF"})
    assert r.status_code == 404


# R4 + R6 ---------------------------------------------------------------------------------------------------------
def test_inbound_recall_accept_asks_the_bank_system_and_waits_for_confirmation():
    before = dict(repo.get_case(CASE))
    nid = inbound("camt.056", amount="800.00")["id"]
    assert post(f"cases/{nid}/draft", {"outcome": "CNCL", "reason_code": "CUST", "text": "Customer agreed"}).status_code == 200
    j = post(f"cases/{nid}/authorise", {}, APPR).json()
    assert j["status"] == "AWAITING_BANK_RETURN" and j["response"]["msg_type"] == "camt.029"
    assert sm.parse(j["response"]["xml"])["status_code"] == "CNCL"
    assert j["handoff"]["state"] == "RETURN_REQUESTED" and j["money_moved"] is False
    assert repo.get_case(CASE)["status"] == before["status"] and repo.get_case(CASE)["amount"] == before["amount"]
    r = post(f"cases/{nid}/bank-return", {"reference": "PACS004-REF-123"}, MAKER)
    assert r.status_code == 200 and r.json()["status"] == "CLOSED" and r.json()["handoff"]["state"] == "RETURN_CONFIRMED"


def test_bank_return_only_after_an_accepted_recall():
    nid = inbound("camt.056", amount="800.00")["id"]
    assert post(f"cases/{nid}/bank-return", {"reference": "X"}).status_code == 409


def test_inbound_recall_reject_needs_a_reason_and_closes():
    nid = inbound("camt.056", amount="800.00")["id"]
    assert post(f"cases/{nid}/draft", {"outcome": "RJCR", "text": "no reason code"}).status_code == 422
    assert post(f"cases/{nid}/draft", {"outcome": "RJCR", "reason_code": "ARDT", "text": "Already returned"}).status_code == 200
    j = post(f"cases/{nid}/authorise", {}, RSK).json()
    assert j["status"] == "CLOSED" and sm.parse(j["response"]["xml"])["status_code"] == "RJCR" and j["handoff"] is None


def test_outbound_recall_is_drafted_then_authorised_then_answered():
    r = post("outbound", {"kind": "RECALL", "uetr": uetr_of(), "reason_code": "DUPL", "narrative": "Sent twice", "counterparty_bic": "CNTPDEFF"}, MAKER)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["status"] == "DRAFTED" and d["request"]["msg_type"] == "camt.056"
    assert post(f"cases/{d['id']}/authorise", {}, MAKER).status_code == 403
    a = post(f"cases/{d['id']}/authorise", {}, APPR)
    assert a.status_code == 200 and a.json()["status"] == "SENT"
    s = post(f"cases/{d['id']}/simulate-reply", {"outcome": "CNCL"}, MAKER)
    assert s.status_code == 200 and s.json()["status"] == "REPLY_RECEIVED" and sm.parse(s.json()["response"]["xml"])["status_code"] == "CNCL"


def test_outbound_recall_bad_reason_is_refused():
    r = post("outbound", {"kind": "RECALL", "uetr": uetr_of(), "reason_code": "ZZZZ", "narrative": "x", "counterparty_bic": "CNTPDEFF"})
    assert r.status_code == 422


# R5 ------------------------------------------------------------------------------------------------------------
def test_large_amounts_need_two_different_approvers():
    nid = inbound("camt.056", amount="300000.00")["id"]
    assert post(f"cases/{nid}/draft", {"outcome": "CNCL", "reason_code": "CUST", "text": "ok"}).status_code == 200
    d = get(nid)
    assert d["approvals_needed"] == 2
    one = post(f"cases/{nid}/authorise", {}, APPR).json()
    assert one["status"] == "PART_APPROVED" and len(one["approvals"]) == 1
    assert post(f"cases/{nid}/authorise", {}, APPR).status_code == 409                       # same person twice
    two = post(f"cases/{nid}/authorise", {}, RSK).json()
    assert two["status"] == "AWAITING_BANK_RETURN" and len(two["approvals"]) == 2


def test_small_amounts_need_one():
    nid = inbound("camt.056", amount="300.00")["id"]
    assert get(nid)["approvals_needed"] == 1


def test_threshold_follows_policy(client):
    pid = client.post("/api/v2/policy/changes", json={"key": "dual_auth_amount", "value": 100000, "reason": "Tighter limit"}, headers=H(POL)).json()["id"]
    assert client.post(f"/api/v2/policy/changes/{pid}/approve", json={}, headers=H("POL-8002")).status_code == 200
    nid = inbound("camt.056", amount="150000.00")["id"]
    assert get(nid)["approvals_needed"] == 2


# R7 ------------------------------------------------------------------------------------------------------------
def _hours(d):
    from datetime import datetime
    f = lambda x: datetime.fromisoformat(x.replace("Z", "+00:00"))
    return (f(d["due_at"]) - f(d["created_at"])).total_seconds() / 3600


def test_due_time_comes_from_policy(client):
    assert round(_hours(inbound())) == 48
    ps = {p["key"]: p for p in client.get("/api/v2/policy/params", headers=H(POL)).json()["params"]}
    assert "network_response_hours" in ps
    pid = client.post("/api/v2/policy/changes", json={"key": "network_response_hours", "value": 24, "reason": "Faster answers"}, headers=H(POL)).json()["id"]
    client.post(f"/api/v2/policy/changes/{pid}/approve", json={}, headers=H("POL-8002"))
    assert round(_hours(inbound())) == 24


def test_overdue_cases_are_flagged_and_counted():
    nid = inbound()["id"]
    from app.db.models import V2NetworkCaseModel
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        r = db.query(V2NetworkCaseModel).filter(V2NetworkCaseModel.id == nid).one()
        r.due_at = iso(now() - timedelta(hours=2))
        db.commit()
    finally:
        db.close()
    j = client_.get("/api/v2/network/cases", headers=H(SUP)).json()
    row = next(x for x in j["items"] if x["id"] == nid)
    assert row["overdue"] is True and j["counts"]["overdue"] >= 1


def test_closed_cases_are_never_overdue():
    nid = inbound(uetr=str(uuid.uuid4()))["id"]
    post(f"cases/{nid}/draft", {"outcome": "RJCT", "text": "Not our payment"})
    post(f"cases/{nid}/authorise", {}, APPR)
    assert get(nid)["status"] in ("SENT", "CLOSED") and get(nid)["overdue"] is False


# listing -------------------------------------------------------------------------------------------------------
def test_listing_filters_and_counts():
    inbound()
    inbound("camt.056")
    post("outbound", {"kind": "INVESTIGATION", "uetr": uetr_of(), "reason_code": "STAT", "narrative": "Please check", "counterparty_bic": "CNTPDEFF"})
    j = client_.get("/api/v2/network/cases", headers=H(SUP)).json()
    c = j["counts"]
    assert c["investigations"] == 2 and c["recalls"] == 1 and c["inbound"] == 2 and c["outbound"] == 1 and c["open"] == 3
    r = client_.get("/api/v2/network/cases", params={"kind": "RECALL"}, headers=H(SUP)).json()["items"]
    assert len(r) == 1 and r[0]["kind"] == "RECALL"
    r = client_.get("/api/v2/network/cases", params={"direction": "OUTBOUND"}, headers=H(SUP)).json()["items"]
    assert len(r) == 1 and r[0]["direction"] == "OUTBOUND"


def test_sample_message_for_demo_links_to_a_real_case():
    r = post("inbound/sample", {"kind": "RECALL", "case_id": CASE})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["kind"] == "RECALL" and d["linked_case"]["case_id"] == CASE and d["request"]["fields"]["sender_bic"]


# R8 ------------------------------------------------------------------------------------------------------------
def test_every_step_is_in_the_audit_trail():
    nid = inbound(uetr=str(uuid.uuid4()), amount="300.00")["id"]
    post(f"cases/{nid}/draft", {"outcome": "ANSW", "text": "Done"})
    post(f"cases/{nid}/authorise", {}, APPR)
    ev = client_.get("/api/v2/audit/events", params={"case_id": nid}, headers=H(AUD)).json()["items"]
    names = " ".join(e["event"] for e in ev).lower()
    assert "received" in names and "draft" in names and "authoris" in names and "sent" in names
    assert {e["actor"] for e in ev} >= {"Priya Nair", "Mei Tan"}


def test_audit_and_risk_reads_but_cannot_write():
    nid = inbound()["id"]
    assert client_.get("/api/v2/network/cases", headers=H(AUD)).status_code == 200
    assert client_.get(f"/api/v2/network/cases/{nid}", headers=H(AUD)).status_code == 200
    assert post(f"cases/{nid}/draft", {"outcome": "ANSW", "text": "x"}, AUD).status_code == 403
    assert receive(msg("camt.110"), AUD).status_code == 403


def test_compliance_can_read_not_work():
    nid = inbound()["id"]
    assert client_.get(f"/api/v2/network/cases/{nid}", headers=H(CMP)).status_code == 200
    assert post(f"cases/{nid}/draft", {"outcome": "ANSW", "text": "x"}, CMP).status_code == 403


@pytest.mark.parametrize("uid", [ADM, POL])
def test_admin_and_policy_owner_have_no_access(uid):
    assert client_.get("/api/v2/network/cases", headers=H(uid)).status_code == 403
    assert receive(msg("camt.110"), uid).status_code == 403


def test_approvers_cannot_receive_or_draft():
    assert receive(msg("camt.110"), APPR).status_code == 403
    nid = inbound()["id"]
    assert post(f"cases/{nid}/draft", {"outcome": "ANSW", "text": "x"}, APPR).status_code == 403


def test_cannot_authorise_before_a_draft_or_after_sending():
    nid = inbound(uetr=str(uuid.uuid4()))["id"]
    assert post(f"cases/{nid}/authorise", {}, APPR).status_code == 409
    post(f"cases/{nid}/draft", {"outcome": "ANSW", "text": "done"})
    assert post(f"cases/{nid}/authorise", {}, APPR).status_code == 200
    assert post(f"cases/{nid}/authorise", {}, RSK).status_code == 409


def test_unknown_case_is_404():
    assert client_.get("/api/v2/network/cases/NET-NOPE", headers=H(SUP)).status_code == 404


# R9 ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("uid,has", [(MAKER, True), (SUP, True), (APPR, True), (RSK, True), (CMP, True), (AUD, True), (ADM, False), (POL, False)])
def test_menu(uid, has):
    nav = client_.get("/api/v2/me", headers=H(uid)).json()["nav"]
    assert ("network" in [n["key"] for n in nav]) is has
    if has:
        assert next(n for n in nav if n["key"] == "network")["path"] == "/network"


def test_outbound_can_be_raised_by_payment_case_id_and_listing_carries_the_code_lists():
    r = post("outbound", {"kind": "INVESTIGATION", "case_id": CASE, "reason_code": "CRDT", "narrative": "Credit not received", "counterparty_bic": "CNTPDEFF"})
    assert r.status_code == 201, r.text
    assert r.json()["uetr"] == uetr_of() and r.json()["linked_case"]["case_id"] == CASE
    assert post("outbound", {"kind": "INVESTIGATION", "case_id": "PEX-NOPE-9999", "reason_code": "CRDT", "narrative": "Credit not received", "counterparty_bic": "CNTPDEFF"}).status_code == 404
    codes = client_.get("/api/v2/network/cases", headers=H(SUP)).json()["codes"]
    assert "STAT" in codes["investigation_reasons"] and "DUPL" in codes["recall_reasons"]
