"""Simulated bank (DEMO ONLY) + hand-off reconciler.

The simulated bank stands in for a real payment hub while bank communication is not integrated.
It does NOT touch case state directly: it answers through the very same signed callback path
(api/endpoints/bank.process_signed_outcome) a real bank would use, so the control path is exercised.
Deterministic behaviour per case id (so demos are repeatable):
  ~88% -> EXECUTED_CONFIRMED then SETTLED
  ~6%  -> REJECTED (e.g. account closed)
  ~3%  -> EXECUTED_CONFIRMED only (settlement pending)
  ~3%  -> silence (no answer) -> the reconciler flips the case to STATUS_UNKNOWN ("do not resend")
The reconciler (hand-off timeout -> STATUS_UNKNOWN) is production behaviour, not demo-only.
"""
import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def _age_seconds(iso: Optional[str]) -> float:
    if not iso:
        return 1e9
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds()
    except Exception:
        return 1e9


def _behaviour(case_id: str) -> str:
    r = int(hashlib.sha256(case_id.encode()).hexdigest()[:6], 16) % 100
    if r < 88:
        return "SETTLE"
    if r < 94:
        return "REJECT"
    if r < 97:
        return "CONFIRM_ONLY"
    return "SILENT"


def _send(case_id: str, outcome: str, reference: str, reason: Optional[str] = None):
    from app.api.endpoints.bank import process_signed_outcome, sign_body
    raw = json.dumps({
        "case_id": case_id, "outcome": outcome, "bank_reference": reference,
        "clearing_system": "SIMULATED_BANK", "reason": reason,
        "idempotency_key": f"SIM-{case_id}-{outcome}",
    }).encode()
    return process_signed_outcome(raw, sign_body(raw))


def _pending(limit: int = 200):
    from app.db.models import CaseModel
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        rows = db.query(CaseModel.case_id, CaseModel.handed_off_at).filter(
            CaseModel.status == "DISPATCHED", CaseModel.dispatch_status == "AWAITING_BANK_ACK").limit(limit).all()
        return [(r[0], r[1]) for r in rows]
    finally:
        db.close()


def simulate_bank_once(min_age: Optional[float] = None) -> int:
    """One pass of the simulated bank. Returns the number of cases answered."""
    min_age = settings.SIM_BANK_ACK_SECONDS if min_age is None else min_age
    n = 0
    for case_id, handed in _pending():
        if _age_seconds(handed) < min_age:
            continue
        b = _behaviour(case_id)
        ref = "SIMACK-" + hashlib.sha256(case_id.encode()).hexdigest()[:10].upper()
        try:
            if b == "SILENT":
                continue
            if b == "REJECT":
                _send(case_id, "REJECTED", ref, "Simulated bank: beneficiary account closed")
            else:
                _send(case_id, "EXECUTED_CONFIRMED", ref)
                if b == "SETTLE":
                    _send(case_id, "SETTLED", ref)
            n += 1
        except Exception as e:  # never kill the loop
            logger.warning("Simulated bank error for %s: %s", case_id, e)
    return n


def reconcile_stale_handoffs(timeout_seconds: Optional[float] = None) -> int:
    """Hand-offs with no bank answer within the timeout become STATUS_UNKNOWN (resend is blocked)."""
    from app.services.data_loader import repo
    from app.services.state_machine import transition_case
    from app.services.audit_service import audit_service
    timeout = settings.STATUS_UNKNOWN_AFTER_SECONDS if timeout_seconds is None else timeout_seconds
    n = 0
    for case_id, handed in _pending():
        if _age_seconds(handed) < timeout:
            continue
        case = repo.get_case(case_id)
        if not case:
            continue
        transition_case(case, "STATUS_UNKNOWN", actor="HANDOFF_RECONCILER",
                        reason=f"No bank confirmation within {int(timeout)}s. Do NOT resend; check with the bank.",
                        dispatch_status="STATUS_UNKNOWN_DO_NOT_RESEND")
        repo.save_case(case)
        audit_service.log_event(
            case_id=case_id, correlation_id=case.get("uetr", case_id), stage_name="RECONCILIATION",
            actor_id="SYS-RECONCILER", actor_role="PLATFORM_GUARD", action_name="STATUS_UNKNOWN",
            details="Bank did not confirm the hand-off in time. Status unknown; resend is blocked.",
            control_tags=["STATUS_UNKNOWN", "DO_NOT_RESEND"], amount=case.get("amount"), currency=case.get("currency"))
        n += 1
    return n


class _Worker:
    def __init__(self):
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="pex-sim-bank", daemon=True)
        self._thread.start()
        logger.info("Simulated bank + reconciler started (ack after %ss)", settings.SIM_BANK_ACK_SECONDS)

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.wait(1.5):
            try:
                if settings.PEX_DEMO and settings.BANK_COMM_MODE == "SIMULATED":
                    simulate_bank_once()
                reconcile_stale_handoffs()
            except Exception as e:
                logger.warning("sim-bank loop error: %s", e)


worker = _Worker()
