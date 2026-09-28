# 📝 PeX — Cloud Reference Architecture v0.2 Changeset & Specification Diff

**Document ID:** `PEX-CLOUD-CHANGESET-v0.2`  
**Governing Baseline:** PeX `v1.9.4` (`9e9184b`) / Enterprise Architecture `v0.2`  
**Scope:** Authoritative Text Diffs & Refinements for Cloud Reference Architecture v0.2  
**Date:** September 28, 2026  
**Status:** Approved Architecture Changeset  

---

## 1. Summary of Changeset

This document defines the formal, exact before/after text modifications to elevate **PeX Cloud Reference Architecture v0.1** to **v0.2**, completely resolving all 9 assurance review findings (GAP-SEC-01 through GAP-OBS-01).

```text
+------------+----------+-------------------------------------------------------------+
| Finding ID | Severity | Focus Area & Resolution Summary                             |
+------------+----------+-------------------------------------------------------------+
| GAP-SEC-01 | P1       | Disentangle Token Vault Enclave Datastore from Cloud KMS    |
| GAP-PAY-01 | P1       | Disentangle Clearing Transport ACK from Final Settlement     |
| GAP-DR-01  | P1       | Bifurcate Multi-AZ RPO (<1s) vs Regional DR RPO (<=5s)      |
| GAP-MAP-01 | P2       | Document Pub/Sub deduplication adapter vs SQS FIFO native   |
| GAP-STOR-01| P2       | Explicitly separate 30-day scratch from 7-year WORM GCS/S3  |
| GAP-AI-01  | P2       | Specify Model Gateway buffered validation before domain use |
| GAP-IAC-01 | P2       | Define cross-cloud Terraform module interface contract      |
| GAP-DOC-01 | P3       | Clarify Document AI vs Textract peripheral ICD adapters     |
| GAP-OBS-01 | P3       | Mandate PII sanitization filters on OpenTelemetry loggers   |
+------------+----------+-------------------------------------------------------------+
```

---

## 2. Detailed Before / After Specification Diffs

### Diff 1: Token Vault Persistence Topology (`GAP-SEC-01` / P1)
**Target File:** `docs/PEX_CLOUD_NEUTRAL_LOGICAL_ARCHITECTURE.md` (§2) & `docs/PEX_CLOUD_REFERENCE_ARCHITECTURE_v0.1.md` (§5)

```diff
<<<< BEFORE (v0.1)
The Token Vault is hosted in a Hardware Security Module (FIPS 140-2 Level 3 HSM / KMS) which securely stores the raw PII mappings (account numbers, debtor names, creditor tax IDs) and returns randomized surrogate tokens (e.g. `TKN_DEBT_98412`) to the domain core.
====
>>>> AFTER (v0.2)
The Token Vault is architected as a microsegmented two-tier security enclave:
1. Application Enclave Datastore: A dedicated, isolated relational database partition (AWS Aurora PostgreSQL / GCP Cloud SQL / Azure SQL) residing in an isolated private VPC/VNet with strict network security groups, holding the encrypted surrogate mappings `(surrogate_token, encrypted_raw_pii, key_id, iv, tag)`.
2. Cloud Key Management Service (KMS / HSM): Cloud KMS (AWS KMS, Google Cloud KMS, Azure Key Vault Managed HSM) configured with FIPS 140-2 Level 3 Customer-Managed Keys (CMKs) to perform envelope encryption, generating and wrapping/unwrapping ephemeral Data Encryption Keys (DEKs) for each tokenization transaction. The KMS provides cryptographic key lifecycle management, while the enclave database handles token persistence and query resolution.
```

---

### Diff 2: Clearing Transport ACK vs. Settlement State (`GAP-PAY-01` / P1)
**Target File:** `docs/PEX_CLOUD_REFERENCE_ARCHITECTURE_v0.1.md` (§4.2, §4.3) & `docs/PEX_AWS_REFERENCE_ARCHITECTURE.md` (§3)

```diff
<<<< BEFORE (v0.1)
Upon successful transmission of the repaired payment message to the payment clearing gateway (SWIFT / Fedwire), the clearing adapter receives the clearing delivery confirmation and immediately transitions the payment case to `LifecycleStage.SETTLED`.
====
>>>> AFTER (v0.2)
The clearing adapter strictly disentangles message transport delivery from final irreversible clearing settlement across two distinct state machine transitions:
1. Clearing Transport Dispatch (`LifecycleStage.DISPATCHED`): Occurs upon receiving an immediate network transport delivery acknowledgement (e.g. SWIFT ACK, Fedwire FAIM accept receipt, CHAPS gateway ACK). The delivery receipt is recorded in the audit trail, and the case enters `DISPATCHED` status.
2. Final Settlement Confirmation (`LifecycleStage.SETTLED`): Occurs ONLY upon receiving an authoritative inbound settlement confirmation—specifically an ISO 20022 `pacs.002.001.10` Payment Status Report with status `ACCP` (Accepted Customer Profile / Accepted Settlement), an inbound `camt.054` Debit/Credit Notification, or an internal core banking DDA ledger posting confirmation.
```

---

### Diff 3: RPO Sizing Bifurcation Under Peak Burst (`GAP-DR-01` / P1)
**Target File:** `docs/PEX_CLOUD_REFERENCE_ARCHITECTURE_v0.1.md` (§6) & `validation_audit/PEX_CLOUD_NFR_MAPPING.md` (§2)

```diff
<<<< BEFORE (v0.1)
Recovery Point Objective (RPO): < 1 second across all database, event streaming, and state storage components for regional failover.
====
>>>> AFTER (v0.2)
Recovery Point Objective (RPO) is rigorously bifurcated by failure domain:
1. Local Multi-AZ Zone Failure: RPO < 1 second (RPO = 0 for all committed transactions via synchronous multi-AZ WAL replication on AWS Aurora Multi-AZ, GCP Cloud SQL HA, Azure SQL Business Critical).
2. Cross-Region Disaster Recovery: RPO <= 5 seconds under sustained peak write stress (500 TPS / ~2.5 MB/s WAL generation), governed by asynchronous cross-region storage replication lag (AWS Aurora Global Database, GCP Cloud SQL Cross-Region Replica, Azure SQL Active Geo-Replication). RPO < 1 second during nominal traffic (<100 TPS).
```

---

### Diff 4: Event Stream Deduplication Handling (`GAP-MAP-01` / P2)
**Target File:** `docs/PEX_GCP_REFERENCE_ARCHITECTURE.md` (§3) & `validation_audit/PEX_PORT_ADAPTER_CLOUD_MAPPING.md` (§5)

```diff
<<<< BEFORE (v0.1)
Google Cloud Pub/Sub provides event streaming and message queuing with FIFO ordering and at-least-once delivery, directly substituting for AWS SQS FIFO.
====
>>>> AFTER (v0.2)
Google Cloud Pub/Sub provides high-throughput event streaming with message ordering keys. While AWS SQS FIFO and Azure Service Bus provide native server-side deduplication windows (e.g. 5-minute deduplication ID tracking), GCP Pub/Sub guarantees at-least-once delivery with ordering keys but requires an adapter-level deduplication filter. The PeX GCP Secondary Ingress Adapter implements an in-memory/Redis Bloom filter and idempotency key check (`MessageDeduplicationId`) to guarantee strictly exactly-once processing semantics at the application boundary.
```

---

### Diff 5: Object Storage Retention Policy Granularity (`GAP-STOR-01` / P2)
**Target File:** `docs/PEX_CLOUD_REFERENCE_ARCHITECTURE_v0.1.md` (§5) & `docs/PEX_GCP_REFERENCE_ARCHITECTURE.md` (§4)

```diff
<<<< BEFORE (v0.1)
Object storage (AWS S3, GCP Cloud Storage, Azure Blob) holds raw payment payloads, peripheral documentary evidence, and audit logs with Object Lock WORM retention policies applied.
====
>>>> AFTER (v0.2)
Object storage architecture mandates strict separation of storage buckets/containers by retention lifecycle:
1. Ephemeral Scratch & Ingestion Bucket: Stores incoming raw MT/MX payloads, transient OCR artifacts, and intermediate JSON dumps with a 30-day lifecycle auto-deletion policy. No WORM retention lock is applied.
2. Regulatory Evidence & Audit Archive Bucket: Stores final signed dispatch packets, corroboration evidence bundles, and tamper-evident SHA-256 Merkle audit logs with bucket-level / container-level WORM Object Lock (AWS S3 Object Lock in Compliance Mode, GCP Cloud Storage Bucket Lock, Azure Immutable Blob Storage Policy) configured for 7-year unalterable retention.
```

---

### Diff 6: Model Gateway Buffered Validation (`GAP-AI-01` / P2)
**Target File:** `validation_audit/PEX_CLOUD_AI_REFERENCE_ARCHITECTURE.md` (§2) & `docs/PEX_CLOUD_NEUTRAL_LOGICAL_ARCHITECTURE.md` (§3)

```diff
<<<< BEFORE (v0.1)
The AI Model Gateway streams LLM reasoning responses directly to the client interface and downstream evaluation engines to minimize perceived user latency.
====
>>>> AFTER (v0.2)
The AI Model Gateway decouples human streaming from backend engine ingestion:
1. Interactive UI: For human operator walkthroughs, the Model Gateway provides an SSE (Server-Sent Events) token stream for visual display.
2. Core Engine Ingestion: For automated STP decision pipelines, the Model Gateway buffers the full LLM completion, executes strict Pydantic JSON schema validation against `ReasoningResult`, validates that no hallucinated fields or invalid confidence scores exist, and passes ONLY validated, schema-compliant `ReasoningResult` objects to downstream rule and hypothesis engines.
```

---

### Diff 7: Infrastructure-as-Code Module Contract (`GAP-IAC-01` / P2)
**Target File:** `docs/PEX_CLOUD_REFERENCE_ARCHITECTURE_v0.1.md` (§7)

```diff
<<<< BEFORE (v0.1)
Infrastructure will be deployed using Terraform modules specific to AWS, GCP, and Azure.
====
>>>> AFTER (v0.2)
Infrastructure deployment uses a standardized, modular Terraform / OpenTofu contract structure:
- Root Module: Declares common variables (`environment`, `region`, `vpc_cidr`, `db_instance_class`, `token_vault_hsm_enabled`, `dr_region`, `rpo_threshold_seconds`).
- Provider Modules: `modules/aws/`, `modules/gcp/`, `modules/azure/` each implement identical output interfaces (`pex_api_endpoint`, `pex_db_connection_secret_arn`, `pex_token_vault_key_id`, `pex_event_stream_arn`, `pex_audit_bucket_id`), ensuring uniform pipeline deployment and zero environment drift.
```

---

### Diff 8: Peripheral ICD OCR Adapter Clarification (`GAP-DOC-01` / P3)
**Target File:** `validation_audit/PEX_CLOUD_PROVIDER_SERVICE_MAPPING.md` (§3)

```diff
<<<< BEFORE (v0.1)
Document OCR and extraction is performed by AWS Textract, GCP Document AI, or Azure AI Document Intelligence as core internal services.
====
>>>> AFTER (v0.2)
Document OCR services (AWS Textract, Google Cloud Document AI, Azure AI Document Intelligence) are peripheral Interface Control Document (ICD) adapters invoked strictly via the read-only `ICorroborationPort`. They are auxiliary ingestion tools for non-STP documentary evidence (e.g. paper invoices, physical tax certificates) and are completely decoupled from core ISO 20022 / SWIFT MT structured payment processing.
```

---

### Diff 9: Observability PII Redaction Filter (`GAP-OBS-01` / P3)
**Target File:** `validation_audit/PEX_CLOUD_NFR_MAPPING.md` (§5) & `docs/PEX_CLOUD_REFERENCE_ARCHITECTURE_v0.1.md` (§6)

```diff
<<<< BEFORE (v0.1)
OpenTelemetry collectors aggregate logs, metrics, and traces from all microservices and stream them to cloud-native monitoring services (AWS CloudWatch, GCP Cloud Logging, Azure Monitor).
====
>>>> AFTER (v0.2)
OpenTelemetry collectors and application loggers implement a mandatory Zero-PII sanitization processor at the container logging boundary. All log events, trace spans, and metric tags are filtered through regex redaction and surrogate token validators before leaving the container memory space, ensuring no unmasked IBANs, names, or addresses ever enter CloudWatch, Google Cloud Logging, Azure Monitor, or third-party APM tools.
```

---

## 3. Approval and Sign-Off

The modifications detailed above are formally incorporated into **PeX Cloud Reference Architecture v0.2**. All architecture diagrams, adapter contracts, and implementation blueprints in Phase 3 shall conform to these authoritative diffs.
