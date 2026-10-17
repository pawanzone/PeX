"""Governed State Machine & Transition Kernel for the PeX case lifecycle.

Invariants enforced here (and tested in tests/test_p05_hardening.py):
  1. EVERY lifecycle status write goes through transition_case().
  2. Transitions not in ALLOWED_TRANSITIONS raise IllegalTransition (no silent warnings).
  3. SETTLED / EXECUTED_CONFIRMED (and bank REJECTED/FAILED outcomes) can ONLY be set with
     is_bank_signal=True, i.e. from the authenticated inbound bank-outcome handler.
  4. PeX never settles: the strongest state PeX can reach by itself is DISPATCHED (handed to bank).
"""
from typing import Dict, Any, Optional, Union, FrozenSet
from datetime import datetime, timezone
import logging

from app.schemas.canonical import LifecycleStage

logger = logging.getLogger(__name__)


class IllegalTransition(ValueError):
    """Raised when a lifecycle transition is not permitted."""


# HANDED_TO_BANK is an alias of DISPATCHED (same canonical value).
BANK_SIGNAL_ONLY: FrozenSet[str] = frozenset({"EXECUTED_CONFIRMED", "SETTLED"})
BANK_SIGNAL_TARGETS: FrozenSet[str] = frozenset({"EXECUTED_CONFIRMED", "SETTLED", "REJECTED", "FAILED"})

ALLOWED_TRANSITIONS: Dict[Optional[str], FrozenSet[str]] = {k: frozenset(v) for k, v in {
    None: ["INGESTED", "CANONICALIZED", "VALIDATED", "RECOMMENDED", "PENDING_APPROVAL"],
    "INGESTED": ["CANONICALIZED", "VALIDATED", "INVESTIGATING", "RECOMMENDED", "PENDING_APPROVAL",
                 "ESCALATED", "FAILED", "STATUS_UNKNOWN"],
    "CANONICALIZED": ["VALIDATED", "INVESTIGATING", "RECOMMENDED", "PENDING_APPROVAL", "ESCALATED", "FAILED"],
    "VALIDATED": ["INVESTIGATING", "RECOMMENDED", "PENDING_APPROVAL", "ESCALATED", "FAILED"],
    "INVESTIGATING": ["VALIDATED", "RECOMMENDED", "PENDING_APPROVAL", "ESCALATED", "FAILED"],
    "RECOMMENDED": ["PENDING_APPROVAL", "APPROVED", "SHADOW_RECORDED", "INVESTIGATING", "REJECTED",
                    "ESCALATED", "FAILED"],
    "PENDING_APPROVAL": ["AWAITING_SECOND_APPROVAL", "APPROVED", "RETURNED_FOR_REWORK", "REJECTED",
                         "ESCALATED", "RECOMMENDED", "FAILED"],
    "AWAITING_SECOND_APPROVAL": ["APPROVED", "RETURNED_FOR_REWORK", "REJECTED", "ESCALATED", "PENDING_APPROVAL"],
    "RETURNED_FOR_REWORK": ["PENDING_APPROVAL", "RECOMMENDED", "INVESTIGATING", "REJECTED", "ESCALATED"],
    "ESCALATED": ["PENDING_APPROVAL", "RECOMMENDED", "REJECTED"],
    "APPROVED": ["DISPATCHED", "SHADOW_RECORDED", "FAILED"],
    "DISPATCHED": ["EXECUTED_CONFIRMED", "SETTLED", "REJECTED", "FAILED", "STATUS_UNKNOWN"],
    "EXECUTED_CONFIRMED": ["SETTLED", "FAILED", "STATUS_UNKNOWN"],
    "STATUS_UNKNOWN": ["EXECUTED_CONFIRMED", "SETTLED", "REJECTED", "FAILED", "INVESTIGATING"],
    "SHADOW_RECORDED": [],
    "SETTLED": [],
    "REJECTED": [],
    "FAILED": ["PENDING_APPROVAL"],
}.items()}


def normalize_status(value: Any) -> Optional[str]:
    """Canonical string for a status (handles Enum members and 'LifecycleStage.X' strings; HANDED_TO_BANK -> DISPATCHED)."""
    if value is None:
        return None
    if hasattr(value, "value"):
        value = value.value
    s = str(value).strip()
    if s.startswith("LifecycleStage."):
        s = s[len("LifecycleStage."):]
    if s == "HANDED_TO_BANK":
        s = "DISPATCHED"
    return s or None


def _get(case: Any, key: str):
    return case.get(key) if isinstance(case, dict) else getattr(case, key, None)


def _set(case: Any, key: str, value: Any):
    if isinstance(case, dict):
        case[key] = value
    elif hasattr(case, key):
        setattr(case, key, value)


def transition_case(
    case: Any,
    to_state: Union[LifecycleStage, str],
    actor: str,
    reason: str,
    is_bank_signal: bool = False,
    dispatch_status: Optional[str] = None,
    settled_at: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    system_reset: bool = False,
) -> Any:
    """Executes a governed lifecycle transition on a case (dict or ORM object).

    system_reset=True bypasses the transition table (seed/demo reset only) but NEVER the
    bank-signal rule for SETTLED/EXECUTED_CONFIRMED.
    """
    to_s = normalize_status(to_state)
    from_s = normalize_status(_get(case, "status"))

    if to_s in BANK_SIGNAL_ONLY and not is_bank_signal:
        raise IllegalTransition(
            f"Transition to {to_s} is prohibited: it may be set ONLY by an inbound bank-signal handler (authenticated inbound bank "
            f"signal on /api/bank/outcome). Actor: {actor}."
        )
    if is_bank_signal and to_s not in BANK_SIGNAL_TARGETS:
        raise IllegalTransition(f"A bank signal may only produce {sorted(BANK_SIGNAL_TARGETS)}, not {to_s}.")

    if from_s != to_s and not system_reset:
        allowed = ALLOWED_TRANSITIONS.get(from_s)
        if allowed is None or to_s not in allowed:
            raise IllegalTransition(f"Illegal lifecycle transition {from_s} -> {to_s} by {actor}. Reason given: {reason}")

    now_iso = datetime.now(timezone.utc).isoformat()
    _set(case, "status", to_s)
    if dispatch_status:
        _set(case, "dispatch_status", dispatch_status)
    if to_s == "DISPATCHED":
        _set(case, "handed_off_at", now_iso)
    if to_s in ("EXECUTED_CONFIRMED", "SETTLED", "REJECTED", "FAILED") and is_bank_signal:
        _set(case, "dispatch_status", "BANK_" + to_s)
    if to_s == "SETTLED":
        _set(case, "settled_at", settled_at or _get(case, "settled_at") or now_iso)
    elif settled_at:
        _set(case, "settled_at", settled_at)

    # Append to the case timeline
    tl = _get(case, "audit_timeline")
    color = ("emerald" if to_s in ("SETTLED", "EXECUTED_CONFIRMED", "APPROVED")
             else "blue" if to_s in ("DISPATCHED", "RECOMMENDED", "VALIDATED")
             else "red" if to_s in ("REJECTED", "FAILED", "STATUS_UNKNOWN") else "amber")
    entry_title = {"DISPATCHED": "Handed to bank (awaiting confirmation)",
                   "SHADOW_RECORDED": "Shadow mode: recommendation recorded, no action taken",
                   "EXECUTED_CONFIRMED": "Bank confirmed execution", "SETTLED": "Bank confirmed settlement",
                   "STATUS_UNKNOWN": "Execution status unknown: do not resend"}.get(to_s, f"Lifecycle transition: {to_s}")
    entry = {
        "step_index": (len(tl) + 1) if isinstance(tl, list) else 1,
        "timestamp": now_iso,
        "actor_name": actor,
        "actor_role": "BANK_OUTCOME" if is_bank_signal else "SYSTEM",
        "badge_color": color,
        "action_title": entry_title,
        "icon": "✓" if to_s in ("SETTLED", "EXECUTED_CONFIRMED") else "⚡",
        "summary": reason,
    }
    if isinstance(tl, list):
        if isinstance(case, dict):
            tl.append(entry)
        else:
            _set(case, "audit_timeline", list(tl) + [entry])
    elif tl is None and not isinstance(case, dict) and hasattr(case, "audit_timeline"):
        _set(case, "audit_timeline", [entry])
    return case
