"""Targeted E2E Tests for PeX Inbound Batch JSON File Watcher Service.

Verifies the 15 required criteria from Stage 2 specification:
1. Existing single-object JSON compatibility.
2. Multi-record envelope parsing (CanonicalE2EBatchInput).
3. A batch containing different valid records and different resolution outcomes.
4. Record-level schema validation failure while subsequent valid records continue.
5. Evidence isolation between records.
6. Multiple exceptions associated with one transaction.
7. Identical-file replay (content-hash idempotency).
8. Transaction replay across different files (case-level idempotency).
9. Duplicate identifiers within a single batch.
10. Partial processing failure and safe retry behavior.
11. File-level reconciliation counts and mathematical reconciliation.
12. Audit-chain cryptographic integrity across batch events.
13. Malformed JSON syntax error handling without fabricated records.
14. Incomplete-file safety via file-readiness guards.
15. Bank-control boundary: execution_owner == "BANK" and zero live payment execution.
"""
import os
import time
import json
import uuid
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple, Union, Set
import pytest

from app.services.file_watcher import FileWatcherService
from app.services.data_loader import repo
from app.services.audit_service import audit_service
from app.core.tokenization import token_vault
from app.schemas.contracts.e2e_schemas import (
    CanonicalE2EInput,
    CanonicalE2EBatchInput,
    BatchReconciliationReport,
)


def _build_valid_dq01_record(
    exception_id: str,
    uetr: Optional[str] = None,
    amount: float = 5000.0,
    currency: str = "GBP"
) -> dict:
    """Builds a valid DQ-01 (Transposed IBAN) record that resolves to STP."""
    uetr = uetr or f"UETR-{uuid.uuid4().hex[:12].upper()}"
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
            "value_date": "2026-10-16",
            "debtor_name": "Apex Global Treasury (US)",
            "debtor_account": "US11APEX9988770100",
            "debtor_agent_bic": "CHASUS33XXX",
            "creditor_name": "Nordhavn Components A/S",
            "creditor_account": "GB29MIDL40051512345678", # Transposed/invalid check
            "creditor_agent_bic": "BARCGB22XXX",
            "remittance_info": f"INV-{exception_id}"
        },
        "bank_supplied_evidence": {
            "core_dda_account": "GB29MIDL40051512345679", # Authoritative correct check
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
            "historical_match_count": 12,
            "confidence_heuristic": 0.97
        },
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    }


def _build_compliance_co01_record(
    exception_id: str,
    uetr: Optional[str] = None,
    amount: float = 75000.0,
    currency: str = "USD"
) -> dict:
    """Builds a Compliance (CO-01 / Sanctions) record that requires HITL review."""
    uetr = uetr or f"UETR-{uuid.uuid4().hex[:12].upper()}"
    return {
        "exception_id": exception_id,
        "tenant_id": "DEFAULT_BANK",
        "profile_id": "CO-01",
        "domain": "COMPLIANCE",
        "error_code": "ERR_OFAC_WATCHLIST_MATCH",
        "error_message": "Creditor party matched OFAC SDN Specially Designated Nationals screening list.",
        "payment_info": {
            "payment_id": f"PMT-{exception_id}",
            "uetr": uetr,
            "amount": amount,
            "currency": currency,
            "clearing_rail": "FEDWIRE",
            "value_date": "2026-10-16",
            "debtor_name": "Acme Industrial Corp",
            "debtor_account": "US22CHAS0099881122",
            "debtor_agent_bic": "CHASUS33XXX",
            "creditor_name": "Redacted SDN Entity Ltd",
            "creditor_account": "GB82WEST12345698765432",
            "creditor_agent_bic": "WESTGB2LXXX",
            "remittance_info": f"SANCTIONS-TEST-{exception_id}"
        },
        "bank_supplied_evidence": {
            "sanctions_screening_hit": True,
            "match_confidence": 0.94,
            "list_provider": "OFAC_SDN_LIST"
        },
        "external_authoritative_evidence": {
            "screening_agency": "US_TREASURY_OFAC",
            "hit_details": "Target entity designated under Executive Order 14024"
        },
        "derived_evidence": {
            "sanctions_block_recommended": True
        },
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    }


# =========================================================================
# Test 1: Existing single-object JSON compatibility
# =========================================================================
def test_01_single_object_json_compatibility(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    case_id = f"TEST-BATCH-S1-{uuid.uuid4().hex[:6].upper()}"
    single_record = _build_valid_dq01_record(exception_id=case_id)
    (in_dir / "single_file.json").write_text(json.dumps(single_record, indent=2), encoding="utf-8")

    results = watcher.scan_once()
    assert len(results) == 1
    assert results[0]["exception_id"] == case_id
    assert results[0]["status"] == "PROCESSED"
    assert (out_dir / "single_file.output.json").exists()
    assert repo.get_case(case_id) is not None


# =========================================================================
# Test 2: Multi-record envelope parsing (CanonicalE2EBatchInput)
# =========================================================================
def test_02_multi_record_envelope_parsing(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    batch_id = f"BATCH-ENV-{uuid.uuid4().hex[:6].upper()}"
    case_1 = f"CASE-ENV-1-{uuid.uuid4().hex[:6].upper()}"
    case_2 = f"CASE-ENV-2-{uuid.uuid4().hex[:6].upper()}"

    batch_payload = {
        "batch_id": batch_id,
        "source_system": "CORE_PAYMENT_HUB",
        "records": [
            _build_valid_dq01_record(exception_id=case_1),
            _build_valid_dq01_record(exception_id=case_2)
        ],
        "processing_metadata": {"test_run": "stage2_validation"}
    }
    (in_dir / "batch_envelope.json").write_text(json.dumps(batch_payload, indent=2), encoding="utf-8")

    results = watcher.scan_once()
    assert len(results) == 1
    res = results[0]
    assert res["batch_id"] == batch_id
    assert res["total_records"] == 2
    assert res["processed_count"] == 2
    assert res["failed_count"] == 0
    assert res["status"] == "PROCESSED"

    # Both individual output files must exist
    assert (out_dir / f"{case_1}.output.json").exists()
    assert (out_dir / f"{case_2}.output.json").exists()

    # Reconciliation report must exist
    recon_file = out_dir / f"{batch_id}.reconciliation.json"
    assert recon_file.exists()
    recon_data = json.loads(recon_file.read_text(encoding="utf-8"))
    assert recon_data["batch_id"] == batch_id
    assert recon_data["total_records"] == 2
    assert recon_data["processed_count"] == 2


# =========================================================================
# Test 3: Batch containing different valid records and different resolution outcomes
# =========================================================================
def test_03_batch_different_records_different_outcomes(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    batch_id = f"BATCH-DIFF-{uuid.uuid4().hex[:6].upper()}"
    case_stp = f"CASE-STP-{uuid.uuid4().hex[:6].upper()}"
    case_hitl = f"CASE-HITL-{uuid.uuid4().hex[:6].upper()}"

    batch_payload = {
        "batch_id": batch_id,
        "records": [
            _build_valid_dq01_record(exception_id=case_stp),
            _build_compliance_co01_record(exception_id=case_hitl)
        ]
    }
    (in_dir / "batch_diff.json").write_text(json.dumps(batch_payload), encoding="utf-8")

    watcher.scan_once()

    # Case 1 (DQ-01): Resolves via STP Fast-Lane. Default mode is SHADOW, so it is recorded and nothing is sent to the bank (PeX never settles).
    c1 = repo.get_case(case_stp)
    assert c1 is not None
    assert c1["status"] == "SHADOW_RECORDED"
    assert c1["queue"] == "STP Fast-Lane"

    # Case 2 (CO-01): Resolves to PENDING_APPROVAL via Compliance Queue
    c2 = repo.get_case(case_hitl)
    assert c2 is not None
    assert c2["status"] == "PENDING_APPROVAL"
    assert c2["queue"] == "Compliance"

    # Reconciliation report outcomes
    recon = json.loads((out_dir / f"{batch_id}.reconciliation.json").read_text(encoding="utf-8"))
    assert recon["outcomes_by_status"].get("SHADOW_RECORDED") == 1
    assert recon["outcomes_by_status"].get("PENDING_APPROVAL") == 1


# =========================================================================
# Test 4: Record-level schema validation failure while subsequent valid records continue
# =========================================================================
def test_04_record_level_schema_failure_subsequent_continue(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    batch_id = f"BATCH-MALREC-{uuid.uuid4().hex[:6].upper()}"
    case_good_1 = f"CASE-GOOD-1-{uuid.uuid4().hex[:6].upper()}"
    case_good_2 = f"CASE-GOOD-2-{uuid.uuid4().hex[:6].upper()}"

    malformed_record = {
        "exception_id": "MALFORMED-RECORD-001",
        "error_message": "Missing mandatory payment_info structure completely"
        # Omitted required payment_info
    }

    batch_payload = {
        "batch_id": batch_id,
        "records": [
            _build_valid_dq01_record(exception_id=case_good_1),
            malformed_record,
            _build_valid_dq01_record(exception_id=case_good_2)
        ]
    }
    (in_dir / "batch_with_malformed.json").write_text(json.dumps(batch_payload), encoding="utf-8")

    watcher.scan_once()

    # Good records must be processed and persisted
    assert repo.get_case(case_good_1) is not None
    assert repo.get_case(case_good_2) is not None
    assert (out_dir / f"{case_good_1}.output.json").exists()
    assert (out_dir / f"{case_good_2}.output.json").exists()

    # Malformed record must NOT crash the watcher or halt subsequent processing
    recon = json.loads((out_dir / f"{batch_id}.reconciliation.json").read_text(encoding="utf-8"))
    assert recon["total_records"] == 3
    assert recon["valid_records"] == 2
    assert recon["invalid_records"] == 1
    assert recon["processed_count"] == 2
    assert recon["failed_count"] == 1

    # Check malformed record disposition
    rec_disp = recon["records"][1]
    assert rec_disp["record_index"] == 1
    assert rec_disp["status"] == "FAILED_SCHEMA"
    assert "payment_info" in rec_disp["error_details"]


# =========================================================================
# Test 5: Evidence isolation between records
# =========================================================================
def test_05_evidence_isolation_between_records(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    batch_id = f"BATCH-ISO-{uuid.uuid4().hex[:6].upper()}"
    case_with_evidence = f"CASE-EVD-WITH-{uuid.uuid4().hex[:6].upper()}"
    case_without_evidence = f"CASE-EVD-WITHOUT-{uuid.uuid4().hex[:6].upper()}"

    r1 = _build_valid_dq01_record(exception_id=case_with_evidence)
    r2 = _build_valid_dq01_record(exception_id=case_without_evidence)
    # Strip authoritative evidence from Record 2
    r2["bank_supplied_evidence"] = {}
    r2["external_authoritative_evidence"] = {}

    batch_payload = {
        "batch_id": batch_id,
        "records": [r1, r2]
    }
    (in_dir / "batch_isolation.json").write_text(json.dumps(batch_payload), encoding="utf-8")

    watcher.scan_once()

    out1 = json.loads((out_dir / f"{case_with_evidence}.output.json").read_text(encoding="utf-8"))
    out2 = json.loads((out_dir / f"{case_without_evidence}.output.json").read_text(encoding="utf-8"))

    # Record 1 had sufficient evidence -> STP passed
    assert out1["stp_eligible"] is True
    assert out1["evidence_status"] == "SUFFICIENT"

    # Record 2 had NO evidence -> MUST NOT inherit Record 1's evidence -> STP failed
    assert out2["stp_eligible"] is False
    assert out2["evidence_status"] == "INSUFFICIENT"


# =========================================================================
# Test 6: Multiple exceptions associated with one transaction
# =========================================================================
def test_06_multiple_exceptions_on_one_transaction(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    case_id = f"CASE-MULTI-EXC-{uuid.uuid4().hex[:6].upper()}"
    rec = _build_valid_dq01_record(exception_id=case_id)
    rec["secondary_profile_ids"] = ["DQ-09", "CO-01"] # Compound: Invalid IBAN + Beneficiary Mismatch + Sanctions

    batch_payload = {
        "batch_id": f"BATCH-COMPOUND-{uuid.uuid4().hex[:6].upper()}",
        "records": [rec]
    }
    (in_dir / "compound.json").write_text(json.dumps(batch_payload), encoding="utf-8")

    watcher.scan_once()

    case_db = repo.get_case(case_id)
    assert case_db is not None
    assert case_db["profile"] == "DQ-01"
    assert "DQ-09" in case_db["secondary_profiles"]
    assert "CO-01" in case_db["secondary_profiles"]


# =========================================================================
# Test 7: Identical-file replay
# =========================================================================
def test_07_identical_file_replay(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    case_id = f"CASE-REPLAY-{uuid.uuid4().hex[:6].upper()}"
    batch_payload = {
        "batch_id": "BATCH-REPLAY-001",
        "records": [_build_valid_dq01_record(exception_id=case_id)]
    }
    file_path = in_dir / "replay_test.json"
    file_path.write_text(json.dumps(batch_payload), encoding="utf-8")

    initial_cases = len(repo.cases)

    # First scan: processes file
    r1 = watcher.scan_once()
    assert len(r1) == 1
    assert r1[0]["processed_count"] == 1
    assert len(repo.cases) == initial_cases + 1

    # Second scan: identical file skipped by hash
    r2 = watcher.scan_once()
    assert len(r2) == 0
    assert len(repo.cases) == initial_cases + 1


# =========================================================================
# Test 8: Transaction replay across different files
# =========================================================================
def test_08_transaction_replay_across_different_files(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    shared_case_id = f"CASE-SHARED-{uuid.uuid4().hex[:6].upper()}"
    unique_case_id = f"CASE-UNIQUE-{uuid.uuid4().hex[:6].upper()}"

    # File 1 contains shared_case_id
    file_1 = {
        "batch_id": "BATCH-FILE-1",
        "records": [_build_valid_dq01_record(exception_id=shared_case_id)]
    }
    (in_dir / "file_1.json").write_text(json.dumps(file_1), encoding="utf-8")
    watcher.scan_once()
    assert repo.get_case(shared_case_id) is not None

    cases_after_file1 = len(repo.cases)

    # File 2 contains shared_case_id AND a new unique_case_id
    file_2 = {
        "batch_id": "BATCH-FILE-2",
        "records": [
            _build_valid_dq01_record(exception_id=shared_case_id),
            _build_valid_dq01_record(exception_id=unique_case_id)
        ]
    }
    (in_dir / "file_2.json").write_text(json.dumps(file_2), encoding="utf-8")
    watcher.scan_once()

    # Exactly 1 new case added (unique_case_id)
    assert len(repo.cases) == cases_after_file1 + 1
    assert repo.get_case(unique_case_id) is not None

    # Reconciliation for File 2 must record shared_case_id as SKIPPED_EXISTING_CASE
    recon = json.loads((out_dir / "BATCH-FILE-2.reconciliation.json").read_text(encoding="utf-8"))
    assert recon["total_records"] == 2
    assert recon["processed_count"] == 1
    assert recon["skipped_count"] == 1
    assert recon["records"][0]["status"] == "SKIPPED_EXISTING_CASE"
    assert recon["records"][1]["status"] == "PROCESSED"


# =========================================================================
# Test 9: Duplicate identifiers within a batch
# =========================================================================
def test_09_duplicate_identifiers_within_batch(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    batch_id = f"BATCH-INTRADUP-{uuid.uuid4().hex[:6].upper()}"
    dup_case_id = f"CASE-DUP-{uuid.uuid4().hex[:6].upper()}"

    batch_payload = {
        "batch_id": batch_id,
        "records": [
            _build_valid_dq01_record(exception_id=dup_case_id, amount=1000.0),
            _build_valid_dq01_record(exception_id=dup_case_id, amount=2000.0) # Duplicate ID in same batch
        ]
    }
    (in_dir / "intra_batch_dup.json").write_text(json.dumps(batch_payload), encoding="utf-8")

    watcher.scan_once()

    # Exactly 1 case should exist in DB
    case = repo.get_case(dup_case_id)
    assert case is not None
    assert case["amount"] == 1000.0 # First record processed

    recon = json.loads((out_dir / f"{batch_id}.reconciliation.json").read_text(encoding="utf-8"))
    assert recon["total_records"] == 2
    assert recon["processed_count"] == 1
    assert recon["skipped_count"] == 1
    assert recon["records"][1]["status"] == "SKIPPED_DUPLICATE_IN_BATCH"


# =========================================================================
# Test 10: Partial processing failure and safe retry
# =========================================================================
def test_10_partial_processing_failure_and_safe_retry(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    batch_id = f"BATCH-RETRY-{uuid.uuid4().hex[:6].upper()}"
    c1 = f"CASE-RETRY-1-{uuid.uuid4().hex[:6].upper()}"
    c2 = f"CASE-RETRY-2-{uuid.uuid4().hex[:6].upper()}"

    # First attempt: record 2 is invalid
    file_attempt_1 = {
        "batch_id": batch_id,
        "records": [
            _build_valid_dq01_record(exception_id=c1),
            {"exception_id": c2, "invalid_structure": True} # Broken record
        ]
    }
    f1 = in_dir / "attempt_1.json"
    f1.write_text(json.dumps(file_attempt_1), encoding="utf-8")
    watcher.scan_once()

    assert repo.get_case(c1) is not None
    assert repo.get_case(c2) is None

    # Second attempt: corrected file with different content hash
    file_attempt_2 = {
        "batch_id": batch_id,
        "records": [
            _build_valid_dq01_record(exception_id=c1), # Already processed
            _build_valid_dq01_record(exception_id=c2)  # Now valid
        ]
    }
    f2 = in_dir / "attempt_2.json"
    f2.write_text(json.dumps(file_attempt_2), encoding="utf-8")
    watcher.scan_once()

    # Both cases now exist without c1 being duplicated
    assert repo.get_case(c1) is not None
    assert repo.get_case(c2) is not None

    recon2 = json.loads((out_dir / f"{batch_id}.reconciliation.json").read_text(encoding="utf-8"))
    assert recon2["records"][0]["status"] == "SKIPPED_EXISTING_CASE"
    assert recon2["records"][1]["status"] == "PROCESSED"


# =========================================================================
# Test 11: File-level reconciliation counts and mathematical reconciliation
# =========================================================================
def test_11_reconciliation_counts_reconcile_strictly(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    batch_id = f"BATCH-MATH-{uuid.uuid4().hex[:6].upper()}"
    case_good = f"CASE-G-{uuid.uuid4().hex[:6].upper()}"
    case_dup = f"CASE-D-{uuid.uuid4().hex[:6].upper()}"

    # Seed one existing case in repo first
    repo.save_case({"case_id": case_dup, "status": "INGESTED"})

    batch_payload = {
        "batch_id": batch_id,
        "records": [
            _build_valid_dq01_record(exception_id=case_good),     # Valid -> PROCESSED (1)
            {"exception_id": "BAD-REC"},                          # Invalid schema -> FAILED (1)
            _build_valid_dq01_record(exception_id=case_dup),      # Exists in DB -> SKIPPED (1)
            _build_valid_dq01_record(exception_id=case_good)      # Duplicate in batch -> SKIPPED (1)
        ]
    }
    (in_dir / "math_check.json").write_text(json.dumps(batch_payload), encoding="utf-8")
    watcher.scan_once()

    recon = json.loads((out_dir / f"{batch_id}.reconciliation.json").read_text(encoding="utf-8"))

    # Mathematical identity checks
    assert recon["total_records"] == 4
    assert recon["valid_records"] == 3
    assert recon["invalid_records"] == 1
    assert recon["total_records"] == recon["valid_records"] + recon["invalid_records"]

    assert recon["processed_count"] == 1
    assert recon["skipped_count"] == 2
    assert recon["failed_count"] == 1
    assert recon["total_records"] == recon["processed_count"] + recon["skipped_count"] + recon["failed_count"]


# =========================================================================
# Test 12: Audit-chain cryptographic integrity across batch events
# =========================================================================
def test_12_audit_chain_cryptographic_integrity_across_batch(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    batch_id = f"BATCH-AUDIT-{uuid.uuid4().hex[:6].upper()}"
    c1 = f"CASE-AUDIT-1-{uuid.uuid4().hex[:6].upper()}"
    c2 = f"CASE-AUDIT-2-{uuid.uuid4().hex[:6].upper()}"

    batch_payload = {
        "batch_id": batch_id,
        "records": [
            _build_valid_dq01_record(exception_id=c1),
            _build_valid_dq01_record(exception_id=c2)
        ]
    }
    (in_dir / "audit_batch.json").write_text(json.dumps(batch_payload), encoding="utf-8")
    watcher.scan_once()

    # Chain verification
    verification = audit_service.verify_chain()
    assert verification.is_intact is True


# =========================================================================
# Test 13: Malformed JSON syntax handling without fabricated records
# =========================================================================
def test_13_malformed_json_syntax_error(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    bad_file = in_dir / "broken_syntax.json"
    bad_file.write_text("{\n  \"batch_id\": \"BROKEN\",\n  \"records\": [ unclosed json ...\n", encoding="utf-8")

    past = time.time() - 5.0
    os.utime(str(bad_file), (past, past))

    results = watcher.scan_once()
    assert len(results) == 1
    assert results[0]["status"] == "FAILED"
    assert "Malformed JSON syntax" in results[0]["error"]
    assert "broken_syntax.json" in watcher._failed_files

    # Must NOT generate a reconciliation report with fabricated records
    assert not (out_dir / "broken_syntax.reconciliation.json").exists()


# =========================================================================
# Test 14: Incomplete-file safety via file-readiness guards
# =========================================================================
def test_14_incomplete_file_safety(tmp_path):
    in_dir = tmp_path / "input"
    in_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=tmp_path / "out")

    # 1. Zero-byte file is not ready
    empty_f = in_dir / "empty.json"
    empty_f.touch()
    assert not watcher._is_file_ready(empty_f)

    # 2. File modified within last 1.5s with incomplete syntax is not ready (in-flight write)
    partial_f = in_dir / "partial.json"
    partial_f.write_text("{\"batch_id\": \"PARTIAL\", \"records\": [", encoding="utf-8")
    assert not watcher._is_file_ready(partial_f)

    # 3. File modified > 2.0s ago with valid content is ready
    fresh_f = in_dir / "complete.json"
    fresh_f.write_text("{\"batch_id\": \"COMPLETE\", \"records\": []}", encoding="utf-8")
    past = time.time() - 5.0
    os.utime(str(fresh_f), (past, past))
    assert watcher._is_file_ready(fresh_f)


# =========================================================================
# Test 15: Bank-control boundary: execution_owner == "BANK" and zero live payment execution
# =========================================================================
def test_15_bank_control_boundary_and_zero_live_payment(tmp_path):
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    watcher = FileWatcherService(input_dir=in_dir, output_dir=out_dir, poll_interval=0.1)

    case_id = f"CASE-SAFETY-{uuid.uuid4().hex[:6].upper()}"
    batch_payload = {
        "batch_id": f"BATCH-SAFETY-{uuid.uuid4().hex[:6].upper()}",
        "records": [_build_valid_dq01_record(exception_id=case_id)]
    }
    (in_dir / "safety.json").write_text(json.dumps(batch_payload), encoding="utf-8")
    watcher.scan_once()

    out = json.loads((out_dir / f"{case_id}.output.json").read_text(encoding="utf-8"))

    # Invariant: execution_owner must be BANK
    assert out["execution_owner"] == "BANK"
    # Invariant: bank_handoff_status must indicate handoff ready, not bank settlement executed
    assert out["bank_handoff_status"] == "BANK_HANDOFF_READY"

    recon = json.loads((out_dir / f"{batch_payload['batch_id']}.reconciliation.json").read_text(encoding="utf-8"))
    assert recon["records"][0]["execution_owner"] == "BANK"
