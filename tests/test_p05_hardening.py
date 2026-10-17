"""P0.5 hardening: strict lifecycle, signed bank callback, signed tokens, mode-aware handoff."""
import json
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.core.auth import create_token, verify_token
from app.api.endpoints.bank import sign_body, callback_secret
from app.services.data_loader import repo
from app.services.state_machine import transition_case, IllegalTransition, normalize_status
from app.services.outbound_port import resolve_handoff_state

client = TestClient(app)


def _case(status="DISPATCHED", cid="CASE-P05-T1"):
    c = {"case_id": cid, "status": status, "amount": 100.0, "currency": "USD", "timeline": []}
    return c


def test_status_normalization():
    assert normalize_status("HANDED_TO_BANK") == "DISPATCHED"
    assert normalize_status("LifecycleStage.APPROVED") == "APPROVED"
    assert normalize_status(None) is None


@pytest.mark.parametrize("target", ["SETTLED", "EXECUTED_CONFIRMED"])
def test_only_bank_signal_can_settle(target):
    with pytest.raises(IllegalTransition):
        transition_case(_case(), target, actor="OP-1", reason="try")
    transition_case(_case(), target, actor="BANK", reason="ok", is_bank_signal=True)


def test_illegal_transition_rejected():
    with pytest.raises(IllegalTransition):
        transition_case(_case("PENDING_APPROVAL"), "DISPATCHED", actor="OP-1", reason="skip approval")


def test_shadow_terminal():
    c = _case("APPROVED")
    transition_case(c, "SHADOW_RECORDED", actor="X", reason="shadow")
    with pytest.raises(IllegalTransition):
        transition_case(c, "DISPATCHED", actor="X", reason="resurrect")


def test_handoff_modes():
    assert resolve_handoff_state("APR-1", mode="SHADOW")[0] == "SHADOW_RECORDED"
    assert resolve_handoff_state("APR-1", mode="ASSISTED")[0] == "DISPATCHED"
    assert resolve_handoff_state("SYS-AUTONOMOUS-STP", policy_approved=True, mode="ASSISTED")[0] is None
    assert resolve_handoff_state(None, mode="LIVE")[0] is None
    assert resolve_handoff_state("SYS-AUTONOMOUS-STP", policy_approved=True, mode="LIVE")[0] == "DISPATCHED"


def test_token_roundtrip_and_tamper():
    t = create_token("APR-3191")
    assert verify_token(t) == "APR-3191"
    head, body, sig = t.split(".")
    assert verify_token(f"{head}.{body}.{sig[:-2]}xx") is None
    assert verify_token("garbage") is None


def _post_outcome(payload, sign=True, sig=None):
    raw = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if sign:
        headers["X-Bank-Signature"] = sig or sign_body(raw, callback_secret())
    return client.post("/api/bank/outcome", content=raw, headers=headers)


def _seed_dispatched(cid):
    c = _case("DISPATCHED", cid)
    repo.cases[cid] = c
    repo.save_case(c)


def test_callback_requires_valid_signature():
    _seed_dispatched("CASE-P05-SIG")
    p = {"case_id": "CASE-P05-SIG", "outcome": "SETTLED", "bank_reference": "B1", "clearing_system": "FEDWIRE"}
    assert _post_outcome(p, sign=False).status_code == 401
    assert _post_outcome(p, sig="deadbeef").status_code == 401
    assert normalize_status(repo.get_case("CASE-P05-SIG")["status"]) == "DISPATCHED"


def test_signed_callback_settles_and_is_idempotent():
    _seed_dispatched("CASE-P05-OK")
    p = {"case_id": "CASE-P05-OK", "outcome": "SETTLED", "bank_reference": "B2",
         "clearing_system": "FEDWIRE", "idempotency_key": "IDEM-P05-" + __import__("uuid").uuid4().hex}
    r = _post_outcome(p)
    assert r.status_code == 200, r.text
    assert normalize_status(repo.get_case("CASE-P05-OK")["status"]) == "SETTLED"
    r2 = _post_outcome(p)
    assert r2.status_code == 200 and r2.json().get("idempotent_replay") is True


def test_callback_cannot_settle_unsent_case():
    c = _case("PENDING_APPROVAL", "CASE-P05-BAD")
    repo.cases["CASE-P05-BAD"] = c
    repo.save_case(c)
    r = _post_outcome({"case_id": "CASE-P05-BAD", "outcome": "SETTLED", "bank_reference": "B3", "clearing_system": "FEDWIRE"})
    assert r.status_code == 409


def test_batch_release_blocks_operator_and_uses_token_identity():
    tok = create_token("OP-9013")  # operator (maker)
    r = client.post("/api/stp/batch-release", headers={"Authorization": f"Bearer {tok}"},
                    json={"case_ids": ["X"], "approver_id": "APR-3191", "approver_name": "Forged", "approver_role": "ADMIN"})
    assert r.status_code == 403


def test_stp_limit_is_unified():
    assert settings.STP_MAX_AMOUNT == 10000.0 or os.environ.get("PEX_STP_MAX_AMOUNT")
