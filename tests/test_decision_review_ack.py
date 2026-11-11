"""Every checker decision (approve, return to maker, reject) needs the 'I have reviewed the change summary and evidence' confirmation.

Run:  DATABASE_URL=sqlite:////tmp/v2ack.db python3 -m pytest tests/test_decision_review_ack.py -q
"""
import pytest

from app.services.data_loader import repo
from app.services.v2 import seed as v2seed
from tests.test_ui_v2_api import APPR, H, MAKER, post

CASE = "PEX-INV-0001"
RC = {"reason_code": "EVIDENCE_INCOMPLETE", "comment": "Attach statement."}


@pytest.fixture(autouse=True)
def seeded():
    v2seed.seed_v2()
    yield


def _err(client, path, body, expect=422):
    r = client.post("/api/v2" + path, json=body, headers=H(APPR))
    assert r.status_code == expect, f"{path} -> {r.status_code} {r.text}"
    return r.json()


def test_return_without_review_confirmation_is_refused(client):
    e = _err(client, f"/cases/{CASE}/return", dict(RC))
    assert e["error"]["field"] == "reviewed"
    assert repo.get_case(CASE)["status"] != "RETURNED_FOR_REWORK"


def test_reject_without_review_confirmation_is_refused(client):
    e = _err(client, f"/cases/{CASE}/reject", dict(RC))
    assert e["error"]["field"] == "reviewed"
    assert repo.get_case(CASE)["status"] != "REJECTED"


@pytest.mark.parametrize("action", ["return", "reject"])
def test_reviewed_false_is_refused(client, action):
    _err(client, f"/cases/{CASE}/{action}", {**RC, "reviewed": False})


@pytest.mark.parametrize("action", ["return", "reject"])
def test_reason_and_comment_still_required_with_confirmation(client, action):
    _err(client, f"/cases/{CASE}/{action}", {"reviewed": True})
    _err(client, f"/cases/{CASE}/{action}", {"reviewed": True, "reason_code": "EVIDENCE_INCOMPLETE"})


def test_return_with_confirmation_works(client):
    post(client, APPR, f"/cases/{CASE}/return", {**RC, "reviewed": True})
    assert repo.get_case(CASE)["status"] == "RETURNED_FOR_REWORK"


def test_reject_with_confirmation_works(client):
    post(client, APPR, f"/cases/{CASE}/reject", {**RC, "reviewed": True})
    assert repo.get_case(CASE)["status"] == "REJECTED"


def test_approve_still_needs_confirmation(client):
    _err(client, f"/cases/{CASE}/approve", {})
    _err(client, f"/cases/{CASE}/approve", {"reviewed": False})


def test_refused_decline_is_not_audited(client):
    before = len(client.get(f"/api/v2/audit/events?case_id={CASE}", headers=H("AUD-5001")).json())
    _err(client, f"/cases/{CASE}/return", dict(RC))
    after = len(client.get(f"/api/v2/audit/events?case_id={CASE}", headers=H("AUD-5001")).json())
    assert after == before
