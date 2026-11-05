"""Value model: what straight-through handling is worth, from the bank's own inputs. No PeX price is assumed.

  V1  Hours and cost saved are exact arithmetic on the inputs: cases x share x (minutes per case - review minutes) / 60 x hourly cost.
  V2  Scenario shares are shown side by side (default 20, 40, 60 percent); annual = 12 x monthly.
  V3  Inputs outside their range are refused with a reason; nothing is guessed.
  V4  Review minutes at or above handling minutes give zero saving, never a negative one.
  V5  Every figure comes with the assumptions behind it, in words.
  V6  Once shadow results are loaded, a "measured" scenario uses the share PeX would have released, and says whether wrong releases still exist.
  V7  Without shadow results there is no measured scenario and no invented one.
  V8  Same read access as the shadow scorecard.
"""
import pytest

from app.core.auth import create_token
from app.services.v2 import seed as v2seed
from app.services.v2 import policy
from tests.test_shadow_scorecard import eligible_with_value, fixed, load

ADMIN, OP, SUP = "ADM-0002", "OP-9012", "SUP-2001"
BASE = {"monthly_exceptions": 6000, "minutes_per_case": 15, "cost_per_hour": 48, "review_minutes": 3}


def H(uid):
    return {"Authorization": "Bearer " + create_token(uid)}


def val(client, uid=ADMIN, **kw):
    return client.get("/api/v2/value-model", params={**BASE, **kw}, headers=H(uid))


@pytest.fixture(autouse=True)
def fresh(client):
    v2seed.seed_v2()
    policy.reset_all()
    client.delete("/api/v2/shadow", headers=H(ADMIN))
    yield
    client.delete("/api/v2/shadow", headers=H(ADMIN))


def test_v1_v2_arithmetic_and_scenarios(client):
    r = val(client)
    assert r.status_code == 200, r.text
    d = r.json()
    assert [s["share"] for s in d["scenarios"] if s["kind"] == "assumed"] == [0.2, 0.4, 0.6]
    s = d["scenarios"][0]
    assert s["cases_per_month"] == 1200
    assert s["hours_saved_month"] == pytest.approx(1200 * (15 - 3) / 60)  # 240
    assert s["cost_saved_month"] == pytest.approx(240 * 48)
    assert s["cost_saved_year"] == pytest.approx(240 * 48 * 12)
    assert d["scenarios"][2]["hours_saved_month"] == pytest.approx(3600 * 12 / 60)


@pytest.mark.parametrize("bad", [{"monthly_exceptions": 0}, {"monthly_exceptions": 5_000_000}, {"minutes_per_case": 0}, {"minutes_per_case": 600},
                                 {"cost_per_hour": 0}, {"cost_per_hour": 5000}, {"review_minutes": -1}, {"monthly_exceptions": "abc"}])
def test_v3_bad_inputs_refused(client, bad):
    r = val(client, **bad)
    assert r.status_code in (400, 422) and r.text


def test_v4_no_negative_saving(client):
    d = val(client, review_minutes=20).json()
    assert all(s["hours_saved_month"] == 0 and s["cost_saved_month"] == 0 for s in d["scenarios"])


def test_v5_assumptions_are_stated(client):
    d = val(client).json()
    assert len(d["assumptions"]) >= 4 and all(isinstance(a, str) and a for a in d["assumptions"])
    assert any("price" in a.lower() for a in d["assumptions"])
    assert d["inputs"]["monthly_exceptions"] == 6000


def test_v6_measured_scenario_from_shadow_results(client):
    xs = eligible_with_value(3)
    rows = [fixed(xs[0][0], xs[0][1][1], minutes=10), fixed(xs[1][0], xs[1][1][1], minutes=14), fixed(xs[2][0], "nope", minutes=9)]
    assert load(client, rows).status_code == 200
    d = val(client).json()
    m = [s for s in d["scenarios"] if s["kind"] == "measured"]
    assert len(m) == 1
    assert m[0]["share"] == pytest.approx(3 / 3)  # all three loaded cases pass the rules: share released = eligible / compared
    assert m[0]["wrong_releases"] == 1 and "wrong" in m[0]["caveat"].lower()
    assert d["measured_minutes_per_case"] == pytest.approx((10 + 14 + 9) / 3)


def test_v7_no_measured_scenario_without_shadow(client):
    d = val(client).json()
    assert not [s for s in d["scenarios"] if s["kind"] == "measured"] and d["measured_minutes_per_case"] is None


def test_v8_access(client):
    assert val(client, uid=SUP).status_code == 200
    assert val(client, uid=OP).status_code == 403
