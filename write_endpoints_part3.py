import os

ep_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\api\endpoints"

# 8. endpoints/approvals.py
with open(os.path.join(ep_dir, "approvals.py"), "w", encoding="utf-8") as f:
    f.write('''"""Role-Gated Approvals Endpoints."""
from fastapi import APIRouter, HTTPException, Header
from typing import List, Dict, Any, Optional

from app.schemas.approval import ApprovalSubmission, ApprovalRecord
from app.services.approval_engine import approval_engine
from app.services.audit_service import audit_service
from app.services.data_loader import repo
from app.core.security import get_persona

router = APIRouter()

@router.post("/submit")
def submit_approval(submission: ApprovalSubmission, authorization: Optional[str] = Header(None)):
    user_id = "APR-3191" # Default to Daniel Osei (Operations Approver)
    if authorization and authorization.startswith("Bearer pex-token-"):
        user_id = authorization.replace("Bearer pex-token-", "").strip()
    
    approver = get_persona(user_id)
    if not approver:
        raise HTTPException(status_code=401, detail="Unauthorized approver persona")

    success, message, record, next_stage = approval_engine.process_approval_action(
        submission=submission,
        approver_id=user_id
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Log audit event
    audit_service.log_event(
        case_id=submission.case_id,
        correlation_id=submission.case_id,
        stage_name="HITL_APPROVAL",
        actor_id=approver.user_id,
        actor_role=approver.role.value,
        action_name=f"APPROVAL_{submission.action.value}",
        details=f"Approver {approver.name} submitted {submission.action.value}. Decision message: {submission.comments}. Next stage: {next_stage.value}",
        control_tags=["Maker-checker enforced", "Role entitlements verified", f"Step {record.step_number}"]
    )

    return {
        "success": True,
        "message": message,
        "approval_record": record.dict() if record else None,
        "next_stage": next_stage.value
    }
''')

# 9. endpoints/actions.py
with open(os.path.join(ep_dir, "actions.py"), "w", encoding="utf-8") as f:
    f.write('''"""Governed Action Execution Endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.action_executor import action_executor
from app.services.audit_service import audit_service
from app.services.data_loader import repo

router = APIRouter()

class ExecuteActionRequest(BaseModel):
    case_id: str
    idempotency_key: Optional[str] = None

@router.post("/execute")
def execute_action(req: ExecuteActionRequest):
    success, message, action_contract, receipt = action_executor.execute_governed_action(
        case_id=req.case_id,
        idempotency_key=req.idempotency_key
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Log audit event
    audit_service.log_event(
        case_id=req.case_id,
        correlation_id=req.case_id,
        stage_name="ACTION_DISPATCH",
        actor_id="SIMULATED-ACTION-ADAPTER",
        actor_role="DISPATCHER",
        action_name="DEMO_REPAIR_SETTLED",
        details=f"Simulated repair action {action_contract.action_id} settled against external ledger. Delivery receipt reference: {receipt.bank_ack_reference}",
        control_tags=["Idempotency key recorded", "External bank dispatch simulated", "Ledger updated"]
    )

    return {
        "success": True,
        "message": message,
        "action_contract": action_contract.dict() if action_contract else None,
        "delivery_receipt": receipt.dict() if receipt else None
    }
''')

# 10. endpoints/events.py
with open(os.path.join(ep_dir, "events.py"), "w", encoding="utf-8") as f:
    f.write('''"""Bank Event Ingestion Endpoints."""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import uuid

from app.schemas.bank_events import RawBankEvent
from app.services.canonicalizer import canonicalizer
from app.services.data_loader import repo
from app.services.audit_service import audit_service

router = APIRouter()

@router.post("/ingest")
def ingest_bank_event(event: RawBankEvent):
    # 1. Canonicalize
    payment, exception = canonicalizer.canonicalize_bank_event(event)

    # 2. Store Case
    case_obj = {
        "case_id": exception.case_id,
        "payment_id": payment.payment_id,
        "uetr": payment.uetr,
        "payment_ref": payment.instruction_id,
        "profile": exception.profile,
        "error_code": exception.error_code,
        "reason": exception.reason,
        "amount": payment.amount,
        "currency": payment.currency,
        "payment_rail": payment.payment_rail,
        "debtor_party": payment.debtor_party.dict(),
        "debtor_account": payment.debtor_account.dict(),
        "creditor_party": payment.creditor_party.dict(),
        "creditor_account": payment.creditor_account.dict(),
        "queue": exception.assigned_queue,
        "status": "PENDING_APPROVAL",
        "severity": exception.severity,
        "priority": exception.priority,
        "sla_due_at": exception.sla_due_at,
        "dual_auth_required": payment.amount >= 250000.0,
        "ai_confidence": 0.96 if exception.profile.value == "INVALID_IBAN" else 0.88,
        "created_at": exception.detected_at,
        "approval_history": []
    }
    repo.save_case(case_obj)

    # 3. Log Audit Event
    audit_service.log_event(
        case_id=exception.case_id,
        correlation_id=payment.uetr,
        stage_name="INTAKE",
        actor_id="BANK-INGEST-GATEWAY",
        actor_role="SYSTEM",
        action_name="PAYMENT_RECEIVED",
        details=f"Ingested {event.source_bank_id} event {event.event_id}. Canonical case {exception.case_id} registered with {payment.amount} {payment.currency}.",
        control_tags=["Schema validated", "Tenant idempotency checked", f"Source: {event.source_bank_id}"]
    )

    return {
        "success": True,
        "case_id": exception.case_id,
        "payment": payment.dict(),
        "exception": exception.dict()
    }
''')

# 11. endpoints/cases.py
with open(os.path.join(ep_dir, "cases.py"), "w", encoding="utf-8") as f:
    f.write('''"""Cases & Investigation Workflow Endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

from app.services.data_loader import repo
from app.services.evidence_planner import evidence_planner
from app.services.context_builder import context_builder
from app.services.model_gateway import model_gateway
from app.services.decision_engine import decision_engine
from app.services.audit_service import audit_service
from app.schemas.canonical import (
    CanonicalPayment, CanonicalException, CanonicalParty, CanonicalAccount,
    LifecycleStage, ExceptionProfile, ExceptionSeverity, ExceptionPriority
)
from app.core.tokenization import token_vault

router = APIRouter()

class PaymentInitiationRequest(BaseModel):
    client_reference: Optional[str] = None
    payment_rail: str = "SWIFT / CBPR+"
    exception_profile: str = "INVALID_IBAN"
    debtor_name: str = "Acme Global Holdings"
    debtor_account: Optional[str] = "US89CHAS12345678901234"
    creditor_name: str = "Nordhavn Components A/S"
    creditor_iban: str = "GB82WEST12345698765432"
    amount: float = 250000.0
    currency: str = "USD"
    beneficiary_country: str = "DK"
    exception_reason: Optional[str] = None
    corrected_beneficiary_iban: Optional[str] = None

@router.get("")
def list_cases(
    queue: Optional[str] = None,
    status: Optional[str] = None,
    profile: Optional[str] = None,
    search: Optional[str] = None
):
    cases = repo.list_cases(queue=queue, status=status, profile=profile, search=search)
    return cases

@router.get("/{case_id}")
def get_case(case_id: str):
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    
    rec = repo.recommendations.get(case_id)
    approvals = repo.approvals.get(case_id, [])
    
    return {
        "case": case,
        "recommendation": rec.dict() if rec else None,
        "approvals": [a.dict() for a in approvals]
    }

@router.post("/{case_id}/investigate")
def run_investigation(case_id: str, scenario_override: Optional[str] = None):
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    profile = ExceptionProfile(case.get("profile")) if isinstance(case.get("profile"), str) else case.get("profile")

    # Reconstruct Canonical Objects
    debtor_p = CanonicalParty(**case.get("debtor_party"))
    debtor_a = CanonicalAccount(**case.get("debtor_account"))
    creditor_p = CanonicalParty(**case.get("creditor_party"))
    creditor_a = CanonicalAccount(**case.get("creditor_account"))

    payment = CanonicalPayment(
        payment_id=case.get("payment_id", f"PMT-{case_id}"),
        uetr=case.get("uetr", f"UETR-{case_id}"),
        instruction_id=case.get("payment_ref", f"REF-{case_id}"),
        amount=float(case.get("amount", 42000.0)),
        currency=case.get("currency", "USD"),
        payment_rail=case.get("payment_rail", "SWIFT"),
        debtor_party=debtor_p,
        debtor_account=debtor_a,
        creditor_party=creditor_p,
        creditor_account=creditor_a,
        source_bank_id="BANK_A"
    )

    exception = CanonicalException(
        exception_id=f"EXC-{case_id}",
        case_id=case_id,
        profile=profile,
        error_code=case.get("error_code", "ERR_IBAN_MOD97"),
        reason=case.get("reason", "Exception investigation"),
        severity=ExceptionSeverity(case.get("severity", "MEDIUM")),
        priority=ExceptionPriority(case.get("priority", "NORMAL")),
        sla_due_at=datetime.utcnow() + timedelta(hours=2),
        at_risk_amount=float(case.get("amount", 42000.0)),
        assigned_queue=case.get("queue", "Repair")
    )

    # 1. Evidence Planning
    evidence_items, policies, historical_cases = evidence_planner.plan_and_gather_evidence(
        case_id=case_id,
        profile=profile,
        party_name=creditor_p.party_name,
        account_val=creditor_a.iban or "",
        currency=payment.currency,
        mock_scenario=scenario_override
    )

    # 2. Context Building (Tokenized)
    context = context_builder.build_investigation_context(
        payment=payment,
        exception=exception,
        evidence_items=evidence_items,
        policies=policies,
        historical_cases=historical_cases
    )

    # 3. Model Gateway AI Reasoning
    recommendation = model_gateway.evaluate_investigation(
        context=context,
        scenario_key=scenario_override
    )
    repo.recommendations[case_id] = recommendation

    # 4. Decision Engine Governance Gate
    gate_ok, gate_msg = decision_engine.evaluate_governance_gate(
        recommendation=recommendation,
        profile=profile,
        amount=payment.amount
    )

    # 5. Log Audit Event
    audit_service.log_event(
        case_id=case_id,
        correlation_id=payment.uetr,
        stage_name="AI_INVESTIGATION",
        actor_id=recommendation.model_identifier,
        actor_role="MODEL_GATEWAY",
        action_name=f"RECOMMEND_{recommendation.action_type.value}",
        details=f"AI Evaluated Case. Confidence: {recommendation.confidence_score}. Rationale: {recommendation.rationale}",
        control_tags=["Tokenized PII boundary", "Policy rules evaluated", "Zero autonomous action"]
    )

    return {
        "case_id": case_id,
        "tokenized_context": context.dict(),
        "recommendation": recommendation.dict(),
        "governance_gate": {"passed": gate_ok, "message": gate_msg}
    }

@router.post("/initiate")
def initiate_payment(req: PaymentInitiationRequest):
    case_id = f"PEX-{uuid.uuid4().hex[:6].upper()}"
    uetr = f"UETR-{uuid.uuid4().hex[:8]}"
    client_ref = req.client_reference or f"CLIENT-REF-{uuid.uuid4().hex[:6].upper()}"
    
    try:
        prof = ExceptionProfile(req.exception_profile)
    except Exception:
        prof = ExceptionProfile.INVALID_IBAN

    reason = req.exception_reason or "Beneficiary account identifier failed validation against receiving bank profile."
    queue = "Repair"
    if prof in [ExceptionProfile.SANCTIONS_SUSPECTED, ExceptionProfile.KYC_EXPIRED]:
        queue = "Compliance"
    elif prof in [ExceptionProfile.DUPLICATE_PAYMENT, ExceptionProfile.RETURNED_PAYMENT]:
        queue = "Investigation"

    severity = ExceptionSeverity.MEDIUM
    if req.amount >= 250000.0 or prof == ExceptionProfile.SANCTIONS_SUSPECTED:
        severity = ExceptionSeverity.HIGH
    if req.amount >= 1000000.0:
        severity = ExceptionSeverity.CRITICAL

    priority = ExceptionPriority.NORMAL
    if severity in [ExceptionSeverity.HIGH, ExceptionSeverity.CRITICAL]:
        priority = ExceptionPriority.HIGH
    if req.amount >= 1000000.0:
        priority = ExceptionPriority.CRITICAL

    debtor_tok = token_vault.tokenize(req.debtor_name, "PARTY")
    creditor_tok = token_vault.tokenize(req.creditor_name, "PARTY")
    debtor_acc_tok = token_vault.tokenize(req.debtor_account or "ACC-US-01", "ACC")
    creditor_iban_tok = token_vault.tokenize(req.creditor_iban, "IBAN")

    case_obj = {
        "case_id": case_id,
        "payment_id": f"PMT-{uuid.uuid4().hex[:6].upper()}",
        "uetr": uetr,
        "payment_ref": client_ref,
        "profile": prof,
        "error_code": "ERR_IBAN_MOD97" if prof == ExceptionProfile.INVALID_IBAN else "ERR_GENERAL",
        "reason": reason,
        "amount": req.amount,
        "currency": req.currency,
        "payment_rail": req.payment_rail,
        "debtor_party": {
            "party_id": f"PARTY-DEBTOR-{uuid.uuid4().hex[:4]}",
            "party_name": req.debtor_name,
            "country": "US",
            "party_type": "DEBTOR",
            "token_ref": debtor_tok
        },
        "debtor_account": {
            "account_id": f"ACC-DEBTOR-{uuid.uuid4().hex[:4]}",
            "account_number": req.debtor_account,
            "iban": req.debtor_account,
            "currency": req.currency,
            "bank_bic": "CHASUS33",
            "token_ref": debtor_acc_tok
        },
        "creditor_party": {
            "party_id": f"PARTY-CREDITOR-{uuid.uuid4().hex[:4]}",
            "party_name": req.creditor_name,
            "country": req.beneficiary_country,
            "party_type": "CREDITOR",
            "token_ref": creditor_tok
        },
        "creditor_account": {
            "account_id": f"ACC-CREDITOR-{uuid.uuid4().hex[:4]}",
            "account_number": req.creditor_iban[-8:],
            "iban": req.creditor_iban,
            "currency": req.currency,
            "bank_bic": "WESTGB2L",
            "token_ref": creditor_iban_tok
        },
        "queue": queue,
        "status": LifecycleStage.PENDING_APPROVAL,
        "severity": severity,
        "priority": priority,
        "sla_due_at": datetime.utcnow() + timedelta(hours=2),
        "dual_auth_required": req.amount >= 250000.0,
        "ai_confidence": 0.96 if prof == ExceptionProfile.INVALID_IBAN else 0.88,
        "created_at": datetime.utcnow(),
        "approval_history": []
    }

    repo.save_case(case_obj)

    # Log Intake Audit
    audit_service.log_event(
        case_id=case_id,
        correlation_id=uetr,
        stage_name="INTAKE",
        actor_id="DEMO-INTAKE-SERVICE",
        actor_role="OPERATOR",
        action_name="PAYMENT_RECEIVED",
        details=f"{req.debtor_name} initiated {req.amount} {req.currency} via {req.payment_rail}. Exception detected: {reason}",
        control_tags=["Schema validated", "Tenant idempotency checked", "Profile evidence gate"]
    )

    # Automatically run initial AI investigation
    run_investigation(case_id)

    return {
        "success": True,
        "message": "Payment exception accepted into PeX governance lifecycle.",
        "case_id": case_id,
        "case": case_obj
    }
''')

print("Wrote approvals.py, actions.py, events.py, and cases.py")
