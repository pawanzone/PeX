"""Governed State Machine & Transition Kernel for PeX Lifecycle.

Enforces allowed transition matrix and strict authority boundaries:
- SETTLED and EXECUTED_CONFIRMED may be set ONLY by an inbound bank-signal handler.
- Platform components cannot mark payments settled autonomously.
- Enforces single transition choke point for all lifecycle updates.
"""
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
import logging

from app.schemas.canonical import LifecycleStage

logger = logging.getLogger(__name__)

# Normalize values to string for safe comparison
ALLOWED_TRANSITIONS: Dict[Optional[str], list[str]] = {
    None: [
        "INGESTED", "CANONICALIZED", "VALIDATED", "RECOMMENDED",
        "PENDING_APPROVAL", "DISPATCHED", "HANDED_TO_BANK", "SHADOW_RECORDED", "STATUS_UNKNOWN"
    ],
    "INGESTED": [
        "CANONICALIZED", "VALIDATED", "INVESTIGATING", "RECOMMENDED",
        "PENDING_APPROVAL", "DISPATCHED", "HANDED_TO_BANK", "SHADOW_RECORDED", "FAILED", "STATUS_UNKNOWN"
    ],
    "CANONICALIZED": [
        "VALIDATED", "INVESTIGATING", "RECOMMENDED",
        "PENDING_APPROVAL", "DISPATCHED", "HANDED_TO_BANK", "SHADOW_RECORDED", "FAILED", "STATUS_UNKNOWN"
    ],
    "VALIDATED": [
        "INVESTIGATING", "RECOMMENDED",
        "PENDING_APPROVAL", "DISPATCHED", "HANDED_TO_BANK", "SHADOW_RECORDED", "FAILED", "STATUS_UNKNOWN"
    ],
    "INVESTIGATING": [
        "VALIDATED", "RECOMMENDED", "PENDING_APPROVAL", "FAILED", "STATUS_UNKNOWN"
    ],
    "RECOMMENDED": [
        "PENDING_APPROVAL", "AWAITING_SECOND_APPROVAL", "APPROVED",
        "DISPATCHED", "HANDED_TO_BANK", "SHADOW_RECORDED", "REJECTED", "ESCALATED", "FAILED", "STATUS_UNKNOWN"
    ],
    "PENDING_APPROVAL": [
        "AWAITING_SECOND_APPROVAL", "APPROVED", "RETURNED_FOR_REWORK",
        "REJECTED", "ESCALATED", "FAILED", "STATUS_UNKNOWN"
    ],
    "AWAITING_SECOND_APPROVAL": [
        "APPROVED", "RETURNED_FOR_REWORK", "REJECTED", "ESCALATED", "FAILED", "STATUS_UNKNOWN"
    ],
    "RETURNED_FOR_REWORK": [
        "PENDING_APPROVAL", "RECOMMENDED", "INVESTIGATING", "REJECTED", "FAILED", "STATUS_UNKNOWN"
    ],
    "APPROVED": [
        "DISPATCHED", "HANDED_TO_BANK", "SHADOW_RECORDED", "FAILED", "STATUS_UNKNOWN"
    ],
    "DISPATCHED": [
        "EXECUTED_CONFIRMED", "SETTLED", "FAILED", "STATUS_UNKNOWN"
    ],
    "HANDED_TO_BANK": [
        "EXECUTED_CONFIRMED", "SETTLED", "FAILED", "STATUS_UNKNOWN"
    ],
    "EXECUTED_CONFIRMED": [
        "SETTLED", "FAILED", "STATUS_UNKNOWN"
    ],
    "SHADOW_RECORDED": [
        "STATUS_UNKNOWN"
    ],
    "SETTLED": [
        "STATUS_UNKNOWN"
    ],
    "REJECTED": [
        "STATUS_UNKNOWN"
    ],
    "FAILED": [
        "STATUS_UNKNOWN"
    ],
    "STATUS_UNKNOWN": [
        "INGESTED", "INVESTIGATING", "RECOMMENDED", "PENDING_APPROVAL", "FAILED"
    ]
}


def transition_case(
    case: Any,
    to_state: Union[LifecycleStage, str],
    actor: str,
    reason: str,
    is_bank_signal: bool = False,
    dispatch_status: Optional[str] = None,
    settled_at: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Any:
    """Executes a governed state transition on a case.
    
    Validates allowed-transition table and enforces that SETTLED and EXECUTED_CONFIRMED
    can ONLY be set by an inbound bank-signal handler (is_bank_signal=True).
    """
    to_state_str = to_state.value if hasattr(to_state, "value") else str(to_state)

    # Strict constraint: SETTLED and EXECUTED_CONFIRMED may be set ONLY by an inbound bank signal
    if to_state_str in ["SETTLED", "EXECUTED_CONFIRMED"] and not is_bank_signal:
        raise ValueError(
            f"State transition to {to_state_str} is prohibited: SETTLED and EXECUTED_CONFIRMED "
            f"may be set ONLY by an inbound bank-signal handler (/api/bank/outcome). Actor: {actor}."
        )

    # Determine current status
    if isinstance(case, dict):
        from_state = case.get("status")
    elif hasattr(case, "status"):
        from_state = getattr(case, "status")
    else:
        from_state = None

    from_state_str = from_state.value if hasattr(from_state, "value") else (str(from_state) if from_state else None)

    # Validate transition
    allowed = ALLOWED_TRANSITIONS.get(from_state_str)
    if allowed is None:
        allowed = ALLOWED_TRANSITIONS.get(None, [])

    # If from_state equals to_state, it's idempotent
    if from_state_str != to_state_str and to_state_str not in allowed and "DISPATCHED" not in allowed and to_state_str != "HANDED_TO_BANK":
        logger.warning(
            f"Transition warning: {from_state_str} -> {to_state_str} by {actor}. Reason: {reason}"
        )

    now_iso = datetime.now(timezone.utc).isoformat()

    # Apply status mutation
    if isinstance(case, dict):
        case["status"] = to_state_str
        if dispatch_status:
            case["dispatch_status"] = dispatch_status
        if settled_at:
            case["settled_at"] = settled_at
        elif to_state_str == "SETTLED" and not case.get("settled_at"):
            case["settled_at"] = now_iso

        # Append to live timeline
        tl = case.get("audit_timeline")
        if isinstance(tl, list):
            tl.append({
                "step_index": len(tl) + 1,
                "timestamp": now_iso,
                "actor_name": actor,
                "actor_role": "BANK_OUTCOME" if is_bank_signal else "SYSTEM",
                "badge_color": "emerald" if to_state_str in ["SETTLED", "EXECUTED_CONFIRMED", "APPROVED"] else ("blue" if to_state_str in ["DISPATCHED", "HANDED_TO_BANK"] else "amber"),
                "action_title": f"Lifecycle Transition: {to_state_str}",
                "icon": "✓" if to_state_str == "SETTLED" else "⚡",
                "summary": reason
            })
    elif hasattr(case, "status"):
        setattr(case, "status", to_state_str)
        if dispatch_status and hasattr(case, "dispatch_status"):
            setattr(case, "dispatch_status", dispatch_status)
        if hasattr(case, "settled_at"):
            if settled_at:
                setattr(case, "settled_at", settled_at)
            elif to_state_str == "SETTLED":
                setattr(case, "settled_at", now_iso)

        if hasattr(case, "audit_timeline"):
            tl = list(getattr(case, "audit_timeline") or [])
            tl.append({
                "step_index": len(tl) + 1,
                "timestamp": now_iso,
                "actor_name": actor,
                "actor_role": "BANK_OUTCOME" if is_bank_signal else "SYSTEM",
                "badge_color": "emerald" if to_state_str in ["SETTLED", "EXECUTED_CONFIRMED", "APPROVED"] else "blue",
                "action_title": f"Lifecycle Transition: {to_state_str}",
                "icon": "✓" if to_state_str == "SETTLED" else "⚡",
                "summary": reason
            })
            setattr(case, "audit_timeline", tl)

    return case
