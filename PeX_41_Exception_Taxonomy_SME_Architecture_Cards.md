# 🏛️ PeX: Complete 41-Profile Architecture & Business Rules Taxonomy Cards
> **Document Type:** Production Architecture Reference Cards (All 41 Error Types)
> **Target Audience:** Payment SMEs, Business Analysts, Operations Leads, Enterprise Architects & Client Evaluators
> **Specification Standard:** BIAN v10.0 / ISO 20022 CBPR+ / SWIFT PMPG Canonical Framework

---

## 📌 Structure of Each Taxonomy Card
Each of the 41 cards provides an exhaustive, code-independent blueprint covering:
1. **Profile ID, Name & BIAN Domain**
2. **ISO 20022 Context & Root Cause Trigger**
3. **#1 The 2-Point Human Triage Checklist** (The strategic questions presented to the human operator)
4. **#2 Value Derivation & Grounding Source Channels** (Where the replacement value or decision comes from)
5. **#3 The 5-Step Canonical Investigation Assessment & Proof Details** (The 5 automated checks evaluated by PeX)
6. **#4 Governance & Dual-Auth Threshold** (Approval routing and risk gates)

---


# 🏢 DOMAIN 1: DATA QUALITY & FORMAT ERRORS (9 PROFILES)

## 🏷️ Card [DQ-01]: INVALID_IBAN — Invalid IBAN Checksum (MOD-97 Remainder Break)
**BIAN Business Domain:** `DATA_QUALITY`  
**ISO 20022 Context:** `pacs.008.001.10 <CdtrAcct><Id><IBAN> - Fails ISO 13616 / ISO 7064 checksum verification`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[DATA INTEGRITY] Did someone typo the account number, or is this routing to the wrong beneficiary?**  
  *Operator Tip: Check character transposition diff and Confirmation of Payee (CoP) match.*
* **[REGULATORY CHECK] Does the repaired IBAN pass MOD-97 math and match the counterparty's Standing Settlement Instructions (SSI)?**  
  *Operator Tip: Verify ISO 7064 mathematical remainder = 1.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (SSI Directory): Queries Counterparty Master for registered canonical IBAN (Ref #SSI-9912).
* Channel 2 (Historical Velocity): Extracts IBAN from 14 successful prior settlements over last 90 days.
* Channel 3 (MOD-97 Math Solver): Solves transposition typos (DE98 -> DE89) ensuring remainder == 1.
* **Target Field Being Repaired:** `creditor_account.iban`
* **Sample Repaired Value:** `DE89 3704 0044 0532 0130 00`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **ISO 7064 MOD-97 Format Check** | Raw MOD-97 remainder = 1 (Deterministic Pass) | `[✓ VALIDATED]` |
| **2** | **Beneficiary Master Directory SSI** | Matched active profile in SSI Central Directory (Ref #SSI-9912) | `[✓ 100% SSI MATCH]` |
| **3** | **Confirmation of Payee (CoP)** | Beneficiary name matches destination account registry | `[✓ NAME MATCHED]` |
| **4** | **Clearing Rail & Currency Fit** | Target bank BIC active and accepts pacs.008 ISO 20022 messages | `[✓ CBPR+ PASS]` |
| **5** | **Behavioral Anomaly Guardrail** | Zero velocity anomalies. Established 3.5yr counterparty relationship | `[✓ NO ANOMALIES]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval (<$250k). Tier-2 Risk Dual-Auth required if >= $250k.

---

## 🏷️ Card [DQ-02]: INVALID_BIC — Invalid / Inactive SWIFT BIC Routing Code
**BIAN Business Domain:** `DATA_QUALITY`  
**ISO 20022 Context:** `pacs.008.001.10 <CdtrAgt><FinInstnId><BICFI> - BIC inactive, closed branch, or 8/11 character mismatch`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[ROUTING INTEGRITY] Why is this BIC failing? Has the destination bank merged or consolidated branches?**  
  *Operator Tip: Inspect SWIFT CBPR+ directory lifecycle status and head office clearing node.*
* **[CLEARING FIT] Does the target institution participate in the requested clearing scheme?**  
  *Operator Tip: Verify TARGET2 / Fedwire / CHAPS directory membership.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (SWIFTPlus Directory): Resolves retired sub-branch BIC to parent institution head-office BIC.
* Channel 2 (Clearing Scheme Registry): Validates active ISO 20022 reachable BIC in national RTGS directory.
* Channel 3 (Historical Routing Log): Matches previous successful wires to same corporate counterparty.
* **Target Field Being Repaired:** `creditor_account.bank_bic`
* **Sample Repaired Value:** `WESTGB2LXXX -> WESTGB2L`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **SWIFT Ref Data Cross-Check** | BIC validated against live ISO 9362 SWIFT directory | `[✓ SWIFT ACTIVE]` |
| **2** | **Head-Office Consolidation Map** | Retired branch routed to active regional clearing hub | `[✓ ROUTED HUB]` |
| **3** | **National Clearing Rail Reachability** | Target BIC confirmed active on CHAPS/Fedwire | `[✓ REACHABLE]` |
| **4** | **Sanctions & Embargo Filter** | Clearing institution has zero sanctions or embargo flags | `[✓ CLEARED]` |
| **5** | **Audit Custody Hash** | BIC replacement tied to SWIFT update bulletin #2026-04 | `[✓ AUDIT SEAL]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval. System automatically routes to active parent hub.

---

## 🏷️ Card [DQ-03]: MISSING_BENEFICIARY_DATA — Missing Beneficiary Legal Name / Incomplete Identity
**BIAN Business Domain:** `DATA_QUALITY`  
**ISO 20022 Context:** `pacs.008.001.10 <Cdtr><Nm> - Empty, truncated, or placeholder legal entity name`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[LEGAL IDENTITY] Is the complete legal entity name available in the bank's Counterparty Master?**  
  *Operator Tip: Cross-reference debtor account AP ledger and corporate registry.*
* **[FRAUD RISK] Does this wire match a known invoice, or does it show signs of social engineering?**  
  *Operator Tip: Verify invoice reference against debtor commercial trade history.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (DDA Master): Retrieves full legal name registered to the destination account number.
* Channel 2 (AP Trade Invoice): Extracts legal vendor name from remittance invoice token.
* Channel 3 (LEI Global Directory): Matches Legal Entity Identifier (LEI) to canonical business title.
* **Target Field Being Repaired:** `creditor_party.party_name`
* **Sample Repaired Value:** `Apex Precision Engineering GMBH`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Core DDA Name Retrieval** | Fetched registered corporate entity title from Account Master | `[✓ DDA MATCH]` |
| **2** | **LEI / Corporate Registry Match** | Verified against GLEIF registry database (LEI #549300...) | `[✓ LEI VERIFIED]` |
| **3** | **Commercial Invoice Tie-Out** | Invoice #INV-2026 matches registered creditor trade name | `[✓ AP MATCH]` |
| **4** | **Sanctions Re-Screening** | Re-screened full legal name against OFAC/EU watchlists (0% hit) | `[✓ SANCTIONS 0%]` |
| **5** | **ISO 20022 Field Structure** | Populated <Cdtr><Nm> within 140 character XML limit | `[✓ XSD PASS]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Maker Triage -> Tier-1 Ops Approval. High-risk if counterparty is newly created (<30 days).

---

## 🏷️ Card [DQ-04]: MISSING_REMITTANCE_INFO — Missing Mandatory Remittance Information
**BIAN Business Domain:** `DATA_QUALITY`  
**ISO 20022 Context:** `pacs.008.001.10 <RmtInf><Ustrd> - Missing invoice reference or structured remittance data`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[RECONCILIATION] Can this payment be auto-reconciled by the receiving corporate without an invoice tag?**  
  *Operator Tip: Check debtor ERP purchase order repository.*
* **[PURPOSE FIT] Does the remittance match the commercial purpose code of the transaction?**  
  *Operator Tip: Verify <Purp><Cd> aligns with invoice details.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (ERP Open AP Ledger): Matches wire amount and debtor ID to outstanding supplier invoice.
* Channel 2 (Historical Remittance Pattern): Synthesizes standard monthly billing contract reference.
* Channel 3 (E-Invoicing Network): Queries Peppol / electronic invoice data bridge.
* **Target Field Being Repaired:** `remittance_information.unstructured`
* **Sample Repaired Value:** `INV-2026-88412 APEX PART SHIPMENT PO-90112`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **ERP AP Invoice Match** | Exact amount match to outstanding invoice #INV-2026-88412 | `[✓ ERP MATCH]` |
| **2** | **Vendor Contract Verification** | Contract #CT-4401 active between debtor and creditor | `[✓ CONTRACT OK]` |
| **3** | **Duplicate Invoice Check** | Invoice #INV-2026-88412 has not been paid previously | `[✓ NO DUPLICATE]` |
| **4** | **ISO 20022 Formatting** | Structured into <RmtInf><Ustrd> tag complying with ISO rule | `[✓ XSD VALID]` |
| **5** | **Audit Provenance Stamp** | Attached ERP PO timestamp to case audit block | `[✓ AUDITED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval. Straight-through enrichment if ERP confidence >= 95%.

---

## 🏷️ Card [DQ-05]: INVALID_ADDRESS_FORMAT — Unstructured / Truncated ISO 20022 Postal Address
**BIAN Business Domain:** `DATA_QUALITY`  
**ISO 20022 Context:** `pacs.008.001.10 <PstlAdr> - Missing structured TownName/StreetName under 2026 mandate`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[SCHEMA COMPLIANCE] Does the address parse into structured ISO 20022 tags (TownName, StreetName, PstCd)?**  
  *Operator Tip: Unstructured address lines trigger hard 2026 CBPR+ reject.*
* **[JURISDICTION RISK] Is the country code aligned with the national clearing rail?**  
  *Operator Tip: Verify ISO 3166-1 alpha-2 country code.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Postal Address Parsing Engine): Deconstructs unstructured string into ISO tags.
* Channel 2 (National Postal Directory): Validates postal code against Deutsche Post / Royal Mail / USPS.
* Channel 3 (Corporate Registry Master): Pulls registered official corporate address.
* **Target Field Being Repaired:** `creditor_party.address_structured`
* **Sample Repaired Value:** `<StrtNm>Industriestrasse</StrtNm><BldgNb>14</BldgNb><PstCd>60329</PstCd><TwnNm>Frankfurt</TwnNm><Ctry>DE</Ctry>`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **ISO 20022 Structured Parser** | Successfully exploded into 5 discrete XML address tags | `[✓ STRUCTURED]` |
| **2** | **Postal Authority DB Check** | Postal Code 60329 matches Frankfurt am Main in national DB | `[✓ POSTAL PASS]` |
| **3** | **Sanctions Geographic Filter** | Address is outside sanctioned / disputed territories | `[✓ CLEARED]` |
| **4** | **Character Set / UTF-8 Check** | Zero illegal non-SWIFT characters in address fields | `[✓ UTF-8 OK]` |
| **5** | **Clearing Validation** | Target RTGS accepts structured postal block | `[✓ RTGS PASS]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval. Automated parser validation.

---

## 🏷️ Card [DQ-06]: MISSING_PURPOSE_CODE — Missing Mandatory ISO 20022 Purpose Code
**BIAN Business Domain:** `DATA_QUALITY`  
**ISO 20022 Context:** `pacs.008.001.10 <Purp><Cd> - Required under 2026 clearing mandates (e.g. GDSV, INTE, SALA)`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[MANDATORY TAG] Which 4-character ISO 20022 Purpose Code accurately classifies this payment?**  
  *Operator Tip: Check underlying commercial transaction context (Commercial Goods, Payroll, Treasury).*
* **[REGULATORY REPORTING] Does this corridor mandate Balance of Payments (BoP) reporting tags?**  
  *Operator Tip: Verify cross-border exchange control regulations.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Semantic Purpose Classifier): Analyzes invoice and remittance keywords -> classifies code.
* Channel 2 (Historical Debtor Profile): Identifies standard corporate purpose category (GDSV).
* Channel 3 (Corridor Regulatory Matrix): Maps statutory code mandated by destination central bank.
* **Target Field Being Repaired:** `purpose_code`
* **Sample Repaired Value:** `<Purp><Cd>GDSV</Cd></Purp> (Purchase & Sale of Goods)`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **ISO 20022 External Code List** | Purpose Code 'GDSV' is active in official ISO 20022 registry | `[✓ CODE VALID]` |
| **2** | **Invoice Text Alignment** | Invoice text 'PART SHIPMENT' aligns with GDSV commercial classification | `[✓ ALIGNED]` |
| **3** | **Central Bank Clearing Rule** | Satisfies destination central bank cross-border reporting mandate | `[✓ BOP PASS]` |
| **4** | **Counterparty Business Model** | Creditor SIC code 3541 (Manufacturing) matches GDSV purpose | `[✓ SIC MATCH]` |
| **5** | **XML Schema Validation** | <Purp> block inserted in correct XML sequence | `[✓ XSD PASS]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval. Straight-through classification if invoice match >= 98%.

---

## 🏷️ Card [DQ-07]: INVALID_ACCOUNT_NUMBER — Invalid Domestic Account Number Format / Length
**BIAN Business Domain:** `DATA_QUALITY`  
**ISO 20022 Context:** `pain.001.001.09 / Fedwire Tag {4200} - Account number string violates national clearing rules`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[ACCOUNT STRUCTURE] Does the account number conform to the domestic bank's routing format?**  
  *Operator Tip: Check standard length and padding (e.g. 10-digit US DDA vs 8-digit UK Sort).*
* **[CLIENT HISTORY] Has this debtor sent wires to this account number before?**  
  *Operator Tip: Inspect customer counterparty archive.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (National Clearing Algorithm): Applies zero-padding or check-digit correction.
* Channel 2 (DDA Core Registry): Validates account against live account ledger.
* Channel 3 (Previous Wires Archive): Cross-checks past successful wire instructions.
* **Target Field Being Repaired:** `creditor_account.account_number`
* **Sample Repaired Value:** `009876543210 (Padded 12-digit format)`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **National Rule Check** | Account length matches 12-digit Fedwire clearing spec | `[✓ RULE PASS]` |
| **2** | **DDA Account Modulus Check** | Passed modulus-11 check digit verification | `[✓ MOD-11 PASS]` |
| **3** | **Receiving Bank Validation** | Receiving routing ABA confirms branch operates this range | `[✓ ABA VALID]` |
| **4** | **Beneficiary Confirmation** | Account holder matches corporate trade name | `[✓ NAME MATCH]` |
| **5** | **Velocity Check** | Normal transaction amount within historical range | `[✓ SAFE VELOCITY]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval.

---

## 🏷️ Card [DQ-08]: INVALID_ROUTING_CODE — Invalid Fedwire ABA / UK Sort Code / Canadian Transit Code
**BIAN Business Domain:** `DATA_QUALITY`  
**ISO 20022 Context:** `pacs.008.001.10 <ClrSysMmbId><MmbId> - Routing code fails national checksum or inactive node`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[CLEARING DIRECTORY] Is this routing number active and eligible for funds settlement?**  
  *Operator Tip: Verify Federal Reserve E-Payments routing directory or UK Sort Code database.*
* **[BRANCH STATUS] Has this branch been acquired or merged into another routing ID?**  
  *Operator Tip: Check national routing directory merger tables.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Federal Reserve Routing Directory): Queries live 9-digit ABA routing master.
* Channel 2 (National Clearing Switch): Validates routing transit reachability.
* Channel 3 (Bank Merger Cross-Reference): Automatically maps merged routing IDs to successor bank.
* **Target Field Being Repaired:** `creditor_agent.routing_number`
* **Sample Repaired Value:** `021000021 (JPMorgan Chase NY Main Branch)`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Federal Reserve ABA Checksum** | Passed 3-7-1 weighting checksum calculation | `[✓ ABA VALID]` |
| **2** | **Fedwire Funds Eligibility** | Routing ID is flagged 'Eligible for Fedwire Funds' in Fed Directory | `[✓ FED ELIGIBLE]` |
| **3** | **Institution Name Match** | Routing name matches Beneficiary Bank title | `[✓ BANK MATCH]` |
| **4** | **Cutoff SLA Verification** | Target clearing node operating with normal SLA window | `[✓ SLA OPEN]` |
| **5** | **Audit Trail Block** | Routing verification logged in immutable ledger block | `[✓ AUDIT OK]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval.

---

## 🏷️ Card [DQ-09]: BENEFICIARY_NAME_MISMATCH — Confirmation of Payee (CoP) Name Discrepancy
**BIAN Business Domain:** `DATA_QUALITY`  
**ISO 20022 Context:** `camt.056 / pacs.008 - Name on wire diverges from destination account registration title`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[COP VERIFICATION] Is this an abbreviation/trading name (DBA), or a completely different legal entity?**  
  *Operator Tip: Inspect DBA records, corporate registry, and commercial contract.*
* **[FRAUD SCREEN] Does this indicate authorized push payment (APP) fraud or invoice redirection?**  
  *Operator Tip: Verify debtor trade history and bank account change authorization.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Corporate Registry DBA Cross-Ref): Resolves 'Apex Engineering' to 'Apex Precision Engineering GMBH'.
* Channel 2 (Trade Contract Vault): Verifies trade contract naming aliases.
* Channel 3 (Receiving Bank CoP API): Queries Confirmation of Payee match score.
* **Target Field Being Repaired:** `creditor_party.party_name`
* **Sample Repaired Value:** `Apex Precision Engineering GMBH (Verified Legal Entity)`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **CoP Fuzzy Matching Score** | Algorithmic match score = 94.2% (Close Match / Legal Alias) | `[✓ COP 94.2%]` |
| **2** | **Commercial Registry DBA Link** | Corporate registry links trading name to full corporate title | `[✓ DBA LINKED]` |
| **3** | **Debtor AP Relationship Length** | Debtor has active AP history with creditor for > 24 months | `[✓ ESTABLISHED]` |
| **4** | **Account Change Audit** | No recent bank account change within the last 60 days | `[✓ NO APP FRAUD]` |
| **5** | **Sanctions Rescan** | Resolved full legal name passed 100% clean sanctions scan | `[✓ SANCTIONS 0%]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Maker Review -> Tier-1 Ops Approval. Requires senior sign-off if CoP score < 85%.

---


# 🏢 DOMAIN 2: PROCESSING & ROUTING FAILURES (9 PROFILES)

## 🏷️ Card [PR-01]: DUPLICATE_PAYMENT — Duplicate Payment Detection (UETR / Amount Match)
**BIAN Business Domain:** `PROCESSING`  
**ISO 20022 Context:** `pacs.008.001.10 <UETR> / <InstdAmt> - Identical payment submitted within 24h window`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[DUPLICATION RISK] Is this a legitimate recurring payment, or an accidental double-submission?**  
  *Operator Tip: Check UETR, EndToEndId, amount, and debtor submission timestamp.*
* **[INTERCEPT ACTION] Should this duplicate transaction be canceled before clearing dispatch?**  
  *Operator Tip: Enforce cancel/reject workflow to prevent dual-debit.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Intraday UETR Deduplication Index): Detects exact UETR collision in active queue.
* Channel 2 (Transaction Hash Fingerprint): Compares [Debtor + Creditor + Amount + Remittance] hash.
* Channel 3 (Debtor ERP Submission Log): Identifies dual webhook dispatch from corporate client ERP.
* **Target Field Being Repaired:** `lifecycle.disposition`
* **Sample Repaired Value:** `INTERCEPT_AND_CANCEL_DUPLICATE`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **UETR Collision Test** | Matched active UETR #eb481a80... in transit clearing queue | `[✓ DUPLICATE UETR]` |
| **2** | **Payload Fingerprint Match** | 100% byte-for-byte match on Debtor, Creditor, Amount ($450k) | `[✓ HASH MATCH]` |
| **3** | **Settlement Status of Original** | Original transaction #TXN-8841 already SETTLED at 14:10 UTC | `[✓ SETTLED]` |
| **4** | **Debtor Dual-Debit Protection** | Intercepted duplicate before DDA debit execution | `[✓ DEBIT BLOCKED]` |
| **5** | **Audit Cancellation Seal** | Cancellation reason stamped into SHA-256 audit ledger | `[✓ CANCELLED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval for cancellation. Escalates to Maker if client requests override.

---

## 🏷️ Card [PR-02]: ROUTING_FAILURE — Clearing Rail / Intermediary Routing Failure
**BIAN Business Domain:** `PROCESSING`  
**ISO 20022 Context:** `pacs.008.001.10 <IntrmyAgt1> - Primary clearing bridge unavailable or disconnected`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[RAIL CONTINGENCY] Can this payment be rerouted via a secondary clearing bridge or bilateral corridor?**  
  *Operator Tip: Check clearing network availability and alternative correspondent hops.*
* **[CUTOFF TIME] Will the alternative route deliver funds prior to beneficiary cutoff?**  
  *Operator Tip: Verify secondary rail SLA cutoff time.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Dynamic Rail Health Monitor): Detects network outage on primary correspondent bridge.
* Channel 2 (Alternate Routing Engine): Identifies secondary reachable clearing path (e.g. TARGET2 via secondary node).
* Channel 3 (Correspondent Nostro Matrix): Verifies secondary intermediary holds funded settlement account.
* **Target Field Being Repaired:** `intermediary_agent.bic`
* **Sample Repaired Value:** `DEUTDEDDXXX (Secondary Active Correspondent)`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Primary Bridge Status Scan** | Primary node reported TIMEOUT / DEGRADED in health registry | `[✓ PRIMARY DOWN]` |
| **2** | **Secondary Rail Reachability** | Secondary correspondent node DEUTDEDD confirmed 100% OPERATIONAL | `[✓ SECONDARY ACTIVE]` |
| **3** | **Nostro Liquidity on Alt Rail** | Secondary Nostro account balance = $22.4M (Sufficient) | `[✓ NOSTRO OK]` |
| **4** | **Corridor SLA Verification** | Secondary route estimated settlement latency = 4.2 minutes | `[✓ SLA MET]` |
| **5** | **XSD Schema Adjustment** | Updated <IntrmyAgt1> XML tags to secondary correspondent | `[✓ XSD VALID]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval. System automatically configures contingency routing.

---

## 🏷️ Card [PR-03]: ISO20022_VALIDATION_ERROR — ISO 20022 XML Schema (XSD) Structural Error
**BIAN Business Domain:** `PROCESSING`  
**ISO 20022 Context:** `pacs.008.001.10 - Invalid XML tag hierarchy, illegal characters, or missing root envelope`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[SCHEMA VALIDATION] Which XML node violates the official ISO 20022 XSD schema specification?**  
  *Operator Tip: Inspect XSD line error and schema definition rules.*
* **[MESSAGE PURITY] Are there illegal control characters or unescaped XML entities?**  
  *Operator Tip: Verify character sanitization.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (XSD Schema Validator): Locates precise XML line break and missing envelope wrapper.
* Channel 2 (Canonical Transformation Engine): Restructures XML elements to compliant schema version.
* Channel 3 (Character Sanitizer): Strips non-UTF-8 control codes and unescaped ampersands.
* **Target Field Being Repaired:** `raw_payload_structure`
* **Sample Repaired Value:** `Valid ISO 20022 pacs.008.001.10 XML Envelope`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **XSD Syntax Compilation** | Compiled payload against official ISO 20022 pacs.008.001.10 schema | `[✓ XSD PASS]` |
| **2** | **Tag Sequence Ordering** | Reordered <GrpHdr>, <PmtInf>, <CdtTrfTxInf> in valid sequence | `[✓ SEQ VALID]` |
| **3** | **Character Entity Sanitization** | Replaced raw characters with valid XML entities (&amp;) | `[✓ SANITIZED]` |
| **4** | **Mandatory Element Fill** | Injected default mandatory settlement method <SttlmMtd>CLRG</SttlmMtd> | `[✓ MANDATORY OK]` |
| **5** | **Cryptographic Hash Recomputed** | Calculated payload hash for clean message | `[✓ HASH SEAL]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval. Straight-through reformatting if business data unchanged.

---

## 🏷️ Card [PR-04]: CUTOFF_MISSED — RTGS / High-Value Clearing Cutoff SLA Approaching (<1h)
**BIAN Business Domain:** `PROCESSING`  
**ISO 20022 Context:** `pacs.008.001.10 - Transaction in danger of breaching clearing window (Fedwire 16:30 / TARGET2 18:00)`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[URGENCY & SLA] Can this transaction be prioritized and auto-released before the cutoff closes?**  
  *Operator Tip: Inspect remaining minutes to cutoff vs processing latency.*
* **[NEXT-DAY SETTLEMENT] If cutoff is missed, will value-dating rollover cause client liquidity impact?**  
  *Operator Tip: Check value date policy and customer notification rules.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Real-Time Cutoff Monitor): Calculates remaining SLA minutes to clearing gate close.
* Channel 2 (Fast-Track Priority Queue): Elevates case to high-priority fast-track execution lane.
* Channel 3 (Value Date Adjuster): Automatically sets next-day value date if window is closed.
* **Target Field Being Repaired:** `processing_priority.queue`
* **Sample Repaired Value:** `FAST_TRACK_PRIORITY_LANE_DISPATCH`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Remaining SLA Calculation** | 42 minutes remaining to Fedwire 16:30 EST final cutoff | `[✓ SLA CRITICAL]` |
| **2** | **Fast-Track Queue Elevation** | Elevated to Priority Queue 0 (Top of Processing Stack) | `[✓ ELEVATED]` |
| **3** | **Pre-Funded Liquidity Allocation** | Earmarked instant settlement balance from central clearing pool | `[✓ FUNDED]` |
| **4** | **Maker Notification Ping** | Dispatched instant desktop notification to active Operations Lead | `[✓ PINGED]` |
| **5** | **Direct Clearing Bridge Dispatch** | Bypassed standard batch wait -> instant socket dispatch | `[✓ DISPATCHED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Operations Lead (Daniel Osei) Fast-Track Authorization.

---

## 🏷️ Card [PR-05]: CORRUPTED_MESSAGE_FORMAT — Corrupted Wire Message Payload / Encoding Error
**BIAN Business Domain:** `PROCESSING`  
**ISO 20022 Context:** `ISO 20022 message payload truncated during network transmission`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[PAYLOAD RECOVERY] Can the original payload be reconstructed from the ingress raw network packet?**  
  *Operator Tip: Check transmission gateway raw buffer and message checksum.*
* **[INTEGRITY SEAL] Does the recovered payload match the originator's submission hash?**  
  *Operator Tip: Verify payload digest against client transmission receipt.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Network Ingress Buffer): Reconstructs lost packet from raw gateway socket stream.
* Channel 2 (Client Transmission Receipt): Cross-checks client API payload hash.
* Channel 3 (Message Repair Engine): Repairs truncated closing XML tags.
* **Target Field Being Repaired:** `message_payload.reconstruction`
* **Sample Repaired Value:** `RECONSTRUCTED_FROM_INGRESS_BUFFER`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Raw Socket Stream Reassembly** | Reassembled missing 2.4KB from TCP packet stream | `[✓ REASSEMBLED]` |
| **2** | **XML Tag Closure** | Closed dangling XML tags and validated root structure | `[✓ TAGS OK]` |
| **3** | **Payload Checksum Verification** | Calculated SHA-256 matches client transmission receipt | `[✓ HASH MATCH]` |
| **4** | **Financial Data Verification** | Amounts and accounts match original ingress header | `[✓ DATA INTACT]` |
| **5** | **Re-Entry into Engine** | Re-injected into canonical processing pipeline | `[✓ RE-INJECTED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval.

---

## 🏷️ Card [PR-06]: INTERMEDIARY_BANK_REJECTION — Intermediary Correspondent Bank Technical Rejection
**BIAN Business Domain:** `PROCESSING`  
**ISO 20022 Context:** `pacs.002.001.10 (Payment Status Report) received with RJCT status from intermediary`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[REJECTION ANALYSIS] Why did the intermediary bank reject the wire (e.g. AC01, AGNT, RR04)?**  
  *Operator Tip: Examine ISO 20022 <StsRsnInf><Rsn><Cd> rejection code.*
* **[REROUTING OPTIONS] Should this wire be rerouted through an alternate correspondent or returned to debtor?**  
  *Operator Tip: Check bilateral correspondent network alternatives.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (pacs.002 Rejection Parser): Extracts specific rejection reason code (e.g. AC01 Incorrect Account).
* Channel 2 (Alternate Correspondent Matrix): Identifies secondary correspondent with direct clearing rights.
* Channel 3 (Customer Return Workflow): Generates pacs.004 return if error is non-repairable.
* **Target Field Being Repaired:** `intermediary_routing.action`
* **Sample Repaired Value:** `REROUTE_VIA_SECONDARY_CORRESPONDENT`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **pacs.002 Status Parser** | Parsed intermediary rejection: 'AC01 - Format Error at Correspondent' | `[✓ REASON AC01]` |
| **2** | **Format Normalization** | Adjusted formatting to match destination correspondent profile | `[✓ NORMALIZED]` |
| **3** | **Alternate Route Selection** | Selected secondary active correspondent DEUTDEDD | `[✓ ALT ROUTE]` |
| **4** | **Nostro Liquidity Re-allocation** | Transferred liquidity allocation to secondary Nostro | `[✓ FUNDS MOVED]` |
| **5** | **Re-Dispatch Preparation** | Generated new UETR sub-chain for outbound dispatch | `[✓ READY]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval.

---

## 🏷️ Card [PR-07]: NETWORK_TIMEOUT — Clearing Network Timeout / Missing Acknowledgment
**BIAN Business Domain:** `PROCESSING`  
**ISO 20022 Context:** `pacs.008 dispatched to SWIFT / Fedwire with zero ACK/NAK response within 180s`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[SETTLEMENT FINALITY] Did the central bank clear the wire, or was the packet lost in transit?**  
  *Operator Tip: Execute status inquiry (camt.056 / Fedwire inquiry) before re-sending.*
* **[DUPLICATION SHIELD] Is it safe to retransmit without creating a duplicate payment?**  
  *Operator Tip: Verify central bank message sequence number.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (camt.056 Status Inquiry Adapter): Automatically queries central bank gateway for finality status.
* Channel 2 (SWIFT gpi Tracker API): Verifies payment status via real-time gpi telemetry.
* Channel 3 (Safe Resend Engine): Retransmits with original UETR and duplication guard flag.
* **Target Field Being Repaired:** `network_status.inquiry`
* **Sample Repaired Value:** `STATUS_INQUIRY_CONFIRMED_UNPROCESSED_SAFE_RESEND`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Automated Status Query** | Dispatched camt.056 status inquiry to clearing gateway | `[✓ INQUIRY SENT]` |
| **2** | **Central Bank Status Response** | Gateway confirmed: 'NOT_FOUND_IN_CENTRAL_REGISTER' | `[✓ NOT CLEARED]` |
| **3** | **Debtor Account Audit** | Debtor funds held in pending transit suspense (Not debited) | `[✓ FUNDS HELD]` |
| **4** | **Safe Retransmission Key** | Generated idempotent retry header using original UETR | `[✓ IDEMPOTENT]` |
| **5** | **Resend Execution** | Dispatched packet over secondary socket channel | `[✓ RESENT OK]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval.

---

## 🏷️ Card [PR-08]: QUEUE_PROCESSING_FAILURE — Internal Payment Engine Queue Serialization Failure
**BIAN Business Domain:** `PROCESSING`  
**ISO 20022 Context:** `Transaction trapped in backend message broker (Kafka / MQ) due to partition lock`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[QUEUE HEALTH] Is this a single-case lock or a systemic partition bottleneck?**  
  *Operator Tip: Inspect broker queue depth and consumer group health.*
* **[RESUMPTION] Can this transaction be safely re-queued without violating sequence order?**  
  *Operator Tip: Verify account transaction sequence counter.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Dead Letter Queue Inspector): Extracts serialized message from DLQ.
* Channel 2 (Account Sequence Analyzer): Validates non-colliding sequence nonce.
* Channel 3 (Re-Drive Worker): Re-injects message into active processing partition.
* **Target Field Being Repaired:** `queue_status.redrive`
* **Sample Repaired Value:** `REDRIVE_DEAD_LETTER_MESSAGE`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Dead Letter Queue Extraction** | Extracted uncorrupted payload from DLQ partition #3 | `[✓ EXTRACTED]` |
| **2** | **Message Sequence Validation** | Account sequence counter validated (Seq #4401) | `[✓ SEQ OK]` |
| **3** | **Partition Lock Release** | Cleared stale consumer lock on worker node | `[✓ LOCK FREED]` |
| **4** | **Integrity Check** | All XML payload fields verified intact | `[✓ PAYLOAD OK]` |
| **5** | **Active Stream Injection** | Re-injected into priority processing stream | `[✓ RE-DRIVEN]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval.

---

## 🏷️ Card [PR-09]: PAYMENT_HELD_FOR_REPAIR — Payment Held in Core Banking Manual Repair Queue
**BIAN Business Domain:** `PROCESSING`  
**ISO 20022 Context:** `Legacy core banking platform marked transaction for manual operator intervention`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[REPAIR REASON] Why did legacy core hold this wire? Is it an unmapped field or standard review flag?**  
  *Operator Tip: Check legacy repair code mapping table.*
* **[AUTO-ENRICHMENT] Can PeX auto-enrich the missing field and release the hold in core banking?**  
  *Operator Tip: Verify core banking API hold release contract.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Legacy Repair Code Translator): Translates legacy core hold code to ISO 20022 canonical error.
* Channel 2 (Enrichment Engine): Auto-populates required field.
* Channel 3 (Core Banking Release API): Dispatches automated un-hold API call.
* **Target Field Being Repaired:** `core_banking.hold_status`
* **Sample Repaired Value:** `RELEASE_HOLD_IN_CORE_BANKING`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Legacy Hold Code Translation** | Translated legacy hold 'ERR-77' -> Missing Remittance Tag | `[✓ TRANSLATED]` |
| **2** | **Autonomous Field Enrichment** | Enriched missing remittance from ERP AP database | `[✓ ENRICHED]` |
| **3** | **Validation Rule Pass** | Passed all 5 data quality canonical guardrails | `[✓ GUARDRAILS PASS]` |
| **4** | **Core Banking API Contract** | Prepared REST API payload for Core DDA un-hold endpoint | `[✓ API READY]` |
| **5** | **Release Execution** | Core banking hold released -> advanced to settlement | `[✓ HOLD RELEASED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval.

---


# 🏢 DOMAIN 3: COMPLIANCE, SANCTIONS & AML (8 PROFILES)

## 🏷️ Card [CO-01]: SANCTIONS_SUSPECTED — Sanctions Screening Alert (Watchlist Homonym False Positive)
**BIAN Business Domain:** `COMPLIANCE`  
**ISO 20022 Context:** `pacs.008.001.10 - Screening engine hit on Beneficiary name against OFAC / EU / UN sanctions lists`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[SANCTIONS DISAMBIGUATION] Is this a true sanctioned entity or a false-positive homonym?**  
  *Operator Tip: Verify Tax ID, Country of Incorporation, Registration Date, and UBO chain.*
* **[LEGAL AUTHORITY] Does the reviewer possess formal compliance approval authority to clear this alert?**  
  *Operator Tip: Enforce compliance-only sign-off under SOP-301.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Secondary Identifier Disambiguation): Compares Tax ID, DOB, and Inc Date against SDN record.
* Channel 2 (Corporate Registry Verification): Confirms verified UK/US incorporation distinct from sanctioned person.
* Channel 3 (UBO Ownership Registry): Analyzes 100% of ownership tree down to 0% sanctioned interest.
* **Target Field Being Repaired:** `compliance_screening.disposition`
* **Sample Repaired Value:** `FALSE_POSITIVE_HOMONYM_CLEARED`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **OFAC / EU List Cross-Check** | Name similarity = 0.87 against SDN individual 'N. Components' | `[✓ ALERT 87%]` |
| **2** | **Tax ID / Registration Verification** | UK Companies House Reg #08819201 != SDN Individual Identifier | `[✓ TAX ID DIVERGENT]` |
| **3** | **Date of Incorporation Check** | Incorporated in 2014 vs SDN designation date in 1982 | `[✓ DOB MISMATCH]` |
| **4** | **Ultimate Beneficial Ownership (UBO)** | 100% of UBO chain cleared. Zero PEP / SDN ownership > 0% | `[✓ UBO CLEARED]` |
| **5** | **Adverse Media & Negative News** | Zero adverse media hits or regulatory enforcement actions | `[✓ CLEAN MEDIA]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** COMPLIANCE OFFICER EXCLUSIVE AUTHORITY (Marisol Vega). Operations cannot override.

---

## 🏷️ Card [CO-02]: AML_ALERT — Anti-Money Laundering (AML) Transaction Velocity Anomaly
**BIAN Business Domain:** `COMPLIANCE`  
**ISO 20022 Context:** `pacs.008.001.10 - Rule breach on transaction velocity, structuring, or unusual volume spike`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[COMMERCIAL JUSTIFICATION] Is there a documented commercial trade justification for this transaction volume?**  
  *Operator Tip: Verify underlying trade contract, invoice, and bill of lading.*
* **[SOURCE OF WEALTH] Has the debtor's source of wealth / funds been verified under AML policy?**  
  *Operator Tip: Inspect CDD refresh file and audited financials.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Enhanced Due Diligence Vault): Matches wire to registered annual supply agreement.
* Channel 2 (Historical Seasonality Model): Confirms annual inventory procurement cycle.
* Channel 3 (Corporate Bank Statement): Verifies origin of funds in debtor operating account.
* **Target Field Being Repaired:** `compliance_screening.aml_disposition`
* **Sample Repaired Value:** `EDD_VERIFIED_COMMERCIAL_TRADE`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Trade Contract Verification** | Underlying contract #TC-8812 verified with signed PO | `[✓ CONTRACT OK]` |
| **2** | **Seasonal Volume Alignment** | Matches annual Q3 supply procurement volume pattern | `[✓ SEASONAL PATTERN]` |
| **3** | **Debtor Operating Balance** | Funds originated from normal operational revenue | `[✓ LEGITIMATE SOURCE]` |
| **4** | **Beneficiary Operational Match** | Beneficiary business model aligns with supplied goods | `[✓ BUSINESS MATCH]` |
| **5** | **AML Risk Score Recalibration** | Recalibrated case risk score to 0.14 (Low Risk) | `[✓ LOW RISK]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Compliance Officer (Marisol Vega) Sign-off required.

---

## 🏷️ Card [CO-03]: PEP_MATCH — Politically Exposed Person (PEP) Screening Hit
**BIAN Business Domain:** `COMPLIANCE`  
**ISO 20022 Context:** `pacs.008.001.10 - Counterparty officer or UBO identified as PEP in global intelligence registry`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[PEP IDENTIFICATION] Is the matched individual a current senior political figure or family member?**  
  *Operator Tip: Verify PEP tier classification (Tier 1 Head of State vs Tier 3 Local).*
* **[SENIOR MANAGEMENT OK] Has Enhanced Due Diligence (EDD) been signed off by Senior Compliance Officer?**  
  *Operator Tip: Enforce PEP governance matrix.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Global PEP Registry): Evaluates exact political role, jurisdiction, and active status.
* Channel 2 (Commercial Transaction Verification): Verifies funds belong to corporate entity, not personal account.
* Channel 3 (Anti-Bribery & Corruption Shield): Validates zero government contract corruption flags.
* **Target Field Being Repaired:** `compliance_screening.pep_clearance`
* **Sample Repaired Value:** `PEP_TIER_3_EDD_CLEARED`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **PEP Tier Classification** | Director classified as Tier-3 (Former regional municipal councilor, left office 2018) | `[✓ TIER 3 PEP]` |
| **2** | **Entity vs Personal Fund Check** | Transaction is standard B2B commercial corporate wire (Not personal) | `[✓ B2B WIRE]` |
| **3** | **Source of Funds Verification** | Funds derived from audited commercial operating profits | `[✓ SOURCE VERIFIED]` |
| **4** | **Bribery Risk Analysis** | Zero public procurement / government bidding nexus | `[✓ NO BRIBERY RISK]` |
| **5** | **Senior Compliance Clearance** | EDD certificate approved under PEP Governance SOP-402 | `[✓ EDD APPROVED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Senior Compliance Lead Sign-Off.

---

## 🏷️ Card [CO-04]: RESTRICTED_CORRIDOR — Restricted Geopolitical Corridor / High-Risk Territory
**BIAN Business Domain:** `COMPLIANCE`  
**ISO 20022 Context:** `pacs.008.001.10 - Wire traverses high-risk or sanctioned geographic territory`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[CORRIDOR CLEARANCE] Does this corridor qualify under humanitarian, diplomatic, or licensed trade exemptions?**  
  *Operator Tip: Check OFAC General License or central bank trade permit.*
* **[TRANSIT ROUTING] Is intermediary routing isolated from sanctioned clearing jurisdictions?**  
  *Operator Tip: Verify intermediary transit banks.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Geopolitical Territory Risk Matrix): Assesses country risk rating and active sanctions.
* Channel 2 (Trade License Registry): Verifies OFAC/EU trade license authorization #GL-441.
* Channel 3 (Isolated Correspondent Rail): Ensures transit routing uses fully compliant intermediary.
* **Target Field Being Repaired:** `compliance_screening.corridor_license`
* **Sample Repaired Value:** `OFAC_GENERAL_LICENSE_GL441_ATTACHED`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Corridor Sanctions Map** | Destination territory subject to sectoral restrictions with valid license | `[✓ SECTORAL RESTRICTION]` |
| **2** | **Trade License Validation** | Valid OFAC General License #GL-441 verified on file | `[✓ LICENSE VALID]` |
| **3** | **Cargo & Goods Inspection** | Underlying invoice covers medical/humanitarian supplies (Exempt) | `[✓ EXEMPT GOODS]` |
| **4** | **Intermediary Clearance** | All transit correspondent banks hold valid corridor clearance | `[✓ TRANSIT OK]` |
| **5** | **Regulatory Reporting Stamp** | Automated filing prepared for central bank trade ledger | `[✓ FILING ATTACHED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Compliance Officer Sign-Off.

---

## 🏷️ Card [CO-05]: ADVERSE_MEDIA_MATCH — Adverse Media / Negative News Screening Alert
**BIAN Business Domain:** `COMPLIANCE`  
**ISO 20022 Context:** `pacs.008.001.10 - Counterparty flagged in global negative news and regulatory enforcement feeds`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[MEDIA RELEVANCE] Does the negative news relate to financial crime (fraud/bribery) or non-financial litigation?**  
  *Operator Tip: Evaluate adverse media category and legal adjudication status.*
* **[RISK POSTURE] Has the counterparty been cleared by the Special Investigations Unit (SIU)?**  
  *Operator Tip: Inspect SIU risk review report.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Adverse Media NLP Classifier): Categorizes news into Financial Crime vs Civil Litigation.
* Channel 2 (Legal Registry Disambiguation): Confirms lawsuit was dismissed with prejudice in 2023.
* Channel 3 (SIU Clearance Certificate): Pulls active SIU periodic clearance on file.
* **Target Field Being Repaired:** `compliance_screening.adverse_media`
* **Sample Repaired Value:** `ADVERSE_MEDIA_CIVIL_DISMISSAL_CLEARED`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **NLP Severity Categorization** | Flagged article relates to resolved civil trademark dispute (Not financial crime) | `[✓ CIVIL DISPUTE]` |
| **2** | **Court Docket Verification** | Civil case #CV-8891 dismissed with prejudice in 2023 | `[✓ DISMISSED]` |
| **3** | **Zero Financial Crime Nexus** | Zero mentions of money laundering, fraud, bribery, or tax evasion | `[✓ NO FIN-CRIME]` |
| **4** | **SIU Clearance Status** | SIU annual risk rating confirmed 'Standard Risk' | `[✓ SIU CLEARED]` |
| **5** | **Compliance Seal** | Attached court docket digest to case audit block | `[✓ SEALED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Compliance Officer (Marisol Vega) Sign-off.

---

## 🏷️ Card [CO-06]: HIGH_RISK_JURISDICTION — FATF High-Risk / Greylist Jurisdiction Processing
**BIAN Business Domain:** `COMPLIANCE`  
**ISO 20022 Context:** `pacs.008.001.10 - Payment involves entity or rail located in FATF monitored jurisdiction`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[FATF ENHANCED DUE DILIGENCE] Has Enhanced Customer Due Diligence (ECDD) been conducted for this corridor?**  
  *Operator Tip: Verify source of wealth, commercial trade invoice, and recipient registration.*
* **[REGULATORY REPORTING] Is a mandatory Suspicious Activity Report (SAR) or threshold filing required?**  
  *Operator Tip: Check FATF reporting requirements.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (FATF Compliance Gateway): Verifies enhanced CDD profile on debtor and creditor.
* Channel 2 (Commercial Invoice Tie-Out): Validates genuine physical trade documentation.
* Channel 3 (Regulatory Declaration Tag): Injects required regulatory classification tag.
* **Target Field Being Repaired:** `compliance_screening.fatf_clearance`
* **Sample Repaired Value:** `FATF_ECDD_VERIFIED_TRANSACTION`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **FATF Country Risk Score** | Corridor identified as FATF Monitored (Greylist) | `[✓ FATF GREYLIST]` |
| **2** | **ECDD Documentation Audit** | Refreshed ECDD file on record (Audited by KPMG, valid to 2027) | `[✓ ECDD CURRENT]` |
| **3** | **Physical Trade Inspection** | Bill of Lading #BL-9912 verified with port authority registry | `[✓ TRADE VERIFIED]` |
| **4** | **Dual Counterparty Screening** | 100% clean sanctions screening on all counterparties | `[✓ CLEAN]` |
| **5** | **Regulatory Reporting Envelope** | Embedded mandatory regulatory reporting tags into ISO XML | `[✓ REPORTED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Compliance Officer Sign-Off.

---

## 🏷️ Card [CO-07]: REGULATORY_REPORTING_REQUIRED — Mandatory Central Bank Regulatory Reporting (BoP Code Missing)
**BIAN Business Domain:** `COMPLIANCE`  
**ISO 20022 Context:** `pacs.008.001.10 <RgltryRptg> - Missing Balance of Payments (BoP) statistical declaration`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[BOP STATISTICAL CODE] Which Balance of Payments code is required by the destination central bank?**  
  *Operator Tip: Check central bank foreign exchange statistical guidelines.*
* **[TAX WITHHOLDING] Does this cross-border transaction require statutory tax withholding tags?**  
  *Operator Tip: Verify double-taxation treaty certificate.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Central Bank Reporting Matrix): Maps transaction type to statutory BoP classification code.
* Channel 2 (Tax Treaty Database): Validates applicable withholding tax exemption code.
* Channel 3 (ISO 20022 XML Builder): Formats <RgltryRptg> structure.
* **Target Field Being Repaired:** `regulatory_reporting.bop_code`
* **Sample Repaired Value:** `<RgltryRptg><Dtls><Cd>GDSV</Cd><Authrty><Ctry>DE</Ctry></Authrty></Dtls></RgltryRptg>`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Central Bank Mandate Rule** | Destination jurisdiction mandates BoP code for cross-border wires > EUR 12,500 | `[✓ MANDATE APPLIES]` |
| **2** | **Statutory Code Selection** | Selected code 'GDSV' (Trade in Physical Merchandise) | `[✓ CODE GDSV]` |
| **3** | **Tax Treaty Certificate** | Form W-8BEN-E / DTT treaty exemption verified on file | `[✓ TAX EXEMPT]` |
| **4** | **ISO XML Tag Generation** | Generated compliant <RgltryRptg> element | `[✓ XSD VALID]` |
| **5** | **Regulatory Registry Log** | Logged transaction in statutory central bank export queue | `[✓ LOGGED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval. Straight-through insertion if invoice is categorized.

---

## 🏷️ Card [CO-08]: CUSTOMER_WATCHLIST_MATCH — Internal Bank High-Risk / Special Attention Watchlist Hit
**BIAN Business Domain:** `COMPLIANCE`  
**ISO 20022 Context:** `pacs.008.001.10 - Counterparty matched internal bank risk watchlist or restricted list`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[INTERNAL WATCHLIST] Why was this customer placed on internal watch (e.g. credit monitoring, dispute history)?**  
  *Operator Tip: Inspect internal risk management case notes.*
* **[RELATIONSHIP MANAGER OK] Has the Senior Relationship Manager / Credit Officer approved this release?**  
  *Operator Tip: Verify credit committee approval memo.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Internal Risk Watchlist DB): Retrieves internal risk memorandum and case reason.
* Channel 2 (Credit Officer Approval Portal): Verifies active credit committee waiver.
* Channel 3 (Account Monitoring Rule): Validates transaction is within permitted activity scope.
* **Target Field Being Repaired:** `internal_risk.watchlist_clearance`
* **Sample Repaired Value:** `INTERNAL_WATCHLIST_WAIVER_APPROVED`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Internal Watchlist Match** | Matched internal watchlist category: 'Special Mention - Working Capital Monitor' | `[✓ SPECIAL MENTION]` |
| **2** | **Credit Officer Clearance** | Credit Officer (J. Sterling) approved operational processing memo | `[✓ CREDIT OK]` |
| **3** | **Permitted Activity Scope** | Wire is standard supplier payment within approved monthly limit | `[✓ WITHIN LIMIT]` |
| **4** | **Zero External Sanctions Hit** | 100% clean external regulatory screening | `[✓ OFAC CLEAN]` |
| **5** | **Audit Block Timestamp** | Logged credit committee memo #CC-4412 into audit trail | `[✓ AUDIT LOGGED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Compliance & Credit Approver Sign-off.

---


# 🏢 DOMAIN 4: CLIENT & TREASURY LIQUIDITY (8 PROFILES)

## 🏷️ Card [TR-01]: NOSTRO_SHORTFALL — Nostro Account Balance Shortfall / Liquidity Deficit
**BIAN Business Domain:** `CLIENT_TREASURY`  
**ISO 20022 Context:** `pacs.008.001.10 - Insufficient settled funds in destination currency Nostro account`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[LIQUIDITY ASSESSMENT] Is the Nostro corridor funded or does it require an intraday sweep?**  
  *Operator Tip: Check Nostro real-time balance and intraday credit line availability.*
* **[MANDATE VERIFICATION] Has the debtor corporate signatory threshold been validated?**  
  *Operator Tip: Verify mandate authorization matrix.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Central Treasury Pool Adapter): Triggers automated sweep from master liquidity pool.
* Channel 2 (Daylight Overdraft Facility): Evaluates pre-approved correspondent intraday credit line.
* Channel 3 (Intraday FX Swap Engine): Executes spot/intraday liquidity rebalancing.
* **Target Field Being Repaired:** `treasury_liquidity.corridor_allocation`
* **Sample Repaired Value:** `NOSTRO_SWEEP_FUNDED ($14.2M Allocated)`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Intraday Liquidity Position** | Central liquidity pool allocation confirmed ($14.2M available) | `[✓ FUNDS ALLOCATED]` |
| **2** | **Daylight Facility Check** | Debtor daylight overdraft authorized within approved facility | `[✓ FACILITY ACTIVE]` |
| **3** | **FX Market Rate Lock** | Guaranteed rate quote bound via secondary aggregator | `[✓ FX LOCKED]` |
| **4** | **Corporate Mandate Sign-Off** | Corporate treasurer authorization verified via digital portal | `[✓ MANDATE OK]` |
| **5** | **BCBS 248 Buffer Protection** | Intraday liquidity outflow complies with regulatory buffer targets | `[✓ BUFFER MET]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval (<$250k). Tier-2 Risk Dual-Auth required if >= $250k.

---

## 🏷️ Card [TR-02]: KYC_EXPIRED — Periodic KYC / Customer Due Diligence (CDD) Expired
**BIAN Business Domain:** `CLIENT_TREASURY`  
**ISO 20022 Context:** `pain.001 / pacs.008 - Debtor or Creditor annual KYC review date has elapsed`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[KYC GOVERNANCE] Is this counterparty eligible for a 30-day provisional processing waiver under SOP-302?**  
  *Operator Tip: Check counterparty risk rating, documentation refresh status, and historical dispute rate.*
* **[HIGH-VALUE ESCALATION] Does this transaction exceed $250k requiring secondary Risk Approver dual sign-off?**  
  *Operator Tip: Enforce Step 1 Compliance -> Step 2 Risk dual approval chain.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Onboarding KYC Master DB): Verifies refreshed documentation is in review pipeline.
* Channel 2 (SOP-302 Policy Waiver Engine): Calculates provisional processing eligibility score.
* Channel 3 (Relationship Credit Matrix): Confirms Tier-1 Multinational corporate standing.
* **Target Field Being Repaired:** `customer_kyc.provisional_status`
* **Sample Repaired Value:** `WAIVER_ACTIVE_30_DAYS`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Tier-1 Corporate Status** | Certified Tier-1 Multinational Corporate account | `[✓ TIER 1 CLIENT]` |
| **2** | **Documentation Refresh Status** | Refreshed board resolution received and in review by onboarding | `[✓ REFRESH IN PROGRESS]` |
| **3** | **24-Month Risk Track Record** | Zero SARs, regulatory queries, or returned payments in 24 months | `[✓ CLEAN RECORD]` |
| **4** | **Corridor Risk Ceiling** | Low-risk AUD/USD clearing corridor; well within credit limits | `[✓ LOW RISK]` |
| **5** | **SOP-302 Waiver Compliance** | Provisional 30-day processing waiver authorized under SOP-302 §4 | `[✓ WAIVER GRANTED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Compliance Approval + Tier-2 Risk Dual-Auth if >= $250k.

---

## 🏷️ Card [TR-03]: INSUFFICIENT_FUNDS — Insufficient Available Customer Funds in Debit Account
**BIAN Business Domain:** `CLIENT_TREASURY`  
**ISO 20022 Context:** `pain.001.001.09 - DDA account balance insufficient to cover wire principal + fees`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[FUNDS AVAILABILITY] Does the client have incoming cleared funds in transit or an active sweep agreement?**  
  *Operator Tip: Inspect intraday ledger deposits and linked multi-currency accounts.*
* **[CREDIT LINE OVERDRAFT] Can daylight overdraft be authorized based on client credit rating?**  
  *Operator Tip: Verify uncommitted daylight facility limit.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Core Banking DDA Ledger): Identifies incoming cleared deposit pending batch post.
* Channel 2 (Corporate Sweep Agreement): Triggers automated sweep from subsidiary account.
* Channel 3 (Daylight Credit Limit Engine): Authorizes temporary intraday overdraft.
* **Target Field Being Repaired:** `account_balance.sweep_authorization`
* **Sample Repaired Value:** `INTRADAY_SWEEP_EXECUTED ($500k Sweep)`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Incoming Deposit Verification** | Confirmed $850k incoming wire in transit clearing queue | `[✓ FUNDS INCOMING]` |
| **2** | **Corporate Sweep Authorization** | Automated sweep triggered from master USD treasury account | `[✓ SWEEP OK]` |
| **3** | **Daylight Credit Line** | Overdraft authorized within approved $5M daylight facility | `[✓ CREDIT ACTIVE]` |
| **4** | **DDA Debit Execution** | DDA account balance restored to positive $350k balance | `[✓ BALANCE RESTORED]` |
| **5** | **Settlement Release** | Released wire hold for immediate RTGS dispatch | `[✓ RELEASED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval + Credit Lead if overdraft drawn.

---

## 🏷️ Card [TR-04]: FX_RATE_UNAVAILABLE — Cross-Currency FX Rate Quote Timeout / Expired Spread
**BIAN Business Domain:** `CLIENT_TREASURY`  
**ISO 20022 Context:** `pacs.008.001.10 - FX conversion quote elapsed during exception processing delay`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[FX SPREAD] Can the FX quote be refreshed within the client's pre-agreed pricing spread?**  
  *Operator Tip: Check live treasury aggregator rate vs client FX pricing schedule.*
* **[SLIPPAGE RISK] Does rate slippage exceed client authorization threshold (e.g. > 15 bps)?**  
  *Operator Tip: Enforce slippage tolerance guardrails.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Treasury FX Aggregator API): Requests live streaming quote for currency pair.
* Channel 2 (Client Pre-Agreed Spread Schedule): Applies contract pricing tier (e.g. 8 bps).
* Channel 3 (FX Lock Contract): Locks rate for 120-second execution window.
* **Target Field Being Repaired:** `foreign_exchange.rate_quote`
* **Sample Repaired Value:** `FX_RATE_REFRESHED_1.0842_EUR_USD`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Live Treasury Quote Request** | Fetched live rate EUR/USD = 1.0842 from Primary Treasury Engine | `[✓ RATE FETCHED]` |
| **2** | **Contract Spread Application** | Applied corporate Tier-1 contracted spread (+0.0008) | `[✓ SPREAD APPLIED]` |
| **3** | **Slippage Tolerance Check** | Market movement = 4.2 bps (Well within 15 bps tolerance limit) | `[✓ SLIPPAGE OK]` |
| **4** | **Execution Window Lock** | Locked rate guaranteed for 120s execution window | `[✓ RATE LOCKED]` |
| **5** | **ISO XML Tag Update** | Populated <XchgRate>1.0850</XchgRate> in pacs.008 message | `[✓ XSD UPDATED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval.

---

## 🏷️ Card [TR-05]: AUTHORIZATION_MISSING — Debtor Corporate Signatory Dual-Authorization Missing
**BIAN Business Domain:** `CLIENT_TREASURY`  
**ISO 20022 Context:** `pain.001.001.09 - High-value payment submitted with single signature violating mandate`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[SIGNATURE MANDATE] Does corporate mandate require 2 authorized signatories for this amount?**  
  *Operator Tip: Inspect digital portal authorization matrix and signature limit.*
* **[CALLBACK VERIFICATION] Has out-of-band digital callback verification been completed?**  
  *Operator Tip: Verify OTP / multi-factor biometrics from secondary signer.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Corporate Banking Portal API): Pulls secondary digital signature from approval queue.
* Channel 2 (Mandate Matrix Engine): Verifies signer authority level (Class A Signatory).
* Channel 3 (Multi-Factor Biometric Log): Attaches cryptographic signature confirmation.
* **Target Field Being Repaired:** `mandate_authorization.status`
* **Sample Repaired Value:** `DUAL_AUTHORIZATION_VERIFIED`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Corporate Mandate Policy Check** | Mandate mandates Dual Sign-off for payments >= $250k | `[✓ MANDATE REQUIRED]` |
| **2** | **Secondary Digital Sign-off** | Secondary signatory (Corporate CFO) approved via digital token | `[✓ SIGNED OK]` |
| **3** | **Signatory Authority Level** | Signatory verified as Class-A registered director | `[✓ CLASS A SIGNER]` |
| **4** | **Out-of-Band Callback** | Multi-factor authentication confirmed at 14:11:04 UTC | `[✓ MFA VERIFIED]` |
| **5** | **Release to Processing** | Dual authorization completed -> released to clearing | `[✓ MANDATE CLEARED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approver + Tier-2 Risk Dual-Auth.

---

## 🏷️ Card [TR-06]: LIMIT_BREACH — Corporate Daily Outflow / Velocity Limit Exceeded
**BIAN Business Domain:** `CLIENT_TREASURY`  
**ISO 20022 Context:** `pain.001.001.09 - Wire exceeds corporate pre-set daily cumulative transfer limit`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[LIMIT OVERRIDE] Is the limit breach intentional due to month-end payroll or major supplier invoice?**  
  *Operator Tip: Check customer temporary limit increase request.*
* **[TREASURY SIGN-OFF] Has Corporate Treasury relationship lead approved the temporary ceiling increase?**  
  *Operator Tip: Verify credit risk approval memo.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Corporate Limit Engine): Validates temporary limit increase request on file.
* Channel 2 (Relationship Manager Portal): Fetches approved limit expansion memo.
* Channel 3 (Intraday Exposure Ledger): Recomputes cumulative daily volume ceiling.
* **Target Field Being Repaired:** `velocity_limit.override`
* **Sample Repaired Value:** `TEMPORARY_LIMIT_INCREASE_AUTHORIZED`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Cumulative Outflow Calculation** | Daily volume = $12.4M (Exceeds standard $10M ceiling by $2.4M) | `[✓ LIMIT BREACHED]` |
| **2** | **Temporary Limit Request Check** | Found active temporary limit request #TL-8812 for month-end AP | `[✓ REQUEST ON FILE]` |
| **3** | **Relationship Credit Officer Sign-off** | Senior Credit Officer (K. Watanabe) authorized ceiling to $15M | `[✓ OVERRIDE GRANTED]` |
| **4** | **Collateral & Balance Coverage** | Debtor maintains 120% compensating deposit balance | `[✓ FULLY COVERED]` |
| **5** | **Limit Ceiling Updated** | Temporary limit active until 23:59 UTC -> Wire released | `[✓ RELEASED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Risk Approver (Kenji Watanabe) Dual-Auth required.

---

## 🏷️ Card [TR-07]: LIQUIDITY_CONSTRAINT — Clearing Rail Intraday Liquidity Cap Exceeded
**BIAN Business Domain:** `CLIENT_TREASURY`  
**ISO 20022 Context:** `pacs.008.001.10 - Bank's central clearing queue exceeds central bank intraday cap`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[INTRADAY LIQUIDITY] Can this payment be queued for the next central bank settlement window (LSM)?**  
  *Operator Tip: Check Liquidity-Saving Mechanism (LSM) cycle timing.*
* **[COLLATERAL POSTING] Has Treasury posted additional central bank collateral to expand the cap?**  
  *Operator Tip: Verify central bank collateral ledger.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Central Bank Collateral Portal): Confirms repo collateral posting.
* Channel 2 (Liquidity-Saving Mechanism Optimizer): Re-sequences wire in next LSM clearing cycle.
* Channel 3 (Bilateral Offset Engine): Matches offsetting incoming wire to net exposure.
* **Target Field Being Repaired:** `clearing_cap.allocation`
* **Sample Repaired Value:** `LSM_CYCLE_OPTIMIZATION_ALLOCATED`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Central Bank Cap Monitor** | RTGS clearing cap reached 98% utilization | `[✓ CAP CRITICAL]` |
| **2** | **Treasury Collateral Posting** | Treasury posted $50M eligible securities to central bank facility | `[✓ COLLATERAL POSTED]` |
| **3** | **Cap Expansion Confirmation** | Central bank expanded intraday net debit cap by $50M | `[✓ CAP EXPANDED]` |
| **4** | **LSM Bilateral Offset** | Matched with incoming $12M credit from counterparty | `[✓ NETTED OFFSET]` |
| **5** | **Queue Release** | Wire dispatched through expanded RTGS window | `[✓ DISPATCHED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval + Treasury Lead.

---

## 🏷️ Card [TR-08]: CREDIT_EXPOSURE_BREACH — Counterparty Pre-Settlement Credit Exposure Limit Maxed
**BIAN Business Domain:** `CLIENT_TREASURY`  
**ISO 20022 Context:** `pacs.008.001.10 - Outbound wire to counterparty exceeds total daily pre-settlement credit line`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[COUNTERPARTY RISK] Is the counterparty pre-settlement credit line exhausted for today?**  
  *Operator Tip: Inspect Credit Risk Engine real-time exposure report.*
* **[NETTING / COLLATERAL] Has the counterparty posted intraday variation margin or offsetting trades?**  
  *Operator Tip: Verify margin call and netting agreement.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Enterprise Credit Risk Engine): Calculates real-time PFE (Potential Future Exposure).
* Channel 2 (Collateral Margin Ledger): Confirms receipt of intraday variation margin.
* Channel 3 (Master Netting Agreement): Applies ISDA/bilateral payment netting.
* **Target Field Being Repaired:** `credit_exposure.margin_clearance`
* **Sample Repaired Value:** `VARIATION_MARGIN_COLLATERALIZED`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Pre-Settlement Exposure Calculation** | Exposure at 102% of approved $20M counterparty ceiling | `[✓ EXPOSURE HIGH]` |
| **2** | **Variation Margin Verification** | Confirmed receipt of $4.5M cash margin in collateral ledger | `[✓ MARGIN RECEIVED]` |
| **3** | **Net Exposure Re-calculation** | Net uncollateralized exposure reduced to $16.2M (81% of cap) | `[✓ EXPOSURE SAFE]` |
| **4** | **Credit Risk Officer Approval** | Credit Risk Officer (K. Watanabe) digitally stamped authorization | `[✓ RISK APPROVED]` |
| **5** | **Release to Settlement** | Cleared for outbound clearing dispatch | `[✓ RELEASED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Risk Approver (Kenji Watanabe) Dual-Auth Required.

---


# 🏢 DOMAIN 5: SETTLEMENT & RETURNS BREAKS (7 PROFILES)

## 🏷️ Card [ST-01]: RETURNED_PAYMENT — Inbound pacs.004 Payment Return Processing
**BIAN Business Domain:** `SETTLEMENT_RETURNS`  
**ISO 20022 Context:** `pacs.004.001.10 - Inbound return message received from receiving bank with refund principal`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[RETURN RECONCILIATION] Does this pacs.004 match our original outbound pacs.008 by UETR and amount?**  
  *Operator Tip: Cross-reference original wire transaction and suspense ledger.*
* **[CLIENT RE-CREDIT] Should funds be immediately re-credited to debtor operating account?**  
  *Operator Tip: Verify return fee deduction and debtor account status.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Original pacs.008 Matcher): Matches return to original transaction via UETR.
* Channel 2 (Suspense Ledger Reversal Adapter): Clears transit suspense account.
* Channel 3 (Debtor DDA Re-Credit Engine): Posts principal re-credit to customer operating account.
* **Target Field Being Repaired:** `settlement_ledger.suspense_recredit`
* **Sample Repaired Value:** `RECREDIT_DEBTOR_DDA_AND_CLOSE`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Original pacs.008 UETR Match** | Matched return to original wire #TXN-8841 via UETR #eb481a80... | `[✓ UETR MATCH]` |
| **2** | **Return Reason Analysis** | Parsed reason code 'AC04 - Account Closed at Receiving Bank' | `[✓ REASON AC04]` |
| **3** | **Intermediary Fee Audit** | Net returned amount = $449,975.00 (Standard $25 SWIFT repair fee deducted) | `[✓ FEES AUDITED]` |
| **4** | **Suspense Account Clearing** | Debited transit suspense account #SUSP-9910 | `[✓ SUSPENSE CLEARED]` |
| **5** | **Debtor DDA Re-Credit** | Credited $449,975.00 back to debtor account #9876543210 | `[✓ RE-CREDITED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval.

---

## 🏷️ Card [ST-02]: ACCOUNT_CLOSED — Beneficiary Account Closed (AC04 Hard Rejection)
**BIAN Business Domain:** `SETTLEMENT_RETURNS`  
**ISO 20022 Context:** `pacs.002 / pacs.004 with reason code <Rsn><Cd>AC04</Cd>`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[BENEFICIARY ACCOUNT STATUS] Is there a successor / migrated account number on file for this corporate client?**  
  *Operator Tip: Check corporate counterparty migration database.*
* **[RETURN VS REROUTE] Does client standing instruction mandate immediate return or auto-reroute?**  
  *Operator Tip: Inspect customer standing instruction rule.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Bank Account Migration Directory): Identifies successor account if branch migrated.
* Channel 2 (Customer Return Workflow): Generates pacs.004 return if account is permanently closed.
* Channel 3 (Customer Notification Gateway): Dispatches automated advisory to corporate treasurer.
* **Target Field Being Repaired:** `account_closed.disposition`
* **Sample Repaired Value:** `DISPATCH_PACS004_RETURN_TO_ORIGINATOR`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **AC04 Rejection Verification** | Receiving bank confirmed account closed on 2026-06-30 | `[✓ ACCOUNT CLOSED]` |
| **2** | **Successor Account Scan** | Zero successor account registered for this legal entity | `[✓ NO SUCCESSOR]` |
| **3** | **Standing Mandate Check** | Client mandate mandates: 'Immediate Return on Closed Account' | `[✓ RETURN MANDATE]` |
| **4** | **pacs.004 Return Generation** | Generated ISO 20022 pacs.004 refund payload with original UETR | `[✓ PACS.004 READY]` |
| **5** | **Debtor Notification Dispatch** | Dispatched automated email/API alert to Debtor AP team | `[✓ CLIENT NOTIFIED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval.

---

## 🏷️ Card [ST-03]: BENEFICIARY_ACCOUNT_FROZEN — Beneficiary Account Frozen / Court Restraint (AC06)
**BIAN Business Domain:** `SETTLEMENT_RETURNS`  
**ISO 20022 Context:** `pacs.002 / pacs.004 with reason code <Rsn><Cd>AC06</Cd> - Blocked by legal order`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[LEGAL HOLD] Is the account subject to a legal freeze, court restraint, or insolvency block?**  
  *Operator Tip: Inspect receiving bank legal notice tag.*
* **[FUNDS RETENTION] Are funds trapped at intermediary under court order or eligible for return?**  
  *Operator Tip: Verify legal jurisdiction retention guidelines.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Receiving Bank Legal Advisory): Parses court restraint / freeze memorandum.
* Channel 2 (Insolvency Protection Workflow): Blocks further outbound payment attempts.
* Channel 3 (Debtor Legal Notification): Generates formal legal freeze notification.
* **Target Field Being Repaired:** `frozen_account.disposition`
* **Sample Repaired Value:** `HOLD_IN_SUSPENSE_AWAITING_LEGAL_CLEARANCE`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **AC06 Legal Restraint Code** | Receiving bank tagged account 'AC06 - Blocked under Judicial Restraint' | `[✓ JUDICIAL FREEZE]` |
| **2** | **Insolvency Register Cross-Check** | Confirmed debtor entered statutory administration on 2026-08-12 | `[✓ ADMINISTRATION]` |
| **3** | **Automated Re-Attempt Block** | Placed permanent system block on creditor account to prevent loops | `[✓ CORRIDOR BLOCKED]` |
| **4** | **Suspense Ledger Segregation** | Segregated funds into legally protected escrow suspense ledger | `[✓ ESCROW HELD]` |
| **5** | **Legal Department Alert** | Dispatched high-priority case packet to Bank Legal Counsel | `[✓ LEGAL ALERT]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Compliance & Legal Officer Sign-Off.

---

## 🏷️ Card [ST-04]: RECONCILIATION_BREAK — Intraday General Ledger / Nostro Reconciliation Break
**BIAN Business Domain:** `SETTLEMENT_RETURNS`  
**ISO 20022 Context:** `camt.053 (Bank Statement) vs internal payment ledger amount discrepancy`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[LEDGER DISCREPANCY] Does the break stem from correspondent fee deductions or an FX rounding mismatch?**  
  *Operator Tip: Inspect camt.053 line items vs original wire principal.*
* **[ADJUSTMENT POSTING] Can the fee break be posted to the automated correspondent repair ledger?**  
  *Operator Tip: Verify correspondent fee tolerance schedule.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (camt.053 Statement Reconciler): Parses raw bank statement entry.
* Channel 2 (Correspondent Fee Tolerance Engine): Identifies standard $25 repair fee.
* Channel 3 (Automated Journal Voucher): Posts balanced ledger adjusting entry.
* **Target Field Being Repaired:** `ledger_reconciliation.adjustment`
* **Sample Repaired Value:** `AUTO_JOURNAL_ADJUSTMENT_POSTED ($25 Fee)`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **camt.053 Statement Comparison** | Matched statement entry #STMT-991 to wire #TXN-8841 | `[✓ MATCHED]` |
| **2** | **Discrepancy Identification** | Identified exact $25.00 variance = Intermediary processing fee | `[✓ VARIANCE $25]` |
| **3** | **Fee Tolerance Schedule Check** | $25 fee complies with Correspondent Schedule of Charges §3 | `[✓ TOLERANCE OK]` |
| **4** | **GL Journal Entry Generation** | Generated journal entry: Debit Fee Expense $25 / Credit Nostro $25 | `[✓ JOURNAL POSTED]` |
| **5** | **Ledger Balance Reconciled** | GL and Nostro statement reconciled with zero net variance | `[✓ 100% BALANCED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval.

---

## 🏷️ Card [ST-05]: SETTLEMENT_FAILURE — Central Bank Settlement Finality Failure (TARGET2 / Fedwire)
**BIAN Business Domain:** `SETTLEMENT_RETURNS`  
**ISO 20022 Context:** `pacs.002 received with status RJCT at final central bank clearing settlement cut`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[FINALITY BREAK] Did the central bank reject the wire due to gridlock or participant suspension?**  
  *Operator Tip: Examine central bank settlement report.*
* **[CONTINGENCY DISPATCH] Should the payment be resubmitted via alternative RTGS window?**  
  *Operator Tip: Check participant RTGS operational status.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Central Bank Settlement Monitor): Parses finality failure code.
* Channel 2 (Contingency Settlement Adapter): Prepares wire for secondary clearing window.
* Channel 3 (Liquidity Release Worker): Unwinds unsettled DDA earmark.
* **Target Field Being Repaired:** `settlement_finality.action`
* **Sample Repaired Value:** `CONTINGENCY_CLEARING_WINDOW_DISPATCH`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Central Bank Settlement Report** | TARGET2 reported participant transient gridlock at 17:45 CET | `[✓ GRIDLOCK]` |
| **2** | **Participant Status Check** | Receiving bank confirmed operational and participating in next window | `[✓ ACTIVE]` |
| **3** | **Earmarked Liquidity Validation** | Settlement liquidity remains reserved in central pool | `[✓ RESERVED]` |
| **4** | **Contingency Window Selection** | Selected TARGET2 Contingency Window 2 for priority release | `[✓ WINDOW SELECTED]` |
| **5** | **Outbound Re-Dispatch** | Dispatched message with priority flag -> Settled with finality | `[✓ FINALITY SETTLED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Operations Lead (Daniel Osei) Approval.

---

## 🏷️ Card [ST-06]: FUNDS_TRAPPED_AT_CORRESPONDENT — Funds Trapped at Intermediary Correspondent (Nostro Transit Break)
**BIAN Business Domain:** `SETTLEMENT_RETURNS`  
**ISO 20022 Context:** `camt.054 received with debit confirmation, but beneficiary bank received zero credit`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[TRACKER STATUS] Where in the correspondent banking chain are the funds currently located?**  
  *Operator Tip: Inspect SWIFT gpi tracker hop timestamps and intermediary node.*
* **[SWIFT INVESTIGATION] Should a formal MT199/camt.056 inquiry message be dispatched to the intermediary?**  
  *Operator Tip: Verify correspondent query SLA.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (SWIFT gpi Tracker API): Pinpoints exact intermediary holding the wire.
* Channel 2 (camt.056 Query Dispatcher): Auto-generates structured tracking message.
* Channel 3 (Correspondent Escalation Desk): Elevates case to correspondent desk lead.
* **Target Field Being Repaired:** `transit_investigation.status`
* **Sample Repaired Value:** `DISPATCH_CAMT056_INTERMEDIARY_INQUIRY`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **SWIFT gpi Hop Pinpoint** | gpi Tracker confirms funds held at intermediary BIC DEUTDEDD (Hop #2) | `[✓ HOP 2 HELD]` |
| **2** | **Hold Duration Calculation** | Funds held at intermediary for > 180 minutes without onward routing | `[✓ HOLD 180m]` |
| **3** | **camt.056 Inquiry Generation** | Generated ISO 20022 camt.056 status inquiry with UETR reference | `[✓ CAMT.056 READY]` |
| **4** | **Correspondent SLA Alert** | Triggered Level-1 correspondent desk priority SLA alert | `[✓ SLA PINGED]` |
| **5** | **Client Telemetry Update** | Updated customer portal tracker: 'Investigating with Intermediary' | `[✓ CLIENT UPDATED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval.

---

## 🏷️ Card [ST-07]: UNMATCHED_CREDIT — Unmatched Inbound Credit in Nostro Statement
**BIAN Business Domain:** `SETTLEMENT_RETURNS`  
**ISO 20022 Context:** `camt.054 / MT910 credit received in Nostro account with zero matching internal payment`

### 🎯 1. Human Triage Checklist (The 2 Operator Questions):
* **[UNCLAIMED CREDIT] Does this inbound credit match an expected client trade or customer deposit?**  
  *Operator Tip: Search corporate trade expected receipts database by amount and remitter.*
* **[SUSPENSE RETENTION] Should funds be parked in unallocated suspense or returned to ordering institution?**  
  *Operator Tip: Verify 48-hour unclaimed funds return policy.*

### 🔍 2. Value Derivation & Grounding Channels (Where the Data Comes From):
* Channel 1 (Expected Receipts Matcher): Scans debtor scheduled receivables.
* Channel 2 (Remitter Name Search): Matches remitter corporate name to client DDA.
* Channel 3 (Unallocated Suspense Posting): Parks funds in governed ledger awaiting claim.
* **Target Field Being Repaired:** `unmatched_credit.disposition`
* **Sample Repaired Value:** `ALLOCATE_TO_DEBTOR_RECEIVABLES_LEDGER`

### 🔬 3. Step-by-Step Investigation Assessment (The 5 Automated Tests):
| Step # | Investigation Test Name | Exact Proof & Verification Detail | Badge / Status |
| :---: | :--- | :--- | :--- |
| **1** | **Inbound Credit Statement Parse** | Parsed $125,000.00 credit in EUR Nostro account from remitter 'BASF SE' | `[✓ CREDIT PARSED]` |
| **2** | **Expected Receivables Match** | Matched expected receivable invoice #REC-4412 for client 'Acme Corp' | `[✓ RECEIVABLE MATCH]` |
| **3** | **Remitter Identity Verification** | Remitter 'BASF SE' confirmed authorized vendor on client account | `[✓ VENDOR MATCH]` |
| **4** | **DDA Credit Posting** | Credited $125,000.00 to Acme Corp operating account #9876543210 | `[✓ DDA CREDITED]` |
| **5** | **Reconciliation Close** | Nostro statement line and client ledger reconciled with zero variance | `[✓ CLOSED]` |

### ⚖️ 4. Governance & Dual-Auth Threshold:
**Routing Rule:** Tier-1 Ops Approval.

---

