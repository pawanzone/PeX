# SME Playbook: Compliance Exception Domain (8 Profiles)
**Domain Reference**: `BIAN-COMP-DOM-03`  
**Governing Standards**: OFAC SDN Directives, FATF Recommendations (Rec 16 Wire Transfer Rule), Wolfsberg AML Principles, EU AMLD6  
**Assigned Queue**: `Compliance Queue`  
**Default Roles**: Compliance Approvers (Marisol Vega), MLRO Officers

---

## 1. Executive Summary & Legal Governance

The **Compliance Domain** isolates all financial crime, sanctions screening, anti-money laundering (AML), and regulatory embargo risks. 

> [!CAUTION]
> Under institutional segregation of duties, **only certified Compliance Approvers** hold legal authority to clear alerts or grant regulatory exemptions in this domain.

---

## 2. 8 Detailed Exception Profiles & SME Resolution Logic

### 1. `SANCTIONS_SUSPECTED` (Watchlist Fuzzy Match)
* **Screening Focus**: OFAC, EU, UN, UK OFSI lists.
* **SME Heuristic**: If match score $85\%-97\%$, examine Tax ID, Date of Incorporation, and registered address. Clear false positive if 2+ independent secondary identifiers diverge from the target SDN.

### 2. `AML_ALERT` (Structuring / Rapid Velocity Spike)
* **Root Cause**: Transaction triggers pattern detection (e.g. repeated transfers just below regulatory reporting thresholds, or sudden surge in volume).
* **SME Heuristic**: Review 90-day account transaction velocity $\rightarrow$ verify source of wealth documentation $\rightarrow$ clear or escalate to MLRO for SAR filing.

### 3. `PEP_MATCH` (Politically Exposed Person Identified)
* **Root Cause**: Debtor or Creditor ultimate beneficial owner (UBO) identified as a senior political official, judicial figure, or immediate family member.
* **SME Heuristic**: Execute Enhanced Due Diligence (EDD) $\rightarrow$ verify Senior Management Approval Form $\rightarrow$ sign off with Level 2 Dual-Auth.

### 4. `RESTRICTED_CORRIDOR` (Embargo / Geopolitical Sanctions)
* **Root Cause**: Payment routing path or counterparty jurisdiction intersects with a sanctioned geographic territory (e.g. comprehensive embargoed regions).
* **SME Heuristic**: Verify whether specific humanitarian / OFAC general license applies. If no license $\rightarrow$ **HARD BLOCK & FREEZE**.

### 5. `ADVERSE_MEDIA_MATCH` (Negative News Alert)
* **Root Cause**: Entity identified in global adverse news screening (allegations of bribery, corruption, fraud, or tax evasion).
* **SME Heuristic**: Cross-reference legal status of allegations (conviction vs unsubstantiated press) $\rightarrow$ determine ongoing risk tolerance rating.

### 6. `HIGH_RISK_JURISDICTION` (FATF Grey / Black List Corridor)
* **Root Cause**: Counterparty bank located in jurisdiction subject to FATF increased monitoring.
* **SME Heuristic**: Mandate Enhanced Due Diligence (EDD) certificate + Nostro correspondent justification before releasing wire.

### 7. `REGULATORY_REPORTING_REQUIRED` (Balance of Payments Declaration)
* **Root Cause**: Cross-border foreign exchange transfer exceeds statutory reporting limit (e.g. BoP reporting in EU, SAFE reporting in Asia-Pac).
* **SME Heuristic**: Extract trade invoice / customs declaration number $\rightarrow$ populate mandatory regulatory declaration tags (`<RgltryRptg>`).

### 8. `CUSTOMER_WATCHLIST_MATCH` (Internal Bank Blacklist)
* **Root Cause**: Entity matched against internal bank risk blacklist (fraudulent chargebacks, previous bad debt, off-boarded counterparty).
* **SME Heuristic**: Review internal exit memo $\rightarrow$ determine if legacy account closure or active fraud alert $\rightarrow$ enforce closure policy.
