# SME Playbook: Sanctions Clearance & Homonym Disambiguation
**Document Reference**: `SOP-301-SAN`  
**Governing Standard**: OFAC / EU Sanctions Directives / FATF Recommendation 16  
**Target Roles**: Compliance Approvers (Marisol Vega), Compliance Analysts

---

## 1. Exception Definition & Legal Authority

A `SANCTIONS_SUSPECTED` exception occurs when an entity in the payment chain (Debtor, Creditor, Intermediary, or Beneficiary Country) triggers a lexical match against an active watchlist (OFAC SDN, EU Consolidated List, UN Security Council List, UK OFSI).

> [!CAUTION]
> **Strict Legal Authority Requirement**: Only certified **Compliance Approvers** (or designated MLRO officers) hold institutional legal authority to clear sanctions alerts. Operations Approvers and Makers cannot clear sanctions.

---

## 2. 4-Tier Fuzzy Matching & Confidence Scoring

The sanctions screening engine scores potential hits based on string distance, token permutations, and phonetics (Jaro-Winkler, Levenshtein, Double Metaphone):

| Match Score | Alert Tier | Initial Assessment |
| :--- | :--- | :--- |
| **$98\% - 100\%$** | Tier 1: Exact / High Probability Match | Presumed True Hit. Mandatory freeze pending deep regulatory investigation. |
| **$85\% - 97\%$** | Tier 2: Strong Partial / Phonetic Match | Suspected Homonym. Requires secondary identifier cross-examination. |
| **$70\% - 84\%$** | Tier 3: Loose Lexical Permutation | Low Probability. Rapid disambiguation via registration numbers. |
| **$< 70\%$** | Tier 4: Below Threshold | Auto-filtered by pre-screening pipeline. |

---

## 3. Secondary Identifier Disambiguation Protocol

To clear a suspected false-positive (homonym), Compliance Approvers MUST verify at least **two independent secondary identifiers**:

```
┌────────────────────────────────────────────────────────┐
│   Secondary Identifier Cross-Examination Checklist     │
├────────────────────────────────────────────────────────┤
│ [✓] 1. Corporate Registration / Tax ID Number          │
│        Target Entity Tax ID ≠ Watchlist Specially      │
│        Designated National (SDN) Listed Identifier.    │
│                                                        │
│ [✓] 2. Date of Incorporation / Date of Birth (DOB)     │
│        Incorporation date (e.g. 2014) ≠ Target SDN     │
│        creation date (e.g. 1982).                      │
│                                                        │
│ [✓] 3. Registered Country of Incorporation & Street    │
│        Jurisdiction is NOT a sanctioned territory      │
│        (e.g. United Kingdom vs Designated Region).     │
│                                                        │
│ [✓] 4. Ultimate Beneficial Ownership (UBO >= 25%)      │
│        UBO chain contains no listed sanctioned parties.│
└────────────────────────────────────────────────────────┘
```

---

## 4. Governed Action Execution & Audit Tagging

When the Compliance Approver clicks **`✓ Clear False Positive & Release`**:
* The system stamps the cryptographic audit record with `CLEAR_FALSE_POSITIVE`.
* Mandatory audit tags logged: `["OFAC SDN Checked", "Tax ID Disambiguated", "DOB Mismatch Validated", "Zero Listed UBO"]`.
* The case transitions to `PENDING_APPROVAL` (or `APPROVED` if Tier-1 clearance is sufficient).
