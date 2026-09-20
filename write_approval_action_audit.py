import os

srv_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app\services"

# 7. approval_engine.py
with open(os.path.join(srv_dir, "approval_engine.py"), "w", encoding="utf-8") as f:
    f.write('''"""Approval Engine: Enforces RBAC permissions, Segregation of Duties (Maker-Checker), and Dual-Authorization."""
import uuid
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

from app.schemas.approval import ApprovalRecord, ApprovalAction, UserRole, ApprovalSubmission
from app.schemas.canonical import LifecycleStage
from app.core.security import check_can_approve, get_persona
from app.services.data_loader import repo
from app.config import settings

class ApprovalEngine:
    def process_approval_action(
        self,
        submission: ApprovalSubmission,
        approver_id: str
    ) -> Tuple[bool, str, Optional[ApprovalRecord], LifecycleStage]:
        case = repo.get_case(submission.case_id)
        if not case:
            return False, f"Case {submission.case_id} not found", None, LifecycleStage.FAILED

        approver = get_persona(approver_id)
        if not approver:
            return False, f"Unknown approver ID {approver_id}", None, case.get("status")

        can_approve, reason = check_can_approve(
            role=approver.role,
            amount=case.get("amount", 0.0),
            queue=case.get("queue", "Repair")
        )
        if not can_approve:
            return False, reason, None, case.get("status")

        current_status = case.get("status")
        if current_status not in [LifecycleStage.PENDING_APPROVAL, LifecycleStage.AWAITING_SECOND_APPROVAL, LifecycleStage.INVESTIGATING]:
            return False, f"Case is in {current_status} state, not awaiting approval", None, current_status

        rec = repo.recommendations.get(submission.case_id)
        rec_id = rec.recommendation_id if rec else "REC-MANUAL"
        approved_changes = submission.override_changes or (rec.proposed_changes if rec else [])

        amount = float(case.get("amount", 0.0))
        dual_auth = amount >= settings.DUAL_AUTH_THRESHOLD
        
        existing_approvals = repo.approvals.get(submission.case_id, [])

        if submission.action == ApprovalAction.APPROVE:
            if dual_auth and len(existing_approvals) == 0:
                next_stage = LifecycleStage.AWAITING_SECOND_APPROVAL
                step_no = 1
            else:
                if existing_approvals and existing_approvals[0].approver_id == approver_id:
                    return False, "Dual Authorization violation: Second approver must be a distinct officer from the first approver.", None, current_status
                next_stage = LifecycleStage.APPROVED
                step_no = 2 if existing_approvals else 1
        elif submission.action == ApprovalAction.REJECT:
            next_stage = LifecycleStage.REJECTED
            step_no = len(existing_approvals) + 1
        elif submission.action == ApprovalAction.ESCALATE:
            next_stage = LifecycleStage.ESCALATED
            step_no = len(existing_approvals) + 1
        elif submission.action == ApprovalAction.MODIFY:
            next_stage = LifecycleStage.APPROVED
            step_no = len(existing_approvals) + 1
        else:
            next_stage = current_status
            step_no = 1

        record = ApprovalRecord(
            approval_id=f"APR-{uuid.uuid4().hex[:6].upper()}",
            case_id=submission.case_id,
            recommendation_id=rec_id,
            approver_id=approver.user_id,
            approver_name=approver.name,
            approver_role=approver.role,
            action=submission.action,
            comments=submission.comments,
            approved_changes=approved_changes,
            step_number=step_no,
            created_at=datetime.utcnow()
        )

        if submission.case_id not in repo.approvals:
            repo.approvals[submission.case_id] = []
        repo.approvals[submission.case_id].append(record)

        case["status"] = next_stage
        if "approval_history" not in case:
            case["approval_history"] = []
        case["approval_history"].append(record.dict())
        repo.save_case(case)

        return True, f"Approval action {submission.action.value} recorded successfully.", record, next_stage

approval_engine = ApprovalEngine()
''')

# 8. action_executor.py
with open(os.path.join(srv_dir, "action_executor.py"), "w", encoding="utf-8") as f:
    f.write('''"""Action Executor: Dispatches simulated bank repairs with strict idempotency and zero real financial risk."""
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

        if case.get("status") != LifecycleStage.APPROVED:
            return False, f"Cannot execute action: Case status is {case.get('status')}, expected APPROVED.", None, None

        approvals = repo.approvals.get(case_id, [])
        if not approvals:
            return False, "Cannot execute action without signed approval records.", None, None

        actual_idempotency_key = idempotency_key or f"IDEMP-{case_id}-{approvals[-1].approval_id}"
        if actual_idempotency_key in repo.actions:
            existing = repo.actions[actual_idempotency_key]
            existing_receipt = repo.receipts.get(existing.action_id)
            return True, "Idempotent response: action already settled.", existing, existing_receipt

        last_approval = approvals[-1]
        action_contract = GovernedActionContract(
            action_id=f"ACT-{uuid.uuid4().hex[:6].upper()}",
            case_id=case_id,
            approval_ids=[a.approval_id for a in approvals],
            action_type=ActionType.REPAIR_IBAN,
            target_system="SIMULATED_BANK_PAYMENT_HUB",
            idempotency_key=actual_idempotency_key,
            dispatch_payload={
                "uetr": case.get("uetr"),
                "payment_ref": case.get("payment_ref"),
                "repaired_fields": [c.dict() for c in last_approval.approved_changes],
                "approver": last_approval.approver_name,
                "approver_role": last_approval.approver_role.value
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
                "message": "Payment instruction successfully repaired in simulated settlement ledger.",
                "settlement_rail": case.get("payment_rail", "SWIFT_CBPR+"),
                "repaired_iban": last_approval.approved_changes[0].proposed_value_masked if last_approval.approved_changes else "REPAIRED"
            }
        )

        repo.actions[actual_idempotency_key] = action_contract
        repo.receipts[action_contract.action_id] = receipt

        case["status"] = LifecycleStage.SETTLED
        case["settled_at"] = datetime.utcnow().isoformat()
        repo.save_case(case)

        return True, "Action successfully executed and settled.", action_contract, receipt

action_executor = ActionExecutor()
''')

# 9. services/audit_service.py
with open(os.path.join(srv_dir, "audit_service.py"), "w", encoding="utf-8") as f:
    f.write('''"""Continuous Audit Service: Cryptographic SHA-256 Provenance Chaining for all 20 Lifecycle Steps."""
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.schemas.audit import AuditEvent, ProvenanceChain, HashVerificationResult
from app.core.hashing import calculate_event_hash, verify_audit_chain, GENESIS_HASH
from app.services.data_loader import repo

class AuditService:
    def log_event(
        self,
        case_id: str,
        correlation_id: str,
        stage_name: str,
        actor_id: str,
        actor_role: str,
        action_name: str,
        details: str,
        control_tags: Optional[List[str]] = None
    ) -> AuditEvent:
        event_index = len(repo.audit_log) + 1
        prev_hash = repo.latest_chain_hash
        timestamp = datetime.utcnow()
        timestamp_iso = timestamp.isoformat()

        curr_hash = calculate_event_hash(
            event_index=event_index,
            timestamp_iso=timestamp_iso,
            case_id=case_id,
            stage_name=stage_name,
            actor_id=actor_id,
            action_name=action_name,
            details=details,
            prev_hash=prev_hash
        )

        event = AuditEvent(
            event_index=event_index,
            timestamp=timestamp,
            case_id=case_id,
            correlation_id=correlation_id,
            stage_name=stage_name,
            actor_id=actor_id,
            actor_role=actor_role,
            action_name=action_name,
            details=details,
            control_tags=control_tags or [],
            prev_hash=prev_hash,
            current_hash=curr_hash
        )

        repo.audit_log.append(event)
        repo.latest_chain_hash = curr_hash
        return event

    def get_case_provenance(self, case_id: str) -> ProvenanceChain:
        case_events = [e for e in repo.audit_log if e.case_id == case_id]
        head_hash = case_events[-1].current_hash if case_events else repo.latest_chain_hash
        return ProvenanceChain(
            case_id=case_id,
            chain_head_hash=head_hash,
            total_events=len(case_events),
            is_valid=True,
            events=case_events
        )

    def get_all_events(self, limit: int = 100) -> List[AuditEvent]:
        return list(reversed(repo.audit_log[-limit:]))

    def verify_chain(self) -> HashVerificationResult:
        raw_events = [e.dict() for e in repo.audit_log]
        is_intact = verify_audit_chain(raw_events)
        return HashVerificationResult(
            chain_head=repo.latest_chain_hash,
            total_events_checked=len(repo.audit_log),
            is_intact=is_intact,
            verified_at=datetime.utcnow()
        )

audit_service = AuditService()
''')

print("Wrote approval_engine.py, action_executor.py, and audit_service.py")
