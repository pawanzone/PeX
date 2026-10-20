"""Approvals desk: "My desk" and "Others" in one view. Acceptance tests from the requirements.

  R1  An approver sees what is waiting for them (My desk) and what is waiting for others, in the same screen.
  R2  Every case is in exactly one of the two; the counts add up to the whole queue.
  R3  Others is read only: nothing there can be approved from this person's account.
  R4  Others names who has it.
  R5  Not passing a desk keeps the old behaviour (the whole queue).
"""
import pytest

from app.core.auth import create_token
from app.services.v2 import seed as v2seed

APPR, RSK, SUP = "APR-3192", "RSK-7714", "SUP-2001"


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def seeded():
    v2seed.seed_v2()
    yield


def q(client, uid, **kw):
    r = client.get("/api/v2/approvals", params={"page_size": 200, **kw}, headers=H(uid))
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("uid", [APPR, RSK, SUP])
def test_my_desk_and_others_split_the_whole_queue(client, uid):
    whole, mine, others = q(client, uid), q(client, uid, desk="mine"), q(client, uid, desk="others")
    ids = lambda d: {r["case_id"] for r in d["items"]}
    assert ids(mine).isdisjoint(ids(others))
    assert ids(mine) | ids(others) == ids(whole)
    assert whole["counts"] == {"mine": mine["total"], "others": others["total"]} == mine["counts"] == others["counts"]
    assert mine["total"] + others["total"] == whole["total"]


def test_my_desk_holds_only_my_cases(client):
    for r in q(client, APPR, desk="mine")["items"]:
        assert r["mine"] is True
        assert r["can_approve"] or (r["approver_assigned"] or {}).get("user_id") == APPR


def test_others_is_read_only_and_names_who_has_it(client):
    d = q(client, APPR, desk="others")
    assert d["items"], "seeded data has cases for other approvers"
    for r in d["items"]:
        assert r["mine"] is False and r["can_approve"] is False
        assert (r["approver_assigned"] or {}).get("name")
        assert r["cannot_approve_reason"]


def test_other_cannot_be_approved_through_the_api(client):
    cid = q(client, APPR, desk="others")["items"][0]["case_id"]
    r = client.post(f"/api/v2/cases/{cid}/approve", json={}, headers=H(APPR))
    assert r.status_code in (400, 403, 409, 422), r.text


def test_default_is_the_whole_queue(client):
    whole = q(client, APPR)
    assert whole["total"] == q(client, APPR, desk="all")["total"] and whole["total"] > 0


def test_tier_filter_still_works_inside_a_desk(client):
    d = q(client, APPR, desk="others", tier="2")
    assert all(r["dual_auth"] for r in d["items"])
