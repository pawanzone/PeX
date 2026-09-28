# 📈 PeX — Cloud Non-Functional Requirements (NFR) Mapping

**Document ID:** `PEX-CLOUD-NFR-MAPPING-v0.1`  
**Governing Baseline:** PeX `v1.9.4` (`9e9184b`) / Enterprise Architecture `v0.2`  
**Scope:** Exhaustive Mapping of Enterprise NFRs across AWS, GCP, and Azure  
**Date:** September 28, 2026  
**Status:** Approved Reference NFR Mapping  

---

## 1. NFR Classification Methodology

Every Non-Functional Requirement is evaluated against concrete cloud mechanisms and assigned an authoritative engineering classification:
- `ARCHITECTURALLY_SUPPORTED`: Directly satisfied by multi-AZ platform topology and core invariants.
- `TARGET_REQUIRES_LOAD_TEST`: Design target requiring distributed performance benchmark validation.
- `CLIENT_INPUT_REQUIRED`: Dependent on client institutional volume and SLA requirements (`OQ-02`).
- `IMPLEMENTATION_DEPENDENT`: Dependent on third-party model inference latency and network bandwidth.
- `EXTERNAL_SYSTEM_DEPENDENT`: Dependent on external central bank clearing network responsiveness.

---

## 2. Exhaustive NFR Implementation & Verification Matrix

| NFR Dimension | Enterprise Target Requirement | Classification | AWS Implementation Mechanism | GCP Implementation Mechanism | Azure Implementation Mechanism | Required Validation Evidence Strategy |
|---|---|---|---|---|---|---|
| **High Availability** | **99.99% Uptime** ($\le 52.6\text{ min/yr}$) | `ARCHITECTURALLY_SUPPORTED` | Multi-AZ ECS Fargate + Aurora PostgreSQL Multi-AZ + ALB. | Multi-Zone Cloud Run / GKE + Cloud SQL HA + GLB. | Zone-Redundant Container Apps + PostgreSQL Flex HA. | Synthetic uptime monitoring & monthly chaos engineering drill. |
| **Ingestion Latency** | **$< 100\text{ ms}$** (Broker to case DB) | `TARGET_REQUIRES_LOAD_TEST` | SQS FIFO + Asyncio FastAPI batch consumer + Aurora WAL write. | Pub/Sub Ordering Keys + Cloud Run async consumer + Cloud SQL. | Service Bus Sessions + Container Apps + PostgreSQL Flex. | OpenTelemetry trace span timer from ingress webhook to DB commit. |
| **Evidence Planning Latency**| **$< 500\text{ ms}$** (Parallel fetch) | `TARGET_REQUIRES_LOAD_TEST` | Async Python concurrent queries to OpenSearch, ElastiCache, and BMD. | Async Python concurrent queries to Vertex Search, Memorystore, BMD. | Async Python concurrent queries to AI Search, Azure Redis, BMD. | Microservice span duration metrics under 100 concurrent requests. |
| **AI Reasoning Latency** | **$< 1,500\text{ ms}$** (Inference + eval)| `IMPLEMENTATION_DEPENDENT` | Amazon Bedrock Claude 3.5 Sonnet over PrivateLink + streaming JSON. | Vertex AI Gemini 1.5 Flash / Pro over Private Service Connect. | Azure OpenAI GPT-4o-mini / GPT-4o over Azure Private Endpoints. | Model Gateway roundtrip latency histogram logged in OpenTelemetry. |
| **Dispatch Latency** | **$< 300\text{ ms}$** (Release to network)| `EXTERNAL_SYSTEM_DEPENDENT` | Direct Connect 10 Gbps + async mTLS SWIFT Alliance Gateway dispatch. | Cloud Interconnect 10 Gbps + async mTLS SWIFT / FedLine dispatch. | Azure ExpressRoute 10 Gbps + async mTLS SWIFT / FedLine dispatch. | Dispatcher egress timestamp to central bank ACK receipt diff. |
| **Throughput & Scale** | **100 to 500 TPS** (Stress ceiling) | `CLIENT_INPUT_REQUIRED` | Aurora PostgreSQL I/O scaling + SQS FIFO partition sharding. | Cloud SQL / AlloyDB scaling + Pub/Sub partition throughput. | PostgreSQL Flexible Server vCore scaling + Service Bus Partitions. | Distributed Locust / k6 load test simulating 500 exceptions/sec. |
| **Concurrent Users** | **500 Concurrent Officers** | `TARGET_REQUIRES_LOAD_TEST` | Stateless container autoscaling (50 instances) behind ALB + Redis cache. | Cloud Run autoscaling (50 instances) behind GLB + Memorystore. | Container Apps autoscaling (50 instances) behind App Gateway + Redis.| WebSocket / REST synthetic load test simulating 500 active sessions. |
| **Recovery Point (RPO)** | **$< 1\text{ second}$** (Zero loss) | `ARCHITECTURALLY_SUPPORTED` | Multi-AZ Aurora synchronous storage replication across 3 AZs. | Cloud SQL Multi-Zone synchronous regional storage replication. | PostgreSQL Flexible Server Zone-Redundant synchronous replication. | Primary database crash simulation during active transaction load. |
| **Recovery Time (RTO)** | **$< 15\text{ minutes}$** (Regional DR) | `ARCHITECTURALLY_SUPPORTED` | Route 53 ARC + Aurora Global DB secondary promote in `us-west-2`. | Cloud DNS Failover + Cloud SQL cross-region replica promote in `us-east4`.| Azure Front Door switch + PostgreSQL geo-replica promote in `Central US`.| Automated regional disaster recovery drill executed annually. |
| **Regulatory Archival** | **7 Years** Immutable WORM Storage | `ARCHITECTURALLY_SUPPORTED` | Amazon S3 Object Lock (Compliance Mode, locked retention policy). | Google Cloud Storage Bucket Lock (Compliance Mode locked policy). | Azure Blob Storage Immutable Storage (Time-based retention policy). | AWS/GCP/Azure compliance storage API policy verification. |
| **Data Encryption** | FIPS 140-2 Level 3 HSM + TLS 1.3 | `ARCHITECTURALLY_SUPPORTED` | AWS KMS CMK backed by CloudHSM + TLS 1.3 ALB listeners. | Google Cloud KMS backed by Cloud HSM + TLS 1.3 GLB listeners. | Azure Key Vault Managed HSM + TLS 1.3 App Gateway listeners. | Automated TLS cipher scanner & Cloud HSM compliance certificate. |
| **Zero-PII Protection** | Zero raw PII in logs/caches/LLMs | `ARCHITECTURALLY_SUPPORTED` | Format-preserving surrogate tokenization in isolated Nitro Enclave. | Format-preserving surrogate tokenization in Confidential VM. | Format-preserving surrogate tokenization in Confidential VM. | Automated regex PII scanner over log groups and LLM audit traces. |
