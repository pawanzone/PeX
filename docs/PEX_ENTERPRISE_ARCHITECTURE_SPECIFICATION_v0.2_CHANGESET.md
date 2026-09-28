# 📋 PeX Enterprise Architecture Specification v0.2 Changeset

**Document ID:** `PEX-SPEC-v0.2-CHANGESET`  
**Base Document:** `docs/PEX_ENTERPRISE_ARCHITECTURE_SPECIFICATION_v0.1.md`  
**Governing Baseline:** PeX `v1.9.4` (`9e9184b`)  
**Date:** September 28, 2026  
**Status:** Authoritative Patch Changeset for Enterprise Architecture v0.2  

---

## Changeset Entry 1: Cryptographic Provenance Terminology (GAP-01)

- **Finding:** GAP-01 (`TERMINOLOGY_ISSUE` / Medium)
- **Current v0.1 Statement (§3, §15.1, §21 ADR-005):**
  > "Continuous SHA-256 Merkle Provenance Hash Chain Chaining every state transition across all 20 lifecycle stages..."
- **Problem:**
  The mathematical hash chaining formula in §15.1:
  $$\text{Current\_Hash}_n = \text{SHA-256}(\text{Node\_ID} \,\|\, \dots \,\|\, \text{Previous\_Hash}_{n-1})$$
  is technically a **Linear Cryptographic Hash Chain** (like git or blockchain blocks), rather than a hierarchical Merkle Tree or Merkle DAG. Calling it a "Merkle Provenance Chain" introduces terminological ambiguity regarding whether intermediate branch proofs exist.
- **Proposed v0.2 Statement:**
  > "Continuous SHA-256 Linear Provenance Hash Chain with Cloud Merkle Tree Root Anchoring. Core state transitions are chained linearly across all 20 lifecycle stages to guarantee immediate mathematical tamper detection. In enterprise cloud deployments, daily linear chain digests are hierarchically aggregated into a daily Merkle Root anchored into WORM Object Storage for efficient batch verification."
- **Reason:** Accurately reflects mathematical implementation in code while defining the enterprise cloud batch archival extension.
- **Impact:** Aligns documentation to `MST-010` and eliminates architectural confusion.

---

## Changeset Entry 2: Advisory Status of AI Reasoning Output (GAP-02)

- **Finding:** GAP-02 (`AI_GOVERNANCE_GAP` / High)
- **Current v0.1 Statement (§3 Layer 4, §13.1):**
  > "Model Gateway formats zero-PII prompt, enforces JSON schema output, and validates output against `ReasoningResult` contract."
- **Problem:**
  Does not explicitly state in the architectural layer description that `ReasoningResult` is strictly non-authoritative and possesses zero approval or release authority.
- **Proposed v0.2 Statement:**
  > "The AI Reasoner and its structured `ReasoningResult` output are **strictly advisory**. The AI Reasoner possesses \$0.00 approval authority, zero payment release capability, zero compliance waiver authority, and cannot override deterministic validation failures. All proposed mutations must pass deterministic validation, policy AST evaluation, and human Maker-Checker authorization prior to execution."
- **Reason:** Institutional banking regulators require explicit architectural proof that AI cannot autonomously disburse funds or bypass controls.
- **Impact:** Eliminates compliance ambiguity and hardens AI governance boundaries.

---

## Changeset Entry 3: Level 5 Autonomy Bounds & Clearing Safeguards (GAP-03)

- **Finding:** GAP-03 (`ARCHITECTURE_AMBIGUITY` / High)
- **Current v0.1 Statement (§14 Autonomy Table):**
  > "Level 5 (Autonomous Multi-Agent): Self-Healing Multi-Rail Routing: Dynamic clearing re-route $\le \$2,500$ Real-Time Policy & Sanctions Gate, Automated Clearing Recall (camt.056)."
- **Problem:**
  Autonomous multi-rail rerouting without explicit pre-flight RTGS cutoff checks, nostro liquidity reservation, and sanctions re-screening creates high clearing operational risk.
- **Proposed v0.2 Statement:**
  > "Level 5 (Governed Dynamic Multi-Rail Re-routing): Autonomous alternative rail rerouting (e.g. SWIFT to Fedwire/CHIPS) for micro-payments $\le \$2,500.00$. Mandates deterministic pre-flight RTGS clearing cutoff verification, real-time sanctions re-screening via `ComplianceAdapter`, Nostro liquidity reservation in `CoreBankingAdapter`, and instant cryptographic audit node generation. In the event of destination rail rejection, automated `camt.056` recall is dispatched with immediate operator escalation."
- **Reason:** Guarantees that clearing reroutes comply with FATF Travel Rule, liquidity thresholds, and clearing cutoffs.
- **Impact:** Protects bank against settlement failures and regulatory breaches.

---

## Changeset Entry 4: Business Idempotency vs. Transport Deduplication (GAP-04)

- **Finding:** GAP-04 (`ARCHITECTURE_AMBIGUITY` / Medium)
- **Current v0.1 Statement (§12.2):**
  > "Deduplication: Exactly-once semantics via transactional outbox pattern and distributed deduplication keys."
- **Problem:**
  Conflates transport-level message deduplication (e.g. SQS FIFO 5-minute deduplication window) with persistent business-level payment release idempotency.
- **Proposed v0.2 Statement:**
  > "Two-Tier Idempotency Architecture:
  > 1. **Technical Transport Deduplication:** Effectively-once delivery on message brokers using `MessageDeduplicationId` generated from `SHA256(event_id || timestamp)`.
  > 2. **Business Payment Idempotency:** Exactly-once wire release enforced via distributed Redis/DB locking on `idempotency_key` tied to `(uetr, action_type, case_id)`. Submitting duplicate execution requests returns cached delivery receipts without re-transmitting to clearing networks."
- **Reason:** Prevents duplicate wire releases under network retries and distributed consumer racing.
- **Impact:** Clarifies exact implementation contracts for cloud engineers.

---

## Changeset Entry 5: Token Vault IAM Boundary & Key Rotation Replay (GAP-05)

- **Finding:** GAP-05 (`SECURITY_GAP` / Medium)
- **Current v0.1 Statement (§10.1, §17.2):**
  > "Controlled Detokenization Gate: Strictly Gated to Outbound Dispatcher..."
- **Problem:**
  Lacks explicit specification of service-to-service IAM credentials, mTLS client identity validation, and key version handling during historical audit replay.
- **Proposed v0.2 Statement:**
  > "Detokenization Service-to-Service IAM Policy: Detokenization APIs are restricted strictly to the Outbound Clearing Dispatcher service principal via Mutual TLS (mTLS) client certificate verification and Cloud IAM KMS Decrypt policies (`kms:Decrypt` restricted to `arn:...:role/pex-dispatcher-service`). During annual KMS CMK key rotation, historical records retain Key ID references (`key_version_id`), enabling transparent historical audit replay without re-encrypting existing vault records."
- **Reason:** Hardens the most critical PII boundary in the system against unauthorized internal service access.
- **Impact:** Satisfies PCI-DSS Requirement 3 and FFIEC cryptographic architecture audits.

---

## Changeset Entry 6: NFR Sizing Categorization (GAP-06)

- **Finding:** GAP-06 (`NFR_GAP` / Medium)
- **Current v0.1 Statement (§16 NFR Table):**
  > "Throughput & Scale: 100 to 500 TPS (Peak throughput of 50,000+ exceptions/day)..."
- **Problem:**
  Could be mistaken for committed prototype capabilities or fixed contractual SLAs rather than enterprise target sizing ceilings.
- **Proposed v0.2 Statement:**
  > "Non-Functional Requirements (NFRs) Classification: The figures below represent **Architectural Design Targets & Peak Stress Ceilings** for high-volume Tier-1 clearing institutions. Production deployment SLAs are calibrated against actual client volume forecasts and clearing network bandwidth during onboarding (`OQ-02`)."
- **Reason:** Establishes clear distinction between architectural capability targets and commercial client SLAs.
- **Impact:** Prevents contractual misalignment while maintaining clear engineering performance targets.

---

## Changeset Entry 7: Domain 5 Return vs. Recall Disentanglement (GAP-07)

- **Finding:** GAP-07 (`DOMAIN_GAP` / Low)
- **Current v0.1 Statement (§6.2, §9):**
  > "SETTLEMENT & RETURNS: SETTLEMENT_FAILURE, RETURN_RECALL_UNMATCHED, VALUE_RETURN_PAC004_DISPUTE..."
- **Problem:**
  Does not explicitly highlight the payment lifecycle difference between `pacs.004` (value return) and `camt.056` (recall request).
- **Proposed v0.2 Statement:**
  > "Settlement Returns vs. Payment Recalls (Domain 5):
  > - **Payment Recall (`camt.056`):** An inquiry request demanding counterparty consent to return funds (no immediate debit/credit).
  > - **Payment Return (`pacs.004`):** An authorized value transfer returning principal funds back to the instructing agent with standard ISO return reason codes (`AC04`, `AM04`, `MD01`)."
- **Reason:** Reconciles Domain 5 specification strictly with `MST-026` standard taxonomy.
- **Impact:** Eliminates payment domain logic errors in live clearing adapters.

---

## Changeset Entry 8: Deterministic Validation Precedence Rule (GAP-08)

- **Finding:** GAP-08 (`AI_GOVERNANCE_GAP` / High)
- **Current v0.1 Statement (§13.1, §20 AC-5):**
  > "Deterministic Checksum Validation: No repaired IBAN or US routing number shall be presented to an approver unless it passes ISO 7064 MOD-97-10 or 9-digit ABA MOD-10 validation."
- **Problem:**
  Needs an explicit hierarchy rule declaring that deterministic mathematical validation unconditionally overrules AI model confidence scores.
- **Proposed v0.2 Statement:**
  > "Deterministic Gate Precedence Invariant: Deterministic mathematical validators (ISO 7064 MOD-97-10 IBAN checksum, 9-digit ABA routing checksum, BIC syntax validator) and authoritative directory matches unconditionally supersede AI model confidence scores. If an AI Reasoner generates a repair with 0.99 confidence that fails deterministic check digit verification, the Model Gateway immediately rejects the proposal and marks the case as `INVALID_REPAIR_PROPOSAL`."
- **Reason:** Guarantees zero algorithmic bypass of mathematical payment standards.
- **Impact:** Ensures zero corrupted IBANs or account numbers reach clearing rails.

---

## Changeset Entry 9: Partitioning Strategy for Long-Running Cases (GAP-09)

- **Finding:** GAP-09 (`DATA_ARCHITECTURE_GAP` / Low)
- **Current v0.1 Statement (§8.1):**
  > "Partitioning: Range partitioned by `ingestion_timestamp` (Monthly tables)."
- **Problem:**
  Complex investigation cases and disputed returns (`pacs.004`) can remain active across month boundaries. Monthly range partitioning can cause cross-partition updates if not indexed globally.
- **Proposed v0.2 Statement:**
  > "Database Partitioning Architecture: Range partitioned by `ingestion_timestamp` with quarterly partitions (`cases_y2026_q1`, `cases_y2026_q2`) supported by global unpartitioned unique indexes on `case_id` and `uetr`. Closed and settled cases older than 90 days are automatically archived to cold partitioned storage."
- **Reason:** Optimizes PostgreSQL query planning and avoids cross-partition update overhead.
- **Impact:** Improves database write performance at scale.

---

## Changeset Entry 10: AI Provider Timeout & Degradation Strategy (GAP-10)

- **Finding:** GAP-10 (`OPERABILITY_GAP` / Medium)
- **Current v0.1 Statement (§5 Principle 9, §13.1):**
  > "If an AI model provider is unavailable, PeX degrades gracefully to deterministic rule execution or routes cases to human investigation desks without data loss."
- **Problem:**
  Needs explicit operational timeout thresholds and state transition definitions.
- **Proposed v0.2 Statement:**
  > "AI Gateway Circuit Breaker & Fallback Protocol:
  > - **Timeout:** 3,000 ms per inference call.
  > - **Circuit Breaker:** Opens after 5 consecutive 5xx/timeout errors from the cloud LLM endpoint.
  > - **Fallback Execution:** When circuit is OPEN or call times out, PeX executes deterministic AST Policy Rule triage. If no AST rule matches, the case is routed to `INVESTIGATING` with status flag `AI_UNAVAILABLE_MANUAL_TRIAGE`. Zero exceptions are dropped, and all intake events remain persisted in PostgreSQL."
- **Reason:** Guarantees business continuity and zero downtime during third-party AI outages.
- **Impact:** Enhances operational resilience and meets 99.99% availability target.
