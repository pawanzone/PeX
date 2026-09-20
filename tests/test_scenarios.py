"""End-to-End Tests for Core Scenarios: IBAN-REPAIR-001, IBAN-ESCALATE-001, IBAN-MISSING-EVIDENCE-001."""
import pytest
from app.schemas.bank_events import RawBankEvent
from app.services.canonicalizer import canonicalizer
from app.services.evidence_planner import evidence_planner
from app.services.context_builder import context_builder
from app.services.model_gateway import model_gateway
from app.services.approval_engine import approval_engine
from app.services.action_executor import action_executor
from app.services.audit_service import audit_service
from app.schemas.recommendation import ActionType
from app.schemas.approval import ApprovalSubmission, ApprovalAction
from app.schemas.canonical import LifecycleStage
from app.services.data_loader import repo

def test_scenario_iban_repair_001():
    """Scenario IBAN-REPAIR-001: End-to-end full repair, approval and settled action."""
    # Step 1: Ingest Bank Event
    event = RawBankEvent(
        event_id="EVT-TEST-REPAIR-001",
        source_bank_id="BANK_A",
        event_type="PAYMENT_EXCEPTION",
        raw_payload={
            "payment_reference": "REF-REPAIR-001",
            "error_code": "ERR_IBAN_MOD97",
            "error_message": "Beneficiary IBAN failed MOD-97 check validation",
            "amount": 42000.0,
            "currency": "USD",
            "debtor_name": "Acme Global Holdings",
            "debtor_account": "US89CHAS12345678901234",
            "creditor_name": "HarborView Supplier Ltd",
            "creditor_iban": "GB82WEST12345698765432"
        }
    )
    pmt, exc = canonicalizer.canonicalize_bank_event(event)
    repo.save_case({
        "case_id": exc.case_id, "payment_id": pmt.payment_id, "uetr": pmt.uetr,
        "payment_ref": pmt.instruction_id, "profile": exc.profile, "error_code": exc.error_code,
        "reason": exc.reason, "amount": pmt.amount, "currency": pmt.currency, "payment_rail": pmt.payment_rail,
        "debtor_party": pmt.debtor_party.dict(), "debtor_account": pmt.debtor_account.dict(),
        "creditor_party": pmt.creditor_party.dict(), "creditor_account": pmt.creditor_account.dict(),
        "queue": exc.assigned_queue, "status": LifecycleStage.PENDING_APPROVAL, "severity": exc.severity,
        "priority": exc.priority, "sla_due_at": exc.sla_due_at, "dual_auth_required": False,
        "ai_confidence": 0.96, "created_at": exc.detected_at, "approval_history": []
    })

    # Step 2: Evidence Gathering
    evidence, policies, hist = evidence_planner.plan_and_gather_evidence(
        case_id=exc.case_id, profile=exc.profile, party_name=pmt.creditor_party.party_name,
        account_val=pmt.creditor_account.iban, currency=pmt.currency
    )
    assert len(evidence) >= 2

    # Step 3: Tokenized Context
    ctx = context_builder.build_investigation_context(
        payment=pmt, exception=exc, evidence_items=evidence, policies=policies, historical_cases=hist
    )

    # Step 4: Model Gateway Decision
    rec = model_gateway.evaluate_investigation(ctx)
    repo.recommendations[exc.case_id] = rec
    assert rec.action_type == ActionType.REPAIR_IBAN
    assert rec.confidence_score >= 0.90
    assert len(rec.proposed_changes) > 0

    # Step 5: Human Approval (Daniel Osei)
    sub = ApprovalSubmission(case_id=exc.case_id, action=ApprovalAction.APPROVE, comments="Verified MOD97 checksum.")
    ok, msg, record, stage = approval_engine.process_approval_action(sub, approver_id="APR-3191")
    assert ok is True
    assert stage == LifecycleStage.APPROVED

    # Step 6: Action Execution
    act_ok, act_msg, contract, receipt = action_executor.execute_governed_action(exc.case_id)
    assert act_ok is True
    assert receipt.status == "SETTLED_CONFIRMED"
    
    # Assert case status is settled
    case = repo.get_case(exc.case_id)
    assert case["status"] == LifecycleStage.SETTLED

def test_scenario_iban_escalate_001():
    """Scenario IBAN-ESCALATE-001: Ambiguous evidence generates ESCALATE and blocks action execution."""
    # Context with ESCALATE scenario
    event = RawBankEvent(
        event_id="EVT-TEST-ESC-001", source_bank_id="BANK_A", event_type="PAYMENT_EXCEPTION",
        raw_payload={"payment_reference": "REF-ESC-001", "error_code": "ERR_AMBIGUOUS", "error_message": "Conflicting IBAN records",
                     "amount": 42000.0, "currency": "USD", "debtor_name": "Acme", "debtor_account": "1", "creditor_name": "Supplier", "creditor_iban": "GB8211"}
    )
    pmt, exc = canonicalizer.canonicalize_bank_event(event)
    ctx = context_builder.build_investigation_context(pmt, exc, [], [], [])
    
    rec = model_gateway.evaluate_investigation(ctx, scenario_key="IBAN-ESCALATE-001")
    assert rec.action_type == ActionType.ESCALATE
    assert len(rec.proposed_changes) == 0

def test_scenario_iban_missing_evidence_001():
    """Scenario IBAN-MISSING-EVIDENCE-001: Missing mandatory evidence yields INSUFFICIENT_EVIDENCE."""
    event = RawBankEvent(
        event_id="EVT-TEST-MISS-001", source_bank_id="BANK_A", event_type="PAYMENT_EXCEPTION",
        raw_payload={"payment_reference": "REF-MISS-001", "error_code": "ERR_NO_DIR", "error_message": "No directory entry",
                     "amount": 42000.0, "currency": "USD", "debtor_name": "Acme", "debtor_account": "1", "creditor_name": "Supplier", "creditor_iban": "GB8211"}
    )
    pmt, exc = canonicalizer.canonicalize_bank_event(event)
    evidence, policies, hist = evidence_planner.plan_and_gather_evidence(
        exc.case_id, exc.profile, "Unknown Party", "GB8211", "USD", mock_scenario="IBAN-MISSING-EVIDENCE-001"
    )
    ctx = context_builder.build_investigation_context(pmt, exc, evidence, policies, hist)
    rec = model_gateway.evaluate_investigation(ctx, scenario_key="IBAN-MISSING-EVIDENCE-001")
    assert rec.action_type == ActionType.INSUFFICIENT_EVIDENCE
