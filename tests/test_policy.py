"""Rules & Policy Studio: acceptance tests written from the requirements.

  R1  Only a Policy Owner can see and change rules. Administrators, supervisors, approvers, auditors and makers cannot.
  R2  The studio lists the rules the platform really uses, with the value in force and what each one controls.
  R3  A change is proposed with a reason, checked for range, and shows what it would change on recent cases before anyone decides.
  R4  A proposal does nothing until a DIFFERENT Policy Owner approves it (four eyes). Reject and withdraw leave the old value.
  R5  Once approved the platform behaves differently straight away (dual authorisation, batch limit, confidence gate, reveal window).
  R6  Every proposal and decision is in the audit trail; the value survives a restart.
  R7  Only one open proposal per rule.
"""
import pytest

from app.core.auth import create_token
from app.services.data_loader import repo
from app.services.v2 import logic as lg
from app.services.v2 import policy
from app.services.v2 import seed as v2seed

OWNER1, OWNER2 = "POL-8001", "POL-8002"
OTHERS = ["OP-9012", "SUP-2001", "APR-3192", "RSK-7714", "CMP-6001", "AUD-5001", "ADM-0002"]
KEYS = {"dual_auth_amount", "batch_limit", "confidence_threshold", "reveal_minutes", "expedite_cooldown_min", "expedite_auto_escalate_min"}


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def fresh():
    v2seed.seed_v2()
    policy.reset_all()
    yield
    policy.reset_all()


def params(client, uid=OWNER1):
    r = client.get("/api/v2/policy/params", headers=H(uid))
    assert r.status_code == 200, r.text
    return {p["key"]: p for p in r.json()["params"]}


def propose(client, key, value, reason="Quarterly policy review", uid=OWNER1):
    return client.post("/api/v2/policy/changes", json={"key": key, "value": value, "reason": reason}, headers=H(uid))


def decide(client, cid, how, uid=OWNER2, note="ok"):
    return client.post(f"/api/v2/policy/changes/{cid}/{how}", json={"note": note}, headers=H(uid))


# R1 ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("uid", OTHERS)
def test_only_policy_owners_can_see_or_change_rules(client, uid):
    assert client.get("/api/v2/policy/params", headers=H(uid)).status_code == 403
    assert propose(client, "dual_auth_amount", 100000, uid=uid).status_code == 403


def test_policy_owner_has_the_studio_and_reference_in_the_menu(client):
    me = client.get("/api/v2/me", headers=H(OWNER1)).json()
    keys = [n["key"] for n in me["nav"]]
    assert "policy" in keys and "dashboard" == keys[0] and "worklist" not in keys and "approvals" not in keys
    assert all("policy" not in [n["key"] for n in client.get("/api/v2/me", headers=H(u)).json()["nav"]] for u in OTHERS)


def test_policy_owner_cannot_work_cases(client):
    assert client.post("/api/v2/cases/PEX-INV-0001/approve", json={"reviewed": True}, headers=H(OWNER1)).status_code in (403, 409)
    assert client.post("/api/v2/cases/PEX-INV-0001/ping", json={}, headers=H(OWNER1)).status_code == 403


# R2 ------------------------------------------------------------------------------------------------------------


def test_rules_are_listed_with_value_and_meaning(client):
    p = params(client)
    assert KEYS <= set(p)
    d = p["dual_auth_amount"]
    assert d["value"] == 250000 and d["default"] == 250000 and d["label"] and d["description"] and d["used_by"] and d["min"] < d["max"] and d["pending"] is None
    assert p["confidence_threshold"]["value"] == 85 and p["reveal_minutes"]["value"] == 10


# R3 ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key,value", [("dual_auth_amount", -5), ("dual_auth_amount", "abc"), ("confidence_threshold", 150), ("reveal_minutes", 0), ("nope", 1)])
def test_bad_values_are_refused(client, key, value):
    assert propose(client, key, value).status_code in (400, 404, 422)


def test_reason_is_required(client):
    assert propose(client, "dual_auth_amount", 100000, reason="  ").status_code in (400, 422)


def test_proposal_shows_what_it_would_change_and_changes_nothing_yet(client):
    pend = [c for c in repo._case_cache.values() if lg.status_of(c) in lg.PENDING]
    expect = sum(1 for c in pend if 100000 <= float(c.get("amount") or 0) < 250000 and not c.get("dual_auth_required") and lg.status_of(c) != "AWAITING_SECOND_APPROVAL")
    r = propose(client, "dual_auth_amount", 100000)
    assert r.status_code == 200, r.text
    ch = r.json()
    assert ch["status"] == "PENDING" and ch["prev_value"] == 250000 and ch["value"] == 100000
    assert ch["impact"]["summary"] and ch["impact"]["cases_affected"] == expect
    assert params(client)["dual_auth_amount"]["value"] == 250000
    assert params(client)["dual_auth_amount"]["pending"]["id"] == ch["id"]


def test_preview_endpoint_gives_the_same_numbers(client):
    r = client.post("/api/v2/policy/preview", json={"key": "dual_auth_amount", "value": 100000}, headers=H(OWNER1))
    assert r.status_code == 200 and r.json()["cases_affected"] >= 0 and r.json()["summary"]


# R4 ------------------------------------------------------------------------------------------------------------
def test_proposer_cannot_approve_own_change(client):
    cid = propose(client, "dual_auth_amount", 100000).json()["id"]
    r = decide(client, cid, "approve", uid=OWNER1)
    assert r.status_code in (403, 409)
    assert params(client)["dual_auth_amount"]["value"] == 250000


def test_second_owner_approves_and_value_goes_live(client):
    cid = propose(client, "dual_auth_amount", 100000).json()["id"]
    r = decide(client, cid, "approve")
    assert r.status_code == 200 and r.json()["status"] == "ACTIVE"
    p = params(client)["dual_auth_amount"]
    assert p["value"] == 100000 and p["pending"] is None and p["default"] == 250000
    assert [h["status"] for h in p["history"]][:1] == ["ACTIVE"]


def test_reject_and_withdraw_keep_the_old_value(client):
    cid = propose(client, "batch_limit", 50000).json()["id"]
    assert decide(client, cid, "reject").json()["status"] == "REJECTED"
    assert params(client)["batch_limit"]["value"] == 25000
    cid2 = propose(client, "batch_limit", 40000).json()["id"]
    assert decide(client, cid2, "withdraw", uid=OWNER2).status_code in (403, 409)     # only the proposer withdraws
    assert decide(client, cid2, "withdraw", uid=OWNER1).json()["status"] == "WITHDRAWN"
    assert params(client)["batch_limit"]["value"] == 25000


def test_decided_change_cannot_be_decided_again(client):
    cid = propose(client, "batch_limit", 50000).json()["id"]
    decide(client, cid, "approve")
    assert decide(client, cid, "reject").status_code == 409


# R5 ------------------------------------------------------------------------------------------------------------
def test_dual_authorisation_rule_changes_behaviour(client):
    case = next(c for c in repo._case_cache.values() if lg.status_of(c) == "PENDING_APPROVAL" and 100000 <= float(c.get("amount") or 0) < 250000 and not c.get("dual_auth_required"))
    assert lg.is_dual(case) is False
    decide(client, propose(client, "dual_auth_amount", 100000).json()["id"], "approve")
    assert lg.is_dual(case) is True


def test_confidence_threshold_changes_the_gate(client):
    case = next(c for c in repo._case_cache.values() if lg.confidence_of(c) and lg.confidence_of(c)["applies"])
    assert lg.confidence_of(case)["threshold"] == 85
    decide(client, propose(client, "confidence_threshold", 95).json()["id"], "approve")
    assert lg.confidence_of(case)["threshold"] == 95


def test_batch_limit_changes_the_batch_screen(client):
    decide(client, propose(client, "batch_limit", 30000).json()["id"], "approve")
    r = client.get("/api/v2/stp/review", headers=H("APR-3192")).json()
    assert r["policy"]["limit"]["amount"] == 30000


def test_reveal_window_changes(client):
    decide(client, propose(client, "reveal_minutes", 5).json()["id"], "approve")
    r = client.post("/api/v2/cases/PEX-INV-0001/pii/reveal", json={"reason": "Checking the beneficiary with the client"}, headers=H("SUP-2001"))
    assert r.status_code == 200 and "5 minutes" in r.json()["message"]


# R6 ------------------------------------------------------------------------------------------------------------
def test_audit_trail_and_restart_survival(client):
    cid = propose(client, "dual_auth_amount", 100000).json()["id"]
    decide(client, cid, "approve")
    ev = client.get("/api/v2/audit/events", params={"case_id": "POLICY-dual_auth_amount"}, headers=H("AUD-5001")).json()["items"]
    names = " ".join(e["event"] for e in ev).lower()
    assert "propos" in names and "approv" in names and {e["actor"] for e in ev} >= {"Nadia Rahman", "Greg Holt"}
    policy.reset_cache()                                   # as after a restart: reloaded from the database
    assert params(client)["dual_auth_amount"]["value"] == 100000


# R7 ------------------------------------------------------------------------------------------------------------
def test_one_open_proposal_per_rule(client):
    assert propose(client, "dual_auth_amount", 100000).status_code == 200
    assert propose(client, "dual_auth_amount", 120000).status_code == 409
    assert propose(client, "batch_limit", 30000).status_code == 200
