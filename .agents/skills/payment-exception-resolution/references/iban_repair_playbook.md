# SME Playbook: Invalid IBAN Validation & Transposition Repair
**Document Reference**: `SOP-114-IBAN`  
**Governing Standard**: ISO 13616 / ISO 7064 MOD-97-10  
**Target Roles**: Payment Operations Analysts (Makers), Operations Approvers (Checkers)

---

## 1. Exception Definition & Root Cause Taxonomy

An `INVALID_IBAN` exception occurs when an incoming pacs.008 credit transfer contains a creditor account identifier that fails canonical structural or mathematical validation:

| Error Sub-Type | Description | Common Root Causes |
| :--- | :--- | :--- |
| **MOD-97 Failure** | Structure is valid, but the 2-digit check digits fail modulo 97 calculation. | Single-digit typo, adjacent digit transposition (e.g. `23` $\rightarrow$ `32`), copy-paste omission. |
| **Length Mismatch** | Total character count does not match the national standard for the country code. | Missing leading bank zeroes, truncated copy-paste, accidental white spaces. |
| **Invalid Country Code** | Leading 2 characters do not match an ISO 3166-1 alpha-2 registered banking jurisdiction. | Typo in country code (e.g. `GE` instead of `DE`, `GB` instead of `GI`). |
| **BBAN Character Set Violation** | Basic Bank Account Number (BBAN) contains forbidden symbols or letters in numeric fields. | Hyphens, slashes, or alphabetical characters in strictly numeric national account fields. |

---

## 2. Deterministic Validation Algorithm (ISO 7064 MOD-97-10)

The validation engine and human reviewers MUST execute the following mathematical verification:

1. **Country Length Check**:
   Verify length against the ISO 13616 registry matrix:
   * **DE (Germany)**: 22 chars
   * **GB (United Kingdom)**: 22 chars
   * **FR (France)**: 27 chars
   * **IT (Italy)**: 27 chars
   * **ES (Spain)**: 24 chars
   * **NL (Netherlands)**: 18 chars
   * **CH (Switzerland)**: 21 chars
   * **AU (Australia)**: Not IBAN (Uses 6-digit BSB + 9-digit Account No)

2. **Rearrange String**:
   Move the first 4 characters (Country Code + Check Digits) to the end of the string:
   $$\text{Original: } \mathbf{GB82}\text{BARC20041538192831} \longrightarrow \text{Rearranged: } \text{BARC20041538192831}\mathbf{GB82}$$

3. **Character Conversion**:
   Convert all alphabetical letters to digits ($A=10, B=11, \dots, Z=35$):
   $$\text{BARC...} \longrightarrow 1110271220041538192831161182$$

4. **Compute Modulo 97**:
   Divide the integer by 97.
   $$\text{Result: } \text{BigInteger} \pmod{97} \equiv 1$$
   * If remainder is **1**: The IBAN is **mathematically valid** [✓ PASS].
   * If remainder is **$\neq 1$**: The IBAN is **corrupted / invalid** [✕ FAIL].

---

## 3. Grounded Repair Heuristics & Decision Tree

When repairing an invalid IBAN, the reasoner must follow this prioritized decision tree:

```
[Incoming Corrupted IBAN]
         │
         ▼
[Step 1: Check Beneficiary Master Directory SSI]
         │
         ├─── Exact Entity Match Found ───► Propose Registered SSI IBAN (+25% Conf)
         │
         └─── No Exact Match Found
                  │
                  ▼
[Step 2: Generate Adjacent Transposition Hypotheses]
         │
         ├─── Transposition Yields MOD-97 == 1 ───► Evaluate Historical Settlement History
         │                                               ├── Validated Corridor History ──► Propose Transposition (+30% Conf)
         │                                               └── No History ──► Flag for Analyst Manual Callout
         │
         └─── No Valid Transposition ───► Propose Return to Maker / Inquire Counterparty
```

---

## 4. Required Audit Evidence & Output Format

Every approved IBAN repair must output a structured change record:
* **Original Corrupted Value**: Masked showing corruption (e.g. `GB82BARC20041538192831`).
* **Repaired Value**: Validated IBAN (e.g. `GB29BARC20041538192831`).
* **Mathematical Proof**: Remainder = 1 confirmation log.
* **Beneficiary Verification**: Master SSI ID (e.g. `SSI-GLO-BARC-001`).
* **Attribution Score**: Minimum 90% required for Straight-Through Tier 1 sign-off.
