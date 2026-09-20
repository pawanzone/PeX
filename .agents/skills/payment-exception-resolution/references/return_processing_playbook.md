# SME Playbook: Returned Payment & pacs.004 Reconciliation
**Document Reference**: `SOP-401-RET`  
**Governing Standard**: ISO 20022 Financial Services — Payment Return (`pacs.004.001.09`) / CBPR+  
**Target Roles**: Payment Operations Analysts (Makers), Operations Approvers (Checkers)

---

## 1. Exception Definition & ISO 20022 Return Architecture

A `RETURNED_PAYMENT` exception occurs when an outbound credit transfer (`pacs.008`) is rejected or returned by the creditor bank or clearing hub via an incoming ISO 20022 `pacs.004` Payment Return message.

---

## 2. Standard ISO 20022 Return Reason Code Matrix

The decision engine and operational reviewers categorize returns using the official ISO 20022 external return code directory:

| ISO Code | Name | Root Cause | Governed Operational Action |
| :--- | :--- | :--- | :--- |
| **`AC04`** | Closed Account Number | Creditor account closed prior to settlement arrival. | Hold funds in escrow; request updated counterparty beneficiary details from debtor. |
| **`AC06`** | Blocked Account | Creditor account frozen due to legal/court order or insolvency. | Return principal to originator; notify relationship manager. |
| **`AG01`** | Disallowed Transaction / Currency | Clearing rail or receiver does not support payment type/currency. | Re-route via alternative correspondent corridor or convert currency. |
| **`MD01`** | Counterparty Revocation | Debtor requested recall of direct debit / payment instruction. | Reconcile with originator treasury authorization. |
| **`BE04`** | Missing Creditor Address | Beneficiary address missing in pacs.008 (CBPR+ rule violation). | Populate canonical address from Client Master Vault $\rightarrow$ Re-dispatch. |

---

## 3. 5-Step Operational Reconciliation Workflow

1. **UETR Correlation**: Match incoming `pacs.004` `OrgnlTxId` and `OrgnlUETR` against the original outbound `pacs.008` settlement record.
2. **Fee & Principal Breakdown**: Verify whether intermediary banks deducted processing charges (e.g. Returned Amount = Original Amount - Charges).
3. **Escrow / Nostro Credit**: Credit returned funds to internal intermediary suspense account.
4. **Debtor Notification**: Generate automated remittance advice to debtor treasury describing return code rationale.
5. **Maker-Checker Sign-Off**: Operator submits proposed ledger re-credit $\rightarrow$ Operations Approver authorizes ledger release.
