# 🔌 PeX — Port & Adapter Cloud Mapping Specification

**Document ID:** `PEX-PORT-ADAPTER-MAPPING-v0.1`  
**Governing Baseline:** PeX `v1.9.4` (`9e9184b`) / Enterprise Architecture `v0.2`  
**Scope:** Exhaustive Mapping of Secondary Ports to Concrete Cloud Adapters  
**Date:** September 28, 2026  
**Status:** Approved Reference Mapping  

---

## 1. Hexagonal Boundary Principles

1. **Port Invariance:** Secondary Port interfaces are defined in pure Python standard library types and Pydantic domain models with zero vendor imports.
2. **Adapter Isolation:** Cloud-specific SDKs (`boto3`, `google-cloud-*`, `azure-*`) reside exclusively inside adapter implementations within `backend/app/adapters/`.
3. **Runtime Dependency Injection:** The application dynamically binds concrete adapter classes at startup based on configuration environment variables (`PEX_CLOUD_PROVIDER=aws|gcp|azure`).

---

## 2. Exhaustive Secondary Port to Cloud Adapter Matrix

| Port Name | Provider-Neutral Interface Responsibility | AWS Concrete Adapter Class | GCP Concrete Adapter Class | Azure Concrete Adapter Class | Domain Impact |
|---|---|---|---|---|:---:|
| **`PersistenceRepository`** | CRUD operations on cases, payments, exceptions, rules, approvals, and audit nodes. | `AWSAuroraPostgresAdapter` (`backend/app/adapters/aws/persistence.py`) | `GCPCloudSQLPostgresAdapter` (`backend/app/adapters/gcp/persistence.py`) | `AzurePostgresFlexAdapter` (`backend/app/adapters/azure/persistence.py`) | **NONE** |
| **`SecretStore`** | Retrieval and rotation of database credentials, API keys, and internal service tokens. | `AWSSecretsManagerAdapter` (`backend/app/adapters/aws/secrets.py`) | `GCPSecretManagerAdapter` (`backend/app/adapters/gcp/secrets.py`) | `AzureKeyVaultSecretsAdapter` (`backend/app/adapters/azure/secrets.py`) | **NONE** |
| **`KeyManagementService`** | Generation of DEKs, envelope encryption, and CMK wrapping via Cloud HSM. | `AWSKMSCloudHSMAdapter` (`backend/app/adapters/aws/kms.py`) | `GCPCloudKMSHSMAdapter` (`backend/app/adapters/gcp/kms.py`) | `AzureKeyVaultManagedHSMAdapter` (`backend/app/adapters/azure/kms.py`) | **NONE** |
| **`IdentityProvider`** | Validation of incoming user JWT bearer tokens, claims extraction, and role mapping. | `AWSIAMIdentityCenterAdapter` (`backend/app/adapters/aws/identity.py`) | `GCPWorkforceIdentityAdapter` (`backend/app/adapters/gcp/identity.py`) | `AzureEntraIDIdentityAdapter` (`backend/app/adapters/azure/identity.py`) | **NONE** |
| **`EventBus`** | Publishing of asynchronous lifecycle events and dispatch messages with FIFO ordering. | `AWSSQSFIFOEventBusAdapter` (`backend/app/adapters/aws/eventbus.py`) | `GCPPubSubOrderingEventBusAdapter` (`backend/app/adapters/gcp/eventbus.py`)| `AzureServiceBusSessionAdapter` (`backend/app/adapters/azure/eventbus.py`) | **NONE** |
| **`ObjectEvidenceStore`** | Storage and immutable retrieval of raw ISO XMLs, MT files, and 7-year WORM logs. | `AWSS3ObjectLockAdapter` (`backend/app/adapters/aws/evidence.py`) | `GCPGCSBucketLockAdapter` (`backend/app/adapters/gcp/evidence.py`) | `AzureBlobImmutableStorageAdapter` (`backend/app/adapters/azure/evidence.py`)| **NONE** |
| **`LLMGateway`** | Zero-PII prompt dispatch, structured `ReasoningResult` schema validation, and fallback. | `AWSBedrockClaudeGatewayAdapter` (`backend/app/adapters/aws/llm.py`) | `GCPVertexAIGeminiGatewayAdapter` (`backend/app/adapters/gcp/llm.py`) | `AzureOpenAIGatewayAdapter` (`backend/app/adapters/azure/llm.py`) | **NONE** |
| **`PaymentRailAdapter`** | Outbound wire formatting, signature generation, and bi-directional clearing exchange.| `AWSDirectConnectRailAdapter` (`backend/app/adapters/aws/rails.py`) | `GCPInterconnectRailAdapter` (`backend/app/adapters/gcp/rails.py`) | `AzureExpressRouteRailAdapter` (`backend/app/adapters/azure/rails.py`) | **NONE** |
| **`CoreBankingAdapter`** | Querying internal Beneficiary Master Directories (BMD), SSI, and DDA balances. | `AWSInternalBMDAdapter` (`backend/app/adapters/aws/core_banking.py`) | `GCPInternalBMDAdapter` (`backend/app/adapters/gcp/core_banking.py`) | `AzureInternalBMDAdapter` (`backend/app/adapters/azure/core_banking.py`) | **NONE** |
| **`ComplianceAdapter`** | Interface with real-time sanctions screening engines (OFAC, PEP, and Watchlists). | `AWSComplianceScreeningAdapter` (`backend/app/adapters/aws/compliance.py`)| `GCPComplianceScreeningAdapter` (`backend/app/adapters/gcp/compliance.py`)| `AzureComplianceScreeningAdapter` (`backend/app/adapters/azure/compliance.py`)| **NONE** |

---

## 3. Domain Impact Verification

- **Domain Impact Assessment:** **`NONE (100% INVARIANT)`**
- **Verification Result:** Every single secondary port mapping preserves the core Pydantic domain models in `backend/app/schemas/` without requiring any changes to business rules, state machine logic, or API contracts.
