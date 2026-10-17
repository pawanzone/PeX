# 01-prd-as-built.md — PRD Reconstructed from the Code

**Document Status:** COMPLETE / EVIDENCE-AUDITED  
**Auditor Mode:** Objective External Review  
**Target Codebase:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Date of Audit:** October 2026  

---

## 1. Problem Statement and Target Users (Reconstructed from Code)

### Reconstructed Problem Statement
Commercial banks processing high-volume cross-border and domestic payments (SWIFT CBPR+, Fedwire, CHAPS, SEPA) experience exception rates between 2% and 8%. When a payment fails due to syntax errors, invalid routing, missing beneficiary data, sanctions homonyms, or liquidity constraints:
1. It falls out of straight-through processing (STP) into fragmented operator queues.
2. Payment operators manually cross-reference 5+ internal bank systems (Core DDA, Standing Settlement Instructions [SSI], SWIFT Ref directory, OFAC sanctions filters, general ledger).
3. Operators propose manual repairs in the payment hub, requiring manual second-line approval (Maker-Checker).
4. Incident handoffs between operations, compliance, and treasury are uncoordinated, leading to clearing cutoff breaches, regulatory penalties, and counterparty inquiry claims.

PeX is designed as a **vendor-neutral exception resolution layer** that sits alongside existing payment hubs (Finacle, Temenos, ACI, Volante, Pega, Swift Alliance). It receives exception events, gathers reference evidence, proposes validated repairs, enforces bank policy, routes to human approvers via role-gated desks, and prepares outbound handoff instructions.

### Target Personas & Users (Implied by Code)
- **Payment Operations Analyst (Maker)**: Triage exceptions, inspect AI-recommended repairs and 5-step validation proofs, modify proposed values, and submit for second-eye review.
- **Operations Approver (Checker)**: Verify Maker repairs, review anomaly guardrails, and authorize outbound handoff within monetary limits ($250,000 USD).
- **Financial Crime Compliance Officer**: Review sanctions entity homonyms, PEP alerts, and AML holds; execute false-positive clearances or mandate SAR filing.
- **Treasury / Risk Approver**: Authorize liquidity overrides, nostro rebalancing handoffs, and transactions exceeding standard operations limits ($250,000 to $10,000,000 USD).
- **Platform Governance / Auditor**: Inspect immutable provenance hash chains, SLA performance, and STP eligibility telemetry.

---

## 2. Personas and Roles Implemented in Code

The platform defines 5 formal user roles and 9 distinct demo personas:

### User Roles Schema (`backend/app/schemas/approval.py`, lines 10-15)
```python
class UserRole(str, Enum):
    OPERATOR = "OPERATOR"
    OPERATIONS_APPROVER = "OPERATIONS_APPROVER"
    COMPLIANCE_APPROVER = "COMPLIANCE_APPROVER"
    RISK_APPROVER = "RISK_APPROVER"
    ADMIN = "ADMIN"
```

### Personas and Enforcement Inventory (`backend/app/core/security.py`, lines 8-95)

| Persona ID | Name | Role String | Department | Approval Limit (USD) | Code Enforcement Point |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `OP-9012` | Priya Nair | `OPERATOR` | Payment Repair Operations | **$0.00** | `security.py:73`: `"Operators cannot approve repairs (Maker-Checker policy violation)."` |
| `OP-1001` | Priya Nair | `OPERATOR` | Payment Repair Operations | **$0.00** | Identical operator restriction. |
| `OP-9013` | Amina Okafor | `OPERATOR` | Triage & Investigation | **$0.00** | Identical operator restriction. |
| `OP-8472` | Amina Okafor | `OPERATOR` | Triage & Investigation | **$0.00** | Identical operator restriction (`is_demo_active=True`). |
| `APR-3191` | Daniel Osei | `OPERATIONS_APPROVER` | Payment Exceptions | **$250,000.00** | `security.py:84-86`: Blocked if `amount > 250000.0`. Blocked from Compliance queue. |
| `CMP-4420` | Marisol Vega | `COMPLIANCE_APPROVER`| Financial Crime Compliance| **$5,000,000.00** | `security.py:76-77`: Authorized to clear Compliance queue exceptions. |
| `CMP-5502` | Marisol Vega | `COMPLIANCE_APPROVER`| Financial Crime Compliance| **$5,000,000.00** | Identical compliance authorization. |
| `RSK-7714` | Kenji Watanabe| `RISK_APPROVER` | Enterprise Risk Mgmt | **$10,000,000.00**| Authorized for risk/treasury overrides and dual-authorizations up to $10M. |
| `ADM-0001` | Alex Whitfield | `ADMIN` | Platform Governance | **$10,000,000.00**| Full administrative authority across all queues and limits. |

### Segregation of Duties (Maker-Checker) Enforcement Finding
- **What is enforced**: An `OPERATOR` role cannot submit an approval action (`check_can_approve` returns `False`). Monetary limits and queue restrictions are strictly evaluated.
- **Critical Enforcement Gap**: The backend **fails to enforce Maker-Checker identity separation**. `check_can_approve` does not inspect whether `user_id == case.maker_id`. In the current UI and API, an operator who creates or modifies a repair under persona `OP-9012` can switch persona to `APR-3191` and approve their own submission. The backend checks caller role, not transaction maker identity (`backend/app/core/security.py`, lines 71-88).

---

## 3. Capabilities Inventory (As Built)

Every capability is labeled with exactly one status: `IMPLEMENTED`, `PARTIAL`, `MOCKED`, `STUB`, or `NOT PRESENT`.

| Capability | Status | Evidence (File & Line / Test) | Architectural Notes |
| :--- | :--- | :--- | :--- |
| **Inbound Drop-Folder Ingestion** | `IMPLEMENTED` | `backend/app/services/file_watcher.py:1-620`<br>`tests/wave0b/test_wave0b_foundational.py` | Background watcher detects `.json` batch files, canonicalizes records, runs validation predicates, archives input, writes output reconciliation. |
| **REST API Event Ingestion** | `IMPLEMENTED` | `backend/app/api/endpoints/events.py:18-35`<br>`tests/contracts/test_wave0a_contracts.py` | Receives raw heterogeneous bank payloads (`RawBankEvent`) via HTTP POST `/api/events/ingest`. |
| **Streaming Queue Ingestion (Kafka/MQ)** | `MOCKED` | `backend/app/adapters/reference/reference_message_broker_adapter.py:1-75` | Reference adapter implements `StreamingMessageBrokerPort` using in-memory Python `collections.deque`. Zero external broker SDKs. |
| **Heterogeneous Format Canonicalization** | `IMPLEMENTED` | `backend/app/services/canonicalizer.py:118-297`<br>`tests/test_canonicalization.py` | Maps payloads from `BANK_A` (proprietary), `BANK_B` (ISO body/header), and `BANK_C` (camt.056) into `CanonicalPayment` and `CanonicalException`. |
| **41-Profile BIAN Exception Taxonomy** | `IMPLEMENTED` | `backend/app/schemas/canonical.py:29-83`<br>`tests/wave1/`, `tests/wave2/`, `tests/wave3/` | 41 profiles defined across 5 domains: Data Quality (9), Processing (9), Compliance (8), Treasury (8), Settlement/Returns (7). |
| **Deterministic MOD-97 Checksum Validator** | `IMPLEMENTED` | `backend/app/services/canonicalizer.py:54-72`<br>`tests/test_canonicalization.py:25-60` | Full mathematical ISO 7064 MOD-97-10 implementation (`int(num_str) % 97 == 1`). |
| **ISO 13616 IBAN Structure Validation** | `IMPLEMENTED` | `backend/app/services/canonicalizer.py:73-100`<br>`tests/contracts/test_wave0a_contracts.py` | Validates national length registry for 50+ countries, non-IBAN exclusions (US, JP, SG), and country BBAN rules (DE numeric, GB format). |
| **Fedwire FAIM IMAD Validator** | `IMPLEMENTED` | `backend/app/services/canonicalizer.py:101-110` | Validates Federal Reserve 18-character FAIM syntax (`YYYYMMDD + Source + Sequence`). |
| **ISO 20022 Purpose Code Validation** | `IMPLEMENTED` | `backend/app/services/canonicalizer.py:111-116` | Validates 4-character codes against official ISO `ExternalPurpose1Code` set. |
| **Bank Policy Rule Evaluation Engine** | `IMPLEMENTED` | `backend/app/services/rule_engine.py:1-250`<br>`tests/test_rules_engine.py` | Evaluates dynamic policy rules (e.g. `RULE-AUTH-001`, `RULE-SANCTION-HOLD`) with JSON logic conditions. |
| **Autonomous STP Fast-Lane Engine** | `PARTIAL` | `backend/app/services/stp_engine.py:1-650`<br>`backend/app/services/file_watcher.py:574-577` | Real logic evaluates 8 deterministic gates; however, `file_watcher.py` (lines 574-575) directly sets `status = SETTLED` internally, violating the rule that PeX never settles payments. |
| **Reference Evidence & Directory Lookups** | `MOCKED` | `backend/app/services/icd_staging_service.py:1-66`<br>`backend/app/data/icd_staging_store.json` | Lookups for Fedwire ABA, SWIFT BIC, Counterparty SSI, and OFAC homonyms query a static JSON file on disk. Zero live directory APIs. |
| **AI / LLM Reasoning Gateway** | `MOCKED` | `backend/app/services/model_gateway.py:1-92`<br>`backend/app/services/data_loader.py:62-180` | `model_gateway.py` does not invoke Gemini, OpenAI, or Bedrock. It returns canned responses with hard-coded token counts (`prompt_tokens=120`, `completion_tokens=45`). |
| **5-Step Validation Proofs (UI Display)** | `MOCKED` | `backend/app/services/data_loader.py:93-99` | The 5-step proof items displayed in UI are hardcoded static strings in `data_loader.py` (e.g. `"Raw MOD-97 remainder = 1"` is hardcoded text, not computed output). |
| **Hypothesis Generation & Ranking** | `MOCKED` | `backend/app/services/data_loader.py:100-104` | Hypotheses (HYP-1, HYP-2, HYP-3) and confidence scores (0.96, 0.03, 0.01) are static dictionary entries. No live probabilistic inference. |
| **Maker-Checker Dual Authorization** | `PARTIAL` | `backend/app/services/approval_engine.py:1-180`<br>`backend/app/core/security.py:71-92` | Enforces operator block and monetary limits; fails to enforce maker/checker user ID segregation. |
| **Cryptographic Provenance Audit Ledger** | `PARTIAL` | `backend/app/core/hashing.py:1-75`<br>`backend/app/services/audit_service.py:1-87` | Implements a linear SHA-256 hash chain in SQLite. Lacks Merkle tree aggregation, digital signatures, or external timestamp sealing claimed in docs. |
| **PII Tokenization & Surrogate Isolation** | `PARTIAL` | `backend/app/core/tokenization.py:1-55`<br>`backend/app/services/canonicalizer.py:216-244` | In-memory `TokenVault` generates SHA-256 surrogates (`TOK-PARTY-*`). However, canonical payment records continue to store raw cleartext names/accounts in parallel. |
| **Outbound Bank System Handoff** | `MOCKED` | `backend/app/services/action_executor.py:1-120` | Generates `GovernedActionContract` payload, but outbound execution is simulated via in-memory mock returning synthetic `DeliveryReceipt`. |
| **Live Bank Settlement Execution** | `NOT PRESENT` | N/A | Strictly not implemented by design. PeX prepares handoffs but cannot settle payments. |
| **Enterprise SSO / OAuth2 / OIDC** | `NOT PRESENT` | `backend/app/api/endpoints/auth.py:1-60` | Authentication uses hardcoded demo persona switching via `/api/auth/persona/{user_id}` and static JWT tokens. No Okta, Ping, or Azure AD integration. |

---

## 4. Out-of-Scope and Deferred Items Found in Codebase

Forensic examination of codebase docstrings, comments, and architectural notes reveals explicit deferred items:

1. **Enterprise Token Vault & Key Management Service**:
   - `backend/app/adapters/reference/reference_token_vault_adapter.py:3-5`: *"TEST / DEMO / REFERENCE ONLY. Implements SecretTokenizationVaultPort using HMAC-SHA256 deterministic token mapping... Production requires AWS KMS / HashiCorp Vault."*
2. **Semantic Dynamic AI Model Gateway**:
   - `backend/app/services/model_gateway.py:1`: Pluggable interface defined, but live LLM orchestration deferred. Hardcoded synthetic responses returned.
3. **Normalized 3NF Relational Relational Store**:
   - `backend/app/db/models.py:20-55`: Case tables store complete canonical entities as raw SQLite JSON blobs rather than normalized 3NF relational schemas.
4. **Enterprise High-Throughput Streaming Ingestion**:
   - `backend/app/adapters/reference/reference_message_broker_adapter.py:3`: Reference deque adapter explicitly marked *"TEST / REFERENCE ONLY. Zero external broker SDKs."* Kafka/IBM MQ streaming deferred to Phase 3.
5. **Live Core Banking & Clearing Connectors**:
   - `backend/app/services/icd_staging_service.py:6`: Reads from local static JSON store (`icd_staging_store.json`). Direct ISO 20022 MQ / AS2 / SWIFT Alliance connectors deferred.
6. **Outbound ISO 20022 XML Serializer & SWIFT LAU Signer**:
   - Outbound actions emit JSON dictionaries rather than signed ISO 20022 XML documents (`pacs.008.001.10`) with HMAC-SHA256 Local Authentication Units (LAU).

---

## 5. Discrepancies Between Existing Documentation and Code

| Document Claim | Source Document | Code Reality | Discrepancy Severity |
| :--- | :--- | :--- | :--- |
| **"PeX never settles payments"** | `PeX_Master_PRD_and_Technical_Blueprint.md` (Principle 4) | `backend/app/services/file_watcher.py:575` sets `final_status = LifecycleStage.SETTLED.value` directly when `output.stp_eligible` is true. | **HIGH (Architectural Drift)** |
| **"Cryptographic Merkle DAG Audit Ledger"** | `PeX_Phase3_Industrialization_Architecture_v0.1.md` | `backend/app/core/hashing.py:8-48` implements a simple sequential SHA-256 hash chain (`prev_hash`). No Merkle trees or DAGs exist. | **MEDIUM (Marketing Overstatement)** |
| **"Zero-PII Internal AI Boundary"** | `PeX_Master_PRD_and_Technical_Blueprint.md` | `backend/app/services/canonicalizer.py:218, 225, 240` stores cleartext debtor/creditor names and account numbers directly in `CanonicalPayment`. | **HIGH (Data Privacy Risk)** |
| **"Dynamic Multi-Hypothesis AI Reasoning"** | `PeX_41_Exception_Taxonomy_SME_Architecture_Cards.md` | `backend/app/services/model_gateway.py` and `data_loader.py:100-104` return hardcoded static dictionaries for hypotheses and confidence scores. | **MEDIUM (Simulation Drift)** |
| **"Confirmation of Payee (CoP) API Integration"** | `PeX_Payment_SME_Product_and_Technical_Walkthrough_Specification.md` | Step 3 ("Confirmation of Payee") displays a static badge string `"NAME MATCHED"` hardcoded in `data_loader.py:96`. No external CoP API is called. | **MEDIUM (Simulation Drift)** |
