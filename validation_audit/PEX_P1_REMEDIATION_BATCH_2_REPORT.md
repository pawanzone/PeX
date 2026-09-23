# PeX — P1 Remediation Batch 2 Report
## State Machine, Approval Governance & HITL Integrity

**Authoritative Baseline:** `validation_audit/PEX_MASTER_REMEDIATION_REGISTER_FINAL.md`  
**Platform Release Tag:** `v1.9.1`  
**Previous Baseline:** `v1.9.0` (commit `8d0a20b`)  
**Safety Checkpoint Tag:** `pex-pre-p1-batch2-20260923`  
**Execution Date:** September 23, 2026  
**Status:** **100% COMPLETE — 76 / 76 Tests Passing (0 Regressions)**

---

## 1. Executive Summary

P1 Remediation Batch 2 focused strictly on resolving state machine inconsistencies, human-in-the-loop (HITL) approval governance gaps, and audit logging redundancies across the PeX backend. 

All 5 targeted Master IDs (`MST-040`, `MST-041`, `MST-042`, `MST-043`, and `MST-011`) have been remediated in source code, verified with 13 new dedicated automated tests in `tests/test_p1_batch_2_remediation.py`, and validated across the entire 76-test suite with zero regressions.

---

## 2. Remediated Findings Matrix

| Master ID | Original Finding Ref | Category | Severity | Summary of Issue | Files Modified | Resolution Status |
|---|---|---|---|---|---|---|
| **`MST-040`** | `DEF-07` | State Machine | HIGH | Approval Allowed in `INVESTIGATING` State | `backend/app/services/approval_engine.py` | **REMEDIATED** |
| **`MST-041`** | `DEF-08` | Governance | HIGH | `MODIFY` Bypasses Dual Authorization | `backend/app/services/approval_engine.py` | **REMEDIATED** |
| **`MST-042`** | `DEF-09` | State Machine | HIGH | Ingestion Sets `PENDING_APPROVAL` (Bypasses Intake) | `backend/app/api/endpoints/events.py` | **REMEDIATED** |
| **`MST-043`** | `DEF-10` | Governance | HIGH | `check_can_approve` Ignores Monetary Limits | `backend/app/core/security.py`, `backend/app/services/approval_engine.py` | **REMEDIATED** |
| **`MST-011`** | `REV-02` / `AUD-02` | Audit Ledger | MEDIUM | Double Audit Logging on Approvals | `backend/app/api/endpoints/approvals.py` | **REMEDIATED** |

---

## 3. Detailed Technical Remediation

### 3.1 `MST-040` — Approval Allowed in `INVESTIGATING` State
* **Root Cause:** In `backend/app/services/approval_engine.py`, the state check previously accepted `[LifecycleStage.PENDING_APPROVAL, LifecycleStage.AWAITING_SECOND_APPROVAL, LifecycleStage.INVESTIGATING]`. This allowed premature approval execution while a case was still under investigation.
* **Remediation:** Removed `INVESTIGATING` from the allowed approval stages in `ApprovalEngine.process_approval_action`. Only `PENDING_APPROVAL` (Level 1) and `AWAITING_SECOND_APPROVAL` (Level 2 dual auth) are permitted for approval actions.
* **Code Change:**
  ```python
  allowed_stages = [
      LifecycleStage.PENDING_APPROVAL,
      LifecycleStage.PENDING_APPROVAL.value,
      LifecycleStage.AWAITING_SECOND_APPROVAL,
      LifecycleStage.AWAITING_SECOND_APPROVAL.value
  ]
  if current_status not in allowed_stages:
      return False, f"Case is in {current_status} state, not awaiting approval", None, current_status
  ```

---

### 3.2 `MST-041` — `MODIFY` Bypasses Dual Authorization
* **Root Cause:** In `backend/app/services/approval_engine.py`, submitting `ApprovalAction.MODIFY` previously set `next_stage = LifecycleStage.APPROVED` unconditionally, bypassing Level 2 dual authorization for high-value cases ($\ge \$250\text{k}$).
* **Remediation:** Unified `ApprovalAction.MODIFY` into the dual-authorization evaluation block alongside `APPROVE`, `CLEAR_FALSE_POSITIVE`, and `GRANT_KYC_WAIVER`. If `dual_auth` is required, `MODIFY` transitions Level 1 to `AWAITING_SECOND_APPROVAL` (`step_no = 1`) and requires a distinct officer for Level 2 (`step_no = 2`).
* **Code Change:**
  ```python
  if submission.action in [ApprovalAction.APPROVE, ApprovalAction.CLEAR_FALSE_POSITIVE, ApprovalAction.GRANT_KYC_WAIVER, ApprovalAction.MODIFY]:
      if current_status in [LifecycleStage.PENDING_APPROVAL, LifecycleStage.PENDING_APPROVAL.value]:
          if dual_auth:
              next_stage = LifecycleStage.AWAITING_SECOND_APPROVAL
              step_no = 1
          else:
              next_stage = LifecycleStage.APPROVED
              step_no = 1
      elif current_status in [LifecycleStage.AWAITING_SECOND_APPROVAL, LifecycleStage.AWAITING_SECOND_APPROVAL.value]:
          # Level 2 Dual Authorization: distinct officer validation
          ...
          next_stage = LifecycleStage.APPROVED
          step_no = 2
  ```

---

### 3.3 `MST-042` — Ingestion Sets `PENDING_APPROVAL`
* **Root Cause:** In `backend/app/api/endpoints/events.py`, raw bank event ingestion stored new cases with `"status": "PENDING_APPROVAL"`, prematurely advancing raw exceptions past the triage, investigation, and reasoning steps.
* **Remediation:** Changed initial status upon raw ingestion to `"INGESTED"` (matching `LifecycleStage.INGESTED`) and attached the canonical `domain` field from `exception.domain`.
* **Code Change:**
  ```python
  case_obj = {
      "case_id": exception.case_id,
      "payment_id": payment.payment_id,
      "uetr": payment.uetr,
      ...
      "queue": exception.assigned_queue,
      "domain": exception.domain.value if hasattr(exception.domain, "value") else str(exception.domain),
      "status": "INGESTED",
      "severity": exception.severity,
      ...
  }
  ```

---

### 3.4 `MST-043` — `check_can_approve` Ignores Monetary Limits
* **Root Cause:** In `backend/app/core/security.py`, `check_can_approve(role, amount, queue)` received `amount` but never evaluated it against the approver persona's `max_approval_amount` or role limit constants.
* **Remediation:**
  1. Defined `ROLE_MAX_APPROVAL_LIMITS` dictionary mapping roles to their maximum authorized amounts:
     - `OPERATOR`: $\$0.00$
     - `OPERATIONS_APPROVER`: $\$250,000.00$
     - `COMPLIANCE_APPROVER`: $\$5,000,000.00$
     - `RISK_APPROVER`: $\$10,000,000.00$
     - `ADMIN`: $\$10,000,000.00$
  2. Updated `check_can_approve` to inspect `persona.max_approval_amount` (with fallback to role limit) and return `False, "Approval limit exceeded: ..."` when `amount > max_limit`.
  3. Updated `ApprovalEngine.process_approval_action` to pass `user_id=approver.user_id` and `persona=approver` to `check_can_approve`.

---

### 3.5 `MST-011` — Double Audit Logging on Approvals
* **Root Cause:** When an approval was submitted via `POST /api/approvals/submit`, `approval_engine.process_approval_action` logged an audit event to `audit_service` (line 161), and `endpoints/approvals.py` immediately called `audit_service.log_event` a second time (line 32), creating duplicate consecutive audit blocks in the SHA-256 chain for every single approval.
* **Remediation:** Removed the redundant `audit_service.log_event` call from `backend/app/api/endpoints/approvals.py`. `approval_engine` remains the single, authoritative service logging state transitions to the cryptographic audit trail.

---

## 4. Test Verification & Regression Results

### 4.1 Dedicated Test Suite (`tests/test_p1_batch_2_remediation.py`)

| Test Name | Master ID Covered | Verification Scope | Status |
|---|---|---|---|
| `test_mst_040_approval_rejected_in_investigating` | `MST-040` | Rejection of approval in `INVESTIGATING` state | **PASSED** |
| `test_mst_040_approval_rejected_in_ingested` | `MST-040` | Rejection of approval in `INGESTED` state | **PASSED** |
| `test_mst_040_approval_accepted_in_pending_approval` | `MST-040` | Successful approval in `PENDING_APPROVAL` state | **PASSED** |
| `test_mst_041_modify_high_value_requires_dual_authorization` | `MST-041` | High-value `MODIFY` triggers L2 dual auth + distinct officer check | **PASSED** |
| `test_mst_041_modify_low_value_single_approval` | `MST-041` | Low-value `MODIFY` transitions directly to `APPROVED` | **PASSED** |
| `test_mst_042_ingestion_sets_ingested_status` | `MST-042` | Ingestion API sets status `INGESTED` and domain `DATA_QUALITY` | **PASSED** |
| `test_mst_043_operator_limit_zero` | `MST-043` | Operator ($0 limit) rejected for any approval | **PASSED** |
| `test_mst_043_operations_approver_limit_exceeded` | `MST-043` | Tier-1 Ops Approver rejected for $500k (> $250k limit) | **PASSED** |
| `test_mst_043_operations_approver_within_limit` | `MST-043` | Tier-1 Ops Approver authorized for $250k (<= $250k limit) | **PASSED** |
| `test_mst_043_compliance_approver_limit_exceeded` | `MST-043` | Compliance Approver rejected for $6M (> $5M limit) | **PASSED** |
| `test_mst_043_compliance_approver_within_limit` | `MST-043` | Compliance Approver authorized for $1M (<= $5M limit) | **PASSED** |
| `test_mst_043_approval_engine_enforces_limit_rejection` | `MST-043` | ApprovalEngine end-to-end rejects submission exceeding limit | **PASSED** |
| `test_mst_011_single_audit_event_logged_per_approval` | `MST-011` | Exactly one audit event logged in global ledger on approval API | **PASSED** |

### 4.2 Full Test Suite Summary

```
============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\pawan\.gemini\antigravity\scratch\pex_platform
configfile: pytest.ini

tests/test_audit_trace.py .                                              [  1%]
tests/test_audit_trail.py .......                                        [ 10%]
tests/test_canonicalization.py .                                         [ 11%]
tests/test_contracts.py ...                                              [ 15%]
tests/test_functional_adversarial.py ..................                  [ 39%]
tests/test_hitl_approval.py ...                                          [ 43%]
tests/test_p0_batch_1_remediation.py ..........                          [ 56%]
tests/test_p1_batch_2_remediation.py .............                       [ 73%]
tests/test_scenarios.py ...                                              [ 77%]
tests/test_tokenization.py .                                             [ 78%]
backend/tests/test_disambiguation_and_rule_edit.py ...                    [ 82%]
backend/tests/test_rules_e2e.py ........                                 [ 93%]
backend/tests/test_stp_e2e.py .....                                      [100%]

======================= 76 passed, 53 warnings in 6.71s =======================
```

---

## 5. Artifacts & Checkpoints

- **Pre-Change Git Safety Tag:** `pex-pre-p1-batch2-20260923`
- **Release Version Tag:** `v1.9.1`
- **Backup Archive:** `backups/rollback_checkpoint_p1_batch2_v1_9_1_20260923.zip`
- **Updated Inventory:** `VERSION_INVENTORY.md`
