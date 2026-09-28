# 📜 PeX — Cloud Reference Architecture Decision Records (ADRs)

**Document ID:** `PEX-CLOUD-ADRS-v0.1`  
**Governing Baseline:** PeX `v1.9.4` (`9e9184b`) / Enterprise Architecture `v0.2`  
**Scope:** Architectural Decision Records ADR-001 through ADR-012  
**Date:** September 28, 2026  
**Status:** Approved Reference Architecture Decision Records  

---

## ADR-001: Hexagonal Architecture (Ports and Adapters)
- **Status:** Approved / Enforced
- **Decision:** All infrastructure interactions (persistence, messaging, encryption, AI, clearing rails) are mediated through abstract secondary ports.
- **Context:** PeX must deploy across AWS, GCP, Azure, and On-Premises environments without altering the core domain model.
- **Consequences:** Core domain logic in `backend/app/schemas/` and `services/` contains zero cloud SDK imports.

## ADR-002: Cloud Provider Neutrality
- **Status:** Approved / Enforced
- **Decision:** AWS, GCP, and Azure are treated as peer reference implementations with zero architectural preference or declared winner.
- **Context:** Financial institutions maintain distinct cloud vendor partnerships and regulatory landing zones.
- **Consequences:** Switching cloud providers is achieved via configuration environment variables binding different adapter classes with zero core code edits.

## ADR-003: Zero-Trust Perimeter Tokenization & HSM KMS Boundary
- **Status:** Approved / Enforced
- **Decision:** Tokenize all sensitive account numbers, IBANs, PANs, and party names into format-preserving surrogate tokens (`TOK_IBAN_...`) at the perimeter before payload ingestion.
- **Context:** Bank privacy regulations (GDPR, GLBA) strictly prohibit sending customer PII to external AI foundation models.
- **Consequences:** Foundation models operate exclusively on surrogate tokens; detokenization is restricted to the outbound wire dispatch hub.

## ADR-004: Enterprise Identity Federation & Maker-Checker SoD
- **Status:** Approved / Enforced
- **Decision:** Delegate authentication to corporate OIDC/SAML 2.0 IdPs while enforcing Segregation of Duties (\$0 Operator limit) and Level-2 Dual Authorization ($\ge \$250\text{k}$) inside the PeX authorization engine.
- **Context:** FFIEC and internal audit mandates require strict separation between investigation and payment release authority.
- **Consequences:** Operators cannot self-approve; high-value payments require two distinct authorized signatures.

## ADR-005: Multi-AZ Relational Persistence (PostgreSQL 16 3NF)
- **Status:** Approved / Enforced
- **Decision:** Standardize relational persistence on PostgreSQL 16 (3NF normalized tables) deployed on managed multi-AZ cloud clusters (Aurora / Cloud SQL / PG Flex).
- **Context:** High-concurrency banking operations mandate ACID compliance, row-level locking, and 35-day continuous Point-in-Time Recovery.
- **Consequences:** Complete cross-cloud SQL portability using standard SQLAlchemy and asyncpg drivers.

## ADR-006: Two-Tier Event-Driven Messaging & Idempotency
- **Status:** Approved / Enforced
- **Decision:** Enforce technical transport deduplication on FIFO brokers paired with business payment idempotency on distributed database transaction locks.
- **Context:** Network drops and automated retries must never cause duplicate wire disbursements.
- **Consequences:** Exactly-once business execution is guaranteed regardless of transport delivery retries.

## ADR-007: Non-Invasive Sidecar Integration via Secondary Ports
- **Status:** Approved / Enforced
- **Decision:** Encapsulate external payment network (SWIFT, Fedwire, Core Banking) communication behind `PaymentRailAdapter`, `CoreBankingAdapter`, and `ComplianceAdapter` ports.
- **Context:** PeX operates as an intelligent overlay connecting to existing bank payment queues without replacing core systems.
- **Consequences:** Changes to external rail formats do not impact internal exception resolution logic.

## ADR-008: Model-Agnostic AI Gateway with JSON Contracts
- **Status:** Approved / Enforced
- **Decision:** Abstract all LLM interactions behind the `LLMGateway` port, validating outputs against the canonical `ReasoningResult` JSON contract.
- **Context:** Banks use diverse private AI models (Bedrock Claude, Vertex Gemini, Azure OpenAI).
- **Consequences:** Switching AI model providers requires modifying a single environment variable with zero code changes.

## ADR-009: Cognitive Safety & Deterministic Validation Precedence
- **Status:** Approved / Enforced
- **Decision:** Mandate that the AI Reasoner is strictly advisory (\$0.00 approval authority) and that deterministic mathematical checks (ISO 7064 MOD-97-10 check digit, ABA 9-digit checksum) unconditionally overrule AI confidence scores.
- **Context:** Preventing hallucinated account numbers or invalid routing codes from reaching clearing rails.
- **Consequences:** High AI confidence cannot bypass mathematical validation failures.

## ADR-010: Linear Provenance Hash Chain with Cloud Merkle Root Anchoring
- **Status:** Approved / Enforced
- **Decision:** Chain all 20 lifecycle stages into a continuous linear SHA-256 hash sequence in the transactional DB, while daily batch digests are hierarchically aggregated into Merkle Roots anchored to WORM object storage.
- **Context:** Regulatory compliance requires mathematical proof of audit trail tamper-evidence.
- **Consequences:** Immediate linear tamper detection in transactional processing combined with efficient batch verification for 7-year regulatory audits.

## ADR-011: Multi-AZ High Availability & Cross-Region Disaster Recovery
- **Status:** Approved / Enforced
- **Decision:** Mandate Multi-AZ active-active compute and synchronous database replication within the primary region ($\text{RPO} < 1\text{s}$), paired with cross-region asynchronous standby replication ($\text{RTO} < 15\text{m}$).
- **Context:** Critical payment infrastructure requires continuous operation and rapid recovery during regional outages.
- **Consequences:** Satisfies Tier-1 banking business continuity mandates.

## ADR-012: OpenTelemetry Distributed Observability & SLA Radar
- **Status:** Approved / Enforced
- **Decision:** Standardize application telemetry on OpenTelemetry (OTel), injecting standard correlation IDs (`uetr`, `case_id`) across all microservice spans and logs.
- **Context:** End-to-end transaction visibility and real-time RTGS clearing cutoff deadline tracking are mandatory.
- **Consequences:** Traces, metrics, and logs stream seamlessly to CloudWatch, Google Cloud Monitoring, or Azure Monitor.
