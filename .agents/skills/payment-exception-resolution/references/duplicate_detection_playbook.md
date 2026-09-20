# SME Playbook: Duplicate Payment & Burst Detection
**Document Reference**: `SOP-204-DUP`  
**Governing Standard**: FFIEC Retail Payment Systems / Basel Operational Risk Framework  
**Target Roles**: Payment Operations Analysts, Operations Approvers, Risk Officers

---

## 1. Exception Definition & Risk Exposure

A `DUPLICATE_PAYMENT` exception occurs when multiple payment instructions with matching attributes are received within a narrow timeframe, introducing risk of double settlement, customer overdraft, or fraudulent replay.

---

## 2. 4-Point Duplicate Evaluation Matrix

The decision engine compares incoming transactions against the active 30-day settlement index using a 4-point verification vector:

| Comparison Vector | Exact Match Criteria | Tolerance / Variance Allowed |
| :--- | :--- | :--- |
| **Vector 1: Beneficiary Entity** | Creditor Account Number / IBAN + Name Token | 0% variance (Exact Match) |
| **Vector 2: Remittance Reference** | Invoice Number / Payment Reference Tag | 0% variance (e.g. `INV-2026-8891`) |
| **Vector 3: Exact Monetary Amount** | Value in Settlement Currency | 0% variance (e.g. `AUD 3,274,920.10`) |
| **Vector 4: Ingestion Time Window** | Timestamp differential $\Delta t$ | $\Delta t \le 30\text{ minutes}$ $\rightarrow$ Immediate Duplicate Alert |

---

## 3. Disambiguation: True Duplicate vs Legitimate Business Batch

Not all identical payments are duplicates. Reviewers must evaluate the following business hypotheses:

### Hypothesis A: Erroneous ERP System Retry (True Duplicate)
* **Indicators**: Same UETR prefix or same invoice number transmitted twice within $< 15\text{ minutes}$; debtor AP system logged network timeout.
* **Governed Action**: **REJECT & CANCEL** duplicate instruction; retain original transaction for settlement.

### Hypothesis B: Scheduled Recurring Payroll / Retainer (Legitimate)
* **Indicators**: Remittance description indicates period cadence (e.g. *"Monthly Consulting Retainer - August 2026"*), regular calendar schedule match.
* **Governed Action**: **RELEASE & CLEAR** with Maker-Checker dual confirmation.

### Hypothesis C: Milestone Tranche Payment (Legitimate)
* **Indicators**: Commercial contract specifies multi-tranche disbursements with identical monetary values (e.g. Tranche 1 of 3, Tranche 2 of 3).
* **Governed Action**: Verify contract schedule in Document Vault $\rightarrow$ **RELEASE**.
