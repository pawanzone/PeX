"""Action Executor: Dispatches governed payment repairs to bank execution systems."""
import uuid
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone

from app.schemas.action import GovernedActionContract, DeliveryReceipt, ActionStatus
from app.schemas.canonical import LifecycleStage
from app.schemas.recommendation import ActionType
from app.services.data_loader import repo
from app.services.state_machine import transition_case, normalize_status
from app.services.outbound_port import dispatch_to_bank_handoff


class ActionExecutor:
    def execute_governed_action(
        self,
        case_id: str,
        idempotency_key: Optional[str] = None
    ) -> Tuple[bool, str, Optional[GovernedActionContract], Optional[DeliveryReceipt]]:
        case = repo.get_case(case_id)
        if not case:
            return False, f"Case {case_id} not found", None, None

        # Check if already executed under provided idempotency key
        if idempotency_key and idempotency_key in repo.actions:
            existing = repo.actions[idempotency_key]
            existing_receipt = repo.receipts.get(existing.action_id)
            return True, "Idempotent response: action already handed off.", existing, existing_receipt

        approvals = repo.approvals.get(case_id, [])
        if not approvals:
            return False, "Cannot execute action without signed approval records.", None, None

        actual_idempotency_key = idempotency_key or f"IDEMP-{case_id}-{approvals[-1].approval_id}"
        if actual_idempotency_key in repo.actions:
            existing = repo.actions[actual_idempotency_key]
            existing_receipt = repo.receipts.get(existing.action_id)
            return True, "Idempotent response: action already handed off.", existing, existing_receipt

        if normalize_status(case.get("status")) != LifecycleStage.APPROVED.value:
            st = normalize_status(case.get("status"))
            hint = " Do NOT resend: the bank has not confirmed." if st == "STATUS_UNKNOWN" else ""
            return False, f"Cannot execute action: Case status is {st}, expected APPROVED.{hint}", None, None

        last_approval = approvals[-1]
        rec = repo.recommendations.get(case_id)
        action_type = rec.action_type if rec else ActionType.REPAIR_DATA

        action_contract = GovernedActionContract(
            action_id=f"ACT-{uuid.uuid4().hex[:6].upper()}",
            case_id=case_id,
            approval_ids=[a.approval_id for a in approvals],
            action_type=action_type,
            target_system="BANK_PAYMENT_HUB",
            idempotency_key=actual_idempotency_key,
            dispatch_payload={
                "uetr": case.get("uetr"),
                "payment_ref": case.get("payment_ref"),
                "repaired_fields": [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in last_approval.approved_changes],
                "approver": last_approval.approver_name,
                "approver_role": last_approval.approver_role.value if hasattr(last_approval.approver_role, "value") else str(last_approval.approver_role),
                "action_type": action_type.value if hasattr(action_type, "value") else str(action_type)
            },
            status=ActionStatus.DISPATCHED,
            dispatched_at=datetime.now(timezone.utc),
            settled_at=None
        )

        # Single outbound choke point: mode-aware (SHADOW suppresses, ASSISTED needs a named human approver).
        actor_label = f"{last_approval.approver_name} ({last_approval.approver_role.value if hasattr(last_approval.approver_role, 'value') else last_approval.approver_role})"
        result = dispatch_to_bank_handoff(
            case, action_contract=action_contract, actor=actor_label,
            approved_by=last_approval.approver_id,
            reason="Governed action authorized and handed to bank execution system; awaiting bank ACK.")
        case["expedite_ping"] = None
        repo.save_case(case)
        if not result["dispatched"] and result["mode"] != "SHADOW":
            return False, result["message"], None, None

        repo.actions[actual_idempotency_key] = action_contract
        if result["mode"] == "SHADOW":
            return True, "SHADOW mode: recommendation recorded; nothing was sent to the bank.", action_contract, None
        # No synthetic receipt is generated. The bank's answer arrives via the signed /api/bank/outcome path.
        return True, "Action handed off to the bank (awaiting bank confirmation).", action_contract, None


action_executor = ActionExecutor()
