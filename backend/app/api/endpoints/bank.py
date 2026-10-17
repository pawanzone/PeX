"""Inbound bank outcome gateway: the ONLY way a case can become EXECUTED_CONFIRMED / SETTLED.

Security: the body is authenticated with HMAC-SHA256 (header `X-Bank-Signature: sha256=<hex>`) using
PEX_BANK_CALLBACK_SECRET. Without a configured secret (and outside PEX_DEMO) the endpoint refuses.
Idempotency is persisted (table bank_outcomes), so replays are no-ops even after a restart.
"""
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import settings
from app.db.models import BankOutcomeModel
from app.db.session import SessionLocal
from app.services.audit_service import audit_service
from app.services.data_loader import repo
from app.services.state_machine import IllegalTransition, normalize_status, transition_case

router = APIRouter(tags=["Bank Systems Inbound Signal Gateway"])

# Demo-only ephemeral secret shared with the in-process simulated bank when no secret is configured.
_DEMO_SECRET = secrets.token_hex(32)


def callback_secret() -> str:
    if settings.BANK_CALLBACK_SECRET:
        return settings.BANK_CALLBACK_SECRET
    return _DEMO_SECRET if settings.PEX_DEMO else ""


def sign_body(raw: bytes, secret: Optional[str] = None) -> str:
    key = (secret or callback_secret()).encode()
    return "sha256=" + hmac.new(key, raw, hashlib.sha256).hexdigest()


class BankOutcomeRequest(BaseModel):
    case_id: str
    uetr: Optional[str] = None
    outcome: str = Field(..., description="SETTLED | EXECUTED_CONFIRMED | REJECTED | FAILED")
    bank_reference: str
    clearing_system: Optional[str] = "CORE_BANKING"
    settlement_timestamp: Optional[str] = None
    idempotency_key: Optional[str] = None
    reason: Optional[str] = None


def process_signed_outcome(raw: bytes, signature: Optional[str]) -> Dict[str, Any]:
    secret = callback_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="Bank callback secret not configured (PEX_BANK_CALLBACK_SECRET)")
    if not signature or not hmac.compare_digest(signature, sign_body(raw, secret)):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Bank-Signature")
    try:
        payload = BankOutcomeRequest(**json.loads(raw))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Malformed outcome payload: {e}")

    outcome = payload.outcome.upper().strip()
    if outcome not in ("SETTLED", "EXECUTED_CONFIRMED", "REJECTED", "FAILED"):
        raise HTTPException(status_code=400, detail=f"Invalid bank outcome '{payload.outcome}'")

    idem = payload.idempotency_key or f"IDEMP-BANK-{payload.case_id}-{payload.bank_reference}-{outcome}"
    db = SessionLocal()
    try:
        if db.query(BankOutcomeModel).filter(BankOutcomeModel.idempotency_key == idem).first():
            return {"status": outcome, "case_id": payload.case_id, "bank_reference": payload.bank_reference,
                    "idempotent_replay": True, "message": "Outcome already processed."}
    finally:
        db.close()

    case = repo.get_case(payload.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {payload.case_id} not found")

    now_iso = payload.settlement_timestamp or datetime.now(timezone.utc).isoformat()
    try:
        transition_case(
            case, outcome, actor=f"BANK_GATEWAY_{payload.clearing_system}",
            reason=payload.reason or f"Bank signal from {payload.clearing_system}: {payload.bank_reference}",
            is_bank_signal=True, settled_at=now_iso if outcome == "SETTLED" else None)
    except IllegalTransition as e:
        raise HTTPException(status_code=409, detail=str(e))

    case["bank_ack_reference"] = payload.bank_reference
    case["bank_clearing_system"] = payload.clearing_system
    repo.save_case(case)

    db = SessionLocal()
    try:
        db.add(BankOutcomeModel(idempotency_key=idem, case_id=payload.case_id, outcome=outcome,
                                bank_reference=payload.bank_reference, clearing_system=payload.clearing_system,
                                received_at=datetime.now(timezone.utc).isoformat(), signature_verified=True))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

    audit_service.log_event(
        case_id=payload.case_id, correlation_id=payload.uetr or case.get("uetr", f"UETR-{payload.case_id}"),
        stage_name="BANK_OUTCOME", actor_id=f"BANK-{payload.clearing_system}", actor_role="EXTERNAL_BANK_GATEWAY",
        action_name=f"BANK_{outcome}_SIGNAL",
        details=f"Authenticated bank outcome {outcome} via {payload.clearing_system}. Ref: {payload.bank_reference}",
        control_tags=["Bank Signal", "HMAC verified", payload.clearing_system or "", outcome,
                      f"BANK_COMM_{settings.BANK_COMM_MODE}"],
        amount=case.get("amount"), currency=case.get("currency"))
    return {"status": outcome, "case_id": payload.case_id, "bank_reference": payload.bank_reference,
            "idempotent_replay": False, "message": f"Bank outcome processed. Case is now {normalize_status(case.get('status'))}."}


@router.post("/outcome", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def post_bank_outcome(request: Request, x_bank_signature: Optional[str] = Header(None, alias="X-Bank-Signature")):
    raw = await request.body()
    return process_signed_outcome(raw, x_bank_signature)
