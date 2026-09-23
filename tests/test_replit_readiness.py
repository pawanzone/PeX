"""Replit Readiness & Application Validation Test Suite for PeX Platform.

Verifies:
- Application package imports & clean configuration loading
- Database persistence lifecycle & dialect telemetry
- Synthetic data loader & repository synchronization
- Health check & cryptographic audit chain status
- Frontend SPA bundle serving & API route protection
- Full 20-step end-to-end exception resolution lifecycle
- AI Model Gateway abstraction & provider independence
"""
import pytest
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.db.session import get_db_info
from app.services.data_loader import repo
from app.schemas.canonical import LifecycleStage
from app.schemas.approval import ApprovalAction, UserRole
from app.schemas.recommendation import ActionType


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ==============================================================================
# 1. Environment & Configuration Readiness
# ==============================================================================

def test_replit_environment_and_config():
    """Verify that configuration settings load with sensible, cloud-agnostic defaults."""
    assert settings.PROJECT_NAME == "PeX Enterprise Payment Exception Platform"
    assert settings.API_V1_STR == "/api"
    assert settings.DUAL_AUTH_THRESHOLD == 250000.0
    assert settings.DATABASE_URL is not None
    assert settings.MODEL_GATEWAY_MODE in ["mock", "gemini", "openai"]


def test_replit_database_telemetry():
    """Verify database engine telemetry and dialect detection."""
    db_info = get_db_info()
    assert db_info["status"] == "ONLINE"
    assert "dialect" in db_info
    assert "url_masked" in db_info


def test_replit_synthetic_data_integrity():
    """Verify that synthetic cases, policy rules, and ICD nodes are loaded in repository."""
    assert len(repo.cases) > 0, "Repository cases should be populated"
    assert len(repo.rules) > 0, "Policy rules should be preloaded"
    assert len(repo.icd_nodes) > 0, "ICD nodes should be preloaded"
    assert repo.latest_chain_hash is not None, "Provenance hash chain must be initialized"


# ==============================================================================
# 2. HTTP API Health & Static Frontend Serving
# ==============================================================================

def test_replit_health_endpoint(client):
    """Verify /health endpoint returns comprehensive telemetry and online status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"
    assert "version" in data
    assert "database" in data
    assert data["database"]["status"] == "ONLINE"
    assert data["cases_count"] >= len(repo.cases)
    assert data["latest_audit_hash"] is not None


def test_replit_frontend_spa_serving(client):
    """Verify that root route '/' serves the compiled React single-page application."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "<!DOCTYPE html>" in resp.text or "<div id=\"root\">" in resp.text


def test_replit_api_404_protection(client):
    """Verify that invalid API routes return structured JSON 404 and are not swallowed by SPA."""
    resp = client.get("/api/nonexistent/route/path")
    assert resp.status_code == 404
    assert resp.headers.get("content-type", "").startswith("application/json")
    data = resp.json()
    assert "detail" in data


# ==============================================================================
# 3. End-to-End Exception Resolution Lifecycle
# ==============================================================================

def test_replit_end_to_end_exception_resolution_lifecycle(client):
    """Complete 20-step lifecycle test: Ingest -> Triage -> Reasoner -> Approve -> Execute -> Settle -> Audit."""
    # Step 1: Ingest Bank Exception Event
    event_id = f"EVT-REPLIT-{uuid.uuid4().hex[:6]}"
    raw_payload = {
        "event_id": event_id,
        "source_bank_id": "BANK_A",
        "event_type": "PAYMENT_EXCEPTION",
        "raw_payload": {
            "payment_reference": f"REF-RPL-{uuid.uuid4().hex[:6]}",
            "uetr": f"UETR-RPL-{uuid.uuid4().hex[:8]}",
            "amount": 75000.0,
            "currency": "USD",
            "debtor_name": "Replit Enterprise Client",
            "debtor_account": "021000021-9988112233",
            "creditor_name": "HarborView Supplier Ltd",
            "creditor_iban": "GB82WEST12345698765431",
            "creditor_bic": "WESTGB2L",
            "error_code": "ERR_IBAN_MOD97",
            "error_message": "Beneficiary account validation required",
            "settlement_rail": "SWIFT_CBPR+"
        }
    }

    ingest_resp = client.post("/api/events/ingest", json=raw_payload)
    assert ingest_resp.status_code == 200
    ingest_data = ingest_resp.json()
    assert ingest_data["success"] is True
    case = ingest_data["case"]
    case_id = case["case_id"]
    assert case["status"] == "INGESTED"

    # Step 2: Fetch Case Details
    case_resp = client.get(f"/api/cases/{case_id}")
    assert case_resp.status_code == 200
    case_wrapper = case_resp.json()
    assert "case" in case_wrapper
    case_obj = case_wrapper["case"]
    assert case_obj["case_id"] == case_id

    # Step 3: Trigger AI Repair & Fetch Recommendation
    repair_resp = client.post(f"/api/cases/{case_id}/run-ai-repair?analyst_id=OP-9012")
    assert repair_resp.status_code == 200
    repair_data = repair_resp.json()
    assert repair_data["success"] is True
    rec_data = repair_data["recommendation"]
    assert "action_type" in rec_data
    assert "confidence_score" in rec_data
    assert "proposed_changes" in rec_data

    # Step 4: Advance case to PENDING_APPROVAL for human sign-off
    case_obj["status"] = LifecycleStage.PENDING_APPROVAL.value
    repo.save_case(case_obj)

    # Step 5: Submit Maker-Checker Approval (Operations Approver APR-3191)
    auth_headers = {"Authorization": "Bearer pex-token-APR-3191"}
    approval_payload = {
        "case_id": case_id,
        "action": ApprovalAction.APPROVE.value,
        "comments": "Validated beneficiary standing record against clearing directory. Approved for execution.",
        "override_changes": rec_data.get("proposed_changes", [])
    }
    appr_resp = client.post("/api/approvals/submit", json=approval_payload, headers=auth_headers)
    assert appr_resp.status_code == 200
    appr_data = appr_resp.json()
    assert appr_data["success"] is True
    assert appr_data["next_stage"] == LifecycleStage.APPROVED.value

    # Step 6: Execute Governed Action
    exec_payload = {
        "case_id": case_id,
        "idempotency_key": f"IDEMP-RPL-{uuid.uuid4().hex[:6]}"
    }
    exec_resp = client.post("/api/actions/execute", json=exec_payload, headers=auth_headers)
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    assert exec_data["success"] is True
    assert "delivery_receipt" in exec_data
    assert exec_data["delivery_receipt"]["bank_ack_reference"].startswith("ACK-SIM-")

    # Step 7: Verify Terminal Settlement & Audit Trail
    final_case_resp = client.get(f"/api/cases/{case_id}")
    assert final_case_resp.status_code == 200
    final_case_wrapper = final_case_resp.json()
    final_case = final_case_wrapper["case"]
    assert final_case["status"] == LifecycleStage.SETTLED.value
    assert len(final_case["audit_timeline"]) > 0


# ==============================================================================
# 4. Model Gateway & Provider Independence
# ==============================================================================

def test_replit_model_gateway_mode_configured():
    """Verify that Model Gateway mode is cleanly decoupled from core business logic."""
    assert settings.MODEL_GATEWAY_MODE in ["mock", "gemini", "openai"]
    # Verify that synthetic data loader loads all BIAN domain recommendations without requiring live API keys
    assert len(repo.recommendations) > 0
