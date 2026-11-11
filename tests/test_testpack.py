"""The manual-test data pack: every one of the 41 profiles has a clean case in a known state, and the three kinds of clean workflow run end to end.

Run:  DATABASE_URL=sqlite:////tmp/v2tp.db python3 -m pytest tests/test_testpack.py -q
"""
import pytest

from app.services.v2 import library as lib
from app.services.v2 import seed as v2seed
from app.services.v2 import testpack
from tests.test_ui_v2_api import H, post

MAKER, OPS1, OPS2, CMP1, RISK = "OP-9012", "APR-3191", "APR-3192", "CMP-4420", "RSK-7714"
CODES = [r["code"] for r in lib.library()["profiles"]]
TWO_STEP = {"CO-01", "CO-02", "CO-03", "CO-05", "CO-06", "CO-08"}
INVEST = {"ST-04", "ST-05", "ST-07"}


@pytest.fixture(autouse=True, scope="module")
def pack():
    v2seed.seed_v2()
    return testpack.seed_testpack()


def _page(client, uid, cid):
    r = client.get(f"/api/v2/cases/{cid}/page", headers=H(uid))
    assert r.status_code == 200, r.text
    return r.json()


def test_pack_has_57_cases_and_all_41_profiles(pack):
    assert pack["cases"] == 57
    clean = {m["code"] for m in testpack.PACK if m["scenario"] == "CLEAN"}
    assert clean == set(CODES) and len(clean) == 41


@pytest.mark.parametrize("code", CODES)
def test_each_profile_starts_in_the_right_state(client, code):
    cid = f"TST-{code.replace('-', '')}-01"
    v = _page(client, MAKER, cid)["variant"]
    if code.startswith("CO-"):
        assert v == "COMPLIANCE_HOLD"
    elif code in INVEST:
        pg = _page(client, OPS1, cid)
        assert v == "GENERIC" and len(pg["decision_request"]["options"]) == 3
    elif code == "DQ-03":
        assert v == "MISSING_INFO"
    else:
        assert v == "DECISION"


def test_maker_checker_clean_path(client):
    cid = "TST-DQ02-01"
    post(client, MAKER, f"/cases/{cid}/submit", {"handover_note": "checked"})
    out = post(client, OPS1, f"/cases/{cid}/approve", {"reviewed": True, "comment": "ok"})
    assert out["status"] in ("DISPATCHED", "SHADOW_RECORDED")


def test_compliance_then_risk_clean_path(client):
    cid = "TST-CO01-01"
    post(client, CMP1, f"/cases/{cid}/compliance/decision", {"decision": "release", "reason_code": "FALSE_MATCH_NAME", "comment": "different entity"})
    post(client, OPS1, f"/cases/{cid}/approve", {"reviewed": True, "comment": "x"}, expect=403)
    out = post(client, RISK, f"/cases/{cid}/approve", {"reviewed": True, "comment": "ok"})
    assert out["status"] in ("DISPATCHED", "SHADOW_RECORDED")


def test_investigation_clean_path_needs_a_second_person(client):
    cid = "TST-ST05-01"
    post(client, OPS1, f"/cases/{cid}/decision", {"option": "CONTINGENCY_CLEARING_WINDOW_DISPATCH", "comment": "contingency window"})
    post(client, OPS1, f"/cases/{cid}/approve", {"reviewed": True, "comment": "x"}, expect=403)
    out = post(client, OPS2, f"/cases/{cid}/approve", {"reviewed": True, "comment": "ok"})
    assert out["status"] in ("DISPATCHED", "SHADOW_RECORDED")


def test_dual_authorisation_needs_two_risk_approvers(client):
    cid = "TST-DQ01-08"
    post(client, MAKER, f"/cases/{cid}/submit", {"handover_note": "n"})
    post(client, OPS1, f"/cases/{cid}/approve", {"reviewed": True, "comment": "x"}, expect=403)
    post(client, RISK, f"/cases/{cid}/approve", {"reviewed": True, "comment": "first"})
    post(client, RISK, f"/cases/{cid}/approve", {"reviewed": True, "comment": "again"}, expect=403)
    out = post(client, "RSK-7715", f"/cases/{cid}/approve", {"reviewed": True, "comment": "second"})
    assert out["status"] in ("DISPATCHED", "SHADOW_RECORDED")
