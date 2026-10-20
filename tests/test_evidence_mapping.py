"""One checklist, one story. The AI view's expected evidence is linked to the checks that were run.

  M1  Every expected item says how it is covered: a check that was run, the payment instruction itself, or not run.
  M2  Evidence nobody checked earns no credit. An item with no check behind it is "not run" and is not counted as present.
  M3  Each item that was checked points at the check that covers it, so the two tabs can be read side by side.
  M4  A must-have item that was not run is a gap and is named in the reasons.
  M5  The full set of checks on the demo invalid-IBAN cases is run, so those cases score on real evidence.
  M6  Cases whose checks are not linked to the checklist say so instead of claiming the items are present.
"""
import copy

import pytest

from app.services.data_loader import repo
from app.services.v2 import logic as lg
from app.services.v2 import seed as v2seed


@pytest.fixture(autouse=True)
def seeded():
    v2seed.seed_v2()
    yield


def conf(case_id, mutate=None):
    case = repo.get_case(case_id)
    ext = copy.deepcopy(lg.ext_of(case))
    if mutate:
        mutate(ext)
    return lg.confidence_of(case, ext), ext


def by_name(res):
    return {i["name"]: i for i in res["items"]}


def test_demo_invalid_iban_case_runs_the_full_set_of_checks():
    res, ext = conf("PEX-INV-0002")
    checks = [r["check"] for r in ext["evidence"]]
    assert len(checks) >= 5, checks
    items = by_name(res)
    assert all(i["state"] == "PRESENT" for i in items.values())
    assert items["Original payload (creditor IBAN, parties)"]["basis"] == "instruction"
    assert items["CoP / VoP name check"]["basis"] == "check"
    assert items["Beneficiary account status (open / active)"]["basis"] == "check"
    assert res["coverage_pct"] == 100


def test_every_checked_item_points_at_its_check():
    res, ext = conf("PEX-INV-0002")
    ids = {r["id"] for r in ext["evidence"]}
    for i in res["items"]:
        if i["basis"] == "check":
            assert i["check_id"] in ids and i["check"]


def test_not_run_earns_no_credit():
    def drop_vop(ext):
        ext["evidence"] = [r for r in ext["evidence"] if "holder" not in r["check"].lower()]
    res, _ = conf("PEX-INV-0002", drop_vop)
    it = by_name(res)["CoP / VoP name check"]
    assert it["state"] == "NOT_RUN" and it["basis"] == "none"
    assert res["coverage_pct"] == 90          # the name check carries weight 10
    assert res["not_run"] == 1 and res["checked"] == 4


def test_must_have_not_run_is_a_named_gap():
    def drop_dir(ext):
        ext["evidence"] = [r for r in ext["evidence"] if "directory" not in r["check"].lower()]
    res, _ = conf("PEX-INV-0002", drop_dir)
    assert by_name(res)["Beneficiary SSI master record"]["state"] == "NOT_RUN"
    assert any("Beneficiary SSI master record" in r for r in res["reasons"])
    assert res["extra_approval"]


def test_missing_data_case_links_each_item_to_what_was_found():
    res, ext = conf("PEX-BEN-0012")
    items = by_name(res)
    assert items["Original payload (parties present)"]["state"] == "PRESENT"
    assert items["Required-field set for corridor (R16 / scheme rules)"]["state"] == "MISSING"
    assert items["Prior payments to same beneficiary"]["state"] == "MISSING"
    assert items["Client confirmation of beneficiary details"]["state"] == "MISSING"
    assert res["coverage_pct"] == 15


def test_unlinked_cases_say_so():
    res, _ = conf("PEX-INV-0042")
    assert res["linked"] is False
    assert all(i["basis"] == "assumed" for i in res["items"])


def test_linked_flag_on_demo_case():
    res, _ = conf("PEX-INV-0002")
    assert res["linked"] is True
