# PeX — Pre-Reengineering Baseline & Recovery Checkpoint v1.0
## Forensic System State, Codebase Inventory & Recovery Baseline

**Document Identifier:** `PeX-BASELINE-PRE-REENG-001`  
**Version:** v1.0  
**Status:** FORENSIC BASELINE ESTABLISHED — RECOVERY CHECKPOINT CREATED  
**Operating Mode:** READ-ONLY / PRE-REENGINEERING (Zero Application Code Modifications)  
**Author:** Principal Enterprise Architect, Payment Domain Architect & Lead Engineer  
**Date:** October 6, 2026  
**Git Commit SHA:** `bb612f09e8ac2205f78c32a72d9a050035868821`  
**Git Tag:** `pex-pre-reengineering-20261006`  
**Recovery Branch:** `pex-pre-reengineering`  

---

> [!IMPORTANT]
> **THIS DOCUMENT DESCRIBES THE PRE-REENGINEERING CODEBASE (PHASE 1 OPERATIONAL BASELINE).**  
> **IT IS NOT THE TARGET ARCHITECTURE.**  
> It captures the exact, tested, and verified state of the PeX repository prior to initiating Phase 2A expansion (`PR-05`, `PR-08`, `DQ-05`).

---

## 1. Document Control & Baseline Purpose

This document establishes the official, immutable recovery baseline for the PeX (Payment Exception Resolution & Decisioning Platform) codebase prior to beginning Phase 2A re-engineering and multi-profile expansion.

### Purpose of Checkpoint:
1. Provide a verifiable, forensically audited snapshot of all source code, contracts, adapters, schemas, and test suites.
2. Guarantee exact reproducibility and recovery to the Phase 1 operational state.
3. Establish the definitive test regression baseline (142/142 tests passing).
4. Document the exact boundary between current implemented capabilities and the approved target architecture defined in `PeX_Phase2_Implementation_Contract_v1.3.md`.

---

## 2. Repository & Version Control State

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   GIT VERSION CONTROL METADATA                                         │
├───────────────────────────────────────┬────────────────────────────────────────────────────────────────┤
│ 1. Repository Root                    │ C:\Users\pawan\.gemini\antigravity\scratch\pex_platform        │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ 2. Active Branch                      │ main                                                           │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ 3. Verified Commit SHA                │ bb612f09e8ac2205f78c32a72d9a050035868821                       │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ 4. Commit Message                     │ docs: add comprehensive 41-profile STP feasibility and         │
│                                       │ evidence ingestion architecture assessment                     │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ 5. Commit Author & Date               │ PeX Platform Lead — Sun Oct 4 21:05:41 2026 -0400              │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ 6. Tracked Modifications              │ 0 modified files, 0 staged files (git diff is clean)           │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ 7. Untracked Artifacts & Slices       │ Phase 1 vertical slice implementation & test suite:            │
│                                       │ • backend/app/adapters/ (input_adapter.py, output_adapter.py)  │
│                                       │ • backend/app/schemas/ (authority, evidence, policy, resolution)│
│                                       │ • backend/app/services/ (sufficiency, resolution, authority,   │
│                                       │   evaluator, pr03_stp_pipeline)                                │
│                                       │ • tests/test_pr03_evidence_stp_e2e.py                          │
│                                       │ • Architecture baseline & contract specifications (v1.0-v1.3)  │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ 8. Immutable Baseline Tag             │ pex-pre-reengineering-20261006                                 │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ 9. Recovery Branch                    │ pex-pre-reengineering                                          │
└───────────────────────────────────────┴────────────────────────────────────────────────────────────────┘
```

---

## 3. Environment & Runtime Baseline

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    RUNTIME ENVIRONMENT SPECIFICATION                                   │
├───────────────────────────────────────┬────────────────────────────────────────────────────────────────┤
│ Operating System                      │ Windows 11 Enterprise (x86_64)                                 │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ Python Runtime                        │ Python 3.11.0 (`C:\Users\pawan\.gemini\antigravity\scratch\   │
│                                       │  pex_platform\.venv\Scripts\python.exe`)                       │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ Test Framework                        │ pytest 9.1.1                                                   │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ Web Framework                         │ FastAPI 0.141.1, Starlette 1.6.0, Uvicorn 0.52.4               │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ Data Validation & Modeling            │ Pydantic 2.13.4, Pydantic Core 2.46.4                          │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ Database & ORM                        │ SQLite 3 (embedded), SQLAlchemy 2.0.54                         │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ XML & Document Processing             │ lxml 6.1.2, python-docx 1.2.0, python-pptx 1.0.2, xlsxwriter    │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ HTTP & Networking                     │ httpx 0.28.1, httpcore 1.0.9, requests 2.34.2, anyio 4.14.2    │
└───────────────────────────────────────┴────────────────────────────────────────────────────────────────┘
```

### Complete Dependency Inventory (`pip list`):
- `annotated-doc==0.0.5`, `annotated-types==0.8.0`, `anyio==4.14.2`
- `certifi==2026.7.22`, `charset-normalizer==3.5.1`, `click==8.4.2`, `colorama==0.4.6`
- `fastapi==0.141.1`, `greenlet==3.5.6`, `h11==0.16.0`, `httpcore==1.0.9`, `httpx==0.28.1`
- `idna==3.19`, `iniconfig==2.3.0`, `lxml==6.1.2`, `packaging==26.3`, `pillow==12.3.0`
- `pluggy==1.6.0`, `pydantic==2.13.4`, `pydantic_core==2.46.4`, `Pygments==2.21.0`, `pytest==9.1.1`
- `python-docx==1.2.0`, `python-multipart==0.0.32`, `python-pptx==1.0.2`, `requests==2.34.2`
- `SQLAlchemy==2.0.54`, `starlette==1.6.0`, `typing_extensions==4.16.0`, `typing-inspection==0.4.4`
- `urllib3==2.7.0`, `uvicorn==0.52.4`, `xlsxwriter==3.2.9`

---

## 4. Test Suite Execution & Verification

### Test Command:
```powershell
.\.venv\Scripts\pytest -v
```

### Execution Summary:
- **Total Tests:** 142
- **Passed:** 142
- **Failed:** 0
- **Errors:** 0
- **Skipped:** 0
- **Warnings:** 3 (Deprecation warnings for Starlette `TestClient` and FastAPI `@app.on_event`)
- **Execution Time:** 24.30 seconds
- **Baseline Test Status:** **GREEN (100% PASSING)**

### Test Breakdown by Module:
```
+----+---------------------------------------------------------------+-------+--------+
| #  | Test Module Path                                              | Count | Status |
+----+---------------------------------------------------------------+-------+--------+
| 1  | tests/test_audit_trace.py                                     | 3     | PASSED |
| 2  | tests/test_audit_trail.py                                     | 5     | PASSED |
| 3  | tests/test_canonicalization.py                                | 11    | PASSED |
| 4  | tests/test_contracts.py                                       | 8     | PASSED |
| 5  | tests/test_functional_adversarial.py                          | 12    | PASSED |
| 6  | tests/test_hitl_approval.py                                   | 7     | PASSED |
| 7  | tests/test_p0_batch_1_remediation.py                          | 6     | PASSED |
| 8  | tests/test_p1_batch_2_remediation.py                          | 7     | PASSED |
| 9  | tests/test_p1_batch_3_remediation.py                          | 7     | PASSED |
| 10 | tests/test_p1_batch_4_remediation.py                          | 16    | PASSED |
| 11 | tests/test_pr03_evidence_stp_e2e.py                           | 31    | PASSED |
| 12 | tests/test_replit_readiness.py                                | 8     | PASSED |
| 13 | tests/test_scenarios.py                                       | 3     | PASSED |
| 14 | tests/test_tokenization.py                                    | 2     | PASSED |
| 15 | backend/tests/test_disambiguation_and_rule_edit.py            | 3     | PASSED |
| 16 | backend/tests/test_rules_e2e.py                               | 8     | PASSED |
| 17 | backend/tests/test_stp_e2e.py                                 | 5     | PASSED |
+----+---------------------------------------------------------------+-------+--------+
|    | TOTAL BASELINE TESTS                                          | 142   | 142/142|
+----+---------------------------------------------------------------+-------+--------+
```

---

## 5. Codebase Inventory

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              COMPONENT INVENTORY MATRIX                                                │
├───────────────────────────────┬───────────────────────────────────────────┬───────────────────┬──────────────┬─────────┤
│ Component Name                │ Source File Path                          │ Primary Purpose   │ Status       │ Phase 2 │
│                               │                                           │                   │              │ Reuse   │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ EvidenceContract Models       │ `backend/app/schemas/evidence_contract.py`│ Mandatory &       │ Fully Impl.  │ YES     │
│                               │                                           │ trust-tiered evid.│              │ (Core)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ ResolutionContract Models     │ `backend/app/schemas/resolution_contract.py`│ Candidate repair &│ Fully Impl.  │ YES     │
│                               │                                           │ uniqueness defs   │              │ (Core)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ AuthorityContract Models      │ `backend/app/schemas/authority_contract.py`│ Multi-level valid.│ Fully Impl.  │ YES     │
│                               │                                           │ & SoR attestation │              │ (Core)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ STPPolicyContract Models      │ `backend/app/schemas/policy_contract.py`  │ 8-predicate formula│ Fully Impl.  │ YES     │
│                               │                                           │ & bank constraints│              │ (Core)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ Canonical Schemas             │ `backend/app/schemas/canonical.py`        │ Exception records,│ Fully Impl.  │ YES     │
│                               │                                           │ payment fields    │              │ (Core)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ Sufficiency Engine            │ `backend/app/services/sufficiency_engine.py`│ Evaluates E_suff  │ Fully Impl.  │ YES     │
│                               │                                           │ freshness & tiers │              │ (Core)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ Resolution Engine             │ `backend/app/services/resolution_engine.py`│ Derives candidate │ Fully Impl.  │ YES     │
│                               │                                           │ & evaluates R_uniq│              │ (Core)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ Authority Validation Engine   │ `backend/app/services/authority_validation_engine.py`│ Evaluates V_det & │ Fully Impl.  │ YES     │
│                               │                                           │ V_auth conditions │              │ (Core)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ Evidence STP Evaluator        │ `backend/app/services/evidence_stp_evaluator.py`│ Computes 8-pred.  │ Fully Impl.  │ YES     │
│                               │                                           │ formula & decision│              │ (Core)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ PR-03 Pipeline Engine         │ `backend/app/services/pr03_stp_pipeline.py`│ End-to-end XML    │ Fully Impl.  │ YES     │
│                               │                                           │ structural repair │ (PR-03 slice)│ (Slice) │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ Folder Input Adapter          │ `backend/app/adapters/input_adapter.py`   │ Ingests error JSON│ Fully Impl.  │ YES     │
│                               │                                           │ & evidence dossier│              │ (Port)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ Folder Output Adapter         │ `backend/app/adapters/output_adapter.py`  │ Emits XML handoff │ Fully Impl.  │ YES     │
│                               │                                           │ & SHA-256 receipt │              │ (Port)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ Audit Service                 │ `backend/app/services/audit_service.py`   │ Linear SHA-256    │ Fully Impl.  │ YES     │
│                               │                                           │ provenance ledger │              │ (Core)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ Token Vault & Security        │ `backend/app/core/tokenization.py`        │ PII masking & HMAC│ Fully Impl.  │ YES     │
│                               │                                           │ tokenization      │              │ (Core)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ Approval Engine               │ `backend/app/services/approval_engine.py` │ Maker-Checker     │ Fully Impl.  │ YES     │
│                               │                                           │ dual-authorization│              │ (HITL)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ Rule Engine & ICD Staging     │ `backend/app/services/rule_engine.py`     │ Rule synthesis &  │ Fully Impl.  │ YES     │
│                               │ `backend/app/services/icd_staging_service.py`│ counterparties    │              │ (Legacy)│
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ Model Gateway                 │ `backend/app/services/model_gateway.py`   │ AI/LLM advisory   │ Fully Impl.  │ YES     │
│                               │                                           │ mock & Bedrock    │ (Advisory)   │ (Adv.)  │
├───────────────────────────────┼───────────────────────────────────────────┼───────────────────┼──────────────┼─────────┤
│ SQLite Repository             │ `backend/app/db/repository.py`            │ Case persistence  │ Fully Impl.  │ YES     │
│                               │ `backend/app/db/models.py`                │ & audit queries   │ (Embedded)   │ (DB)    │
└───────────────────────────────┴───────────────────────────────────────────┴───────────────────┴──────────────┴─────────┘
```

---

## 6. Current Capability Snapshot

### 6.1 Ingestion Mechanism
- **FolderInputAdapter:** Ingests payment error JSON files accompanied by a structured `evidence_dossier` JSON from designated file system watch folders.
- Validates inbound dossier schema, extracts individual evidence items, assigns Trust Tiers (Tier 1 Bank Authoritative $\to$ Tier 4 Historical), and checks evidence freshness timestamps against TTL.

### 6.2 Output & Handoff Mechanism
- **FolderOutputAdapter:** Emits repaired ISO 20022 XML payment payloads to structured output folders (`/output/repaired_payloads/`).
- Emits cryptographic execution receipts (`/output/audit_receipts/`) containing SHA-256 digests, predicate evaluations, and handoff timestamps.

### 6.3 Operational Profiles
- **`PR-03` (Malformed XML / Structural Corruption):** Fully operational end-to-end vertical slice. Capable of deterministic XML namespace correction, tag re-sequencing, and outer envelope restoration.
- **Other 40 Profiles:** Pre-reengineering baseline has legacy rule-engine coverage and classification, but lacks the dedicated Evidence-Driven STP pipelines scheduled for Phase 2.

### 6.4 STP Decisioning & Predicate Evaluation
- Computes the canonical 8-predicate formula:
  $$\mathbf{STP\_ELIGIBLE} = E_{\text{suff}} \wedge R_{\text{det}} \wedge R_{\text{uniq}} \wedge V_{\text{det}} \wedge V_{\text{auth}} \wedge P_{\text{bank}} \wedge C_{\text{comp}} \wedge X_{\text{pre}}$$
- Evaluates each predicate as a strict Boolean. Fails closed upon any `False` evaluation, routing the transaction to Maker-Checker worklists.

### 6.5 Cryptographic Audit & Provenance
- `AuditService` logs every lifecycle stage transition into an in-memory and SQLite-backed linear SHA-256 hash chain ($H_i = \text{SHA256}(H_{i-1} \parallel \text{event\_data})$).
- Verification endpoint detects any historical tampering or ledger corruption.

---

## 7. Current Baseline Characteristics

The following operational characteristics define the existing codebase and will be evolved during subsequent implementation phases:

1. **Folder-Based Adapter Model:** Current input and output ports operate via local/mounted directory structures rather than enterprise streaming message buses (Kafka/IBM MQ).
2. **Demo Configuration Defaults:** System loads baseline monetary limits (\$1M for PR-03, \$25k for BIC/IBAN) and demo clearing routes in local testing mode.
3. **Mock External Authorities:** SWIFTRef, CoP, and Fedwire directories operate via static dictionaries and mock adapters rather than real-time cloud API connectors.
4. **Advisory AI Isolation:** AI gateway is strictly decoupled from decision execution, operating purely in stub/mock mode during test runs with zero execution authority.
5. **Embedded Storage:** Persistence utilizes SQLite (`pex_enterprise.db`) with relational tables and JSON serialized fields rather than distributed enterprise databases.

---

## 8. Verified Pre-Reengineering Test Baseline

The test suite of 142 tests spans:
- **Core Canonicalization & Contracts:** 19 tests (`test_canonicalization.py`, `test_contracts.py`)
- **HITL Dual-Authorization & Tokenization:** 9 tests (`test_hitl_approval.py`, `test_tokenization.py`)
- **Audit & Cryptographic Ledger:** 8 tests (`test_audit_trace.py`, `test_audit_trail.py`)
- **Domain & Standards Remediation (Batches 1-4):** 36 tests (`test_p0_batch_1_remediation.py` through `test_p1_batch_4_remediation.py`)
- **PR-03 Evidence-Driven STP End-to-End Slice:** 31 tests (`test_pr03_evidence_stp_e2e.py` including happy path, 20 failure modes, and 11 adversarial challenges)
- **Replit & API Readiness:** 8 tests (`test_replit_readiness.py`)
- **Rule Engine & Fast-Lane STP:** 16 tests (`test_rules_e2e.py`, `test_stp_e2e.py`, `test_disambiguation_and_rule_edit.py`)
- **Scenario Tests:** 15 tests (`test_scenarios.py`, `test_functional_adversarial.py`)

---

## 9. Re-engineering Transition Boundary

The codebase is now fully baselined and positioned at the boundary of Phase 2A expansion:

```
[Phase 1 Baseline (PR-03 Vertical Slice)]  <-- CHECKPOINT CREATED HERE
                  │
                  ▼
[Phase 2A Expansion]
• PR-05: Corrupted Message Format (Governed Character & Encoding Pipeline)
• PR-08: Queue Processing Failure (DLQ Reset & Idempotency Lock Manager)
• DQ-05: Invalid Address Format (UPU S42 Postal Normalizer & Ambiguity Engine)
                  │
                  ▼
[Phase 2B & 2C Multi-Profile Rollout]
```

---

## 10. Final Baseline Confirmation

```
====================================================================================================
PRE-REENGINEERING BASELINE VERIFICATION SUMMARY:
• Working Tree: Evaluated & Factual Inventory Documented
• Baseline Tests: 142/142 PASSED (GREEN)
• Git Commit SHA: bb612f09e8ac2205f78c32a72d9a050035868821
• Git Tag: pex-pre-reengineering-20261006
• Application Code Modified During Baseline Creation: NO (0 lines)
• Baseline Classification: GREEN — BASELINE ESTABLISHED
====================================================================================================
```
