"""Bank-wide dashboard: acceptance tests written from the requirements.

Requirements (from the product owner)
  R1  Everyone sees the same bank-wide picture: what is going on, where something is stuck, which cases may breach SLA.
  R2  It says WHERE each case is (stage) and WITH WHOM.
  R3  Numbers add up (SLA bands and stages both sum to the open work).
  R4  Each role also gets a few extras for its own job.
  R5  No real personal values on the dashboard.
  R6  Every role has the dashboard in its menu, first.

Run:  DATABASE_URL=sqlite:////tmp/dash.db python3 -m pytest tests/test_dashboard.py -q
"""
import json
from datetime import timedelta

import pytest

from app.core.auth import create_token
from app.services.data_loader import repo
from app.services.v2 import logic as lg
from app.services.v2 import seed as v2seed
from app.services.v2.core import ext_store, iso, now

MAKER, SUP, APPR, RSK, CMP, AUD, ADM = "OP-9012", "SUP-2001", "APR-3192", "RSK-7714", "CMP-6001", "AUD-5001", "ADM-0002"
ROLES = [MAKER, SUP, APPR, RSK, CMP, AUD, ADM]
FINAL = lg.DONE - {"DISPATCHED"}


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def seeded():
    v2seed.seed_v2()
    yield


def dash(client, uid=SUP, **q):
    r = client.get("/api/v2/dashboard", params=q, headers=H(uid))
    assert r.status_code == 200, r.text
    return r.json()


def expected_open():
    return sum(1 for c in repo._case_cache.values() if lg.status_of(c) not in lg.DONE)


# R1 ------------------------------------------------------------------------------------------------------------
def test_every_role_sees_the_same_bank_wide_numbers(client):
    base = dash(client, SUP)
    assert base["scope"]["label"] == "Bank-wide"
    for uid in ROLES:
        d = dash(client, uid)
        assert d["scope"]["label"] == "Bank-wide"
        assert d["headline"] == base["headline"] and d["sla"] == base["sla"] and d["stages"] == base["stages"], uid


def test_open_work_matches_the_case_store(client):
    d = dash(client)
    tile = {t["key"]: t["value"] for t in d["headline"]}
    assert tile["open"] == expected_open()
    assert {"open", "awaiting_approval", "compliance_holds", "sla_breached", "sla_under_1h", "stuck", "with_bank"} <= set(tile)


# R3 ------------------------------------------------------------------------------------------------------------
def test_sla_bands_and_stages_add_up_to_open_work(client):
    d = dash(client)
    open_n = {t["key"]: t["value"] for t in d["headline"]}["open"]
    assert sum(b["count"] for b in d["sla"]["bands"]) == open_n
    assert sum(s["count"] for s in d["stages"] if s["key"] != "with_bank") == open_n
    assert sum(b["count"] for b in d["ageing"]) == open_n


def test_at_risk_list_is_ordered_and_explains_itself(client):
    d = dash(client)
    risk = d["at_risk"]
    assert risk, "the seeded data has cases near or past cutoff"
    left = [r["cutoff"]["seconds_left"] for r in risk]
    assert left == sorted(left)
    for r in risk:
        assert r["case_id"].startswith("PEX-") and r["stage"] and r["with"]["name"] and r["link"] == f"/cases/{r['case_id']}"
        assert r["cutoff"]["band"] in ("passed", "under_1h")


# R2 ------------------------------------------------------------------------------------------------------------
def test_stuck_case_names_the_stage_the_owner_and_the_wait(client):
    cid = "PEX-INV-0001"                                            # pending approval
    e = ext_store.get(cid)
    e["submitted_at"] = iso(now() - timedelta(hours=3))
    e["last_change_at"] = iso(now() - timedelta(hours=3))
    ext_store.put(cid, e)
    d = dash(client, stuck_limit=200)
    row = next(s for s in d["stuck"] if s["case_id"] == cid)
    assert row["stage"] == "Pending approval" and row["with"]["name"] and row["minutes"] >= 170
    assert "approver" in row["reason"].lower()


def test_status_unknown_is_flagged_as_stuck_with_the_bank(client):
    cid = "PEX-TMO-0044"
    e = ext_store.get(cid)
    e["last_change_at"] = iso(now() - timedelta(hours=2))
    e.pop("last_status_check", None)
    ext_store.put(cid, e)
    c = repo.get_case(cid)
    c["handed_off_at"] = iso(now() - timedelta(hours=2))
    d = dash(client, stuck_limit=200)
    row = next(s for s in d["stuck"] if s["case_id"] == cid)
    assert row["with"]["name"] == "Bank operations" and "bank" in row["reason"].lower()
    stage = next(s for s in d["stages"] if s["key"] == "status_unknown")
    assert stage["count"] >= 1


def test_where_cases_are_and_with_whom_workload(client):
    d = dash(client)
    keys = {s["key"] for s in d["stages"]}
    assert {"with_maker", "pending_approval", "compliance_hold", "status_unknown", "with_bank"} <= keys
    assert d["workload"] and all({"name", "role", "open", "at_risk"} <= set(w) for w in d["workload"])
    assert d["rails"] and all({"rail", "open", "at_risk"} <= set(r) for r in d["rails"])


# R4 ------------------------------------------------------------------------------------------------------------
def test_each_role_gets_its_own_extras(client):
    titles = {}
    for uid in ROLES:
        x = dash(client, uid)["role_extras"]
        assert x["title"] and x["items"] and all({"label", "value"} <= set(i) for i in x["items"])
        titles[uid] = x["title"]
    assert len(set(titles.values())) >= 5


def test_admin_extras_show_connectors_and_audit_extras_show_reveals(client):
    assert any("connector" in i["label"].lower() for i in dash(client, ADM)["role_extras"]["items"])
    assert any("reveal" in i["label"].lower() for i in dash(client, AUD)["role_extras"]["items"])


# R5 ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("cid", ["PEX-INV-0001", "PEX-CON-0031", "PEX-NAM-0027", "PEX-LOW-0096"])
def test_no_real_personal_values_on_the_dashboard(client, cid):
    from app.services.v2 import ext as xt
    c = repo.get_case(cid)
    blob = json.dumps(dash(client, APPR))
    for raw in (c["creditor_party"]["party_name"], c["debtor_party"]["party_name"], xt.iban_compact(c["creditor_account"].get("iban", "x" * 20)),
                xt.iban_group(c["creditor_account"].get("iban", "x" * 20))):
        assert raw not in blob


# R6 ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("uid", ROLES)
def test_dashboard_is_first_in_every_roles_menu(client, uid):
    r = client.get("/api/v2/me", headers=H(uid)).json()
    assert r["nav"][0]["key"] == "dashboard" and r["nav"][0]["path"] == "/dashboard"
    assert [n["key"] for n in r["nav"]].count("dashboard") == 1
