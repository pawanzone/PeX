# PeX Phase 3 Governance & Delivery Charter
## Strategic Planning, Capability Architecture & Authorization Roadmap for Remaining 30 Profiles
### Version v0.1 — Governance Baseline

---

### 1. Executive Summary

```
================================================================================
           PE-X PHASE 3 STRATEGIC GOVERNANCE & DELIVERY CHARTER
================================================================================

STATUS:               PLANNING & GOVERNANCE BASELINE (READ-ONLY)
ENGINEERING AUTH:     NOT YET GRANTED (Requires separate explicit authorizations)
TAXONOMY BASELINE:    41 IMMUTABLE CANONICAL PROFILES
PHASE 2 CLOSURE:      FORMALLY CLOSED (11 Active Profiles Reconciled & Validated)
PHASE 3 SCOPE:        30 REMAINING EXCEPTION PROFILES (73.2% of Taxonomy)
DELIVERY MODEL:       CAPABILITY-FIRST, WAVE-BASED INDUSTRIALIZATION (WAVES 0–6)
CANONICAL STP FORMULA: PRESERVED (8-Predicate Conjunction Invariant)
PRODUCTION STP:       STRICTLY BLOCKED (Awaiting Enterprise Cloud Infrastructure)

FINAL PLANNING STATUS: READY FOR GOVERNANCE APPROVAL

================================================================================
```

#### Strategic Charter Objectives
1. **Industrialize the Remaining 30 Profiles**: Transition PeX from an 11-profile validated baseline into an enterprise platform covering all 41 canonical exception profiles across the 5 BIAN payment domains.
2. **Capability-First Architecture**: Eliminate custom per-profile code silos by architecting 10 reusable domain engines (e.g. Account Master Engine, Dynamic Rail Router, Treasury Liquidity Engine, Financial Crime Dossier Engine) serving multiple profile archetypes.
3. **Strict Governance & Invariant Preservation**: Retain Phase 2 core invariants without compromise: evidence-driven eligibility, contextual authority supremacy, the canonical 8-predicate formula, AI advisory boundary ($0\%$ authority), Maker-Checker Segregation of Duties ($maker\_id \neq checker\_id$), and terminal bank handoff (`execution_owner = "BANK"`).
4. **Structured Wave Delivery**: Group profiles into 6 delivery waves based on shared capability dependencies, deterministic resolution potential, and risk boundaries.
5. **Clear Separation of Profile Development and Production Enablement**: Maintain an independent infrastructure track (Wave 0) to productionize cloud adapters (AWS KMS, Redis, Kafka, Aurora, Live Core DDA) without coupling them to profile logic.

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

#### Lessons Learned Applied to Phase 3
- **Prevent Early Semantic Collisions**: Conduct formal pre-implementation semantic boundary analyses before authorizing any wave to prevent overlaps (e.g. historical DQ-08/DQ-02 and PR-08/PR-05 collisions).
- **Capability-First over Profile-First**: Build core domain engines first, then attach individual profile adapters.
- **Fail-Closed by Default**: Unconfigured bank policy or missing directory evidence must always fail closed (`BANK_CONFIG_REQUIRED` or `COMPLIANCE_SUSPENSE`).
- **Autonomous STP vs HITL Realism**: Acknowledge that high-risk compliance (CO-01..CO-08) and credit/liquidity (TR-05..TR-08) profiles are inherently controlled workflows requiring human authorization.

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

The table below classifies every remaining profile across execution characteristics, risks, complexity, reuse potential, and target wave:

| Profile ID | Canonical Taxonomy Name | Domain | STP Potential | HITL Requirement | Risk Level | Implementation Complexity | Reusable Engine Potential | Key Dependencies | Recommended Delivery Wave |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DQ-03** | `MISSING_BENEFICIARY_DATA` | Data Quality | Policy STP | High (if ambiguous)| Medium | Medium | High (Beneficiary Master) | Core KYC / Client Master | **Wave 2** |
| **DQ-04** | `MISSING_REMITTANCE_INFO` | Data Quality | High STP | Low (if matched) | Low | Low | High (ERP Matcher) | Billing / Invoice Index | **Wave 1** |
| **DQ-07** | `INVALID_ACCOUNT_NUMBER` | Data Quality | High STP | Low (if unique) | Medium | Medium | High (Account Master) | Core DDA Account Master | **Wave 1** |
| **DQ-09** | `BENEFICIARY_NAME_MISMATCH` | Data Quality | Policy STP | High (Consumer) | Medium | High | High (CoP Registry) | Confirmation of Payee API | **Wave 2** |
| **PR-02** | `ROUTING_FAILURE` | Processing | High STP | Low (Policy rail) | Medium | Medium | High (Dynamic Rail Router)| Real-time Rail Status | **Wave 2** |
| **PR-04** | `CUTOFF_MISSED` | Processing | High STP | Low (Auto roll) | Low | Low | High (Clearing Calendar) | Scheme Cutoff Registry | **Wave 2** |
| **PR-06** | `INTERMEDIARY_REJECTION` | Processing | Policy STP | High (Unmapped) | Medium | High | Medium (Inquiry Dispatch) | pacs.002 Parser | **Wave 3** |
| **PR-07** | `NETWORK_TIMEOUT` | Processing | High STP | Low (Query match)| Medium | Medium | High (In-Flight Tracker) | Gateway Transport Logs | **Wave 3** |
| **PR-09** | `PAYMENT_HELD_FOR_REPAIR` | Processing | Non-STP | Mandatory HITL | Low | Medium | High (Operations Desk) | Operations Workbench | **Wave 3** |
| **CO-01** | `SANCTIONS_SCREENING_HIT` | Compliance | Non-STP | Mandatory MLRO | Critical | High | High (Sanctions Dossier) | Watchlist / OFAC Engine | **Wave 6** |
| **CO-02** | `AML_ALERT` | Compliance | Non-STP | Mandatory MLRO | Critical | High | High (AML Dossier) | Transaction Monitoring | **Wave 6** |
| **CO-03** | `PEP_MATCH` | Compliance | Non-STP | Mandatory EDD | High | High | High (PEP Dossier) | PEP Watchlist Engine | **Wave 6** |
| **CO-05** | `ADVERSE_MEDIA_MATCH` | Compliance | Non-STP | Mandatory Analyst| Medium | Medium | High (Adverse Media) | News / Legal Feeds | **Wave 6** |
| **CO-06** | `HIGH_RISK_JURISDICTION` | Compliance | Policy STP | High (Threshold) | High | Medium | High (Country Risk) | FATF / Country Risk DB | **Wave 6** |
| **CO-07** | `REGULATORY_REPORTING` | Compliance | High STP | Low (Auto CTR) | Medium | Medium | High (Regulatory Handoff)| FinCEN / BoE Reporting | **Wave 6** |
| **CO-08** | `CUSTOMER_WATCHLIST_MATCH`| Compliance | Non-STP | Mandatory Fraud | High | Medium | High (Internal Watchlist)| Bank Fraud Engine | **Wave 6** |
| **TR-01** | `KYC_EXPIRED` | Client/Treasury| Policy STP | High (No grace) | Medium | Medium | High (KYC Lifecycle) | Client Master Expiry DB | **Wave 5** |
| **TR-02** | `INSUFFICIENT_FUNDS` | Client/Treasury| High STP | Low (Sweep auth) | Medium | Medium | High (Liquidity Pool) | Core DDA Real-Time Bal | **Wave 4** |
| **TR-03** | `NOSTRO_SHORTFALL` | Client/Treasury| Policy STP | Mandatory Treas | High | High | High (Nostro Position) | Treasury Position DB | **Wave 4** |
| **TR-04** | `FX_RATE_UNAVAILABLE` | Client/Treasury| High STP | Low (Spread auth)| Medium | Medium | High (FX Quote Engine) | Real-time FX Rates | **Wave 4** |
| **TR-05** | `AUTHORIZATION_MISSING` | Client/Treasury| Non-STP | Client-Facing | Medium | Medium | High (Mandate Gateway) | Corporate Mandate DB | **Wave 5** |
| **TR-06** | `LIMIT_BREACH` | Client/Treasury| Policy STP | High (Credit auth)| High | Medium | High (Limit Controller) | Credit Risk Limit Engine| **Wave 4** |
| **TR-07** | `LIQUIDITY_CONSTRAINT` | Client/Treasury| Policy STP | Mandatory Treas | High | High | High (RTGS Sequencer) | Central Bank RTGS Monitor| **Wave 4** |
| **TR-08** | `CREDIT_EXPOSURE_BREACH` | Client/Treasury| Policy STP | Mandatory Risk | High | High | High (Exposure Tracker) | ERM Risk Counterparty | **Wave 5** |
| **ST-02** | `ACCOUNT_CLOSED` | Settlement | High STP | Low (Auto credit)| Low | Low | High (Return Re-Credit) | Inbound pacs.004 Parser | **Wave 1** |
| **ST-03** | `ACCOUNT_FROZEN` | Settlement | Policy STP | High (Legal) | Medium | Medium | High (Legal Suspense) | Core DDA Freeze Ledger | **Wave 1** |
| **ST-04** | `RECONCILIATION_BREAK` | Settlement | Policy STP | High (Unmatched)| Medium | High | High (Multi-Way Recon) | camt.053 / MT940 Feed | **Wave 5** |
| **ST-05** | `SETTLEMENT_FAILURE` | Settlement | Policy STP | High (Recall) | High | High | High (Clearing Inquiry) | RTGS Finality Monitor | **Wave 3** |
| **ST-06** | `FUNDS_TRAPPED_AT_CORR` | Settlement | High STP | Low (GPI Inquiry)| Medium | Medium | High (SWIFT GPI Tracker)| SWIFT GPI API / MT199 | **Wave 3** |
| **ST-07** | `UNMATCHED_CREDIT` | Settlement | High STP | Low (Auto return)| Medium | Medium | High (Return Re-Credit) | Inward Settlement Ledger| **Wave 1** |

---

### 5. STP vs Controlled Workflow Classification

The remaining 30 profiles are classified into 5 operational execution tiers based on determinism, authority availability, and regulatory mandates:

```
+-------------------------------------------------------------------------------+
|                      PHASE 3 OPERATIONAL EXECUTION TIERS                      |
+-------------------------------------------------------------------------------+
| Tier A: STP-Capable Candidate (Deterministic & Authoritative) [8 Profiles]    |
|   * DQ-04, DQ-07, PR-02, PR-04, PR-07, ST-02, ST-06, ST-07                   |
|   -> Full autonomous STP under canonical 8-predicate formula.                 |
+-------------------------------------------------------------------------------+
| Tier B: STP-Capable Under Specific Bank Policy Envelope [11 Profiles]         |
|   * DQ-03, DQ-09, PR-06, CO-06, CO-07, TR-01, TR-02, TR-03, TR-04, TR-06, ST-03|
|   -> STP permitted if amount <= limit, pre-approved mandate/sweep active.    |
|   -> Otherwise routes to Maker-Checker dual authorization.                    |
+-------------------------------------------------------------------------------+
| Tier C: Human-In-The-Loop (HITL) / Controlled Decision [7 Profiles]          |
|   * CO-01, CO-02, CO-03, CO-05, CO-08, TR-07, TR-08                           |
|   -> Autonomous STP strictly prohibited by law or bank risk policy.          |
|   -> PeX gathers evidence dossier, pre-scores, and routes to Compliance/Risk. |
+-------------------------------------------------------------------------------+
| Tier D: Client-Facing Authorization / Operations Investigation [4 Profiles]   |
|   * PR-09, TR-05, ST-04, ST-05                                                |
|   -> Interactive corporate approval challenge or complex multi-way break recon.|
+-------------------------------------------------------------------------------+
```

---

### 6. Profile Resolution Archetypes

To eliminate duplicative code, the 30 profiles are mapped into **7 Core Resolution Archetypes**:

1. **Archetype 1: Deterministic Data & Identity Repair** (`DQ-03`, `DQ-04`, `DQ-07`, `DQ-09`):
   - Pattern: Match corrupted/missing field against authoritative bank master (DDA, CoP, ERP) and substitute verified value.
2. **Archetype 2: Dynamic Rail & Clearing Rescheduling** (`PR-02`, `PR-04`):
   - Pattern: Evaluate network availability and scheme cutoff calendars; switch rail (e.g. SWIFT $\to$ Fedwire) or roll value date.
3. **Archetype 3: Interbank Transport Inquiry & GPI Tracking** (`PR-06`, `PR-07`, `ST-05`, `ST-06`):
   - Pattern: Query clearing gateway or SWIFT GPI tracker; if unexecuted, re-dispatch; if rejected, initiate inquiry/recall.
4. **Archetype 4: Inward Settlement Returns & Automated Re-Credit** (`ST-02`, `ST-03`, `ST-07`):
   - Pattern: Multi-way reconciliation of inward return messages (pacs.004) with original payment debit; generate re-credit instruction.
5. **Archetype 5: Intraday Liquidity, Balance Sweeps & FX Quotes** (`TR-02`, `TR-03`, `TR-04`, `TR-06`, `TR-07`, `TR-08`):
   - Pattern: Query real-time DDA balance / nostro position / FX engine; execute automated sweep or route for credit extension.
6. **Archetype 6: Corporate Client Mandates & Multi-Way Reconciliation** (`TR-01`, `TR-05`, `ST-04`):
   - Pattern: Check corporate signatory matrix or reconcile statement (camt.053) against internal ledgers.
7. **Archetype 7: Financial Crime Compliance Dossier & Reporting** (`CO-01`, `CO-02`, `CO-03`, `CO-05`, `CO-06`, `CO-07`, `CO-08`):
   - Pattern: Assembly of immutable compliance evidence dossiers, prompt-injection sanitized entity scoring, and dual-authorization workflow.

---

### 7. Reusable Capability Map (TABLE B)

The table below defines the **10 Reusable Platform Engines** that will power all 30 remaining profiles:

| Reusable Platform Engine | Profiles Served | Primary Evidence Consumed | Authoritative Source Required | Reusability Factor | Target Production Infrastructure | AI / Agentic Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Account Master & CoP Engine** | `DQ-03, DQ-07, DQ-09, ST-02, ST-03` | Inbound account/name, CoP directory response | Core Banking DDA, Pay.UK CoP API | Very High (5 profiles) | Live Core DDA Adapter, Open Banking CoP | Name fuzzy matching, candidate alias ranking |
| **2. Dynamic Rail & Cutoff Engine** | `PR-02, PR-04, PR-06` | Payment payload, rail status, cutoff calendar | Scheme Operating Circular, Gateway Status | High (3 profiles) | Clearing Calendar DB, Real-Time Rail API | Historical routing cost/latency ranking |
| **3. Interbank Inquiry & GPI Tracker**| `PR-06, PR-07, ST-05, ST-06` | Gateway transport logs, SWIFT GPI UETR tracker | SWIFT Alliance Gateway, GPI API | High (4 profiles) | Live SWIFT SAG Connector, Message Bus | Inbound MT199/camt.029 natural language parsing |
| **4. Settlement Return & Re-Credit Engine**| `ST-02, ST-03, ST-07` (extends ST-01)| Inbound pacs.004, original debit ledger record | Core Settlement Ledger, Inward Clearing | High (3 profiles) | Core DDA Ledger API, Outbound Serializer | Reason code explanation generation |
| **5. Intraday Liquidity & Sweep Engine**| `TR-02, TR-03, TR-06, TR-07, TR-08` | DDA balance, Nostro positions, Credit limits | Core DDA Balance, Treasury Nostro Monitor | Very High (5 profiles) | Real-time Core Banking DDA API | Liquidity forecasting, sweep optimization |
| **6. Real-Time FX Contract Resolver** | `TR-04` | Currency pair, payment amount, value date | Bank Treasury FX Engine, Margin Policy | Medium (1 profile) | Treasury FX API, Rate Cache | FX spread trend analysis |
| **7. Financial Crime Dossier Engine** | `CO-01, CO-02, CO-03, CO-05, CO-06, CO-08`| Watchlist match, PEP record, Transaction history | OFAC/UN Feeds, TMS Alert DB, KYC Vault | Very High (6 profiles) | Dow Jones / LexisNexis API, AML DB | Entity disambiguation summary, news extraction |
| **8. Regulatory Reporting Dispatcher** | `CO-07` | Payment canonical data, reporting threshold | Statutory Reporting Authority (FinCEN) | Medium (1 profile) | Secure Regulatory Gateway API | Regulatory XML filing payload assembly |
| **9. Corporate Mandate & Auth Gateway**| `TR-01, TR-05` | Corporate signatory matrix, KYC expiry dates | Corporate Mandate DB, Client Master | Medium (2 profiles) | Corporate e-Banking SSO / Challenge API | Mandate clause interpretation |
| **10. Multi-Way Break Recon Engine** | `ST-04` | camt.053 / MT940 statements, internal ledgers | Central Clearing Statement, Bank Ledger | Medium (1 profile) | Statement Parsing Pipeline, Recon DB | Break root cause classification |

---

### 8. Phase 3 Dependency Graph

```
+----------------------------------------------------------------------------------------------------+
|                                      PHASE 3 DEPENDENCY GRAPH                                      |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [WAVE 0: PRODUCTION PLATFORM HARDENING]                                                            |
|  * AWS KMS / Enterprise Vault Port                                                                 |
|  * Distributed Redis / DynamoDB Idempotency Lock Manager                                           |
|  * Streaming Message Broker Connectors (Kafka / SQS / IBM MQ)                                      |
|  * Live Core Banking & Policy Adapters Interface                                                   |
|          |                                                                                         |
|          +---------------------------------------------------+                                     |
|          |                                                   |                                     |
|          v                                                   v                                     |
|  [WAVE 1: DATA QUALITY & RETURNS]                    [WAVE 4: LIQUIDITY & NOSTRO]                  |
|  * Reusable Account Master Engine                    * Reusable Intraday Liquidity Engine          |
|  * Reusable Return Re-Credit Engine                  * Reusable FX Quote Engine                    |
|  * Profiles: DQ-04, DQ-07, ST-02, ST-03, ST-07       * Profiles: TR-02, TR-03, TR-04, TR-06, TR-07 |
|          |                                                   |                                     |
|          v                                                   v                                     |
|  [WAVE 2: IDENTITY & ROUTING]                        [WAVE 5: MANDATES & RECONCILIATION]           |
|  * Reusable Beneficiary CoP Engine                   * Reusable Mandate Gateway                    |
|  * Reusable Dynamic Rail Router                      * Reusable Break Recon Engine                 |
|  * Profiles: DQ-03, DQ-09, PR-02, PR-04              * Profiles: TR-01, TR-05, TR-08, ST-04        |
|          |                                                   |                                     |
|          +-------------------------+-------------------------+                                     |
|                                    |                                                               |
|                                    v                                                               |
|                    [WAVE 3: NETWORK & INQUIRY TRACKING]                                            |
|                    * Reusable SWIFT GPI Tracker & Inquiry Engine                                   |
|                    * Profiles: PR-06, PR-07, PR-09, ST-05, ST-06                                   |
|                                    |                                                               |
|                                    v                                                               |
|                    [WAVE 6: FINANCIAL CRIME & REGULATORY]                                          |
|                    * Reusable Financial Crime Dossier Engine                                       |
|                    * Reusable Regulatory Reporting Dispatcher                                      |
|                    * Profiles: CO-01, CO-02, CO-03, CO-05, CO-06, CO-07, CO-08                     |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---

### 9. Semantic Collision Risk Assessment

A pre-implementation boundary audit was conducted across 12 critical adjacent profile pairs to pre-empt taxonomy collisions:

```
+----------------------------------------------------------------------------------------------------+
|                                    SEMANTIC COLLISION ASSESSMENT                                   |
+----------------------------------------------------------------------------------------------------+
| Profile Pair    | Potential Overlap Risk               | Immutable Architectural Boundary          |
+-----------------+--------------------------------------+-------------------------------------------+
| DQ-07 vs DQ-01  | Account vs IBAN format               | DQ-01 owns ISO 13616 IBANs. DQ-07 owns    |
|                 |                                      | domestic BBAN account numbers.            |
+-----------------+--------------------------------------+-------------------------------------------+
| DQ-03 vs DQ-09  | Missing data vs Mismatched name      | DQ-03 handles empty/missing tags. DQ-09   |
|                 |                                      | handles present tags failing CoP check.   |
+-----------------+--------------------------------------+-------------------------------------------+
| PR-02 vs DQ-08  | Routing failure vs Invalid code      | DQ-08 owns static routing number syntax.  |
|                 |                                      | PR-02 owns runtime dynamic rail failures. |
+-----------------+--------------------------------------+-------------------------------------------+
| PR-04 vs PR-08  | Cutoff missed vs Queue failure       | PR-04 handles scheme operating clocks.    |
|                 |                                      | PR-08 handles broker/DLQ deadlocks.       |
+-----------------+--------------------------------------+-------------------------------------------+
| PR-06 vs PR-02  | Intermediary reject vs Local routing | PR-02 is internal routing engine failure. |
|                 |                                      | PR-06 is external pacs.002 reject message.|
+-----------------+--------------------------------------+-------------------------------------------+
| PR-07 vs PR-08  | Socket timeout vs Broker DLQ         | PR-07 handles network transit ACK timeout.|
|                 |                                      | PR-08 handles internal queue persistence. |
+-----------------+--------------------------------------+-------------------------------------------+
| CO-01 vs CO-08  | Global sanctions vs Internal list    | CO-01 owns statutory OFAC/UN sanctions.   |
|                 |                                      | CO-08 owns internal bank fraud lists.     |
+-----------------+--------------------------------------+-------------------------------------------+
| CO-02 vs CO-03  | AML velocity alert vs PEP match      | CO-02 owns transaction monitoring alerts. |
|                 |                                      | CO-03 owns political exposure screening.  |
+-----------------+--------------------------------------+-------------------------------------------+
| TR-02 vs TR-07  | Account balance vs RTGS quota        | TR-02 owns customer DDA account balance.  |
|                 |                                      | TR-07 owns bank-wide RTGS clearing quota. |
+-----------------+--------------------------------------+-------------------------------------------+
| TR-03 vs TR-07  | Single Nostro vs Bank-wide RTGS      | TR-03 owns correspondent Nostro funding.  |
|                 |                                      | TR-07 owns central bank RTGS cap/quota.   |
+-----------------+--------------------------------------+-------------------------------------------+
| ST-02 vs DQ-07  | Closed account vs Invalid account    | DQ-07 owns unparseable account syntax.    |
|                 |                                      | ST-02 owns valid account closed in DDA.   |
+-----------------+--------------------------------------+-------------------------------------------+
| ST-04 vs ST-05  | Accounting break vs Settlement fail  | ST-04 owns ledger reconciliation breaks.  |
|                 |                                      | ST-05 owns failed central clearing cycles.|
+----------------------------------------------------------------------------------------------------+
```

---

### 10. Contextual Authority Source Strategy (TABLE D)

The table below maps the contextual authority required to establish validity for each remaining profile:

| Profile ID | Exception Condition | Authoritative Source (Tier 1 / Tier 2) | Primary Evidence Consumed | Bank Policy Scope | Mandatory Human Control |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DQ-03** | Missing Beneficiary Data | Core KYC / Client Onboarding Master | Customer Onboarding Record | Permitted field population rules | Maker-Checker if ambiguous |
| **DQ-04** | Missing Remittance Info | Corporate Client Billing / ERP Index | Invoice Ref / PO Number | Automated matching threshold | Operator if unindexed |
| **DQ-07** | Invalid Account Number | Core Banking DDA Account Master | Verified BBAN Record | Transposition repair policy | Operator if multiple accounts |
| **DQ-09** | Beneficiary Name Mismatch| National CoP Registry (Pay.UK / SEPA VoP)| Match Score & Legal Name | Name variance threshold | Mandatory for retail consumer |
| **PR-02** | Routing Failure | National Clearing / RTGS Status Feed | Gateway Status & Rail Matrix | Permitted alternate rails | Maker-Checker if fee exceeds |
| **PR-04** | Cutoff Missed | Scheme Operating Circular & Calendar | Scheme Clock & Timestamp | Next-day roll authorization | Operator if same-day mandated|
| **PR-06** | Intermediary Rejection | Downstream pacs.002 Reject Message | Return Code & Rejection Reason| Correspondent routing policy | Mandatory Maker-Checker |
| **PR-07** | Network Timeout | Network Gateway Transport Journal | In-Flight Message Tracker | Inquire-before-retry policy | Operator if status unknown |
| **PR-09** | Payment Held for Repair| Payment Operations Policy Manual | Repair Queue Ticket | Operations repair guidelines | Mandatory Operations Maker |
| **CO-01** | Sanctions Screening Hit| Statutory Sanctions Matrix (OFAC/UN/EU)| SDN Watchlist Dossier | Sanctions escalation policy | Mandatory MLRO Sign-Off |
| **CO-02** | AML Alert | AML Monitoring Engine (TMS) | Transaction Velocity Profile | AML escalation guidelines | Mandatory MLRO Sign-Off |
| **CO-03** | PEP Match | National PEP Register / EDD Archive | PEP Profile & EDD Report | PEP approval authority | Mandatory Senior Mgmt |
| **CO-05** | Adverse Media Match | Adverse Media Provider / Court Index | News Dossier & Legal Records | Adverse media risk appetite | Mandatory Compliance Analyst |
| **CO-06** | High-Risk Jurisdiction | FATF Country Risk Registry | FATF Blacklist / Greylist | Country risk threshold | Maker-Checker for high-value |
| **CO-07** | Regulatory Reporting | Statutory Reporting Rules (FinCEN/BoE) | Large Cash Wire Trigger | Automated filing policy | Compliance Officer Review |
| **CO-08** | Customer Watchlist | Bank Internal Fraud Watchlist | Fraud Incident History | Fraud risk policy | Mandatory Fraud Operations |
| **TR-01** | KYC Expired | Bank KYC Onboarding Master | Expiration Date & Renewal App | KYC grace period policy | Compliance Desk Review |
| **TR-02** | Insufficient Funds | Core DDA Real-Time Balance Ledger | Available Balance & Credit Line| Automated sweep policy | Credit Officer if unbacked |
| **TR-03** | Nostro Shortfall | Treasury Nostro Balance Monitor | Nostro Position & Clearings | Nostro buffer policy | Mandatory Treasury Officer |
| **TR-04** | FX Rate Unavailable | Treasury FX Market Rate Feed | Real-time FX Quote & Spread | FX spread tolerance policy | Treasury Desk if wide spread |
| **TR-05** | Authorization Missing | Corporate Electronic Banking Mandate | Corporate Signature Matrix | Mandate challenge policy | Corporate Signatory Action |
| **TR-06** | Limit Breach | Enterprise Credit Limit Engine | Daily Debit Accumulator | Temporary extension policy | Mandatory Credit Officer |
| **TR-07** | Liquidity Constraint | Central Bank RTGS Liquidity Monitor | RTGS Collateral & Headroom | Liquidity queue prioritization| Mandatory Head of Treasury |
| **TR-08** | Credit Exposure Breach | Enterprise Risk Management (ERM) DB | Counterparty Exposure Ledger | Exposure ceiling policy | Mandatory Chief Risk Officer |
| **ST-02** | Account Closed | Inbound pacs.004 (`AC04`) Return | Return Message & Original Debit| Auto-recredit policy | Operator if debit unposted |
| **ST-03** | Account Frozen | Core DDA Freeze Ledger / Court Order | Freeze Metadata & Legal Notice| Legal hold policy | Mandatory Legal Compliance |
| **ST-04** | Reconciliation Break | Central Clearing Statement (camt.053) | Daily Bank Ledger vs Statement| Break write-off threshold | Mandatory Accounting Officer |
| **ST-05** | Settlement Failure | Central Bank RTGS Finality Journal | Negative Settlement ACK | Recall vs Re-present policy | Mandatory Clearing Officer |
| **ST-06** | Funds Trapped at Corr | SWIFT GPI Tracker Journal | GPI Status & MT199 Trace | Query escalation timeline | Operator if unacknowledged |
| **ST-07** | Unmatched Credit | Nostro Inward Statement Ledger | Unmatched Inward pacs.008 | Return unmatched policy | Operator if claim active |

---

### 11. Bank-Scope vs Product-Scope Boundaries

To maintain clean enterprise separation, Phase 3 components are partitioned into 5 architectural layers:

```
+-------------------------------------------------------------------------------+
|                       PHASE 3 ARCHITECTURAL SCOPE LAYERS                      |
+-------------------------------------------------------------------------------+
| 1. UNIVERSAL PE-X PLATFORM CORE:                                              |
|    - Canonical 8-predicate STP evaluator, Trust Tier model, Idempotency lock   |
|    - Abstract BasePort interfaces, Cryptographic Audit Provenance Ledger       |
+-------------------------------------------------------------------------------+
| 2. REUSABLE DOMAIN ENGINES:                                                   |
|    - Account Master Engine, Rail Router, Sweep Engine, Return Reconciler       |
|    - Reusable across multiple banks and clearing schemes                       |
+-------------------------------------------------------------------------------+
| 3. BANK-SPECIFIC OPERATIONAL CONFIGURATION:                                   |
|    - Auto-STP threshold amounts, overdraft limits, permitted rail matrices   |
|    - Injected via structured BankPolicyRecord (Fails closed if missing)        |
+-------------------------------------------------------------------------------+
| 4. SCHEME / REGULATORY JURISDICTION ADAPTERS:                                 |
|    - ISO 20022 clearing specifications (Fedwire, CHAPS, TARGET2, SEPA)        |
|    - Statutory sanctions lists (OFAC, EU, UN, UK OFSI)                        |
+-------------------------------------------------------------------------------+
| 5. ENTERPRISE INFRASTRUCTURE ADAPTERS:                                        |
|    - Core Banking DDA connectors (Finacle, Temenos, SAP Banking)               |
|    - Cloud streaming & vault connectors (AWS KMS, Redis, Kafka, Aurora)        |
+-------------------------------------------------------------------------------+
```

---

### 12. Prioritization Framework & Scoring

Phase 3 profiles are prioritized across 6 weighted architectural and business dimensions:

$$\text{Priority Score} = 0.25(\text{Business Value}) + 0.20(\text{STP Potential}) + 0.20(\text{Determinism}) + 0.15(\text{Capability Reuse}) + 0.10(\text{Low Complexity}) + 0.10(\text{Dependency Weight})$$

1. **Business Value & Volume (25%)**: Market frequency of exception occurrences.
2. **STP Potential (20%)**: Feasibility of automated resolution without human risk.
3. **Resolution Determinism (20%)**: Mathematical and rule-based predictability.
4. **Platform Capability Reuse (15%)**: Unlocks shared engines for multiple profiles.
5. **Low Implementation Risk & Complexity (10%)**: Absence of blocking external dependencies.
6. **Dependency Foundation Weight (10%)**: Foundation required by downstream profiles.

---

### 13. Proposed Phase 3 Implementation Waves (TABLE C)

Phase 3 is partitioned into **7 Sequential Delivery Waves (Waves 0 through 6)**:

| Wave ID | Wave Name | Profiles Included | Shared Platform Capability | Dependencies | Value & Focus | STP Potential | Gate Exit Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Wave 0** | **Platform Infrastructure Enablement**| Infrastructure Only | Distributed Lock Manager, Cloud KMS, Kafka Connectors | Phase 2 Baseline | High / Platform Scalability | Infrastructure | Enterprise Cloud Adapters Verified |
| **Wave 1** | **Deterministic Data & Returns** | `DQ-04, DQ-07, ST-02, ST-03, ST-07` | Account Master Engine, Return Re-Credit Engine | Wave 0 | High / Immediate STP Volume | High (75%) | 100% Tests, Forensic Review Passed |
| **Wave 2** | **Identity & Dynamic Rail Routing**| `DQ-03, DQ-09, PR-02, PR-04` | Beneficiary CoP Engine, Rail & Cutoff Router | Wave 1 | High / Industry CoP Mandate | Medium (50%) | 100% Tests, Forensic Review Passed |
| **Wave 3** | **Transport, Network & Inquiry** | `PR-06, PR-07, PR-09, ST-05, ST-06`| SWIFT GPI Tracker & Inquiry Engine | Wave 0, Wave 2 | High / Interbank Visibility | Medium (40%) | 100% Tests, Forensic Review Passed |
| **Wave 4** | **Treasury, Balance & Liquidity** | `TR-02, TR-03, TR-04, TR-06, TR-07`| Core DDA Liquidity & Treasury Engine | Wave 0, Wave 1 | Very High / Liquidity Optimization | Medium (45%) | 100% Tests, Forensic Review Passed |
| **Wave 5** | **Mandates & Settlement Breaks** | `TR-01, TR-05, TR-08, ST-04` | Corporate Mandate Gateway, Recon Engine | Wave 4 | Medium / Governance Control | Low (25%) | 100% Tests, Forensic Review Passed |
| **Wave 6** | **Financial Crime & Compliance** | `CO-01, CO-02, CO-03, CO-05, CO-06, CO-07, CO-08`| Financial Crime Dossier & CTR Dispatcher | Wave 0, Wave 1 | Critical / Regulatory Safety | Low (15% - CTR only)| 100% Tests, Forensic Review Passed |

---

### 14. Production Infrastructure Track (TABLE E)

The table below outlines enterprise infrastructure dependencies and fail-closed behaviors:

| Infrastructure Dependency | Profiles Affected | Target Wave | Production Implementation Requirement | Fail-Closed Behavior if Unavailable |
| :--- | :--- | :--- | :--- | :--- |
| **AWS KMS / HashiCorp Vault** | All 41 Profiles | Wave 0 | Enterprise Hardware Security Module (HSM) PII Tokenizer | Aborts tokenization; fails closed (`SECURITY_ERROR`) |
| **Distributed Lock Manager** | All STP Profiles | Wave 0 | Multi-Node Redis / DynamoDB Atomic CAS Lock Manager | Rejects execution; returns `LOCK_UNAVAILABLE_SUSPENSE` |
| **Live Message Broker** | `PR-06..08, ST-05..07` | Wave 0 | Apache Kafka / IBM MQ / AWS SQS FIFO Cluster | Suspends queue processing; halts re-enqueue |
| **Live Core DDA Connector** | `DQ-07, TR-02, ST-02` | Wave 1 & 4 | Real-time REST/ISO 20022 Core Banking DDA API | Fails closed to `BANK_CONFIG_REQUIRED` |
| **Confirmation of Payee (CoP) API**| `DQ-09` | Wave 2 | Open Banking Directory / Pay.UK CoP API Connector | Returns `RESOLUTION_NOT_DETERMINED` $\to$ HITL Desk |
| **SWIFT Alliance Gateway (SAG)** | `PR-06, PR-07, ST-06` | Wave 3 | Live SWIFT GPI API & Interbank Messaging Gateway | Halts inquiry; routes to Operations Suspense |
| **Live Sanctions Feed** | `CO-01, CO-03, CO-06` | Wave 6 | Real-time OFAC / UN / EU XML XML Screening Feed | Fails closed to `COMPLIANCE_SUSPENSE` |

---

### 15. AI & Agentic Role in Phase 3

AI capabilities in Phase 3 remain strictly advisory, with zero authority to approve payments or clear compliance:

```
+-------------------------------------------------------------------------------+
|                         AI ROLES & BOUNDARIES IN PHASE 3                      |
+-------------------------------------------------------------------------------+
| PERMITTED AI CAPABILITIES (ADVISORY ONLY):                                    |
|  * Parsing unformatted remittance text and mapping to structured ERP invoices |
|  * Fuzzy scoring of corporate legal entity names against client alias tables  |
|  * Extracting relevant news passages from adverse media feeds (CO-05)         |
|  * Natural language explanation generation for operator repair desks (PR-09)  |
|  * Ranking candidate correspondent rerouting paths by cost/latency (PR-02)    |
+-------------------------------------------------------------------------------+
| STRICTLY FORBIDDEN AI ACTIONS (ZERO TOLERANCE):                               |
|  * Satisfying any of the 8 STP predicates (V_auth, P_bank, C_comp, X_pre)    |
|  * Clearing sanctions or AML screening alerts (CO-01, CO-02)                  |
|  * Inferring regulatory exemption licenses or customer authorizations         |
|  * Bypassing Maker-Checker Segregation of Duties                              |
|  * Directly mutating core banking ledgers or releasing wires                  |
+-------------------------------------------------------------------------------+
```

---

### 16. KPI & Observability Framework

Platform-level telemetry and metrics for Phase 3:

| KPI Category | Metric Name | Baseline Status | Measurement Purpose |
| :--- | :--- | :--- | :--- |
| **STP Performance** | Autonomous STP Rate (%) | Baseline Required | Measures % of exceptions resolved without human intervention |
| **STP Safety** | False Resolution Rate (PPM) | Target: 0 PPM | Ensures zero incorrect repairs or unauthorized wires occur |
| **Operational Speed**| Average Resolution Time (Sec) | Hypothesis: < 2.5s | Measures end-to-end pipeline latency from ingestion to handoff |
| **Evidence Quality** | Evidence Sufficiency Rate (%) | Baseline Required | Tracks frequency of complete vs incomplete bank evidence packages|
| **Human Workflow** | Maker-Checker Turnaround Time | Baseline Required | Measures operator review speed in HITL worklists |
| **Compliance Safety**| Compliance Escalation Rate (%) | Bank-Specific | Tracks volume of wires held for MLRO / EDD review |
| **Audit Completeness**| Merkle Provenance Chain Integrity| Target: 100% | Cryptographically verifies 100% tamper-evident audit trails |

---

### 17. Phase 3 Governance & Delivery Model

To ensure zero architecture drift, every Phase 3 Wave must execute the established 7-stage governance cycle:

$$\text{1. Wave Architecture Specification} \longrightarrow \text{2. Explicit Engineering Authorization}$$
$$\downarrow$$
$$\text{3. Implementation & AST Verification} \longrightarrow \text{4. Dedicated Behavioral & Adversarial Tests}$$
$$\downarrow$$
$$\text{5. Independent Forensic Acceptance Review} \longrightarrow \text{6. Multi-Profile Semantic Reconciliation}$$
$$\downarrow$$
$$\mathbf{7.\; Wave\; Acceptance\; Sign-Off\; \longrightarrow\; Proceed\; to\; Next\; Wave}$$

---

### 18. Phase 3 Program Exit Criteria

Phase 3 completion will be certified when all of the following conditions are met:

1. **Complete Taxonomy Coverage**: All 41 canonical exception profiles implemented, verified, and mapped.
2. **Zero Semantic Overlaps**: 100% disjoint domain ownership across all 41 profiles.
3. **Forensic Acceptance Chain**: All 6 delivery waves independently audited with zero P0, P1, or P2 defects.
4. **Canonical 8-Predicate Invariant**: Formula preserved universally without shortcuts.
5. **Full Platform Test Suite**: 100% green pass rate across all unit, behavioral, adversarial, and regression tests.
6. **Enterprise Infrastructure Readiness**: All Wave 0 cloud adapters verified against production staging environments.
7. **Maker-Checker & Terminal Handoff**: SoD and `execution_owner = "BANK"` verified across all 41 profiles.

---

### 19. Risks & Open Architectural Decisions

```
+-------------------------------------------------------------------------------+
|                           RISKS & OPEN DECISIONS LOG                          |
+-------------------------------------------------------------------------------+
| Risk ID     | Description                             | Mitigation Strategy   |
+-------------+-----------------------------------------+-----------------------+
| RISK-P3-01  | CoP API latency / external downtime     | Fail closed to HITL   |
|             | for DQ-09 (Beneficiary Name Mismatch).  | Disambiguation Desk.  |
+-------------+-----------------------------------------+-----------------------+
| RISK-P3-02  | Incomplete DDA real-time balances       | Require Tier 1 DDA    |
|             | causing false insufficient funds STP.   | Balance Lock adapter. |
+-------------+-----------------------------------------+-----------------------+
| RISK-P3-03  | High-throughput lock contention in      | Implement distributed |
|             | high-volume multi-pod cloud deployment. | Redis Redlock cluster.|
+-------------+-----------------------------------------+-----------------------+
| DECISION-01 | Confirmation of Payee fuzzy threshold   | Bank-Scope Policy DB  |
|             | (e.g. 85% vs 90% name match cutoff).    | Configuration.        |
+-------------+-----------------------------------------+-----------------------+
```

---

### 20. Explicit Engineering Authorization Requirements

```
================================================================================
                    GOVERNANCE BOUNDARY & AUTHORIZATION NOTICE
================================================================================

THIS CHARTER IS A PLANNING AND GOVERNANCE SPECIFICATION ONLY.

NO ENGINEERING AUTHORIZATION IS GRANTED BY THIS DOCUMENT.

Implementation of Phase 3 Waves (Wave 0 through Wave 6) requires:
1. Executive Governance Approval of this Charter.
2. Separate, explicit engineering authorizations issued per Wave.
3. Creation of isolated implementation branches for authorized waves.

================================================================================
```

---

### 21. Final Governance Recommendation

```
================================================================================
                       FINAL GOVERNANCE RECOMMENDATION
================================================================================

PHASE 3 PLANNING STATUS:  READY FOR GOVERNANCE APPROVAL

RECOMMENDED NEXT STEPS:
1. Submit this Charter (v0.1) for formal executive governance sign-off.
2. Issue explicit Engineering Authorization for WAVE 0 (Production Platform
   Infrastructure Enablement & Enterprise Cloud Adapters).
3. Authorize WAVE 1 (Deterministic Data Quality & Clearing Returns: DQ-04,
   DQ-07, ST-02, ST-03, ST-07) upon completion of Wave 0.

================================================================================
```

---
*Report filed by: Independent Senior Architecture Strategist & Phase Governance Planner*  
*Date: 2026-10-07*
