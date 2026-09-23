# PeX — Cloud-Provider Agnostic Architecture & Model-Neutral Gateway Specification

**Authoritative Architecture Specification for the Payment Exception Resolution (PeX) Platform**  
**Version:** `1.0.0` (Aligned with PeX Release `v1.9.4` / Replit Readiness Baseline)  
**Date:** September 23, 2026  
**Target Environments:** Replit Sandbox, Local Development, AWS, Google Cloud Platform (GCP), Microsoft Azure  

---

## 1. Executive Summary & Core Architectural Principle

The **Payment Exception Resolution (PeX)** platform is architected according to **Hexagonal Architecture (Ports and Adapters)** principles. The business domain—encompassing canonical ISO 20022 / SWIFT message models, BIAN-aligned exception taxonomies across 5 banking domains, Maker-Checker dual authorization, Policy-as-Code AST rules, and deterministic repair execution—is strictly isolated from underlying cloud infrastructure, database engines, message brokers, identity providers, and large language model (LLM) providers.

```
       +-------------------------------------------------------------+
       |                     PRIMARY ADAPTERS                        |
       |  [FastAPI HTTP / REST]   [Event Ingestion]   [React UI]     |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                       PeX CORE DOMAIN                       |
       |  * Canonical Data Model (ISO 20022 / pacs / camt)           |
       |  * 41 BIAN Exception Taxonomy & Domain Classifiers          |
       |  * Policy-as-Code (AST Compiler & Simulation Engine)        |
       |  * Maker-Checker & Dual-Authorization State Machine         |
       |  * Governed STP & Fast-Lane Release Engine                  |
       |  * Zero-PII Context Assembly & Surrogate Token Vault        |
       |  * Cryptographic SHA-256 Merkle Audit Chain                 |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                    SECONDARY PORTS                          |
       |  [SecretStore] [KMS] [IdP] [Persistence] [EventBus] [LLM]   |
       +------------------------------+------------------------------+
                                      |
       +------------------------------+------------------------------+
       |                    SECONDARY ADAPTERS                       |
       |  Replit/Local  |     AWS      |     GCP      |    Azure     |
       |  --------------+--------------+--------------+------------- |
       |  * SQLite      | * Aurora PG  | * Cloud SQL  | * Azure PG   |
       |  * EnvSecrets  | * SecretsMgr | * SecretMgr  | * Key Vault  |
       |  * In-Memory   | * SQS FIFO   | * Pub/Sub    | * Svc Bus    |
       |  * Mock AI     | * Bedrock    | * Vertex AI  | * Azure AI   |
       +-------------------------------------------------------------+
```

---

## 2. Pluggable Ports & Secondary Interfaces

To ensure complete independence from vendor lock-in, all external dependencies communicate with the PeX domain through abstract secondary interfaces.

### 2.1. Secret Store Port (`SecretStore`)
Handles secure storage, rotation, and retrieval of credentials, API tokens, and database passwords.
```python
from abc import ABC, abstractmethod
from typing import Dict, Optional

class SecretStore(ABC):
    @abstractmethod
    def get_secret(self, secret_name: str) -> str:
        """Retrieve plaintext secret by identifier."""
        pass

    @abstractmethod
    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set or rotate a secret value."""
        pass
```
- **Local/Replit Adapter:** `EnvironmentSecretStore` reading from environment variables or `.env` / Replit Secrets.
- **AWS Adapter:** `AWSSecretsManagerStore` calling AWS Secrets Manager.
- **GCP Adapter:** `GCPSecretManagerStore` calling Google Secret Manager.
- **Azure Adapter:** `AzureKeyVaultSecretStore` calling Azure Key Vault Secrets.

---

### 2.2. Key Management Service Port (`KeyManagementService`)
Handles envelope encryption, data-key generation, and cryptographic operations for PII isolation in the Token Vault.
```python
class KeyManagementService(ABC):
    @abstractmethod
    def generate_data_key(self, key_id: str) -> Dict[str, bytes]:
        """Generate plaintext data key and ciphertext wrapped data key."""
        pass

    @abstractmethod
    def decrypt_data_key(self, ciphertext_key: bytes, key_id: str) -> bytes:
        """Decrypt wrapped data key using root KMS customer-managed key (CMK)."""
        pass

    @abstractmethod
    def sign_audit_payload(self, payload_hash: str, key_id: str) -> str:
        """Generate asymmetric cryptographic signature for audit seal."""
        pass
```
- **Local/Replit Adapter:** `SoftwareKMS` utilizing local AES-256-GCM / HMAC-SHA256 with static master keys.
- **AWS Adapter:** `AWSKMSAdapter` utilizing AWS KMS with Customer Managed Keys (CMKs).
- **GCP Adapter:** `GCPCloudKMSAdapter` utilizing Cloud KMS keyrings.
- **Azure Adapter:** `AzureKeyVaultKMSAdapter` utilizing Azure Key Vault Hardware Security Modules (HSMs).

---

### 2.3. Identity Provider Port (`IdentityProvider`)
Handles user authentication, SSO token introspection, role resolution, and Maker-Checker segregation of duties.
```python
class IdentityProvider(ABC):
    @abstractmethod
    def authenticate_token(self, bearer_token: str) -> Dict[str, Any]:
        """Validate OIDC / SAML token and return standardized ClaimsPrincipal."""
        pass

    @abstractmethod
    def get_user_persona(self, user_id: str) -> Optional["Persona"]:
        """Resolve enterprise user, active role, permissions, and monetary limits."""
        pass
```
- **Local/Replit Adapter:** `MockIdentityProvider` mapping pre-configured deterministic personas (`OP-9012`, `APR-3191`, `CMP-4401`).
- **AWS Adapter:** `AWSCognitoAdapter` or `AWS_IAM_IdentityCenterAdapter`.
- **GCP Adapter:** `GCPCloudIdentityAdapter` or `FirebaseAuthenticationAdapter`.
- **Azure Adapter:** `MicrosoftEntraIDAdapter` (Azure AD).

---

### 2.4. Persistence Repository Port (`PersistenceRepository`)
Provides relational persistence and querying for Canonical Cases, Rules AST, Approvals, and Audit Nodes.
```python
class PersistenceRepository(ABC):
    @abstractmethod
    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_case(self, case_data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def list_cases(self, queue: Optional[str] = None, status: Optional[str] = None, profile: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def append_audit_node(self, audit_node: "AuditNode") -> None:
        pass
```
- **Local/Replit Adapter:** `SQLiteRepository` utilizing SQLAlchemy or lightweight SQLite engine with memory caching.
- **Enterprise Adapter (AWS/GCP/Azure):** `PostgreSQLRepository` connecting to AWS Aurora PostgreSQL, Google Cloud SQL for PostgreSQL, or Azure Database for PostgreSQL Flexible Server via connection pooling (PgBouncer).

---

### 2.5. Event Bus Port (`EventBus`)
Handles distributed asynchronous event streaming for inbound bank events, telemetry, and outbound clearing messages.
```python
class EventBus(ABC):
    @abstractmethod
    def publish_event(self, topic_or_channel: str, event_payload: Dict[str, Any], correlation_id: str) -> str:
        """Publish event to distributed queue with guaranteed delivery."""
        pass

    @abstractmethod
    def subscribe(self, topic_or_channel: str, handler_callback: Any) -> None:
        """Register subscriber for asynchronous message processing."""
        pass
```
- **Local/Replit Adapter:** `InMemoryEventBus` / `AsyncQueueEventBus`.
- **AWS Adapter:** `AmazonSQSFIFOAdapter` / `AmazonEventBridgeAdapter`.
- **GCP Adapter:** `GCPCloudPubSubAdapter`.
- **Azure Adapter:** `AzureServiceBusAdapter` (Sessions/FIFO).

---

### 2.6. Object Evidence Store Port (`ObjectEvidenceStore`)
Handles archival storage of raw ISO 20022 XML messages, SWIFT MT text, and immutable evidence blobs.
```python
class ObjectEvidenceStore(ABC):
    @abstractmethod
    def put_evidence(self, bucket: str, object_key: str, data: bytes, content_type: str) -> str:
        """Store raw evidence payload and return immutable URI."""
        pass

    @abstractmethod
    def get_evidence(self, bucket: str, object_key: str) -> bytes:
        """Retrieve raw evidence payload."""
        pass
```
- **Local/Replit Adapter:** `LocalFileSystemEvidenceStore` inside project `./storage/`.
- **AWS Adapter:** `AmazonS3Adapter` with Object Lock (WORM).
- **GCP Adapter:** `GoogleCloudStorageAdapter` with Bucket Retention Policy.
- **Azure Adapter:** `AzureBlobStorageAdapter` with Immutable Blob Storage.

---

## 3. Model-Neutral AI Gateway (`LLMGateway`)

The AI Reasoner within PeX is strictly provider-agnostic. The PeX core isolates all PII before the context is assembled, sending only format-preserving surrogate tokens and canonical exception metadata to the AI Gateway.

```
+-------------------------------------------------------------+
|                      PeX Core Context                       |
|   * Zero PII Context (Tokens: TOK_IBAN_..., TOK_AMT_...)    |
|   * BIAN Exception Profile & Domain Grounding Rules         |
|   * Clearing Directory Verification Facts (SSI, BIC, IMAD)  |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                    LLMGateway Interface                     |
|   +generate_reasoning(context: ZeroPiiContext) -> Result    |
+------------------------------+------------------------------+
                               |
       +-----------------------+-----------------------+
       |                       |                       |
       v                       v                       v
+---------------+       +---------------+       +---------------+
|  Mock Reasoner|       | Google Gemini |       | Anthropic/    |
|  (Deterministic       | (Vertex AI /  |       | OpenAI /      |
|   Synthetic)  |       |  GenerativeAI)|       | Bedrock Cl.   |
+---------------+       +---------------+       +---------------+
       |                       |                       |
       +-----------------------+-----------------------+
                               |
                               v
+-------------------------------------------------------------+
|                Standardized ReasoningResult                 |
|   * action_type: REPAIR_AND_RELEASE | ESCALATE | RETURN     |
|   * confidence_score: float (0.0 to 1.0)                    |
|   * proposed_changes: List[CorrectionPatch]                 |
|   * evidence_corroboration: List[CorroborationCheck]        |
|   * policy_rationale: str                                   |
+-------------------------------------------------------------+
```

### 3.1. Standardized Reasoning Contract
Regardless of model provider (Gemini 1.5 Pro, Claude 3.5 Sonnet, GPT-4o, or Bedrock Titan/Llama), all outputs are validated and parsed into the canonical `ReasoningResult` schema.

```python
class CorrectionPatch(BaseModel):
    field_path: str
    original_value: Any
    proposed_value: Any
    rationale: str
    validation_rule: str

class CorroborationCheck(BaseModel):
    source: str
    status: str  # VERIFIED | FAILED | NOT_APPLICABLE
    details: str

class ReasoningResult(BaseModel):
    action_type: str  # "REPAIR_AND_RELEASE", "ESCALATE_TO_COMPLIANCE", "RETURN_PAYMENT", "REQUEST_BENEFICIARY_INFO"
    confidence_score: float
    policy_code: str
    proposed_changes: List[CorrectionPatch]
    evidence_corroboration: List[CorroborationCheck]
    rationale: str
```

### 3.2. Configuration Switching
The active gateway implementation is selected via configuration:
```bash
# Model Gateway Provider Selection
MODEL_GATEWAY_MODE=mock      # Deterministic synthetic reasoning (Replit / CI/CD)
MODEL_GATEWAY_MODE=gemini    # Google Gemini Pro / Flash on Vertex AI
MODEL_GATEWAY_MODE=openai    # OpenAI GPT-4o / Azure OpenAI
MODEL_GATEWAY_MODE=bedrock   # AWS Bedrock Claude / Titan
```

---

## 4. Multi-Cloud Implementation Mapping

PeX services map cleanly across all major cloud platforms without altering domain logic:

| Functional Domain | Replit / Local Dev | Amazon Web Services (AWS) | Google Cloud Platform (GCP) | Microsoft Azure |
|---|---|---|---|---|
| **Web / API Compute** | Python 3.11 / Uvicorn | AWS ECS Fargate / EKS | Google Cloud Run / GKE | Azure Container Apps / AKS |
| **Relational Database** | SQLite 3.x (In-Process) | Amazon Aurora PostgreSQL | Google Cloud SQL for PG | Azure Database for PG Flex |
| **Secrets Management** | `.replit` / Env Secrets | AWS Secrets Manager | Google Cloud Secret Manager | Azure Key Vault Secrets |
| **Envelope Encryption (KMS)** | Local Software KMS (AES-256) | AWS KMS (CMK) | Google Cloud KMS | Azure Key Vault Managed HSM |
| **Identity & Access (IdP)** | Mock Personas (Deterministic) | AWS Cognito / IAM Id Center | Google Cloud Identity / Firebase | Microsoft Entra ID (Azure AD) |
| **Event Bus / Messaging** | In-Memory Async Queue | Amazon SQS FIFO / EventBridge | Google Cloud Pub/Sub | Azure Service Bus (FIFO) |
| **Object Evidence Storage** | Local File System (`./storage`) | Amazon S3 (Object Lock WORM) | Google Cloud Storage (Bucket Retention) | Azure Immutable Blob Storage |
| **AI / LLM Reasoner** | Synthetic Deterministic Model | Amazon Bedrock (Claude/Titan) | Google Vertex AI (Gemini 1.5) | Azure OpenAI Service (GPT-4o) |
| **Log Immutability** | SHA-256 Hash Chain File | AWS CloudWatch + S3 WORM | Google Cloud Logging + GCS Lock | Azure Monitor + Blob Immutability |

---

## 5. Architectural Verification & Zero-Leakage Guarantee

1. **Zero Cloud-Specific Imports in Core:** Core domain models (`backend/app/schemas/canonical.py`, `backend/app/services/approval_engine.py`, `backend/app/services/decision_engine.py`, `backend/app/core/tokenization.py`) contain zero SDK imports from `boto3`, `google-cloud-*`, or `azure-*`.
2. **Zero PII Exposure to AI:** All payload fields containing names, account numbers, or identification numbers are transformed to format-preserving surrogate tokens before invoking any LLM provider.
3. **Deterministic Local Execution:** The entire 20-step payment exception lifecycle, Maker-Checker dual authorization, and Policy-as-Code engine execute 100% locally in Replit and CI/CD pipelines without external cloud credentials.
