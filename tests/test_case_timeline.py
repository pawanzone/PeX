"""Case page tabs need a per-case audit timeline that every role who can open the case may read.

  R1  Any role that can open a case can read its timeline (not only Audit).
  R2  Only that case's events, newest last, with who acted (name and role) and what happened.
  R3  No real personal values.
"""
import json

import pytest

from app.core.auth import create_token
from app.services.data_loader import repo
from app.services.v2 import seed as v2seed
from app.services.v2 import ext as xt


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def seeded():
    v2seed.seed_v2()
    yield


@pytest.mark.parametrize("uid", ["OP-9012", "SUP-2001", "APR-3192", "RSK-7714", "CMP-6001", "AUD-5001", "ADM-0002"])
def test_every_role_can_read_a_case_timeline(client, uid):
    r = client.get("/api/v2/cases/PEX-INV-0001/timeline", headers=H(uid))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["case_id"] == "PEX-INV-0001" and d["items"]


def test_events_belong_to_the_case_in_time_order_and_name_the_actor(client):
    d = client.get("/api/v2/cases/PEX-INV-0001/timeline", headers=H("OP-9012")).json()
    times = [e["time"] for e in d["items"]]
    assert times == sorted(times)
    for e in d["items"]:
        assert e["case_id"] == "PEX-INV-0001" and e["event"] and e["actor"] and e["role"]


def test_unknown_case_is_404(client):
    assert client.get("/api/v2/cases/PEX-NOPE-9999/timeline", headers=H("OP-9012")).status_code == 404


def test_no_real_values_in_timeline(client):
    for cid in ("PEX-INV-0001", "PEX-CON-0031", "PEX-NAM-0027"):
        c = repo.get_case(cid)
        blob = json.dumps(client.get(f"/api/v2/cases/{cid}/timeline", headers=H("SUP-2001")).json())
        for raw in (c["creditor_party"]["party_name"], c["debtor_party"]["party_name"], xt.iban_compact((c.get("creditor_account") or {}).get("iban", "x" * 22))):
            assert raw not in blob
