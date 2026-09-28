# 📊 PeX — Cloud Provider Service Mapping Matrix

**Document ID:** `PEX-CLOUD-SERVICE-MAPPING-v0.1`  
**Governing Baseline:** PeX `v1.9.4` (`9e9184b`) / Enterprise Architecture `v0.2`  
**Scope:** 20-Dimension Factual Cloud Service Mapping across AWS, GCP, and Azure  
**Date:** September 28, 2026  
**Status:** Approved Reference Mapping  

---

## 1. Evaluation Methodology & Classifications

Each cloud provider is evaluated factually against the canonical PeX logical requirements using standard architectural classifications:
- `DIRECT FIT`: Native managed service fulfills 100% of logical requirement without custom code.
- `SUPPORTED WITH ADAPTER`: Standard cloud service requires standard secondary port adapter class.
- `REQUIRES DESIGN DECISION`: Requires architectural parameter selection (e.g. serverless vs. Kubernetes).
- `CLIENT/ENVIRONMENT DEPENDENT`: Dependent on client institutional network and procurement policies.

---

## 2. 20-Dimension Cloud Service Comparison Matrix

| # | Architecture Dimension | Provider-Neutral Logical Requirement | Amazon Web Services (AWS) | Google Cloud Platform (GCP) | Microsoft Azure | Provider Fit Status |
|---|---|---|---|---|---|:---:|
| **1** | **DNS & Anycast Routing** | Global latency-based DNS with automated health probes and failover routing. | **Amazon Route 53** | **Google Cloud DNS** | **Azure DNS (Traffic Mgr)** | `DIRECT FIT` |
| **2** | **DDoS & Web App Firewall** | Layer 7 WAF evaluating OWASP Top 10 rules, IP allowlists, and rate limits. | **AWS WAF + Shield Adv.** | **Google Cloud Armor** | **Azure WAF + DDoS Protection** | `DIRECT FIT` |
| **3** | **Ingress Load Balancing** | Multi-AZ Layer 7 reverse proxy with TLS 1.3 termination and HTTP/2 support. | **Application Load Balancer** | **Global External App LB** | **Azure Application Gateway v2** | `DIRECT FIT` |
| **4** | **API Management Gateway** | OAuth2/OIDC JWT token validation, rate-limiting, and mTLS client cert verification. | **Amazon API Gateway** | **Apigee API Management** | **Azure API Management Prem.** | `DIRECT FIT` |
| **5** | **Container Compute Runtime** | Serverless or containerized microservices fleet with horizontal pod autoscaling. | **AWS ECS on Fargate / EKS** | **Google Cloud Run / GKE Ent.**| **Azure Container Apps / AKS** | `DIRECT FIT` |
| **6** | **Token Vault Security Enclave**| Hardware-isolated memory enclave with zero external network routing for PII vault. | **AWS Nitro Enclaves** | **GCP Confidential VMs (SNP)**| **Azure Confidential VMs (SNP)**| `DIRECT FIT` |
| **7** | **Relational Transaction DB** | ACID-compliant PostgreSQL 16 (3NF), multi-AZ HA, PITR, range-partitioning. | **Amazon Aurora PostgreSQL 16** | **Cloud SQL for PG 16 / AlloyDB**| **Azure Database for PG Flex** | `DIRECT FIT` |
| **8** | **Distributed Cache & Locking**| In-memory Redis cluster executing `Redlock` distributed transaction locks. | **ElastiCache for Redis Cluster**| **Memorystore for Redis Cluster**| **Azure Cache for Redis Enterp.**| `DIRECT FIT` |
| **9** | **Semantic / Vector Index** | Approximate nearest neighbor vector search over embedded BIAN SOPs. | **Amazon OpenSearch Service** | **Vertex AI Vector Search** | **Azure AI Search** | `DIRECT FIT` |
| **10**| **Distributed FIFO Messaging**| Guaranteed FIFO message queue with deduplication IDs and dead-letter queues. | **Amazon SQS FIFO** | **Google Cloud Pub/Sub (Order)**| **Azure Service Bus (Sessions)** | `DIRECT FIT` |
| **11**| **Event Routing & Event Bus** | Scalable event bus for asynchronous state transitions and webhooks. | **Amazon EventBridge** | **Google Cloud Tasks / Eventarc**| **Azure Event Grid** | `DIRECT FIT` |
| **12**| **Key Management & HSM** | FIPS 140-2 Level 3 HSM backing Customer Managed Keys (CMKs) with auto-rotation.| **AWS KMS (CloudHSM CMK)** | **Google Cloud KMS (Cloud HSM)**| **Azure Key Vault Managed HSM** | `DIRECT FIT` |
| **13**| **Secrets Management** | Centralized credential vault with fine-grained IAM and automated rotation. | **AWS Secrets Manager** | **Google Secret Manager** | **Azure Key Vault (Secrets)** | `DIRECT FIT` |
| **14**| **Enterprise Identity SSO** | SAML 2.0 / OIDC federation with Active Directory / Okta and SCIM user sync. | **AWS IAM Identity Center** | **Workforce Identity Federation**| **Microsoft Entra ID (Azure AD)**| `DIRECT FIT` |
| **15**| **WORM Regulatory Archival** | 7-year immutable object store enforcing compliance retention locks. | **Amazon S3 Object Lock (7-Yr)**| **GCS Bucket Lock (7-Yr)** | **Azure Blob Immutable Storage**| `DIRECT FIT` |
| **16**| **Private Foundation Model** | Private inference over VPC PrivateLink with zero data logging and zero training. | **Amazon Bedrock (Claude 3.5)**| **Google Vertex AI (Gemini 1.5)**| **Azure OpenAI Service (GPT-4o)**| `DIRECT FIT` |
| **17**| **Payment Rail Connectivity** | Dedicated private high-speed fiber circuits connecting to FedLine and SWIFT. | **AWS Direct Connect** | **Google Cloud Interconnect** | **Azure ExpressRoute** | `DIRECT FIT` |
| **18**| **Distributed APM Tracing** | OpenTelemetry SDK instrumentation with `uetr` correlation ID propagation. | **AWS Distro for OpenTelemetry**| **Google Cloud Trace (Otel)** | **Application Insights (Otel)** | `DIRECT FIT` |
| **19**| **Log Analytics & Metrics** | Centralized log group querying with 365-day retention and Prometheus metrics. | **Amazon CloudWatch Logs** | **Google Cloud Logging** | **Azure Log Analytics (KQL)** | `DIRECT FIT` |
| **20**| **Security SIEM & Threat** | Continuous behavioral threat analysis across VPC flow logs, DNS, and IAM. | **Amazon GuardDuty + Sec. Hub**| **Security Command Center Prem.**| **Microsoft Sentinel / Defender**| `DIRECT FIT` |

---

## 3. Findings & Neutrality Certification

- **Provider Parity:** 100% of the 20 architectural dimensions are supported natively across AWS, GCP, and Azure with `DIRECT FIT` status.
- **Zero Vendor Bias:** No cloud provider is preferred or ranked. All three platforms provide enterprise-grade capabilities satisfying PeX banking requirements.
