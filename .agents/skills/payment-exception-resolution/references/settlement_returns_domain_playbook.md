# SME Playbook: Settlement & Returns Exception Domain (7 Profiles)
**Domain Reference**: `BIAN-SETT-DOM-05`  
**Governing Standards**: ISO 20022 `pacs.004.001.09` (Payment Return), `camt.056` (Payment Cancellation Request), `pacs.002` (Payment Status Report), SWIFT Exception & Investigation (E&I)  
**Assigned Queue**: `Settlement / Returns Queue`  
**Default Roles**: Cash Management Operations, Reconciliation Specialists, Settlement Officers

---

## 1. Executive Summary & Domain Scope

The **Settlement & Returns Domain** resolves post-dispatch failures, rejected clearing deliveries, beneficiary account freezes, correspondent trapping, and ledger reconciliation breaks.

---

## 2. 7 Detailed Exception Profiles & SME Resolution Logic

### 1. `RETURNED_PAYMENT` (Generic pacs.004 Return Arrival)
* **Root Cause**: Receiving bank returned funds via `pacs.004` message.
* **SME Heuristic**: Parse return reason code $\rightarrow$ reconcile principal vs charges deducted $\rightarrow$ re-credit originator escrow account.

### 2. `ACCOUNT_CLOSED` (ISO Return Code `AC04`)
* **Root Cause**: Beneficiary account closed by receiving bank prior to wire arrival.
* **SME Heuristic**: Hold funds in suspense $\rightarrow$ generate automated secure inquiry to debtor treasury requesting active replacement beneficiary account $\rightarrow$ re-dispatch.

### 3. `BENEFICIARY_ACCOUNT_FROZEN` (ISO Return Code `AC06`)
* **Root Cause**: Beneficiary account blocked due to legal garnishment, insolvency proceedings, or court order.
* **SME Heuristic**: Refund net principal to debtor account $\rightarrow$ generate formal legal notice advice to customer.

### 4. `RECONCILIATION_BREAK` (Internal Ledger vs Bank Statement Mismatch)
* **Root Cause**: `camt.053` bank statement end-of-day balance does not match internal settlement subledger entry.
* **SME Heuristic**: Run automated 3-way matching algorithm (UETR, amount, value date) $\rightarrow$ isolate missing ledger leg $\rightarrow$ generate balancing posting.

### 5. `SETTLEMENT_FAILURE` (Clearing House Delivery NACK)
* **Root Cause**: RTGS clearing hub rejected settlement instruction due to participant technical outage or invalid message hash.
* **SME Heuristic**: Verify participant network status $\rightarrow$ regenerate SHA-256 digital signature $\rightarrow$ re-submit to clearing rail.

### 6. `FUNDS_TRAPPED_AT_CORRESPONDENT` (Intermediary Liquidity Staging)
* **Root Cause**: Funds credited to intermediary Nostro account but forward dispatch to beneficiary bank stalled.
* **SME Heuristic**: Issue automated SWIFT `camt.027` (Claim for Non-Receipt) or `camt.087` (Request for Status Modification) to intermediary operations desk.

### 7. `UNMATCHED_CREDIT` (Inbound pacs.008 Without Internal Account)
* **Root Cause**: Inbound payment arrived for which no active internal customer DDA / Virtual Account exists.
* **SME Heuristic**: Query Master Customer Directory for historical name variations $\rightarrow$ if verified, route to target account; otherwise initiate `pacs.004` return within statutory 24-hour window.
