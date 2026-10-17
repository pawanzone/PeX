# 04-exception-taxonomy.md — Exception Taxonomy (The 41 Profiles)

**Document Status:** COMPLETE / EVIDENCE-AUDITED  
**Auditor Mode:** Objective External Review  
**Target Codebase:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Date of Audit:** October 2026  

---

## 1. The 41 Exception Profiles Across 5 Domains

The PeX platform defines 41 distinct exception profiles grouped into 5 operational domains in `backend/app/schemas/canonical.py` (lines 29-83). The table below details every profile's detection, evidence acquisition, resolution, validation, policy rule, implementation status, and test coverage:

| Profile Code & Name | Domain | Detection Logic | Evidence Acquisition Source | Proposed Resolution Logic | Validation Gates Applied | Applied Policy Rule | Status | Test Coverage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DQ-01: INVALID_IBAN** | Data Quality | ISO 13616 / MOD-97 check failure (`canonicalizer.py:54`) | Beneficiary Master Directory & SSI (`icd_staging_store.json`) | Transposition correction or SSI replacement | ISO 7064 MOD-97-10 check digit math | `RULE-DQ-001` (MOD-97 remainder = 1) | `IMPLEMENTED` | `tests/wave1/`, `e2e_fixtures/output/` |
| **DQ-02: INVALID_BIC** | Data Quality | Length != 8/11 or inactive BIC in directory | SWIFT Reference Master Directory | Map branch BIC to active Head Office BIC | ISO 9362 8/11 syntax & CBPR+ registry | `RULE-DQ-002` (Active SWIFT BIC) | `IMPLEMENTED` | `tests/wave1/test_wave1_profiles.py` |
| **DQ-03: MISSING_BENEFICIARY_DATA** | Data Quality | Empty creditor name or address lines | Core Banking SSI & Client Master | Enrich legal name & registered address from SSI | Length > 0, alphanumeric syntax | `RULE-DQ-003` (Mandatory party info) | `IMPLEMENTED` | `tests/wave1/` |
| **DQ-04: MISSING_REMITTANCE_INFO** | Data Quality | Missing remittance narrative / invoice ref | Historical transaction matching | Populate structured invoice ref from prior wire | ISO 20022 RmtInf structure check | `RULE-DQ-004` (Remittance match) | `IMPLEMENTED` | `tests/wave1/` |
| **DQ-05: INVALID_ADDRESS_FORMAT** | Data Quality | Unstructured address exceeding line limit | National Postal Directory | Parse and format into structured street/city/postal | ISO 20022 PstlAdr structural schema | `RULE-DQ-005` (Postal format) | `IMPLEMENTED` | `tests/wave1/` |
| **DQ-06: MISSING_PURPOSE_CODE** | Data Quality | Mandatory regulatory code missing | Corroborating trade document | Inject valid purpose code (e.g. `GDSV`, `SALA`) | ISO ExternalPurpose1Code set | `RULE-DQ-006` (Purpose code valid) | `IMPLEMENTED` | `tests/wave1/` |
| **DQ-07: INVALID_ACCOUNT_NUMBER** | Data Quality | BBAN length / check failure | Receiving Bank Clearing Specs | Reformat leading zeros / domestic clearing mask | Receiving clearing scheme rules | `RULE-DQ-007` (BBAN length) | `IMPLEMENTED` | `tests/wave1/` |
| **DQ-08: INVALID_ROUTING_CODE** | Data Quality | ABA / Sort Code unresolvable | Fedwire ABA / UK Sort Directory | Map historical clearing identifier to active routing | Fedwire FAIM 9-digit routing check | `RULE-DQ-008` (ABA checksum) | `IMPLEMENTED` | `tests/wave1/` |
| **DQ-09: BENEFICIARY_NAME_MISMATCH** | Data Quality | Confirmation of Payee (CoP) mismatch | Receiving Bank Account Directory | Update name with verified account holder legal title | Confirmation of Payee threshold >= 85% | `RULE-DQ-009` (CoP clearance) | `PARTIAL` | `tests/wave1/` |
| **PR-01: DUPLICATE_PAYMENT** | Processing | Identical amount, creditor, date window | Inbound duplicate hash index | Suppress duplicate; request cancellation or trace | Unique UETR & EndToEndId uniqueness | `RULE-PR-001` (Duplicate block) | `IMPLEMENTED` | `tests/wave2/test_wave2_profiles.py` |
| **PR-02: ROUTING_FAILURE** | Processing | Intermediary clearing node unreachable | Clearing Rail Transit Directory | Calculate alternative correspondent routing hop | Rail availability calendar check | `RULE-PR-002` (Corridor open) | `IMPLEMENTED` | `tests/wave2/` |
| **PR-03: ISO20022_VALIDATION_ERROR**| Processing | XSD syntax validation error | pacs.008 schema repository | Strip illegal characters; correct XML hierarchy | W3C XML Schema Definition validation | `RULE-PR-003` (XSD schema pass) | `PARTIAL` (Seeded JSON input; no XML parser) | `tests/wave2/` |
| **PR-04: CUTOFF_MISSED** | Processing | Timestamp exceeds clearing cutoff window | RTGS Clearing Calendar | Roll value date to next business day or reroute | Clearing cutoff timetable | `RULE-PR-004` (Cutoff evaluation) | `IMPLEMENTED` | `tests/wave2/` |
| **PR-05: CORRUPTED_MESSAGE_FORMAT** | Processing | Incomplete message framing / header loss | Raw socket capture | Reserialize canonical fields into clean ISO envelope | Canonical header completeness | `RULE-PR-005` (Header integrity) | `PARTIAL` | `tests/wave2/` |
| **PR-06: INTERMEDIARY_BANK_REJECTION**| Processing | pacs.002 negative status receipt | Intermediary return message | Reroute via direct clearing correspondent | Correspondent bilateral limit | `RULE-PR-006` (Intermediary route) | `PARTIAL` | `tests/wave2/` (1 test failure) |
| **PR-07: NETWORK_TIMEOUT** | Processing | Acknowledgment timeout | Network transit status log | Issue status inquiry (camt.027) or retry dispatch | Idempotency sequence check | `RULE-PR-007` (Timeout retry) | `PARTIAL` | `tests/wave2/` |
| **PR-08: QUEUE_PROCESSING_FAILURE** | Processing | Processing hub internal error | Dead Letter Queue (DLQ) state | Re-queue instruction with clean sequence ID | Hub sequence integrity | `RULE-PR-008` (DLQ recovery) | `IMPLEMENTED` | `tests/wave2/` |
| **PR-09: PAYMENT_HELD_FOR_REPAIR** | Processing | Payment hub manual intervention flag | Repair queue queue metadata | Route to specialized operator desk | Operator desk assignment rules | `RULE-PR-009` (Desk routing) | `IMPLEMENTED` | `tests/wave2/` |
| **CO-01: SANCTIONS_SUSPECTED** | Compliance | Watchlist filter hit (OFAC SDN) | OFAC SDN Watchlist (`icd_staging_store`) | Confirm homonym false-positive or block/escalate | Entity disambiguation match score | `RULE-CO-001` (Sanctions clearance) | `IMPLEMENTED` | `tests/wave3/test_wave3_profiles.py` |
| **CO-02: AML_ALERT** | Compliance | Structuring / velocity rule triggered | Transaction monitoring history | Review transaction purpose and historical patterns | AML risk threshold (< 0.70) | `RULE-CO-002` (AML clearance) | `PARTIAL` | `tests/wave3/` |
| **CO-03: PEP_MATCH** | Compliance | Politically Exposed Person indicator | PEP Registry & adverse media | Enhanced Due Diligence (EDD) verification | PEP clearance sign-off | `RULE-CO-003` (PEP sign-off) | `PARTIAL` | `tests/wave3/` |
| **CO-04: RESTRICTED_CORRIDOR** | Compliance | Origin/destination corridor embargo | Regulatory Corridor Policy Table | Reroute via permitted hub or reject payment | Sanctioned jurisdiction whitelist | `RULE-CO-004` (Corridor clearance) | `IMPLEMENTED` | `tests/wave3/` |
| **CO-05: ADVERSE_MEDIA_MATCH** | Compliance | Negative news intelligence match | Public news index | Verify identity disambiguation vs adverse entity | Compliance officer review | `RULE-CO-005` (Adverse media check) | `PARTIAL` | `tests/wave3/` |
| **CO-06: HIGH_RISK_JURISDICTION** | Compliance | FATF grey/black list corridor hit | FATF Jurisdictions Registry | Apply enhanced compliance fee and source check | FATF Rec 16 compliance rules | `RULE-CO-006` (FATF compliance) | `PARTIAL` | `tests/wave3/` |
| **CO-07: REGULATORY_REPORTING_REQ** | Compliance | Exceeds statutory reporting threshold | National Regulatory Registry | Generate regulatory reporting disclosure payload | Statutory disclosure completeness | `RULE-CO-007` (Regulatory filing) | `PARTIAL` | `tests/wave3/` (1 test failure) |
| **CO-08: CUSTOMER_WATCHLIST_MATCH** | Compliance | Internal bank black-list hit | Core Bank Internal Watchlist | Review internal dispute / fraud indicator | Fraud ops clearance | `RULE-CO-008` (Internal list clear) | `PARTIAL` | `tests/wave3/` |
| **TR-01: KYC_EXPIRED** | Client / Treasury | Counterparty KYC review date lapsed | Client KYC Master Directory | Request emergency waiver or refresh document | KYC validity date >= CurrentDate | `RULE-TR-001` (KYC waiver/refresh) | `IMPLEMENTED` | `tests/wave3/` |
| **TR-02: INSUFFICIENT_FUNDS** | Client / Treasury | Debtor account balance < amount | Core DDA Account Balance | Intra-day credit line draw or credit freeze | Debtor available balance check | `RULE-TR-002` (Balance sufficiency) | `PARTIAL` | `tests/wave3/` (1 test failure) |
| **TR-03: NOSTRO_SHORTFALL** | Client / Treasury | Target currency nostro account deficit | Nostro Position Registry | Initiate FX swap or nostro rebalancing transfer | Nostro settlement buffer check | `RULE-TR-003` (Nostro liquidity) | `PARTIAL` | `tests/wave3/` (1 test failure) |
| **TR-04: FX_RATE_UNAVAILABLE** | Client / Treasury | FX pricing feed timeout / volatility | Treasury FX Pricing Desk | Lock fallback rate or request manual rate quote | Spot rate band tolerance check | `RULE-TR-004` (FX band tolerance) | `PARTIAL` | `tests/wave3/` (1 test failure) |
| **TR-05: AUTHORIZATION_MISSING** | Client / Treasury | Corporate mandate dual-sign missing | Corporate Mandate Registry | Request second corporate signatory approval | Corporate mandate threshold rule | `RULE-TR-005` (Mandate signature) | `IMPLEMENTED` | `tests/wave3/` |
| **TR-06: LIMIT_BREACH** | Client / Treasury | Client daily transaction limit exceeded | Limit Management System | Request credit officer temporary limit increase | Client credit limit rule | `RULE-TR-006` (Credit limit check) | `PARTIAL` | `tests/wave3/` (1 test failure) |
| **TR-07: LIQUIDITY_CONSTRAINT** | Client / Treasury | Central bank reserve constraint | Intraday Liquidity Monitor | Queue for next RTGS liquidity optimization cycle | Central bank buffer requirement | `RULE-TR-007` (Reserve threshold) | `PARTIAL` | `tests/wave3/` (1 test failure) |
| **TR-08: CREDIT_EXPOSURE_BREACH** | Client / Treasury | Counterparty credit risk exposure capped | Risk Engine / Credit Master | Require Risk Approver waiver ($10M limit) | Enterprise risk exposure rule | `RULE-TR-008` (Risk waiver) | `PARTIAL` | `tests/wave3/` (1 test failure) |
| **ST-01: RETURNED_PAYMENT** | Settlement / Returns| Inbound pacs.004 return receipt | Inbound return message payload | Credit debtor account; post reversal charges | Original transaction UETR match | `RULE-ST-001` (Return reconciliation) | `PARTIAL` (Seeded JSON return payload; no pacs.004 XML parser) | `tests/wave2/` |
| **ST-02: ACCOUNT_CLOSED** | Settlement / Returns| Beneficiary bank AC04 return code | Successor Account Directory | Reroute to active successor account | Successor account MOD-97 check | `RULE-ST-002` (Successor routing) | `PARTIAL` | `tests/wave2/` (1 test failure) |
| **ST-03: BENEFICIARY_ACCOUNT_FROZEN**| Settlement / Returns| AC06 return code / legal freeze | Legal Registry & Court Order Store | Place funds in general ledger suspense account | Suspense ledger account validity | `RULE-ST-003` (Suspense booking) | `PARTIAL` | `tests/wave2/` (1 test failure) |
| **ST-04: RECONCILIATION_BREAK** | Settlement / Returns| General ledger / bank statement break | Statement reconciliation feed | Match unmatched debit/credit ledger entries | Ledger break amount tolerance = 0 | `RULE-ST-004` (Ledger match) | `PARTIAL` | `tests/wave2/` |
| **ST-05: SETTLEMENT_FAILURE** | Settlement / Returns| Clearing settlement reject | RTGS Settlement Gateway | Resubmit in subsequent clearing cycle | Settlement window open check | `RULE-ST-005` (Settlement resubmit) | `PARTIAL` | `tests/wave2/` |
| **ST-06: FUNDS_TRAPPED_CORRESPONDENT**| Settlement / Returns| pacs.002 PDNG without settlement | SWIFT gpi transit tracker | Dispatch camt.056 recall or MT199 status query | UETR tracker status check | `RULE-ST-006` (Recall dispatch) | `IMPLEMENTED` | `tests/wave2/` |
| **ST-07: UNMATCHED_CREDIT** | Settlement / Returns| Inbound credit without matching order | Inbound pacs.008 message | Match against open accounts receivable invoice | Customer invoice balance match | `RULE-ST-007` (Invoice matching) | `PARTIAL` | `tests/wave2/` |

---

## 2. End-to-End Implementation Depth vs. Seed / Label Status

Forensic inspection confirms varying degrees of implementation depth across the 41 profiles:

### Profiles with Full End-to-End Automated Path (`IMPLEMENTED`)
- **DQ-01 (`INVALID_IBAN`)**: Full path through `file_watcher.py`, `e2e_runner.py`, mathematical MOD-97 checks, SSI matching, STP fast-lane evaluation, output reconciliation JSON serialization, and persistent SQLite database recording.
- **DQ-02 (`INVALID_BIC`)**, **DQ-03 (`MISSING_BENEFICIARY_DATA`)**, **DQ-06 (`MISSING_PURPOSE_CODE`)**, **DQ-08 (`INVALID_ROUTING_CODE`)**, **PR-01 (`DUPLICATE_PAYMENT`)**, **CO-01 (`SANCTIONS_SUSPECTED`)**, **TR-01 (`KYC_EXPIRED`)**, **TR-05 (`AUTHORIZATION_MISSING`)**, **ST-01 (`RETURNED_PAYMENT`)**: Full simulation paths tested in Wave 1, 2, and 3 suites with synthetic responses.

### Profiles That Function Primarily as Seed Labels (`PARTIAL`)
- **PR-05, PR-06, PR-07, CO-02, CO-03, CO-05, CO-06, CO-07, TR-02, TR-03, TR-04, TR-06, TR-07, TR-08, ST-02, ST-03, ST-04, ST-05, ST-07**:
  - These profiles exist as valid `ExceptionProfile` enum constants.
  - In `backend/app/services/data_loader.py`, they return canned recommendations generated by `build_rich_guided_recommendation`.
  - While they are fully queryable via REST APIs and render properly in the React cockpit, their underlying resolution logic does not execute real clearing protocols or banking engine integrations.

---

## 3. BIAN Naming Analysis: Standard Alignment vs. Taxonomy Label

The documentation asserts that PeX is modeled on the **Banking Industry Architecture Network (BIAN)** standard. Forensic audit reveals:
1. **No BIAN BOM / Schema Dependencies**: The repository does not import BIAN service domain definitions, BIAN Business Object Model (BOM) schemas, or BIAN OpenAPI definitions.
2. **Taxonomy Labeling**: The 5 domains (Data Quality, Processing, Compliance, Client Treasury, Settlement Returns) and 41 profiles are an **internal categorization taxonomy** devised by the PeX engineering team. They are referred to in docstrings as "BIAN Market Domains", but they represent operational categories rather than formal BIAN Service Domains (e.g., `Payment Execution`, `Correspondent Bank Operations`, `Financial Crime Screening`).
3. **Conclusion**: BIAN naming is an architectural alignment concept and marketing label; it is **not** a formal implementation of BIAN interface specifications.

---

## 4. Nature of the Platform: Data Repair Tool vs. Investigation Tool

The 41 profiles divide into three distinct operational categories:

| Operational Category | Profile Codes Included | Operational Nature | Code Implementation Reality |
| :--- | :--- | :--- | :--- |
| **Field-Level Data Repair** | DQ-01 to DQ-09, PR-03, PR-04, ST-02 | Syntactic / structural data modification (modifying IBAN, BIC, purpose code, account number). | **REAL IMPLEMENTATION**: The platform excels here. Field diffs (`original_value` vs `proposed_value`) are generated, validated, approved, and handed off. |
| **Exception Investigation** | PR-01, PR-06, PR-07, ST-01, ST-04, ST-06, ST-07 | Tracing payment transit, reconciling ledger breaks, handling recall messages (camt.056/camt.029). | **MOCKED / SIMULATED**: The UI displays an "Investigations Hub" tab with 167 items; however, code shows these are simply audit log events, not distinct investigation workflows. No MT199/camt.027 message generators exist. |
| **Authoritative Decision** | CO-01 to CO-08, TR-01 to TR-08, ST-03 | Compliance holds, PEP reviews, liquidity overrides, credit limit waivers. | **WORKFLOW ROUTING ONLY**: The platform routes these cases to specialized desks (Compliance, Risk) and enforces role limits. It does not perform live sanctions disambiguation or ledger balance reserving. |

### Candid Auditor Verdict
**PeX is currently an automated and governed Data Repair Tool with role-gated approval workflows.** It is **not yet a true Payment Investigation Tool** in the sense of SWIFT Case Management or Pega Smart Investigate, because it cannot generate outbound inquiry messages, ingest multi-party case correspondence, or manage bilateral claim indemnities.
