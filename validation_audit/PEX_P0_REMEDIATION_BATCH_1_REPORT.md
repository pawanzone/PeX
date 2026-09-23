# PeX — P0 Remediation Batch 1 Completion Report

**Authority Baseline:** `validation_audit/PEX_MASTER_REMEDIATION_REGISTER_FINAL.md`  
**Execution Date:** September 23, 2026  
**Scope:** P0 Batch 1 (Security, Cryptographic Integrity, STP Engine Governance, IAM/SoD, Domain Propagation & Test Hygiene)  
**Status:** **100% COMPLETE & VERIFIED (63 / 63 Tests Passing)**

---

## 1. Executive Summary

P0 Remediation Batch 1 has been executed in full conformance with the authoritative Master Remediation Register. Exactly the 8 scoped Master IDs (`MST-009`, `MST-034`, `MST-037`, `MST-036`, `MST-035`, `MST-038`, `MST-039`, `MST-033`) have been remediated, hardened with dedicated adversarial test suites, and verified against the regression baseline.

| Master ID | Finding Description | Severity | Target Files | Remediation Status |
|---|---|---|---|---|
| **`MST-009`** | Amount, Currency & Accounts Omitted from Audit Hash | **CRITICAL** | `backend/app/core/hashing.py`<br>`backend/app/schemas/audit.py`<br>`backend/app/db/models.py`<br>`backend/app/db/repository.py`<br>`backend/app/db/init_db.py`<br>`backend/app/services/audit_service.py` | **REMEDIATED & VERIFIED** |
| **`MST-034`** | Missing Adversarial Cryptographic Hash Tampering Tests | **HIGH** | `tests/test_audit_trail.py` | **IMPLEMENTED (7 / 7 PASSED)** |
| **`MST-037`** | Missing SQLAlchemy `Session` Import in STP Engine | **CRITICAL** | `backend/app/services/stp_engine.py` | **REMEDIATED & VERIFIED** |
| **`MST-036`** | STP Fast-Lane Drops AI Repairs | **HIGH** | `backend/app/services/stp_engine.py` | **REMEDIATED & VERIFIED** |
| **`MST-035`** | Frontend Dispatch Omits Auth Headers & Hardcoded User | **CRITICAL** | `backend/app/api/endpoints/actions.py`<br>`build_guided_frontend.py`<br>`frontend/dist/index.html`<br>`frontend/src/services/api.ts` | **REMEDIATED & VERIFIED** |
| **`MST-038`** | `auto_approve` Maker-Checker Bypass | **CRITICAL** | `backend/app/api/endpoints/rules.py`<br>`backend/app/db/repository.py` | **REMEDIATED & VERIFIED** |
| **`MST-039`** | Canonicalizer Omits Domain Parameter | **MEDIUM** | `backend/app/services/canonicalizer.py` | **REMEDIATED & VERIFIED** |
| **`MST-033`** | 13 Root Scripts Polluting Pytest Discovery | **HIGH** | Root workspace -> `tools/diagnostics/`<br>`pytest.ini` | **REMEDIATED & CLEAN** |

---

## 2. Granular Remediation Breakdown by Master ID

### A. `MST-009` — Audit Hash Financial Invariant Expansion
- **Defect:** `calculate_event_hash` did not bind financial attributes (`amount`, `currency`, `debtor_account`, `creditor_account`). A database administrator or attacker could silently modify the wire amount (e.g. from \$10,000 to \$1,000,000) or alter account numbers without invalidating the SHA-256 hash chain.
- **Remediations Implemented:**
  1. `backend/app/core/hashing.py`:
     - Updated `calculate_event_hash` to include deterministic serialization of `amount` (formatted to `.2f`), `currency`, `debtor_account`, and `creditor_account`.
     - Uses canonical JSON sorting (`sort_keys=True, separators=(',', ':')`).
     - Updated `verify_audit_chain` to pass financial attributes through verification.
  2. `backend/app/schemas/audit.py`: Added `amount`, `currency`, `debtor_account`, `creditor_account` fields to `AuditEvent`.
  3. `backend/app/db/models.py`: Added `amount`, `currency`, `debtor_account`, `creditor_account` columns to `AuditEventModel`.
  4. `backend/app/db/repository.py`: Updated `log_audit_event` to auto-lookup financial attributes from the case if not explicitly provided, sanitize dict representations into strings, and persist them.
  5. `backend/app/db/init_db.py`: Added automatic SQLite schema migration (`PRAGMA table_info` check and `ALTER TABLE audit_events ADD COLUMN`).
  6. `backend/app/services/audit_service.py`: Forwarded financial fields in `log_event` and extracted them in `verify_chain()`.

### B. `MST-034` — Adversarial Cryptographic Tampering Test Suite
- **Requirement:** Comprehensive adversarial tests proving that any post-facto modification of case details or audit fields breaks the cryptographic hash chain.
- **Remediations Implemented:**
  - Created `tests/test_audit_trail.py` with 7 dedicated adversarial test cases:
    1. `test_audit_trail_amount_tampering_detected`: Validates that modifying wire amount from \$50,000 to \$500,000 fails `verify_audit_chain`.
    2. `test_audit_trail_currency_tampering_detected`: Validates that modifying currency from USD to EUR fails hash verification.
    3. `test_audit_trail_debtor_account_tampering_detected`: Validates that modifying ordering account fails hash verification.
    4. `test_audit_trail_creditor_account_tampering_detected`: Validates that modifying beneficiary account fails hash verification.
    5. `test_audit_trail_multiple_fields_tampering`: Validates multi-field tampering detection.
    6. `test_audit_trail_database_level_tampering_fails_verification`: Validates that direct SQL updates to SQLite `audit_events` records break `audit_service.verify_chain()`.
    7. `test_audit_trail_canonical_determinism`: Validates that dictionary key order does not alter the hash output.

### C. `MST-037` — Missing SQLAlchemy `Session` Import in STP Engine
- **Defect:** `backend/app/services/stp_engine.py` referenced type hint `Session` without importing it, which caused a runtime `NameError` whenever `execute_autonomous_stp` or `execute_batch_fast_lane_release` was invoked.
- **Remediations Implemented:**
  - Added `from sqlalchemy.orm import Session` at line 15 in `backend/app/services/stp_engine.py`.
  - Added unit test `test_mst_037_stp_session_import_integrity` verifying `Session is SQLAlchemySession`.

### D. `MST-036` — STP Fast-Lane Autonomous Repair Preservation
- **Defect:** In `backend/app/services/stp_engine.py`, `execute_autonomous_stp` and `execute_batch_fast_lane_release` created an `ApprovalRecordModel` with empty `approved_changes=[]`, dropping AI recommendations (e.g. IBAN MOD-97 repairs) and sending unrepaired XML payloads.
- **Remediations Implemented:**
  - Updated `execute_autonomous_stp` to lookup AI recommendations from `repo.get_recommendation(case_id)` and extract `rec.proposed_changes`.
  - Populated `approved_changes` on `ApprovalRecordModel` and updated `case["approval_history"]`.
  - Embedded `repaired_fields` into `dispatch_payload` on the generated `GovernedActionModel`.
  - Updated `execute_batch_fast_lane_release` to similarly extract and attach AI proposed changes.
  - Added test `test_mst_036_stp_fast_lane_preserves_repaired_fields`.

### E. `MST-035` — Frontend Dispatch Authentication & SoD Enforcement
- **Defect:** Frontend `handleExecuteDispatch` submitted unauthenticated `POST /api/actions/execute` requests without headers. Backend defaulted missing authentication to `APR-3191` (Daniel Osei), allowing Operators to settle wires while falsely stamping an Approver's signature.
- **Remediations Implemented:**
  1. `build_guided_frontend.py` (and recompiled `frontend/dist/index.html`):
     - Updated `handleExecuteDispatch` to pass `Authorization: Bearer pex-token-${currentPersona.user_id}` and `actor_id: currentPersona.user_id`.
  2. `frontend/src/services/api.ts`: Updated `executeAction` to accept optional `token` and `actor_id` and attach `Authorization` header.
  3. `backend/app/api/endpoints/actions.py`:
     - Removed default fallback to `"APR-3191"`.
     - Required valid `Authorization` Bearer token or `req.actor_id`; returns `HTTP 401 Unauthorized` if neither is present.
     - Looked up persona via `get_persona(user_id)`; returns `HTTP 401 Unauthorized` if persona is unrecognized.
     - Enforced Segregation of Duties: returns `HTTP 403 Forbidden` if `actor.role == UserRole.OPERATOR`.
  4. Added adversarial tests `test_mst_035_dispatch_unauthenticated_rejected`, `test_mst_035_dispatch_invalid_persona_rejected`, and `test_mst_035_dispatch_operator_rejected_sod`.

### F. `MST-038` — Rules & ICD Auto-Approve Maker-Checker Governance
- **Defect:** `POST /api/rules/submit` and `POST /api/rules/icd-configs/submit` accepted `auto_approve: bool = True` without role validation, allowing Operators to inject active production rules without Checker review.
- **Remediations Implemented:**
  1. `backend/app/api/endpoints/rules.py`:
     - In `submit_rule_for_approval` and `submit_icd_config`: if `payload.auto_approve` is `True`, enforces:
       - `checker_id` must be present (returns `403 Forbidden` if omitted).
       - Segregation of Duties: `maker_id != checker_id` (returns `403 Forbidden` if self-approving).
       - Checker role verification: `get_persona(checker_id).role != UserRole.OPERATOR` (returns `403 Forbidden` if an Operator attempts to sign off).
  2. `backend/app/db/repository.py`:
     - Updated `save_policy_rule` and `save_icd_config` to persist `checker_id`, `checker_name`, `checker_comments`, and `approved_at` on newly created records.
  3. Added adversarial tests `test_mst_038_rule_auto_approve_operator_checker_rejected`, `test_mst_038_rule_auto_approve_self_approval_rejected`, `test_mst_038_rule_auto_approve_valid_approver_accepted`, and `test_mst_038_icd_auto_approve_governance`.

### G. `MST-039` — Canonicalizer Domain Parameter Propagation
- **Defect:** `canonicalize_bank_event` in `backend/app/services/canonicalizer.py` instantiated `CanonicalException` without passing `domain`, causing all exceptions to default to `DATA_QUALITY`.
- **Remediations Implemented:**
  - Imported `get_domain_for_profile` and `ExceptionDomain` into `backend/app/services/canonicalizer.py`.
  - Added `override_profile: Optional[ExceptionProfile] = None` support.
  - Derived `domain = get_domain_for_profile(profile)` and explicitly passed `domain=domain` to `CanonicalException(...)`.
  - Added test `test_mst_039_canonicalizer_domain_propagation` validating all 5 market domains (`COMPLIANCE`, `DATA_QUALITY`, `PROCESSING`, `CLIENT_TREASURY`, `SETTLEMENT_RETURNS`).

### H. `MST-033` — Test Discovery & Root Directory Hygiene
- **Defect:** 13 ad-hoc diagnostic scripts in the repository root (`test_*.py`) polluted pytest test discovery.
- **Remediations Implemented:**
  - Created directory `tools/diagnostics/` and moved all 13 files (`test_cases_count.py`, `test_check.py`, `test_compliance_second_approval.py`, `test_db_e2e.py`, `test_double_load.py`, `test_http_marisol.py`, `test_import.py`, `test_live_api.py`, `test_live_marisol_ok.py`, `test_live_ok.py`, `test_marisol_approval.py`, `test_ping.py`, `test_stages.py`).
  - Added `pytest.ini` in workspace root configuring `testpaths = tests backend/tests` and `pythonpath = backend`.

---

## 3. Test Suite Verification & Execution Results

All test suites were executed under Python 3.11 with pytest:

```
============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\pawan\.gemini\antigravity\scratch\pex_platform
configfile: pytest.ini

tests/test_audit_trace.py .                                              [  1%]
tests/test_audit_trail.py .......                                        [ 12%]
tests/test_canonicalization.py .                                         [ 14%]
tests/test_contracts.py ...                                              [ 19%]
tests/test_functional_adversarial.py ..................                  [ 47%]
tests/test_hitl_approval.py ...                                          [ 52%]
tests/test_p0_batch_1_remediation.py ..........                          [ 68%]
tests/test_scenarios.py ...                                              [ 73%]
tests/test_tokenization.py .                                             [ 74%]
backend/tests/test_disambiguation_and_rule_edit.py ...                    [ 79%]
backend/tests/test_rules_e2e.py ........                                 [ 92%]
backend/tests/test_stp_e2e.py .....                                      [100%]

======================= 63 passed, 40 warnings in 4.82s =======================
```

---

## 4. Governance & Audit State Reconciled

- **P0 Items Scoped:** 8 Master IDs
- **P0 Items Remediated & Passing:** 8 Master IDs (100%)
- **Regressions Introduced:** 0
- **Unauthorized Changes to P1/Deferred Cloud Findings:** 0

P0 Batch 1 remediation is officially **COMPLETE**. Standing by for subsequent batch coordination per governance guidelines.
