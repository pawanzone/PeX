"""Outbound Dispatch Choke Point: Governs execution handoff across SHADOW, ASSISTED, and LIVE modes."""
from typing import Dict, Any, Optional, Callable
import logging

from app.config import settings
from app.schemas.canonical import LifecycleStage
from app.services.state_machine import transition_case
from app.services.audit_service import audit_service
from app.services.data_loader import repo

logger = logging.getLogger(__name__)


def dispatch_to_bank_handoff(
    case: Any,
    action_contract: Optional[Any] = None,
    outbound_network_sender: Optional[Callable] = None,
    mode: Optional[str] = None,
    actor: str = "OUTBOUND_DISPATCH_PORT",
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """Single outbound choke point through which all bank handoffs and execution requests must pass.
    
    Modes:
    - SHADOW: Outbound network calls are strictly suppressed. Case transitions to SHADOW_RECORDED,
      and an audit event is logged for pilot evaluation.
    - ASSISTED: Outbound handoff requires verified human approval before dispatch.
    - LIVE: Outbound handoff proceeds to external bank systems; case transitions to HANDED_TO_BANK.
    """
    op_mode = (mode or getattr(settings, "PEX_OPERATION_MODE", "SHADOW")).upper()
    case_id = case.get("case_id") if isinstance(case, dict) else getattr(case, "case_id", "UNKNOWN")
    uetr = (case.get("uetr") if isinstance(case, dict) else getattr(case, "uetr", None)) or f"UETR-{case_id}"
    amount = case.get("amount") if isinstance(case, dict) else getattr(case, "amount", 0.0)
    currency = case.get("currency") if isinstance(case, dict) else getattr(case, "currency", "USD")

    # 1. SHADOW MODE
    if op_mode == "SHADOW":
        logger.info(f"[PeX Choke Point] SHADOW mode active: suppressing outbound dispatch for case {case_id}.")
        transition_case(
            case=case,
            to_state=LifecycleStage.SHADOW_RECORDED,
            actor=actor,
            reason=reason or "Execution suppressed in SHADOW mode; handoff recommendation recorded for pilot evaluation."
        )
        if isinstance(case, dict):
            repo.save_case(case)

        audit_service.log_event(
            case_id=case_id,
            correlation_id=uetr,
            stage_name="SHADOW_EVALUATION",
            actor_id="SYS-CHOKE-POINT",
            actor_role="PLATFORM_GUARD",
            action_name="SHADOW_HANDOFF_RECORDED",
            details=f"Case {case_id} reached execution handoff boundary. Outbound call suppressed in SHADOW mode. Handoff recorded for pilot agreement metric.",
            control_tags=["SHADOW_MODE", "ZERO_OUTBOUND", "PILOT_SAFEGUARD"],
            amount=amount,
            currency=currency
        )
        return {
            "dispatched": False,
            "mode": "SHADOW",
            "status": LifecycleStage.SHADOW_RECORDED.value,
            "message": "Outbound execution suppressed in SHADOW mode. Recommendation recorded for pilot evaluation."
        }

    # 2. ASSISTED MODE
    if op_mode == "ASSISTED":
        # Check human approval requirement
        approvals = repo.approvals.get(case_id, [])
        is_approved = (
            (case.get("status") if isinstance(case, dict) else getattr(case, "status")) == LifecycleStage.APPROVED.value
            or len(approvals) > 0
        )
        if not is_approved:
            logger.warning(f"[PeX Choke Point] ASSISTED mode blocked autonomous handoff for unapproved case {case_id}.")
            transition_case(
                case=case,
                to_state=LifecycleStage.PENDING_APPROVAL,
                actor=actor,
                reason="Handoff blocked: Human approval required for every handoff in ASSISTED mode."
            )
            if isinstance(case, dict):
                repo.save_case(case)
            return {
                "dispatched": False,
                "mode": "ASSISTED",
                "status": LifecycleStage.PENDING_APPROVAL.value,
                "message": "Outbound handoff blocked: Human authorization mandatory in ASSISTED mode."
            }

    # 3. DISPATCH (LIVE or Approved ASSISTED)
    if outbound_network_sender and callable(outbound_network_sender):
        outbound_network_sender(case=case, action_contract=action_contract)

    transition_case(
        case=case,
        to_state=LifecycleStage.HANDED_TO_BANK,
        actor=actor,
        reason=reason or f"Case successfully handed to bank execution system in {op_mode} mode.",
        dispatch_status="AWAITING_BANK_ACK"
    )
    if isinstance(case, dict):
        repo.save_case(case)

    audit_service.log_event(
        case_id=case_id,
        correlation_id=uetr,
        stage_name="HANDOFF",
        actor_id="SYS-CHOKE-POINT",
        actor_role="OUTBOUND_GATEWAY",
        action_name=f"{op_mode}_HANDOFF_DISPATCHED",
        details=f"Case {case_id} sealed and handed to bank execution hub ({op_mode} mode). Status: AWAITING_BANK_ACK.",
        control_tags=[f"MODE_{op_mode}", "HANDED_TO_BANK", "AWAITING_BANK_ACK"],
        amount=amount,
        currency=currency
    )

    return {
        "dispatched": True,
        "mode": op_mode,
        "status": LifecycleStage.HANDED_TO_BANK.value,
        "message": f"Successfully handed off to bank execution engine in {op_mode} mode (awaiting bank ACK)."
    }
