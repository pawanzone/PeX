# SME Playbook: KYC Expiration & Provisional Waiver Governance
**Document Reference**: `SOP-302-KYC`  
**Governing Standard**: Wolfsberg Group Anti-Money Laundering Principles / Customer Due Diligence (CDD)  
**Target Roles**: Compliance Approvers (Marisol Vega), Risk Approvers (Kenji Watanabe)

---

## 1. Exception Definition & Institutional Policy

A `KYC_EXPIRED` exception occurs when an ordering customer or beneficiary counterparty has exceeded their mandatory periodic Customer Due Diligence (CDD) review cycle date.

| Risk Category | Mandatory Review Frequency | Grace Period Allowed | Waiver Eligibility |
| :--- | :--- | :---: | :---: |
| **Low Risk (Tier 1 Corporates)** | Every 36 Months | 30 Calendar Days | Eligible for 1-time 30-day waiver |
| **Medium Risk (Commercial SMEs)** | Every 24 Months | 15 Calendar Days | Eligible with Relationship Manager sign-off |
| **High Risk / PEP / Correspondent**| Every 12 Months | 0 Days (Hard Freeze) | Ineligible for waiver — Full refresh required |

---

## 2. Standard Operating Procedure (SOP-302): Granting 30-Day Provisional Waivers

A Compliance Approver may grant a **30-Day Provisional KYC Waiver** if ALL of the following criteria are satisfied:

1. **Active Refresh in Progress**: The client onboarding team has formally requested refreshed documentation from the counterparty within the last 14 days.
2. **Clean Historical Conduct**: Zero Suspicious Activity Reports (SARs) or regulatory inquiries filed against the counterparty in the preceding 24 months.
3. **Corridor Risk Assessment**: The transaction payment corridor (e.g. AUD/USD, EUR/GBP) is low-risk and does not involve FATF high-risk jurisdictions.
4. **Institutional Exposure Threshold**: Single transaction amount is within corporate line limits.

---

## 3. High-Value Dual Authorization Escalation

If transaction amount $\ge \$250,000.00$:
* **Step 1**: Compliance Approver grants the 30-Day Waiver.
* **Step 2 (Mandatory Dual-Auth)**: Risk Approver (`Kenji Watanabe`) must co-authorize the high-value release before dispatch to settlement rails.
