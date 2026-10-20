"""A person who is not an approver is told so and told what to do. The API answers 403 with that message."""
import pytest

from app.services.v2 import seed as v2seed
from tests.test_ui_v2_api import MAKER, post


@pytest.fixture(autouse=True)
def seeded():
    v2seed.seed_v2()
    yield


def test_operator_approving_gets_a_clear_403(client):
    r = post(client, MAKER, "/cases/PEX-INV-0001/approve", {"reviewed": True}, expect=403)
    msg = r["error"]["message"]
    assert "not an approver" in msg and "Ask an approver" in msg
    assert r["error"]["code"] == "FORBIDDEN"
