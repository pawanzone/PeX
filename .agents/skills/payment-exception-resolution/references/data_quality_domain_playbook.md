# SME Playbook: Data Quality Exception Domain (9 Profiles)
**Domain Reference**: `BIAN-DQ-DOM-01`  
**Governing Standards**: ISO 13616 (IBAN), ISO 7064 MOD-97-10, ISO 9362 (BIC), ISO 20022 External Purpose Code List, UK Confirmation of Payee (CoP) / EPC Verification of Payee (VoP)  
**Assigned Queue**: `Repair Queue`  
**Default Roles**: Payment Operations Analysts (Makers), Operations Approvers (Checkers)

---

## 1. Executive Summary & Domain Scope

The **Data Quality Domain** governs the syntactic, structural, and semantic integrity of payment party identifiers, account numbers, routing codes, and regulatory purpose declarations across all domestic and cross-border settlement rails (Fedwire, CHIPS, TARGET2, CHAPS, SEPA, SWIFT CBPR+).

---

## 2. Global IBAN Country Registry & Mathematical Verification

### Country Length Specifications (ISO 13616)
* **DE (Germany)**: 22 chars
* **GB (United Kingdom)**: 22 chars
* **FR (France)**: 27 chars
* **IT (Italy)**: 27 chars
* **ES (Spain)**: 24 chars
* **NL (Netherlands)**: 18 chars
* **CH (Switzerland)**: 21 chars
* **AU (Australia)**: Not IBAN (Uses 6-digit BSB + 9-digit Account No)
* **US (United States)**: Not IBAN (Uses 9-digit ABA Routing + DDA)

### Deterministic ISO 7064 MOD-97-10 Verification Algorithm
1. **Rearrange String**: Move initial 4 characters (Country Code + 2 Check Digits) to the end:
   $$\text{Original: } \mathbf{GB82}\text{WEST12345698765432} \longrightarrow \text{Rearranged: } \text{WEST12345698765432}\mathbf{GB82}$$
2. **Alpha-to-Numeric Substitution**: Replace each letter ($A=10, B=11, \dots, Z=35$):
   $$\text{WEST...} \longrightarrow 3214282912345698765432161182$$
3. **Compute Modulo 97**:
   $$\text{Integer(Substituted String)} \pmod{97} \equiv 1$$
   * Remainder $= 1$: **Checksum Valid** [✓ PASS]
   * Remainder $\neq 1$: **Checksum Corrupted / Transposition Detected** [✕ FAIL]

```json
{
  "validator": "ISO_7064_MOD97",
  "input_iban": "GB82WEST12345698765432",
  "rearranged": "WEST12345698765432GB82",
  "remainder": 14,
  "status": "FAIL_CHECKSUM",
  "candidate_repair": {
    "proposed_iban": "GB82WEST12345698765431",
    "remainder": 1,
    "confidence": 0.98,
    "justification": "Transposition repair on check digit matching beneficiary master record."
  }
}
```

---

## 3. Standardized BIC Structure & Routing Decision Tree (ISO 9362)

$$\underbrace{\mathbf{BARC}}_{\text{Bank Code (4)}}\;\underbrace{\mathbf{GB}}_{\text{Country (2)}}\;\underbrace{\mathbf{22}}_{\text{Location (2)}}\;\underbrace{\mathbf{XXX}}_{\text{Branch (3)}}$$

| Scenario | Primary Evidence | Required Action | Confidence Rating |
| :--- | :--- | :--- | :---: |
| **8-Char BIC Missing Branch** | SWIFT BIC Plus Directory | Append `XXX` head office identifier | **96%** |
| **Merged / Acquired Bank** | Legal Entity Identifier (LEI) Directory | Substitute with Successor Holding BIC | **94%** |
| **Branch Decommissioned** | Beneficiary Geocoding Database | Route to regional operating hub BIC | **92%** |
| **Non-Participant Bank** | Correspondent Clearing Table | Insert Intermediary Settlement BIC | **90%** |

---

## 4. 9 Detailed Exception Profiles & SME Resolution Logic

### 1. `INVALID_IBAN` (ISO 7064 Checksum Failure)
* **Root Cause**: Transposition of digits (e.g. `23` $\rightarrow$ `32`), missing bank zeroes, or typo in country code check digits.
* **Resolution**: Execute MOD-97 validation $\rightarrow$ cross-reference Beneficiary Standing Settlement Instructions (SSI) $\rightarrow$ propose corrected string.
```json
{
  "profile": "INVALID_IBAN",
  "field_path": "creditor_account.iban",
  "original_value": "GB82WEST12345698765432",
  "proposed_value": "GB82WEST12345698765431",
  "validation_status": "VALIDATED_CHECKSUM_PASS",
  "confidence_score": 0.98
}
```

### 2. `INVALID_BIC` (SWIFT Routing Failure)
* **Root Cause**: 8-character BIC sent without branch identifier; branch closed; bank acquired.
* **Resolution**: Query SWIFT BIC Plus directory. Append `XXX` head office default or map to successor holding BIC.
```json
{
  "profile": "INVALID_BIC",
  "field_path": "creditor_account.bank_bic",
  "original_value": "LOYDGB2LXXX",
  "proposed_value": "LOYDGB21XXX",
  "validation_status": "DIRECTORY_MATCH_CONFIRMED",
  "confidence_score": 0.96
}
```

### 3. `MISSING_BENEFICIARY_DATA` (Incomplete Creditor Block)
* **Root Cause**: Missing creditor legal entity name, country, or mandatory ISO 20022 structured postal address tags (`<PstlAdr>`).
* **Resolution**: Retrieve verified counterparty master dossier from Client KYC vault $\rightarrow$ populate structured street name, building number, post code, and town.

### 4. `MISSING_REMITTANCE_INFO` (Unstructured Payment Narrative)
* **Root Cause**: Missing `<RmtInf>` unstructured narrative or structured invoice reference (`<Strd>`) for B2B commercial wire.
* **Resolution**: Cross-reference debtor Accounts Payable (AP) open purchase order index $\rightarrow$ populate commercial invoice number.

### 5. `INVALID_ADDRESS_FORMAT` (CBPR+ Structured Address Non-Compliance)
* **Root Cause**: Unstructured `<AdrLine>` used where clearing rail requires structured `<StrtNm>`, `<BldgNb>`, `<PstCd>`, `<TwnNm>`.
* **Resolution**: Execute Address Parsing Engine against ISO 20022 national schema $\rightarrow$ convert free-text lines to discrete structured XML tags.

### 6. `MISSING_PURPOSE_CODE` (Mandatory Regulatory Purpose Tag Missing)
* **Root Cause**: Missing 4-character ISO 20022 external purpose code (e.g. `SALA`, `SUPP`, `TREA`, `GDSV`) required by destination clearing rail.
* **Resolution**: Infer purpose code from invoice metadata / debtor business segment $\rightarrow$ assign standardized 4-character code.

### 7. `INVALID_ACCOUNT_NUMBER` (Domestic Clearing Account Corrupted)
* **Root Cause**: Non-IBAN domestic account number (e.g. US 9-digit ABA DDA, UK 8-digit account number) contains hyphens, spaces, or check digit error.
* **Resolution**: Apply national modulo algorithm (UK Modulus Weighting, US Fedwire Routing Checksum 3-7-1) $\rightarrow$ propose sanitized sequence.

### 8. `INVALID_ROUTING_CODE` (National Clearing Transit Number Invalid)
* **Root Cause**: Obsolete Fedwire ABA routing number, UK Sort Code (6 digits), or Australian BSB (6 digits).
* **Resolution**: Cross-reference national clearing transit tables (Federal Reserve E-Payments Directory / UK EISCD) $\rightarrow$ replace with active clearing transit code.

### 9. `BENEFICIARY_NAME_MISMATCH` (Confirmation of Payee / CoP Alert)
* **Root Cause**: Account name on payment instruction (e.g. *"Acme Tech"*) does not match exact corporate ledger name on receiving bank account (e.g. *"Acme Technologies Global Ltd"*).
* **Resolution**: Execute Jaro-Winkler token similarity. If score $\ge 0.85$ (Close Match), verify trading name alias in Company House / SEC registry $\rightarrow$ approve with Maker-Checker dual audit sign-off.
