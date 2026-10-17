"""Outbound handoff: the ONE place that decides what happens when a case reaches the bank boundary.

Modes (settings.PEX_OPERATION_MODE):
  SHADOW   - read-only. Nothing is sent, ever. Cases end in SHADOW_RECORDED (recommendation recorded).
  ASSISTED - every handoff requires a named human approver (maker-checker). Autonomous release is refused.
  LIVE     - handoff to the bank after human approval OR a human-authored STP policy; still never settles.

Bank communication is SIMULATED in this build (settings.BANK_COMM_MODE): the handoff marks the case
DISPATCHED / AWAITING_BANK_ACK and the (demo) simulated bank answers via the signed /api/bank/outcome path.
PeX never sets SETTLED itself.
"""
from typing import Any, Callable, Dict, Optional, Tuple
import logging

from app.config import settings
from app.schemas.canonical import LifecycleStage
from app.services.state_machine import transition_case, normalize_status
from app.services.audit_service import audit_service
from app.services.data_loader import repo

logger = logging.getLogger(__name__)

VALID_MODES = ("SHADOW", "ASSISTED", "LIVE")


def operation_mode() -> str:
    mode = str(getattr(settings, "PEX_OPERATION_MODE", "SHADOW")).upper()
    return mode if mode in VALID_MODES else "SHADOW"


def _is_human(approver: Optional[str]) -> bool:
    return bool(approver) and not str(approver).upper().startswith(("SYS", "POLICY", "SYSTEM"))


def resolve_handoff_state(approved_by: Optional[str] = None, policy_approved: bool = False,
                          mode: Optional[str] = None) -> Tuple[Optional[str], str]:
    """Returns (target_state, reason). target_state None means: refuse (do not move the case)."""
    m = (mode or operation_mode()).upper()
    if m == "SHADOW":
        return LifecycleStage.SHADOW_RECORDED.value, "SHADOW mode: nothing is sent to the bank."
    if m == "ASSISTED":
        if _is_human(approved_by):
            return LifecycleStage.HANDED_TO_BANK.value, "ASSISTED mode: human-approved handoff."
        return None, "ASSISTED mode requires a named human approver for every handoff."
    # LIVE
    if _is_human(approved_by) or policy_approved:
        return LifecycleStage.HANDED_TO_BANK.value, "LIVE mode: approved handoff."
    return None, "LIVE mode requires human approval or an approved STP policy."


def dispatch_to_bank_handoff(
    case: Any,
    action_contract: Optional[Any] = None,
    outbound_network_sender: Optional[Callable] = None,
    mode: Optional[str] = None,
    actor: str = "OUTBOUND_DISPATCH_PORT",
    reason: Optional[str] = None,
    approved_by: Optional[str] = None,
    policy_approved: bool = False,
) -> Dict[str, Any]:
    """Moves an approved case across the bank boundary according to the operation mode."""
    op_mode = (mode or operation_mode()).upper()
    get = (lambda k, d=None: case.get(k, d)) if isinstance(case, dict) else (lambda k, d=None: getattr(case, k, d))
    case_id = get("case_id", "UNKNOWN")
    uetr = get("uetr") or f"UETR-{case_id}"

    target, why = resolve_handoff_state(approved_by=approved_by, policy_approved=policy_approved, mode=op_mode)
    if target is None:
        audit_service.log_event(
            case_id=case_id, correlation_id=uetr, stage_name="HANDOFF_BLOCKED", actor_id="SYS-OUTBOUND-PORT",
            actor_role="PLATFORM_GUARD", action_name="HANDOFF_REFUSED", details=why,
            control_tags=[f"MODE_{op_mode}", "HANDOFF_REFUSED"], amount=get("amount"), currency=get("currency"))
        return {"dispatched": False, "mode": op_mode, "status": normalize_status(get("status")), "message": why}

    if target == LifecycleStage.SHADOW_RECORDED.value:
        transition_case(case, LifecycleStage.SHADOW_RECORDED, actor, reason or why)
        if isinstance(case, dict):
            repo.save_case(case)
        audit_service.log_event(
            case_id=case_id, correlation_id=uetr, stage_name="SHADOW_EVALUATION", actor_id="SYS-OUTBOUND-PORT",
            actor_role="PLATFORM_GUARD", action_name="SHADOW_HANDOFF_RECORDED",
            details=f"Case {case_id} reached the handoff boundary. Nothing sent (SHADOW). Recorded for the agreement metric.",
            control_tags=["SHADOW_MODE", "ZERO_OUTBOUND", "PILOT_SAFEGUARD"], amount=get("amount"), currency=get("currency"))
        return {"dispatched": False, "mode": "SHADOW", "status": LifecycleStage.SHADOW_RECORDED.value, "message": why}

    # ASSISTED (human approved) / LIVE: hand off. Transport is simulated unless a sender is injected.
    if outbound_network_sender is not None and callable(outbound_network_sender):
        outbound_network_sender(case=case, action_contract=action_contract)
    transition_case(case, LifecycleStage.HANDED_TO_BANK, actor,
                    reason or f"Handed to bank execution system ({op_mode}, {settings.BANK_COMM_MODE}); awaiting bank confirmation.",
                    dispatch_status="AWAITING_BANK_ACK")
    if isinstance(case, dict):
        repo.save_case(case)
    audit_service.log_event(
        case_id=case_id, correlation_id=uetr, stage_name="HANDOFF", actor_id="SYS-OUTBOUND-PORT",
        actor_role="OUTBOUND_GATEWAY", action_name=f"{op_mode}_HANDOFF_DISPATCHED",
        details=f"Case {case_id} handed to bank ({settings.BANK_COMM_MODE}). Awaiting bank confirmation; PeX does not settle.",
        control_tags=[f"MODE_{op_mode}", "HANDED_TO_BANK", "AWAITING_BANK_ACK", f"BANK_COMM_{settings.BANK_COMM_MODE}"],
        amount=get("amount"), currency=get("currency"))
    return {"dispatched": True, "mode": op_mode, "status": LifecycleStage.HANDED_TO_BANK.value,
            "message": "Handed off to the bank (awaiting bank confirmation)."}
