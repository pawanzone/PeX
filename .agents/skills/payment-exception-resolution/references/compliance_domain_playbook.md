# SME Playbook: Compliance Exception Domain (8 Profiles)
**Domain Reference**: `BIAN-COMP-DOM-03`  
**Governing Standards**: OFAC SDN Directives, FATF Recommendations (Rec 16 Wire Transfer Rule), Wolfsberg AML Principles, EU AMLD6  
**Assigned Queue**: `Compliance Queue`  
**Default Roles**: Compliance Approvers (Marisol Vega), MLRO Officers

---

## 1. Executive Summary & Legal Governance

The **Compliance Domain** isolates all financial crime, sanctions screening, anti-money laundering (AML), and regulatory embargo risks. 

> [!CAUTION]
> **Strict Legal Authority Requirement**: Under institutional segregation of duties, **only certified Compliance Approvers** hold legal authority to clear alerts or grant regulatory exemptions in this domain. Operations Approvers and Makers are strictly barred from clearing compliance exceptions.

---

## 2. 4-Tier Fuzzy Matching & Watchlist Confidence Rating

The sanctions screening engine scores potential hits based on string distance, token permutations, and phonetics (Jaro-Winkler, Levenshtein, Double Metaphone):

| Match Score | Alert Tier | Initial Assessment | Operational Protocol |
| :--- | :--- | :--- | :--- |
| **$98\% - 100\%$** | Tier 1: Exact Match | Presumed True Hit | **Mandatory Freeze**. Escalate to MLRO & General Counsel. |
| **$85\% - 97\%$** | Tier 2: Strong Partial Match | Suspected Homonym | Execute Secondary Identifier Disambiguation Protocol. |
| **$70\% - 84\%$** | Tier 3: Loose Permutation | Low Probability | Rapid disambiguation via official corporate registry check. |
| **$< 70\%$** | Tier 4: Below Threshold | Noise | Auto-filtered by pre-screening pipeline. |

---

## 3. Secondary Identifier Disambiguation Protocol (Homonym Clearance)

To clear a suspected false-positive (homonym), Compliance Approvers MUST verify at least **two independent secondary identifiers**:

```
┌────────────────────────────────────────────────────────┐
│   Secondary Identifier Cross-Examination Checklist     │
├────────────────────────────────────────────────────────┤
│ [✓] 1. Corporate Registration / Tax ID Number          │
│        Target Entity Tax ID ≠ Watchlist SDN Identifier.│
│                                                        │
│ [✓] 2. Date of Incorporation / Date of Birth (DOB)     │
│        Incorporation date (e.g. 2014) ≠ Target SDN     │
│        creation date (e.g. 1982).                      │
│                                                        │
│ [✓] 3. Registered Jurisdiction & Physical Address      │
│        Jurisdiction is NOT a sanctioned territory      │
│        (e.g. United Kingdom vs Designated Region).     │
│                                                        │
│ [✓] 4. Ultimate Beneficial Ownership (UBO >= 25%)      │
│        UBO ownership chain contains zero listed parties│
└────────────────────────────────────────────────────────┘
```

```json
{
  "compliance_clearance": {
    "screening_engine": "OFAC_SDN_WATCHLIST_v4.2",
    "target_hit": "AL-TAQWA TRADE LTD (SDN-9841)",
    "subject_entity": "AL-TAQWA LOGISTICS UK LTD",
    "lexical_similarity": 0.88,
    "clearance_verdict": "CLEAR_FALSE_POSITIVE",
    "verified_differentiators": [
      "Tax ID: UK-889124401 vs SDN-IRAN-00912",
      "Incorporation Date: 2018-04-12 vs SDN Listing Date: 2001-11-07",
      "Registered Country: United Kingdom (Non-Sanctioned)"
    ],
    "dual_auth_required": false,
    "authorized_by": "Marisol Vega (COMPLIANCE_APPROVER)"
  }
}
```

---

## 4. 8 Detailed Exception Profiles & SME Resolution Logic

### 1. `SANCTIONS_SUSPECTED` (Watchlist Fuzzy Match)
* **Screening Focus**: OFAC, EU, UN, UK OFSI lists.
* **Resolution**: If match score $85\%-97\%$, examine Tax ID, Date of Incorporation, and registered address. Clear false positive if 2+ independent secondary identifiers diverge from target SDN.

### 2. `AML_ALERT` (Structuring / Rapid Velocity Spike)
* **Root Cause**: Transaction triggers pattern detection (e.g. repeated transfers just below regulatory reporting thresholds, or sudden surge in volume).
* **Resolution**: Review 90-day account transaction velocity $\rightarrow$ verify source of wealth documentation $\rightarrow$ clear or escalate to MLRO for SAR filing.

### 3. `PEP_MATCH` (Politically Exposed Person Identified)
* **Root Cause**: Debtor or Creditor ultimate beneficial owner (UBO) identified as a senior political official, judicial figure, or immediate family member.
* **Resolution**: Execute Enhanced Due Diligence (EDD) $\rightarrow$ verify Senior Management Approval Form $\rightarrow$ sign off with Level 2 Dual-Auth.

### 4. `RESTRICTED_CORRIDOR` (Embargo / Geopolitical Sanctions)
* **Root Cause**: Payment routing path or counterparty jurisdiction intersects with a sanctioned geographic territory.
* **Resolution**: Verify whether specific humanitarian / OFAC general license applies. If no license $\rightarrow$ **HARD BLOCK & FREEZE**.

### 5. `ADVERSE_MEDIA_MATCH` (Negative News Alert)
* **Root Cause**: Entity identified in global adverse news screening (allegations of bribery, corruption, fraud, or tax evasion).
* **Resolution**: Cross-reference legal status of allegations (conviction vs unsubstantiated press) $\rightarrow$ determine ongoing risk tolerance rating.

### 6. `HIGH_RISK_JURISDICTION` (FATF Grey / Black List Corridor)
* **Root Cause**: Counterparty bank located in jurisdiction subject to FATF increased monitoring.
* **Resolution**: Mandate Enhanced Due Diligence (EDD) certificate + Nostro correspondent justification before releasing wire.

### 7. `REGULATORY_REPORTING_REQUIRED` (Balance of Payments Declaration)
* **Root Cause**: Cross-border foreign exchange transfer exceeds statutory reporting limit (e.g. BoP reporting in EU, SAFE reporting in Asia-Pac).
* **Resolution**: Extract trade invoice / customs declaration number $\rightarrow$ populate mandatory regulatory declaration tags (`<RgltryRptg>`).

### 8. `CUSTOMER_WATCHLIST_MATCH` (Internal Bank Blacklist)
* **Root Cause**: Entity matched against internal bank risk blacklist (fraudulent chargebacks, previous bad debt, off-boarded counterparty).
* **Resolution**: Review internal exit memo $\rightarrow$ determine if legacy account closure or active fraud alert $\rightarrow$ enforce closure policy.
