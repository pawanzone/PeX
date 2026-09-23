"""
P1 Remediation Batch 2 Dedicated Test Suite:
State Machine, Approval Governance & HITL Integrity

Covers:
- MST-040: Approval Allowed in INVESTIGATING (ApprovalEngine disallows INVESTIGATING & INGESTED)
- MST-041: MODIFY Bypasses Dual Authorization (MODIFY respects dual-auth governance)
- MST-042: Ingestion Sets PENDING_APPROVAL (Bank event ingestion initializes status to INGESTED)
- MST-043: check_can_approve Ignores Monetary Limits (Enforces persona.max_approval_amount and role limits)
- MST-011: Double Audit Logging on Approvals (Single authoritative audit log per approval)
"""
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_loader import repo
from app.services.approval_engine import approval_engine
from app.services.audit_service import audit_service
from app.core.security import check_can_approve, get_persona
from app.schemas.approval import ApprovalSubmission, ApprovalAction, UserRole
from app.schemas.canonical import LifecycleStage, ExceptionProfile, ExceptionDomain
from app.schemas.bank_events import RawBankEvent
from app.schemas.recommendation import ProposedFieldChange


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# MST-040: Approval Allowed in INVESTIGATING
# ==============================================================================

def test_mst_040_approval_rejected_in_investigating():
    """Verify that approval engine rejects cases in INVESTIGATING status."""
    case_id = f"CASE-MST040-INV-{uuid.uuid4().hex[:6]}"
    repo.save_case({
        "case_id": case_id,
        "amount": 50000.0,
        "status": LifecycleStage.INVESTIGATING.value,
        "queue": "Repair",
        "approval_history": []
    })

    sub = ApprovalSubmission(
        case_id=case_id,
        action=ApprovalAction.APPROVE,
        comments="Attempting approval in INVESTIGATING state"
    )
    ok, msg, rec, stage = approval_engine.process_approval_action(sub, approver_id="APR-3191")
    assert ok is False
    assert "not awaiting approval" in msg
    assert "INVESTIGATING" in msg


def test_mst_040_approval_rejected_in_ingested():
    """Verify that approval engine rejects cases in INGESTED status."""
    case_id = f"CASE-MST040-ING-{uuid.uuid4().hex[:6]}"
    repo.save_case({
        "case_id": case_id,
        "amount": 50000.0,
        "status": LifecycleStage.INGESTED.value,
        "queue": "Repair",
        "approval_history": []
    })

    sub = ApprovalSubmission(
        case_id=case_id,
        action=ApprovalAction.APPROVE,
        comments="Attempting approval in INGESTED state"
    )
    ok, msg, rec, stage = approval_engine.process_approval_action(sub, approver_id="APR-3191")
    assert ok is False
    assert "not awaiting approval" in msg
    assert "INGESTED" in msg


def test_mst_040_approval_accepted_in_pending_approval():
    """Verify that approval engine accepts cases in PENDING_APPROVAL status."""
    case_id = f"CASE-MST040-PA-{uuid.uuid4().hex[:6]}"
    repo.save_case({
        "case_id": case_id,
        "amount": 50000.0,
        "status": LifecycleStage.PENDING_APPROVAL.value,
        "queue": "Repair",
        "approval_history": []
    })

    sub = ApprovalSubmission(
        case_id=case_id,
        action=ApprovalAction.APPROVE,
        comments="Valid approval in PENDING_APPROVAL state"
    )
    ok, msg, rec, stage = approval_engine.process_approval_action(sub, approver_id="APR-3191")
    assert ok is True
    assert stage == LifecycleStage.APPROVED


# ==============================================================================
# MST-041: MODIFY Bypasses Dual Authorization
# ==============================================================================

def test_mst_041_modify_high_value_requires_dual_authorization():
    """Verify that MODIFY action on high-value cases requires Level 2 dual authorization."""
    case_id = f"CASE-MST041-HV-{uuid.uuid4().hex[:6]}"
    repo.save_case({
        "case_id": case_id,
        "amount": 250000.0,  # Requires dual-auth within Daniel Osei's limit
        "status": LifecycleStage.PENDING_APPROVAL.value,
        "queue": "Repair",
        "dual_auth_required": True,
        "approval_history": []
    })
    repo.approvals[case_id] = []

    # Level 1 MODIFY approval by Daniel Osei (APR-3191)
    override = [
        ProposedFieldChange(
            field_path="creditor_account.iban",
            original_value_masked="GB82WEST12345698765431",
            proposed_value_masked="GB82WEST12345698765432",
            justification="Manual IBAN checksum correction"
        )
    ]
    sub1 = ApprovalSubmission(
        case_id=case_id,
        action=ApprovalAction.MODIFY,
        comments="Level 1 Modified and Approved",
        override_changes=override
    )
    ok1, msg1, rec1, stage1 = approval_engine.process_approval_action(sub1, approver_id="APR-3191")
    assert ok1 is True
    assert stage1 == LifecycleStage.AWAITING_SECOND_APPROVAL
    assert rec1.step_number == 1
    assert rec1.action == ApprovalAction.MODIFY

    # Ensure same approver CANNOT self-cosign Level 2
    sub2_self = ApprovalSubmission(
        case_id=case_id,
        action=ApprovalAction.MODIFY,
        comments="Level 2 Self-cosign attempt"
    )
    ok_self, msg_self, _, _ = approval_engine.process_approval_action(sub2_self, approver_id="APR-3191")
    assert ok_self is False
    assert "Dual Authorization violation" in msg_self

    # Level 2 dual-authorization by distinct approver: Kenji Watanabe (RSK-7714)
    sub2 = ApprovalSubmission(
        case_id=case_id,
        action=ApprovalAction.APPROVE,
        comments="Level 2 Risk Sign-off on modified fields"
    )
    ok2, msg2, rec2, stage2 = approval_engine.process_approval_action(sub2, approver_id="RSK-7714")
    assert ok2 is True
    assert stage2 == LifecycleStage.APPROVED
    assert rec2.step_number == 2


def test_mst_041_modify_low_value_single_approval():
    """Verify that MODIFY action on low-value cases (< $250k) transitions directly to APPROVED."""
    case_id = f"CASE-MST041-LV-{uuid.uuid4().hex[:6]}"
    repo.save_case({
        "case_id": case_id,
        "amount": 45000.0,
        "status": LifecycleStage.PENDING_APPROVAL.value,
        "queue": "Repair",
        "dual_auth_required": False,
        "approval_history": []
    })
    repo.approvals[case_id] = []

    sub = ApprovalSubmission(
        case_id=case_id,
        action=ApprovalAction.MODIFY,
        comments="Low-value direct approval with field modification"
    )
    ok, msg, rec, stage = approval_engine.process_approval_action(sub, approver_id="APR-3191")
    assert ok is True
    assert stage == LifecycleStage.APPROVED
    assert rec.step_number == 1


# ==============================================================================
# MST-042: Ingestion Sets PENDING_APPROVAL
# ==============================================================================

def test_mst_042_ingestion_sets_ingested_status(client):
    """Verify that raw bank event ingestion initializes case status to INGESTED, not PENDING_APPROVAL."""
    raw_event = {
        "event_id": f"EVT-ING-{uuid.uuid4().hex[:6]}",
        "source_bank_id": "BANK_A",
        "event_type": "PAYMENT_EXCEPTION",
        "raw_payload": {
            "payment_reference": f"REF-ING-{uuid.uuid4().hex[:6]}",
            "uetr": f"UETR-ING-{uuid.uuid4().hex[:8]}",
            "amount": 75000.0,
            "currency": "USD",
            "debtor_name": "Test Ingestion Corp",
            "debtor_account": "US89CHAS12345678901234",
            "creditor_name": "Ingestion Beneficiary Ltd",
            "creditor_iban": "GB82WEST12345698765431",
            "error_code": "ERR_IBAN_MOD97",
            "error_message": "Invalid check digits on beneficiary IBAN",
            "settlement_rail": "SWIFT_CBPR+"
        }
    }

    resp = client.post("/api/events/ingest", json=raw_event)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    case_id = data["case_id"]

    stored_case = repo.get_case(case_id)
    assert stored_case is not None
    assert stored_case["status"] == "INGESTED"
    assert stored_case["status"] != "PENDING_APPROVAL"
    assert stored_case["domain"] == "DATA_QUALITY"


# ==============================================================================
# MST-043: check_can_approve Ignores Monetary Limits
# ==============================================================================

def test_mst_043_operator_limit_zero():
    """Verify that Operators have $0 approval limit and are rejected."""
    can_approve, reason = check_can_approve(
        role=UserRole.OPERATOR,
        amount=100.0,
        queue="Repair",
        user_id="OP-8472"
    )
    assert can_approve is False
    assert "Maker-Checker" in reason or "Operator" in reason


def test_mst_043_operations_approver_limit_exceeded():
    """Verify that Operations Approver (limit $250k) is rejected for amounts > $250k."""
    can_approve, reason = check_can_approve(
        role=UserRole.OPERATIONS_APPROVER,
        amount=500000.0,
        queue="Repair",
        user_id="APR-3191"
    )
    assert can_approve is False
    assert "Approval limit exceeded" in reason
    assert "$500,000.00" in reason
    assert "$250,000.00" in reason


def test_mst_043_operations_approver_within_limit():
    """Verify that Operations Approver (limit $250k) is approved for amounts <= $250k."""
    can_approve, reason = check_can_approve(
        role=UserRole.OPERATIONS_APPROVER,
        amount=250000.0,
        queue="Repair",
        user_id="APR-3191"
    )
    assert can_approve is True
    assert reason == "Authorized"


def test_mst_043_compliance_approver_limit_exceeded():
    """Verify that Compliance Approver (limit $5M) is rejected for amounts > $5M."""
    can_approve, reason = check_can_approve(
        role=UserRole.COMPLIANCE_APPROVER,
        amount=6000000.0,
        queue="Compliance",
        user_id="CMP-4420"
    )
    assert can_approve is False
    assert "Approval limit exceeded" in reason
    assert "$6,000,000.00" in reason
    assert "$5,000,000.00" in reason


def test_mst_043_compliance_approver_within_limit():
    """Verify that Compliance Approver is approved for amounts <= $5M."""
    can_approve, reason = check_can_approve(
        role=UserRole.COMPLIANCE_APPROVER,
        amount=1000000.0,
        queue="Compliance",
        user_id="CMP-4420"
    )
    assert can_approve is True
    assert reason == "Authorized"


def test_mst_043_approval_engine_enforces_limit_rejection():
    """Verify that ApprovalEngine rejects approval submission when amount exceeds approver limit."""
    case_id = f"CASE-MST043-EXCEED-{uuid.uuid4().hex[:6]}"
    repo.save_case({
        "case_id": case_id,
        "amount": 750000.0,  # Exceeds Daniel Osei's $250k limit
        "status": LifecycleStage.PENDING_APPROVAL.value,
        "queue": "Repair",
        "approval_history": []
    })

    sub = ApprovalSubmission(
        case_id=case_id,
        action=ApprovalAction.APPROVE,
        comments="Approver attempting to sign off above limit"
    )
    ok, msg, rec, stage = approval_engine.process_approval_action(sub, approver_id="APR-3191")
    assert ok is False
    assert "Approval limit exceeded" in msg


# ==============================================================================
# MST-011: Double Audit Logging on Approvals
# ==============================================================================

def test_mst_011_single_audit_event_logged_per_approval(client):
    """Verify that submitting an approval via the endpoint produces exactly one audit log."""
    case_id = f"CASE-MST011-AUDIT-{uuid.uuid4().hex[:6]}"
    repo.save_case({
        "case_id": case_id,
        "uetr": f"UETR-AUDIT-{uuid.uuid4().hex[:8]}",
        "amount": 35000.0,
        "status": LifecycleStage.PENDING_APPROVAL.value,
        "queue": "Repair",
        "approval_history": [],
        "audit_timeline": []
    })
    repo.approvals[case_id] = []

    initial_audit_count = len(repo.audit_log)

    payload = {
        "case_id": case_id,
        "action": "APPROVE",
        "comments": "Single audit logging verification sign-off",
        "override_changes": []
    }
    headers = {"Authorization": "Bearer pex-token-APR-3191"}

    resp = client.post("/api/approvals/submit", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Audit events in global audit ledger must increase by EXACTLY 1
    new_audit_count = len(repo.audit_log)
    assert new_audit_count == initial_audit_count + 1

    # Verify the logged event
    last_event = repo.audit_log[-1]
    assert last_event.case_id == case_id
    assert last_event.stage_name == "HITL_APPROVAL"
    assert last_event.action_name == "APPROVAL_APPROVE"
    assert last_event.actor_id == "APR-3191"
