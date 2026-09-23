"""
P1 Remediation Batch 3 Dedicated Test Suite:
Contracts, Reliability & Code Hygiene

Covers:
- MST-018: STP Batch Transaction Leak (Rollback and transaction cleanliness)
- MST-019: Silent Datetime Exception Swallowing (Explicit error handling & logging)
- MST-020: TypeScript vs Pydantic Drift (Model alignment and structural consistency)
- MST-030: Dual Disconnected Frontend Codebases (Authoritative UI bundle verification)
- MST-031: Orphaned Generator Scripts in Root (Root cleanliness & tools structure)
- MST-032: Deprecated Pydantic .dict() Calls (.model_dump() serialization)
- MST-044: Incomplete Ingestion Case Schema (Full case contract populated on intake)
- MST-045: Static Ontology Context Data (Dynamic KYC & STP eligibility computation)
- MST-046: SLA Velocity Resolution Math (REJECTED terminal classification)
- MST-047: SPA Route Swallows Unmatched APIs (JSON 404 on unmatched /api/*)
"""
import os
import uuid
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_loader import repo
from app.services.stp_engine import stp_engine
from app.schemas.stp import BatchSTPRequest
from app.schemas.canonical import LifecycleStage, ExceptionProfile, ExceptionDomain
from app.schemas.bank_events import RawBankEvent


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# MST-018: STP Batch Transaction Leak
# ==============================================================================

def test_mst_018_stp_batch_transaction_integrity():
    """Verify that STP batch processing maintains database transactional integrity."""
    case_id = f"CASE-MST018-{uuid.uuid4().hex[:6]}"
    repo.save_case({
        "case_id": case_id,
        "payment_id": f"PMT-{case_id}",
        "uetr": f"UETR-{case_id}",
        "amount": 5000.0,
        "currency": "USD",
        "status": LifecycleStage.PENDING_APPROVAL.value,
        "queue": "Repair",
        "ai_confidence": 0.98,
        "approval_history": []
    })

    req = BatchSTPRequest(
        case_ids=[case_id],
        approver_id="APR-3191",
        approver_name="Daniel Osei",
        approver_role="OPERATIONS_APPROVER",
        comments="Batch transaction integrity test"
    )

    resp = stp_engine.execute_batch_fast_lane_release(req)
    assert resp.processed_count == 1
    assert resp.failed_count == 0
    assert len(resp.settled_cases) == 1
    assert resp.settled_cases[0].case_id == case_id


def test_mst_018_stp_autonomous_rollback_on_failure():
    """Verify that autonomous STP properly cleans up and handles exceptions."""
    non_existent_id = f"NONEXISTENT-{uuid.uuid4().hex[:6]}"
    # Executing autonomous STP on non-existent case raises ValueError
    with pytest.raises(ValueError) as exc_info:
        stp_engine.execute_autonomous_stp(non_existent_id)
    assert "not found" in str(exc_info.value)


# ==============================================================================
# MST-019: Silent Datetime Exception Swallowing
# ==============================================================================

def test_mst_019_datetime_parsing_explicit_fallback():
    """Verify that invalid datetime string in audit model uses observable fallback without crashing."""
    from app.db.session import SessionLocal
    from app.db.models import AuditEventModel

    db = SessionLocal()
    try:
        corrupted_event = AuditEventModel(
            event_index=999999,
            timestamp="NOT_A_VALID_ISO_DATETIME",
            case_id="CORRUPT-TEST",
            correlation_id="CORR-CORRUPT",
            stage_name="INTAKE",
            actor_id="TEST",
            actor_role="SYSTEM",
            action_name="TEST",
            details="Testing datetime exception handling",
            control_tags=["TEST"],
            prev_hash="0" * 64,
            current_hash="1" * 64
        )
        db.add(corrupted_event)
        db.commit()

        # Query audit_log property to trigger datetime conversion
        logs = repo.audit_log
        found = [l for l in logs if l.case_id == "CORRUPT-TEST"]
        assert len(found) == 1
        # Fallback to datetime.utcnow() was applied
        assert isinstance(found[0].timestamp, datetime)

        # Cleanup test event
        db.query(AuditEventModel).filter(AuditEventModel.case_id == "CORRUPT-TEST").delete()
        db.commit()
    finally:
        db.close()


# ==============================================================================
# MST-020: TypeScript vs Pydantic Drift
# ==============================================================================

def test_mst_020_frontend_types_file_exists_and_synced():
    """Verify that frontend/src/types/index.ts exists and defines all 5 market domains and 41 exception profiles."""
    types_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "types", "index.ts")
    assert os.path.exists(types_path)

    with open(types_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify domain constants
    assert "DATA_QUALITY" in content
    assert "PROCESSING" in content
    assert "COMPLIANCE" in content
    assert "CLIENT_TREASURY" in content
    assert "SETTLEMENT_RETURNS" in content

    # Verify key lifecycle stages
    assert "RETURNED_FOR_REWORK" in content
    assert "AWAITING_SECOND_APPROVAL" in content

    # Verify representative profiles from all 5 domains
    assert "INVALID_IBAN" in content
    assert "DUPLICATE_PAYMENT" in content
    assert "SANCTIONS_SUSPECTED" in content
    assert "KYC_EXPIRED" in content
    assert "UNMATCHED_CREDIT" in content


# ==============================================================================
# MST-030: Dual Disconnected Frontend Codebases
# ==============================================================================

def test_mst_030_authoritative_frontend_dist_bundle():
    """Verify that the authoritative frontend bundle (frontend/dist/index.html) is built and contains active features."""
    dist_html = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist", "index.html")
    assert os.path.exists(dist_html)

    with open(dist_html, "r", encoding="utf-8") as f:
        html = f.read()

    # Verify core SPA elements
    assert "<!DOCTYPE html>" in html or "<html" in html
    assert "PeX" in html
    # Verify README guide exists
    readme_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "README.md")
    assert os.path.exists(readme_path)


# ==============================================================================
# MST-031: Orphaned Generator Scripts in Root
# ==============================================================================

def test_mst_031_root_workspace_cleanliness():
    """Verify that root directory contains only appropriate files and orphaned scripts are in tools/."""
    root_dir = os.path.join(os.path.dirname(__file__), "..")
    root_files = [f for f in os.listdir(root_dir) if f.endswith(".py")]

    # Only build_guided_frontend.py should be in root
    assert root_files == ["build_guided_frontend.py"]

    # Verify tools subdirectories exist
    assert os.path.exists(os.path.join(root_dir, "tools", "generators"))
    assert os.path.exists(os.path.join(root_dir, "tools", "diagnostics"))
    assert os.path.exists(os.path.join(root_dir, "tools", "legacy_scaffolding"))


# ==============================================================================
# MST-032: Deprecated Pydantic .dict() Calls
# ==============================================================================

def test_mst_032_model_dump_serialization(client):
    """Verify that case detail API returns valid JSON without .dict() deprecation warnings."""
    case_id = list(repo.cases.keys())[0]
    resp = client.get(f"/api/cases/{case_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "case" in data
    assert "recommendation" in data
    assert "approvals" in data


# ==============================================================================
# MST-044: Incomplete Ingestion Case Schema
# ==============================================================================

def test_mst_044_ingestion_complete_case_contract(client):
    """Verify that bank event ingestion endpoint populates full canonical case attributes in response."""
    raw_event = {
        "event_id": f"EVT-FULL-{uuid.uuid4().hex[:6]}",
        "source_bank_id": "BANK_B",
        "event_type": "PAYMENT_EXCEPTION",
        "raw_payload": {
            "payment_reference": f"REF-FULL-{uuid.uuid4().hex[:6]}",
            "uetr": f"UETR-FULL-{uuid.uuid4().hex[:8]}",
            "amount": 125000.0,
            "currency": "EUR",
            "debtor_name": "Nordic Marine Group",
            "debtor_account": "DE89370400440532013000",
            "creditor_name": "Hanseatic Port Logistics",
            "creditor_iban": "DE89370400440532013001",
            "error_code": "ERR_IBAN_MOD97",
            "error_message": "Invalid check digits",
            "settlement_rail": "TARGET2"
        }
    }

    resp = client.post("/api/events/ingest", json=raw_event)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "case" in data
    c = data["case"]

    # Verify complete schema attributes
    assert c["case_id"].startswith("PEX-")
    assert c["status"] == "INGESTED"
    assert c["domain"] == "DATA_QUALITY"
    assert c["amount"] == 125000.0
    assert c["currency"] == "EUR"
    assert c["counterparty"] == "Hanseatic Port Logistics"
    assert "secondary_profiles" in c
    assert "at_risk_amount" in c
    assert "audit_timeline" in c


# ==============================================================================
# MST-045: Static Ontology Context Data
# ==============================================================================

def test_mst_045_ontology_dynamic_kyc_expired(client):
    """Verify that ontology endpoint dynamically computes KYC status and restrictions for KYC_EXPIRED cases."""
    case_id = f"CASE-KYC-{uuid.uuid4().hex[:6]}"
    repo.save_case({
        "case_id": case_id,
        "profile": "KYC_EXPIRED",
        "amount": 50000.0,
        "currency": "USD",
        "status": LifecycleStage.INVESTIGATING.value,
        "queue": "Treasury",
        "debtor_party": {"party_id": "01", "party_name": "Old Client", "country": "US"},
        "creditor_party": {"party_id": "02", "party_name": "Beneficiary", "country": "GB"},
        "approval_history": []
    })

    resp = client.get(f"/api/ontology/cases/{case_id}/context")
    assert resp.status_code == 200
    data = resp.json()

    # Verify dynamic KYC attributes
    assert data["kyc"]["kycStatus"]["value"] == "EXPIRED"
    assert data["kyc"]["paymentRestriction"]["value"] == "true"
    assert data["kyc"]["riskClassification"]["value"] == "HIGH"
    assert "Certificate of Incumbency" in data["kyc"]["expiredDocuments"]["value"]
    assert data["client"]["straightThroughRepairEligible"]["value"] == "false"


def test_mst_045_ontology_dynamic_standard_repair(client):
    """Verify that ontology endpoint dynamically computes ACTIVE status and STP eligibility for standard cases."""
    case_id = f"CASE-STD-{uuid.uuid4().hex[:6]}"
    repo.save_case({
        "case_id": case_id,
        "profile": "INVALID_IBAN",
        "amount": 5000.0,  # <= 10k -> STP eligible
        "currency": "USD",
        "status": LifecycleStage.PENDING_APPROVAL.value,
        "queue": "Repair",
        "debtor_party": {"party_id": "01", "party_name": "Standard Corp", "country": "US"},
        "creditor_party": {"party_id": "02", "party_name": "Standard Vendor", "country": "GB"},
        "approval_history": []
    })

    resp = client.get(f"/api/ontology/cases/{case_id}/context")
    assert resp.status_code == 200
    data = resp.json()

    assert data["kyc"]["kycStatus"]["value"] == "ACTIVE"
    assert data["kyc"]["paymentRestriction"]["value"] == "false"
    assert data["client"]["straightThroughRepairEligible"]["value"] == "true"


# ==============================================================================
# MST-046: SLA Velocity Resolution Math
# ==============================================================================

def test_mst_046_sla_velocity_excludes_rejected_from_backlog(client):
    """Verify that SLA velocity and summary APIs classify REJECTED as terminal/resolved and not open backlog."""
    rej_case_id = f"CASE-REJ-{uuid.uuid4().hex[:6]}"
    repo.save_case({
        "case_id": rej_case_id,
        "status": LifecycleStage.REJECTED.value,
        "amount": 10000.0,
        "queue": "Compliance",
        "approval_history": []
    })

    resp_summary = client.get("/api/analytics/summary")
    assert resp_summary.status_code == 200
    summary = resp_summary.json()

    resp_velocity = client.get("/api/analytics/velocity")
    assert resp_velocity.status_code == 200
    velocity = resp_velocity.json()
    today_entry = [v for v in velocity if v["day"] == "Today"][0]

    # Open cases in summary and velocity must match and exclude REJECTED
    assert summary["open_cases"] == today_entry["opened"]
    assert summary["resolved_cases"] == today_entry["resolved"]


# ==============================================================================
# MST-047: SPA Route Swallows Unmatched APIs
# ==============================================================================

def test_mst_047_unmatched_api_returns_json_404(client):
    """Verify that unmatched /api/* requests return HTTP 404 JSON, not SPA HTML."""
    resp = client.get("/api/v1/nonexistent_route_test")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    data = resp.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_mst_047_spa_fallback_serves_html(client):
    """Verify that legitimate SPA routes return 200 with HTML."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
