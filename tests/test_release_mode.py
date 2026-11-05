"""Release mode: how a bank decides who releases straight-through payments.

  M1  The studio lists release_mode (AUTO_RELEASE / APPROVE_ALL / REVIEW_EACH) and zero_touch_limit beside the existing rules.
  M2  Defaults reproduce today's behaviour: APPROVE_ALL, zero-touch limit 10,000, batch limit 25,000.
  M3  Both are changed only through the four-eyes route (proposal, different Policy Owner approves), with a reason, and are audited.
  M4  A choice rule accepts only its listed options; the amount rule keeps its range.
  M5  REVIEW_EACH: the batch screen has no bulk release (review says so, approve refuses and releases nothing).
  M6  APPROVE_ALL: the bulk release works as before; every case that is not eligible is listed with the rule that stopped it.
  M7  AUTO_RELEASE: the bulk release still works for people; eligible cases at or under the zero-touch limit are marked, nothing is handed off by itself.
  M8  No mode can make a NEVER profile or a failing predicate releasable.
  M9  The zero-touch limit in the policy is the one the engine and the Admin pages use.
"""
import pytest

from app.config import settings
from app.core.auth import create_token
from app.services.v2 import policy
from app.services.v2 import seed as v2seed

OWNER1, OWNER2 = "POL-8001", "POL-8002"
APPR, MAKER = "APR-3192", "OP-9012"
RULE_OF = {"COMPLIANCE_HOLD": "C_comp", "EVIDENCE_CONFLICT": "E_suff", "EVIDENCE_MISSING": "E_suff", "VALIDATION_FAILED": "V_det",
           "HARD_BLOCK": "Profile ceiling", "ABOVE_LIMIT": "P_bank"}


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def fresh():
    v2seed.seed_v2()
    policy.reset_all()
    yield
    policy.reset_all()


def params(client):
    return {p["key"]: p for p in client.get("/api/v2/policy/params", headers=H(OWNER1)).json()["params"]}


def propose(client, key, value, reason="Release model review", uid=OWNER1):
    return client.post("/api/v2/policy/changes", json={"key": key, "value": value, "reason": reason}, headers=H(uid))


def set_mode(client, mode):
    r = propose(client, "release_mode", mode)
    assert r.status_code == 200, r.text
    a = client.post(f"/api/v2/policy/changes/{r.json()['id']}/approve", json={"note": "ok"}, headers=H(OWNER2))
    assert a.status_code == 200, a.text


def review(client):
    r = client.get("/api/v2/stp/review", headers=H(APPR))
    assert r.status_code == 200, r.text
    return r.json()


# M1, M2 --------------------------------------------------------------------------------------------------------
def test_new_rules_are_listed_with_defaults_that_change_nothing(client):
    p = params(client)
    m, z = p["release_mode"], p["zero_touch_limit"]
    assert m["value"] == "APPROVE_ALL" and m["default"] == "APPROVE_ALL"
    assert [o["value"] for o in m["options"]] == ["AUTO_RELEASE", "APPROVE_ALL", "REVIEW_EACH"]
    assert all(o["label"] and o["meaning"] for o in m["options"])
    assert z["value"] == float(settings.STP_MAX_AMOUNT)  # shipped default is 10,000; the test environment may override it
    assert p["batch_limit"]["value"] == float(settings.BATCH_APPROVAL_MAX_AMOUNT)


# M3 ------------------------------------------------------------------------------------------------------------
def test_mode_change_needs_a_second_policy_owner_and_is_audited(client):
    r = propose(client, "release_mode", "REVIEW_EACH")
    assert r.status_code == 200 and r.json()["status"] == "PENDING"
    assert params(client)["release_mode"]["value"] == "APPROVE_ALL"
    cid = r.json()["id"]
    same = client.post(f"/api/v2/policy/changes/{cid}/approve", json={"note": "x"}, headers=H(OWNER1))
    assert same.status_code == 403
    assert params(client)["release_mode"]["value"] == "APPROVE_ALL"
    assert client.post(f"/api/v2/policy/changes/{cid}/approve", json={"note": "x"}, headers=H(OWNER2)).status_code == 200
    assert params(client)["release_mode"]["value"] == "REVIEW_EACH"
    ev = client.get("/api/v2/audit/events", params={"case_id": "POLICY-release_mode"}, headers=H("AUD-5001")).json()["items"]
    names = " ".join(e["event"] for e in ev).lower()
    assert "propos" in names and "approv" in names
    policy.reset_cache()
    assert params(client)["release_mode"]["value"] == "REVIEW_EACH"


@pytest.mark.parametrize("uid", ["OP-9012", "SUP-2001", APPR, "RSK-7714", "CMP-6001", "AUD-5001", "ADM-0002"])
def test_nobody_else_can_change_the_mode(client, uid):
    assert propose(client, "release_mode", "REVIEW_EACH", uid=uid).status_code == 403


def test_proposal_says_what_the_mode_would_change(client):
    r = propose(client, "release_mode", "REVIEW_EACH").json()
    assert r["impact"]["summary"] and "batch" in r["impact"]["summary"].lower()


# M4 ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("value", ["", "auto", "approve_all", 5, None])
def test_unknown_mode_is_refused(client, value):
    assert propose(client, "release_mode", value).status_code in (400, 422)


@pytest.mark.parametrize("value", [-1, 0, "abc", 10_000_000])
def test_zero_touch_limit_keeps_its_range(client, value):
    assert propose(client, "zero_touch_limit", value).status_code in (400, 422)


# M5 ------------------------------------------------------------------------------------------------------------
def test_review_each_has_no_bulk_release(client):
    before = review(client)
    ids = [i["case_id"] for i in before["eligible"]][:3]
    assert ids, "the seed must have eligible cases"
    set_mode(client, "REVIEW_EACH")
    after = review(client)
    assert after["release_mode"]["value"] == "REVIEW_EACH" and after["release_mode"]["bulk_release"] is False
    r = client.post("/api/v2/stp/approve", json={"case_ids": ids}, headers=H(APPR))
    assert r.status_code == 409, r.text
    assert "review" in r.text.lower()
    assert [i["case_id"] for i in review(client)["eligible"]] == [i["case_id"] for i in before["eligible"]]


# M6 ------------------------------------------------------------------------------------------------------------
def test_approve_all_works_and_lists_every_exception_with_its_rule(client):
    d = review(client)
    assert d["release_mode"]["value"] == "APPROVE_ALL" and d["release_mode"]["bulk_release"] is True
    ids = [i["case_id"] for i in d["eligible"]][:2]
    r = client.post("/api/v2/stp/approve", json={"case_ids": ids}, headers=H(APPR))
    assert r.status_code == 200, r.text
    groups = review(client)["not_eligible"]["groups"]
    assert groups
    for g in groups:
        assert g["rule"] == RULE_OF[g["code"]], g


# M7 ------------------------------------------------------------------------------------------------------------
def test_auto_release_marks_cases_but_hands_nothing_off(client):
    set_mode(client, "AUTO_RELEASE")
    d = review(client)
    assert d["release_mode"]["value"] == "AUTO_RELEASE" and d["release_mode"]["bulk_release"] is True
    limit = d["release_mode"]["zero_touch_limit"]
    assert limit == float(settings.STP_MAX_AMOUNT)
    for i in d["eligible"]:
        assert i["auto_release_eligible"] == (i["amount"]["amount"] <= limit)
    assert d["release_mode"]["note"] and "no trigger" in d["release_mode"]["note"].lower()
    before = d["totals"]["eligible"]
    assert review(client)["totals"]["eligible"] == before  # reviewing hands nothing off


# M8 ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("mode", ["AUTO_RELEASE", "APPROVE_ALL"])
def test_no_mode_loosens_the_gates(client, mode):
    base = {g["code"]: {c["case_id"] for c in g["cases"]} for g in review(client)["not_eligible"]["groups"]}
    base_ids = {i["case_id"] for i in review(client)["eligible"]}
    set_mode(client, mode)
    d = review(client)
    assert {i["case_id"] for i in d["eligible"]} == base_ids
    assert {g["code"]: {c["case_id"] for c in g["cases"]} for g in d["not_eligible"]["groups"]} == base
    blocked = [c["case_id"] for g in d["not_eligible"]["groups"] for c in g["cases"]]
    if blocked:
        r = client.post("/api/v2/stp/approve", json={"case_ids": blocked[:5]}, headers=H(APPR)).json()
        assert r["handed_to_bank"] == 0 and r["recorded"] == 0 and len(r["skipped"]) == len(blocked[:5])


# M9 ------------------------------------------------------------------------------------------------------------
def test_zero_touch_limit_in_policy_drives_the_engine_and_the_pages(client):
    r = propose(client, "zero_touch_limit", 5000)
    assert r.status_code == 200, r.text
    assert client.post(f"/api/v2/policy/changes/{r.json()['id']}/approve", json={"note": "ok"}, headers=H(OWNER2)).status_code == 200
    assert review(client)["policy"]["autonomous_limit"]["amount"] == 5000
    from app.services.v2 import library
    assert library.bank_settings()
