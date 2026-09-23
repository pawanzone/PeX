import sys
sys.path.insert(0, r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend")

from app.services.data_loader import repo
from app.services.approval_engine import approval_engine
from app.schemas.approval import ApprovalSubmission, ApprovalAction
from app.core.security import get_persona, check_can_approve

persona = get_persona("CMP-4420")
print("Persona CMP-4420:", persona)

case = repo.get_case("PEX-KYC-0017")
print("Case PEX-KYC-0017:", case["case_id"], case["profile"], case["amount"], case["status"], case["queue"])

can_app, reason = check_can_approve(persona.role, case["amount"], case["queue"])
print("Can approve?", can_app, reason)

sub = ApprovalSubmission(
    case_id="PEX-KYC-0017",
    action=ApprovalAction.APPROVE,
    comments="Compliance dual-auth approved by Marisol Vega"
)
ok, msg, rec, stage = approval_engine.process_approval_action(sub, approver_id="CMP-4420")
print("Approval result:", ok, msg, stage)
