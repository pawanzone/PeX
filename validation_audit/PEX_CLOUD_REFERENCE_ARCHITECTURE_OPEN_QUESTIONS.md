# ❓ PeX — Cloud Reference Architecture Open Questions & Decision Register

**Document ID:** `PEX-CLOUD-OPEN-QUESTIONS-v0.1`  
**Governing Baseline:** PeX `v1.9.4` (`9e9184b`) / Enterprise Architecture `v0.2`  
**Scope:** Status and Action Plan for Architectural Open Questions (OQ-01 through OQ-10)  
**Date:** September 28, 2026  
**Status:** Authoritative Decision & Client Input Register  

---

## 1. Enterprise Open Questions Status Matrix

| # | Question / Decision Area | Impacted Cloud Component | Architecture Reference Status | Required Institutional Input | Action Plan & Fallback Default |
|:---:|---|---|---|---|---|
| **OQ-01** | **Target Enterprise Cloud Provider** | All Infrastructure | `ARCHITECTURALLY_RESOLVED` | Bank Enterprise Architecture Committee (AWS vs GCP vs Azure vs Hybrid). | Fully architected for AWS, GCP, and Azure with zero vendor lock-in. Client selects target cloud during landing zone setup. |
| **OQ-02** | **Peak Exception Throughput (TPS)** | Compute & Database Sizing | `CLIENT_INPUT_REQUIRED` | Bank Operations Sizing Team (Peak exceptions/second and daily volume). | Architecture scales from 10 to 500 TPS stress ceiling. Default sizing assumes 50,000 exceptions/day with autoscaling. |
| **OQ-03** | **Core Banking Interface Protocol** | `CoreBankingAdapter` | `CLIENT_INPUT_REQUIRED` | Bank Payment IT (REST API vs IBM MQ Series vs Apache Kafka vs CDC). | Abstract `CoreBankingAdapter` port defined. Adapter implementation built for client's specific core banking interface. |
| **OQ-04** | **Approved Enterprise LLM Provider** | `LLMGateway` | `ARCHITECTURALLY_RESOLVED` | Bank AI Governance Committee (Bedrock Claude vs Vertex Gemini vs Azure OpenAI).| Abstract `LLMGateway` port defined with adapters for Bedrock, Vertex AI, and Azure OpenAI. Switching requires changing 1 env var. |
| **OQ-05** | **Client Dual-Auth Threshold Customization**| `PolicyAuthorizationService`| `CLIENT_INPUT_REQUIRED` | Bank Risk & Operations Policy (Default is \$250,000; bank may set rail limits). | System enforces \$250,000 default. Threshold is configurable via Policy-as-Code AST rule without code changes. |
| **OQ-06** | **Historical Data Retention Period** | `ObjectEvidenceStore` (WORM)| `CLIENT_INPUT_REQUIRED` | Bank Regulatory Compliance (Default is 7 years; some regions require 10 years).| S3/GCS/Azure WORM object lock duration parameterized in Terraform IaC. Default set to 2,555 days (7 years). |
| **OQ-07** | **Disaster Recovery Target SLAs (RTO/RPO)** | Multi-Region Topology | `ARCHITECTURALLY_RESOLVED` | Bank Business Continuity Management (Default: RTO $< 15\text{m}$, RPO $< 1\text{s}$).| Multi-AZ + Cross-Region Warm Standby blueprint satisfies RTO $< 15\text{m}$ and RPO $< 1\text{s}$. |
| **OQ-08** | **Container Orchestration Runtime Model** | Application Tier Compute | `CLIENT_INPUT_REQUIRED` | Bank Cloud Infrastructure Team (Serverless Containers vs Managed Kubernetes).| Reference architecture provides dual blueprints: Serverless (Fargate/Cloud Run/ACA) vs Kubernetes (EKS/GKE/AKS). |
| **OQ-09** | **HSM Partition Tenancy Model** | Security & Token Vault | `CLIENT_INPUT_REQUIRED` | Bank Information Security (Multi-tenant Cloud KMS vs Dedicated Single-Tenant HSM).| Abstract `KeyManagementService` port supports both standard Cloud KMS CMEK and dedicated CloudHSM / Managed HSM appliances. |
| **OQ-10** | **Cross-Region DR Staging Topology** | Disaster Recovery Tier | `CLIENT_INPUT_REQUIRED` | Bank Treasury & BCP Team (Warm Standby Pilot Light vs Active-Active Multi-Region).| Default blueprint specifies Warm Standby Pilot Light ($\text{RTO} < 15\text{m}$). Active-Active multi-region available if required. |

---

## 2. Governance Resolution Summary

- **Architecturally Resolved Questions:** OQ-01, OQ-04, OQ-07 (All technical options fully designed and supported via secondary ports).
- **Client Input Required Questions:** OQ-02, OQ-03, OQ-05, OQ-06, OQ-08, OQ-09, OQ-10 (Parameter selections configured during institutional client onboarding).
- **Zero Implementation Blockers:** Every open client input has a fully defined, enterprise-grade fallback default.
