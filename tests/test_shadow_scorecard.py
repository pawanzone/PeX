"""Shadow scorecard: what PeX would have done, against what the bank's analyst actually did.

  S1  An analyst fix equal to PeX's proposal on a case that passes the 8 rules = AGREE, counted as "would have released correctly".
  S2  A different analyst value on a case that passes the rules = DIFFER, counted as "would have released wrongly" and listed with both values.
  S3  A case that fails a rule is "sent to a person": never counted as released or wrong, whatever the analyst did.
  S4  An analyst who rejected / escalated / returned a case PeX would have released = ANALYST_NO_FIX, counted as wrong-release risk.
  S5  Rows that cannot be used (unknown case, bad action, fix without a value, bad minutes, duplicate in the file) are rejected with a reason; the rest load.
  S6  Loading the same case again replaces it; nothing is counted twice.
  S7  Values compare ignoring case and spacing.
  S8  Minutes are optional; time on would-have-released cases is summed.
  S9  By-profile rows add up to the totals.
  S10 Loading never changes a case, releases nothing, and leaves one audit event per load.
  S11 Only Administrators load; Administrators, Policy Owners, Supervisors and Audit read; others are refused.
  S12 Nothing loaded: zeros, no rates, a note that says how to start.
  S13 Verdicts do not depend on the release mode.
  S14 A profile that is never straight-through is never "would have released".
  S15 CSV upload works with the documented columns; a missing required column is refused.
  S16 Clearing removes the loaded rows (Administrator only, audited).
"""
import io

import pytest

from app.core.auth import create_token
from app.services.v2 import logic as lg
from app.services.v2 import policy, stp
from app.services.v2 import seed as v2seed
from app.services.v2.core import profile_code
from app.services.v2.rows import all_cases

ADMIN, OWNER1, OWNER2 = "ADM-0002", "POL-8001", "POL-8002"
SUP, OP, APPR, AUD = "SUP-2001", "OP-9012", "APR-3192", "AUD-5001"


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def fresh(client):
    v2seed.seed_v2()
    policy.reset_all()
    client.delete("/api/v2/shadow", headers=H(ADMIN))
    yield
    client.delete("/api/v2/shadow", headers=H(ADMIN))
    policy.reset_all()


def pex_view():
    """case_id -> (eligible, proposed value, profile) as PeX sees it now."""
    out = {}
    for c in all_cases():
        ch = lg.ext_of(c).get("change") or {}
        out[c["case_id"]] = (stp.evaluate(c)["eligible"], (ch.get("proposed") or {}).get("value"), profile_code(c.get("profile")), c)
    return out


def eligible_with_value(n=1):
    xs = [(k, v) for k, v in sorted(pex_view().items()) if v[0] and v[1] and v[2] not in stp.HARD_BLOCK_STP]
    assert len(xs) >= n, "the seed needs eligible cases with a proposed value"
    return xs[:n]


def blocked_with_value():
    xs = [(k, v) for k, v in sorted(pex_view().items()) if not v[0] and v[1]]
    assert xs
    return xs[0]


def fixed(case_id, value, **kw):
    return {"case_id": case_id, "action": "FIXED", "value": value, **kw}


def load(client, rows, uid=ADMIN):
    return client.post("/api/v2/shadow/rows", json={"rows": rows}, headers=H(uid))


def card(client, uid=ADMIN):
    r = client.get("/api/v2/shadow/scorecard", headers=H(uid))
    assert r.status_code == 200, r.text
    return r.json()


def verdicts(client, uid=ADMIN):
    r = client.get("/api/v2/shadow/cases", headers=H(uid))
    assert r.status_code == 200, r.text
    return {x["case_id"]: x for x in r.json()["items"]}


# S1 -------------------------------------------------------------------------------------------------------------
def test_matching_fix_on_eligible_case_is_released_correctly(client):
    (cid, v), = eligible_with_value()
    r = load(client, [fixed(cid, v[1])])
    assert r.status_code == 200 and r.json()["accepted"] == 1 and r.json()["rejected"] == []
    assert verdicts(client)[cid]["verdict"] == "AGREE"
    c = card(client)
    assert c["release"]["released_correctly"] == 1 and c["release"]["released_wrongly"]["count"] == 0
    assert c["compared"] == 1 and c["rates"]["agree_rate"] == 1.0 and c["rates"]["safe_release_rate"] == 1.0


# S2 -------------------------------------------------------------------------------------------------------------
def test_different_value_on_eligible_case_is_a_wrong_release_and_shows_both(client):
    (cid, v), = eligible_with_value()
    load(client, [fixed(cid, "SOMETHING ELSE ENTIRELY")])
    row = verdicts(client)[cid]
    assert row["verdict"] == "DIFFER" and row["pex_would_release"] is True
    assert row["pex_value"] == v[1] and row["analyst_value"] == "SOMETHING ELSE ENTIRELY"
    c = card(client)
    assert c["release"]["released_wrongly"] == {"count": 1, "differ": 1, "analyst_no_fix": 0}
    assert c["release"]["released_correctly"] == 0 and c["rates"]["safe_release_rate"] == 0.0


# S3 -------------------------------------------------------------------------------------------------------------
def test_case_failing_a_rule_goes_to_a_person_whatever_the_analyst_did(client):
    cid, v = blocked_with_value()
    load(client, [fixed(cid, v[1])])
    row = verdicts(client)[cid]
    assert row["pex_would_release"] is False and row["blocked_by"]
    c = card(client)
    assert c["release"]["sent_to_person"] == 1
    assert c["release"]["released_correctly"] == 0 and c["release"]["released_wrongly"]["count"] == 0


# S4 -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("action", ["REJECTED", "ESCALATED", "RETURNED"])
def test_analyst_who_did_not_fix_what_pex_would_release(client, action):
    (cid, _), = eligible_with_value()
    load(client, [{"case_id": cid, "action": action}])
    assert verdicts(client)[cid]["verdict"] == "ANALYST_NO_FIX"
    assert card(client)["release"]["released_wrongly"] == {"count": 1, "differ": 0, "analyst_no_fix": 1}


# S5 -------------------------------------------------------------------------------------------------------------
def test_unusable_rows_are_rejected_with_a_reason_and_the_rest_load(client):
    (cid, v), = eligible_with_value()
    rows = [fixed(cid, v[1]), fixed("NO-SUCH-CASE", "x"), {"case_id": cid, "action": "SHRUG"}, {"case_id": "PEX-XXX", "action": "FIXED"},
            fixed(cid, v[1], minutes=-3), fixed(cid, v[1], minutes="abc"), {"action": "FIXED", "value": "x"}]
    r = load(client, rows)
    assert r.status_code == 200
    b = r.json()
    assert b["accepted"] == 1 and len(b["rejected"]) == 6
    assert all(x["reason"] for x in b["rejected"]) and {x["row"] for x in b["rejected"]} == {2, 3, 4, 5, 6, 7}


def test_fix_without_a_value_is_rejected(client):
    (cid, _), = eligible_with_value()
    b = load(client, [{"case_id": cid, "action": "FIXED"}]).json()
    assert b["accepted"] == 0 and "value" in b["rejected"][0]["reason"].lower()


def test_duplicate_case_inside_one_file_is_rejected(client):
    (cid, v), = eligible_with_value()
    b = load(client, [fixed(cid, v[1]), fixed(cid, "other")]).json()
    assert b["accepted"] == 1 and len(b["rejected"]) == 1 and "twice" in b["rejected"][0]["reason"].lower()


# S6 -------------------------------------------------------------------------------------------------------------
def test_loading_a_case_again_replaces_it(client):
    (cid, v), = eligible_with_value()
    load(client, [fixed(cid, "wrong")])
    b = load(client, [fixed(cid, v[1])]).json()
    assert b["accepted"] == 1 and b["replaced"] == 1
    c = card(client)
    assert c["compared"] == 1 and c["release"]["released_correctly"] == 1 and c["release"]["released_wrongly"]["count"] == 0


# S7 -------------------------------------------------------------------------------------------------------------
def test_values_compare_ignoring_case_and_spacing(client):
    (cid, v), = eligible_with_value()
    load(client, [fixed(cid, "  " + str(v[1]).lower().replace(" ", "   ") + " ")])
    assert verdicts(client)[cid]["verdict"] == "AGREE"


# S8 -------------------------------------------------------------------------------------------------------------
def test_minutes_are_optional_and_summed_on_released_cases_only(client):
    (a, va), (b, vb) = eligible_with_value(2)
    cid, v = blocked_with_value()
    load(client, [fixed(a, va[1], minutes=12), fixed(b, vb[1]), fixed(cid, v[1], minutes=30)])
    t = card(client)["time"]
    assert t["minutes_on_released"] == 12 and t["cases_with_minutes"] == 2 and t["released_cases"] == 2
    assert t["minutes_all"] == 42


# S9 -------------------------------------------------------------------------------------------------------------
def test_by_profile_adds_up_to_the_totals(client):
    xs = eligible_with_value(5)
    rows = [fixed(k, v[1] if i % 2 else "nope") for i, (k, v) in enumerate(xs)]
    cid, bv = blocked_with_value()
    rows.append(fixed(cid, bv[1]))
    load(client, rows)
    c = card(client)
    bp = c["by_profile"]
    assert sum(p["compared"] for p in bp) == c["compared"]
    assert sum(p["released_correctly"] for p in bp) == c["release"]["released_correctly"]
    assert sum(p["released_wrongly"] for p in bp) == c["release"]["released_wrongly"]["count"]
    assert sum(p["sent_to_person"] for p in bp) == c["release"]["sent_to_person"]
    assert c["compared"] == c["release"]["released_correctly"] + c["release"]["released_wrongly"]["count"] + c["release"]["sent_to_person"]


# S10 ------------------------------------------------------------------------------------------------------------
def test_loading_changes_no_case_and_leaves_an_audit_event(client):
    (cid, v), = eligible_with_value()
    def loaded():
        ev = client.get("/api/v2/audit/events", params={"case_id": "SHADOW-COMPARISON", "page_size": 500}, headers=H(AUD)).json()["items"]
        return [e for e in ev if e["event"] == "Shadow comparison loaded"]
    before = {c["case_id"]: lg.status_of(c) for c in all_cases()}
    n = len(loaded())
    load(client, [fixed(cid, v[1])])
    assert {c["case_id"]: lg.status_of(c) for c in all_cases()} == before
    assert len(loaded()) == n + 1


# S11 ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("uid", [OP, APPR, OWNER1, SUP, AUD])
def test_only_administrators_load(client, uid):
    assert load(client, [], uid=uid).status_code == 403


@pytest.mark.parametrize("uid", [ADMIN, OWNER1, SUP, AUD])
def test_these_roles_can_read(client, uid):
    assert client.get("/api/v2/shadow/scorecard", headers=H(uid)).status_code == 200


@pytest.mark.parametrize("uid", [OP, APPR])
def test_other_roles_cannot_read(client, uid):
    assert client.get("/api/v2/shadow/scorecard", headers=H(uid)).status_code == 403
    assert client.get("/api/v2/shadow/cases", headers=H(uid)).status_code == 403


# S12 ------------------------------------------------------------------------------------------------------------
def test_empty_scorecard_has_zeros_no_rates_and_a_note(client):
    c = card(client)
    assert c["compared"] == 0 and c["release"]["released_correctly"] == 0
    assert c["rates"]["agree_rate"] is None and c["rates"]["safe_release_rate"] is None
    assert c["by_profile"] == [] and "load" in c["note"].lower()
    assert c["columns"] and c["columns"][0]["name"] == "case_id"


# S13 ------------------------------------------------------------------------------------------------------------
def test_verdicts_do_not_depend_on_the_release_mode(client):
    (cid, v), = eligible_with_value()
    load(client, [fixed(cid, v[1])])
    base = card(client)["release"]
    r = client.post("/api/v2/policy/changes", json={"key": "release_mode", "value": "REVIEW_EACH", "reason": "test"}, headers=H(OWNER1)).json()
    client.post(f"/api/v2/policy/changes/{r['id']}/approve", json={"note": "ok"}, headers=H(OWNER2))
    assert card(client)["release"] == base


# S14 ------------------------------------------------------------------------------------------------------------
def test_never_straight_through_profile_is_never_released(client):
    never = [(k, v) for k, v in sorted(pex_view().items()) if v[2] in stp.HARD_BLOCK_STP and v[1]]
    if not never:
        pytest.skip("no seeded case of a never-straight-through profile with a proposal")
    cid, v = never[0]
    load(client, [fixed(cid, v[1])])
    assert verdicts(client)[cid]["pex_would_release"] is False
    assert card(client)["release"]["released_correctly"] == 0


# S15 ------------------------------------------------------------------------------------------------------------
def test_csv_upload_and_missing_column(client):
    (cid, v), = eligible_with_value()
    csv = f"case_id,action,value,minutes,analyst_ref,resolved_at\n{cid},FIXED,{v[1]!s},9,AN-17,2026-11-02T10:00:00Z\n"
    r = client.post("/api/v2/shadow/upload", files={"file": ("a.csv", io.BytesIO(csv.encode()), "text/csv")}, headers=H(ADMIN))
    assert r.status_code == 200 and r.json()["accepted"] == 1
    assert verdicts(client)[cid]["verdict"] == "AGREE"
    bad = client.post("/api/v2/shadow/upload", files={"file": ("a.csv", io.BytesIO(b"case_id,value\nX,1\n"), "text/csv")}, headers=H(ADMIN))
    assert bad.status_code == 400 and "action" in bad.text


# S16 ------------------------------------------------------------------------------------------------------------
def test_clear_removes_rows_admin_only_and_audited(client):
    (cid, v), = eligible_with_value()
    load(client, [fixed(cid, v[1])])
    assert client.delete("/api/v2/shadow", headers=H(SUP)).status_code == 403
    assert card(client)["compared"] == 1
    assert client.delete("/api/v2/shadow", headers=H(ADMIN)).status_code == 200
    assert card(client)["compared"] == 0
    names = " ".join(e["event"] for e in client.get("/api/v2/audit/events", params={"case_id": "SHADOW-COMPARISON"}, headers=H(AUD)).json()["items"]).lower()
    assert "clear" in names
