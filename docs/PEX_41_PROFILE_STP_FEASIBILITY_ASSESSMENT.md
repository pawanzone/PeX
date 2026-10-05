# 🏛️ PeX — 41-Profile STP Feasibility & Evidence Ingestion Architecture Assessment

> **Document Type:** Principal Enterprise Architecture, Payment SME & Regulatory Assessment  
> **Target Audience:** CXOs, Head of Payments Operations, Enterprise Architects, Regulatory Compliance & Product Leads  
> **Scope:** Exhaustive 41-Profile Evaluation of Batch/Folder STP Ingestion vs. Hexagonal ICD Corroboration  
> **Status:** Authoritative Architecture Assessment & Recommendation  

---

## Executive Summary & Reality Check

Your leadership proposed an operational model for PeX built on four foundational requirements:
1. **Input Folder / Heavy Upfront Ingestion:** Bank dumps an Error JSON into an input folder containing the break details plus pre-bundled evidence (pre-agreed fields) gathered simultaneously from multiple bank systems.
2. **Sufficiency Gate & Historical Pattern Matching:** PeX checks evidence sufficiency (`NON_FIXABLE` if incomplete); otherwise, compares evidence with historical repair records to determine the fix.
3. **Automated Output Folder (Auto-STP):** For pre-agreed error/risk/amount combinations, PeX auto-repairs and drops an Output JSON into an output folder for the bank's downstream settlement process.
4. **Direct Settlement Dispatch Option:** PeX dispatches the repaired transaction directly to clearing/settlement networks (Fedwire, SWIFT, CHAPS, TARGET2) on behalf of the bank.

### The Strategic Question: Is this a real Bank Business Case, or an Unvalidated Assumption?

**The Short Answer:**
It is a **hybrid reality**:
* **Where the Boss's Model is Factually True & Highly Desired:** Banks desperately want high STP rates (80%+) for **deterministic Data Quality and Syntax breaks** (Domains 1 & 2), and dropping repaired instructions into an output queue/folder is standard for legacy payment engines.
* **Where the Boss's Model is an Unviable Assumption:** 
  1. **Upfront Multi-System Bundling by Upstream Hubs:** Expecting a bank's legacy payment hub to orchestrate real-time synchronous queries across DDA Core, Sanctions Screening, Fedwire Directories, and Treasury to "pre-bundle evidence into a fat JSON" is contradictory. If the legacy hub had the integration bandwidth and intelligence to gather all that cross-system evidence in real-time, *it would have repaired the payment internally and never generated an exception*.
  2. **Direct Clearing Settlement Bypass:** Tier-1 banks will **never** allow a third-party AI platform to inject wires directly into central bank RTGS (Fedwire/TARGET2) or SWIFT without passing through the bank's core accounting, debit reservation, and AML compliance gate. Doing so violates UCC Article 4A, central bank operating circulars, and Segregation of Duties (SoD).
  3. **Binary Non-Fixable Rejection:** Marking payments `NON_FIXABLE` simply because upfront evidence wasn't pre-packaged destroys the core value proposition of PeX (which is proactive multi-channel corroboration).

---

# 1. Architectural Evaluation of the Boss's 4 Requirements

```
                               ┌────────────────────────────────────────────────────────┐
                               │       THE BOSS'S 4-REQUIREMENT PROPOSAL                │
                               └────────────────────────────────────────────────────────┘
                                                            │
         ┌──────────────────────────┬───────────────────────┴───────────────────────┬──────────────────────────┐
         ▼                          ▼                                               ▼                          ▼
┌──────────────────┐      ┌──────────────────┐                            ┌──────────────────┐       ┌──────────────────┐
│ 1. Upfront Batch │      │ 2. Binary Gate & │                            │ 3. Output Folder │       │ 4. Direct Clearing│
│    Folder Drop   │      │    Historical DB │                            │    Auto-STP Drop │       │    Agency Bypass │
└──────────────────┘      └──────────────────┘                            └──────────────────┘       └──────────────────┘
         │                          │                                               │                          │
         ▼                          ▼                                               ▼                          ▼
  REALITY CHECK:             REALITY CHECK:                                  REALITY CHECK:             REALITY CHECK:
❌ Flawed Premise          ⚠️ Partially Valid                              ✅ Industry Standard       ❌ Legally/Operationally
Legacy payment hubs        Historical pattern works for                    Pre-agreed STP repair      Disallowed
cannot query 5 peripheral  static SSI/BIC; dangerous                       for low-risk/low-amount    Banks must own ledger
systems during a break.    for dynamic liquidity/sanctions.                works via re-injection.    reservation & RTGS keys.
```

### Requirement 1: Upfront Multi-System Evidence Bundling in Input Folder
* **Bank Operational Reality:** In Tier-1 and Tier-2 banks, payment breaks occur in the Payment Engine (e.g., FIS OPF, Finastra GPP, Volante, ACI). When an exception triggers, the payment engine creates a bare error record (e.g., `ERR_CODE: INVALID_IBAN`, `RAW_MSG: <pacs.008>`).
* **Why Upfront Bundling Fails as a Sole Strategy:**
  * Core banking (DDA), Sanctions Screening, CRM, and Nostro ledgers are decoupled mainframe/microservice silos.
  * Payment engines do not have orchestrators to perform 5-way out-of-band queries during exception generation.
  * Ingestion folder polling (SFTP/File Drop) is viable as a **transport adapter**, but the *payload* will almost always be **evidence-poor**. PeX must possess the outbound intelligence (ICD adapters) to fetch missing data on-demand.

### Requirement 2: Sufficiency Gate (`NON_FIXABLE`) & Historical Pattern Comparison
* **Bank Operational Reality:** 
  * If PeX immediately marks an error `NON_FIXABLE` when evidence is missing from the input JSON, 85%+ of bank exceptions will be discarded back to manual queues, defeating the ROI of buying PeX.
  * **Historical Pattern Matching:** Highly effective for static counterparty repairs (e.g., "Corporate X always routes to DE89..."). However, **fatal** if applied blindly to dynamic states (e.g., applying historical routing when a beneficiary account has been closed or frozen by court order).
* **PeX Architectural Mandate:** PeX must use historical data as **Hypothesis Generation**, but corroborate against live real-time registries before authorizing repair.

### Requirement 3: Output Folder Auto-STP for Pre-Agreed Profiles/Amounts
* **Bank Operational Reality:** **100% Valid and Standard Practice.**
  * Banks call this "STP Repair Re-injection".
  * For low-risk, deterministic errors (e.g., IBAN MOD-97 check digit repair, structured postal formatting, purpose code enrichment) below risk thresholds (e.g., <$50,000), the bank configures auto-approval rules.
  * PeX writes the repaired canonical JSON (or formatted ISO 20022 XML) into the bank's pickup directory / message queue (MQ/Kafka), where the payment engine ingests it and continues the settlement journey.

### Requirement 4: Direct Dispatch to Settlement Agency on Behalf of Bank
* **Bank Operational Reality:** **Extremely Rare & Highly Restricted.**
  * Direct Fedwire/SWIFT injection requires:
    1. Direct participant SWIFT Alliance Gateway / FedLine Direct connectivity.
    2. SWIFT LAU (Local Authentication Unit) symmetric keys or HSM hardware security modules owned by the bank.
    3. Real-time accounting reservation: The bank's core ledger *must* debit the customer account before funds leave the central bank reserve. If PeX fires a wire directly, the bank risks an unhedged intraday overdraft or legal dispute under UCC 4A-202.
  * **Verdict:** PeX should generate the valid ISO 20022 clearing payload, but route it **back into the Bank's Payment Orchestrator**, which holds the cryptographic keys and performs core accounting debits.

---

# 2. Complete 41-Profile STP Feasibility & Evidence Matrix

The table below evaluates all **41 canonical exception profiles** across the 5 BIAN payment domains against:
1. **Error Detail & Trigger**
2. **Required Evidences & Source Systems**
3. **Upfront Bundling Feasibility (Can Bank send it in initial Error JSON?)**
4. **Compliance, Legal & Regulatory Constraints**
5. **Recommended STP Pattern & Architecture Verdict**

---

### DOMAIN 1: DATA QUALITY & FORMAT ERRORS (9 PROFILES)

| Code & Profile | Error Detail & ISO 20022 Context | Required Evidences & Source Systems | Upfront Feasibility at Error JSON Creation | Compliance, Legal & Regulatory Constraints | STP Feasibility & Recommended Resolution Pattern |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DQ-01**<br>`INVALID_IBAN` | Checksum remainder failure (`pacs.008` `<CdtrAcct><Id><IBAN>`). MOD-97 remainder $\neq 1$. | • Counterparty SSI Master (Internal)<br>• Historical Settlement Ledger (PeX/Bank)<br>• ISO 7064 MOD-97 Mathematical Solver | **HIGH (Partial)**<br>Bank can send raw IBAN and Debtor/Creditor IDs. Bank *cannot* run MOD-97 solver in legacy hub. | • UCC Article 4A (Erroneous Execution)<br>• Confirmation of Payee (CoP) UK/EU rules | **FULL AUTO-STP VIABLE (<$250k)**<br>PeX solves transposition typo (e.g. DE98 $\to$ DE89), validates MOD-97 = 1, checks SSI directory, generates repaired Output JSON. |
| **DQ-02**<br>`INVALID_BIC` | Inactive, retired, or malformed SWIFT BIC (`<CdtrAgt><FinInstnId><BICFI>`). | • SWIFTRef / ISO 9362 Directory (External)<br>• National RTGS Routing Directory (Fed/TARGET2)<br>• Head-Office Consolidation Map | **LOW**<br>Bank payment hub knows BIC failed validation, but rarely bundles SWIFTRef delta bulletins. | • SWIFT CBPR+ Mandate<br>• National RTGS Scheme Reachability Rules | **FULL AUTO-STP VIABLE**<br>PeX queries live SWIFTRef, maps sub-branch to active head-office BIC (`WESTGB2LXXX` $\to$ `WESTGB2L`), outputs repaired JSON. |
| **DQ-03**<br>`MISSING_BENEFICIARY_DATA` | Empty, placeholder, or truncated Creditor Name/Address (`<Cdtr><Nm>`). | • Core DDA Customer Master (Bank)<br>• AP Commercial Invoice / ERP (Corporate)<br>• Global LEI GLEIF Registry (External) | **MEDIUM**<br>Bank DDA has debtor info, but usually lacks creditor master for cross-border wires without ICD lookup. | • FATF Recommendation 16 (Travel Rule)<br>• FinCEN CDD Rule<br>• OFAC Re-screening Mandate | **CONDITIONAL STP (<$100k) / HITL (High)**<br>If LEI/Invoice match confidence $\ge 98\%$, auto-enrich and re-screen sanctions. Dual-auth required for new counterparties (<30d). |
| **DQ-04**<br>`MISSING_REMITTANCE_INFO` | Missing mandatory invoice reference or structured remittance (`<RmtInf><Ustrd>`). | • Open AP Ledger / ERP (Corporate Debtor)<br>• Historical Remittance Pattern (PeX Archive)<br>• E-Invoicing Peppol Network | **LOW**<br>Payment hub receives raw payload from debtor portal; cannot natively query corporate ERP AP tables. | • Commercial Contract Terms<br>• Central Bank Trade Reconciliation Audits | **AUTO-STP VIABLE (<$100k)**<br>PeX matches exact wire amount + debtor ID against AP open invoice feed, formats `<RmtInf>`, outputs repaired JSON. |
| **DQ-05**<br>`INVALID_ADDRESS_FORMAT` | Unstructured address lines violating 2026 ISO 20022 CBPR+ structured mandate. | • Postal Parsing Engine / NLP Parser<br>• National Postal Master (USPS/Deutsche Post)<br>• Corporate Registry Master | **HIGH**<br>Bank sends the unstructured raw text string. Upstream hub cannot parse discrete XML tags. | • ISO 20022 November 2026 Structured Address Enforcement Mandate | **FULL AUTO-STP VIABLE**<br>PeX explodes string into `<StrtNm>`, `<BldgNb>`, `<PstCd>`, `<TwnNm>`, `<Ctry>`, verifies postal schema, writes Output JSON. |
| **DQ-06**<br>`MISSING_PURPOSE_CODE` | Missing mandatory 4-letter ISO Purpose Code (`<Purp><Cd>`) in statutory corridor. | • Semantic Invoice Classifier (PeX)<br>• Corporate Debtor Historical Profile<br>• Destination Central Bank BoP Matrix | **LOW**<br>Bank hub lacks semantic classifier to deduce purpose code from free-text remittance. | • Cross-Border Balance of Payments (BoP) Reporting Statutory Mandates | **FULL AUTO-STP VIABLE**<br>PeX classifies remittance tokens (e.g. "PART SHIPMENT" $\to$ `GDSV`), validates against ISO 20022 external list, outputs repaired JSON. |
| **DQ-07**<br>`INVALID_ACCOUNT_NUMBER` | Domestic account number fails length/padding/check-digit rules (Fedwire {4200}). | • National Clearing Modulus Rules (Mod-10/11)<br>• Core DDA Routing Database<br>• Historical Debtor Outflows | **MEDIUM**<br>Bank provides account string. Hub cannot calculate multi-clearing modulus rules. | • NACHA Rules / Fedwire Operating Circular 6 | **FULL AUTO-STP VIABLE**<br>PeX applies domestic padding/modulus calculation (e.g., zero-padding 10 to 12 digits), checks branch range, outputs repaired JSON. |
| **DQ-08**<br>`INVALID_ROUTING_CODE` | Invalid ABA Routing (Fedwire), UK Sort Code, or Canadian Transit Code. | • Fedwire E-Payments Routing Directory<br>• UK EISCD Directory<br>• National Merger & Acquisition Transition Map | **LOW**<br>Bank payment hub holds static tables that may be outdated after bank mergers. | • Federal Reserve Regulation J<br>• Payment Finality Directives | **FULL AUTO-STP VIABLE**<br>PeX cross-references national clearing merger tables, substitutes retired ABA with successor routing number, outputs repaired JSON. |
| **DQ-09**<br>`BENEFICIARY_NAME_MISMATCH` | Confirmation of Payee (CoP) indicates name discrepancy between wire and account. | • Destination Bank CoP API / Directory<br>• Trade Contract / DBA (Doing Business As) Master<br>• Debtor Verified Beneficiary Master | **MEDIUM**<br>Bank can pass the CoP match score (Close Match / No Match), but lacks DBA cross-referencing. | • PSR Mandatory Reimbursement (APP Fraud)<br>• UK Confirmation of Payee Mandate | **HUMAN-IN-THE-LOOP (HITL) MANDATORY**<br>Cannot be 100% STP due to authorized push payment (APP) fraud liability. PeX prepares fuzzy name proof for Operator Maker-Checker. |

---

### DOMAIN 2: PROCESSING & ROUTING ERRORS (9 PROFILES)

| Code & Profile | Error Detail & ISO 20022 Context | Required Evidences & Source Systems | Upfront Feasibility at Error JSON Creation | Compliance, Legal & Regulatory Constraints | STP Feasibility & Recommended Resolution Pattern |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PR-01**<br>`DUPLICATE_PAYMENT` | Exact UETR collision or identical Amount/Beneficiary within 24h window. | • 24-Hour Settlement Archive (PeX/Bank)<br>• Original Message Hash Ledger<br>• Debtor Intent Confirmation | **HIGH**<br>Payment hub detects collision and flags the duplicate transaction ID/hash in the Error JSON. | • UCC Article 4A-205 (Erroneous Payments)<br>• CPDI Idempotency Mandates | **AUTOMATED SUPPRESSION / CANCEL**<br>If identical hash/UETR already settled: Auto-cancel duplicate. If distinct invoice with identical amount: Route to HITL for debtor release. |
| **PR-02**<br>`ROUTING_FAILURE` | Clearing rail unavailable, currency mismatch, or intermediary network break. | • Real-Time Clearing Rail Health Monitor<br>• Correspondent Nostro Directory<br>• CBPR+ Currency Corridor Matrix | **LOW**<br>Payment hub only sees connection reject; does not have multi-rail dynamic rerouting logic. | • Clearing Cutoff Regulations<br>• FX Exchange Control Regulations | **AUTO-STP REROUTE VIABLE**<br>PeX re-routes transaction from broken clearing rail (e.g. CHAPS offline $\to$ SWIFT CBPR+ or Fedwire), adjusts routing header, drops to Output Folder. |
| **PR-03**<br>`ISO20022_VALIDATION_ERROR` | Schema validation reject (XSD failure, invalid XML tag sequence, bad namespace). | • ISO 20022 XSD Schema Validator<br>• CBPR+ Usage Guidelines Matrix<br>• XML Element Order Re-sequencer | **HIGH**<br>Bank sends the raw malformed XML payload + XSD parser error trace. | • SWIFT Standards Release CBPR+ Strict Validation Rules | **FULL AUTO-STP VIABLE**<br>PeX repairs XML tag ordering, strips non-conformant namespace tags, validates against official XSD, drops compliant XML to Output Folder. |
| **PR-04**<br>`CUTOFF_MISSED` | High-value payment delayed; RTGS system cutoff SLA approaching (<1 hour). | • RTGS Operating Schedules (Fedwire/TARGET2)<br>• Intraday Value Dating Rules<br>• Liquidity Release Queue Status | **HIGH**<br>Payment hub timestamps confirm message creation time vs scheme cutoff. | • Federal Reserve OC 6<br>• TARGET2 Operating Mandate | **AUTO-STP VALUE DATE EXTENSION**<br>PeX evaluates next-day value date rollover (`<ValDt>`) or re-routes to 24/7 instant rail (FedNow/RTP) if amount eligible (<$500k). |
| **PR-05**<br>`CORRUPTED_MESSAGE_FORMAT` | Encoding corruption, illegal UTF-8 bytes, SWIFT Z-char set violation. | • Hex Payload Analyzer<br>• SWIFT Character Set Normalizer (EBCDIC/ASCII/UTF-8)<br>• Canonical Field Parser | **HIGH**<br>Bank dumps raw binary/hex payload in the Error JSON. | • SWIFT MT/MX Message Integrity Standards | **FULL AUTO-STP VIABLE**<br>PeX sanitizes illegal byte sequences, normalizes UTF-8 strings into valid SWIFT X/Z-character sets, outputs clean JSON/XML. |
| **PR-06**<br>`INTERMEDIARY_BANK_REJECTION` | Intermediary correspondent rejected wire with technical reason code. | • SWIFT MT199 / camt.056 Reject Trace<br>• Secondary Correspondent Routing Matrix<br>• Nostro Relationship Status | **MEDIUM**<br>Bank provides the reject code, but cannot dynamically compute alternate correspondent hops. | • Wolfsberg Correspondent Banking Principles | **AUTO-STP REROUTE VIABLE**<br>PeX replaces rejected intermediary BIC with verified alternate correspondent from bilateral agreement matrix, outputs repaired JSON. |
| **PR-07**<br>`NETWORK_TIMEOUT` | Clearing network unacknowledged ACK/NAK timeout; in-flight status unknown. | • SWIFT FIN/ACK Sniffer<br>• FedLine Direct Query Adapter<br>• Nostro Mirror Intraday Ledger | **LOW**<br>Payment hub is hung waiting on TCP socket; cannot determine state without deep network query. | • CPDI Settlement Finality Rules<br>• Non-Repudiation Directives | **ICD QUERY + RE-INJECTION**<br>PeX polls clearing network via ICD. If never received $\to$ re-dispatches with original UETR. If ACKed $\to$ marks settled. |
| **PR-08**<br>`QUEUE_PROCESSING_FAILURE` | Internal payment engine database lock / dead-letter queue (DLQ) serialization fault. | • Payment Hub Message State DB<br>• Idempotency Distributed Lock Store<br>• Transaction Sequence Log | **HIGH**<br>Bank middleware can dump the stalled queue payload directly into the Input Folder. | • Internal Operational Risk Standards | **FULL AUTO-STP RE-INJECTION**<br>PeX resets internal state counters, re-enriches canonical envelope, and drops clean message back to the engine's primary queue. |
| **PR-09**<br>`PAYMENT_HELD_FOR_REPAIR` | Generic manual repair queue hold in legacy Core/Hub. | • Legacy Core Repair Reason Code<br>• Field Validation Delta Report<br>• Historical Repair Taxonomy Map | **MEDIUM**<br>Bank provides the raw message and internal hold flag. | • Bank Standard Operating Procedures (SOP) | **AUTO-CLASSIFICATION & STP**<br>PeX parses the raw payload, auto-classifies the root cause into one of the 40 other profiles, and executes the appropriate STP fix. |

---

### DOMAIN 3: COMPLIANCE & SANCTIONS (8 PROFILES)

| Code & Profile | Error Detail & ISO 20022 Context | Required Evidences & Source Systems | Upfront Feasibility at Error JSON Creation | Compliance, Legal & Regulatory Constraints | STP Feasibility & Recommended Resolution Pattern |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CO-01**<br>`SANCTIONS_SUSPECTED` | Screening alert: Beneficiary or Debtor matches OFAC/UN/EU watchlist homonym. | • OFAC / UN / EU Consolidated Watchlists<br>• Full Customer KYC Dossier & DOB / Nationality<br>• Historical 32-Year Entity Disambiguation DB | **MEDIUM (Alert Only)**<br>Bank can pass the alert ID and matching string. Bank *cannot* pass full external watchlist graph. | • OFAC 50% Rule<br>• FinCEN Screening Mandates<br>• **STP strictly regulated** | **HUMAN-IN-THE-LOOP (HITL) MANDATORY**<br>PeX runs multi-factor disambiguation (DOB, Country $\neq$ Cuba), proves 0% entity match, but **requires L1/L2 Compliance Officer dual-sign-off**. Auto-release without human review violates federal consent decrees! |
| **CO-02**<br>`AML_ALERT` | Anti-Money Laundering velocity anomaly, rapid movement of funds, structuring. | • Core Banking 90-Day Transaction Ledger<br>• Customer Expected Turnover Profile<br>• SAR (Suspicious Activity Report) History | **LOW**<br>AML engine triggers alert; payment hub does not have access to customer historical turnover profile. | • Bank Secrecy Act (BSA) / FinCEN SAR Filing Rules | **HUMAN-IN-THE-LOOP (HITL) MANDATORY**<br>PeX aggregates 90-day velocity charts and KYC turnover expectations into an Evidence Dossier. Compliance Maker-Checker sign-off required. |
| **CO-03**<br>`PEP_MATCH` | Politically Exposed Person screening hit (Senior foreign political figure). | • PEP Global Intelligence Database (World-Check)<br>• Customer Source of Wealth (SoW) Filing<br>• Beneficial Ownership Registry | **LOW**<br>Screening tool passes raw PEP match score; lacks CDD documentation. | • FATF Recommendation 12 (PEPs)<br>• Senior Management Approval Mandates | **HITL DUAL-AUTHORIZATION MANDATORY**<br>PeX matches PEP role against public record. Requires Senior Compliance Officer sign-off. **Zero Auto-STP allowed**. |
| **CO-04**<br>`RESTRICTED_CORRIDOR` | Payment involves sanctioned territory (Crimea, Iran, North Korea, Syria, Cuba). | • Geopolitical Sanctions Matrix (OFAC/EU)<br>• Intermediary Bank Routing Geography<br>• Marine/Vessel Tracking AIS Data | **HIGH**<br>Payment hub flags the country code or city name triggering the jurisdictional block. | • OFAC Comprehensive Sanctions Programs<br>• Export Administration Regs (EAR) | **DETERMINISTIC REJECTION / BLOCK**<br>If verified sanctioned corridor: Auto-generate `pacs.002` Reject JSON and freeze transaction. If false geographic homonym: Route to Compliance. |
| **CO-05**<br>`ADVERSE_MEDIA_MATCH` | Negative news screening match (Financial fraud, bribery, terrorism ties). | • Adverse Media News Feed & Sentiment Engine<br>• KYC Master Entity Graph<br>• Commercial Trade Background | **LOW**<br>Bank screening tool alerts on news keyword; payment hub has no media context. | • Wolfsberg Group Anti-Corruption Standards | **HITL COMPLIANCE REVIEW**<br>PeX crawls articles, filters false positive names, scores adverse media severity, presents evidence package to Compliance Analyst. |
| **CO-06**<br>`HIGH_RISK_JURISDICTION` | FATF Greylist / High-Risk country transit requiring Enhanced Due Diligence (EDD). | • FATF Consolidated Greylist / Blacklist<br>• Enhanced Due Diligence (EDD) Form<br>• Commercial Trade License & Contract | **MEDIUM**<br>Bank can pass the country code; lacks trade contract attachment in the error payload. | • FATF Recommendation 19 (High-Risk Countries)<br>• EU 6AMLD Directives | **HITL EDD CLEARANCE**<br>PeX verifies EDD questionnaire completion status via ICD. If satisfied $\to$ presents for Compliance release. |
| **CO-07**<br>`REGULATORY_REPORTING_REQUIRED` | Missing central bank statutory Balance of Payments (BoP) reporting declaration. | • Central Bank Regulatory Reporting Portal<br>• Underlying Commercial Invoice / Customs Form<br>• Debtor Tax / Trade Identifier | **LOW**<br>Bank hub detects missing tag; cannot generate statutory BoP declaration without invoice. | • National Central Bank Exchange Control Mandates | **AUTO-STP GENERATION (<$250k)**<br>PeX generates required regulatory reporting XML block from parsed commercial invoice, updates `<RgltryRptg>` tag, drops to Output Folder. |
| **CO-08**<br>`CUSTOMER_WATCHLIST_MATCH` | Debtor or Creditor matches internal bank "Do Not Transact" or Special Attention list. | • Internal Bank Security / Risk Watchlist<br>• Credit Default / Fraud Historical DB<br>• Relationship Manager Case Notes | **HIGH**<br>Internal watchlist engine provides exact internal list ID and match reason. | • Internal Bank Risk Policy & Legal Mandates | **HITL RISK OFFICER APPROVAL**<br>PeX displays internal risk notes and reason for listing. Requires Risk Approver sign-off. |

---

### DOMAIN 4: CLIENT & TREASURY / OPERATIONAL ERRORS (8 PROFILES)

| Code & Profile | Error Detail & ISO 20022 Context | Required Evidences & Source Systems | Upfront Feasibility at Error JSON Creation | Compliance, Legal & Regulatory Constraints | STP Feasibility & Recommended Resolution Pattern |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TR-01**<br>`NOSTRO_SHORTFALL` | Nostro account at correspondent bank lacks intraday funds to cover wire settlement. | • Intraday Nostro Balance Feeds (camt.053)<br>• Treasury Liquidity Sweeping Engine<br>• Money Market / FX Swap Facility | **LOW**<br>Payment hub receives settlement hold from Nostro agent; lacks treasury cash balance across accounts. | • BCBS 248 Intraday Liquidity Management<br>• Clearing Scheme Default Rules | **TREASURY AUTO-SWEEP / QUEUE STP**<br>PeX triggers automated intraday Nostro rebalancing sweep request via ICD, polls for credit confirmation, releases wire upon liquidity arrival. |
| **TR-02**<br>`KYC_EXPIRED` | Corporate customer Periodic KYC / CDD review cycle is expired. | • Core Banking KYC Status DB<br>• Client Onboarding / Document Portal<br>• Compliance KYC Extension Registry | **HIGH**<br>Core banking blocks wire and provides KYC expiry date and customer ID. | • FinCEN Customer Due Diligence (CDD) Final Rule | **CONDITIONAL STP (Temporary Waiver)**<br>If low-risk recurring payroll/trade and KYC update is in-flight $\to$ PeX verifies approved 30-day grace period, tags waiver, and releases. |
| **TR-03**<br>`INSUFFICIENT_FUNDS` | Debtor customer account has insufficient available balance in DDA ledger. | • Core DDA Real-Time Balance Ledger<br>• Pre-Approved Intraday Overdraft Limit DB<br>• Scheduled Inbound Cash Sweeps | **HIGH**<br>Core banking DDA returns balance deficit amount and overdraft limit status. | • UCC Article 4A-201<br>• Federal Reserve Daylight Overdraft Rules | **STP LIQUIDITY POLLING / OVERDRAFT CHECK**<br>PeX checks if intraday credit line covers shortfall $\to$ auto-approves temporary hold; or queues wire until expected inbound batch posts. |
| **TR-04**<br>`FX_RATE_UNAVAILABLE` | Cross-currency wire FX rate quote timed out or market volatility exceeded spread. | • Treasury FX Auto-Pricing Engine<br>• Reuters/Bloomberg Market FX Ticker<br>• Client FX Margin Agreement | **LOW**<br>Payment hub only knows FX quote expired; cannot price new institutional spread. | • MiFID II Best Execution Mandate<br>• Dodd-Frank FX Swap Rules | **AUTO-STP RE-PRICING (<$500k)**<br>PeX requests fresh real-time spot quote from Bank FX Engine via ICD, updates exchange rate and converted amount `<InstdAmt>`, outputs repaired JSON. |
| **TR-05**<br>`AUTHORIZATION_MISSING` | Debtor corporate mandate requires dual-signatory approval (Missing 2nd token). | • Corporate Digital Banking Mandate Master<br>• Signatory Matrix & Delegation of Authority<br>• Out-of-Band Corporate Approval App | **HIGH**<br>Corporate banking channel flags missing 2nd approver in the raw instruction. | • Corporate Banking Mandate Legal Liability | **ASYNC CORPORATE NOTIFICATION STP**<br>PeX triggers push notification/webhook to corporate treasurer app for mobile biometrics. Upon receipt of 2nd signature, auto-releases wire. |
| **TR-06**<br>`LIMIT_BREACH` | Corporate customer daily wire outflow ceiling or velocity limit breached. | • Corporate Limit Management DB<br>• Intraday Cumulative Volume Counter<br>• Credit Officer Temporary Limit Facility | **HIGH**<br>Limit monitoring engine provides daily limit vs cumulative total in the Error JSON. | • Bank Credit & Operational Risk Policy | **HITL CREDIT OFFICER / AUTO-STEP-UP**<br>If within 10% tolerance and collateral pledged $\to$ auto-step-up. Otherwise, routes to Credit Officer for manual limit increase sign-off. |
| **TR-07**<br>`LIQUIDITY_CONSTRAINT` | Bank's aggregate central bank RTGS cap (Fedwire / CHAPS cap) reached for the hour. | • Central Bank Intraday Account Monitor<br>• Bank Treasury High-Value Priority Queue<br>• Collateral Optimization Engine | **LOW**<br>Payment engine is blocked by RTGS throttling; has no visibility into central bank collateral postings. | • Central Bank RTGS Liquidity Mandates | **AUTO-PRIORITY QUEUE RE-SEQUENCING**<br>PeX re-prioritizes queue based on client tier and SLA cutoff, holding low-priority wires until central bank liquidity refresh occurs. |
| **TR-08**<br>`CREDIT_EXPOSURE_BREACH` | Counterparty settlement risk limit maxed for the receiving correspondent bank. | • Enterprise Counterparty Risk Engine<br>• Net Settlement Exposure Ledger<br>• Collateralized Margin Buffer | **LOW**<br>Payment engine receives credit limit reject from risk engine; lacks credit mitigation options. | • Basel III Large Exposures Framework | **HITL CREDIT RISK APPROVAL**<br>PeX compiles gross counterparty exposure and pending inbound returns. Requires Credit Risk Officer authorization. |

---

### DOMAIN 5: SETTLEMENT & RETURNS (7 PROFILES)

| Code & Profile | Error Detail & ISO 20022 Context | Required Evidences & Source Systems | Upfront Feasibility at Error JSON Creation | Compliance, Legal & Regulatory Constraints | STP Feasibility & Recommended Resolution Pattern |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ST-01**<br>`RETURNED_PAYMENT` | Inbound `pacs.004` payment return received from receiving bank with reject code. | • Original Outbound `pacs.008` Archive<br>• Reason Code Registry (AC01, AC04, etc.)<br>• Customer Notification Channel | **HIGH**<br>Bank passes the inbound `pacs.004` XML message directly in the Error JSON. | • SWIFT CBPR+ Return Processing Rules<br>• Clearing Scheme Return Finality | **FULL AUTO-STP RETURN POSTING**<br>PeX matches original UETR, debits Nostro reconciliation mirror, credits customer DDA account, generates customer advice notification JSON. |
| **ST-02**<br>`ACCOUNT_CLOSED` | Beneficiary account closed at receiving institution (Return Reason `AC04`). | • Receiving Bank Return Advice (`pacs.004`)<br>• Counterparty Successor Account Directory<br>• Debtor Corporate Accounting Contact | **HIGH**<br>Receiving bank explicitly passes `AC04` return code. | • UCC Article 4A-402<br>• Payment Finality Directives | **AUTO-RETURN & NOTIFICATION / HITL REPAIR**<br>If debtor provided verified successor account in SSI $\to$ PeX prepares repair. Otherwise $\to$ auto-executes full return credit to debtor. |
| **ST-03**<br>`BENEFICIARY_ACCOUNT_FROZEN` | Account frozen due to court order, bankruptcy, or legal restraint (`AC06`). | • Legal Restraint / Court Order Attachment<br>• Inbound `pacs.004` / `camt.029` Notice<br>• Bank Legal Department Register | **HIGH**<br>Return message explicitly contains `AC06` (Blocked Account). | • Legal Subpoena / Asset Freezing Orders<br>• Insolvency Law | **SUSPENSE ESCROW / HITL LEGAL REVIEW**<br>**Zero Auto-STP allowed**. PeX routes funds to general ledger suspense escrow and alerts Legal/Special Operations. |
| **ST-04**<br>`RECONCILIATION_BREAK` | Nostro statement (`camt.053`) does not match internal ledger posting. | • Intraday Nostro Statement (`camt.053`)<br>• General Ledger Mirror Postings<br>• Clearing Fee / Charge Schedule | **LOW**<br>Reconciliation engine detects break during end-of-day or intraday run; payment hub is disconnected. | • SOX Section 404 (Financial Controls)<br>• BCBS Internal Audit Guidelines | **AUTO-STP RECONCILIATION MATCHING**<br>PeX matches fee deductions (e.g. \$25 correspondent charge), posts balancing GL entry, resolves break, outputs ledger update JSON. |
| **ST-05**<br>`SETTLEMENT_FAILURE` | Central bank RTGS finality failure (TARGET2 / Fedwire settlement unconfirmed). | • RTGS Central Bank Statement (`camt.054`)<br>• FedLine Settlement Confirmation Feed<br>• Intraday Liquidity Ledger | **LOW**<br>Payment hub sent wire but received no central bank finality proof. | • CPMI-IOSCO Principles for Financial Market Infrastructures (PFMI) | **ICD STATUS CORROBORATION + RE-DISPATCH**<br>PeX queries central bank query endpoint. If unsettled due to gridlock $\to$ holds and awaits RTGS release; if dropped $\to$ triggers re-dispatch. |
| **ST-06**<br>`FUNDS_TRAPPED_AT_CORRESPONDENT` | Funds debited from Nostro but never credited to Beneficiary (Stalled in transit). | • SWIFT GPI Tracker Query (UETR)<br>• Correspondent MT199 / camt.027 Claim Feed<br>• Intermediate Bank Nostro Statement | **LOW**<br>Payment hub shows sent; client reports non-receipt. Hub has no GPI tracking engine. | • SWIFT GPI SLA Commitments<br>• Cross-Border Payment Transparency Directives | **AUTO-GPI TRACE & camt.027 INQUIRY**<br>PeX triggers automated SWIFT GPI tracking query, isolates exact correspondent holding funds, auto-generates `camt.027` Claim for Value. |
| **ST-07**<br>`UNMATCHED_CREDIT` | Inbound credit received in Nostro with ambiguous or missing account reference. | • Core Banking Customer Name Matching DB<br>• Historical Corporate Inflows Ledger<br>• Inbound `pacs.008` / `pacs.009` Message | **HIGH**<br>Nostro agent passes the raw unallocated wire into the exception queue. | • Anti-Money Laundering (Unclaimed Funds)<br>• Unclaimed Property Statutes | **AUTO-MATCHING STP (<$100k) / HITL**<br>PeX executes fuzzy name + amount match against outstanding customer invoices. If 100% match $\to$ auto-posts DDA credit; if ambiguous $\to$ HITL. |

---

# 3. Structural Comparison: Boss's Batch Folder Model vs. PeX Event Architecture

```
┌───────────────────────────────────────┬───────────────────────────────────────────┬───────────────────────────────────────────┐
│ ARCHITECTURAL DIMENSION               │ BOSS'S PROPOSAL (Flat Folder / Batch STP) │ PeX REFERENCE ARCHITECTURE (Hexagonal)    │
├───────────────────────────────────────┼───────────────────────────────────────────┼───────────────────────────────────────────┤
│ Ingestion Model                       │ Input Folder (Polling JSON files on SFTP) │ Multi-Modal: Kafka / MQ Streaming + REST  │
│                                       │                                           │ + Ingestion Folder File Adapters          │
├───────────────────────────────────────┼───────────────────────────────────────────┼───────────────────────────────────────────┤
│ Evidence Availability                 │ Expected 100% Upfront in Error JSON       │ On-Demand Active Corroboration via ICD    │
│                                       │ (Unrealistic for legacy bank hubs)        │ Adapters (Core DDA, SWIFT, Fed, ERP)      │
├───────────────────────────────────────┼───────────────────────────────────────────┼───────────────────────────────────────────┤
│ Incomplete Evidence Handling          │ Binary Rejection: Mark `NON_FIXABLE`      │ Proactive Querying + Progressive Scoring  │
│                                       │ (Discards 85%+ of repair opportunities)   │ + Guided HITL if data missing             │
├───────────────────────────────────────┼───────────────────────────────────────────┼───────────────────────────────────────────┤
│ Decision Engine                       │ Historical Pattern Matching               │ Hybrid: Deterministic Algorithms (MOD-97) │
│                                       │ (Blind replay of past records)            │ + Live Registry Proofs + Policy Thresholds│
├───────────────────────────────────────┼───────────────────────────────────────────┼───────────────────────────────────────────┤
│ Resolution Execution                  │ Output Folder JSON Drop                   │ Output Queue / Re-injection API + Schema  │
│                                       │ (Bank picks up to settle)                 │ Re-validation + Event Notification        │
├───────────────────────────────────────┼───────────────────────────────────────────┼───────────────────────────────────────────┤
│ Clearing Rail Dispatch                │ Direct Send to Fedwire/SWIFT by PeX       │ Re-injected into Bank Payment Hub         │
│                                       │ (Legally & Operationally Prohibited)      │ (Bank owns accounting debit & LAU keys)   │
├───────────────────────────────────────┼───────────────────────────────────────────┼───────────────────────────────────────────┤
│ Regulatory Compliance                 │ Undifferentiated STP for all profiles     │ Strict Governance Boundary: Full Auto-STP │
│                                       │ (Violates OFAC/AML/FinCEN regulations)    │ for Syntax; Maker-Checker for Compliance  │
└───────────────────────────────────────┴───────────────────────────────────────────┴───────────────────────────────────────────┘
```

---

# 4. Critical Takeaways & Strategic Recommendation

### 1. Where Your Boss is 100% Right
* **Automated STP Output Queues:** Banks absolutely want automatic repair and STP resolution for high-volume, low-risk operational breaks. PeX *must* support seamless output generation (Output Folder / MQ / Kafka) that allows the bank's existing payment systems to pick up repaired transactions and settle them without human touch.
* **Historical Pattern Leverage:** Historical data is a goldmine for predicting correct beneficiary details, BIC consolidations, and corporate remittance patterns.

### 2. Where the Architecture Must Correct the Assumptions
* **Do Not Rely Exclusively on Upfront Evidence:** If PeX only accepts exceptions with pre-gathered evidence, banks will struggle to integrate PeX because upgrading their legacy payment hubs to orchestrate 5 external systems during a break is a multi-million dollar multi-year project. **PeX's true superpower is its ability to take a broken, evidence-poor JSON and proactively gather the evidence itself via ICD connectors.**
* **Never Execute Direct Clearing Settlement Without Bank Hub Re-injection:** PeX must never act as the direct settlement originator to Fedwire/SWIFT. The bank *must* retain control of the ledger reservation and cryptographic signing keys.
* **Enforce Regulatory Guardrails on Auto-STP:** Pure automated STP is legal and safe for **Domains 1, 2, and parts of 4 & 5** (Data Quality, Routing, Format, Technical Reconciliations). It is **strictly prohibited by law for Domain 3 (Sanctions, AML, PEP)** without audit-logged compliance officer oversight.

### 3. The Recommended Hybrid Architecture Blueprint
1. **Multi-Channel Ingestion Adapter:** Support the boss's **Input Folder JSON drops** for batch-oriented banks, alongside real-time Kafka/REST streaming for modern payment engines.
2. **Dual Evidence Harvesting:** Ingest whatever upfront fields the bank provides in the JSON, and *automatically trigger ICD adapters* to fetch remaining evidence from Core Banking, SWIFTRef, and Fedwire directories.
3. **Tiered STP & Approval Engine:**
   - **Tier 0 (Full Auto-STP):** Deterministic syntax/math repairs (MOD-97, BIC, Structured Address, Purpose Code) $\to$ Instant Output JSON generation.
   - **Tier 1 (Ops Maker-Checker):** Moderate risk / high value (> \$250k) $\to$ One-click approval desk.
   - **Tier 2 (Mandatory Compliance Dual-Auth):** Sanctions, PEP, AML $\to$ Dedicated compliance workflow with immutable Merkle audit hashing.
4. **Safe Downstream Settlement Re-injection:** Output repaired ISO 20022 XML/JSON into the bank's outbound settlement orchestrator, maintaining 100% compliance with UCC Article 4A and central bank operating circulars.
