# SME Playbook: Settlement & Returns Exception Domain (7 Profiles)
**Domain Reference**: `BIAN-SETT-DOM-05`  
**Governing Standards**: ISO 20022 `pacs.004.001.09` (Payment Return), `camt.056` (Payment Cancellation Request), `pacs.002` (Payment Status Report), SWIFT Exception & Investigation (E&I)  
**Assigned Queue**: `Settlement / Returns Queue`  
**Default Roles**: Cash Management Operations, Reconciliation Specialists, Settlement Officers

---

## 1. Executive Summary & Domain Scope

The **Settlement & Returns Domain** resolves post-dispatch failures, rejected clearing deliveries, beneficiary account freezes, correspondent trapping, and ledger reconciliation breaks across domestic RTGS and cross-border networks.

---

## 2. Standard ISO 20022 Return Reason Code Matrix (pacs.004)

The decision engine and operational reviewers categorize returns using the official ISO 20022 external return code directory:

| ISO Code | Name | Root Cause | Governed Operational Action |
| :--- | :--- | :--- | :--- |
| **`AC04`** | Closed Account Number | Creditor account closed prior to settlement arrival. | Hold funds in escrow; request updated counterparty beneficiary details from debtor. |
| **`AC06`** | Blocked Account | Creditor account frozen due to legal/court order or insolvency. | Return principal to originator; notify relationship manager. |
| **`AG01`** | Disallowed Transaction / Currency | Clearing rail or receiver does not support payment type/currency. | Re-route via alternative correspondent corridor or convert currency. |
| **`MD01`** | Counterparty Revocation | Debtor requested recall of direct debit / payment instruction. | Reconcile with originator treasury authorization. |
| **`BE04`** | Missing Creditor Address | Beneficiary address missing in pacs.008 (CBPR+ rule violation). | Populate canonical address from Client Master Vault $\rightarrow$ Re-dispatch. |
| **`RR01`** | Regulatory Reason | Receiving jurisdiction rejected wire due to local regulatory constraint. | Escalate to Compliance Officer. |

```json
{
  "return_reconciliation": {
    "incoming_message": "pacs.004.001.09",
    "original_uetr": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "return_reason_code": "AC04",
    "original_amount": 18200.00,
    "charges_deducted": 25.00,
    "net_recredit_amount": 18175.00,
    "currency": "EUR",
    "status": "FUNDS_HELD_IN_ESCROW",
    "proposed_action": "RETURN_PRINCIPAL_REVERSAL",
    "maker_checker_status": "PENDING_CHECKER_SIGN_OFF"
  }
}
```

---

## 3. 5-Step Operational Reconciliation Workflow

1. **UETR Correlation**: Match incoming `pacs.004` `OrgnlTxId` and `OrgnlUETR` against the original outbound `pacs.008` settlement record.
2. **Fee & Principal Breakdown**: Verify whether intermediary banks deducted processing charges (Returned Amount = Original Amount - Charges).
3. **Escrow / Nostro Credit**: Credit returned funds to internal intermediary suspense account.
4. **Debtor Notification**: Generate automated remittance advice to debtor treasury describing return code rationale.
5. **Maker-Checker Sign-Off**: Operator submits proposed ledger re-credit $\rightarrow$ Operations Approver authorizes ledger release.

---

## 4. 7 Detailed Exception Profiles & SME Resolution Logic

### 1. `RETURNED_PAYMENT` (Generic pacs.004 Return Arrival)
* **Root Cause**: Receiving bank returned funds via `pacs.004` message.
* **Resolution**: Parse return reason code $\rightarrow$ reconcile principal vs charges deducted $\rightarrow$ re-credit originator escrow account.

### 2. `ACCOUNT_CLOSED` (ISO Return Code `AC04`)
* **Root Cause**: Beneficiary account closed by receiving bank prior to wire arrival.
* **Resolution**: Hold funds in suspense $\rightarrow$ generate automated secure inquiry to debtor treasury requesting active replacement beneficiary account $\rightarrow$ re-dispatch.

### 3. `BENEFICIARY_ACCOUNT_FROZEN` (ISO Return Code `AC06`)
* **Root Cause**: Beneficiary account blocked due to legal garnishment, insolvency proceedings, or court order.
* **Resolution**: Refund net principal to debtor account $\rightarrow$ generate formal legal notice advice to customer.

### 4. `RECONCILIATION_BREAK` (Internal Ledger vs Bank Statement Mismatch)
* **Root Cause**: `camt.053` bank statement end-of-day balance does not match internal settlement subledger entry.
* **Resolution**: Run automated 3-way matching algorithm (UETR, amount, value date) $\rightarrow$ isolate missing ledger leg $\rightarrow$ generate balancing posting.

### 5. `SETTLEMENT_FAILURE` (Clearing House Delivery NACK)
* **Root Cause**: RTGS clearing hub rejected settlement instruction due to participant technical outage or invalid message hash.
* **Resolution**: Verify participant network status $\rightarrow$ regenerate SHA-256 digital signature $\rightarrow$ re-submit to clearing rail.

### 6. `FUNDS_TRAPPED_AT_CORRESPONDENT` (Intermediary Liquidity Staging)
* **Root Cause**: Funds credited to intermediary Nostro account but forward dispatch to beneficiary bank stalled.
* **Resolution**: Issue automated SWIFT `camt.027` (Claim for Non-Receipt) or `camt.087` (Request for Status Modification) to intermediary operations desk.

### 7. `UNMATCHED_CREDIT` (Inbound pacs.008 Without Internal Account)
* **Root Cause**: Inbound payment arrived for which no active internal customer DDA / Virtual Account exists.
* **Resolution**: Query Master Customer Directory for historical name variations $\rightarrow$ if verified, route to target account; otherwise initiate `pacs.004` return within statutory 24-hour window.
