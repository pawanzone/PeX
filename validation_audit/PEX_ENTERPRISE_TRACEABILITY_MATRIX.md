# 🔗 PeX Platform: Enterprise Architecture Traceability Matrix

**Document ID:** `PEX-ENTERPRISE-TRACEABILITY-MATRIX-v0.1`  
**Governing Baseline:** PeX `v1.9.4` (`9e9184b`) / `PEX_ENTERPRISE_ARCHITECTURE_SPECIFICATION_v0.1.md`  
**Evaluation Scope:** End-to-End Capability Traceability Chain  
**Date:** September 28, 2026  
**Status:** Authoritative Traceability Ledger  

---

## 1. Traceability Methodology & Schema

Every core domain capability established in the accepted **v1.9.4 baseline** is traced across the full 8-stage lifecycle chain:

$$\text{v1.9.4 Capability} \longrightarrow \text{Current Component} \longrightarrow \text{Secondary Port} \longrightarrow \text{Enterprise Capability} \longrightarrow \text{Target Component} \longrightarrow \text{Enterprise Req.} \longrightarrow \text{Acceptance Criterion} \longrightarrow \text{Future Validation Evidence}$$

---

## 2. End-to-End Capability Traceability Table

| # | v1.9.4 Validated Capability | Current v1.9.4 Component | Existing / New Port | Enterprise Capability (v0.1) | Target Enterprise Component | Enterprise Requirement | Acceptance Criterion (AC) | Future Validation Evidence |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TR-01** | **Canonical Payment & Exception Schemas** | `backend/app/schemas/canonical.py` | Core Domain Model (Port Invariant) | Layer 2: Canonical Ingestion & Data Normalization | `CanonicalizerService` | Lossless parsing across SWIFT CBPR+, Fedwire FAIM, and ISO 20022. | **AC-1, AC-5**: Schema completeness and deterministic format checks. | Automated schema roundtrip tests against SWIFT/Fedwire test vectors. |
| **TR-02** | **41 BIAN Exception Profiles (5 Domains)** | `backend/app/schemas/canonical.py`, `services/canonicalizer.py` | Domain Core Service | Layer 3: BIAN Exception Classification Engine | `BIANExceptionClassifier` | Automatic categorization of payment breaks into 5 market domains. | **AC-1**: Correct domain and profile propagation on intake. | Multi-rail event ingestion test suite (`test_mst_039`). |
| **TR-03** | **Zero-PII Token Vault & Masking** | `backend/app/core/tokenization.py` | `SecretStore`, `KeyManagementService` | Layer 2: Hardware Tokenization Vault | `TokenVaultEnclave` (FIPS 140-2 L3 HSM) | Format-preserving surrogate tokens for PII before LLM context generation. | **AC-1**: Zero raw PII in logs, caches, or model gateway payloads. | Static analysis scanning & automated PII leakage test (`test_tokenization.py`). |
| **TR-04** | **Maker-Checker Segregation of Duties** | `backend/app/core/security.py`, `services/approval_engine.py` | `IdentityProvider` | Layer 3: Enterprise Authorization Engine | `PolicyAuthorizationService` (ABAC/RBAC) | Strict $0 approval limit for Operators; Level-1 ($250k) and Dual-Auth (> $250k). | **AC-2, AC-3**: Maker cannot self-approve; high-value requires dual-signoff. | Negative adversarial SoD test suite (`test_mst_035`, `test_mst_043`). |
| **TR-05** | **Policy-as-Code JSON AST Compiler** | `backend/app/services/rule_engine.py` | Domain Core Service | Layer 3: Policy AST Evaluation Engine | `RuleEngineService` | Deterministic compilation and evaluation of institutional exception policies. | **AC-2, AC-3**: Policy rule simulation and governance gating. | Rule simulation suite (`test_rules_e2e.py`). |
| **TR-06** | **Governed STP Fast-Lane Engine** | `backend/app/services/stp_engine.py` | `PersistenceRepository`, `EventBus` | Layer 4/6: Autonomous Zero-Touch Execution | `STPAutonomousWorker` | Zero-touch autonomous settlement for micro-repairs (<= $10k, >= 98% conf). | **AC-4**: Preserves AI proposed repairs in settled state with zero latency. | STP fast-lane persistence suite (`test_mst_036`, `test_stp_e2e.py`). |
| **TR-07** | **Multi-Hypothesis Disambiguation** | `backend/app/services/model_gateway.py` | `LLMGateway` | Layer 3: Disambiguation & Candidate Ranking | `HypothesisEliminationEngine`| Ranks candidate repair hypotheses and flags ambiguous evidence for human review. | **AC-5**: Disambiguates conflicting directory records. | Disambiguation test suite (`test_disambiguation_and_rule_edit.py`). |
| **TR-08** | **Deterministic MOD-97-10 Checksum Verifier** | `backend/app/services/canonicalizer.py` | Domain Core Service | Layer 3: Deterministic Validator Gate | `ChecksumValidationModule` | ISO 7064 MOD-97-10 and 9-digit ABA routing checksum mathematical verification. | **AC-5**: No invalid IBAN/routing number reaches an approver. | IBAN mathematics test suite (`test_mst_021`, `test_mst_024`). |
| **TR-09** | **Continuous Cryptographic Provenance** | `backend/app/core/hashing.py`, `services/audit_service.py` | `PersistenceRepository`, `ObjectEvidenceStore` | Layer 5: Provenance Hash Chain & WORM Vault | `ProvenanceLedgerService` + Cloud WORM Storage | SHA-256 linear hash chaining across 20 stages; 7-year immutable WORM storage. | **AC-6**: Tamper detection on any database record alteration. | Adversarial database tampering test suite (`test_mst_009`, `test_mst_034`). |
| **TR-10** | **Pluggable Model Gateway & Context Builder** | `backend/app/services/model_gateway.py`, `services/context_builder.py`| `LLMGateway` | Layer 4: Model Gateway & RAG Semantic Layer | `PrivateModelGateway` (Vertex/Bedrock/Azure) | Zero-PII prompt assembly, structured `ReasoningResult` output validation, fallback. | **AC-1, AC-5**: Advisory output validation and zero hallucination. | Model gateway contract test suite (`test_scenarios.py`). |
| **TR-11** | **Idempotent Bank Dispatch & Receipting** | `backend/app/services/action_executor.py` | `PaymentRailAdapter` (New Secondary Port) | Layer 6: Governed Execution & Clearing Dispatch | `ClearingDispatchHub` | Distributed lock idempotency; bi-directional delivery receipt generation. | **AC-4**: Duplicate execution requests produce exactly one wire release. | Idempotency lock test suite (`test_scenarios.py`). |
| **TR-12** | **Relational Persistence & Case Cache** | `backend/app/db/repository.py`, `session.py` | `PersistenceRepository` | Layer 5: Enterprise Multi-AZ Relational DB | `CloudSQLPostgreSQLCluster` | Multi-AZ ACID relational persistence with range partitioning and sub-second failover. | **AC-7**: Multi-AZ failover within 30 seconds with RPO < 1 second. | Multi-AZ automated failover drill in Phase H. |
| **TR-13** | **Federated Evidence Planner & BMD Staging** | `backend/app/services/evidence_planner.py`, `icd_staging_service.py` | `CoreBankingAdapter`, `ComplianceAdapter` (New Secondary Ports) | Layer 3: Federated Evidence Retrieval | `FederatedEvidenceAggregator` | Parallel query of Beneficiary Master Directories (BMD), SSI, and 90-day history. | **AC-5**: Sub-500ms parallel evidence retrieval. | Evidence aggregation performance benchmark in Phase E. |
| **TR-14** | **Observability & RTGS Radar Telemetry** | `backend/app/api/endpoints/analytics.py` | Core Application Service | Layer 7: Enterprise Observability & Tracing | `OpenTelemetryCollector` + Prometheus / Grafana | Distributed tracing with payment correlation IDs, real-time clearing cutoffs radar. | **NFR-8**: Real-time cutoff monitoring and SLA breach prediction. | OpenTelemetry trace verification in Phase B. |

---

## 3. Secondary Port Classification Summary

| Secondary Port Name | v1.9.4 Prototype Status | Enterprise Target Status | Architectural Layer Ownership |
| :--- | :--- | :--- | :--- |
| **`PersistenceRepository`** | Existing (SQLite / InMemory) | Extended (Multi-AZ PostgreSQL 16) | Layer 5 (Persistence & Storage) |
| **`SecretStore`** | Existing (Mock Environment) | Extended (Cloud Secrets Manager) | Layer 2/7 (Security & Infrastructure) |
| **`KeyManagementService`** | Existing (Local Software AES) | Extended (FIPS 140-2 L3 Cloud HSM) | Layer 2 (Tokenization Vault) |
| **`IdentityProvider`** | Existing (Mock Personas/JWT) | Extended (Enterprise OIDC / SAML) | Layer 7 (Enterprise IAM) |
| **`EventBus`** | Existing (Asyncio Queue) | Extended (Distributed FIFO SQS/PubSub) | Layer 2/6 (Event-Driven Architecture) |
| **`ObjectEvidenceStore`** | Existing (Local Disk Cache) | Extended (7-Year WORM S3/GCS/Azure) | Layer 5 (Immutable Evidence Store) |
| **`LLMGateway`** | Existing (Mock/Gemini/OpenAI) | Extended (Private VPC Bedrock/Vertex) | Layer 4 (AI / Model Gateway) |
| **`PaymentRailAdapter`** | **NEW PORT** (Introduced v0.1) | Live mTLS FedLine & SWIFT Gateway | Layer 1/6 (Clearing Integration) |
| **`CoreBankingAdapter`** | **NEW PORT** (Introduced v0.1) | Live BMD / SSI / DDA API Connectors | Layer 1/3 (Core Banking Integration) |
| **`ComplianceAdapter`** | **NEW PORT** (Introduced v0.1) | Real-Time Sanctions/OFAC/PEP Check | Layer 1/3 (Compliance Integration) |

---

## 4. Traceability Integrity Certification

- **Zero Orphaned v1.9.4 Capabilities:** 100% of the 14 baseline functional capabilities map directly to enterprise components in v0.1.
- **Zero Orphaned Enterprise Target Components:** All enterprise layers and new secondary ports (`PaymentRailAdapter`, `CoreBankingAdapter`, `ComplianceAdapter`) are strictly derived from validated prototype requirements.
- **Zero Broken Test Traceability Links:** Every acceptance criterion connects to executable automated tests or explicit operational drills.
