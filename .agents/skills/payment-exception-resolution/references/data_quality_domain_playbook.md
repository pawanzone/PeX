# SME Playbook: Data Quality Exception Domain (9 Profiles)
**Domain Reference**: `BIAN-DQ-DOM-01`  
**Governing Standards**: ISO 13616 (IBAN), ISO 9362 (BIC), ISO 20022 External Purpose Code List, UK Confirmation of Payee (CoP) / EPC Verification of Payee (VoP)  
**Assigned Queue**: `Repair Queue`  
**Default Roles**: Payment Operations Analysts (Makers), Operations Approvers (Checkers)

---

## 1. Executive Summary & Domain Scope

The **Data Quality Domain** governs syntactic, structural, and semantic accuracy of payment party identifiers, account routing codes, and regulatory purpose declarations before transmission into interbank settlement rails.

---

## 2. 9 Detailed Exception Profiles & SME Resolution Logic

### 1. `INVALID_IBAN` (ISO 7064 Checksum Failure)
* **Root Cause**: Transposition of digits (e.g. `23` $\rightarrow$ `32`), missing bank zeroes, or typo in country code check digits.
* **Deterministic Algorithm**: Apply BigInteger MOD-97 check: $\text{Integer(Rearranged String)} \pmod{97} \equiv 1$.
* **SME Heuristic**: Search Counterparty Master SSI directory $\rightarrow$ test single-transposition permutations $\rightarrow$ propose validated replacement (+30% Confidence).

### 2. `INVALID_BIC` (SWIFT Routing Failure)
* **Root Cause**: 8-character BIC sent without branch identifier; branch closed; bank acquired.
* **Deterministic Algorithm**: Query SWIFT BIC Plus directory. If 8-char BIC, append `XXX` head office default. If decommissioned, map to successor holding BIC via LEI directory.

### 3. `MISSING_BENEFICIARY_DATA` (Incomplete Creditor Block)
* **Root Cause**: Missing creditor legal entity name, country, or mandatory ISO 20022 structured postal address tags (`<PstlAdr>`).
* **SME Heuristic**: Retrieve verified counterparty master dossier from Client KYC vault $\rightarrow$ populate structured street name, building number, post code, and town.

### 4. `MISSING_REMITTANCE_INFO` (Unstructured Payment Narrative)
* **Root Cause**: Missing `<RmtInf>` unstructured narrative or structured invoice reference (`<Strd>`) for B2B commercial wire.
* **SME Heuristic**: Cross-reference debtor Accounts Payable (AP) open purchase order index $\rightarrow$ populate commercial invoice number (e.g. `INV-2026-8891`).

### 5. `INVALID_ADDRESS_FORMAT` (CBPR+ Structured Address Non-Compliance)
* **Root Cause**: Unstructured `<AdrLine>` used where clearing rail (e.g. Fedwire ISO / Target2) requires structured `<StrtNm>`, `<BldgNb>`, `<PstCd>`, `<TwnNm>`.
* **SME Heuristic**: Execute Address Parsing Engine against ISO 20022 national schema $\rightarrow$ convert free-text lines to discrete tags.

### 6. `MISSING_PURPOSE_CODE` (Mandatory Regulatory Purpose Tag Missing)
* **Root Cause**: Missing 4-character ISO 20022 external purpose code (e.g. `SALA` for salary, `SUPP` for supplier, `TREA` for treasury) required by destination central bank.
* **SME Heuristic**: Infer purpose code from invoice metadata / debtor business segment $\rightarrow$ assign standardized 4-character code (e.g. `GDSV` for goods & services).

### 7. `INVALID_ACCOUNT_NUMBER` (Domestic Clearing Account Corrupted)
* **Root Cause**: Non-IBAN domestic account number (e.g. US 9-digit ABA DDA, UK 8-digit account number, AU 9-digit account) contains letters or invalid check digit.
* **SME Heuristic**: Apply national modulo algorithm (e.g. UK Modulus Weighting, US Fedwire Routing Checksum 3-7-1 algorithm) $\rightarrow$ propose corrected sequence.

### 8. `INVALID_ROUTING_CODE` (National Clearing Transit Number Invalid)
* **Root Cause**: Obsolete Fedwire ABA routing number, UK Sort Code (6 digits), or Australian BSB (6 digits).
* **SME Heuristic**: Cross-reference national clearing transit tables (Federal Reserve E-Payments Directory / UK Extended Industry Sort Code Directory) $\rightarrow$ replace with active clearing transit code.

### 9. `BENEFICIARY_NAME_MISMATCH` (Confirmation of Payee / CoP Alert)
* **Root Cause**: Account name on payment instruction (e.g. *"Acme Tech"*) does not match exact corporate ledger name on receiving bank account (e.g. *"Acme Technologies Global Ltd"*).
* **SME Heuristic**: Execute Jaro-Winkler token similarity. If score $\ge 0.85$ (Close Match / Partial Match), verify trading name alias in Company House / SEC registry $\rightarrow$ approve with Maker-Checker dual audit sign-off.
