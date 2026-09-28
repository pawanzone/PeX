# 🔗 PeX — Cloud Reference Architecture Traceability Matrix

**Document ID:** `PEX-CLOUD-TRACEABILITY-v0.1`  
**Governing Baseline:** PeX `v1.9.4` (`9e9184b`) / Enterprise Architecture `v0.2`  
**Scope:** Complete 11-Stage Traceability from Baseline to Cloud Adapters and Validation Evidence  
**Date:** September 28, 2026  
**Status:** Approved Reference Traceability Matrix  

---

## 1. Traceability Chain Schema

$$\text{v1.9.4 Baseline} \longrightarrow \text{Ent. Arch v0.2} \longrightarrow \text{Ent. Req.} \longrightarrow \text{Cloud-Neutral Comp.} \longrightarrow \text{Secondary Port} \longrightarrow \text{AWS Adapter} \longrightarrow \text{GCP Adapter} \longrightarrow \text{Azure Adapter} \longrightarrow \text{Security Control} \longrightarrow \text{NFR} \longrightarrow \text{Validation Evidence}$$

---

## 2. End-to-End Cloud Traceability Matrix

| # | v1.9.4 Baseline Capability | Enterprise Architecture v0.2 Requirement | Cloud-Neutral Component | Secondary Port Interface | AWS Adapter | GCP Adapter | Azure Adapter | Security Control | Target NFR | Future Acceptance Evidence |
|:---:|---|---|---|---|---|---|---|---|---|---|
| **1** | **Canonical Schemas** (`schemas/canonical.py`) | Lossless multi-rail data normalization across ISO 20022/FAIM. | `CanonicalizerService` | Port Invariant | In-memory Pydantic Core | In-memory Pydantic Core | In-memory Pydantic Core | Schema Validation | Ingestion $< 100\text{ms}$ | Automated SWIFT/Fedwire roundtrip test suite. |
| **2** | **41 BIAN Profiles** (5 Market Domains) | Automatic break classification into 5 market domains. | `BIANExceptionClassifier`| Port Invariant | In-memory Pydantic Core | In-memory Pydantic Core | In-memory Pydantic Core | Strict Categorization | Throughput $\ge 100\text{ TPS}$ | Domain classification test suite (`test_mst_039`). |
| **3** | **Zero-PII Vault** (`core/tokenization.py`) | Format-preserving surrogate tokenization before AI ingress. | `TokenVaultEnclave` | `KeyManagementService` | `AWSKMSCloudHSMAdapter` | `GCPCloudKMSHSMAdapter` | `AzureKeyVaultManagedHSMAdapter` | Hardware Enclave + Envelope Enc. | Zero PII Leakage | Automated regex PII log scanner (`test_tokenization.py`).|
| **4** | **Maker-Checker SoD** (`core/security.py`) | Strict \$0 Operator limit; Level-1 (\$250k); Dual-Auth ($\ge \$250\text{k}$).| `PolicyAuthorizationService`| `IdentityProvider` | `AWSIAMIdentityCenterAdapter` | `GCPWorkforceIdentityAdapter`| `AzureEntraIDIdentityAdapter` | System-Enforced SoD & Limits | Zero Unauth Releases | Negative adversarial SoD test suite (`test_mst_035`).|
| **5** | **Policy AST Engine** (`services/rule_engine.py`)| Deterministic compilation and evaluation of institutional JSON ASTs. | `RuleEngineService` | Port Invariant | In-memory AST Compiler | In-memory AST Compiler | In-memory AST Compiler | Tamper-Proof JSON AST | Execution $< 50\text{ms}$ | Policy rule simulation suite (`test_rules_e2e.py`). |
| **6** | **Governed STP Engine** (`services/stp_engine.py`)| Autonomous zero-touch settlement for micro-repairs (<= $10k). | `STPAutonomousWorker` | `PersistenceRepository`, `EventBus` | `AWSAuroraPostgresAdapter` + SQS | `GCPCloudSQLPostgresAdapter` + PubSub | `AzurePostgresFlexAdapter` + ServiceBus | Guardrail Gating (<=$10k, >=98%) | Resolution $< 50\text{ms}$ | STP fast-lane persistence suite (`test_mst_036`). |
| **7** | **Multi-Hypothesis Disambiguation** | Ranks candidate accounts and flags ambiguity for human review. | `HypothesisEliminationEngine`| `LLMGateway` | `AWSBedrockClaudeGatewayAdapter`| `GCPVertexAIGeminiGatewayAdapter`| `AzureOpenAIGatewayAdapter` | Ambiguity Flagging | Decision Accuracy | Disambiguation test suite (`test_disambiguation_and_rule_edit.py`).|
| **8** | **Deterministic Checksums** (`services/canonicalizer.py`)| ISO 7064 MOD-97-10 check digit and ABA 9-digit verification. | `ChecksumValidationModule` | Port Invariant | In-memory Deterministic Math | In-memory Deterministic Math | In-memory Deterministic Math | Unconditional Override Gate | Zero Invalid Formats | IBAN mathematics test suite (`test_mst_021`, `test_mst_024`).|
| **9** | **Continuous Provenance** (`core/hashing.py`) | Linear SHA-256 hash chaining across 20 stages + 7-yr WORM. | `ProvenanceLedgerService` | `PersistenceRepository`, `ObjectEvidenceStore` | `AWSS3ObjectLockAdapter` | `GCPGCSBucketLockAdapter` | `AzureBlobImmutableStorageAdapter` | Tamper-Evident Hash Preimage | 7-Year WORM Retention | Adversarial database tampering suite (`test_mst_009`).|
| **10**| **Model Gateway** (`services/model_gateway.py`)| Zero-PII prompt assembly, structured `ReasoningResult`, fallback. | `PrivateModelGateway` | `LLMGateway` | `AWSBedrockClaudeGatewayAdapter`| `GCPVertexAIGeminiGatewayAdapter`| `AzureOpenAIGatewayAdapter` | Advisory Role (\$0 Authority) | AI Latency $< 1,500\text{ms}$ | Model gateway contract test suite (`test_scenarios.py`). |
| **11**| **Idempotent Dispatch** (`services/action_executor.py`)| Distributed lock idempotency; delivery receipt generation. | `ClearingDispatchHub` | `PaymentRailAdapter` | `AWSDirectConnectRailAdapter` | `GCPInterconnectRailAdapter` | `AzureExpressRouteRailAdapter` | Exactly-Once Business Release | Dispatch $< 300\text{ms}$ | Idempotency lock test suite (`test_scenarios.py`). |
| **12**| **Relational Persistence** (`db/repository.py`)| ACID relational persistence with range partitioning and PITR. | `PostgreSQLCluster` | `PersistenceRepository` | `AWSAuroraPostgresAdapter` | `GCPCloudSQLPostgresAdapter` | `AzurePostgresFlexAdapter` | Multi-AZ Synchronous Storage | RPO $< 1\text{s}$, RTO $< 15\text{m}$ | Multi-AZ automated failover drill in Phase H. |
| **13**| **Federated Evidence** (`services/evidence_planner.py`)| Parallel query of internal BMD, SSI, and 90-day history. | `FederatedEvidenceAggregator`| `CoreBankingAdapter`, `ComplianceAdapter` | `AWSInternalBMDAdapter` | `GCPInternalBMDAdapter` | `AzureInternalBMDAdapter` | mTLS Network Encryption | Retrieval $< 500\text{ms}$ | Evidence aggregation benchmark in Phase E. |
| **14**| **Observability Telemetry** (`api/endpoints/analytics.py`)| OpenTelemetry distributed tracing with `uetr` correlation IDs. | `OpenTelemetryCollector` | Core Application Service | `AWS Distro for OpenTelemetry` | `Google Cloud Trace (Otel)` | `Application Insights (Otel)` | Centralized SIEM Auditing | 99.99% Availability | OpenTelemetry trace verification in Phase B. |

---

## 3. Traceability Validation Certification

- **Zero Broken Links:** All 14 baseline functional capabilities connect without gaps to concrete AWS, GCP, and Azure service adapters.
- **Full Governance Preservation:** Security controls, AI governance boundaries, and NFR targets remain 100% consistent across all three cloud targets.
