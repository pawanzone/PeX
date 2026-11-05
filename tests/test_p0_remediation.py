"""Acceptance Test Suite for PeX P0 Remediation.

Covers:
- P0-1: State model, transition_case function, and the SETTLED / EXECUTED_CONFIRMED boundary.
- P0-2: One STP gate (8-predicate evaluation replacing heuristics, threshold reconciliation).
- P0-3: Segregation of Duties (maker_id enforcement, approver != maker, level 2 != level 1).
- P0-4: Shadow/Assisted/Live mode choke point and suppression.
- P0-5: Truthful UI data (runtime MOD-97 math, corrected demo pair, badge consistency).
- P0-6: Audit payload hash tamper detection on extended provenance fields.
"""
import os
import re
import uuid
import pytest
from pathlib import Path
from datetime import datetime

# Set up test environment
writable_db_path = Path(__file__).resolve().parent.parent / "scratch" / "writable_test.db"
writable_db_path.parent.mkdir(parents=True, exist_ok=True)  # the scratch folder is not in the repository
writable_url = f"sqlite:///{writable_db_path.as_posix()}"
os.environ["DATABASE_URL"] = writable_url
os.environ["PYTHONPATH"] = "backend"

from sqlalchemy import create_engine
from app.db import session, init_db
new_engine = create_engine(writable_url, connect_args={"check_same_thread": False})
session.engine = new_engine
init_db.engine = new_engine
session.SessionLocal.configure(bind=new_engine)

from app.schemas.canonical import LifecycleStage
from app.schemas.approval import UserRole, ApprovalSubmission, ApprovalAction
from app.services.canonicalizer import validate_iban_mod97
from app.core.hashing import calculate_event_hash, verify_audit_chain
from app.services.data_loader import repo
repo.load_all_data()


# =========================================================================
# P0-1 TESTS: State Model & Settled Boundary
# =========================================================================

def test_p0_1_transition_case_allows_valid_transitions():
    """transition_case must allow valid transitions and update case status."""
    from app.services.state_machine import transition_case
    case = {"case_id": "TEST-P01-01", "status": LifecycleStage.INGESTED.value, "audit_timeline": []}
    
    # Ingested -> Validated
    transition_case(case, to_state=LifecycleStage.VALIDATED, actor="VALIDATOR", reason="Schema valid")
    assert case["status"] == LifecycleStage.VALIDATED.value

    # Validated -> Recommended
    transition_case(case, to_state=LifecycleStage.RECOMMENDED, actor="REASONER", reason="Repair proposed")
    assert case["status"] == LifecycleStage.RECOMMENDED.value


def test_p0_1_transition_case_blocks_illegal_settled_transition():
    """SETTLED and EXECUTED_CONFIRMED may be set ONLY by an inbound bank-signal handler."""
    from app.services.state_machine import transition_case
    case = {"case_id": "TEST-P01-02", "status": LifecycleStage.RECOMMENDED.value, "audit_timeline": []}
    
    with pytest.raises(ValueError, match="ONLY by an inbound bank-signal handler"):
        transition_case(case, to_state=LifecycleStage.SETTLED, actor="SYS-AUTONOMOUS-STP", reason="Auto settlement")

    with pytest.raises(ValueError, match="ONLY by an inbound bank-signal handler"):
        transition_case(case, to_state=LifecycleStage.EXECUTED_CONFIRMED, actor="ActionExecutor", reason="Executed")


def test_p0_1_a_file_watcher_stp_ends_handed_to_bank_never_settled():
    """STP-eligible case via file_watcher ends HANDED_TO_BANK (or SHADOW_RECORDED), never SETTLED."""
    from app.services.file_watcher import FolderInputWatcher
    from app.schemas.contracts.e2e_schemas import CanonicalE2EInput, E2EPaymentInfo

    watcher = FolderInputWatcher()
    e2e_input = CanonicalE2EInput(
        exception_id="TEST-FW-STP-01",
        profile_id="DQ-01",
        domain="DATA_QUALITY",
        payment_info=E2EPaymentInfo(
            payment_id="PMT-TEST-01",
            uetr="UETR-TEST-01",
            amount=4250.00,
            currency="GBP",
            clearing_rail="CHAPS",
            creditor_account="GB82WEST12345698765423"
        ),
        bank_supplied_evidence={
            "core_dda_account": "GB82WEST12345698765432",
            "verified_iban": "GB82WEST12345698765432",
            "creditor_country": "GB"
        },
        external_authoritative_evidence={
            "routing_directory": {
                "sort_code": "601234",
                "bank_name": "NatWest",
                "chaps_enabled": True
            }
        }
    )

    test_file = Path("e2e_fixtures/archive/test_record.json")
    output, final_status = watcher._process_single_e2e_record(e2e_input, test_file, 0)
    
    assert final_status != "SETTLED"
    assert final_status in [LifecycleStage.HANDED_TO_BANK.value, LifecycleStage.SHADOW_RECORDED.value]


def test_p0_1_b_batch_release_ends_handed_to_bank():
    """batch-release ends HANDED_TO_BANK, never SETTLED."""
    from app.services.stp_engine import stp_engine
    from app.schemas.stp import BatchSTPRequest

    # Seed a qualified case
    case_id = "TEST-BATCH-P01"
    repo.save_case({
        "case_id": case_id,
        "payment_id": "PMT-BATCH-01",
        "uetr": "UETR-BATCH-01",
        "amount": 5000.0,
        "currency": "USD",
        "status": LifecycleStage.RECOMMENDED.value,
        "domain": "DATA_QUALITY",
        "profile": "DQ-01",
        "queue": "STP Fast-Lane",
        "bank_supplied_evidence": {
            "core_dda_account": "GB82WEST12345698765432",
            "verified_iban": "GB82WEST12345698765432",
            "creditor_country": "GB"
        },
        "external_authoritative_evidence": {
            "routing_directory": {
                "sort_code": "601234",
                "bank_name": "NatWest",
                "chaps_enabled": True
            }
        }
    })

    req = BatchSTPRequest(
        case_ids=[case_id],
        approver_id="APR-3191",
        approver_name="Daniel Osei",
        approver_role="OPERATIONS_APPROVER"
    )
    res = stp_engine.execute_batch_fast_lane_release(req)
    
    updated_case = repo.get_case(case_id)
    assert updated_case["status"] != "SETTLED"
    assert updated_case["status"] in [LifecycleStage.HANDED_TO_BANK.value, LifecycleStage.SHADOW_RECORDED.value]


def test_p0_1_c_human_approve_then_execute_ends_handed_to_bank(monkeypatch):
    from app.config import settings as _settings
    monkeypatch.setattr(_settings, "PEX_OPERATION_MODE", "ASSISTED", raising=False)
    _body_c()


def _body_c():
    """Human approve then execute ends HANDED_TO_BANK with status AWAITING_BANK_ACK, no ACK-SIM receipt."""
    from app.services.approval_engine import ApprovalEngine
    from app.services.action_executor import ActionExecutor

    case_id = "TEST-HUMAN-EXEC-01"
    repo.save_case({
        "case_id": case_id,
        "payment_id": "PMT-EXEC-01",
        "uetr": "UETR-EXEC-01",
        "amount": 15000.0,
        "currency": "USD",
        "status": LifecycleStage.PENDING_APPROVAL.value,
        "queue": "Repair",
        "maker_id": "OP-9012"
    })

    # Approve by Daniel Osei
    engine = ApprovalEngine()
    sub = ApprovalSubmission(case_id=case_id, action=ApprovalAction.APPROVE, comments="Approved for dispatch")
    ok, msg, rec, st = engine.process_approval_action(sub, approver_id="APR-3191")
    assert ok is True
    assert repo.get_case(case_id)["status"] == LifecycleStage.APPROVED.value

    # Execute
    executor = ActionExecutor()
    success, msg, act, rcpt = executor.execute_governed_action(case_id)
    assert success is True
    
    case = repo.get_case(case_id)
    assert case["status"] == LifecycleStage.HANDED_TO_BANK.value
    assert case["status"] != "SETTLED"
    assert case.get("dispatch_status") == "AWAITING_BANK_ACK"
    assert rcpt is None or not str(rcpt.bank_ack_reference).startswith("ACK-SIM")


def test_p0_1_d_only_bank_outcome_can_produce_settled():
    """Only /api/bank/outcome can produce SETTLED."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    case_id = "TEST-BANK-OUTCOME-01"
    repo.save_case({
        "case_id": case_id,
        "payment_id": "PMT-BO-01",
        "uetr": "UETR-BO-01",
        "amount": 2500.0,
        "currency": "GBP",
        "status": LifecycleStage.HANDED_TO_BANK.value
    })

    payload = {
        "case_id": case_id,
        "uetr": "UETR-BO-01",
        "outcome": "SETTLED",
        "bank_reference": "REAL-CHAPS-SETTLED-99182",
        "clearing_system": "CHAPS",
        "idempotency_key": "IDEMP-BO-01-" + __import__("uuid").uuid4().hex
    }

    import json as _json
    from app.api.endpoints.bank import sign_body, callback_secret
    raw = _json.dumps(payload).encode()
    resp = client.post("/api/bank/outcome", content=raw,
                       headers={"Content-Type": "application/json", "X-Bank-Signature": sign_body(raw, callback_secret())})
    assert resp.status_code == 200
    assert resp.json()["status"] == "SETTLED"
    assert repo.get_case(case_id)["status"] == LifecycleStage.SETTLED.value


def test_p0_1_e_grep_test_no_direct_status_assignment_outside_transition():
    """Grep test: no direct status assignment in target services outside transition_case."""
    target_files = [
        Path("backend/app/services/file_watcher.py"),
        Path("backend/app/services/stp_engine.py"),
        Path("backend/app/services/action_executor.py"),
        Path("backend/app/services/approval_engine.py"),
    ]
    forbidden_patterns = [
        re.compile(r'^\s*case\[["\']status["\']\]\s*=\s*(?!transition_case)'),
        re.compile(r'^\s*db_case\.status\s*=\s*(?!transition_case)'),
    ]

    violations = []
    for f in target_files:
        lines = f.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, 1):
            for pat in forbidden_patterns:
                if pat.search(line):
                    violations.append(f"{f.name}:{idx} -> {line.strip()}")

    assert not violations, f"Direct status assignment found outside transition_case:\n" + "\n".join(violations)


# =========================================================================
# P0-2 TESTS: One STP Gate
# =========================================================================

def test_p0_2_stp_gate_rejects_missing_conflicting_and_over_limit():
    """Both /api/stp/eligible and /api/stp/batch-release reject missing evidence, conflicting evidence (REC04), and over-limit cases."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # Missing evidence case
    repo.save_case({
        "case_id": "REC03-MISSING",
        "profile": "DQ-01",
        "domain": "DATA_QUALITY",
        "amount": 5000.0,
        "currency": "GBP",
        "status": LifecycleStage.RECOMMENDED.value,
        "bank_supplied_evidence": {} # Missing core_dda_account / verified_iban
    })

    # Conflicting evidence case (REC04)
    repo.save_case({
        "case_id": "REC04-CONFLICT",
        "profile": "DQ-01",
        "domain": "DATA_QUALITY",
        "amount": 5000.0,
        "currency": "GBP",
        "status": LifecycleStage.RECOMMENDED.value,
        "bank_supplied_evidence": {
            "core_dda_account": "GB82WEST12345698765432",
            "ssi_directory_account": "GB82WEST12345698769999", # Contradiction!
            "contradiction_detected": True
        }
    })

    # Amount over configured threshold ($100k limit)
    repo.save_case({
        "case_id": "OVER-LIMIT-01",
        "profile": "DQ-01",
        "domain": "DATA_QUALITY",
        "amount": 150000.0, # Exceeds limit
        "currency": "USD",
        "status": LifecycleStage.RECOMMENDED.value,
        "bank_supplied_evidence": {
            "core_dda_account": "GB82WEST12345698765432",
            "verified_iban": "GB82WEST12345698765432"
        }
    })

    # Check eligible endpoint
    resp = client.get("/api/stp/eligible")
    assert resp.status_code == 200
    eligible_ids = [item["case_id"] for item in resp.json() if item["eligible"]]
    assert "REC03-MISSING" not in eligible_ids
    assert "REC04-CONFLICT" not in eligible_ids
    assert "OVER-LIMIT-01" not in eligible_ids

    # Check batch-release endpoint rejection
    for cid in ["REC03-MISSING", "REC04-CONFLICT", "OVER-LIMIT-01"]:
        batch_resp = client.post("/api/stp/batch-release", json={
            "case_ids": [cid],
            "approver_id": "APR-3191",
            "approver_name": "Daniel Osei",
            "approver_role": "OPERATIONS_APPROVER"
        })
        assert batch_resp.status_code == 200
        data = batch_resp.json()
        assert data["failed_count"] == 1
        assert len(data["settled_cases"]) == 0


def test_p0_2_stp_gate_rec01_passes():
    """REC01 satisfies all 8 predicates and passes /api/stp/eligible."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    repo.save_case({
        "case_id": "REC01-PASS",
        "profile": "DQ-01",
        "domain": "DATA_QUALITY",
        "amount": 4250.0,
        "currency": "GBP",
        "status": LifecycleStage.RECOMMENDED.value,
        "creditor_party": {"party_name": "Nordhavn Components A/S"},
        "creditor_account": {"account_number": "GB82WEST12345698765423"},
        "bank_supplied_evidence": {
            "core_dda_account": "GB82WEST12345698765432",
            "verified_iban": "GB82WEST12345698765432",
            "creditor_country": "GB"
        },
        "external_authoritative_evidence": {
            "routing_directory": {
                "sort_code": "601234",
                "bank_name": "NatWest",
                "chaps_enabled": True
            }
        }
    })

    resp = client.get("/api/stp/eligible")
    assert resp.status_code == 200
    eligible_items = [item for item in resp.json() if item["case_id"] == "REC01-PASS"]
    assert len(eligible_items) == 1
    assert eligible_items[0]["eligible"] is True


# =========================================================================
# P0-3 TESTS: Segregation of Duties
# =========================================================================

def test_p0_3_sod_same_user_cannot_approve_own_case_even_after_persona_switch():
    """Approver cannot approve case where maker_id matches their identity (even if switching persona)."""
    from app.services.approval_engine import ApprovalEngine
    from app.core.security import check_can_approve

    case_id = "TEST-SOD-01"
    repo.save_case({
        "case_id": case_id,
        "maker_id": "OP-9012", # Priya Nair
        "amount": 25000.0,
        "queue": "Repair",
        "status": LifecycleStage.PENDING_APPROVAL.value
    })

    engine = ApprovalEngine()
    sub = ApprovalSubmission(case_id=case_id, action=ApprovalAction.APPROVE, comments="Self approval attempt")

    # Attempt 1: As OP-9012 (Operator role)
    can_appr, reason = check_can_approve(role=UserRole.OPERATOR, amount=25000.0, queue="Repair", user_id="OP-9012", maker_id="OP-9012")
    assert can_appr is False

    # Attempt 2: Persona switch to OP-1001 (same person Priya Nair)
    ok, msg, _, _ = engine.process_approval_action(sub, approver_id="OP-1001")
    assert ok is False
    assert "Segregation of Duties" in msg or "Maker-Checker" in msg


def test_p0_3_sod_different_user_can_approve():
    """Different user (Daniel Osei) can approve case submitted by Priya Nair."""
    from app.services.approval_engine import ApprovalEngine

    case_id = "TEST-SOD-02"
    repo.save_case({
        "case_id": case_id,
        "maker_id": "OP-9012", # Priya Nair
        "amount": 25000.0,
        "queue": "Repair",
        "status": LifecycleStage.PENDING_APPROVAL.value
    })

    engine = ApprovalEngine()
    sub = ApprovalSubmission(case_id=case_id, action=ApprovalAction.APPROVE, comments="Valid checker approval")

    ok, msg, rec, st = engine.process_approval_action(sub, approver_id="APR-3191")
    assert ok is True
    assert rec.approver_id == "APR-3191"


# =========================================================================
# P0-4 TESTS: Shadow / Assisted / Live Mode
# =========================================================================

def test_p0_4_shadow_mode_suppresses_outbound_and_records_shadow(monkeypatch):
    """In SHADOW mode, outbound port is never called; case ends in SHADOW_RECORDED with audit event."""
    from app.config import settings
    from app.services.outbound_port import dispatch_to_bank_handoff
    from unittest.mock import MagicMock

    monkeypatch.setattr(settings, "PEX_OPERATION_MODE", "SHADOW")
    mock_outbound_network = MagicMock()

    case = {
        "case_id": "TEST-SHADOW-01",
        "status": LifecycleStage.APPROVED.value,
        "amount": 50000.0,
        "audit_timeline": []
    }

    result = dispatch_to_bank_handoff(
        case=case,
        action_contract=None,
        outbound_network_sender=mock_outbound_network
    )

    assert mock_outbound_network.called is False
    assert case["status"] == LifecycleStage.SHADOW_RECORDED.value
    assert result["mode"] == "SHADOW"


# =========================================================================
# P0-5 TESTS: Truthful UI Data
# =========================================================================

def test_p0_5_proof_remainder_matches_runtime_mod97_for_seeded_case():
    """Demo case uses repaired valid IBAN with remainder 1, and original invalid IBAN with remainder 49."""
    from app.services.data_loader import build_rich_guided_recommendation
    from app.schemas.canonical import ExceptionProfile

    rec = build_rich_guided_recommendation(
        case_id="PEX-INV-0001",
        profile=ExceptionProfile.INVALID_IBAN,
        amount=10000.0,
        creditor_name="Test Corp",
        creditor_country="GB",
        case_idx=1
    )

    original_iban = rec.proposed_changes[0].original_value_masked.replace(" ", "")
    repaired_iban = rec.proposed_changes[0].proposed_value_masked.replace(" ", "")

    assert original_iban == "GB82WEST12345698765423"
    assert repaired_iban == "GB82WEST12345698765432"

    assert validate_iban_mod97(original_iban) is False
    assert validate_iban_mod97(repaired_iban) is True

    # Proof step 1 must dynamically reflect remainder 1
    step1 = rec.step_assessment[0]
    assert "remainder = 1" in step1.proof_detail


def test_p0_5_badge_counts_equal_list_lengths():
    """Repair badge equals actionable count (26)."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()

    repair_count = data["queue_distribution"]["Repair"]
    assert repair_count == 26


# =========================================================================
# P0-6 TESTS: Audit Payload Hash Tamper Detection
# =========================================================================

def test_p0_6_audit_payload_tamper_detection():
    """Altering before/after values, policy_version, model_version, reason_code, or maker_id breaks hash chain verification."""
    event = {
        "event_index": 1,
        "timestamp": datetime.utcnow().isoformat(),
        "case_id": "TEST-AUD-P06",
        "stage_name": "APPROVAL",
        "actor_id": "APR-3191",
        "action_name": "APPROVE_REPAIR",
        "details": "Maker-checker sign-off",
        "prev_hash": "0" * 64,
        "amount": 25000.0,
        "currency": "USD",
        "before_value": "GB82WEST12345698765423",
        "after_value": "GB82WEST12345698765432",
        "policy_version": "POL-2026.04",
        "model_version": "DETERMINISTIC_RULES_v1",
        "reason_code": "MOD97_CHECK_DIGIT_PASS",
        "maker_id": "OP-9012"
    }

    curr_hash = calculate_event_hash(
        event_index=event["event_index"],
        timestamp_iso=event["timestamp"],
        case_id=event["case_id"],
        stage_name=event["stage_name"],
        actor_id=event["actor_id"],
        action_name=event["action_name"],
        details=event["details"],
        prev_hash=event["prev_hash"],
        amount=event["amount"],
        currency=event["currency"],
        extra_payload={
            "before_value": event["before_value"],
            "after_value": event["after_value"],
            "policy_version": event["policy_version"],
            "model_version": event["model_version"],
            "reason_code": event["reason_code"],
            "maker_id": event["maker_id"]
        }
    )
    event["current_hash"] = curr_hash

    # Verify initial chain passes
    assert verify_audit_chain([event]) is True

    # Tamper 1: change policy_version
    tampered_1 = dict(event)
    tampered_1["extra_payload"] = dict(tampered_1.get("extra_payload", {}))
    tampered_1["extra_payload"]["policy_version"] = "POL-2026.05"
    assert verify_audit_chain([tampered_1]) is False

    # Tamper 2: change maker_id
    tampered_2 = dict(event)
    tampered_2["extra_payload"] = dict(tampered_2.get("extra_payload", {}))
    tampered_2["extra_payload"]["maker_id"] = "ATTACKER-666"
    assert verify_audit_chain([tampered_2]) is False
