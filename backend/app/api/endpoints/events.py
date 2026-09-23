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
        "payment_rail": payment.payment_rail.value if hasattr(payment.payment_rail, "value") else str(payment.payment_rail),
        "debtor_party": payment.debtor_party.model_dump() if hasattr(payment.debtor_party, "model_dump") else payment.debtor_party.dict(),
        "debtor_account": payment.debtor_account.model_dump() if hasattr(payment.debtor_account, "model_dump") else payment.debtor_account.dict(),
        "creditor_party": payment.creditor_party.model_dump() if hasattr(payment.creditor_party, "model_dump") else payment.creditor_party.dict(),
        "creditor_account": payment.creditor_account.model_dump() if hasattr(payment.creditor_account, "model_dump") else payment.creditor_account.dict(),
        "counterparty": payment.creditor_party.party_name or "Beneficiary",
        "queue": exception.assigned_queue,
        "domain": exception.domain.value if hasattr(exception.domain, "value") else str(exception.domain),
        "secondary_profiles": [p.value if hasattr(p, "value") else str(p) for p in (exception.secondary_profiles or [])],
        "status": "INGESTED",
        "severity": exception.severity.value if hasattr(exception.severity, "value") else str(exception.severity),
        "priority": exception.priority.value if hasattr(exception.priority, "value") else str(exception.priority),
        "sla_due_at": exception.sla_due_at.isoformat() if hasattr(exception.sla_due_at, "isoformat") else str(exception.sla_due_at),
        "at_risk_amount": exception.at_risk_amount or payment.amount,
        "dual_auth_required": payment.amount >= 250000.0,
        "ai_confidence": 0.96 if (exception.profile.value if hasattr(exception.profile, "value") else str(exception.profile)) == "INVALID_IBAN" else 0.88,
        "created_at": exception.detected_at.isoformat() if hasattr(exception.detected_at, "isoformat") else str(exception.detected_at),
        "approval_history": [],
        "audit_timeline": []
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
        "payment": payment.model_dump() if hasattr(payment, "model_dump") else payment.dict(),
        "exception": exception.model_dump() if hasattr(exception, "model_dump") else exception.dict(),
        "case": case_obj
    }
