# 🔍 PeX Platform: Enterprise Architecture Gap & Finding Matrix

**Document ID:** `PEX-ARCH-GAP-MATRIX-v0.1`  
**Governing Baseline:** PeX `v1.9.4` (`9e9184b`) / `PEX_ENTERPRISE_ARCHITECTURE_SPECIFICATION_v0.1.md`  
**Evaluation Scope:** Architecture Assurance Review & v0.2 Gap Assessment  
**Date:** September 28, 2026  
**Status:** Authoritative Architecture Finding Register  

---

## 1. Classification & Severity Legend

- **Classifications:** `ARCHITECTURE_GAP`, `ARCHITECTURE_AMBIGUITY`, `TRACEABILITY_GAP`, `SECURITY_GAP`, `AI_GOVERNANCE_GAP`, `DATA_ARCHITECTURE_GAP`, `INTEGRATION_GAP`, `NFR_GAP`, `OPERABILITY_GAP`, `DOMAIN_GAP`, `TERMINOLOGY_ISSUE`, `OVER_SPECIFICATION`, `UNDER_SPECIFICATION`, `OPEN_QUESTION`, `KNOWN_DEFERRED`, `NO_ISSUE`.
- **Severities:** `Critical` (Blocks reference architecture), `High` (Must resolve in v0.2), `Medium` (Clarify in v0.2 / Design), `Low` (Implementation note).

---

## 2. Enterprise Architecture Assurance Gap Matrix

| ID | Area | Finding Summary | Classification | Severity | Source in v0.1 | Recommended Minimum Correction | Target v0.2? | Implementation / Defer? |
| :---: | :--- | :--- | :---: | :---: | :--- | :--- | :---: | :---: |
| **GAP-01** | **Crypto Audit** | Linear SHA-256 hash chain is repeatedly labeled as "Merkle Provenance Chain" or "Merkle Tree". While structurally tamper-evident, it is a linear linked chain, not a tree/DAG. | `TERMINOLOGY_ISSUE` | **Medium** | §3 (Layer 5), §15.1, §21 (ADR-005) | Disambiguate terminology: Define current mechanism as "Continuous SHA-256 Linear Provenance Hash Chain" and specify the cloud enterprise extension as a "Hierarchical Merkle Batch Root". | **YES (v0.2)** | Retain linear chain in core; batch tree in cloud storage. |
| **GAP-02** | **AI Governance** | `ReasoningResult` is not explicitly declared as strictly advisory in all sections, risking assumption that LLM outputs possess autonomous release authority. | `AI_GOVERNANCE_GAP` | **High** | §3 (Layer 4), §13.1, §21 (ADR-003) | Explicitly specify: "The LLM and `ReasoningResult` are strictly advisory. The AI possesses zero authorization, payment release, or compliance clearance authority." | **YES (v0.2)** | Enforced in Approval Engine & State Machine. |
| **GAP-03** | **Autonomy Model** | Level 5 Autonomy specifies "Self-Healing Multi-Rail Routing with Automated Recall (camt.056)" without defining the hard clearing cutoff and liquidity reservation bounds. | `ARCHITECTURE_AMBIGUITY` | **High** | §14 (Level 5 Table Entry) | Clarify that Level 5 autonomous clearing rerouting requires deterministic pre-flight RTGS cutoff validation, sanctions re-screening, and nostro balance reservation. | **YES (v0.2)** | Implement via Clearing Routing Policy AST. |
| **GAP-04** | **Messaging & Eventing** | "Exactly-once semantics via transactional outbox" conflates technical transport deduplication with business-level payment idempotency. | `ARCHITECTURE_AMBIGUITY` | **Medium** | §12.2 (Messaging Guarantees) | Distinguish: Technical transport is *effectively-once* via FIFO deduplication ID; Business idempotency is *exactly-once* via database transaction lock on `idempotency_key` + `uetr`. | **YES (v0.2)** | Enforce in Redis/DB Lock & Dispatcher. |
| **GAP-05** | **Security & KMS** | Token Vault service-to-service IAM boundary and key rotation replay procedure are underspecified. | `SECURITY_GAP` | **Medium** | §10.1, §17.2 | Mandate that Detokenization is strictly gated to the Outbound Dispatcher microservice via mTLS + KMS Decrypt IAM policy. Specify historical token replay key versioning. | **YES (v0.2)** | Cloud KMS CMK policy definition in Ref Arch. |
| **GAP-06** | **NFR Sizing** | NFRs (100–500 TPS, 50k exceptions/day, <1.5s AI reasoning) read as committed SLAs rather than architectural target objectives. | `NFR_GAP` | **Medium** | §16 (NFR Table), §22 (OQ-02) | Add qualification: "NFRs represent Architectural Design Targets (Stress Ceilings) for Tier-1 institutions; actual production SLAs are calibrated during client capacity onboarding (OQ-02)." | **YES (v0.2)** | Calibrate in Client Reference Architecture. |
| **GAP-07** | **Integration** | Separation of `pacs.004` (Value Return) and `camt.056` (Recall Inquiry) clearing state machine flows needs explicit exception taxonomy card alignment. | `DOMAIN_GAP` | **Low** | §6.2 (Domain 5), §9 (Rail Protocols) | Explicitly cross-reference `MST-026` rules: `camt.056` initiates an unconfirmed recall inquiry; `pacs.004` executes an authorized outbound principal return. | **YES (v0.2)** | Adapter state handlers. |
| **GAP-08** | **AI Governance** | Precedence of deterministic validation (MOD-97-10, ABA 9-digit, BMD directory proof) over LLM confidence score is implicit rather than absolute. | `AI_GOVERNANCE_GAP` | **High** | §13.1, §20 (AC-5) | Add explicit rule: "Deterministic mathematical checks and authoritative directory matches supersede AI confidence scores. A 0.99 AI score with failed MOD-97-10 check is strictly blocked." | **YES (v0.2)** | Model Gateway & Policy Engine validation rule. |
| **GAP-09** | **Data Archival** | Transaction DB partitioning is specified on monthly tables, but lifecycle state transitions span months for disputed returns. | `DATA_ARCHITECTURE_GAP` | **Low** | §8.1 (Persistence Topology) | Specify partitioning by `created_at` year/quarter or composite `case_id` hash routing with global unpartitioned index on `case_id` / `uetr`. | **YES (v0.2)** | Database DDL & migration scripts. |
| **GAP-10** | **Resilience & Fallback** | Fallback behavior when AI Provider is down or degraded needs explicit queueing specification. | `OPERABILITY_GAP` | **Medium** | §5 (Principle 9), §13.1 | Specify: "If LLM Gateway times out (>3,000ms) or is unavailable, cases fall back immediately to deterministic AST Policy Rule triage; if no rule matches, case transitions to `PENDING_MANUAL_TRIAGE`." | **YES (v0.2)** | Fallback interceptor in AI Gateway. |

---

## 3. Summary of Findings

- **Total Assessed Findings:** 10
- **Critical:** 0
- **High:** 3 (GAP-02, GAP-03, GAP-08)
- **Medium:** 5 (GAP-01, GAP-04, GAP-05, GAP-06, GAP-10)
- **Low:** 2 (GAP-07, GAP-09)
- **Target for v0.2 Changeset:** 10 / 10
- **Architectural Blocker Severity:** ZERO (All findings are precision, terminology, and governance boundary refinements).
