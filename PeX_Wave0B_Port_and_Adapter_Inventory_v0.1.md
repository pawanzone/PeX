# PeX Wave 0B — Port & Adapter Inventory v0.1
## Hexagonal Architecture Specification & Reference Implementations

======================================================================
1. OVERVIEW & HEXAGONAL BOUNDARY DESIGN
======================================================================

PeX operates on a strict **Hexagonal (Ports and Adapters) Architecture**. The core domain logic and resolution engine have **zero dependencies** on external infrastructure, cloud providers, specific database engines, message brokers, or third-party proprietary SDKs.

- **Ports (`backend/app/ports/`)**: Abstract Base Classes (`abc.ABC`) defining the boundary contracts.
- **Reference Adapters (`backend/app/adapters/reference/`)**: Provider-neutral, in-memory, file-based, or SQLite-backed reference implementations providing full out-of-the-box local and testing functionality.
- **Production Adapters (Future Phase 3/4)**: Drop-in replacements for enterprise infrastructure (e.g., Kafka, AWS KMS, HashiCorp Vault, PostgreSQL Aurora, Core Banking REST/gRPC) implementing the exact same Port interfaces.

---

======================================================================
2. PORT INVENTORY & SPECIFICATIONS
======================================================================

### 2.1 Configuration Store Port (`backend/app/ports/configuration_port.py`)
- **Port Interface**: `ConfigurationStorePort`
- **Purpose**: Retrieve and manage published single Bank Evidence Required JSON configurations per `(tenant_id, profile_id)`.
- **Key Methods**:
  - `get_evidence_config(tenant_id: str, profile_id: str, version: Optional[str] = None) -> Optional[BankEvidenceRequiredConfig]`
  - `publish_evidence_config(config: BankEvidenceRequiredConfig) -> PublishResult`
  - `list_active_configs(tenant_id: str) -> List[ConfigSummary]`
- **Reference Adapter**: `ReferenceConfigurationAdapter` (loads JSON configurations from filesystem / local store; defaults to standard canonical rules if tenant specific not published).

### 2.2 Evidence Store Port (`backend/app/ports/evidence_store_port.py`)
- **Port Interface**: `EvidenceStorePort`
- **Purpose**: Persist, retrieve, deduplicate, and verify acquired evidence items associated with a payment exception case.
- **Key Methods**:
  - `store_evidence(case_id: str, item: EvidenceItemModel) -> StoreEvidenceResult`
  - `get_evidence_dossier(case_id: str) -> List[EvidenceItemModel]`
  - `has_evidence_type(case_id: str, evidence_type: str) -> bool`
  - `compute_dossier_hash(case_id: str) -> str`
- **Reference Adapter**: `ReferenceEvidenceStoreAdapter` (in-memory content-addressable store with SHA-256 hash chaining and deduplication).

### 2.3 Evidence Acquisition Port (`backend/app/ports/acquisition_port.py`)
- **Port Interface**: `EvidenceAcquisitionPort`
- **Purpose**: Interface for fetching external evidence items (supporting Mode 1 Inbound, Mode 2 API Connector, Mode 3 Push, and Mode 4 HITL).
- **Key Methods**:
  - `acquire_evidence(case_id: str, request: AcquisitionRequest) -> AcquisitionResult`
  - `supports_mode(mode: AcquisitionMode) -> bool`
  - `query_source(source_id: str, query_params: Dict[str, Any]) -> SourceResponse`
- **Reference Adapter**: `ReferenceAcquisitionAdapter` (mockable reference connector simulating core banking directory, account master, and compliance lookups).

### 2.4 Core Banking Port (`backend/app/ports/core_banking_port.py`)
- **Port Interface**: `CoreBankingPort`
- **Purpose**: Read-only inquiry into bank account status, balance reservations, and customer master records.
- **Key Methods**:
  - `get_account_details(account_id: str, currency: str) -> AccountInquiryResult`
  - `verify_account_active(account_id: str) -> bool`
  - `get_client_master(client_id: str) -> ClientMasterRecord`
- **Reference Adapter**: `ReferenceCoreBankingAdapter` (in-memory lookup table against pre-loaded mock fixtures).

### 2.5 Accounting & Ledger Handoff Port (`backend/app/ports/ledger_handoff_port.py`)
- **Port Interface**: `LedgerHandoffPort`
- **Purpose**: Handoff formatted, signed, and validated repair instructions to bank downstream payment engine / ledger.
- **Key Methods**:
  - `submit_handoff_package(package: BankHandoffPackage) -> HandoffSubmissionResult`
  - `verify_handoff_acknowledgment(handoff_id: str) -> HandoffStatus`
- **Reference Adapter**: `ReferenceLedgerHandoffAdapter` (generates immutable JSON handoff artifact in output directory with SHA-256 signature and `execution_owner = "BANK"`).

### 2.6 Token Vault Port (`backend/app/ports/token_vault_port.py`)
- **Port Interface**: `TokenVaultPort`
- **Purpose**: Format-preserving tokenization and secure detokenization boundary for sensitive payment PII (IBAN, SSN, Tax ID, Account Numbers).
- **Key Methods**:
  - `tokenize(plain_text: str, token_type: TokenType) -> str`
  - `detokenize(token: str) -> str`
  - `is_token(value: str) -> bool`
- **Reference Adapter**: `ReferenceTokenVaultAdapter` (deterministic HMAC-SHA256 based format-preserving tokenization with zero plain-text storage).

---

======================================================================
3. ADAPTER REGISTRY & DEPENDENCY INJECTION
======================================================================

Wave 0B provides a centralized service factory / dependency injection container (`backend/app/services/container.py` or service registry):
- Allows unit tests and E2E harness to inject in-memory reference adapters.
- Allows production configurations to inject enterprise adapters via configuration flags without changing domain code.
- Guarantees fail-safe fallback: If no tenant-specific override is found, the reference configuration falls back to the published baseline canonical schema.

---

======================================================================
4. AST PROVIDER-NEUTRALITY ENFORCEMENT
======================================================================

An automated AST static analysis test (`tests/contracts/test_provider_neutrality.py`) verifies that no forbidden imports exist in:
- `backend/app/domain/`
- `backend/app/ports/`
- `backend/app/services/`
- `backend/app/schemas/`

Forbidden imports include: `boto3`, `google.cloud`, `azure`, `kafka`, `pika`, `redis`, `openai`, `anthropic`, `langchain`. All external integrations must reside exclusively inside `backend/app/adapters/`.
