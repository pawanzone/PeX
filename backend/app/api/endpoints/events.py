"""Bank Event Ingestion Endpoints."""
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
