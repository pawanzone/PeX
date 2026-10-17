# 15-shadow-mode-readiness.md — Read-Only Shadow-Mode Readiness Assessment

**Document Status:** COMPLETE / EVIDENCE-AUDITED  
**Auditor Mode:** Objective External Review  
**Target Codebase:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Date of Audit:** October 2026  

---

## 1. Executive Summary & Readiness Scorecard

A "Shadow Mode" deployment allows a commercial bank to run PeX in **read-only parallel execution** against live or historical exception queues:
1. PeX ingests real exception events.
2. PeX gathers reference evidence and generates resolution recommendations.
3. PeX logs its recommendation to an immutable ledger without writing back to the bank payment hub.
4. PeX compares its recommendation with what the human operator actually authorized in the payment hub, computing an objective **Recommendation-vs-Human Agreement Rate**.

### Institutional Readiness Scorecard

| Assessment Dimension | Readiness Status | Code Implementation Reality | What Must Be Built | Effort |
| :--- | :---: | :--- | :--- | :---: |
| **Inbound Ingestion Pipeline** | **READY** | Folder watcher (`file_watcher.py`) and REST API (`events.py`) successfully ingest batch files. | None. File-drop or REST feed works today. | **S** (Done) |
| **Data Parsing & Schemas** | **NEEDS WORK** | Ingests JSON (`CanonicalE2EInput`). Zero W3C XML (`pacs.008`) or SWIFT FIN (`MT103`) parsing. | Bank must deploy a lightweight middleware to serialize payment hub exceptions to JSON. | **S** (1 wk) |
| **Deterministic Validation** | **READY** | Real ISO 7064 MOD-97-10 check math, ISO 13616 lengths, FAIM IMAD, and purpose codes. | None. Validates correctly in memory. | **S** (Done) |
| **Server-Enforced Shadow Guard** | **MISSING** | **Zero server-side flags prevent outbound execution**. No `SHADOW_MODE` variable exists in `config.py`. | Add `PEX_OPERATION_MODE=SHADOW` in `config.py` and hard-block `/api/actions/execute`. | **S** (3 days) |
| **Human Outcome Replay & Agreement** | **MISSING** | No schema or endpoint exists to ingest the human's eventual resolution or compute agreement %. | Add `HumanResolutionOutcome` schema, DB table, and agreement analytics endpoint. | **M** (2 wks) |
| **AI Recommendation Reasoning** | **NEEDS WORK** | `ModelGateway` returns canned mock responses with static token counts (120/45). | Connect live AWS Bedrock or Google Gemini API. | **M** (2 wks) |
| **Data Privacy & PII Handling** | **NEEDS WORK** | Cleartext customer names and IBANs are stored in SQLite database JSON blobs. | Enforce vault-backed tokenization before DB persistence. | **M** (2-3 wks)|
| **Enterprise Authentication / SSO** | **NEEDS WORK** | Uses hardcoded demo persona switcher and static JWT secret key. | Integrate bank IdP (Okta / Azure AD OAuth2). | **M** (2 wks) |

**Overall Feasibility Estimate for Read-Only Pilot**: **MEDIUM (M) — 3 to 4 Engineer Weeks** to achieve an institutional-grade, zero-risk shadow deployment against one real payment engine feed.

---

## 2. Forensic Audit: Does Any Code Guard Prevent Outbound Writes?

The marketing positioning asserts: *"PeX can safely run in shadow mode without touching bank systems."*

### Code Inspection Finding: Zero Shadow Guards Exist
- **Configuration Check**: Inspected [`backend/app/config.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/config.py). There is **no configuration variable** named `SHADOW_MODE`, `PEX_MODE`, `READ_ONLY`, or `DRY_RUN`.
- **Action Execution Check**: Inspected [`backend/app/services/action_executor.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/action_executor.py#L15-L60). `execute_governed_action()` checks only if the case is `APPROVED` and whether the idempotency key was previously used. It does **not** inspect any operational mode flag.
- **Proof of Vulnerability**: If a user in the UI clicks "Authorize & Dispatch" or if `/api/stp/batch-release` is invoked, the platform executes the action contract immediately. While outbound delivery in code today is directed to an in-memory mock (`"SIMULATED_BANK_PAYMENT_HUB"`), **if a live payment hub adapter were plugged in, PeX would dispatch real writes without any safety lock!**

### Required Server-Side Guard Fix
To guarantee zero outbound writes during a pilot, the following guard must be implemented in `backend/app/services/action_executor.py`:
```python
if settings.OPERATION_MODE == "SHADOW":
    audit_service.log_event(stage="SHADOW_HOLD", details="Outbound dispatch suppressed under READ_ONLY shadow mode.")
    return True, "Shadow mode active: recommendation recorded; outbound dispatch suppressed.", None, None
```

---

## 3. Minimum Viable Input (MVI) Contract for a Bank Pilot

To launch a 30-day shadow pilot with a commercial bank, the bank does **not** need to install complex software or grant write access to core systems. The bank only needs to drop a daily JSON batch file into an SFTP directory.

### The Minimum Viable Input JSON Schema
```json
{
  "batch_id": "PILOT-BATCH-20261017-001",
  "source_system": "FINACLE_PAYMENT_HUB",
  "generated_at": "2026-10-17T08:00:00Z",
  "records": [
    {
      "exception_id": "EXC-2026-0001",
      "profile_code": "INVALID_IBAN",
      "domain": "DATA_QUALITY",
      "payment_info": {
        "payment_id": "PMT-882910",
        "uetr": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
        "instruction_id": "TRN-2026-001",
        "amount": 18500.00,
        "currency": "GBP",
        "payment_rail": "SWIFT_CBPR+",
        "debtor_name": "Apex Global Treasury",
        "debtor_account": "GB82WEST12345698765432",
        "creditor_name": "HarborView Supplier Ltd",
        "creditor_account": "GB82WEST12345698765423",
        "creditor_bic": "WESTGB2L"
      },
      "bank_supplied_evidence": {
        "core_dda_account": "GB82WEST12345698765432",
        "verified_iban": "GB82WEST12345698765432",
        "ssi_directory_account": "GB82WEST12345698765432",
        "contradictory_evidence_flag": false
      },
      "historical_human_resolution": {
        "operator_id": "OP-1001",
        "action_taken": "SUBSTITUTE_FIELD",
        "repaired_value": "GB82WEST12345698765432",
        "final_status": "RELEASED",
        "resolved_at": "2026-10-17T08:24:12Z"
      }
    }
  ]
}
```

---

## 4. Agreement Metric Calculation Engine (The Missing Capability)

In code today, the agreement metrics shown in executive dashboards are **seeded/hardcoded**. To make shadow mode functional, PeX must introduce a deterministic reconciliation engine comparing PeX recommendations against the bank's historical human resolution.

### Proposed Agreement Logic Formulation
For each exception record $i$:
1. **Decision Agreement ($A_{dec}$)**: Did PeX recommend the same high-level action as the human operator (e.g. `REPAIR` vs `REJECT` vs `RETURN`)?
2. **Value Agreement ($A_{val}$)**: When repairing a field (e.g. IBAN), does PeX's candidate value match the human operator's repaired value exactly?
3. **Safety Agreement ($A_{safe}$)**: Did PeX correctly fail closed on cases where the human operator initiated an investigation or where evidence was contradictory?

$$\text{Agreement Rate} = \frac{\sum_{i=1}^{N} (A_{dec} \land A_{val})}{N_{\text{actionable}}} \times 100\%$$

---

## 5. Bank Infosec & Data Privacy Pilot Requirements

Before connecting a read-only exception feed, a bank's Information Security and Data Protection team will evaluate:

1. **Zero-PII Boundary**:
   - *Current Reality*: Canonical payment objects store cleartext debtor/creditor names and account numbers.
   - *Required for Pilot*: The inbound adapter must tokenize all PII strings into deterministic surrogate keys (`TOK-PARTY-1234`) before writing to the database, ensuring zero cleartext PII is persisted on disk or transmitted to AI models.
2. **Data Retention & Deletion**:
   - A configurable TTL purging routine (`scripts/purge_pilot_data.py`) must be provided to wipe all pilot cases and audit logs upon pilot completion.
3. **Network Boundary**:
   - PeX can be packaged as a single self-contained container (Docker / Podman) running entirely inside the bank's VPC / air-gapped subnet without requiring any outbound Internet connectivity if running in local rule/model mode.
