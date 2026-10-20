"""Evidence dossier (5 steps per check). Acceptance tests from the requirements.

  R1  For each evidence check the user can open a dossier with five steps: where the data comes from (system of record),
      what was asked (the exact query), what came back, which governance rule judged it and the verdict, and when / how long.
  R2  The dossier moves Previous / Next through the case's checks.
  R3  The query and the answer show tokens, never real personal values (reveal stays a separate, logged act).
  R4  The rule verdict agrees with the check result.
  R5  It says whether the source is simulated or real.
"""
import json

import pytest

from app.core.auth import create_token
from app.services.data_loader import repo
from app.services.v2 import logic as lg
from app.services.v2 import seed as v2seed
from app.services.v2 import ext as xt

STEPS = ["System of record", "Data sought", "Data received", "Governance rule", "Latency and trace"]


def H(uid="SUP-2001"):
    return {"Authorization": "Bearer " + create_token(uid)}


@pytest.fixture(autouse=True)
def seeded():
    v2seed.seed_v2()
    yield


def cases_with_evidence():
    out = []
    for cid, c in repo._case_cache.items():
        ev = lg.ext_of(c).get("evidence") or []
        if len(ev) >= 2:
            out.append((cid, [e["id"] for e in ev]))
    return out


def dossier(client, cid, eid, uid="SUP-2001"):
    r = client.get(f"/api/v2/cases/{cid}/evidence/{eid}/dossier", headers=H(uid))
    assert r.status_code == 200, r.text
    return r.json()


def test_there_are_cases_with_evidence():
    assert len(cases_with_evidence()) >= 3


def test_every_check_has_the_five_steps(client):
    for cid, ids in cases_with_evidence()[:6]:
        for eid in ids:
            d = dossier(client, cid, eid)
            assert [s["title"] for s in d["steps"]] == STEPS, (cid, eid)
            s1, s2, s3, s4, s5 = d["steps"]
            assert s1["system"] and s1["mode"] in ("simulated", "real", "zone") and s1["authority"]
            assert s2["query"] and s2["call"]
            assert s3["result"] and "status" in s3
            assert s4["rule_id"] and s4["rule"] and s4["verdict"] in ("pass", "fail", "review", "info")
            assert s5["checked_at"] and isinstance(s5["latency_ms"], int) and s5["trace_hash"]


def test_previous_next_walk_the_whole_case(client):
    cid, ids = cases_with_evidence()[0]
    seen, cur, prev = [], ids[0], None
    while cur:
        d = dossier(client, cid, cur)
        assert d["position"] == len(seen) + 1 and d["total"] == len(ids) and d["prev_id"] == prev
        seen.append(cur)
        prev, cur = cur, d["next_id"]
    assert seen == ids


def test_unknown_check_is_404(client):
    cid, _ = cases_with_evidence()[0]
    assert client.get(f"/api/v2/cases/{cid}/evidence/NOPE/dossier", headers=H()).status_code == 404


@pytest.mark.parametrize("uid", ["OP-9012", "SUP-2001", "APR-3192", "CMP-6001", "AUD-5001", "ADM-0002"])
def test_no_real_values_in_any_dossier(client, uid):
    for cid, ids in cases_with_evidence()[:5]:
        c = repo.get_case(cid)
        raws = [c["creditor_party"]["party_name"], c["debtor_party"]["party_name"]]
        a = c.get("creditor_account") or {}
        if a.get("iban"):
            raws += [xt.iban_compact(a["iban"]), xt.iban_group(a["iban"])]
        blob = json.dumps([dossier(client, cid, e, uid) for e in ids])
        for raw in raws:
            assert raw not in blob, (cid, uid)


def test_query_uses_tokens(client):
    for cid, ids in cases_with_evidence()[:5]:
        for eid in ids:
            q = dossier(client, cid, eid)["steps"][1]
            if q["query"]:
                assert "TOK-" in json.dumps(q["query"]) or q["query"] == {}


def test_verdict_agrees_with_status(client):
    for cid, ids in cases_with_evidence():
        for eid in ids:
            d = dossier(client, cid, eid)
            status = d["steps"][2]["status"]
            verdict = d["steps"][3]["verdict"]
            if status in ("pass", "agree"):
                assert verdict == "pass", (cid, eid, status, verdict)
            if status in ("fail", "differs"):
                assert verdict in ("fail", "review"), (cid, eid, status, verdict)


def test_source_mode_is_stated_and_switchable(client, monkeypatch):
    from app.config import settings
    cid, ids = cases_with_evidence()[0]
    modes = {dossier(client, cid, e)["steps"][0]["mode"] for e in ids}
    assert modes <= {"simulated", "zone"}
    monkeypatch.setattr(settings, "CONNECTOR_MODES", "CUSTM=real")
    # status of the connector is reported, not hidden, when switched
    r = client.get("/api/v2/connectors", headers=H("ADM-0002"))
    assert r.status_code == 200
    assert any(c["key"] == "CUSTM" and c["mode"] == "real" for c in (r.json().get("connectors") if isinstance(r.json(), dict) else r.json()))
