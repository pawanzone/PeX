# PeX Phase 3 Governance & Delivery Charter
## Strategic Planning, Capability Architecture & Authorization Roadmap for Remaining 30 Profiles
### Version v0.2 — Governance Hardened Baseline

---

### 1. Executive Summary

```
================================================================================
           PE-X PHASE 3 STRATEGIC GOVERNANCE & DELIVERY CHARTER
================================================================================

STATUS:               GOVERNANCE HARDENED BASELINE (READ-ONLY)
ENGINEERING AUTH:     NOT GRANTED (Requires separate explicit authorizations)
TAXONOMY BASELINE:    41 IMMUTABLE CANONICAL PROFILES
PHASE 2 CLOSURE:      FORMALLY CLOSED (11 Active Profiles Reconciled & Validated)
PHASE 3 SCOPE:        30 REMAINING EXCEPTION PROFILES (73.2% of Taxonomy)
DELIVERY MODEL:       CAPABILITY-FIRST, WAVE-BASED INDUSTRIALIZATION (WAVES 0A–6)
CANONICAL STP FORMULA: PRESERVED (8-Predicate Conjunction Invariant)
PRODUCTION STP:       STRICTLY BLOCKED (Awaiting Enterprise Infrastructure Gate)

FINAL PLANNING STATUS: READY FOR GOVERNANCE APPROVAL

================================================================================
```

#### Core Hardening Principles Enforced in v0.2
1. **Strict Provider & Technology Neutrality**: PeX defines abstract capability contracts and provider-neutral ports. Specific vendors, cloud services, and infrastructure technologies (e.g. AWS KMS, Redis, Kafka, Finacle, Dow Jones) are strictly categorized as *Example Enterprise Adapters* or *Reference Implementation Candidates*, never committed architecture selections.
2. **Bank-Controlled Execution Boundary**: Eliminates all language implying autonomous financial execution by PeX. PeX determines eligibility, recommends actions, and prepares instructions. All fund movements, ledger mutations, credit decisions, and wire dispatches are executed solely by bank systems at the terminal state (`BANK_HANDOFF_READY`, `execution_owner = "BANK"`).
3. **De-coupling Wave 0 (0A vs 0B)**: Splits platform enablement into **Wave 0A** (*Platform Contract & Architecture Hardening* — universal provider-neutral ports and schemas) and **Wave 0B** (*Enterprise Infrastructure Adapter Enablement* — bank-specific vendor adapter implementations).
4. **Rigorous Profile Classification**: Categorizes the 30 remaining profiles into 5 governance tiers based on mathematical determinism, authority availability, and regulatory mandates, avoiding speculative percentage claims.
5. **Contextual Authority & Jurisdiction Scope**: Clarifies that regulatory authorities (e.g. OFAC, FinCEN, Pay.UK) are contextual jurisdiction examples rather than global universal authorities.
6. **Separation of Milestones**: Distinguishes *Taxonomy Implementation*, *Bank Integration Readiness*, and *Production STP Authorization* as separate governance milestones.

---

### 2. Phase 2 Baseline & Lessons Learned

Phase 2 established an immutable, mathematically verified, and forensically audited architectural foundation:

```
+-------------------------------------------------------------------------------+
|                      PHASE 2 VALIDATED BASELINE CAPABILITIES                  |
+-------------------------------------------------------------------------------+
| 1. Immutable 41-Profile Taxonomy Reference Model                              |
| 2. 11 Active Profiles Validated Across All 5 Domains (100% Green)             |
| 3. Evidence-Driven Eligibility & Trust Tier Model (Tiers 1–4)                 |
| 4. Contextual Authority Hierarchy (Statutory > Bank Policy > History)         |
| 5. Canonical 8-Predicate STP Formula Conjunction                              |
| 6. AI Strictly Advisory Boundary (0% Weighting in STP Boolean Logic)          |
| 7. Universal Bank Execution Boundary (BANK_HANDOFF_READY, owner = BANK)       |
| 8. Maker-Checker Segregation of Duties (maker_id != checker_id)               |
| 9. Provider-Neutral Port/Adapter Architecture                                 |
| 10. Option B Dual-Track Historical Preservation Pattern                       |
| 11. 423 / 423 Cumulative Tests Passing Across 27 Test Modules                 |
+-------------------------------------------------------------------------------+
```

The canonical 8-predicate STP eligibility formula remains immutable:

$$\text{STP\_ELIGIBLE} = E_{\text{suff}} \land R_{\text{det}} \land R_{\text{uniq}} \land V_{\text{det}} \land V_{\text{auth}} \land P_{\text{bank}} \land C_{\text{comp}} \land X_{\text{pre}}$$

---

### 3. Phase 3 Scope & Taxonomy Inventory

The Phase 3 program addresses the **30 remaining exception profiles** (73.2% of the authoritative 41-profile taxonomy):

```
+-------------------------------------------------------------------------------+
|                        PE-X 41-PROFILE TAXONOMY STATUS                        |
+-------------------------------------------------------------------------------+
| Domain                        | Total | Phase 2 Active | Phase 3 Scope (Remaining) |
+-------------------------------+-------+----------------+--------------------------+
| 1. DATA QUALITY (DQ)          |   9   |       5        |       4 (DQ-03,04,07,09) |
| 2. PROCESSING (PR)            |   9   |       4        |       5 (PR-02,04,06,07,09) |
| 3. COMPLIANCE (CO)            |   8   |       1        |       7 (CO-01,02,03,05,06,07,08) |
| 4. CLIENT / TREASURY (TR)     |   8   |       0        |       8 (TR-01..TR-08)   |
| 5. SETTLEMENT / RETURNS (ST)  |   7   |       1        |       6 (ST-02..ST-07)   |
+-------------------------------+-------+----------------+--------------------------+
| TOTAL                         |  41   |      11        |      30                  |
+-------------------------------------------------------------------------------+
```

---

### 4. Remaining 30 Profile Inventory (TABLE A)

| Profile ID | Canonical Taxonomy Name | Domain | STP Category | Human Control Requirement | Risk Classification | Architectural Complexity | Reusable Engine Potential | Key Authority Dependency | Target Delivery Wave |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DQ-03** | `MISSING_BENEFICIARY_DATA` | Data Quality | CONDITIONAL STP | Maker-Checker if multi-match | Medium | Medium | High (Beneficiary Master) | Core KYC / Client Master | **Wave 2** |
| **DQ-04** | `MISSING_REMITTANCE_INFO` | Data Quality | DETERMINISTIC STP | Operations if unindexed | Low | Low | High (ERP Matcher) | Billing / Invoice Index | **Wave 1** |
| **DQ-07** | `INVALID_ACCOUNT_NUMBER` | Data Quality | DETERMINISTIC STP | Operations if multi-account | Medium | Medium | High (Account Master) | Core DDA Account Master | **Wave 1** |
| **DQ-09** | `BENEFICIARY_NAME_MISMATCH` | Data Quality | CONDITIONAL STP | Mandatory for retail consumer | Medium | High | High (CoP Registry) | Confirmation of Payee Service | **Wave 2** |
| **PR-02** | `ROUTING_FAILURE` | Processing | DETERMINISTIC STP | Maker-Checker if fee threshold| Medium | Medium | High (Dynamic Rail Router)| Clearing Status Service | **Wave 2** |
| **PR-04** | `CUTOFF_MISSED` | Processing | DETERMINISTIC STP | Operations if same-day mandate| Low | Low | High (Clearing Calendar) | Scheme Operating Schedule | **Wave 2** |
| **PR-06** | `INTERMEDIARY_REJECTION` | Processing | CONDITIONAL STP | Mandatory Maker-Checker | Medium | High | Medium (Inquiry Dispatch) | Correspondent Reject Parser | **Wave 3** |
| **PR-07** | `NETWORK_TIMEOUT` | Processing | DETERMINISTIC STP | Operations if status unknown | Medium | Medium | High (In-Flight Tracker) | Gateway Transport Journal | **Wave 3** |
| **PR-09** | `PAYMENT_HELD_FOR_REPAIR` | Processing | INVESTIGATION / HITL| Mandatory Operations Maker | Low | Medium | High (Operations Desk) | Operations Policy Manual | **Wave 3** |
| **CO-01** | `SANCTIONS_SCREENING_HIT` | Compliance | CONTROLLED / HITL | Mandatory MLRO Sign-Off | Critical | High | High (Sanctions Dossier) | Statutory Sanctions Authority | **Wave 6** |
| **CO-02** | `AML_ALERT` | Compliance | CONTROLLED / HITL | Mandatory MLRO Sign-Off | Critical | High | High (AML Dossier) | AML Monitoring Engine | **Wave 6** |
| **CO-03** | `PEP_MATCH` | Compliance | CONTROLLED / HITL | Mandatory Senior Management | High | High | High (PEP Dossier) | PEP Registry & EDD Master | **Wave 6** |
| **CO-05** | `ADVERSE_MEDIA_MATCH` | Compliance | CONTROLLED / HITL | Mandatory Compliance Analyst | Medium | Medium | High (Adverse Media) | Adverse Media Provider | **Wave 6** |
| **CO-06** | `HIGH_RISK_JURISDICTION` | Compliance | CONDITIONAL STP | Maker-Checker for high-value | High | Medium | High (Country Risk) | National / FATF Country Risk | **Wave 6** |
| **CO-07** | `REGULATORY_REPORTING` | Compliance | DETERMINISTIC STP | Compliance Officer Review | Medium | Medium | High (Regulatory Handoff)| Statutory Reporting Authority | **Wave 6** |
| **CO-08** | `CUSTOMER_WATCHLIST_MATCH`| Compliance | CONTROLLED / HITL | Mandatory Fraud Officer | High | Medium | High (Internal Watchlist)| Bank Fraud Engine | **Wave 6** |
| **TR-01** | `KYC_EXPIRED` | Client/Treasury| CONDITIONAL STP | Compliance Desk Review | Medium | Medium | High (KYC Lifecycle) | Client Master Expiry DB | **Wave 5** |
| **TR-02** | `INSUFFICIENT_FUNDS` | Client/Treasury| DETERMINISTIC STP | Credit Officer if unbacked | Medium | Medium | High (Liquidity Pool) | Core DDA Real-Time Balance | **Wave 4** |
| **TR-03** | `NOSTRO_SHORTFALL` | Client/Treasury| CONDITIONAL STP | Mandatory Treasury Officer | High | High | High (Nostro Position) | Treasury Position Monitor | **Wave 4** |
| **TR-04** | `FX_RATE_UNAVAILABLE` | Client/Treasury| DETERMINISTIC STP | Treasury Desk if wide spread | Medium | Medium | High (FX Quote Engine) | Treasury FX Rate Feed | **Wave 4** |
| **TR-05** | `AUTHORIZATION_MISSING` | Client/Treasury| INVESTIGATION / HITL| Corporate Signatory Action | Medium | Medium | High (Mandate Gateway) | Corporate Mandate System | **Wave 5** |
| **TR-06** | `LIMIT_BREACH` | Client/Treasury| CONDITIONAL STP | Mandatory Credit Officer | High | Medium | High (Limit Controller) | Credit Risk Limit Engine | **Wave 4** |
| **TR-07** | `LIQUIDITY_CONSTRAINT` | Client/Treasury| CONTROLLED / HITL | Mandatory Head of Treasury | High | High | High (RTGS Sequencer) | Central Clearing Monitor | **Wave 4** |
| **TR-08** | `CREDIT_EXPOSURE_BREACH` | Client/Treasury| CONTROLLED / HITL | Mandatory Chief Risk Officer | High | High | High (Exposure Tracker) | Enterprise Risk Management | **Wave 5** |
| **ST-02** | `ACCOUNT_CLOSED` | Settlement | DETERMINISTIC STP | Operations if debit unposted | Low | Low | High (Return Re-Credit) | Inbound pacs.004 Return | **Wave 1** |
| **ST-03** | `ACCOUNT_FROZEN` | Settlement | CONDITIONAL STP | Mandatory Legal Compliance | Medium | Medium | High (Legal Suspense) | Core DDA Freeze Ledger | **Wave 1** |
| **ST-04** | `RECONCILIATION_BREAK` | Settlement | INVESTIGATION / HITL| Mandatory Accounting Officer | Medium | High | High (Multi-Way Recon) | Central Clearing Statement | **Wave 5** |
| **ST-05** | `SETTLEMENT_FAILURE` | Settlement | INVESTIGATION / HITL| Mandatory Clearing Officer | High | High | High (Clearing Inquiry) | RTGS Finality Journal | **Wave 3** |
| **ST-06** | `FUNDS_TRAPPED_AT_CORR` | Settlement | DETERMINISTIC STP | Operator if unacknowledged | Medium | Medium | High (Interbank Tracker) | Interbank Tracker API | **Wave 3** |
| **ST-07** | `UNMATCHED_CREDIT` | Settlement | DETERMINISTIC STP | Operator if claim active | Medium | Medium | High (Return Re-Credit) | Inward Settlement Ledger | **Wave 1** |

---

### 5. STP / Controlled / Investigation Classification

The remaining 30 profiles are classified into 5 rigorous operational tiers:

```
+-------------------------------------------------------------------------------+
|                      PHASE 3 OPERATIONAL EXECUTION TIERS                      |
+-------------------------------------------------------------------------------+
| Tier A: Deterministic STP Candidate (8 Profiles)                              |
|   * Profiles: DQ-04, DQ-07, PR-02, PR-04, PR-07, ST-02, ST-06, ST-07         |
|   * Criteria: Rule determinism, authoritative data source available,           |
|     low operational ambiguity, candidate action completely verifiable.         |
|   * Handoff: Autonomous BANK_HANDOFF_READY under canonical 8-predicate formula.|
+-------------------------------------------------------------------------------+
| Tier B: Conditional STP Candidate (11 Profiles)                               |
|   * Profiles: DQ-03, DQ-09, PR-06, CO-06, CO-07, TR-01, TR-02, TR-03,        |
|     TR-04, TR-06, ST-03                                                       |
|   * Criteria: STP eligible only when specific pre-authorized bank policy,      |
|     sweep agreement, or low-value threshold is active.                         |
|   * Handoff: BANK_HANDOFF_READY if all predicates hold; else Maker-Checker.   |
+-------------------------------------------------------------------------------+
| Tier C: Controlled / Human-In-The-Loop (HITL) Decision (7 Profiles)          |
|   * Profiles: CO-01, CO-02, CO-03, CO-05, CO-08, TR-07, TR-08                |
|   * Criteria: Autonomous STP prohibited by law, regulation, or bank policy.    |
|   * Action: PeX gathers evidence dossier, scores candidate hypotheses, and    |
|     routes to Compliance Officer, MLRO, or Risk Approver for dual-signoff.   |
+-------------------------------------------------------------------------------+
| Tier D: Interactive Corporate Challenge / Complex Investigation (4 Profiles)  |
|   * Profiles: PR-09, TR-05, ST-04, ST-05                                      |
|   * Criteria: Requires external client signatory action or complex multi-way   |
|     ledger accounting reconciliation.                                         |
+-------------------------------------------------------------------------------+
| Tier E: Insufficiently Defined (0 Profiles)                                   |
|   * All 30 profiles have defined taxonomy problems, triggers, and boundaries.  |
+-------------------------------------------------------------------------------+
```

> [!NOTE]
> *Illustrative Planning Hypothesis*: Autonomous resolution volume in production is a function of bank-specific policy thresholds, client mandates, and exception distribution. No universal percentage guarantees are asserted.

---

### 6. Profile Resolution Archetypes

1. **Archetype 1: Deterministic Data & Identity Repair** (`DQ-03`, `DQ-04`, `DQ-07`, `DQ-09`):
   - *Logic*: Matches missing/corrupted payment attributes against authoritative bank systems (DDA, CoP, Client Master) and prepares standardized substitution instructions.
2. **Archetype 2: Dynamic Rail Routing & Clearing Rescheduling** (`PR-02`, `PR-04`):
   - *Logic*: Evaluates real-time clearing availability and scheme cutoff calendars; constructs proposed rail switch or value-date roll instructions.
3. **Archetype 3: Interbank Transport Inquiry & Status Tracking** (`PR-06`, `PR-07`, `ST-05`, `ST-06`):
   - *Logic*: Queries interbank status feeds or tracker APIs; constructs status inquiry payloads (e.g. camt.027) or re-dispatch recommendations.
4. **Archetype 4: Inward Settlement Returns & Re-Credit Preparation** (`ST-02`, `ST-03`, `ST-07`):
   - *Logic*: Matches inward return messages (pacs.004) with original payment debits and prepares debtor re-credit instructions.
5. **Archetype 5: Intraday Liquidity, Balance Sweeps & Rate Quotes** (`TR-02`, `TR-03`, `TR-04`, `TR-06`, `TR-07`, `TR-08`):
   - *Logic*: Inspects real-time balances, credit lines, and FX rates; formulates sweep recommendations, rate attachments, or credit approvals.
6. **Archetype 6: Corporate Client Mandates & Multi-Way Reconciliation** (`TR-01`, `TR-05`, `ST-04`):
   - *Logic*: Verifies corporate signature rules or reconciles statement feeds against internal settlement journals.
7. **Archetype 7: Financial Crime Compliance Dossier & Reporting** (`CO-01`, `CO-02`, `CO-03`, `CO-05`, `CO-06`, `CO-07`, `CO-08`):
   - *Logic*: Assembles immutable compliance evidence dossiers, executes prompt-injection sanitized entity scoring, and routes to Compliance Desks.

---

### 7. Reusable Capability Map (TABLE B)

```
+----------------------------------------------------------------------------------------------------------------------------------+
|                                                    REUSABLE CAPABILITY MAP                                                       |
+----------------------------------------------------------------------------------------------------------------------------------+
| Reusable Engine       | Profiles Served   | Evidence Required       | Authority Required     | Example Enterprise Adapters       |
+-----------------------+-------------------+-------------------------+------------------------+-----------------------------------+
| 1. Account Master &   | DQ-03, DQ-07,     | Inbound account/name,   | Core Banking DDA,      | Core DDA Connector, Open Banking  |
|    CoP Engine         | DQ-09, ST-02,03   | CoP directory response  | National CoP Service   | Pay.UK / SEPA VoP Adapter         |
+-----------------------+-------------------+-------------------------+------------------------+-----------------------------------+
| 2. Dynamic Rail &     | PR-02, PR-04,     | Payment payload, rail   | Scheme Operating Feed, | Clearing Calendar Feed, Real-Time |
|    Cutoff Router      | PR-06             | status, scheme calendar | Gateway Status Feed    | RTGS Gateway Status Adapter       |
+-----------------------+-------------------+-------------------------+------------------------+-----------------------------------+
| 3. Interbank Inquiry  | PR-06, PR-07,     | Gateway logs, tracker   | Interbank Gateway,     | SWIFT SAG Connector, GPI Tracker  |
|    & Status Tracker   | ST-05, ST-06      | UETR response status    | Correspondent Service  | API Adapter, ISO 20022 camt.027   |
+-----------------------+-------------------+-------------------------+------------------------+-----------------------------------+
| 4. Return Re-Credit   | ST-02, ST-03,     | Inbound pacs.004, debit | Core Settlement Ledger,| Core DDA Ledger Connector,        |
|    Instruction Engine | ST-07 (ext ST-01) | record in bank ledger   | Inward Clearing Feed   | pacs.004 / pacs.008 Serializer    |
+-----------------------+-------------------+-------------------------+------------------------+-----------------------------------+
| 5. Intraday Liquidity | TR-02, TR-03,     | DDA balance, Nostro     | Core DDA Balance,      | Core Banking DDA API, Treasury    |
|    & Sweep Engine     | TR-06, TR-07,08   | positions, limit records| Treasury Position DB   | Position Monitor Adapter          |
+-----------------------+-------------------+-------------------------+------------------------+-----------------------------------+
| 6. Real-Time FX Rate  | TR-04             | Currency pair, amount,  | Bank Treasury FX Rate  | Treasury FX Rate Stream Adapter,  |
|    Quote Resolver     |                   | value date              | Engine, Spread Policy  | Market Data Connector             |
+-----------------------+-------------------+-------------------------+------------------------+-----------------------------------+
| 7. Financial Crime    | CO-01, CO-02,     | Watchlist match record, | Statutory Sanctions DB,| Sanctions Feed Adapter (OFAC/UN), |
|    Dossier Engine     | CO-03,05,06,08    | TMS alert, KYC vault    | Bank Compliance Engine | AML Alert DB Connector            |
+-----------------------+-------------------+-------------------------+------------------------+-----------------------------------+
| 8. Regulatory Report  | CO-07             | Canonical payment data, | Statutory Reporting    | Secure Regulatory Gateway Adapter |
|    Dispatcher         |                   | reporting thresholds    | Specification          | (FinCEN / BoE XML Filer)          |
+-----------------------+-------------------+-------------------------+------------------------+-----------------------------------+
| 9. Corporate Mandate  | TR-01, TR-05      | Signatory matrix, KYC   | Corporate Mandate DB,  | Corporate e-Banking Gateway,      |
|    & Auth Gateway     |                   | expiration dates        | Client Onboarding DB   | Client Master KYC Adapter         |
+-----------------------+-------------------+-------------------------+------------------------+-----------------------------------+
| 10. Multi-Way Break   | ST-04             | Statement (camt.053),   | Central Clearing Feed, | Statement Ingestion Pipeline,     |
|     Recon Engine      |                   | internal bank ledger    | Bank General Ledger    | Reconciliation DB Adapter         |
+----------------------------------------------------------------------------------------------------------------------------------+
```

---

### 8. Provider-Neutral Architecture Model

> [!IMPORTANT]
> **Architectural Invariant**: PeX defines abstract capability contracts and provider-neutral ports. Provider selection is an implementation and bank architecture decision, not a Phase 3 taxonomy or domain-model decision.

```
+-------------------------------------------------------------------------------+
|                     PROVIDER-NEUTRAL PORT / ADAPTER MODEL                     |
+-------------------------------------------------------------------------------+
| Core Domain Logic (Abstract Ports)                                            |
|   * IdempotencyLockManagerPort                                                |
|   * MessageBrokerResetPort                                                    |
|   * CoreBankingDDAPort                                                        |
|   * RegulatoryScreeningPort                                                   |
|   * SecretTokenizationVaultPort                                               |
+-------------------------------------------------------------------------------+
| Example Enterprise Adapters (Bank Architecture Selections)                    |
|   * Distributed Locking: Redis Redlock, DynamoDB, Database Atomic CAS         |
|   * Message Brokers: Apache Kafka, IBM MQ, AWS SQS FIFO, RabbitMQ             |
|   * Core Banking: Finacle REST, Temenos T24, SAP Banking, Custom ISO 20022 API|
|   * Regulatory Screening: Dow Jones, LexisNexis, Internal Compliance Engine   |
|   * Key Management: AWS KMS, HashiCorp Vault, Azure Key Vault, Hardware HSM   |
+-------------------------------------------------------------------------------+
```

---

### 9. Semantic Collision Risk Assessment

| Profile Boundary | Nature of Overlap | Architectural Boundary Definition | Classification |
| :--- | :--- | :--- | :--- |
| **DQ-07 vs DQ-01** | Account vs IBAN format | DQ-01 strictly owns ISO 13616 IBANs. DQ-07 strictly owns domestic BBAN account numbers. | **CONFIRMED DISJOINT** |
| **DQ-07 vs ST-02** | Invalid vs Closed account | DQ-07 owns unparseable/invalid syntax. ST-02 owns valid accounts closed in Core DDA. | **CONFIRMED DISJOINT** |
| **DQ-03 vs DQ-09** | Missing data vs Mismatched name| DQ-03 handles missing tags. DQ-09 handles present tags failing confirmation check. | **CONFIRMED DISJOINT** |
| **PR-02 vs DQ-08** | Routing failure vs Invalid code| DQ-08 owns static routing number syntax. PR-02 owns runtime dynamic clearing link failures.| **CONFIRMED DISJOINT** |
| **PR-04 vs PR-08** | Cutoff missed vs Queue failure | PR-04 handles scheme operating clocks. PR-08 handles message broker queue deadlocks. | **CONFIRMED DISJOINT** |
| **PR-06 vs PR-02** | Intermediary reject vs Local routing| PR-02 is local router failure. PR-06 is external pacs.002 reject message. | **CONFIRMED DISJOINT** |
| **PR-07 vs PR-08** | Socket timeout vs Broker DLQ | PR-07 handles network transit ACK timeout. PR-08 handles internal queue persistence. | **CONFIRMED DISJOINT** |
| **CO-01 vs CO-08** | Global sanctions vs Internal list| CO-01 owns statutory OFAC/UN sanctions. CO-08 owns internal bank fraud watchlists. | **CONFIRMED DISJOINT** |
| **CO-02 vs CO-03** | AML alert vs PEP match | CO-02 owns transaction velocity monitoring. CO-03 owns political exposure screening. | **CONFIRMED DISJOINT** |
| **TR-02 vs TR-07** | Account balance vs RTGS quota | TR-02 owns customer DDA account balance. TR-07 owns bank-wide RTGS clearing quota. | **CONFIRMED DISJOINT** |
| **TR-03 vs TR-07** | Single Nostro vs Bank-wide RTGS| TR-03 owns correspondent Nostro funding. TR-07 owns central bank RTGS headroom. | **CONFIRMED DISJOINT** |
| **ST-04 vs ST-05** | Accounting break vs Settlement fail| ST-04 owns ledger reconciliation breaks. ST-05 owns failed central clearing cycles. | **CONFIRMED DISJOINT** |

---

### 10. Contextual Authority Source Strategy (TABLE D)

Authority is evaluated contextually based on the legal and operational question:

1. **Statutory & Regulatory Questions**: Tier 2 Statutory Authorities govern legal prohibitions. Bank policy cannot override statutory prohibitions.
2. **Bank Operational Questions**: Tier 1 Bank Policy governs bank permissions. Absence of statutory restriction does not grant permission without bank policy.
3. **Account & Balance Questions**: Tier 1 Core Banking DDA governs account ownership and real-time balances.
4. **Historical Precedents**: Tier 4 Historical Data provides contextual guidance only ($0\%$ authority).

---

### 11. Bank, Product, and Jurisdiction Boundaries

```
+-------------------------------------------------------------------------------+
|                       PHASE 3 ARCHITECTURAL SCOPE LAYERS                      |
+-------------------------------------------------------------------------------+
| Layer 1: Universal PeX Core Domain (Canonical 8 predicates, Trust Tiers)       |
| Layer 2: Reusable Domain Engines (Account Master, Rail Router, Sweep Engine)  |
| Layer 3: Bank-Scope Configuration (Auto-STP limits, overdraft policies)       |
| Layer 4: Jurisdiction / Scheme Adapters (Fedwire, CHAPS, TARGET2, SEPA)        |
| Layer 5: Enterprise Infrastructure Adapters (KMS, Redis, Kafka, Core DDA)     |
+-------------------------------------------------------------------------------+
```

---

### 12. Wave 0A — Platform Contract & Architecture Hardening

**Scope**: Establishes all provider-neutral contracts, Pydantic schemas, abstract BasePorts, security boundaries, and test harnesses before any profile implementation.

#### Deliverables of Wave 0A:
1. `SecretTokenizationVaultPort` and contract schemas.
2. `DistributedIdempotencyPort` and atomic lock contract.
3. `StreamingMessageBrokerPort` and queue lifecycle contract.
4. `CoreBankingDDAPort` and real-time balance contract.
5. `RegulatoryScreeningPort` and evidence contract.
6. Unified fail-closed configuration schema (`BankPolicyEnvelope`).
7. Abstract test contract harnesses for mock and live verification.

---

### 13. Wave 0B — Enterprise Infrastructure Adapter Enablement

**Scope**: Implementation of specific enterprise adapters chosen by the bank/client architecture (e.g., AWS KMS, Redis Redlock, Apache Kafka, Core Banking Finacle API).

> [!NOTE]
> Wave 0B represents bank/client integration engineering, decoupled from the core PeX domain architecture.

---

### 14. Phase 3 Delivery Waves (TABLE C)

| Wave ID | Wave Name | Profiles Included | Shared Platform Capability | Core Dependencies | Primary Focus | Target STP Category |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Wave 0A**| **Platform Contracts & Ports** | Infrastructure Only | BasePort Interfaces & Contracts | Phase 2 Baseline | Platform Neutrality | Infrastructure Only |
| **Wave 0B**| **Enterprise Adapters Enablement**| Infrastructure Only | Client-Selected Cloud Adapters | Wave 0A | Production Integration| Infrastructure Only |
| **Wave 1** | **Deterministic Data & Returns** | `DQ-04, DQ-07, ST-02, ST-03, ST-07` | Account Master Engine, Return Reconciler | Wave 0A | Data Quality & Returns | DETERMINISTIC / CONDITIONAL |
| **Wave 2** | **Identity & Dynamic Rail Routing**| `DQ-03, DQ-09, PR-02, PR-04` | Beneficiary CoP Engine, Rail Router | Wave 1 | Identity & Clearing | DETERMINISTIC / CONDITIONAL |
| **Wave 3** | **Transport, Network & Inquiry** | `PR-06, PR-07, PR-09, ST-05, ST-06`| Interbank Tracker & Inquiry Engine | Wave 0A, Wave 2 | Network Operations | DETERMINISTIC / INVESTIGATION |
| **Wave 4** | **Treasury, Balance & Liquidity** | `TR-02, TR-03, TR-04, TR-06, TR-07`| Core DDA Liquidity & FX Resolver | Wave 0A, Wave 1 | Treasury Operations | DETERMINISTIC / CONTROLLED |
| **Wave 5** | **Mandates & Settlement Breaks** | `TR-01, TR-05, TR-08, ST-04` | Corporate Mandate Gateway, Recon Engine| Wave 4 | Corporate Governance | CONDITIONAL / INVESTIGATION |
| **Wave 6** | **Financial Crime & Compliance** | `CO-01, CO-02, CO-03, CO-05, CO-06, CO-07, CO-08`| Financial Crime Dossier & CTR Dispatcher| Wave 0A, Wave 1 | Regulatory Safety | CONTROLLED (CTR: DETERMINISTIC) |

---

### 15. Dependency Graph

$$\text{Wave 0A (Contracts)} \longrightarrow \text{Wave 0B (Adapters)}$$
$$\downarrow$$
$$\text{Wave 1 (Data & Returns)} \longrightarrow \text{Wave 2 (Identity & Routing)} \longrightarrow \text{Wave 3 (Transport & Inquiry)}$$
$$\downarrow$$
$$\text{Wave 4 (Treasury & Liquidity)} \longrightarrow \text{Wave 5 (Mandates & Recon)}$$
$$\downarrow$$
$$\mathbf{Wave\; 6\; (Financial\; Crime\; &\; Regulatory)}$$

---

### 16. AI & Agentic Role in Phase 3

- **Strictly Advisory**: AI confidence carries **$0\%$ authority** in the 8-predicate STP formula.
- **Permitted**: Parsing free-text remittance info, fuzzy matching corporate alias candidates, ranking candidate correspondent routes, and summarizing adverse news.
- **Strictly Prohibited**: Clearing sanctions/AML hits, inferring exemptions, bypassing Maker-Checker controls, or executing financial ledger transactions.

---

### 17. Production Execution Boundary

```
+-------------------------------------------------------------------------------+
|                        PRODUCTION EXECUTION BOUNDARY                          |
+-------------------------------------------------------------------------------+
| PeX Platform Scope (Determines & Recommends):                                 |
|  * Ingests error & evidence dossier -> Evaluates 8 predicates                 |
|  * Formulates repair candidate -> Prepares sealed BankHandoffEnvelope         |
|  * Terminal State: BANK_HANDOFF_READY (execution_owner = "BANK")              |
+-------------------------------------------------------------------------------+
| Bank Infrastructure Scope (Executes & Settles):                               |
|  * Debits/credits core DDA ledgers                                            |
|  * Transmits wire instructions to RTGS / Clearing networks (Fedwire, CHAPS)   |
|  * Executes foreign exchange conversions and liquidity sweeps                 |
+-------------------------------------------------------------------------------+
```

---

### 18. KPI & Observability Framework

- **Architecture Invariants (Non-Negotiable)**: `execution_owner = "BANK"`, `maker_id != checker_id`, 8-predicate boolean conjunction completeness.
- **Operational Metrics (Observed / Baseline Required)**: End-to-end resolution latency, evidence sufficiency rate, Maker-Checker review turnaround time.
- **Business Performance (Hypothesis / Bank-Specific)**: Autonomous STP rate, exception volume reduction, operator touchpoint reduction.

---

### 19. Governance & Forensic Review Model

Every implementation wave must follow the verified 7-stage lifecycle:
1. *Wave Architecture Specification* $\to$ 2. *Explicit Engineering Authorization* $\to$ 3. *Implementation & AST Verification* $\to$ 4. *Behavioral & Adversarial Testing* $\to$ 5. *Independent Forensic Acceptance Review* $\to$ 6. *Multi-Profile Semantic Reconciliation* $\to$ 7. *Wave Acceptance Sign-Off*.

---

### 20. Risks & Open Decisions

- `RISK-P3-01`: Confirmation of Payee (CoP) API external latency $\to$ *Mitigation: Fail-closed to HITL Disambiguation Desk*.
- `RISK-P3-02`: Real-time DDA balance staleness $\to$ *Mitigation: Require Tier 1 Core DDA Balance Lock*.
- `DECISION-01`: Corporate name fuzzy matching score threshold $\to$ *Classified: Bank-Scope Policy DB Decision*.

---

### 21. Phase 3 Program Exit Criteria

Phase 3 completion will be certified when:
1. All 41 canonical taxonomy profiles are implemented and forensically accepted.
2. Semantic boundaries across all 41 profiles are verified disjoint.
3. Universal 8-predicate formula and bank handoff boundaries are intact.
4. Cumulative regression test suite passes at 100%.
5. Enterprise infrastructure adapters (Wave 0B) are verified in staging.

---

### 22. Explicit Engineering Authorization Requirements

```
================================================================================
                    GOVERNANCE BOUNDARY & AUTHORIZATION NOTICE
================================================================================

THIS CHARTER IS A PLANNING AND GOVERNANCE SPECIFICATION ONLY.

NO ENGINEERING AUTHORIZATION IS GRANTED BY THIS DOCUMENT.

Implementation of Phase 3 Waves (Wave 0A through Wave 6) requires:
1. Executive Governance Approval of this Charter v0.2.
2. Separate, explicit engineering authorizations issued per Wave.
3. Creation of isolated implementation branches for authorized waves.

================================================================================
```

---

### 23. Final Governance Recommendation

```
================================================================================
                       FINAL GOVERNANCE RECOMMENDATION
================================================================================

PHASE 3 PLANNING STATUS:  READY FOR GOVERNANCE APPROVAL
ENGINEERING AUTHORIZATION: NOT GRANTED
PRODUCTION STP:           STRICTLY BLOCKED

RECOMMENDED NEXT GOVERNANCE ACTION:
Approve this Charter v0.2, then issue separate explicit Engineering
Authorization for WAVE 0A (Platform Contract & Architecture Hardening).

================================================================================
```

---
*Report filed by: Independent Senior Architecture Governance Reviewer*  
*Date: 2026-10-07*
