"""Action Executor: Dispatches simulated bank repairs with strict idempotency and zero real financial risk."""
import uuid
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

from app.schemas.action import GovernedActionContract, DeliveryReceipt, ActionStatus
from app.schemas.canonical import LifecycleStage
from app.schemas.recommendation import ActionType
from app.services.data_loader import repo

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
            return True, "Idempotent response: action already settled.", existing, existing_receipt

        approvals = repo.approvals.get(case_id, [])
        if not approvals:
            return False, "Cannot execute action without signed approval records.", None, None

        actual_idempotency_key = idempotency_key or f"IDEMP-{case_id}-{approvals[-1].approval_id}"
        if actual_idempotency_key in repo.actions:
            existing = repo.actions[actual_idempotency_key]
            existing_receipt = repo.receipts.get(existing.action_id)
            return True, "Idempotent response: action already settled.", existing, existing_receipt

        if case.get("status") != LifecycleStage.APPROVED:
            return False, f"Cannot execute action: Case status is {case.get('status')}, expected APPROVED.", None, None

        last_approval = approvals[-1]
        rec = repo.recommendations.get(case_id)
        action_type = rec.action_type if rec else ActionType.REPAIR_DATA

        action_contract = GovernedActionContract(
            action_id=f"ACT-{uuid.uuid4().hex[:6].upper()}",
            case_id=case_id,
            approval_ids=[a.approval_id for a in approvals],
            action_type=action_type,
            target_system="SIMULATED_BANK_PAYMENT_HUB",
            idempotency_key=actual_idempotency_key,
            dispatch_payload={
                "uetr": case.get("uetr"),
                "payment_ref": case.get("payment_ref"),
                "repaired_fields": [c.dict() for c in last_approval.approved_changes],
                "approver": last_approval.approver_name,
                "approver_role": last_approval.approver_role.value,
                "action_type": action_type.value
            },
            status=ActionStatus.SETTLED,
            dispatched_at=datetime.utcnow(),
            settled_at=datetime.utcnow()
        )

        receipt = DeliveryReceipt(
            receipt_id=f"RCPT-{uuid.uuid4().hex[:6].upper()}",
            action_id=action_contract.action_id,
            case_id=case_id,
            bank_ack_reference=f"ACK-SIM-{uuid.uuid4().hex[:8].upper()}",
            status="SETTLED_CONFIRMED",
            timestamp=datetime.utcnow(),
            details={
                "message": f"Governed action {action_type.value} successfully reconciled against external settlement ledger.",
                "settlement_rail": case.get("payment_rail", "SWIFT_CBPR+"),
                "action_type": action_type.value,
                "repaired_summary": last_approval.approved_changes[0].proposed_value_masked if last_approval.approved_changes else "GOVERNED_EXECUTION_COMPLETE"
            }
        )

        repo.actions[actual_idempotency_key] = action_contract
        repo.receipts[action_contract.action_id] = receipt

        case["status"] = LifecycleStage.SETTLED.value
        case["settled_at"] = datetime.utcnow().isoformat()
        case["expedite_ping"] = None
        
        if "audit_timeline" not in case:
            case["audit_timeline"] = []
        case["audit_timeline"].append({
            "step_index": len(case["audit_timeline"]) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "actor_name": "PeX Settlement Kernel",
            "actor_role": "SYSTEM",
            "badge_color": "emerald",
            "action_title": "Governed Settlement Dispatched & Reconciled",
            "icon": "✓",
            "summary": f"Transaction sealed and dispatched against bank rail. Delivery Receipt: {receipt.bank_ack_reference}."
        })
        repo.save_case(case)

        return True, "Action successfully executed and settled.", action_contract, receipt

action_executor = ActionExecutor()
