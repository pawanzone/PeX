# 07-uncertain-execution-and-outcomes.md — Uncertain Execution, Timeouts and Outcomes

**Document Status:** COMPLETE / EVIDENCE-AUDITED  
**Auditor Mode:** Objective External Review  
**Target Codebase:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Date of Audit:** October 2026  

---

## 1. Handling of Timeouts and Unknown Payment Status

### Blind-Retry Prevention and Duplicate Protection
In cross-border interbank payments (SWIFT CBPR+, Fedwire), an unacknowledged payment instruction represents severe financial risk: retrying an unconfirmed wire can result in duplicate settlement, overdrafts, and legal liability.

The codebase addresses this risk through two distinct layers:

1. **Idempotency Key Verification**:
   - Implemented in [`backend/app/services/action_executor.py:21-36`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/action_executor.py#L21-L36):
     ```python
     if idempotency_key and idempotency_key in repo.actions:
         existing = repo.actions[idempotency_key]
         existing_receipt = repo.receipts.get(existing.action_id)
         return True, "Idempotent response: action already settled.", existing, existing_receipt
     ```
   - Before executing any repair or handoff, the engine derives or checks an idempotency key `f"IDEMP-{case_id}-{approval_id}"`. If a handoff was previously attempted under this key, the engine refuses to re-dispatch and returns the existing record.
2. **In-Flight Lock Protection**:
   - Defined in [`backend/app/ports/idempotency_port.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/ports/idempotency_port.py) and implemented in [`backend/app/adapters/reference/reference_idempotency_adapter.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/adapters/reference/reference_idempotency_adapter.py).
   - Acquires a mutex lock (`LockStatus.ACQUIRED`) on the payment UETR for 300 seconds. Concurrent threads attempting to execute the same UETR are rejected (`LockStatus.REJECTED_CONCURRENT_LOCK`).

### Remediation of Unknown Execution State and Asynchronous Boundary (P0-1)
Under **P0 Remediation (P0-1)**, the fake synchronous settlement shortcut was eliminated:
- **Removal of Synthetic `ACK-SIM-` Receipts**: `action_executor.py` no longer generates simulated `ACK-SIM-` receipts or claims instant settlement.
- **`HANDED_TO_BANK` Boundary**: The execution path transitions cases to `HANDED_TO_BANK` (canonical string `"DISPATCHED"`) with status `AWAITING_BANK_ACK`.
- **New `STATUS_UNKNOWN` Stage**: Added to `LifecycleStage` to explicitly capture cases where bank clearing acknowledgment is delayed or times out.
- **Outbound Choke Point (`outbound_port.py`)**: All outbound dispatches flow through a single choke point supporting `SHADOW` (suppresses calls, sets `SHADOW_RECORDED`), `ASSISTED` (human gate), and `LIVE` (outbound handoff).

---

## 2. Returns, Recalls, Reconciliation Breaks and Trapped Funds

The platform models complex exception flows across Domain 5 (`SETTLEMENT_RETURNS`) in [`backend/app/schemas/canonical.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/schemas/canonical.py#L72-L80):

| Exception Scenario | Profile Code | What Exists in Code | Implementation Reality |
| :--- | :--- | :--- | :--- |
| **Payment Return** | `ST-01: RETURNED_PAYMENT` | [`canonicalizer.py:208`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/canonicalizer.py#L208) detects `"RETURN"` / `"RECALL"` narratives. Returns debtor refund recommendation. | `IMPLEMENTED` (Simulation path with synthetic reversal receipt). |
| **Account Closed** | `ST-02: ACCOUNT_CLOSED` | Queries `successor_account_registry` in [`icd_staging_service.py:50`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/icd_staging_service.py#L50) to remap closed accounts. | `PARTIAL` (Reads static JSON mapping table). |
| **Account Frozen** | `ST-03: BENEFICIARY_ACCOUNT_FROZEN` | Maps AC06 return code to general ledger suspense booking action. | `PARTIAL` (Routes to Risk/Suspense desk; fails automated test in fresh run). |
| **Reconciliation Break** | `ST-04: RECONCILIATION_BREAK` | Defined in taxonomy; intended to match general ledger statement breaks. | `STUB` (Profile enum exists; no ledger parsing algorithm in code). |
| **Settlement Failure** | `ST-05: SETTLEMENT_FAILURE` | Maps clearing rejection; schedules next-clearing-cycle resubmission. | `PARTIAL` (Static recommendation returned). |
| **Funds Trapped at Correspondent**| `ST-06: FUNDS_TRAPPED_AT_CORRESPONDENT`| Queries transit tracker; generates simulated camt.056 recall message payload. | `IMPLEMENTED` (Generates recall payload dictionary). |
| **Unmatched Credit** | `ST-07: UNMATCHED_CREDIT` | Matches inbound credit against accounts receivable. | `STUB` (Profile enum exists; returns generic fallback recommendation). |

---

## 3. Outcome Confirmation from Bank Systems: Real vs. Simulated

The architectural principle mandates: *"PeX prepares handoffs. Bank systems execute."* The table below details the remediated execution boundary:

| Capability | Real Implementation in Code | Simulated / Mock Implementation | Auditor Verdict |
| :--- | :--- | :--- | :--- |
| **Handoff Packaging** | Assembles `GovernedActionContract` with repaired fields, approver ID, and role. | None. Contract serialization is real. | `IMPLEMENTED` |
| **Outbound Choke Point** | `backend/app/services/outbound_port.py` governs all handoffs across SHADOW, ASSISTED, and LIVE modes. | In SHADOW, suppresses calls and records `SHADOW_RECORDED`. | `IMPLEMENTED (P0-4)` |
| **Bank Execution Acknowledgment**| Removed synthetic `ACK-SIM-` receipts. Status remains `AWAITING_BANK_ACK`. | Mock broker stub in unit tests. | `REMEDIATED (P0-1)` |
| **Settlement Execution Signal**| `POST /api/bank/outcome` receives HMAC-signed, idempotent bank callbacks to transition cases to `EXECUTED_CONFIRMED` or `SETTLED`. | Internal code strictly blocked from setting `SETTLED`. | `REMEDIATED (P0-1)` |

---

## 4. SWIFT and ISO 20022 Investigation Messages Inventory

The table below assesses which SWIFT and ISO 20022 investigation messages are parsed, generated, or ignored:

| Message Type | Message Name / Purpose | Parsed in Ingestion? | Generated in Handoff? | Ignored / Label Only | Code Evidence |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **pacs.008** | Customer Credit Transfer | **Yes** (JSON body mapped in `canonicalizer.py`) | No (Emits JSON dict, not XML) | Real JSON, No XML | [`canonicalizer.py:179`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/canonicalizer.py#L179) |
| **pacs.004** | Payment Return | **Partial** (Return codes extracted) | No | No XML handling | [`canonicalizer.py:40-52`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/canonicalizer.py#L40-L52) |
| **pacs.002** | Payment Status Report (ACK/NAK) | No | No | Label only | Referenced in comments, not parsed |
| **camt.056** | Payment Cancellation Request | **Partial** (`camt_code` string checked for Bank C) | No | No XML handling | [`canonicalizer.py:155`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/canonicalizer.py#L155) |
| **camt.029** | Resolution of Investigation | No | No | Ignored | Referenced in docs, zero code |
| **camt.026** | Unable to Apply (Inquiry) | No | No | Ignored | Referenced in docs, zero code |
| **camt.027** | Claim Non-Receipt | No | No | Ignored | Referenced in docs, zero code |
| **camt.054** | Bank-to-Customer Debit/Credit Notification | No | No | Ignored | Zero code |
| **SWIFT gpi Tracker**| Tracking UETR & intermediary transit | No | No | **MOCKED** | Canned status in `reference_transit_tracker_adapter.py` |

### Auditor Summary
PeX does **not contain an XML parsing or serialization engine** for W3C ISO 20022 schemas (`pacs.008.001.10`, `camt.056.001.08`). It operates entirely on **JSON representations** of payment data. Messages such as `camt.026`, `camt.027`, and `camt.029` exist only as descriptive strings in taxonomy documents and docstrings.
