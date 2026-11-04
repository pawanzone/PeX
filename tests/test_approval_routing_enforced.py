"""The approval engine enforces the pack's routing: compliance profiles need Compliance then Risk; others follow the amount rule."""
import pytest

from app.schemas.approval import ApprovalAction, ApprovalSubmission
from app.schemas.canonical import LifecycleStage
from app.services.approval_engine import approval_engine
from app.services.data_loader import repo
from app.services.file_watcher import PROFILE_CODE_TO_ENUM


def _pending(idx, code, amount=40_000.0, queue=None):
    case = list(repo.cases.values())[idx]
    case.update({"amount": amount, "status": LifecycleStage.PENDING_APPROVAL, "profile": PROFILE_CODE_TO_ENUM[code],
                 "maker_id": "OP-9012", "dual_auth_required": amount >= 250_000.0, "queue": queue or ("Compliance" if code.startswith("CO") else "Repair")})
    repo.approvals[case["case_id"]] = []
    case["approval_history"] = []
    return case["case_id"]


def _approve(cid, approver):
    return approval_engine.process_approval_action(
        ApprovalSubmission(case_id=cid, action=ApprovalAction.APPROVE, comments="test"), approver_id=approver)


def test_compliance_profile_small_amount_still_needs_two_steps():
    cid = _pending(2, "CO-01")
    ok, msg, rec, stage = _approve(cid, "CMP-4420")
    assert ok and stage == LifecycleStage.AWAITING_SECOND_APPROVAL, msg


def test_second_step_must_be_a_risk_approver():
    cid = _pending(3, "CO-02")
    assert _approve(cid, "CMP-4420")[0]
    ok, msg, *_ = _approve(cid, "CMP-5502")          # another compliance approver: not enough
    assert not ok and "Risk Approver" in msg
    ok, msg, rec, stage = _approve(cid, "RSK-7714")
    assert ok and stage == LifecycleStage.APPROVED and rec.step_number == 2, msg


def test_first_step_must_be_a_compliance_approver():
    cid = _pending(4, "CO-03")
    ok, msg, *_ = _approve(cid, "RSK-7714")           # risk cannot go first
    assert not ok and "Compliance Approver" in msg
    ok, msg, *_ = _approve(cid, "ADM-0001")           # nor an admin
    assert not ok and "Compliance Approver" in msg


def test_same_person_cannot_sign_both_steps():
    cid = _pending(5, "CO-05")
    assert _approve(cid, "CMP-4420")[0]
    ok, msg, *_ = _approve(cid, "CMP-4420")
    assert not ok


def test_single_approver_profile_is_one_step_below_the_threshold():
    cid = _pending(6, "ST-04")
    ok, msg, rec, stage = _approve(cid, "APR-3191")
    assert ok and stage == LifecycleStage.APPROVED, msg


def test_single_approver_profile_goes_dual_at_the_threshold():
    cid = _pending(7, "ST-05", amount=250_000.0)
    ok, msg, rec, stage = _approve(cid, "APR-3191")
    assert ok and stage == LifecycleStage.AWAITING_SECOND_APPROVAL, msg


def test_decline_actions_are_not_role_restricted():
    cid = _pending(8, "CO-06")
    ok, *_ = approval_engine.process_approval_action(
        ApprovalSubmission(case_id=cid, action=ApprovalAction.RETURN_TO_MAKER, comments="more evidence"), approver_id="RSK-7714")
    assert ok


def test_older_profiles_unchanged_by_pack_routing():
    cid = _pending(9, "DQ-03")
    ok, msg, rec, stage = _approve(cid, "APR-3191")
    assert ok and stage == LifecycleStage.APPROVED, msg


def _release(cid):
    from app.services.v2 import ext as xt
    xt.ext_store.put(cid, {"compliance": {"released_by": {"user_id": "CMP-4420", "name": "Compliance"}, "released": True}}, persist=False)


def test_after_a_compliance_release_one_risk_approval_finishes_it():
    cid = _pending(10, "CO-01")
    _release(cid)
    ok, msg, *_ = _approve(cid, "CMP-5502")
    assert not ok and "Risk Approver" in msg
    ok, msg, rec, stage = _approve(cid, "RSK-7714")
    assert ok and stage == LifecycleStage.APPROVED, msg


def test_v2_gate_and_is_dual_agree_with_the_engine():
    from app.services.v2 import logic as lg
    from app.core.security import get_persona
    cid = _pending(11, "CO-08")
    case = repo.cases[cid]
    assert lg.is_dual(case) is True                       # compliance has not signed off yet
    ok, code, msg = lg.approve_gate(case, get_persona("RSK-7714"))
    assert not ok and "Compliance Approver" in msg        # risk cannot go first
    _release(cid)
    assert lg.is_dual(case) is False                      # release was step one
    ok, code, msg = lg.approve_gate(case, get_persona("RSK-7714"))
    assert ok, msg
    ok, code, msg = lg.approve_gate(case, get_persona("APR-3191"))
    assert not ok and "Risk Approver" in msg              # ops approver cannot finish a compliance case
    cid2 = _pending(12, "ST-07")
    assert lg.is_dual(repo.cases[cid2]) is False
