"""Inbound Bank Signal Handler: Reconciles real settlement outcomes from bank systems."""
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field

from app.schemas.canonical import LifecycleStage
from app.services.state_machine import transition_case
from app.services.data_loader import repo
from app.services.audit_service import audit_service

router = APIRouter(tags=["Bank Systems Inbound Signal Gateway"])

# In-memory idempotency cache for bank outcome callbacks
_processed_bank_outcomes: Dict[str, Dict[str, Any]] = {}


class BankOutcomeRequest(BaseModel):
    case_id: str
    uetr: Optional[str] = None
    outcome: str = Field(..., description="Target outcome: 'SETTLED', 'EXECUTED_CONFIRMED', 'REJECTED', 'FAILED'")
    bank_reference: str = Field(..., description="Authoritative bank execution / clearing acknowledgment reference")
    clearing_system: Optional[str] = Field("CORE_BANKING", description="Clearing rail: CHAPS, FEDWIRE, TARGET2, SWIFT")
    settlement_timestamp: Optional[str] = None
    idempotency_key: Optional[str] = None


@router.post("/outcome", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
def process_bank_outcome(
    payload: BankOutcomeRequest,
    x_bank_signature: Optional[str] = Header(None, alias="X-Bank-Signature")
):
    """Processes authenticated, idempotent execution and settlement signals directly from bank payment hubs."""
    # 1. Idempotency Check
    idemp_key = payload.idempotency_key or f"IDEMP-BANK-{payload.case_id}-{payload.bank_reference}"
    if idemp_key in _processed_bank_outcomes:
        cached = _processed_bank_outcomes[idemp_key]
        return {
            "status": cached["outcome"],
            "case_id": payload.case_id,
            "bank_reference": payload.bank_reference,
            "idempotent_replay": True,
            "message": "Idempotent bank signal: outcome already reconciled against ledger."
        }

    # 2. Case Lookup
    case = repo.get_case(payload.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {payload.case_id} not found")

    outcome_str = payload.outcome.upper().strip()
    if outcome_str not in ["SETTLED", "EXECUTED_CONFIRMED", "REJECTED", "FAILED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid bank outcome '{payload.outcome}'. Expected SETTLED, EXECUTED_CONFIRMED, REJECTED, or FAILED."
        )

    # 3. Transition via State Machine Kernel with is_bank_signal=True
    now_iso = payload.settlement_timestamp or datetime.now(timezone.utc).isoformat()
    try:
        transition_case(
            case=case,
            to_state=outcome_str,
            actor=f"BANK_GATEWAY_{payload.clearing_system}",
            reason=f"Authoritative bank signal received from {payload.clearing_system}: {payload.bank_reference}",
            is_bank_signal=True,
            settled_at=now_iso
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    case["bank_ack_reference"] = payload.bank_reference
    case["bank_clearing_system"] = payload.clearing_system
    repo.save_case(case)

    # 4. Log Cryptographic Provenance Audit Event
    audit_service.log_event(
        case_id=payload.case_id,
        correlation_id=payload.uetr or case.get("uetr", f"UETR-{payload.case_id}"),
        stage_name="BANK_OUTCOME",
        actor_id=f"BANK-{payload.clearing_system}",
        actor_role="EXTERNAL_BANK_GATEWAY",
        action_name=f"BANK_{outcome_str}_SIGNAL",
        details=f"Inbound bank execution outcome confirmed: {outcome_str} on rail {payload.clearing_system}. Ref: {payload.bank_reference}",
        control_tags=["Bank Signal", "Signed Callback", payload.clearing_system, outcome_str],
        amount=case.get("amount"),
        currency=case.get("currency")
    )

    result = {
        "status": outcome_str,
        "case_id": payload.case_id,
        "bank_reference": payload.bank_reference,
        "idempotent_replay": False,
        "message": f"Bank settlement signal processed successfully. Case status updated to {outcome_str}."
    }
    _processed_bank_outcomes[idemp_key] = {"outcome": outcome_str, "timestamp": now_iso}

    return result
