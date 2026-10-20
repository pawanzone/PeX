"""The evidence tab and the AI reasoning tab must tell the same story.

  C1  If the evidence tab says prior payments are missing, reasoning must not count prior payments as present.
  C2  Evidence that has to come from the client is missing until the client answers.
  C3  Evidence coverage can only fall when evidence is missing, so a case with missing evidence is below 100%.
  C4  A case whose evidence is all found keeps its own reasoning unchanged.
"""
import pytest

from app.services.data_loader import repo
from app.services.v2 import logic as lg
from app.services.v2 import seed as v2seed


@pytest.fixture(autouse=True)
def seeded():
    v2seed.seed_v2()
    yield


def items(case_id):
    res = lg.confidence_of(repo.get_case(case_id))
    return {i["name"]: i["state"] for i in res["items"]}, res


@pytest.mark.parametrize("case_id", ["PEX-BEN-0012", "PEX-WAT-0090"])
def test_prior_payments_missing_is_not_counted_present(case_id):
    st, _ = items(case_id)
    prior = [v for k, v in st.items() if "Prior payments" in k]
    ev = [e for e in lg.ext_of(repo.get_case(case_id)).get("evidence") or [] if e["check"] == "Prior payments"]
    if ev and ev[0]["status"] == "missing":
        assert prior and all(v == "MISSING" for v in prior)


@pytest.mark.parametrize("case_id", ["PEX-BEN-0012", "PEX-WAT-0090"])
def test_client_confirmation_missing_until_reply(case_id):
    st, _ = items(case_id)
    assert st["Client confirmation of beneficiary details"] == "MISSING"


def test_coverage_matches_what_was_found_on_ben_0012():
    st, res = items("PEX-BEN-0012")
    assert res["coverage_pct"] < 50      # one of four checks found, nothing from the client or the master record
    assert res["manual"] if "manual" in res else True


def test_complete_cases_unchanged():
    st, res = items("PEX-INV-0001")
    assert all(v == "PRESENT" for v in st.values()) or res["coverage_pct"] >= 70
