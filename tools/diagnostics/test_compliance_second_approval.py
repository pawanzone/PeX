import sys
sys.path.insert(0, r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend")

from app.services.data_loader import repo
from app.services.approval_engine import approval_engine
from app.schemas.approval import ApprovalSubmission, ApprovalAction
from app.schemas.canonical import LifecycleStage

# Reset and load fresh 50 cases
repo.load_all_data()

# Find cases in AWAITING_SECOND_APPROVAL
dual_auth_cases = [c for c in repo.cases.values() if c["status"] == LifecycleStage.AWAITING_SECOND_APPROVAL]
print(f"Found {len(dual_auth_cases)} cases awaiting second approval:")
for c in dual_auth_cases:
    print(f" - {c['case_id']} | Profile: {c['profile']} | Queue: {c['queue']} | Amount: ${c['amount']:,.2f}")

# Test Marisol Vega (Compliance Approver) doing 2nd level approval on all of them
for c in dual_auth_cases:
    cid = c["case_id"]
    sub = ApprovalSubmission(
        case_id=cid,
        action=ApprovalAction.APPROVE,
        comments="Tier 2 Dual Authorization Approved by Marisol Vega (Compliance Approver)"
    )
    ok, msg, rec, stage = approval_engine.process_approval_action(sub, approver_id="CMP-4420")
    print(f"Approval for {cid}: Success={ok} | Stage={stage} | Approver={rec.approver_name if rec else None} | Msg={msg}")
