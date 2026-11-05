"""Targeted E2E Tests for PeX Inbound File Watcher Service.

Verifies:
1. Detection of new completed input files.
2. Successful ingestion through the actual existing pipeline.
3. Exactly one case created for a single file.
4. Duplicate-content handling via content-hash idempotency.
5. Malformed JSON and schema validation failures handled visibly.
6. Safe restart behavior without re-processing or duplicate cases.
7. Watcher lifecycle and error handling.
8. PII tokenization and cryptographic audit trail integrity.
"""
import os
import time
import json
import uuid
from pathlib import Path
import pytest

from app.services.file_watcher import FileWatcherService, PROFILE_CODE_TO_ENUM
from app.services.data_loader import repo
from app.services.audit_service import audit_service
from app.core.tokenization import token_vault
from app.schemas.contracts.e2e_schemas import CanonicalE2EInput, E2EPaymentInfo


def _build_sample_dq01_payload(
    exception_id: str,
    uetr: str = "UETR-WATCH-TEST-0001",
    amount: float = 4250.0,
    currency: str = "GBP"
) -> dict:
    """Helper to build a valid CanonicalE2EInput dictionary for DQ-01."""
    return {
        "exception_id": exception_id,
        "tenant_id": "DEFAULT_BANK",
        "profile_id": "DQ-01",
        "domain": "DATA_QUALITY",
        "error_code": "ERR_INVALID_IBAN_CHECKSUM",
        "error_message": "Creditor IBAN MOD-97 check digit failure on pacs.008 inbound clearing message.",
        "payment_info": {
            "payment_id": f"PMT-{exception_id}",
            "uetr": uetr,
            "amount": amount,
            "currency": currency,
            "clearing_rail": "CHAPS",
            "value_date": "2026-10-15",
            "debtor_name": "Apex Global Treasury (US)",
            "debtor_account": "US11APEX9988770100",
            "debtor_agent_bic": "CHASUS33XXX",
            "creditor_name": "Nordhavn Components A/S",
            "creditor_account": "GB29MIDL40051512345678", # Invalid check digit
            "creditor_agent_bic": "BARCGB22XXX",
            "remittance_info": f"INV-WATCH-{exception_id}"
        },
        "bank_supplied_evidence": {
            "core_dda_account": "GB29MIDL40051512345679", # Valid verified check digit
            "verified_iban": "GB29MIDL40051512345679",
            "creditor_country": "GB"
        },
        "external_authoritative_evidence": {
            "routing_directory": {
                "sort_code": "400515",
                "bank_name": "HSBC Bank UK PLC",
                "chaps_enabled": True
            }
        },
        "derived_evidence": {
            "mod97_calculated_checksum": "29",
            "inbound_transposition_detected": True
        },
        "historical_evidence": {
            "historical_match_count": 14,
            "confidence_heuristic": 0.98
        },
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    }


def test_watcher_lifecycle(tmp_path):
    """Test start, stop, is_running, and telemetry status of FileWatcherService."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    assert not watcher.is_running()
    status_before = watcher.get_status()
    assert status_before["is_running"] is False
    assert status_before["input_dir"] == str(in_dir)

    watcher.start(initial_scan_baseline=False)
    assert watcher.is_running()
    assert in_dir.exists()
    assert out_dir.exists()

    status_running = watcher.get_status()
    assert status_running["is_running"] is True

    watcher.stop()
    assert not watcher.is_running()
    status_stopped = watcher.get_status()
    assert status_stopped["is_running"] is False


def test_new_file_detection_and_pipeline_execution(tmp_path):
    """Test detection, schema validation, ingestion, reasoning, and database persistence."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    case_id = f"TEST-WATCH-DQ01-{uuid.uuid4().hex[:6].upper()}"
    payload = _build_sample_dq01_payload(exception_id=case_id)
    test_file = in_dir / "dq01_sample.json"
    test_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    results = watcher.scan_once()
    assert len(results) == 1
    assert results[0]["exception_id"] == case_id
    assert results[0]["status"] == "PROCESSED"
    assert results[0]["stp_eligible"] is True

    # Verify output file generated
    expected_out = out_dir / "dq01_sample.output.json"
    assert expected_out.exists()
    out_data = json.loads(expected_out.read_text(encoding="utf-8"))
    assert out_data["exception_id"] == case_id
    assert out_data["stp_eligible"] is True
    assert out_data["execution_owner"] == "BANK"
    assert len(out_data["repaired_fields"]) > 0
    assert out_data["repaired_fields"][0]["repaired_value"] == "GB29MIDL40051512345679"

    # Verify database persistence
    case_db = repo.get_case(case_id)
    assert case_db is not None
    assert case_db["case_id"] == case_id
    assert case_db["status"] == "SHADOW_RECORDED"  # default mode is SHADOW: recorded, nothing sent
    assert case_db["queue"] == "STP Fast-Lane"
    assert case_db["amount"] == 4250.0
    assert case_db["currency"] == "GBP"
    assert case_db["settled_at"] is None  # PeX never settles; the bank does

    # Verify recommendation saved
    rec_db = repo.get_recommendation(case_id)
    assert rec_db is not None
    assert rec_db.case_id == case_id

    # Verify audit chain integrity
    verify_res = audit_service.verify_chain()
    assert verify_res.is_intact is True


def test_exactly_one_case_created_single_file(tmp_path):
    """Ensure that repeated scans over the same file do not produce duplicate cases."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    case_id = f"TEST-WATCH-SINGLE-{uuid.uuid4().hex[:6].upper()}"
    payload = _build_sample_dq01_payload(exception_id=case_id)
    (in_dir / "single_case.json").write_text(json.dumps(payload), encoding="utf-8")

    initial_case_count = len(repo.cases)

    # First scan: processes file
    r1 = watcher.scan_once()
    assert len(r1) == 1
    assert r1[0]["status"] == "PROCESSED"
    assert len(repo.cases) == initial_case_count + 1

    # Second scan: file already processed, skipped
    r2 = watcher.scan_once()
    assert len(r2) == 0
    assert len(repo.cases) == initial_case_count + 1

    # Third scan: still no duplicate
    r3 = watcher.scan_once()
    assert len(r3) == 0
    assert len(repo.cases) == initial_case_count + 1


def test_duplicate_content_handling(tmp_path):
    """Ensure that dropping a second file with identical content does not duplicate cases."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    case_id = f"TEST-WATCH-DUP-{uuid.uuid4().hex[:6].upper()}"
    content = json.dumps(_build_sample_dq01_payload(exception_id=case_id))

    # File 1: original
    (in_dir / "original.json").write_text(content, encoding="utf-8")
    r1 = watcher.scan_once()
    assert len(r1) == 1
    assert r1[0]["status"] == "PROCESSED"

    count_after_first = len(repo.cases)

    # File 2: duplicate content with different name
    (in_dir / "copy_of_original.json").write_text(content, encoding="utf-8")
    r2 = watcher.scan_once()
    assert len(r2) == 0
    assert len(repo.cases) == count_after_first


def test_malformed_json_failure_handled_visibly(tmp_path):
    """Ensure malformed JSON syntax is caught visibly, logged to audit, and does not crash watcher."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    bad_file = in_dir / "bad_syntax.json"
    bad_file.write_text("{\n  \"exception_id\": \"BROKEN\",\n  invalid_json\n", encoding="utf-8")

    # Fast forward mtime so _is_file_ready recognizes it as fully written
    past = time.time() - 5.0
    os.utime(str(bad_file), (past, past))

    r = watcher.scan_once()
    assert len(r) == 1
    assert r[0]["status"] == "FAILED"
    assert "Malformed JSON" in r[0]["error"]
    assert "bad_syntax.json" in watcher._failed_files

    # Subsequent scan should not re-attempt or spin on the file
    r2 = watcher.scan_once()
    assert len(r2) == 0


def test_schema_validation_failure_handled_visibly(tmp_path):
    """Ensure files failing CanonicalE2EInput schema validation are recorded visibly in audit."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    invalid_schema_file = in_dir / "invalid_schema.json"
    invalid_schema_file.write_text(json.dumps({"some_random_field": "no payment info here"}), encoding="utf-8")

    r = watcher.scan_once()
    assert len(r) == 1
    assert r[0]["status"] == "FAILED"
    assert "Schema validation error" in r[0]["error"]
    assert "invalid_schema.json" in watcher._failed_files


def test_safe_restart_behavior(tmp_path):
    """Ensure that restarting the watcher service on existing files avoids re-processing."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    case_id = f"TEST-WATCH-RESTART-{uuid.uuid4().hex[:6].upper()}"
    payload = _build_sample_dq01_payload(exception_id=case_id)
    (in_dir / "restart_case.json").write_text(json.dumps(payload), encoding="utf-8")

    # Instance 1 processes the file via single pass
    w1 = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)
    r1 = w1.scan_once()
    assert len(r1) == 1
    assert repo.get_case(case_id) is not None

    count_after_w1 = len(repo.cases)

    # Instance 2 simulates application restart: baselines existing directory on startup
    w2 = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)
    w2._baseline_existing_files()
    r2 = w2.scan_once()
    assert len(r2) == 0
    assert len(repo.cases) == count_after_w1



def test_tokenization_and_audit_behavior(tmp_path):
    """Verify that debtor/creditor PII is tokenized and audit chain remains cryptographically valid."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    case_id = f"TEST-WATCH-TOKEN-{uuid.uuid4().hex[:6].upper()}"
    payload = _build_sample_dq01_payload(exception_id=case_id)
    payload["payment_info"]["debtor_name"] = "Classified Defense Contractor"
    payload["payment_info"]["creditor_name"] = "Top Secret Avionics Inc"

    (in_dir / "token_case.json").write_text(json.dumps(payload), encoding="utf-8")
    results = watcher.scan_once()
    assert len(results) == 1

    case_db = repo.get_case(case_id)
    assert case_db is not None
    # Check that token references were generated in vault
    debtor_tok = case_db["debtor_party"]["token_ref"]
    creditor_tok = case_db["creditor_party"]["token_ref"]
    assert debtor_tok is not None
    assert creditor_tok is not None

    # Check token vault mapping
    assert token_vault.detokenize(debtor_tok) == "CLASSIFIEDDEFENSECONTRACTOR"
    assert token_vault.detokenize(creditor_tok) == "TOPSECRETAVIONICSINC"

    # Audit chain must be intact
    v = audit_service.verify_chain()
    assert v.is_intact is True


def test_partial_file_copy_safety(tmp_path):
    """Verify that zero-byte and currently-written files are guarded against premature reading."""
    in_dir = tmp_path / "input"
    watcher = FileWatcherService(input_dir=in_dir, output_dir=tmp_path / "out")

    # 1. Zero byte file
    empty_file = in_dir / "empty.json"
    empty_file.parent.mkdir(parents=True, exist_ok=True)
    empty_file.touch()
    assert not watcher._is_file_ready(empty_file)

    # 2. Incomplete JSON with recent modification time (< 1.5s)
    partial_file = in_dir / "partial.json"
    partial_file.write_text("{\"key\": \"val", encoding="utf-8")
    assert not watcher._is_file_ready(partial_file)

    # 3. Valid JSON completed
    valid_file = in_dir / "complete.json"
    valid_file.write_text("{\"key\": \"val\"}", encoding="utf-8")
    assert watcher._is_file_ready(valid_file)


def test_background_thread_monitoring(tmp_path):
    """Verify that the background polling thread actively detects and processes new files automatically."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.05)
    watcher.start(initial_scan_baseline=False)
    assert watcher.is_running()

    case_id = f"TEST-WATCH-BG-{uuid.uuid4().hex[:6].upper()}"
    payload = _build_sample_dq01_payload(exception_id=case_id)
    (in_dir / "bg_case.json").write_text(json.dumps(payload), encoding="utf-8")

    # Wait up to 3 seconds for background thread to process file
    output_file = out_dir / "bg_case.output.json"
    for _ in range(60):
        if output_file.exists():
            break
        time.sleep(0.05)

    assert output_file.exists(), "Background watcher failed to generate output file within 3 seconds"
    assert repo.get_case(case_id) is not None

    watcher.stop()
    assert not watcher.is_running()


def test_watcher_api_endpoints():
    """Verify GET /api/events/watcher/status, POST /api/events/watcher/scan, and /health telemetry."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 1. Health check includes file_watcher
    res_health = client.get("/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert "file_watcher" in data_health
    assert "input_dir" in data_health["file_watcher"]

    # 2. Watcher status endpoint
    res_status = client.get("/api/events/watcher/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert "input_dir" in data_status
    assert "processed_hashes_count" in data_status

    # 3. Manual scan trigger endpoint
    res_scan = client.post("/api/events/watcher/scan")
    assert res_scan.status_code == 200
    data_scan = res_scan.json()
    assert data_scan["success"] is True
    assert "files_processed" in data_scan
