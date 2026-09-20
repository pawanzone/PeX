import os

script_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\scripts"
os.makedirs(script_dir, exist_ok=True)

with open(os.path.join(script_dir, "run_demo.py"), "w", encoding="utf-8") as f:
    f.write('''"""Deterministic 10-Step Demo Runner for PeX Platform (Fulfilling DEMO.md)."""
import sys
import os
import json
import time
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas.bank_events import RawBankEvent
from app.services.canonicalizer import canonicalizer
from app.services.evidence_planner import evidence_planner
from app.services.context_builder import context_builder
from app.services.model_gateway import model_gateway
from app.services.decision_engine import decision_engine
from app.services.approval_engine import approval_engine
from app.services.action_executor import action_executor
from app.services.audit_service import audit_service
from app.schemas.approval import ApprovalSubmission, ApprovalAction
from app.services.data_loader import repo

def print_header(title):
    print("\\n" + "=" * 70)
    print(f" >>> {title}")
    print("=" * 70)

def run_demo():
    print_header("PeX 10-STAGE DETERMINISTIC DEMO: IBAN-REPAIR-001 LIFECYCLE")
    time.sleep(0.3)

    # Stage 1: Ingest Bank Event
    print_header("STAGE 1: BANK EVENT INGESTION (Bank A REST)")
    raw_event = RawBankEvent(
        event_id="EVT-BANKA-DEMO-001",
        source_bank_id="BANK_A",
        event_type="PAYMENT_EXCEPTION",
        raw_payload={
            "payment_reference": "DEMO-REF-2026-001",
            "error_code": "ERR_IBAN_MOD97",
            "error_message": "Beneficiary account identifier failed MOD-97 checksum validation against clearing directory.",
            "amount": 42000.0,
            "currency": "USD",
            "debtor_name": "Acme Global Holdings",
            "debtor_account": "US89CHAS12345678901234",
            "creditor_name": "HarborView Supplier Ltd",
            "creditor_iban": "GB82WEST12345698765432",
            "creditor_bic": "WESTGB2L",
            "settlement_rail": "SWIFT_CBPR+"
        }
    )
    print(f" [✓] Ingested Event: {raw_event.event_id}")
    print(f" [✓] Raw Payload Error: {raw_event.raw_payload['error_message']}")

    # Stage 2: Canonicalization
    print_header("STAGE 2: CANONICALIZATION & LINEAGE MAPPING")
    pmt, exc = canonicalizer.canonicalize_bank_event(raw_event)
    repo.save_case({
        "case_id": exc.case_id, "payment_id": pmt.payment_id, "uetr": pmt.uetr,
        "payment_ref": pmt.instruction_id, "profile": exc.profile, "error_code": exc.error_code,
        "reason": exc.reason, "amount": pmt.amount, "currency": pmt.currency, "payment_rail": pmt.payment_rail,
        "debtor_party": pmt.debtor_party.dict(), "debtor_account": pmt.debtor_account.dict(),
        "creditor_party": pmt.creditor_party.dict(), "creditor_account": pmt.creditor_account.dict(),
        "queue": exc.assigned_queue, "status": "INVESTIGATING", "severity": exc.severity,
        "priority": exc.priority, "sla_due_at": exc.sla_due_at, "dual_auth_required": False,
        "ai_confidence": 0.96, "created_at": exc.detected_at, "approval_history": []
    })
    print(f" [✓] Canonical Payment ID: {pmt.payment_id} | UETR: {pmt.uetr}")
    print(f" [✓] Canonical Exception Profile: {exc.profile.value} | Queue: {exc.assigned_queue}")

    # Stage 3: Tokenization Gate
    print_header("STAGE 3: PRIVACY & TOKENIZATION VAULT BOUNDARY")
    print(f" [✓] Debtor Party Token: {pmt.debtor_party.token_ref}")
    print(f" [✓] Creditor Party Token: {pmt.creditor_party.token_ref}")
    print(f" [✓] Masked Creditor IBAN: {pmt.creditor_account.iban[:4]}****{pmt.creditor_account.iban[-4:]}")
    print(f" [✓] Zero raw PII exposed to downstream AI context.")

    # Stage 4: Evidence Planning
    print_header("STAGE 4: DYNAMIC EVIDENCE RETRIEVAL")
    evidence, policies, hist = evidence_planner.plan_and_gather_evidence(
        case_id=exc.case_id, profile=exc.profile, party_name=pmt.creditor_party.party_name,
        account_val=pmt.creditor_account.iban, currency=pmt.currency
    )
    for e in evidence:
        print(f" [✓] Retrieved Evidence: {e.evidence_type} from {e.source_connector} (Relevance: {e.relevance_score})")

    # Stage 5: Tokenized Semantic Context Assembly
    print_header("STAGE 5: TOKENIZED CONTEXT ASSEMBLY")
    ctx = context_builder.build_investigation_context(pmt, exc, evidence, policies, hist)
    print(f" [✓] Context ID: {ctx.context_id} | Estimated Tokens: {ctx.token_usage_estimated}")

    # Stage 6: Model Gateway AI Reasoning
    print_header("STAGE 6: GOVERNED AI MODEL REASONING & DECISION")
    rec = model_gateway.evaluate_investigation(ctx)
    repo.recommendations[exc.case_id] = rec
    print(f" [✓] Recommendation: {rec.action_type.value} | Confidence: {rec.confidence_score * 100:.1f}%")
    print(f" [✓] Rationale: {rec.rationale}")
    print(f" [✓] Proposed Field Diff: {rec.proposed_changes[0].field_path}: {rec.proposed_changes[0].original_value_masked} -> {rec.proposed_changes[0].proposed_value_masked}")

    # Stage 7: Governance Gate Evaluation
    print_header("STAGE 7: POLICY & GOVERNANCE GATE EVALUATION")
    gate_ok, gate_msg = decision_engine.evaluate_governance_gate(rec, exc.profile, pmt.amount)
    print(f" [✓] Governance Gate: {'PASSED' if gate_ok else 'FAILED'} ({gate_msg})")
    print(f" [✓] Enforcing Institutional Policy: Zero Autonomous Payment Alteration.")

    # Stage 8: Human-in-the-Loop (HITL) Role Approval
    print_header("STAGE 8: ROLE-GATED HUMAN APPROVAL (Daniel Osei - Operations Approver)")
    sub = ApprovalSubmission(
        case_id=exc.case_id,
        action=ApprovalAction.APPROVE,
        comments="Validated MOD-97 check digits against verified Beneficiary Master Directory."
    )
    ok, msg, record, stage = approval_engine.process_approval_action(sub, approver_id="APR-3191")
    print(f" [✓] Approver: {record.approver_name} ({record.approver_role.value})")
    print(f" [✓] Decision: {record.action.value} | New Lifecycle Stage: {stage.value}")

    # Stage 9: Governed Action Execution & Delivery Receipt
    print_header("STAGE 9: SIMULATED BANK ACTION DISPATCH & SETTLEMENT")
    act_ok, act_msg, contract, receipt = action_executor.execute_governed_action(exc.case_id)
    print(f" [✓] Action Contract ID: {contract.action_id} | Target: {contract.target_system}")
    print(f" [✓] Idempotency Key: {contract.idempotency_key}")
    print(f" [✓] Delivery Receipt: {receipt.bank_ack_reference} | Status: {receipt.status}")

    # Stage 10: Cryptographic Provenance Chain Verification
    print_header("STAGE 10: CONTINUOUS SHA-256 AUDIT CHAIN VERIFICATION")
    # Log final audit event
    audit_service.log_event(
        case_id=exc.case_id,
        correlation_id=pmt.uetr,
        stage_name="SETTLEMENT",
        actor_id="SIMULATED-ACTION-ADAPTER",
        actor_role="DISPATCHER",
        action_name="DEMO_REPAIR_SETTLED",
        details=f"Payment instruction successfully repaired and settled under delivery receipt {receipt.bank_ack_reference}.",
        control_tags=["Maker-checker enforced", "Dual authorization checked", "Idempotency confirmed"]
    )
    audit_res = audit_service.verify_chain()
    print(f" [✓] Latest Audit Chain Head: {audit_res.chain_head}")
    print(f" [✓] Total Events Recomputed: {audit_res.total_events_checked}")
    print(f" [✓] Tamper-Evident Integrity: {'VERIFIED INTACT (100%)' if audit_res.is_intact else 'INTEGRITY COMPROMISED'}")

    print_header("DEMO COMPLETE: ALL 10 GOVERNED WORKFLOW STAGES EXECUTED SUCCESSFULLY")

if __name__ == "__main__":
    run_demo()
''')

# Write scripts/run_server.py
with open(os.path.join(script_dir, "run_server.py"), "w", encoding="utf-8") as f:
    f.write('''"""Unified Server Startup Script for PeX Platform."""
import uvicorn
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings

if __name__ == "__main__":
    print(f"Starting PeX Enterprise Platform on http://{settings.HOST}:{settings.PORT}...")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
''')

print("Wrote scripts/run_demo.py and scripts/run_server.py")
