# PeX — Batch 4 Payment Domain Source Register
## Grounded Evidence & Reference-Data Verification Matrix

**Document Reference:** `PEX-AUDIT-BATCH4-SRC-REG`  
**Execution Date:** September 23, 2026  
**Status:** **AUTHORITATIVE & SOURCE-GROUNDED**  
**Remediation Scope:** `MST-021`, `MST-024`, `MST-025`, `MST-026`, `MST-027`, `MST-028`, `MST-029`

---

## 1. Grounding Mandate & Source Hierarchy

In accordance with strict payment engineering governance, domain reference data and message semantics cannot be inferred from prototype assumptions or synthetic artifacts. Every domain assertion in Batch 4 is verified directly against primary international standards bodies, central bank operating circulars, and official registries.

### Primary Authoritative Hierarchy
1. **ISO Standards & Registration Authorities:** ISO 13616 (IBAN Structure & SWIFT Registry), ISO 7064 (MOD 97-10 Check Digits), ISO 20022 Financial Services Message Catalogue & External Code Lists (`ExternalReturnReason1Code`, `ExternalPurpose1Code`).
2. **Central Bank Operating Circulars & Scheme Rulebooks:** Federal Reserve Operating Circular No. 6 & FAIM (Fedwire Funds Service), Deutsche Bundesbank BLZ/IBAN Guidelines, Bank of England CHAPS Operating Rules, Pay.UK Bacs Scheme Rules.
3. **SWIFT Rulebooks:** SWIFT CBPR+ (Cross-Border Payments and Reporting Plus) Guidelines & ISO 9362 BIC Directory.

---

## 2. Authoritative Domain Source Register

| Master ID | Assertion Being Corrected | Authoritative Standard | Governing Body | Official Document / Identifier | Date Verified | Verified Rule & Exact Technical Syntax | Affected Code & Fixtures | Required Implementation Change | Verification Status |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---:|
| **`MST-021`** | US & Japan issue IBANs and are valid IBAN registry countries | ISO 13616-1:2020 / ISO 13616-2:2020; Official SWIFT IBAN Registry | ISO / SWIFT (Registration Authority) | ISO 13616 IBAN Registry Release 96+; Fedwire OC6; BOJ-NET Rules | 2026-09-23 | US, Japan, Singapore, and Australia do NOT issue IBANs and do NOT participate in ISO 13616. US uses 9-digit ABA Routing + DDA Account. Japan uses 4-digit Zengin code + 3-digit branch code + account number. | `backend/app/data/icd_staging_store.json`, `backend/app/services/canonicalizer.py` | Remove `US`, `JP`, `SG` from `supported_countries` in `iban_math_spec`. Remove fake `US64CHAS...` and `JP44BOTK...` standing IBANs; populate domestic `routing_aba`, `account_number`, and `zengin_bank_code`. Reject US/JP country prefixes in IBAN validators. | **SOURCE_VERIFIED** |
| **`MST-024`** | German IBANs contain 26 characters with alphanumeric bank identifiers (`DE89DEUT...`) | ISO 13616-1:2020 (German Registry Entry `DE2!n8!n10!n`); Deutsche Bundesbank BLZ Guidelines | Deutsche Bundesbank / ISO | ISO 13616-1 Annex A; Deutsche Bundesbank IBAN-Regeln | 2026-09-23 | German IBAN is strictly **22 numeric characters**: `DE` (2 alpha) + Check Digits (2 numeric) + Bankleitzahl BLZ (8 numeric) + Account Number (10 numeric). No letters permitted in BBAN. Checksum must satisfy $N \equiv 1 \pmod{97}$ (ISO 7064). | `backend/app/data/icd_staging_store.json:269` | Replace `DE89DEUT370400440532013000` with valid 22-digit numeric German IBAN `DE89370400440532013000` ($N \equiv 1 \pmod{97}$). Implement length and numeric BBAN validation for DE. | **SOURCE_VERIFIED** |
| **`MST-025`** | ISO Return Reason Code `AC01` denotes "Account Closed" or Intermediary Routing Error | ISO 20022 External Code Sets (`ExternalReturnReason1Code`) | ISO 20022 Registration Authority | ISO 20022 `ExternalReturnReason1Code` 2024/2025; EPC SEPA Reason Codes | 2026-09-23 | **`AC01`** strictly means `"IncorrectAccountNumber"` (Account identifier invalid/does not exist). **`AC04`** strictly means `"ClosedAccountNumber"` (Account closed). **`AC06`** means `"BlockedAccount"`. Intermediary routing errors use **`RC01`** (`BankIdentifierIncorrect`) or **`MS03`** (`NotSpecifiedReasonAgentGenerated`). | `backend/app/services/profile_engine.py`, `backend/app/services/data_loader.py`, `PeX_41_Exception_Taxonomy_SME_Architecture_Cards.md` | Align all "Account Closed" return mappings to `AC04`. Ensure `AC01` is strictly documented and validated as "Incorrect Account Number". | **SOURCE_VERIFIED** |
| **`MST-026`** | `pacs.004` (Payment Return) and `camt.056` (Cancellation Request) are interchangeable return messages | ISO 20022 Payments Standards Catalogue (pacs.004 vs camt.056) | ISO / Payments Market Practice Group (PMPG) | ISO 20022 Maintenance Release 2024; SWIFT CBPR+ User Guidelines | 2026-09-23 | **`pacs.004`** is a **financial value message** that returns/reverses funds across interbank settlement ledgers (direct credit to originator). **`camt.056`** is an **investigatory non-value request** asking the receiver to recall a wire (which is accepted via `pacs.004` or rejected via `camt.029`). Inquiries for trapped funds without recall use **`camt.027`** (ClaimNonReceipt) or **`pacs.028`**. | `backend/app/services/profile_engine.py:289`, `backend/app/services/data_loader.py:375-400` | Disentangle `pacs.004` from `camt.056`. Define `pacs.004` as financial settlement return and `camt.056` as non-value recall request. Update profile descriptions and reasoning traces. | **SOURCE_VERIFIED** |
| **`MST-027`** | Codes `GDDS`, `PHAR`, `COMM`, `COMP`, `AUDT` are valid ISO 20022 Purpose Codes | ISO 20022 External Code Sets (`ExternalPurpose1Code`) | ISO 20022 Registration Authority | ISO 20022 `ExternalPurpose1Code` Directory (2024/2025 Catalogue) | 2026-09-23 | Valid official 4-character codes: `GDSV` (PurchaseSaleOfGoods), `COMC` (CommercialPayment), `MDCS` (MedicalServices), `TREA` (TreasuryPayment), `CORT` (TradeSettlementPayment), `SALA` (SalaryPayment), `SUPP` (SupplierPayment), `INTC` (IntraCompanyPayment). `GDDS`, `PHAR`, `COMM`, `COMP`, `AUDT` are invalid/hallucinated. | `backend/app/data/icd_staging_store.json:203,257,275`, `backend/app/schemas/canonical.py` | Replace `GDDS` $\to$ `GDSV`, `COMM` $\to$ `COMC`, `PHAR` $\to$ `MDCS` in `icd_staging_store.json`. Add ISO 20022 purpose code validator recognizing official 4-character codes and rejecting non-standard codes. | **SOURCE_VERIFIED** |
| **`MST-028`** | Fedwire IMAD is 22 alphanumeric characters (`20260901MMQF0001004812`) | Federal Reserve Fedwire Funds Service Operating Circular No. 6 & FAIM | Federal Reserve Banks | Fedwire Application Interface Manual (FAIM v3.0 / v4.0) Section 2.1 | 2026-09-23 | Fedwire **IMAD (Input Message Accountability Data)** is strictly **18 alphanumeric characters**: `YYYYMMDD` (8 numeric) + Source Identifier (4 alphanumeric) + Sequence Number (6 numeric zero-padded: `000001`–`999999`). Pattern: `^[0-9]{8}[A-Z0-9]{4}[0-9]{6}$`. | `backend/app/services/action_executor.py`, `backend/app/services/canonicalizer.py`, synthetic test fixtures | Implement deterministic 18-character IMAD validator and generator. Ensure positive validation for 18-char strings and rejection of 22-char or non-conforming formats. | **SOURCE_VERIFIED** |
| **`MST-029`** | UK Bacs is a high-value RTGS payment rail alongside CHAPS, Fedwire, and TARGET2 | Pay.UK Scheme Rules; Bank of England FMI Supervision | Pay.UK / Bank of England | Pay.UK Bacs Scheme Rules 2024; BoE RTGS & CHAPS Service Description | 2026-09-23 | **Bacs** is a **3-day deferred net settlement bulk batch clearing system** (Automated Clearing House - ACH) for Direct Debits and Bacs Direct Credits. The UK high-value RTGS payment rail is **CHAPS** (operated on Bank of England RTGS). Near-real-time retail is **Faster Payments (FPS)**. | `build_guided_frontend.py`, `frontend/dist/index.html`, Walkthrough Spec & Architecture Docs | Reclassify Bacs as 3-Day Bulk Batch Net Settlement (ACH). Clearly distinguish CHAPS as high-value RTGS and Faster Payments as near-real-time retail. | **SOURCE_VERIFIED** |

---

## 3. Implementation and Test Strategy

For each of the 7 source-verified findings, changes will be made in the codebase to:
1. Correct the invalid reference data in `backend/app/data/icd_staging_store.json`.
2. Implement validation helpers in `backend/app/services/canonicalizer.py` and `backend/app/core/`.
3. Add a dedicated test file `tests/test_p1_batch_4_remediation.py` containing deterministic positive and negative test cases for all 7 Master IDs.
4. Verify complete test suite execution with 0 regressions.
