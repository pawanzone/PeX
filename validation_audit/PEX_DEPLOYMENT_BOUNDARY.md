# PeX — Deployment Boundary & Architectural Transition Blueprint

**Authoritative Boundary Definition: Current Prototype / Replit Sandbox vs. Future Enterprise Production**  
**Version:** `1.0.0`  
**Date:** September 23, 2026  

---

## 1. Executive Summary & Purpose

This document defines the strict architectural boundary between:
1. **Current State:** The PeX Prototype & Replit Validation Environment (fast, deterministic, zero-infrastructure cost, self-contained single-node runtime).
2. **Future State:** The PeX Enterprise Banking Cloud Production Deployment (highly-available, multi-AZ, FIPS 140-2 Level 3 KMS, distributed PostgreSQL, SQS/PubSub/ServiceBus FIFO queues, enterprise SSO, WORM audit vaults).

This distinction guarantees that prototype implementations (such as SQLite, in-process token vaults, and mock ICD adapters) are explicitly understood as **local development adapters** rather than permanent production infrastructure, while preserving the exact same domain core across both environments.

---

## 2. Deployment Architecture Boundary Diagram

```
====================================================================================================
 CURRENT VALIDATION BOUNDARY                               FUTURE ENTERPRISE PRODUCTION BOUNDARY
 (Replit Sandbox / Local Development)                      (AWS / GCP / Azure Tier-1 Banking Cloud)
====================================================================================================

 +-----------------------------------+                     +-----------------------------------+
 |         USER INTERFACE            |                     |       ENTERPRISE FRONTEND         |
 | * React SPA served directly via   |                     | * CloudFront / Cloud CDN / Azure  |
 |   FastAPI StaticFiles fallback    |                     |   Front Door Global Edge CDN      |
 | * Single port (8000 / 5000)       |                     | * WAF v2 DDoS & Bot Mitigation    |
 +-----------------+-----------------+                     +-----------------+-----------------+
                   |                                                         |
                   v                                                         v
 +-----------------------------------+                     +-----------------------------------+
 |     APPLICATION RUNTIME LAYER     |                     |    MANAGED CONTAINER CLUSTER      |
 | * Single Uvicorn ASGI Process     |                     | * AWS ECS Fargate / GKE / AKS     |
 | * Python 3.11 Runtime             |                     | * Auto-Scaling (10 -> 200 tasks)  |
 | * In-Process ThreadPoolExecutor   |                     | * Private VPC Subnets (No Public) |
 +-----------------+-----------------+                     +-----------------+-----------------+
                   |                                                         |
                   |                                                         |
 ==================v=========================================================v======================
                     PeX DOMAIN CORE (IDENTICAL & UNCHANGED IN BOTH ENVIRONMENTS)
   * Canonical ISO 20022 Data Models (pacs.008, pacs.004, pacs.002, camt.056, camt.029, camt.054)
   * 41 BIAN Exception Profiles across 5 Market Domains
   * Policy-as-Code AST Compiler & Impact Simulation Engine
   * Maker-Checker Dual-Authorization State Machine & Role Entitlement Limits
   * Governed STP & Supervised Batch Release Engine
   * Cryptographic SHA-256 Merkle Provenance Audit Trail
 ==================v=========================================================v======================
                   |                                                         |
                   | (Local File / In-Memory Adapters)                       | (Distributed Cloud Ports)
                   v                                                         v
 +-----------------------------------+                     +-----------------------------------+
 |     LOCAL DATA & STORAGE PORTS    |                     |   ENTERPRISE CLOUD INFRASTRUCTURE |
 | * Relational: SQLite (File/Mem)   |                     | * Relational: Multi-AZ PostgreSQL |
 | * Secrets: .env / Replit Secrets  |                     |   (Aurora / AlloyDB / Flexible PG)|
 | * Encryption: AES-256 Software KMS|                     | * Secrets: AWS/GCP/Azure SecMgr   |
 | * Token Vault: In-Memory / SQLite |                     | * Key Mgmt: Dedicated Cloud HSM   |
 | * Messaging: In-Process AsyncQueue|                     | * Messaging: SQS FIFO / PubSub /  |
 | * ICD Adapters: Staged Mock Data  |                     |   Azure Service Bus FIFO          |
 | * AI Gateway: Deterministic Mock  |                     | * Live Adapters: Fedwire / SWIFT  |
 | * Audit: Append-only JSONL / DB   |                     | * AI Gateway: Vertex / Bedrock    |
 |                                   |                     | * Audit: S3 / GCS / Azure WORM    |
 +-----------------------------------+                     +-----------------------------------+
====================================================================================================
```

---

## 3. Side-by-Side Component Boundary Specification

| Architectural Dimension | Current Prototype / Replit Validation | Future Enterprise Cloud Production |
|---|---|---|
| **Primary Compute** | Single-instance Uvicorn ASGI server running inside Replit workspace container. | Multi-AZ auto-scaling container fleet (AWS ECS Fargate, GCP Cloud Run, Azure Container Apps) with zero-downtime rolling deploys. |
| **Relational Database** | SQLite 3 (`./pex_enterprise.db`) with automatic table migration and synthetic data hydration. | High-availability PostgreSQL cluster (Amazon Aurora Global Database, Google AlloyDB, Azure PostgreSQL Flexible Server) with Multi-AZ sync replication, read replicas, and continuous PITR. |
| **Secrets & Keys** | Project environment variables (`.replit`, `.env`, Replit Secrets store). | Cloud Secrets Manager (AWS Secrets Manager, Google Secret Manager, Azure Key Vault) with automated 90-day key rotation and IAM-gated access. |
| **PII Isolation & Encryption** | Software-based AES-256-GCM and SHA-256 HMAC utilizing local static master key. | Hardware-backed envelope encryption utilizing Customer Managed Keys (CMKs) in dedicated FIPS 140-2 Level 3 Cloud HSMs. |
| **Token Vault Storage** | In-process surrogate token mapping stored in SQLite / memory. | Microsegmented, isolated Tokenization Vault in dedicated VPC with strict network isolation and hardware token generation. |
| **Identity & Access (IAM)** | Mock personas with predefined roles (`OP-9012`, `APR-3191`, `CMP-4401`) and hardcoded monetary limits. | Enterprise Identity Federation (SAML 2.0 / OIDC) integrated with corporate Active Directory / Okta / Entra ID, enforcing RBAC/ABAC and MFA. |
| **Clearing Directory Adapters** | Pre-staged in-memory ICD nodes and static mock registries (SWIFT BIC, Fedwire ABA, IBAN MOD-97 tables). | Real-time live ICD integration adapters via mutual TLS (mTLS) to Federal Reserve FedLine Direct, SWIFT Alliance Gateway, and Core Banking APIs. |
| **Asynchronous Messaging** | Python `asyncio.Queue` and threadpool workers for batch STP execution. | Distributed FIFO message bus (Amazon SQS FIFO, Google Cloud Pub/Sub, Azure Service Bus) with dead-letter suspense queues and distributed locks (Redis / DynamoDB). |
| **AI / LLM Reasoning** | Deterministic synthetic reasoner (`MODEL_GATEWAY_MODE=mock`) reproducing exact BIAN recommendations without external network calls. | Enterprise Private LLM endpoints (Amazon Bedrock Anthropic Claude 3.5 Sonnet, Google Vertex AI Gemini 1.5 Pro, Azure OpenAI GPT-4o) with Zero Data Retention agreements. |
| **Audit Log Archival** | Local SHA-256 Merkle-like hash chain persisted in SQLite database and JSONL logs. | Write-Once-Read-Many (WORM) compliant immutable cloud object storage (Amazon S3 Object Lock, GCP Bucket Lock, Azure Immutable Storage) for 7-year regulatory retention. |
| **Network & Perimeter** | Replit standard container networking; single public HTTPS port with SSL termination by Replit. | Zero-Trust Architecture: Private VPC subnets, AWS PrivateLink / GCP Private Service Connect, Web Application Firewall (WAF) with OWASP Top 10 mitigation. |

---

## 4. Architectural Transition Safeguards

To prevent prototype technical debt from leaking into production designs, PeX enforces three transition safeguards:

1. **Strict Interface Decoupling (Hexagonal Ports):** All storage, security, and messaging interactions are mediated through abstract Python protocols (`backend/app/db/repository.py`, `backend/app/core/security.py`, `backend/app/services/model_gateway.py`). No database queries or external API calls are written directly in business logic.
2. **Schema Invariant:** The Canonical Payment, Canonical Exception, Approval Request, and Audit Node Pydantic schemas are 100% identical between Replit and Enterprise Cloud.
3. **Environment-Driven Adapter Binding:** Switching from the local prototype to enterprise cloud requires zero core code changes; it is accomplished purely by configuring `DATABASE_URL` (to PostgreSQL) and setting the appropriate cloud adapter environment variables.
