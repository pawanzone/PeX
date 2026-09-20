"""Tests for Role-Gated Approvals, Maker-Checker, and Dual-Authorization."""
import pytest
from app.services.approval_engine import approval_engine
from app.schemas.approval import ApprovalSubmission, ApprovalAction
from app.services.data_loader import repo
from app.schemas.canonical import LifecycleStage

def test_operator_cannot_approve_maker_checker():
    case = list(repo.cases.values())[0]
    case_id = case["case_id"]
    
    sub = ApprovalSubmission(
        case_id=case_id,
        action=ApprovalAction.APPROVE,
        comments="Operator trying to self-approve"
    )
    # Amina Okafor is an OPERATOR
    success, msg, rec, stage = approval_engine.process_approval_action(sub, approver_id="OP-8472")
    assert success is False
    assert "Maker-Checker" in msg or "Operator" in msg

def test_ops_approver_can_approve_operational_repair():
    # Find or set a low-value repair case
    case = list(repo.cases.values())[0]
    case["amount"] = 42000.0
    case["status"] = LifecycleStage.PENDING_APPROVAL
    case_id = case["case_id"]
    
    sub = ApprovalSubmission(
        case_id=case_id,
        action=ApprovalAction.APPROVE,
        comments="Approved by Ops Approver"
    )
    # Daniel Osei is OPERATIONS_APPROVER
    success, msg, rec, stage = approval_engine.process_approval_action(sub, approver_id="APR-3191")
    assert success is True
    assert stage == LifecycleStage.APPROVED
    assert rec.approver_id == "APR-3191"

def test_dual_authorization_for_high_value_transaction():
    # Create high value case (>= $250k)
    case = list(repo.cases.values())[1]
    case["amount"] = 350000.0
    case["status"] = LifecycleStage.PENDING_APPROVAL
    case_id = case["case_id"]
    repo.approvals[case_id] = [] # Reset approvals
    
    sub = ApprovalSubmission(
        case_id=case_id,
        action=ApprovalAction.APPROVE,
        comments="First approval by Ops Approver"
    )
    # 1st Approval: Daniel Osei
    ok1, msg1, rec1, stage1 = approval_engine.process_approval_action(sub, approver_id="APR-3191")
    assert ok1 is True
    assert stage1 == LifecycleStage.AWAITING_SECOND_APPROVAL
    
    # Same approver cannot do second approval
    sub2 = ApprovalSubmission(
        case_id=case_id,
        action=ApprovalAction.APPROVE,
        comments="Second approval attempt by same person"
    )
    ok_dup, msg_dup, _, _ = approval_engine.process_approval_action(sub2, approver_id="APR-3191")
    assert ok_dup is False
    assert "Dual Authorization violation" in msg_dup
    
    # 2nd Approval by distinct officer: Kenji Watanabe (Risk)
    ok2, msg2, rec2, stage2 = approval_engine.process_approval_action(sub2, approver_id="RSK-7714")
    assert ok2 is True
    assert stage2 == LifecycleStage.APPROVED
