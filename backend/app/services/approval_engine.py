"""Approval Engine: Enforces RBAC permissions, Segregation of Duties (Maker-Checker), and Dual-Authorization."""
import uuid
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

from app.schemas.approval import ApprovalRecord, ApprovalAction, UserRole, ApprovalSubmission
from app.schemas.canonical import LifecycleStage
from app.core.security import check_can_approve, get_persona
from app.services.data_loader import repo
from app.services.rule_engine import rule_engine
from app.services.state_machine import transition_case
from app.services import approval_routing
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
            queue=case.get("queue", "Repair"),
            user_id=approver.user_id,
            persona=approver,
            maker_id=case.get("maker_id")
        )
        if not can_approve:
            return False, reason, None, case.get("status")

        current_status = case.get("status")
        allowed_stages = [
            LifecycleStage.PENDING_APPROVAL,
            LifecycleStage.PENDING_APPROVAL.value,
            LifecycleStage.AWAITING_SECOND_APPROVAL,
            LifecycleStage.AWAITING_SECOND_APPROVAL.value
        ]
        if current_status not in allowed_stages:
            return False, f"Case is in {current_status} state, not awaiting approval", None, current_status

        rec = repo.recommendations.get(submission.case_id)
        rec_id = rec.recommendation_id if rec else "REC-MANUAL"
        approved_changes = submission.override_changes or (rec.proposed_changes if rec else [])

        # Dynamically evaluate active business rules & dual authorization policies
        active_rules = repo.get_policy_rules(status="ACTIVE")
        policy_eval = rule_engine.evaluate_case_policies(case, active_rules)
        # The profile pack can demand two steps (compliance, then risk); the policy/amount rule only adds to that.
        dual_auth = bool(policy_eval.get("dual_auth_required", False)) or approval_routing.pack_requires_two_steps(case)
        
        existing_approvals = repo.approvals.get(submission.case_id, [])

        _approving = submission.action in [ApprovalAction.APPROVE, ApprovalAction.CLEAR_FALSE_POSITIVE, ApprovalAction.GRANT_KYC_WAIVER, ApprovalAction.MODIFY]
        if _approving:
            _step = 2 if current_status in [LifecycleStage.AWAITING_SECOND_APPROVAL, LifecycleStage.AWAITING_SECOND_APPROVAL.value] else 1
            _why = approval_routing.step_role_violation(case, approver.role, _step)
            if _why:
                return False, _why, None, current_status

        if submission.action in [ApprovalAction.APPROVE, ApprovalAction.CLEAR_FALSE_POSITIVE, ApprovalAction.GRANT_KYC_WAIVER, ApprovalAction.MODIFY]:
            if current_status in [LifecycleStage.PENDING_APPROVAL, LifecycleStage.PENDING_APPROVAL.value]:
                # Level 1 Approval
                if dual_auth:
                    next_stage = LifecycleStage.AWAITING_SECOND_APPROVAL
                    step_no = 1
                else:
                    next_stage = LifecycleStage.APPROVED
                    step_no = 1
            elif current_status in [LifecycleStage.AWAITING_SECOND_APPROVAL, LifecycleStage.AWAITING_SECOND_APPROVAL.value]:
                # Level 2 Dual Authorization
                # Find the most recent Level 1 approver who signed step 1 in the current cycle
                valid_l1_approvals = [
                    a for a in existing_approvals
                    if a.action in [ApprovalAction.APPROVE, ApprovalAction.CLEAR_FALSE_POSITIVE, ApprovalAction.GRANT_KYC_WAIVER, ApprovalAction.MODIFY]
                    and a.step_number == 1
                ]
                if valid_l1_approvals:
                    last_l1_approver = valid_l1_approvals[-1]
                    if last_l1_approver.approver_id == approver_id:
                        return False, f"Dual Authorization violation: Second approver must be a distinct officer from the first approver ({last_l1_approver.approver_name}).", None, current_status
                next_stage = LifecycleStage.APPROVED
                step_no = 2
            else:
                next_stage = LifecycleStage.APPROVED
                step_no = 1
        elif submission.action == ApprovalAction.RETURN_TO_MAKER:
            next_stage = LifecycleStage.RETURNED_FOR_REWORK
            step_no = 1
        elif submission.action == ApprovalAction.REJECT:
            next_stage = LifecycleStage.REJECTED
            step_no = 1
        elif submission.action == ApprovalAction.ESCALATE:
            next_stage = LifecycleStage.ESCALATED
            step_no = 1
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
            comments=submission.comments or f"Decision executed by {approver.name} ({approver.role.value})",
            approved_changes=approved_changes,
            step_number=step_no,
            created_at=datetime.utcnow()
        )

        repo.save_approval(record)

        transition_case(
            case=case,
            to_state=next_stage,
            actor=f"{approver.name} ({approver.role.value if hasattr(approver.role, 'value') else approver.role})",
            reason=f"Approval action {submission.action.value if hasattr(submission.action, 'value') else submission.action} executed (Step {step_no})."
        )
        case["expedite_ping"] = None
        if "approval_history" not in case:
            case["approval_history"] = []
        
        # Serialize record with ISO timestamp string for JSON
        rec_dict = record.model_dump() if hasattr(record, "model_dump") else record.dict()
        rec_dict["created_at"] = record.created_at.isoformat() if isinstance(record.created_at, datetime) else str(record.created_at)
        case["approval_history"].append(rec_dict)

        # Append to live audit_timeline
        if "audit_timeline" not in case:
            case["audit_timeline"] = []
            
        badge_color = "emerald"
        action_title = "Approval Sign-off Recorded"
        icon = "🛡️"
        if submission.action == ApprovalAction.RETURN_TO_MAKER:
            badge_color = "amber"
            action_title = "Returned to Maker for Rework"
            icon = "⚠️"
        elif submission.action == ApprovalAction.CLEAR_FALSE_POSITIVE:
            badge_color = "emerald"
            action_title = "Sanctions False Positive Cleared"
            icon = "✓"
        elif submission.action == ApprovalAction.GRANT_KYC_WAIVER:
            badge_color = "blue"
            action_title = "30-Day KYC Waiver Granted"
            icon = "📋"
        elif submission.action == ApprovalAction.REJECT:
            badge_color = "red"
            action_title = "Payment Exception Rejected / Blocked"
            icon = "✕"
        elif submission.action == ApprovalAction.MODIFY:
            badge_color = "purple" if step_no == 2 else "emerald"
            action_title = "Level 2 Dual Authorization (Modified)" if step_no == 2 else "Approval Sign-off (Modified)"
            icon = "🔒" if step_no == 2 else "✏️"
        elif step_no == 2:
            badge_color = "purple"
            action_title = "Level 2 Dual Authorization Approved"
            icon = "🔒"

        case["audit_timeline"].append({
            "step_index": len(case["audit_timeline"]) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "actor_name": approver.name,
            "actor_role": approver.role.value,
            "badge_color": badge_color,
            "action_title": action_title,
            "icon": icon,
            "summary": submission.comments or f"Decision executed by {approver.name} ({approver.role.value})"
        })

        repo.save_case(case)

        # Log to global continuous audit stream
        from app.services.audit_service import audit_service
        audit_service.log_event(
            case_id=submission.case_id,
            correlation_id=case.get("uetr", ""),
            stage_name="HITL_APPROVAL",
            actor_id=approver.user_id,
            actor_role=approver.role.value,
            action_name=f"APPROVAL_{submission.action.value}",
            details=f"Decision executed by {approver.name} ({approver.role.value}): {submission.comments}",
            control_tags=["Segregation of duties verified", "Audit chain updated", "Governance gate cleared"]
        )

        return True, f"Approval action {submission.action.value} recorded successfully.", record, next_stage

approval_engine = ApprovalEngine()
