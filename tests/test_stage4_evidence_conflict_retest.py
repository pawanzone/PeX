"""Stage 4 Evidence Conflict Handling & Batch Retest Suite.

Verifies:
1. Valid unambiguous IBAN repair (REC01) remains eligible for STP.
2. Conflicting DDA and SSI evidence (REC04) fails closed (stp_eligible=False).
3. 'contradictory_evidence_flag=True' is recognized by reference adapter and runner.
4. 'contradiction_detected=True' is recognized by reference adapter and runner.
5. Contradictory authoritative evidence CANNOT be overridden by a valid MOD-97 check digit.
6. Missing mandatory evidence (REC03) fails closed.
7. Invalid repair candidate (REC05) fails deterministic checksum validation.
8. Compound exception (REC06) over threshold (£34,000 > £25,000) requires Maker-Checker.
9. End-to-end batch processing isolates malformed records and skips intra-batch duplicates.
10. UI/API status mapping agrees strictly with persisted database cases and reconciliation.
"""
import os
import json
import uuid
from typing import Optional, List, Dict, Any
import pytest
from pathlib import Path

from app.schemas.contracts.e2e_schemas import (
    CanonicalE2EInput,
    CanonicalE2EBatchInput,
    E2EPaymentInfo,
)
from app.services.e2e_runner import e2e_runner
from app.adapters.reference.reference_evidence_adapter import InMemoryEvidenceAdapter
from app.services.file_watcher import FileWatcherService
from app.db.init_db import init_db
from app.db.session import engine, SessionLocal
from app.db.models import CaseModel


def _build_stage4_records(run_id: Optional[str] = None):
    """Returns the standard 8-record test suite for Stage 4."""
    rid = run_id or uuid.uuid4().hex[:6].upper()
    rec01 = {
        "exception_id": f"PEX-STAGE4-T{rid}-REC01-STP",
        "tenant_id": "DEFAULT_BANK",
        "profile_id": "DQ-01",
        "domain": "DATA_QUALITY",
        "error_code": "ERR_INVALID_IBAN_CHECKSUM",
        "error_message": "Creditor IBAN MOD-97 check digit failure on pacs.008 inbound clearing message.",
        "payment_info": {
            "payment_id": "PMT-STAGE4-001",
            "uetr": "UETR-STAGE4-001-A1B2C3",
            "amount": 4250.00,
            "currency": "GBP",
            "clearing_rail": "CHAPS",
            "value_date": "2026-10-16",
            "debtor_name": "Apex Global Treasury (US)",
            "debtor_account": "US11APEX9988770100",
            "debtor_agent_bic": "CHASUS33XXX",
            "creditor_name": "Nordhavn Components A/S",
            "creditor_account": "GB29MIDL40051512345678",
            "creditor_agent_bic": "BARCGB22XXX",
            "remittance_info": "INV-STAGE4-001-SUPPLIES"
        },
        "bank_supplied_evidence": {
            "core_dda_account": "GB29MIDL40051512345679",
            "verified_iban": "GB29MIDL40051512345679"
        },
        "external_authoritative_evidence": {
            "routing_directory": {
                "sort_code": "400515",
                "bank_name": "HSBC Bank UK PLC"
            }
        },
        "derived_evidence": {
            "mod97_calculated_checksum": "29",
            "inbound_transposition_detected": True
        },
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    }

    rec02 = {
        "exception_id": f"PEX-STAGE4-T{rid}-REC02-HITL-SANCTIONS",
        "tenant_id": "DEFAULT_BANK",
        "profile_id": "CO-01",
        "domain": "COMPLIANCE",
        "error_code": "ERR_OFAC_WATCHLIST_MATCH",
        "error_message": "Creditor party matched OFAC SDN Specially Designated Nationals screening list.",
        "payment_info": {
            "payment_id": "PMT-STAGE4-002",
            "uetr": "UETR-STAGE4-002-B2C3D4",
            "amount": 85000.00,
            "currency": "USD",
            "clearing_rail": "FEDWIRE",
            "value_date": "2026-10-16",
            "debtor_name": "Apex Global Treasury (US)",
            "debtor_account": "US11APEX9988770100",
            "debtor_agent_bic": "CHASUS33XXX",
            "creditor_name": "Islamic Revolutionary Guard Corps",
            "creditor_account": "GB82WEST12345698765432",
            "creditor_agent_bic": "WESTGB2LXXX",
            "remittance_info": "INV-STAGE4-002-CRITICAL"
        },
        "bank_supplied_evidence": {
            "sanctions_screening_hit": True,
            "match_confidence": 0.99,
            "list_provider": "OFAC_SDN_LIST"
        },
        "external_authoritative_evidence": {
            "screening_agency": "US_TREASURY_OFAC",
            "hit_details": "Target entity designated under Executive Order 13224"
        },
        "derived_evidence": {
            "sanctions_block_recommended": True
        },
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    }

    rec03 = {
        "exception_id": f"PEX-STAGE4-T{rid}-REC03-MISSING-EVIDENCE",
        "tenant_id": "DEFAULT_BANK",
        "profile_id": "DQ-01",
        "domain": "DATA_QUALITY",
        "error_code": "ERR_INVALID_IBAN_CHECKSUM",
        "error_message": "Creditor IBAN MOD-97 check digit failure on pacs.008 inbound clearing message.",
        "payment_info": {
            "payment_id": "PMT-STAGE4-003",
            "uetr": "UETR-STAGE4-003-C3D4E5",
            "amount": 1200.00,
            "currency": "GBP",
            "clearing_rail": "CHAPS",
            "value_date": "2026-10-16",
            "debtor_name": "Apex Commercial Treasury",
            "debtor_account": "US11APEX9988770100",
            "debtor_agent_bic": "CHASUS33XXX",
            "creditor_name": "Nordhavn Components A/S",
            "creditor_account": "GB82WEST12345698765423",
            "creditor_agent_bic": "WESTGB2LXXX",
            "remittance_info": "INV-STAGE4-003-MISSING-DATA"
        },
        "bank_supplied_evidence": {},
        "external_authoritative_evidence": {
            "routing_directory": {
                "sort_code": "400515",
                "bank_name": "HSBC Bank UK PLC"
            }
        },
        "derived_evidence": {},
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    }

    rec04 = {
        "exception_id": f"PEX-STAGE4-T{rid}-REC04-CONFLICTING-EVIDENCE",
        "tenant_id": "DEFAULT_BANK",
        "profile_id": "DQ-01",
        "domain": "DATA_QUALITY",
        "error_code": "ERR_CONTRADICTORY_EVIDENCE",
        "error_message": "Internal Core DDA account contradicts external beneficiary SSI directory.",
        "payment_info": {
            "payment_id": "PMT-STAGE4-004",
            "uetr": "UETR-STAGE4-004-D4E5F6",
            "amount": 18500.00,
            "currency": "GBP",
            "clearing_rail": "CHAPS",
            "value_date": "2026-10-16",
            "debtor_name": "Apex Commercial Treasury",
            "debtor_account": "US11APEX9988770100",
            "debtor_agent_bic": "CHASUS33XXX",
            "creditor_name": "Nordhavn Components A/S",
            "creditor_account": "GB82WEST12345698765423",
            "creditor_agent_bic": "WESTGB2LXXX",
            "remittance_info": "INV-STAGE4-004-CONFLICT"
        },
        "bank_supplied_evidence": {
            "core_dda_account": "GB82WEST12345698765432",
            "contradictory_evidence_flag": True
        },
        "external_authoritative_evidence": {
            "ssi_directory_account": "GB29MIDL40051512345679",
            "routing_directory": {
                "sort_code": "400515",
                "bank_name": "HSBC Bank UK PLC"
            }
        },
        "derived_evidence": {
            "contradiction_detected": True
        },
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    }

    rec05 = {
        "exception_id": f"PEX-STAGE4-T{rid}-REC05-INVALID-REPAIR",
        "tenant_id": "DEFAULT_BANK",
        "profile_id": "DQ-01",
        "domain": "DATA_QUALITY",
        "error_code": "ERR_INVALID_PROPOSED_REPAIR",
        "error_message": "Proposed repair value fails deterministic MOD-97 check digit verification.",
        "payment_info": {
            "payment_id": "PMT-STAGE4-005",
            "uetr": "UETR-STAGE4-005-E5F6A7",
            "amount": 9500.00,
            "currency": "GBP",
            "clearing_rail": "CHAPS",
            "value_date": "2026-10-16",
            "debtor_name": "Apex Commercial Treasury",
            "debtor_account": "US11APEX9988770100",
            "debtor_agent_bic": "CHASUS33XXX",
            "creditor_name": "Nordhavn Components A/S",
            "creditor_account": "GB82WEST12345698765423",
            "creditor_agent_bic": "WESTGB2LXXX",
            "remittance_info": "INV-STAGE4-005-INVALID-REPAIR"
        },
        "bank_supplied_evidence": {
            "core_dda_account": "GB82WEST12345698765499",
            "syntax_validation_failed": True
        },
        "external_authoritative_evidence": {
            "routing_directory": {
                "sort_code": "400515",
                "bank_name": "HSBC Bank UK PLC"
            }
        },
        "derived_evidence": {
            "deterministic_validation_failed": True
        },
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    }

    rec06 = {
        "exception_id": f"PEX-STAGE4-T{rid}-REC06-COMPOUND",
        "tenant_id": "DEFAULT_BANK",
        "profile_id": "DQ-01",
        "secondary_profile_ids": ["DQ-09"],
        "domain": "DATA_QUALITY",
        "error_code": "ERR_COMPOUND_EXCEPTION",
        "error_message": "Transposed creditor IBAN combined with beneficiary legal name mismatch.",
        "payment_info": {
            "payment_id": "PMT-STAGE4-006",
            "uetr": "UETR-STAGE4-006-F6A7B8",
            "amount": 34000.00,
            "currency": "GBP",
            "clearing_rail": "CHAPS",
            "value_date": "2026-10-16",
            "debtor_name": "Apex Global Treasury (US)",
            "debtor_account": "US11APEX9988770100",
            "debtor_agent_bic": "CHASUS33XXX",
            "creditor_name": "Nordhavn Components Holding A/S",
            "creditor_account": "GB29MIDL40051512345678",
            "creditor_agent_bic": "BARCGB22XXX",
            "remittance_info": "INV-STAGE4-006-COMPOUND"
        },
        "bank_supplied_evidence": {
            "core_dda_account": "GB29MIDL40051512345679",
            "verified_iban": "GB29MIDL40051512345679"
        },
        "external_authoritative_evidence": {
            "routing_directory": {
                "sort_code": "400515",
                "bank_name": "HSBC Bank UK PLC"
            },
            "confirmation_of_payee": {
                "name_match_status": "CLOSE_MATCH",
                "verified_legal_name": "Nordhavn Components A/S"
            }
        },
        "derived_evidence": {
            "mod97_calculated_checksum": "29",
            "inbound_transposition_detected": True
        },
        "evidence_provenance": "SYNTHETIC_TEST_FIXTURE",
        "test_status": "TEST_ONLY"
    }

    # Record 7: Duplicate replay of REC01
    rec07 = dict(rec01)

    # Record 8: Malformed record (missing payment_info)
    rec08 = {
        "exception_id": f"PEX-STAGE4-T{rid}-REC08-MALFORMED",
        "tenant_id": "DEFAULT_BANK",
        "profile_id": "DQ-01",
        "domain": "DATA_QUALITY",
        "error_code": "ERR_MALFORMED_RECORD",
        "error_message": "Malformed test record missing mandatory payment_info block.",
        "bank_supplied_evidence": {}
    }

    return [rec01, rec02, rec03, rec04, rec05, rec06, rec07, rec08]


# =========================================================================
# Unit / Focused Tests
# =========================================================================

def test_rec01_valid_unambiguous_iban_stps():
    """REC01: Valid unambiguous MOD-97 IBAN repair is STP-eligible."""
    records = _build_stage4_records()
    rec01_in = CanonicalE2EInput.model_validate(records[0])
    out = e2e_runner.process_input(rec01_in)

    assert out.stp_eligible is True
    assert out.predicate_breakdown.e_suff is True
    assert out.predicate_breakdown.r_det is True
    assert out.predicate_breakdown.r_uniq is True
    assert out.predicate_breakdown.v_det is True
    assert out.predicate_breakdown.v_auth is True
    assert out.predicate_breakdown.p_bank is True
    assert out.predicate_breakdown.c_comp is True
    assert out.predicate_breakdown.x_pre is True
    assert out.evidence_status == "SUFFICIENT"
    assert out.resolution_status == "RESOLVED"
    assert out.execution_owner == "BANK"
    assert out.bank_handoff_status == "BANK_HANDOFF_READY"


def test_rec04_conflicting_dda_ssi_evidence_fails_closed():
    """REC04: Conflicting Core DDA and SSI Directory evidence fails closed."""
    records = _build_stage4_records()
    rec04_in = CanonicalE2EInput.model_validate(records[3])
    out = e2e_runner.process_input(rec04_in)

    # STP MUST be prohibited
    assert out.stp_eligible is False
    assert out.predicate_breakdown.e_suff is False
    assert out.predicate_breakdown.r_uniq is False
    assert out.evidence_status == "CONTRADICTORY"
    assert len(out.evidence_contradictions) > 0
    assert "CORE_DDA_ACCOUNT" in out.evidence_contradictions
    assert "SSI_DIRECTORY_ACCOUNT" in out.evidence_contradictions
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"
    assert out.execution_owner == "BANK"
    assert out.bank_handoff_status == "MAKER_CHECKER_PENDING"
    assert out.resolution_status == "INVESTIGATION_REQUIRED"


def test_contradictory_evidence_flag_recognized():
    """Verifies that 'contradictory_evidence_flag=True' alone triggers contradiction."""
    payload = {
        "exception_id": "TEST-FLAG-ONLY",
        "tenant_id": "DEFAULT_BANK",
        "profile_id": "DQ-01",
        "payment_info": {
            "payment_id": "PMT-FLAG",
            "uetr": "UETR-FLAG-001",
            "amount": 1000.0,
            "currency": "GBP",
            "clearing_rail": "CHAPS"
        },
        "bank_supplied_evidence": {
            "core_dda_account": "GB82WEST12345698765432",
            "contradictory_evidence_flag": True
        }
    }
    inp = CanonicalE2EInput.model_validate(payload)
    out = e2e_runner.process_input(inp)
    assert out.stp_eligible is False
    assert out.predicate_breakdown.e_suff is False
    assert out.predicate_breakdown.r_uniq is False
    assert out.evidence_status == "CONTRADICTORY"


def test_contradiction_detected_recognized():
    """Verifies that 'contradiction_detected=True' in derived evidence triggers contradiction."""
    payload = {
        "exception_id": "TEST-DERIVED-CONTRA",
        "tenant_id": "DEFAULT_BANK",
        "profile_id": "DQ-01",
        "payment_info": {
            "payment_id": "PMT-DERIVED",
            "uetr": "UETR-DERIVED-001",
            "amount": 1000.0,
            "currency": "GBP",
            "clearing_rail": "CHAPS"
        },
        "bank_supplied_evidence": {
            "core_dda_account": "GB82WEST12345698765432"
        },
        "derived_evidence": {
            "contradiction_detected": True
        }
    }
    inp = CanonicalE2EInput.model_validate(payload)
    out = e2e_runner.process_input(inp)
    assert out.stp_eligible is False
    assert out.predicate_breakdown.e_suff is False
    assert out.predicate_breakdown.r_uniq is False
    assert out.evidence_status == "CONTRADICTORY"


def test_valid_mod97_checksum_cannot_override_contradiction():
    """Requirement 3: A valid IBAN checksum must NOT override unresolved evidence conflicts."""
    records = _build_stage4_records()
    rec04_in = CanonicalE2EInput.model_validate(records[3])
    out = e2e_runner.process_input(rec04_in)

    # Core DDA account GB82WEST12345698765432 has valid check digits (v_det=True)
    assert out.predicate_breakdown.v_det is True
    # But because evidence is contradictory, STP is still blocked!
    assert out.predicate_breakdown.r_uniq is False
    assert out.predicate_breakdown.e_suff is False
    assert out.stp_eligible is False


def test_missing_mandatory_evidence_fails_closed():
    """Requirement 4: Missing mandatory evidence fails closed."""
    records = _build_stage4_records()
    rec03_in = CanonicalE2EInput.model_validate(records[2])
    out = e2e_runner.process_input(rec03_in)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.e_suff is False
    assert "CORE_DDA_ACCOUNT" in out.evidence_missing
    assert out.evidence_status == "INSUFFICIENT"


def test_invalid_repair_candidate_fails_checksum():
    """Invalid repair candidate fails deterministic validation gate."""
    records = _build_stage4_records()
    rec05_in = CanonicalE2EInput.model_validate(records[4])
    out = e2e_runner.process_input(rec05_in)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.v_det is False
    assert out.hitl_required is True


def test_compound_rec06_requires_maker_checker_policy():
    """REC06: £34,000 exceeds fast-lane policy threshold (£25,000) and routes to Maker-Checker."""
    records = _build_stage4_records()
    rec06_in = CanonicalE2EInput.model_validate(records[5])
    out = e2e_runner.process_input(rec06_in)

    assert out.stp_eligible is False
    assert out.predicate_breakdown.p_bank is False
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"


# =========================================================================
# Isolated End-to-End File Watcher Retest
# =========================================================================

def test_isolated_stage4_batch_e2e_retest(tmp_path):
    """Executes the full Stage 4 file watcher batch workflow in a hermetically isolated environment."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    arch_dir = tmp_path / "archive"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    arch_dir.mkdir(parents=True, exist_ok=True)

    watcher = FileWatcherService(
        input_dir=in_dir,
        output_dir=out_dir,
        archive_dir=arch_dir,
        auto_archive=True,
        poll_interval=0.1
    )

    rid = uuid.uuid4().hex[:6].upper()
    records = _build_stage4_records(run_id=rid)
    batch_file_name = f"BATCH-STAGE4-ISOLATED-{rid}.json"
    batch_input_path = in_dir / batch_file_name

    batch_payload = {
        "batch_id": f"BATCH-STAGE4-ISOLATED-{rid}",
        "source_system": "TEST_WATCHER",
        "records": records
    }
    batch_input_path.write_text(json.dumps(batch_payload, indent=2), encoding="utf-8")

    # Execute watcher scan
    results = watcher.scan_once()
    assert len(results) == 1
    scan_res = results[0]

    # Verify scan result summary
    assert scan_res["total_records"] == 8
    assert scan_res["processed_count"] == 6
    assert scan_res["skipped_count"] == 1
    assert scan_res["failed_count"] == 1

    # Load and verify full BatchReconciliationReport artifact
    recon_file = out_dir / f"BATCH-STAGE4-ISOLATED-{rid}.reconciliation.json"
    assert recon_file.exists()
    recon_data = json.loads(recon_file.read_text(encoding="utf-8"))

    assert recon_data["total_records"] == 8
    assert recon_data["processed_count"] == 6
    assert recon_data["skipped_count"] == 1
    assert recon_data["failed_count"] == 1
    assert recon_data["valid_records"] == 7
    assert recon_data["invalid_records"] == 1

    # Verify status breakdown: EXACTLY 1 SETTLED (REC01), REC04 is RECOMMENDED
    outcomes = recon_data["outcomes_by_status"]
    assert outcomes.get("SHADOW_RECORDED") == 1  # default mode is SHADOW
    assert outcomes.get("RECOMMENDED") == 3  # REC04 (conflicting), REC05 (invalid repair), REC06 (compound £34k)
    assert outcomes.get("PENDING_APPROVAL") == 1  # REC02 (sanctions)
    assert outcomes.get("INGESTED") == 1  # REC03 (missing evidence)
    assert outcomes.get("SKIPPED_DUPLICATE_IN_BATCH") == 1  # Record 6 duplicate
    assert outcomes.get("FAILED_SCHEMA") == 1  # Record 7 malformed

    # Verify input file was moved to archive and input folder is now empty
    assert not batch_input_path.exists()
    archived_file = arch_dir / batch_file_name
    assert archived_file.exists()
    assert len(list(in_dir.glob("*.json"))) == 0

    # Verify individual output JSON files
    rec01_out_file = out_dir / f"PEX-STAGE4-T{rid}-REC01-STP.output.json"
    assert rec01_out_file.exists()
    rec01_data = json.loads(rec01_out_file.read_text(encoding="utf-8"))
    assert rec01_data["stp_eligible"] is True
    assert rec01_data["execution_owner"] == "BANK"
    assert rec01_data["bank_handoff_status"] == "BANK_HANDOFF_READY"

    rec04_out_file = out_dir / f"PEX-STAGE4-T{rid}-REC04-CONFLICTING-EVIDENCE.output.json"
    assert rec04_out_file.exists()
    rec04_data = json.loads(rec04_out_file.read_text(encoding="utf-8"))
    assert rec04_data["stp_eligible"] is False
    assert rec04_data["evidence_status"] == "CONTRADICTORY"
    assert rec04_data["execution_owner"] == "BANK"
    assert rec04_data["bank_handoff_status"] == "MAKER_CHECKER_PENDING"

    # Verify database persistence & UI/API status mapping
    db = SessionLocal()
    try:
        c1 = db.query(CaseModel).filter(CaseModel.case_id == f"PEX-STAGE4-T{rid}-REC01-STP").first()
        assert c1 is not None
        assert c1.status == "SHADOW_RECORDED"
        assert c1.queue == "STP Fast-Lane"

        c4 = db.query(CaseModel).filter(CaseModel.case_id == f"PEX-STAGE4-T{rid}-REC04-CONFLICTING-EVIDENCE").first()
        assert c4 is not None
        assert c4.status == "RECOMMENDED"
        assert c4.queue == "Repair"

        cases = db.query(CaseModel).filter(CaseModel.case_id.like(f"PEX-STAGE4-T{rid}-%")).all()
        assert len(cases) == 6
    finally:
        db.close()
