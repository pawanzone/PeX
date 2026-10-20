"""Expedite ladder: ping the approver, escalate to the supervisor, then the head of operations. Acceptance tests from the requirements.

  R1  A maker (or supervisor) can ping the person holding a pending case; the message lands in that person's chaser panel.
  R2  The ladder has three levels (approver, supervisor, head of operations). It is climbed one step at a time.
  R3  The same level cannot be pinged again straight away (cooldown).
  R4  The receiver can acknowledge; the sender is told. Only the receiver can acknowledge.
  R5  Unacknowledged pings escalate on their own after a while, by the system, and that is visible as such.
  R6  Every ping, acknowledgement and automatic escalation is in the audit trail.
  R7  Only pending cases can be chased; no real personal values travel in the message.
"""
import json
from datetime import timedelta

import pytest

from app.core.auth import create_token
from app.services.data_loader import repo
from app.services.v2 import expedite as ex
from app.services.v2 import logic as lg
from app.services.v2 import seed as v2seed
from app.services.v2.core import iso, now

MAKER, SUP, APPR, RSK, CMP, AUD = "OP-9012", "SUP-2001", "APR-3192", "RSK-7714", "CMP-6001", "AUD-5001"
CID = "PEX-INV-0001"            # pending approval, assigned to APR-3192


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def seeded(monkeypatch):
    v2seed.seed_v2()
    monkeypatch.setattr(ex, "COOLDOWN_MIN", 10)
    c = repo.get_case(CID)
    c["expedite_log"], c["expedite_ping"] = [], None
    repo.save_case(c)
    yield


def ping(client, uid=MAKER, cid=CID, **body):
    return client.post(f"/api/v2/cases/{cid}/ping", json=body, headers=H(uid))


def chasers(client, uid):
    r = client.get("/api/v2/expedite", headers=H(uid))
    assert r.status_code == 200, r.text
    return r.json()


def age_log(minutes):
    c = repo.get_case(CID)
    for e in c["expedite_log"]:
        e["at"] = iso(now() - timedelta(minutes=minutes))
    repo.save_case(c)


# R1 ------------------------------------------------------------------------------------------------------------
def test_ping_reaches_the_assigned_approver(client):
    r = ping(client, note="Cutoff in 90 minutes, please prioritise")
    assert r.status_code == 200, r.text
    d = chasers(client, APPR)
    item = next(i for i in d["items"] if i["case_id"] == CID)
    assert item["level"] == 1 and item["status"] == "UNREAD" and item["sender"]["name"] and item["note"].startswith("Cutoff")
    assert item["amount"] and item["cutoff"] and item["link"] == f"/cases/{CID}"
    assert d["unread"] >= 1


def test_other_people_do_not_see_it(client):
    ping(client)
    assert all(i["case_id"] != CID for i in chasers(client, RSK)["items"])
    assert all(i["case_id"] != CID for i in chasers(client, AUD)["items"])


# R2 ------------------------------------------------------------------------------------------------------------
def test_ladder_is_climbed_one_step_at_a_time(client):
    assert ping(client, level=2).status_code in (400, 409, 422)            # cannot start at the supervisor
    assert ping(client).status_code == 200                                  # level 1
    assert ping(client, level=3).status_code in (400, 409, 422)            # cannot skip level 2
    assert ping(client, level=2).status_code == 200
    assert ping(client, level=3).status_code == 200
    log = repo.get_case(CID)["expedite_log"]
    assert [e["level"] for e in log] == [1, 2, 3]
    assert log[1]["target_role"] == "SUPERVISOR" and log[2]["target_role"] == "SUPERVISOR" and log[2]["target_title"] != log[1]["target_title"]
    assert any(i["case_id"] == CID and i["level"] == 3 for i in chasers(client, SUP)["items"])


def test_case_state_shows_the_ladder(client):
    ping(client)
    r = client.get(f"/api/v2/cases/{CID}/expedite", headers=H(MAKER))
    assert r.status_code == 200
    d = r.json()
    assert [l["level"] for l in d["levels"]] == [1, 2, 3]
    assert d["levels"][0]["sent"] and not d["levels"][1]["sent"] and d["next_level"] == 2 and d["can_ping"] is True


# R3 ------------------------------------------------------------------------------------------------------------
def test_same_level_has_a_cooldown(client):
    assert ping(client).status_code == 200
    r = ping(client, level=1)
    assert r.status_code in (400, 409, 429)
    assert "minute" in json.dumps(r.json()).lower()


# R4 ------------------------------------------------------------------------------------------------------------
def test_receiver_acknowledges_and_sender_is_told(client):
    ping(client)
    entry = next(i for i in chasers(client, APPR)["items"] if i["case_id"] == CID)
    assert client.post(f"/api/v2/expedite/{entry['id']}/ack", headers=H(RSK)).status_code in (403, 404)
    assert client.post(f"/api/v2/expedite/{entry['id']}/ack", headers=H(APPR)).status_code == 200
    after = next(i for i in chasers(client, APPR)["items"] if i["id"] == entry["id"])
    assert after["status"] == "ACKNOWLEDGED" and after["ack_by"]
    notes = client.get("/api/v2/notifications", headers=H(MAKER)).json()["items"]
    assert any(n["case_id"] == CID and "acknowledg" in (n["title"] + n["text"]).lower() for n in notes)


# R5 ------------------------------------------------------------------------------------------------------------
def test_unacknowledged_pings_escalate_by_themselves(client):
    ping(client)
    age_log(ex.AUTO_ESCALATE_MIN + 5)
    d = chasers(client, SUP)
    item = next(i for i in d["items"] if i["case_id"] == CID)
    assert item["level"] == 2 and item["auto"] is True and "SLA" in item["sender"]["name"]
    assert d["items"] and chasers(client, SUP)["items"].count(item) <= 1          # sweeping twice does not duplicate


def test_acknowledged_pings_do_not_escalate(client):
    ping(client)
    e = next(i for i in chasers(client, APPR)["items"] if i["case_id"] == CID)
    client.post(f"/api/v2/expedite/{e['id']}/ack", headers=H(APPR))
    age_log(ex.AUTO_ESCALATE_MIN + 5)
    chasers(client, SUP)
    assert [x["level"] for x in repo.get_case(CID)["expedite_log"]] == [1]


# R6 ------------------------------------------------------------------------------------------------------------
def test_everything_is_audited(client):
    ping(client)
    e = next(i for i in chasers(client, APPR)["items"] if i["case_id"] == CID)
    client.post(f"/api/v2/expedite/{e['id']}/ack", headers=H(APPR))
    ev = client.get(f"/api/v2/cases/{CID}/timeline", headers=H(MAKER)).json()["items"]
    kinds = " ".join(x["event"] for x in ev).lower()
    assert "ping" in kinds or "expedite" in kinds
    assert any("acknowledg" in x["event"].lower() for x in ev)


# R7 ------------------------------------------------------------------------------------------------------------
def test_only_pending_cases_can_be_chased(client):
    done = next(cid for cid, c in repo._case_cache.items() if lg.status_of(c) in lg.DONE)
    r = ping(client, cid=done)
    assert r.status_code in (400, 409)


def test_no_real_personal_values_in_the_message(client):
    c = repo.get_case(CID)
    raw = c["creditor_party"]["party_name"]
    ping(client, note=f"Please release the payment to {raw} today")
    blob = json.dumps(chasers(client, APPR))
    assert raw not in blob


def test_auditors_cannot_ping(client):
    assert ping(client, uid=AUD).status_code in (403, 401)
