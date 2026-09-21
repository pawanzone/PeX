# SME Playbook: Invalid BIC & Routing Resolution
**Document Reference**: `SOP-115-BIC`  
**Governing Standard**: ISO 9362 (Business Identifier Codes) / SWIFT Directory Services  
**Target Roles**: Payment Operations Analysts (Makers), Operations Approvers (Checkers)

---

## 1. Exception Definition & Root Causes

An `INVALID_BIC` exception occurs when the creditor financial institution or intermediary routing code is rejected by clearing networks:

| Root Cause | Mechanism | Resolution Strategy |
| :--- | :--- | :--- |
| **8-to-11 Character Omission** | Originator sent an 8-character BIC without branch routing (`XXX` head office default missing). | Expand with `XXX` or match specific branch code from client street address. |
| **Bank Merger / Acquisition** | Target institution was acquired or merged (e.g. Credit Suisse $\rightarrow$ UBS, Bank of America branch consolidation). | Resolve to successor legal entity BIC registered in SWIFT BIC Plus directory. |
| **Branch Decommissioning** | Specific branch closed, routing must default to primary clearing hub. | Re-route to national head office central settlement BIC. |
| **Clearing Rail Incompatibility** | Target BIC is not direct participant in clearing network (e.g. TARGET2, CHAPS, Fedwire). | Route through designated correspondent / clearing intermediary BIC. |

---

## 2. Standardized 4-Part BIC Structure (ISO 9362)

Reviewers must verify BIC structure against the 4 ISO 9362 components:

$$\underbrace{\mathbf{BARC}}_{\text{Bank Code (4)}}\;\underbrace{\mathbf{GB}}_{\text{Country (2)}}\;\underbrace{\mathbf{22}}_{\text{Location (2)}}\;\underbrace{\mathbf{XXX}}_{\text{Branch (3)}}$$

1. **Bank Code (4 chars)**: Must match registered financial institution.
2. **Country Code (2 chars)**: Must match ISO 3166-1 alpha-2.
3. **Location Code (2 chars)**: Identifies city or time zone region.
4. **Branch Code (3 chars, Optional in ISO 9362, Mandatory in CBPR+)**: Defaults to `XXX` for central office.

---

## 3. Decision Matrix for BIC Repair

| Scenario | Primary Evidence | Required Action | Confidence Rating |
| :--- | :--- | :--- | :---: |
| 8-char BIC missing branch | SWIFT BIC Plus Directory | Append `XXX` head office identifier | **96%** |
| Merged / Acquired Bank | Legal Entity Identifier (LEI) + SWIFT Bulletin | Substitute with Successor Holding BIC | **94%** |
| Branch Closed | Beneficiary Address Geocoding | Route to regional operating hub BIC | **92%** |
| Non-Participant Bank | Correspondent Clearing Table | Insert Intermediary Settlement BIC | **90%** |

---

## 4. Governance & Cutoff Rules

* **Clearing Cutoff Safeguard**: If repair occurs $< 30\text{ mins}$ before rail settlement window closes, high-priority queue dispatch flag is set automatically.
* **Secondary Nostro Limit Check**: High-value route substitutions must verify Nostro balance availability before dispatch.
