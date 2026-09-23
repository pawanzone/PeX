# PeX — 20-Step Deterministic Replit Walkthrough & Demo Script

**End-to-End Payment Exception Resolution Lifecycle Demonstration**  
**Version:** `1.0.0` (Aligned with Release `v1.9.4`)  
**Date:** September 23, 2026  

---

## 1. Overview & Demonstration Objectives

This script provides an exact, deterministic, 20-step walkthrough demonstrating the complete PeX exception resolution lifecycle inside Replit or any local development environment.

It can be executed:
- **Interactively via the Replit Webview UI** (http://localhost:8000/)
- **Programmatically via cURL / REST API**
- **Automated via Pytest** (`pytest tests/test_replit_readiness.py`)

---

## 2. 20-Step Walkthrough Matrix

```
+--------------------------------------------------------------------------------------------------+
| PHASE 1: INGESTION & DIAGNOSTICS (Steps 1 - 5)                                                   |
| 1. System Health Check    2. Operator Auth & SoD    3. Worklist Discovery                        |
| 4. Bank Event Ingestion   5. Case State Validation                                               |
+--------------------------------------------------------------------------------------------------+
| PHASE 2: EVIDENCE ASSEMBLY & AI REASONING (Steps 6 - 11)                                         |
| 6. ICD Clearing Lookup    7. RTGS Cutoff Status     8. AI Repair Context Assembly                |
| 9. Zero-PII Tokenization  10. Recommendation Check  11. Multi-Hypothesis Disambiguation          |
+--------------------------------------------------------------------------------------------------+
| PHASE 3: GOVERNANCE & MAKER-CHECKER APPROVALS (Steps 12 - 17)                                    |
| 12. Policy AST Matching   13. STP Fast-Lane Check   14. Advance to Pending Approval              |
| 15. SoD Self-Approval Blk 16. Level 1 Ops Approval  17. Level 2 Dual-Auth Sign-off (if >$250k)   |
+--------------------------------------------------------------------------------------------------+
| PHASE 4: EXECUTION & AUDIT PROVENANCE (Steps 18 - 20)                                            |
| 18. Governed Dispatch     19. Bank Delivery Receipt 20. Cryptographic Audit Seal Verification    |
+--------------------------------------------------------------------------------------------------+
```

---

## 3. Step-by-Step Execution Guide

### Step 1: System Health & Database Diagnostics
Check that the unified ASGI engine, SQLite relational database, and Model Gateway are healthy.
```bash
curl -s http://localhost:8000/api/health
```
- **Validation:** Response returns `status: "healthy"`, `total_cases_loaded: 233`, `is_sqlite: true`, `model_gateway.mode: "mock"`.

---

### Step 2: Persona Authentication & Entitlements Introspection
Inspect the available role personas and Maker-Checker monetary approval limits.
```bash
curl -s http://localhost:8000/api/auth/personas
```
- **Validation:** 
  - `OP-9012` (Payment Analyst - Maker): Max Approval Limit = `$0.00`
  - `APR-3191` (Operations Approver - Level 1 Checker): Max Approval Limit = `$250,000.00`
  - `CMP-4401` (Compliance Approver - Level 2 Checker): Max Approval Limit = `$5,000,000.00`

---

### Step 3: Worklist Discovery & Queue Filtering
Query open payment exception cases in the `DATA_QUALITY` domain queue.
```bash
curl -s "http://localhost:8000/api/cases?queue=DATA_QUALITY&status=INGESTED"
```
- **Validation:** Returns list of pending cases with BIAN domain tags and SLA timers.

---

### Step 4: Ingest Inbound Bank Exception Event
Ingest a raw payment rejection event (`pacs.008` rejection due to corrupted German IBAN check digits).
```bash
curl -s -X POST http://localhost:8000/api/events/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "EVT-REPLIT-DEMO-001",
    "event_type": "PAYMENT_REJECTED",
    "source_system": "SWIFT_GATEWAY",
    "raw_payload": {
      "uetr": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "amount": 185000.00,
      "currency": "EUR",
      "debtor_name": "Atlas Industrial Logistics",
      "debtor_account": "DE89370400440532013000",
      "creditor_name": "Bavaria Motoren Werke AG",
      "creditor_iban": "DE89370400440532013000",
      "error_code": "AC01",
      "error_description": "Incorrect Account / Check Digits Failed"
    }
  }'
```
- **Validation:** Returns `success: true` with newly assigned `case_id` (e.g. `PEX-EVT-REPLIT-DEMO-001`) and initial `status: "INGESTED"`.

---

### Step 5: Verify Case Lifecycle Initialization
Verify that the case is persisted with proper domain classification and zero premature approval status (`MST-042`).
```bash
curl -s http://localhost:8000/api/cases/PEX-EVT-REPLIT-DEMO-001
```
- **Validation:** `case.status == "INGESTED"`, `case.domain == "DATA_QUALITY"`, `case.profile == "INVALID_IBAN"`.

---

### Step 6: Query Staging Clearing Directory (ICD Adapters)
Query external Standing Settlement Instructions (SSI) and national clearing directories.
```bash
curl -s "http://localhost:8000/api/adapters/ssi?counterparty=Bavaria%20Motoren%20Werke%20AG"
```
- **Validation:** Returns verified BIC `DBEUMM21XXX`, registered national clearing identifier `37040044`, and verified beneficiary account.

---

### Step 7: Introspect RTGS Cutoff Status
Query Real-Time Gross Settlement (RTGS) cutoffs for Target2 (EUR) and Fedwire (USD).
```bash
curl -s http://localhost:8000/api/adapters/cutoffs
```
- **Validation:** Returns Target2 clearing window status, remaining time to cutoff, and priority queue classification.

---

### Step 8: Trigger AI Context Assembly & Algorithmic Repair
Run the Maker Analyst AI repair workflow.
```bash
curl -s -X POST "http://localhost:8000/api/cases/PEX-EVT-REPLIT-DEMO-001/run-ai-repair?analyst_id=OP-9012"
```
- **Validation:** 
  - Gathers 90-day transaction history.
  - Queries SWIFT directory and Bundesbank bankleitzahl registry.
  - Computes ISO 7064 MOD-97-10 check digits.
  - Returns `recommendation.action_type: "REPAIR_AND_RELEASE"` with `confidence_score >= 0.95`.

---

### Step 9: Zero-PII Context Verification
Inspect the tokenization boundary to confirm zero customer PII was exposed during reasoning.
```bash
curl -s http://localhost:8000/api/cases/PEX-EVT-REPLIT-DEMO-001/ai-context
```
- **Validation:** Debtor and Creditor names and account numbers are replaced with tokens (`TOK_IBAN_...`, `TOK_PTY_...`).

---

### Step 10: Recommendation & Proposed Changes Inspection
Review the AI recommendation details and proposed payment correction patch.
```bash
curl -s http://localhost:8000/api/cases/PEX-EVT-REPLIT-DEMO-001
```
- **Validation:** `recommendation.proposed_changes` contains the exact field path `creditor_party.account_number` and the mathematically validated replacement IBAN.

---

### Step 11: Multi-Hypothesis Disambiguation Review
Inspect the multi-hypothesis elimination matrix generated by the AI Reasoner.
- **Validation:** 
  - Hypothesis A (Correct German Bankleitzahl): Validated & Selected (98% confidence).
  - Hypothesis B (Cross-Border SWIFT Routing): Disqualified (Domestic SEPA route confirmed).
  - Hypothesis C (Account Closed): Disqualified (Active ledger standing verified).

---

### Step 12: Policy-as-Code Rule Matching
Evaluate the proposed repair against active organizational Policy-as-Code AST rules.
```bash
curl -s http://localhost:8000/api/rules
```
- **Validation:** Matches Rule `RULE-DQ-001` (Automated IBAN Check-Digit Repair under BIAN Data Quality playbook).

---

### Step 13: Straight-Through Processing (STP) Fast-Lane Evaluation
Check if the case qualifies for zero-touch STP execution or requires human sign-off.
```bash
curl -s http://localhost:8000/api/stp/evaluate/PEX-EVT-REPLIT-DEMO-001
```
- **Validation:** Amount `$185,000.00` exceeds autonomous threshold ($10,000), requiring Maker-Checker human sign-off.

---

### Step 14: Advance Case to `PENDING_APPROVAL`
The Analyst completes investigation and moves the case to the Approvals Desk.
- **Validation:** Case transitions from `RECOMMENDED` to `PENDING_APPROVAL`.

---

### Step 15: Segregation of Duties (SoD) Violation Test
Attempt approval using the Maker Analyst's persona (`OP-9012`).
```bash
curl -s -X POST http://localhost:8000/api/approvals/submit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pex-token-OP-9012" \
  -d '{
    "case_id": "PEX-EVT-REPLIT-DEMO-001",
    "action": "APPROVE",
    "comments": "Attempting self-approval."
  }'
```
- **Validation:** HTTP 403 Forbidden: `"Operator OP-9012 cannot approve cases. Monetary approval limit is $0.00"`.

---

### Step 16: Level 1 Operations Approver Sign-off
Submit authorized approval using Operations Approver persona (`APR-3191`).
```bash
curl -s -X POST http://localhost:8000/api/approvals/submit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pex-token-APR-3191" \
  -d '{
    "case_id": "PEX-EVT-REPLIT-DEMO-001",
    "action": "APPROVE",
    "comments": "Verified beneficiary standing against Bundesbank BLZ directory. Approved for clearing release."
  }'
```
- **Validation:** HTTP 200 OK: `next_stage: "APPROVED"`, `approved_by: "APR-3191"`.

---

### Step 17: Dual-Authorization Gating (if >$250,000)
For transactions exceeding `$250,000.00`, verify that Level 1 transitions to `AWAITING_SECOND_APPROVAL` and requires Compliance Approver (`CMP-4401`) sign-off before release.
- **Validation:** Enforced deterministically by `ApprovalEngine.submit_approval` (`MST-041`).

---

### Step 18: Governed Action Execution & Dispatch
Execute the approved repair and dispatch the corrected `pacs.008` message to the clearing rail.
```bash
curl -s -X POST http://localhost:8000/api/actions/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer pex-token-APR-3191" \
  -d '{
    "case_id": "PEX-EVT-REPLIT-DEMO-001",
    "idempotency_key": "IDEMP-DEMO-185K-001"
  }'
```
- **Validation:** HTTP 200 OK: `success: true`, `status: "SETTLED"`, `delivery_receipt.bank_ack_reference: "ACK-SIM-..."`.

---

### Step 19: Clearing Delivery Receipt & IMAD/UETR Verification
Verify the terminal clearing delivery receipt and bank acknowledgement.
```bash
curl -s http://localhost:8000/api/cases/PEX-EVT-REPLIT-DEMO-001
```
- **Validation:** `case.status == "SETTLED"`, `case.settlement_timestamp` recorded, delivery receipt stored.

---

### Step 20: Cryptographic Audit Trail & Merkle Chain Verification
Inspect the complete tamper-evident audit timeline for the case.
```bash
curl -s http://localhost:8000/api/audit/cases/PEX-EVT-REPLIT-DEMO-001
```
- **Validation:** 
  - Chronological chain of all 20 lifecycle steps.
  - SHA-256 Merkle-like provenance hash linking each step to the previous step.
  - Zero tamper warnings (`is_valid_chain: true`).
