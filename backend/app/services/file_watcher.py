"""Inbound Folder Watcher Service for PeX Automated Transaction Processing.

Monitors e2e_fixtures/input/ for new completed CanonicalE2EInput JSON files,
validates schema, ingests via FolderInputAdapter, executes PII tokenization,
drives the full 8-predicate resolution pipeline via e2e_runner, persists
cases and recommendations to the relational database, and maintains the
cryptographic audit trail.
"""
import os
import sys
import time
import json
import uuid
import hashlib
import logging
import threading
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from app.config import settings
from app.adapters.input_adapter import FolderInputAdapter, InboundPackage
from app.schemas.contracts.e2e_schemas import (
    CanonicalE2EInput,
    CanonicalE2EOutput,
    CanonicalE2EBatchInput,
    BatchReconciliationReport,
    BatchRecordDisposition,
)
from app.services.e2e_runner import e2e_runner, E2EExecutionHarness
from app.core.tokenization import token_vault
from app.services.data_loader import repo, build_rich_guided_recommendation
from app.services.audit_service import audit_service
from app.services.state_machine import transition_case
from app.schemas.canonical import (
    LifecycleStage,
    ExceptionProfile,
    ExceptionSeverity,
    ExceptionPriority,
    ExceptionDomain,
)
from app.schemas.recommendation import (
    DecisionRecommendation,
    ActionType,
    RiskEvaluation,
    ProposedFieldChange,
    CorroboratingEvidenceRef,
)

logger = logging.getLogger("pex.file_watcher")

# Mapping from canonical profile codes to ExceptionProfile enum
PROFILE_CODE_TO_ENUM: Dict[str, ExceptionProfile] = {
    "DQ-01": ExceptionProfile.INVALID_IBAN,
    "DQ-02": ExceptionProfile.INVALID_BIC,
    "DQ-03": ExceptionProfile.MISSING_BENEFICIARY_DATA,
    "DQ-04": ExceptionProfile.MISSING_REMITTANCE_INFO,
    "DQ-05": ExceptionProfile.INVALID_ADDRESS_FORMAT,
    "DQ-06": ExceptionProfile.MISSING_PURPOSE_CODE,
    "DQ-07": ExceptionProfile.INVALID_ACCOUNT_NUMBER,
    "DQ-08": ExceptionProfile.INVALID_ROUTING_CODE,
    "DQ-09": ExceptionProfile.BENEFICIARY_NAME_MISMATCH,
    "PR-01": ExceptionProfile.DUPLICATE_PAYMENT,
    "PR-02": ExceptionProfile.ROUTING_FAILURE,
    "PR-03": ExceptionProfile.ISO20022_VALIDATION_ERROR,
    "PR-04": ExceptionProfile.CUTOFF_MISSED,
    "PR-05": ExceptionProfile.CORRUPTED_MESSAGE_FORMAT,
    "PR-06": ExceptionProfile.INTERMEDIARY_BANK_REJECTION,
    "PR-07": ExceptionProfile.NETWORK_TIMEOUT,
    "PR-08": ExceptionProfile.QUEUE_PROCESSING_FAILURE,
    "PR-09": ExceptionProfile.PAYMENT_HELD_FOR_REPAIR,
    "CO-01": ExceptionProfile.SANCTIONS_SUSPECTED,
    "CO-02": ExceptionProfile.AML_ALERT,
    "CO-03": ExceptionProfile.PEP_MATCH,
    "CO-04": ExceptionProfile.RESTRICTED_CORRIDOR,
    "CO-05": ExceptionProfile.ADVERSE_MEDIA_MATCH,
    "CO-06": ExceptionProfile.HIGH_RISK_JURISDICTION,
    "CO-07": ExceptionProfile.REGULATORY_REPORTING_REQUIRED,
    "CO-08": ExceptionProfile.CUSTOMER_WATCHLIST_MATCH,
    "TR-01": ExceptionProfile.KYC_EXPIRED,
    "TR-02": ExceptionProfile.INSUFFICIENT_FUNDS,
    "TR-03": ExceptionProfile.NOSTRO_SHORTFALL,
    "TR-04": ExceptionProfile.FX_RATE_UNAVAILABLE,
    "TR-05": ExceptionProfile.AUTHORIZATION_MISSING,
    "TR-06": ExceptionProfile.LIMIT_BREACH,
    "TR-07": ExceptionProfile.LIQUIDITY_CONSTRAINT,
    "TR-08": ExceptionProfile.CREDIT_EXPOSURE_BREACH,
    "ST-01": ExceptionProfile.RETURNED_PAYMENT,
    "ST-02": ExceptionProfile.ACCOUNT_CLOSED,
    "ST-03": ExceptionProfile.BENEFICIARY_ACCOUNT_FROZEN,
    "ST-04": ExceptionProfile.RECONCILIATION_BREAK,
    "ST-05": ExceptionProfile.SETTLEMENT_FAILURE,
    "ST-06": ExceptionProfile.FUNDS_TRAPPED_AT_CORRESPONDENT,
    "ST-07": ExceptionProfile.UNMATCHED_CREDIT,
}


class FileWatcherService:
    """Institutional-grade Inbound File Watcher Service for PeX.
    
    Safely monitors the input folder, validates inbound JSON against CanonicalE2EInput,
    ingests payloads via FolderInputAdapter, ensures idempotent at-most-once processing,
    isolates PII through Token Vault, executes the 8-predicate resolution engine,
    and commits resulting cases and cryptographic audit events to the relational database.
    """

    def __init__(
        self,
        input_dir: Optional[Union[str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,
        archive_dir: Optional[Union[str, Path]] = None,
        auto_archive: Optional[bool] = None,
        poll_interval: Optional[float] = None,
        input_adapter: Optional[FolderInputAdapter] = None,
        e2e_runner_instance: Optional[E2EExecutionHarness] = None,
    ):
        base_dir = getattr(settings, "BASE_DIR", Path.cwd())
        configured_input = getattr(settings, "INPUT_WATCH_DIR", base_dir / "e2e_fixtures" / "input")
        configured_output = getattr(settings, "OUTPUT_WATCH_DIR", base_dir / "e2e_fixtures" / "output")
        configured_archive = getattr(settings, "ARCHIVE_WATCH_DIR", base_dir / "e2e_fixtures" / "archive")
        configured_auto_archive = getattr(settings, "WATCHER_AUTO_ARCHIVE", True)
        configured_interval = getattr(settings, "WATCHER_POLL_INTERVAL", 1.0)

        self.input_dir = Path(input_dir or configured_input).resolve()
        self.output_dir = Path(output_dir or configured_output).resolve()
        self.archive_dir = Path(archive_dir or configured_archive).resolve()
        self.auto_archive = auto_archive if auto_archive is not None else configured_auto_archive
        self.poll_interval = float(poll_interval if poll_interval is not None else configured_interval)

        self.input_adapter = input_adapter or FolderInputAdapter(input_dir=str(self.input_dir))
        self.e2e_runner = e2e_runner_instance or e2e_runner

        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Idempotency cache and error registry
        self._processed_hashes: set = set()
        self._failed_files: Dict[str, str] = {}
        self._file_mtimes: Dict[str, float] = {}

    def _baseline_existing_files(self):
        """Indexes pre-existing files in input_dir on startup to avoid re-processing baseline fixtures."""
        if not self.input_dir.exists():
            return
        count = 0
        for f in self.input_dir.glob("*.json"):
            if f.is_file() and not f.name.startswith(".") and not f.name.endswith(".tmp") and ".output." not in f.name:
                try:
                    content = f.read_text(encoding="utf-8")
                    chash = self.input_adapter.calculate_idempotency_hash(content)
                    self._processed_hashes.add(chash)
                    self.input_adapter._processed_hashes.add(chash)
                    count += 1
                except Exception:
                    pass
        logger.info(f"[PeX Watcher] Baselined {count} pre-existing input files in {self.input_dir}")

    def _is_file_ready(self, file_path: Path) -> bool:
        """Verifies that a file is fully written and not currently being copied."""
        try:
            if not file_path.exists() or not file_path.is_file():
                return False

            # Ignore temporary, hidden, or output files
            if file_path.name.startswith(".") or file_path.name.endswith(".tmp") or ".output." in file_path.name:
                return False

            size = file_path.stat().st_size
            if size == 0:
                return False

            # Check if file is readable
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                return False

            # Test JSON parse
            try:
                json.loads(content)
                return True
            except json.JSONDecodeError:
                # If modified within the last 1.5 seconds, could still be copying
                mtime = file_path.stat().st_mtime
                if (time.time() - mtime) < 1.5:
                    return False
                # If older than 1.5s and still cannot parse, treat as ready so error handler can flag it
                return True
        except (IOError, PermissionError):
            return False

    def _archive_file(self, file_path: Path) -> Optional[Path]:
        """Safely moves a consumed input file to the archive directory."""
        if not self.auto_archive:
            return None
        try:
            if not file_path.exists():
                return None
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            dest_file = self.archive_dir / file_path.name
            if dest_file.exists():
                timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                dest_file = self.archive_dir / f"{file_path.stem}_{timestamp_str}{file_path.suffix}"
            shutil.move(str(file_path), str(dest_file))
            logger.info(f"[PeX Watcher] Archived consumed input file: {file_path.name} -> {dest_file.name}")
            return dest_file
        except Exception as e:
            logger.warning(f"[PeX Watcher] Could not archive {file_path.name}: {e}")
            return None

    def process_file(
        self,
        file_path: Union[str, Path],
        force: bool = False
    ) -> Optional[CanonicalE2EOutput]:
        """Executes the complete PeX exception resolution pipeline for a single inbound JSON file."""
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            logger.warning(f"[PeX Watcher] Target file does not exist: {file_path}")
            return None

        # 1. Read raw content
        try:
            content_bytes = file_path.read_bytes()
            content_str = content_bytes.decode("utf-8")
        except Exception as e:
            error_msg = f"Unable to read file {file_path.name}: {e}"
            logger.error(f"[PeX Watcher] {error_msg}")
            self._failed_files[file_path.name] = error_msg
            return None

        # 2. Compute idempotency SHA-256 hash
        content_hash = self.input_adapter.calculate_idempotency_hash(content_str)
        if not force and content_hash in self._processed_hashes:
            logger.debug(f"[PeX Watcher] Content hash {content_hash[:8]} already processed. Skipping {file_path.name}.")
            return None

        # 3. Safe Schema Validation & Batch Detection
        try:
            raw_json = json.loads(content_str)
        except json.JSONDecodeError as jde:
            error_msg = f"Malformed JSON syntax in {file_path.name}: {jde}"
            logger.error(f"[PeX Watcher] {error_msg}")
            self._failed_files[file_path.name] = error_msg
            self._processed_hashes.add(content_hash)
            self._log_failure_audit_event(
                case_id=f"ERR-MALFORMED-{content_hash[:8]}",
                correlation_id=content_hash,
                details=error_msg,
                file_name=file_path.name,
                failure_type="MALFORMED_JSON"
            )
            self._archive_file(file_path)
            return None

        is_batch = isinstance(raw_json, list) or (isinstance(raw_json, dict) and "records" in raw_json)

        # -------------------------------------------------------------------------
        # Branch A: Single Record Flow (Preserves 100% Backward Compatibility)
        # -------------------------------------------------------------------------
        if not is_batch:
            try:
                e2e_input = CanonicalE2EInput.model_validate(raw_json)
            except ValidationError as ve:
                error_msg = f"Schema validation error in {file_path.name}: {ve}"
                logger.error(f"[PeX Watcher] {error_msg}")
                self._failed_files[file_path.name] = error_msg
                self._processed_hashes.add(content_hash)
                self._log_failure_audit_event(
                    case_id=raw_json.get("exception_id", f"ERR-SCHEMA-{content_hash[:8]}"),
                    correlation_id=content_hash,
                    details=error_msg,
                    file_name=file_path.name,
                    failure_type="SCHEMA_VALIDATION_FAILED"
                )
                self._archive_file(file_path)
                return None

            # Check existing case in repository
            if not force and repo.get_case(e2e_input.exception_id):
                logger.info(f"[PeX Watcher] Case {e2e_input.exception_id} already exists in database. Recording hash and skipping.")
                self._processed_hashes.add(content_hash)
                self._archive_file(file_path)
                return None

            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_file = self.output_dir / f"{file_path.stem}.output.json"
            output, final_status = self._process_single_record(
                e2e_input=e2e_input,
                file_path=file_path,
                output_file=output_file,
                content_hash=content_hash,
                batch_id=None,
                record_index=0
            )

            self._processed_hashes.add(content_hash)
            self.input_adapter._processed_hashes.add(content_hash)
            logger.info(f"[PeX Watcher] Successfully processed {file_path.name} -> Case {e2e_input.exception_id} ({final_status})")
            self._archive_file(file_path)
            return output

        # -------------------------------------------------------------------------
        # Branch B: Multi-Record Batch Flow
        # -------------------------------------------------------------------------
        if isinstance(raw_json, dict):
            batch_id = raw_json.get("batch_id") or file_path.stem
            source_system = raw_json.get("source_system", "FILE_DROP")
            raw_records = raw_json.get("records")
            if not isinstance(raw_records, list):
                error_msg = f"Batch envelope in {file_path.name} invalid: 'records' field must be a JSON array."
                logger.error(f"[PeX Watcher] {error_msg}")
                self._failed_files[file_path.name] = error_msg
                self._processed_hashes.add(content_hash)
                self._log_failure_audit_event(
                    case_id=f"ERR-BATCH-{batch_id}",
                    correlation_id=content_hash,
                    details=error_msg,
                    file_name=file_path.name,
                    failure_type="SCHEMA_VALIDATION_FAILED"
                )
                self._archive_file(file_path)
                return None
        else:
            # Top-level array
            batch_id = file_path.stem
            source_system = "FILE_DROP"
            raw_records = raw_json

        total_records = len(raw_records)
        valid_records = 0
        invalid_records = 0
        processed_count = 0
        skipped_count = 0
        failed_count = 0
        outcomes_by_status: Dict[str, int] = {}
        record_dispositions: List[BatchRecordDisposition] = []
        seen_in_batch: Set[str] = set()

        self.output_dir.mkdir(parents=True, exist_ok=True)

        for idx, rec_dict in enumerate(raw_records):
            if not isinstance(rec_dict, dict):
                invalid_records += 1
                failed_count += 1
                outcomes_by_status["FAILED_SCHEMA"] = outcomes_by_status.get("FAILED_SCHEMA", 0) + 1
                err_msg = f"Record at index {idx} in {file_path.name} is not a valid JSON object."
                self._log_failure_audit_event(
                    case_id=f"ERR-{batch_id}-REC-{idx}",
                    correlation_id=f"{batch_id}-{idx}",
                    details=err_msg,
                    file_name=file_path.name,
                    failure_type="SCHEMA_VALIDATION_FAILED"
                )
                record_dispositions.append(BatchRecordDisposition(
                    record_index=idx,
                    exception_id=None,
                    status="FAILED_SCHEMA",
                    error_details=err_msg
                ))
                continue

            try:
                e2e_input = CanonicalE2EInput.model_validate(rec_dict)
                valid_records += 1
            except ValidationError as ve:
                invalid_records += 1
                failed_count += 1
                outcomes_by_status["FAILED_SCHEMA"] = outcomes_by_status.get("FAILED_SCHEMA", 0) + 1
                exc_id = rec_dict.get("exception_id", f"ERR-{batch_id}-REC-{idx}")
                err_msg = f"Record {idx} ({exc_id}) schema validation error: {ve}"
                self._log_failure_audit_event(
                    case_id=exc_id,
                    correlation_id=f"{batch_id}-{idx}",
                    details=err_msg,
                    file_name=file_path.name,
                    failure_type="SCHEMA_VALIDATION_FAILED"
                )
                record_dispositions.append(BatchRecordDisposition(
                    record_index=idx,
                    exception_id=exc_id,
                    status="FAILED_SCHEMA",
                    error_details=str(ve)
                ))
                continue

            exc_id = e2e_input.exception_id
            pmt = e2e_input.payment_info

            # Check duplicate within this batch
            if exc_id in seen_in_batch:
                skipped_count += 1
                outcomes_by_status["SKIPPED_DUPLICATE_IN_BATCH"] = outcomes_by_status.get("SKIPPED_DUPLICATE_IN_BATCH", 0) + 1
                record_dispositions.append(BatchRecordDisposition(
                    record_index=idx,
                    exception_id=exc_id,
                    uetr=pmt.uetr,
                    status="SKIPPED_DUPLICATE_IN_BATCH",
                    error_details="Duplicate exception_id within same batch"
                ))
                continue

            seen_in_batch.add(exc_id)

            # Check existing case in repository
            if not force and repo.get_case(exc_id):
                skipped_count += 1
                outcomes_by_status["SKIPPED_EXISTING_CASE"] = outcomes_by_status.get("SKIPPED_EXISTING_CASE", 0) + 1
                record_dispositions.append(BatchRecordDisposition(
                    record_index=idx,
                    exception_id=exc_id,
                    uetr=pmt.uetr,
                    status="SKIPPED_EXISTING_CASE",
                    error_details=f"Case {exc_id} already exists in database"
                ))
                continue

            # Process record through full domain pipeline
            try:
                rec_output_file = self.output_dir / f"{exc_id}.output.json"
                out, final_status = self._process_single_record(
                    e2e_input=e2e_input,
                    file_path=file_path,
                    output_file=rec_output_file,
                    content_hash=content_hash,
                    batch_id=batch_id,
                    record_index=idx
                )
                processed_count += 1
                outcomes_by_status[final_status] = outcomes_by_status.get(final_status, 0) + 1
                record_dispositions.append(BatchRecordDisposition(
                    record_index=idx,
                    exception_id=exc_id,
                    uetr=pmt.uetr,
                    status="PROCESSED",
                    canonical_stage=final_status,
                    stp_eligible=out.stp_eligible,
                    execution_owner=out.execution_owner,
                    output_file=rec_output_file.name,
                    error_details=None
                ))
            except Exception as pe:
                failed_count += 1
                outcomes_by_status["FAILED_PROCESSING"] = outcomes_by_status.get("FAILED_PROCESSING", 0) + 1
                err_msg = f"Failed processing record {exc_id}: {pe}"
                logger.error(f"[PeX Watcher] {err_msg}", exc_info=True)
                self._log_failure_audit_event(
                    case_id=exc_id,
                    correlation_id=f"{batch_id}-{idx}",
                    details=err_msg,
                    file_name=file_path.name,
                    failure_type="PROCESSING_ERROR"
                )
                record_dispositions.append(BatchRecordDisposition(
                    record_index=idx,
                    exception_id=exc_id,
                    uetr=pmt.uetr,
                    status="FAILED_PROCESSING",
                    error_details=str(pe)
                ))

        # Reconcile report
        recon_report = BatchReconciliationReport(
            batch_id=batch_id,
            source_file=file_path.name,
            file_content_hash=content_hash,
            timestamp=datetime.now(timezone.utc),
            total_records=total_records,
            valid_records=valid_records,
            invalid_records=invalid_records,
            processed_count=processed_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            outcomes_by_status=outcomes_by_status,
            records=record_dispositions
        )

        recon_file = self.output_dir / f"{batch_id}.reconciliation.json"
        recon_file.write_text(recon_report.model_dump_json(indent=2), encoding="utf-8")

        recon_file_by_name = self.output_dir / f"{file_path.stem}.reconciliation.json"
        if recon_file_by_name != recon_file:
            recon_file_by_name.write_text(recon_report.model_dump_json(indent=2), encoding="utf-8")

        audit_service.log_event(
            case_id=f"BATCH-{batch_id}",
            correlation_id=content_hash,
            stage_name="BATCH_RECONCILIATION",
            actor_id="SYSTEM_INBOUND_WATCHER",
            actor_role="SYSTEM",
            action_name="BATCH_RECONCILED",
            details=f"Batch {batch_id} ({file_path.name}): {total_records} total, {processed_count} processed, {skipped_count} skipped, {failed_count} failed. Outcomes: {outcomes_by_status}",
            control_tags=["File Watcher Batch", f"Batch: {batch_id}", f"Source: {file_path.name}"]
        )

        self._processed_hashes.add(content_hash)
        self.input_adapter._processed_hashes.add(content_hash)
        logger.info(f"[PeX Watcher] Successfully reconciled batch {batch_id} from {file_path.name}: {processed_count} processed, {skipped_count} skipped, {failed_count} failed")
        self._archive_file(file_path)
        return recon_report

    def _process_single_e2e_record(
        self,
        e2e_input: CanonicalE2EInput,
        file_path: Optional[Path] = None,
        record_index: int = 0
    ) -> Tuple[CanonicalE2EOutput, str]:
        """Convenience test wrapper for processing a single canonical E2E input."""
        fp = Path(file_path or "test_record.json")
        out_fp = self.output_dir / f"{fp.stem}.output.json"
        ch = hashlib.sha256(e2e_input.model_dump_json().encode("utf-8")).hexdigest()
        return self._process_single_record(
            e2e_input=e2e_input,
            file_path=fp,
            output_file=out_fp,
            content_hash=ch,
            batch_id=None,
            record_index=record_index
        )

    def _process_single_record(
        self,
        e2e_input: CanonicalE2EInput,
        file_path: Path,
        output_file: Path,
        content_hash: str,
        batch_id: Optional[str] = None,
        record_index: int = 0
    ) -> Tuple[CanonicalE2EOutput, str]:
        """Drives ingestion, PII tokenization, reasoning, persistence, and audit for one record."""
        profile_code = (e2e_input.profile_id or "DQ-01").upper()
        secondary_profs = [p.upper() for p in getattr(e2e_input, "secondary_profile_ids", [])]

        # 1. Ingest via FolderInputAdapter (populates EvidenceDossier with isolated evidence)
        try:
            package = InboundPackage(
                package_id=f"PKG-{e2e_input.exception_id}",
                source_channel=f"BANK_WATCH_FOLDER:{file_path.name}",
                raw_payload_str=json.dumps(e2e_input.model_dump(mode="json")),
                evidence_fields={
                    **e2e_input.bank_supplied_evidence,
                    **e2e_input.external_authoritative_evidence,
                    **e2e_input.derived_evidence
                },
                metadata={
                    "batch_id": batch_id or file_path.stem,
                    "record_index": record_index,
                    "file_name": file_path.name
                },
                idempotency_key=e2e_input.payment_info.uetr or e2e_input.exception_id
            )
            self.input_adapter.ingest_payload(package, profile_id=profile_code)
        except Exception as e:
            logger.warning(f"[PeX Watcher] FolderInputAdapter ingestion note: {e}")

        # 2. PII Tokenization Isolation
        pmt = e2e_input.payment_info
        debtor_name_tok = token_vault.tokenize(pmt.debtor_name or "Unknown Debtor", "PARTY")
        debtor_acc_tok = token_vault.tokenize(pmt.debtor_account or "UNKNOWN-ACC", "ACC")
        creditor_name_tok = token_vault.tokenize(pmt.creditor_name or "Unknown Creditor", "PARTY")
        cred_account = pmt.creditor_account or "UNKNOWN-CREDITOR-ACC"
        creditor_acc_tok = token_vault.tokenize(
            cred_account,
            "IBAN" if ("IBAN" in profile_code or "DQ" in profile_code) else "ACC"
        )

        # 3. Cryptographic Ingestion Audit Event
        corr_id = pmt.uetr or f"{batch_id or file_path.stem}-{e2e_input.exception_id}"
        audit_service.log_event(
            case_id=e2e_input.exception_id,
            correlation_id=corr_id,
            stage_name="INTAKE",
            actor_id="SYSTEM_INBOUND_WATCHER",
            actor_role="SYSTEM",
            action_name="RECORD_INGESTED" if batch_id else "FILE_INGESTED",
            details=f"Inbound exception record {e2e_input.exception_id} from {file_path.name} ingested via FolderInputAdapter. Registered canonical case ({profile_code}).",
            control_tags=["File Watcher Ingestion", "FolderInputAdapter", f"Source: {file_path.name}", f"RecordIdx: {record_index}"],
            amount=pmt.amount,
            currency=pmt.currency,
            debtor_account=pmt.debtor_account,
            creditor_account=pmt.creditor_account
        )

        # 4. Drive Canonical Resolution Harness (Evaluates all 8 predicates & outputs CanonicalE2EOutput)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output = self.e2e_runner.process_input(e2e_input, output_file_path=output_file)

        # 5. Workflow Routing & Status Assignment
        op_mode = getattr(settings, "PEX_OPERATION_MODE", "SHADOW").upper()
        if output.stp_eligible:
            target_status = LifecycleStage.SHADOW_RECORDED.value if op_mode == "SHADOW" else LifecycleStage.HANDED_TO_BANK.value
            target_queue = "STP Fast-Lane"
            target_reason = f"Autonomous STP qualified ({output.stp_decision_reason}). Handed off to {target_status}."
        else:
            if e2e_input.domain == "COMPLIANCE" or "CO" in profile_code or profile_code in ["KYC_EXPIRED", "SANCTIONS_SUSPECTED", "TR-01"]:
                target_queue = "Compliance"
                target_status = LifecycleStage.PENDING_APPROVAL.value
            elif profile_code in ["DUPLICATE_PAYMENT", "PR-01", "FUNDS_TRAPPED_AT_CORRESPONDENT", "ST-06", "RETURNED_PAYMENT", "ST-01"]:
                target_queue = "Investigation"
                target_status = LifecycleStage.PENDING_APPROVAL.value
            elif profile_code in ["CREDIT_EXPOSURE_BREACH", "TR-08"]:
                target_queue = "Risk"
                target_status = LifecycleStage.PENDING_APPROVAL.value
            else:
                target_queue = "Repair"
                target_status = LifecycleStage.RECOMMENDED.value if output.resolution_recommendation else LifecycleStage.INGESTED.value
            target_reason = f"Routed to {target_queue} queue: {output.stp_decision_reason or 'Manual review required'}"

        # 6. Case Persistence to Persistent Database
        domain_val = e2e_input.domain or ("DATA_QUALITY" if "DQ" in profile_code else ("PROCESSING" if "PR" in profile_code else ("COMPLIANCE" if "CO" in profile_code else ("CLIENT_TREASURY" if "TR" in profile_code else "SETTLEMENT_RETURNS"))))

        case_dict = {
            "case_id": e2e_input.exception_id,
            "payment_id": pmt.payment_id,
            "uetr": pmt.uetr,
            "payment_ref": pmt.remittance_info or f"REF-{pmt.payment_id}",
            "profile": profile_code,
            "domain": domain_val,
            "secondary_profiles": secondary_profs,
            "error_code": e2e_input.error_code or "ERR_PAYMENT_EXCEPTION",
            "reason": e2e_input.error_message or f"Payment exception in {domain_val}: {profile_code}",
            "amount": float(pmt.amount),
            "currency": pmt.currency,
            "payment_rail": pmt.clearing_rail or "SWIFT_CBPR+",
            "debtor_party": {
                "party_name": pmt.debtor_name or "Ordering Customer",
                "country": "US",
                "token_ref": debtor_name_tok
            },
            "debtor_account": {
                "account_number": pmt.debtor_account or "US11APEX998877",
                "token_ref": debtor_acc_tok
            },
            "creditor_party": {
                "party_name": pmt.creditor_name or "Beneficiary Customer",
                "country": e2e_input.bank_supplied_evidence.get("creditor_country", "GB"),
                "token_ref": creditor_name_tok
            },
            "creditor_account": {
                "account_number": pmt.creditor_account or "GB29MIDL400515",
                "iban": pmt.creditor_account or "GB29MIDL400515",
                "bank_bic": pmt.creditor_agent_bic or "BARCGB22XXX",
                "token_ref": creditor_acc_tok
            },
            "queue": target_queue,
            "status": LifecycleStage.INGESTED.value,
            "severity": ExceptionSeverity.HIGH.value if (pmt.amount >= 250000.0 or "CO" in profile_code) else ExceptionSeverity.MEDIUM.value,
            "priority": ExceptionPriority.HIGH.value if pmt.amount >= 250000.0 else ExceptionPriority.NORMAL.value,
            "sla_due_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            "dual_auth_required": bool(pmt.amount >= 250000.0),
            "ai_confidence": output.ai_confidence_score,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "settled_at": None,
            "approval_history": [],
            "audit_timeline": [
                {
                    "step_index": 1,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "actor_name": "Inbound File Watcher",
                    "actor_role": "SYSTEM",
                    "badge_color": "blue",
                    "action_title": "Exception Ingested from Watch Folder",
                    "icon": "📥",
                    "summary": f"File {file_path.name} ingested via FolderInputAdapter. Registered case {e2e_input.exception_id}."
                },
                {
                    "step_index": 2,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "actor_name": "PeX Governed Reasoner",
                    "actor_role": "SYSTEM",
                    "badge_color": "emerald" if output.stp_eligible else "amber",
                    "action_title": "Canonical 8-Predicate Resolution Evaluated",
                    "icon": "⚡",
                    "summary": f"STP Eligible: {output.stp_eligible}. Decision reason: {output.stp_decision_reason}"
                }
            ],
            "guided_questions": []
        }

        # Transition strictly via transition_case
        transition_case(
            case=case_dict,
            to_state=target_status,
            actor="FolderInputWatcher",
            reason=target_reason,
            dispatch_status="AWAITING_BANK_ACK" if target_status == LifecycleStage.HANDED_TO_BANK.value else None
        )
        final_status = case_dict["status"]

        # Save case
        repo.save_case(case_dict)

        # 7. Persist Structured Recommendation
        self._attach_recommendation(e2e_input, output)

        # 8. Final Disposition Audit Event
        audit_service.log_event(
            case_id=e2e_input.exception_id,
            correlation_id=corr_id,
            stage_name="HANDOFF" if output.stp_eligible else "WORKFLOW_ROUTING",
            actor_id="SYS-AUTONOMOUS-STP" if output.stp_eligible else "WORKFLOW_ROUTER",
            actor_role="SYSTEM",
            action_name="AUTONOMOUS_STP_HANDOFF" if output.stp_eligible else "ROUTED_TO_QUEUE",
            details=f"Case {e2e_input.exception_id} disposition: {final_status} in queue '{target_queue}'. STP eligible: {output.stp_eligible}. Execution owner: {output.execution_owner}.",
            control_tags=["File Watcher Finalized", f"Queue: {target_queue}", f"Status: {final_status}", f"File: {file_path.name}"],
            amount=pmt.amount,
            currency=pmt.currency
        )

        return output, final_status

    def _attach_recommendation(
        self,
        e2e_input: CanonicalE2EInput,
        output: CanonicalE2EOutput
    ):
        """Builds and persists a DecisionRecommendation matching the E2E resolution output."""
        case_id = e2e_input.exception_id
        profile_code = (e2e_input.profile_id or "DQ-01").upper()
        prof_enum = PROFILE_CODE_TO_ENUM.get(profile_code, ExceptionProfile.INVALID_IBAN)
        pmt = e2e_input.payment_info

        try:
            rec = build_rich_guided_recommendation(
                case_id=case_id,
                profile=prof_enum,
                amount=pmt.amount,
                creditor_name=pmt.creditor_name or "Beneficiary",
                creditor_country=e2e_input.bank_supplied_evidence.get("creditor_country", "GB"),
                case_idx=1
            )
            if output.resolution_basis:
                rec.rationale = output.resolution_basis
            if output.repaired_fields:
                rec.proposed_changes = [
                    ProposedFieldChange(
                        field_path=rf.get("field_path", "unknown"),
                        original_value_masked=str(rf.get("original_value", "")),
                        proposed_value_masked=str(rf.get("repaired_value", "")),
                        raw_proposed_value=str(rf.get("repaired_value", "")),
                        justification=output.resolution_basis or "Deterministic repair validated.",
                        validation_status="VALIDATED"
                    )
                    for rf in output.repaired_fields
                ]
            rec.confidence_score = output.ai_confidence_score
            repo.save_recommendation(rec)
        except Exception as e:
            logger.warning(f"[PeX Watcher] Rich recommendation build note: {e}. Using standard contract.")
            action_type_val = ActionType.REPAIR_AND_RELEASE if output.stp_eligible else ActionType.REPAIR_DATA
            fallback_rec = DecisionRecommendation(
                recommendation_id=f"REC-{case_id}",
                case_id=case_id,
                action_type=action_type_val,
                confidence_score=output.ai_confidence_score,
                rationale=output.resolution_basis or "Deterministic resolution evaluated.",
                proposed_changes=[
                    ProposedFieldChange(
                        field_path=rf.get("field_path", "unknown"),
                        original_value_masked=str(rf.get("original_value", "")),
                        proposed_value_masked=str(rf.get("repaired_value", "")),
                        raw_proposed_value=str(rf.get("repaired_value", "")),
                        justification="Deterministic repair validated.",
                        validation_status="VALIDATED"
                    )
                    for rf in output.repaired_fields
                ],
                risk_evaluation=RiskEvaluation(
                    risk_level=ExceptionSeverity.HIGH if pmt.amount >= 250000.0 else ExceptionSeverity.MEDIUM,
                    risk_score=0.15 if output.stp_eligible else 0.45,
                    risk_factors=["Autonomous STP eligible"] if output.stp_eligible else ["Manual review required"],
                    dual_auth_required=(pmt.amount >= 250000.0)
                )
            )
            repo.save_recommendation(fallback_rec)

    def _log_failure_audit_event(
        self,
        case_id: str,
        correlation_id: str,
        details: str,
        file_name: str,
        failure_type: str
    ):
        """Visibly records an audit event for malformed or unparseable input files."""
        try:
            audit_service.log_event(
                case_id=case_id,
                correlation_id=correlation_id,
                stage_name="INGESTION_VALIDATION",
                actor_id="SYSTEM_INBOUND_WATCHER",
                actor_role="SYSTEM",
                action_name=failure_type,
                details=details[:300],
                control_tags=["File Watcher", "Validation Failure", file_name]
            )
        except Exception as e:
            logger.error(f"[PeX Watcher] Failed to log failure audit event: {e}")

    def scan_once(self) -> List[Dict[str, Any]]:
        """Executes a single synchronous scan pass over input_dir.
        
        Returns a list of processing summary dictionaries.
        """
        results = []
        if not self.input_dir.exists():
            return results

        for file_path in sorted(self.input_dir.glob("*.json")):
            if not self._is_file_ready(file_path):
                continue

            try:
                content_bytes = file_path.read_bytes()
                content_str = content_bytes.decode("utf-8")
                content_hash = self.input_adapter.calculate_idempotency_hash(content_str)
                if content_hash in self._processed_hashes:
                    continue

                output = self.process_file(file_path)
                if output:
                    if isinstance(output, BatchReconciliationReport):
                        results.append({
                            "file_name": file_path.name,
                            "batch_id": output.batch_id,
                            "total_records": output.total_records,
                            "processed_count": output.processed_count,
                            "skipped_count": output.skipped_count,
                            "failed_count": output.failed_count,
                            "status": "PROCESSED" if output.failed_count == 0 else ("PARTIAL_SUCCESS" if output.processed_count > 0 else "FAILED")
                        })
                    else:
                        results.append({
                            "file_name": file_path.name,
                            "exception_id": output.exception_id,
                            "profile_id": output.detected_profile_id,
                            "stp_eligible": output.stp_eligible,
                            "status": "PROCESSED"
                        })
                elif file_path.name in self._failed_files:
                    results.append({
                        "file_name": file_path.name,
                        "status": "FAILED",
                        "error": self._failed_files[file_path.name]
                    })
                else:
                    results.append({
                        "file_name": file_path.name,
                        "status": "SKIPPED_EXISTING"
                    })

            except Exception as e:
                logger.error(f"[PeX Watcher] Error scanning file {file_path.name}: {e}")
        return results

    def _watch_loop(self):
        """Continuous background thread polling input_dir."""
        logger.info(f"[PeX Watcher] Background polling thread started on {self.input_dir} (interval={self.poll_interval}s)")
        while not self._stop_event.is_set():
            try:
                self.scan_once()
            except Exception as e:
                logger.error(f"[PeX Watcher] Error in polling loop: {e}", exc_info=True)
            self._stop_event.wait(self.poll_interval)

    def start(self, initial_scan_baseline: bool = True):
        """Starts the file watcher background thread."""
        with self._lock:
            if self._running:
                return

            self._stop_event.clear()
            self.input_dir.mkdir(parents=True, exist_ok=True)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            if self.auto_archive:
                self.archive_dir.mkdir(parents=True, exist_ok=True)

            if initial_scan_baseline:
                self._baseline_existing_files()

            self._thread = threading.Thread(
                target=self._watch_loop,
                name="PeX-Inbound-File-Watcher",
                daemon=True
            )
            self._running = True
            self._thread.start()
            logger.info(f"[PeX Watcher] Started background monitoring on {self.input_dir}")

    def stop(self, timeout: float = 3.0):
        """Stops the file watcher background thread cleanly."""
        with self._lock:
            if not self._running:
                return
            self._stop_event.set()
            self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            logger.info("[PeX Watcher] Stopped background monitoring.")

    def is_running(self) -> bool:
        """Returns True if the background thread is alive and actively running."""
        return self._running and (self._thread is not None) and self._thread.is_alive()

    def get_status(self) -> Dict[str, Any]:
        """Returns runtime status and telemetry for health checks."""
        return {
            "is_running": self.is_running(),
            "input_dir": str(self.input_dir),
            "output_dir": str(self.output_dir),
            "archive_dir": str(self.archive_dir),
            "auto_archive": self.auto_archive,
            "poll_interval": self.poll_interval,
            "processed_hashes_count": len(self._processed_hashes),
            "failed_files_count": len(self._failed_files),
            "failed_files": dict(self._failed_files)
        }


# Global application singleton
file_watcher = FileWatcherService()
FolderInputWatcher = FileWatcherService

