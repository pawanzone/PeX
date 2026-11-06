"""Operations director view: what an ops director asks first, from data PeX already holds. Read only.

  D1  Open exceptions split into buckets that add up to the open count.
  D2  The split follows the 8 rules: passes all rules (within / above the zero-touch limit), blocked by a named rule, no fix proposed.
  D3  Blocked cases are grouped by the rule that stopped them, and the groups add up.
  D4  By exception family: the columns add up to the totals.
  D5  Control: operation mode, the rules in force with their defaults, what changed and what is waiting.
  D6  Control: how many exception types can never be straight-through, from the library, not a typed number.
  D7  Control: SME validation progress equals the review summary.
  D8  Proof: empty until shadow results are loaded, then the headline numbers.
  D9  Plain-language headline sentences that agree with the numbers.
  D10 Access: Administrators, Policy Owners, Supervisors and Audit read; operators and approvers are refused.
  D11 Release mode changes how cases are released, never the split.
  D12 Reading changes nothing.
"""
import pytest

from app.config import settings
from app.core.auth import create_token
from app.services.v2 import dashboard as dash
from app.services.v2 import library, policy, review, shadow
from app.services.v2 import logic as lg
from app.services.v2 import seed as v2seed
from app.services.v2.rows import all_cases
from tests.test_shadow_scorecard import eligible_with_value, fixed, load

ADMIN, OWNER1, OWNER2, SUP, AUD, OP, APPR = "ADM-0002", "POL-8001", "POL-8002", "SUP-2001", "AUD-5001", "OP-9012", "APR-3192"


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def fresh(client):
    v2seed.seed_v2()
    policy.reset_all()
    client.delete("/api/v2/shadow", headers=H(ADMIN))
    client.delete("/api/v2/review", headers=H(ADMIN))
    yield
    client.delete("/api/v2/shadow", headers=H(ADMIN))
    client.delete("/api/v2/review", headers=H(ADMIN))
    policy.reset_all()


def get(client, uid=ADMIN):
    r = client.get("/api/v2/director", headers=H(uid))
    assert r.status_code == 200, r.text
    return r.json()


def propose_and_approve(client, key, value):
    r = client.post("/api/v2/policy/changes", json={"key": key, "value": value, "reason": "test"}, headers=H(OWNER1))
    assert r.status_code == 200, r.text
    assert client.post(f"/api/v2/policy/changes/{r.json()['id']}/approve", json={"note": "ok"}, headers=H(OWNER2)).status_code == 200


# D1, D2 ----------------------------------------------------------------------------------------------------------
def test_buckets_add_up_to_the_open_count(client):
    d = get(client)
    open_n = sum(1 for c in all_cases() if lg.status_of(c) not in dash.FINAL)
    a = d["automation"]
    assert a["open"] == open_n and open_n > 0
    assert sum(b["count"] for b in a["buckets"]) == open_n
    keys = [b["key"] for b in a["buckets"]]
    assert keys[:2] == ["pass_within_zero_touch", "pass_needs_approval"] and keys[-1] == "no_proposal"
    assert all(b["label"] and b["meaning"] for b in a["buckets"])


def test_pass_buckets_agree_with_the_rules(client):
    from app.services.v2 import stp
    d = get(client)
    zt = stp.zero_touch_limit()
    within = above = 0
    for c in all_cases():
        if lg.status_of(c) in dash.FINAL or not (lg.ext_of(c).get("change")):
            continue
        if stp.evaluate(c)["eligible"]:
            if float(c.get("amount") or 0) <= zt:
                within += 1
            else:
                above += 1
    by = {b["key"]: b["count"] for b in d["automation"]["buckets"]}
    assert by["pass_within_zero_touch"] == within and by["pass_needs_approval"] == above


# D3 --------------------------------------------------------------------------------------------------------------
def test_blocked_cases_are_grouped_by_rule(client):
    d = get(client)
    blocked = [b for b in d["automation"]["buckets"] if b["key"].startswith("blocked_")]
    assert blocked and all(b["rule"] and b["count"] > 0 for b in blocked)
    assert d["automation"]["blocked_total"] == sum(b["count"] for b in blocked)
    assert len({b["key"] for b in blocked}) == len(blocked)


# D4 --------------------------------------------------------------------------------------------------------------
def test_family_table_adds_up(client):
    a = get(client)["automation"]
    f = a["by_family"]
    assert {x["family"] for x in f} <= {"CO", "DQ", "PR", "ST", "TR"}
    assert sum(x["open"] for x in f) == a["open"]
    by = {b["key"]: b["count"] for b in a["buckets"]}
    assert sum(x["pass_rules"] for x in f) == by["pass_within_zero_touch"] + by["pass_needs_approval"]
    assert sum(x["no_proposal"] for x in f) == by["no_proposal"]
    assert sum(x["blocked"] for x in f) == a["blocked_total"]


# D5 --------------------------------------------------------------------------------------------------------------
def test_control_block_lists_mode_rules_and_changes(client):
    c = get(client)["control"]
    assert c["operation_mode"] == settings.PEX_OPERATION_MODE and c["operation_mode_meaning"]
    rules = {r["key"]: r for r in c["rules"]}
    assert {"dual_auth_amount", "batch_limit", "zero_touch_limit", "release_mode"} <= set(rules)
    assert all(r["changed"] is False for r in rules.values()) and c["recent_changes"] == [] and c["pending_changes"] == 0
    propose_and_approve(client, "zero_touch_limit", 5000)
    c = get(client)["control"]
    z = {r["key"]: r for r in c["rules"]}["zero_touch_limit"]
    assert z["value"] == 5000 and z["changed"] is True and z["default"] == float(settings.STP_MAX_AMOUNT)
    assert c["recent_changes"][0]["key"] == "zero_touch_limit" and c["recent_changes"][0]["proposed_by"] and c["recent_changes"][0]["decided_by"]


def test_pending_changes_are_counted(client):
    client.post("/api/v2/policy/changes", json={"key": "release_mode", "value": "REVIEW_EACH", "reason": "test"}, headers=H(OWNER1))
    assert get(client)["control"]["pending_changes"] == 1


# D6, D7 ----------------------------------------------------------------------------------------------------------
def test_never_straight_through_count_comes_from_the_library(client):
    never = sum(1 for p in library.library()["profiles"] if p["stp"] == "NEVER")
    c = get(client)["control"]
    assert c["never_straight_through"] == never and never >= 10
    assert c["profiles_total"] == 41


def test_sme_progress_equals_the_review_summary(client):
    client.post("/api/v2/review/items/profile/DQ-01/status", json={"status": "SIGNED_OFF"}, headers=H(ADMIN))
    s = review.summary()
    c = get(client)["control"]["sme_review"]
    assert c["profiles_signed_off"] == s["profiles"]["SIGNED_OFF"] == 1 and c["profiles_total"] == 41
    assert c["controls_signed_off"] == s["controls"]["SIGNED_OFF"] and c["open_comments"] == s["open_comments"]


# D8 --------------------------------------------------------------------------------------------------------------
def test_proof_is_empty_until_shadow_results_are_loaded(client):
    p = get(client)["proof"]
    assert p["loaded"] is False and p["compared"] == 0 and p["safe_release_rate"] is None
    (cid, v), = eligible_with_value()
    load(client, [fixed(cid, v[1], minutes=10)])
    p = get(client)["proof"]
    sc = shadow.scorecard()
    assert p["loaded"] is True and p["compared"] == 1 == sc["compared"]
    assert p["released_correctly"] == 1 and p["released_wrongly"] == 0 and p["safe_release_rate"] == 1.0


# D9 --------------------------------------------------------------------------------------------------------------
def test_headline_sentences_agree_with_the_numbers(client):
    d = get(client)
    assert d["headline"] and all(isinstance(s, str) and s for s in d["headline"])
    text = " ".join(d["headline"])
    assert str(d["automation"]["open"]) in text
    assert "synthetic" in d["data_note"].lower() or "demo" in d["data_note"].lower()


# D10 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("uid", [ADMIN, OWNER1, SUP, AUD])
def test_these_roles_read(client, uid):
    assert client.get("/api/v2/director", headers=H(uid)).status_code == 200


@pytest.mark.parametrize("uid", [OP, APPR])
def test_operators_and_approvers_are_refused(client, uid):
    assert client.get("/api/v2/director", headers=H(uid)).status_code == 403


# D11 -------------------------------------------------------------------------------------------------------------
def test_release_mode_does_not_change_the_split(client):
    before = get(client)["automation"]["buckets"]
    propose_and_approve(client, "release_mode", "REVIEW_EACH")
    d = get(client)
    assert d["automation"]["buckets"] == before
    assert d["automation"]["release_mode"]["value"] == "REVIEW_EACH" and d["automation"]["release_mode"]["label"]


# D12 -------------------------------------------------------------------------------------------------------------
def test_reading_changes_nothing(client):
    before = {c["case_id"]: lg.status_of(c) for c in all_cases()}
    a, b = get(client), get(client)
    assert {c["case_id"]: lg.status_of(c) for c in all_cases()} == before
    assert a["automation"] == b["automation"]
