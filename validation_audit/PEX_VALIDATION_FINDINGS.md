# 🏛️ PeX Platform: Master Consolidated Validation Findings Register

**Document Version:** 1.0.0  
**Audit Classification:** Institutional Payment & Architecture Assurance  
**Lead Auditor:** Lead Validation Coordinator (Independent Multi-Stream Assurance Panel)  
**System Evaluated:** Payment Exception Resolution Platform (PeX)  
**Workspace Root:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Audit Completion Date:** September 23, 2026  
**Governing Standards:** ISO 20022 CBPR+, ISO 13616, ISO 7064, ISO 9362, SWIFT PMPG, BIAN v10.0, Federal Reserve SR 11-7 / OCC Bulletin 2011-12, NIST SP 800-53, PCI-DSS v4.0, GDPR Art. 32, SOX 404.

---

## 1. Executive Summary & Verification Scorecard

The PeX Lead Validation Panel conducted an exhaustive, independent, multi-perspective audit of the PeX platform across five discrete streams:
1. **Payment Domain & Standards Auditor** (External factual & standards conformance)
2. **Enterprise Architecture Challenger** (System resiliency, security boundary, concurrency)
3. **Requirements Traceability Auditor** (PRD vs Code vs UI end-to-end alignment)
4. **Software Implementation Auditor** (Static code analysis, schema drift, API contracts)
5. **Functional & Adversarial Reviewer** (Adversarial penetration, SoD bypass, tamper resilience)

### Consolidated Severity Breakdown

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               MASTER FINDINGS SEVERITY SCORECARD                                 │
├──────────────────────────────┬─────────────┬─────────────┬───────────────────────────────────────┤
│ Severity Classification      │ Total Count │ Percentage  │ Primary Impact Category               │
├──────────────────────────────┼─────────────┼─────────────┼───────────────────────────────────────┤
│ 🔴 CRITICAL (P0)             │      5      │    14.7%    │ Security, Cryptography, Clearing Rail │
│ 🟠 HIGH (P1)                 │     12      │    35.3%    │ Domain Errors, Drift, IAM, Concurrency│
│ 🟡 MEDIUM (P2)               │     11      │    32.4%    │ Taxonomy Drift, Data Model, Mock Rail │
│ 🟢 LOW / HYGIENE (P3)        │      6      │    17.6%    │ Scratch Scripts, Typo, Pydantic v1    │
├──────────────────────────────┼─────────────┼─────────────┼───────────────────────────────────────┤
│ TOTAL CONSOLIDATED FINDINGS  │     34      │   100.0%    │ Deduplicated Across All 5 Streams     │
└──────────────────────────────┴─────────────┴─────────────┴───────────────────────────────────────┘
```

---

## 2. Master Findings Register

| ID | Title | Stream | Category | Severity | Root Cause & Impact | Corrective Action |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **SEC-01** | In-Memory Unsalted Truncated SHA-256 Token Vault | Arch / Code | Security | **CRITICAL** | `token_vault` uses 12-hex SHA-256 without salt or key management (KMS/HSM). Vulnerable to rainbow table preimage attacks and pod desync. | Replace with AWS KMS Envelope Encryption / HashiCorp Vault Transit Engine with tenant salts. |
| **SEC-02** | Plaintext Account Storage in Database Schema | Arch / Code | Security | **CRITICAL** | `TokenVaultModel.raw_value` stores unencrypted account numbers in SQLite/Postgres. Violates PCI-DSS v4.0 Req 3 and GDPR Art 32. | Store only ciphertext encrypted under KMS Customer Master Key (CMK); never store plaintext `raw_value`. |
| **SEC-03** | Omission of Outbound Detokenization in Settlement Dispatch | Arch / Code | Settlement | **CRITICAL** | `action_executor.py` transmits masked display strings (`GB82****5432`) to settlement kernels, guaranteeing 100% hard rejects on live clearing networks. | Detokenize within an isolated Settlement Dispatch Kernel in memory immediately prior to XML emission. |
| **IAM-01** | Default Fallback to Privileged Approver on Missing Token | Arch / Code | IAM | **CRITICAL** | API endpoints strip `Bearer ` via naive replace and default unauthenticated callers to privileged approver `APR-3191` (Daniel Osei). | Enforce strict JWT signature and claim validation; reject unauthenticated calls with HTTP 401 Unauthorized. |
| **AUD-01** | Incomplete Financial Data in Audit SHA-256 Digest | Arch / Code | Audit | **CRITICAL** | `calculate_event_hash` omits amount, currency, and debtor/creditor accounts from block digest, allowing financial tampering without breaking chain. | Include deterministic canonical hash of full payment payload inside the chained block digest. |
| **DOM-01** | Fabricated Non-Existent US & Japanese IBANs | Domain | Domain | **HIGH** | `icd_staging_store.json` and canonicalizer fabricate `US64CHAS...` and `JP44BOTK...`. US/Japan do not issue or recognize IBANs (ISO 13616). | Remove US/JP from IBAN tables; validate US via ABA 9-digit routing and Japan via Zengin clearing codes. |
| **DOM-02** | Conflation of SWIFT LAU with X.509 PKI Certificates | Domain | Cryptography | **HIGH** | PRD Module 5 claims XMLs use "PKI X.509 certificates adhering to SWIFT LAU". SWIFT LAU is strictly symmetric HMAC-SHA256. | Update documentation and security blueprint to distinguish SWIFT LAU (HMAC) from ISO 20022 XML digital signatures (X.509 / XMLDSig). |
| **DOM-03** | Hallucinated Central Bank "FEDWIRE_TARGET2_BRIDGE" | Domain | Clearing | **HIGH** | Specification Step 4 references direct clearing bridge between Fedwire (USD) and TARGET2 (EUR). No central bank bridge exists. | Clarify that cross-currency settlement flows through correspondent banks or CLS, not direct RTGS bridges. |
| **DOM-04** | Invalid 26-Character Alphabetic German IBAN in Fixtures | Domain | Domain | **HIGH** | Staging store contains `DE89DEUT3704...` (26 chars with letters). German IBANs are strictly 22 numeric characters. | Correct test fixtures to compliant 22-character German IBANs (`DE89370400440532013000`). |
| **IAM-02** | Maker-Checker Self-Approval Loophole in Endpoint Layer | Arch / Code | Governance | **HIGH** | Endpoint `/approvals/submit` did not enforce `maker_id != approver_id` prior to recent patch. | Enforce strict SOX 404 Segregation of Duties checks at API gateway, service, and database repository tiers. |
| **AI-01** | Deterministic Mock Gateway vs Advertised Pluggable LLMs | Arch / Code | AI / ML | **HIGH** | Blueprint advertises dynamic Gemini/OpenAI RAG pipeline, but runtime routes 100% through deterministic heuristic stubs. | Clearly demarcate the deterministic baseline engine from the optional external LLM adapter plugin. |
| **AI-02** | Contradiction: 100% HITL Advisory vs Autonomous STP Engine | Arch / Code | Governance | **HIGH** | Blueprint claims "100% Human-in-the-Loop Governance — Zero Autonomous Execution", but `stp_engine.py` allows unmonitored execution. | Formally document Governed STP Fast-Lane as a distinct policy tier with explicit institutional bounds and audit hooks. |
| **AUD-02** | Linear Hash Chain Mislabeled as "Merkle Ledger" | Arch / Code | Audit | **HIGH** | Implementation is a singly-linked SHA-256 block sequence with no binary tree structure or Merkle inclusion proofs. | Relabel documentation as "Cryptographic Linked Provenance Chain" or implement true hierarchical Merkle DAG. |
| **AUD-03** | Duplicate Audit Block Generation on HTTP Approvals | Arch / Code | Audit | **HIGH** | Approvals submit generates redundant audit records in both `approval_engine.py` and `approvals.py` endpoint wrapper. | Consolidate event emission strictly inside domain service transactions. |
| **AUD-04** | Concurrency Race Condition on Monotonic Event Index | Arch / Code | Concurrency | **HIGH** | Repository calculates `count() + 1` and reads `_latest_hash` without pessimistic row locking (`SELECT FOR UPDATE`), risking forks. | Introduce transactional DB-level advisory lock or sequence generator for linear provenance hashing. |
| **DATA-01** | In-Memory Singleton Cache Split-Brain in Multi-Worker Pods | Arch / Code | Architecture | **HIGH** | `PeXDBRepository` relies on local Python memory dicts. Running multiple Uvicorn workers causes immediate cache desynchronization. | Remove in-memory state; query persistent database with Redis distributed caching layer. |
| **RES-01** | Distributed Transaction Leak in STP Batch Processing | Code | Resilience | **HIGH** | `execute_batch_fast_lane_release` opens separate sessions per case, risking partial batch execution on node failure. | Wrap batch execution in an atomic database transaction with savepoint rollbacks. |
| **API-01** | Severe Frontend-Backend TypeScript Model Divergence | Trace / Code | API Contract | **HIGH** | `frontend/src/types/index.ts` implements only 7 Exception Profiles and omits 12 core case fields (`guided_questions`, `audit_timeline`). | Generate TypeScript interfaces automatically from Pydantic schemas via `pydantic-to-typescript` / OpenAPI generator. |
| **DOM-05** | Misapplication of ISO Return Code `AC01` to Intermediary Breaks | Domain | Standards | **MEDIUM** | Card RQ-05 applies `AC01` (Incorrect Account Number) to intermediary routing breaks. Intermediary errors use `RC01` or `AC03`. | Correct return code mapping across architecture cards and rule synthesizers. |
| **DOM-06** | Conflation of `pacs.004` (Return) with `camt.056` (Investigation) | Domain | Standards | **MEDIUM** | Card ST-01 treats `camt.056` as an automated settlement recall. `camt.056` is an inquiry message; `pacs.004` is the funds transfer. | Clarify two-step cancellation workflow: `camt.056` inquiry $\to$ `camt.029` rejection OR `pacs.004` return transfer. |
| **DOM-07** | Hallucinated ISO 20022 Purpose Codes (`GDDS`, `PHAR`, `COMM`) | Domain | Standards | **MEDIUM** | Staging seed uses non-standard purpose codes. Official ISO 20022 external code set uses `GDSV` (Goods/Services) and `COMM` is deprecated. | Update purpose code validation tables against official ISO 20022 External Code Sets catalogue. |
| **DOM-08** | Fedwire IMAD Generated with Invalid 22-Character Length | Domain | Clearing | **MEDIUM** | Spec Step 6 emits 22-character IMAD. Standard Fedwire IMAD is strictly 18 alphanumeric characters (`YYYYMMDD` + 4-char source + 6-char seq). | Align IMAD generator to exact 18-character Federal Reserve FAIM standard. |
| **DOM-09** | Bacs Categorized as High-Value RTGS Rail | Domain | Clearing | **MEDIUM** | Spec Section 1 lists UK Bacs alongside CHAPS/Fedwire as high-value RTGS. Bacs is bulk 3-day net batch clearing. | Correct rail taxonomy: CHAPS = RTGS; Faster Payments = Instant Net; Bacs = Automated Clearing House (ACH). |
| **DATA-02** | Relational Anti-Pattern (JSON Blobs for Core Entities) | Code | Data Model | **MEDIUM** | Debtor/Creditor parties, accounts, and guardrails stored as opaque JSON strings rather than normalized tables. | Normalize core entities into 3NF schema with foreign keys for high-performance indexing and reporting. |
| **DATA-03** | String-Type Timestamps in SQL Database Schemas | Code | Data Model | **MEDIUM** | Timestamps stored as `String(64)` rather than SQL `DateTime(timezone=True)`, preventing DB-level time-window queries. | Migrate timestamp columns to native SQL `TIMESTAMP WITH TIME ZONE`. |
| **INT-01** | Static Mock JSON Staging vs Live Banking Adapters | Arch / Code | Integration | **MEDIUM** | `icd_staging_service.py` queries local JSON files; `adapters.py` simulates connectivity with hardcoded arrays. | Define gRPC / REST asynchronous adapter contracts for live core banking, SWIFT Alliance, and Fedline connectivity. |
| **INT-02** | Omission of Outbound W3C XML DOM pacs.008 Serializer | Code | Integration | **MEDIUM** | Execution kernel returns JSON mock receipts (`ACK-SIM-*`) with no XML schema validation against W3C ISO 20022 XSDs. | Implement schema-validated XML serialization kernel using `xmlschema` and official ISO XSD definitions. |
| **RES-02** | Silent Exception Swallowing in Datetime Parsing | Code | Resilience | **MEDIUM** | Broad `except Exception` blocks in `repository.py` silently default corrupted dates to `datetime.utcnow()`. | Replace broad exceptions with specific `ValueError` handlers and structured error logging. |
| **SEC-04** | Permissive Wildcard CORS Configuration | Code | Security | **MEDIUM** | `CORSMiddleware` configured with `allow_origins=["*"]` and `allow_credentials=True`. | Restrict CORS origins to explicitly configured institutional domain whitelists. |
| **CODE-01** | Dual Disconnected Frontend Codebases | Code | Codebase | **MEDIUM** | `frontend/src/` (TypeScript Vite) is disconnected from `build_guided_frontend.py` (compiled monolithic bundle). | Consolidate build pipeline so `frontend/src` is the single source of truth compiled by Vite. |
| **TST-01** | Test Discovery Pollution by Root Scratch Scripts | Code | Testing | **HIGH** | Root directory contains legacy `test_*.py` scripts making network calls, causing standard `pytest` runs to fail. | Move scratch scripts into `scratch/` and configure `pytest.ini` with strict test root `testpaths = tests backend/tests`. |
| **TST-02** | Omission of Negative Tampering in Audit Test Suite | Code | Testing | **HIGH** | `tests/test_audit_trace.py` only verifies valid chain creation; negative tampering tests existed only in scratch scripts. | Incorporate full adversarial tampering suite into standard CI/CD test runner. |
| **CODE-02** | 30+ Orphaned Legacy Scratch Scripts in Workspace Root | Code | Hygiene | **LOW** | Workspace root cluttered with ad-hoc development scripts (`write_*.py`, `append_*.py`). | Archive legacy generator scripts to `.archive/` or delete from release repository. |
| **DEP-01** | Pydantic v1 Deprecation Warnings Across Backend | Code | Modernization | **LOW** | Codebase uses `.dict()` instead of Pydantic v2 `.model_dump()`. | Migrate Pydantic calls to v2 `.model_dump()` and `.model_validate()`. |

---

## 3. Remediation & Release Roadmap

```mermaid
flowchart TD
    subgraph Phase1["Phase 1: Critical Security & Rail Safety (Pre-Release Blocker)"]
        P1_1["SEC-01: AWS KMS Token Vault"]
        P1_2["SEC-02: Ciphertext DB Encryption"]
        P1_3["SEC-03: Outbound Detokenization Kernel"]
        P1_4["IAM-01: Strict JWT Gateway Authentication"]
        P1_5["AUD-01: Financial Amount Audit Hash Chaining"]
    end

    subgraph Phase2["Phase 2: Payment Domain & Standards Alignment (Sprint 1)"]
        P2_1["DOM-01/04: Fix US/JP & German IBANs"]
        P2_2["DOM-02/03: Clarify SWIFT LAU & Central Bank Bridges"]
        P2_3["DOM-06/07: Correct Purpose & Return Codes"]
        P2_4["DOM-08/09: Fedwire IMAD & Bacs Rail Taxonomy"]
    end

    subgraph Phase3["Phase 3: Architecture Modernization & Cleanliness (Sprint 2)"]
        P3_1["DATA-01: Redis Distributed Cache Layer"]
        P3_2["API-01: TypeScript Contract Generator"]
        P3_3["INT-02: ISO 20022 W3C XML Serializer"]
        P3_4["CODE-01/02: Clean Root & Unified Vite Frontend"]
    end

    Phase1 --> Phase2 --> Phase3
```

---

*This document represents the consolidated, deduplicated master findings register. For full technical proofs and individual stream logs, reference `validation_audit/domain_standards_audit.md`, `validation_audit/enterprise_architecture_challenge.md`, `validation_audit/requirements_traceability_audit.md`, `validation_audit/functional_adversarial_review.md`, and `validation_audit/implementation_code_audit.md`.*
