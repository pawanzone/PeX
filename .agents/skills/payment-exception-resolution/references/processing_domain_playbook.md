# SME Playbook: Processing Exception Domain (9 Profiles)
**Domain Reference**: `BIAN-PROC-DOM-02`  
**Governing Standards**: ISO 20022 XML Schema Validation (XSD), SWIFT CBPR+ Clearing Rules, High-Value Clearing Rail Cutoffs (Fedwire / CHIPS / TARGET2 / CHAPS / SEPA)  
**Assigned Queue**: `Investigation / Repair Queue`  
**Default Roles**: Payment Operations Analysts, Network Operations Engineers, Operations Approvers

---

## 1. Executive Summary & Domain Scope

The **Processing Domain** encompasses message serialization, XML parsing, routing corridors, duplicate burst detection, clearing network timeouts, and cutoff schedule adherence across real-time gross settlement (RTGS) networks.

---

## 2. 4-Point Duplicate Evaluation & Burst Detection Matrix

The decision engine compares incoming transactions against the active 30-day settlement index using a 4-point verification vector:

| Comparison Vector | Exact Match Criteria | Tolerance / Variance Allowed |
| :--- | :--- | :--- |
| **Vector 1: Beneficiary Entity** | Creditor Account Number / IBAN + Name Token | 0% variance (Exact Match) |
| **Vector 2: Remittance Reference** | Invoice Number / Payment Reference Tag | 0% variance (e.g. `INV-2026-8891`) |
| **Vector 3: Exact Monetary Amount** | Value in Settlement Currency | 0% variance (e.g. `AUD 3,274,920.10`) |
| **Vector 4: Ingestion Time Window** | Timestamp differential $\Delta t$ | $\Delta t \le 30\text{ minutes}$ $\rightarrow$ Immediate Duplicate Alert |

### Duplicate Disambiguation Decision Logic
* **ERP Network Retry (True Duplicate)**: Same UETR prefix or same invoice within $< 15\text{ mins}$ $\rightarrow$ **REJECT & SUPPRESS** duplicate.
* **Recurring Payroll / Retainer Run (Legitimate Batch)**: Matching calendar period cadence $\rightarrow$ **RELEASE** with Maker-Checker confirmation.
* **Multi-Tranche Contract Milestone (Legitimate)**: Validated commercial tranche schedule $\rightarrow$ **RELEASE**.

```json
{
  "duplicate_check": {
    "vector_match_score": 1.0,
    "time_delta_seconds": 184,
    "original_payment_ref": "PAY-2026-004821",
    "duplicate_payment_ref": "PAY-2026-004822",
    "recommendation": "SUPPRESS_DUPLICATE",
    "rationale": "Identical amount ($45,200.00) and invoice reference (INV-2026-902) received within 3.1 minutes of initial settlement."
  }
}
```

---

## 3. Clearing Rail Cutoff Windows & Overnight Roll Protocols

| Clearing Rail | Currency | Cutoff Window (Local Time) | Late Wire Action Protocol |
| :--- | :--- | :--- | :--- |
| **TARGET2** | EUR | 18:00 CET | Automatic Value Date Roll ($T+1$) or SEPA Instant re-route |
| **CHAPS** | GBP | 17:30 GMT | Automatic Value Date Roll ($T+1$) or Faster Payments switch |
| **Fedwire** | USD | 18:30 EST | Automatic Value Date Roll ($T+1$) or FedNow instant transfer |
| **CHIPS** | USD | 17:00 EST | Convert to Fedwire Funds Service |

---

## 4. 9 Detailed Exception Profiles & SME Resolution Logic

### 1. `DUPLICATE_PAYMENT` (Burst / Replay Attack Suspected)
* **Detection Vector**: Same Creditor + Amount + Remittance + $\Delta t \le 30\text{m}$.
* **Resolution**: Disambiguate ERP network retries (True Duplicate $\rightarrow$ Reject) from legitimate scheduled payroll / retainer runs (Release).

### 2. `ROUTING_FAILURE` (No Viable Clearing Corridor)
* **Root Cause**: Instruction specified an unreachable intermediary corridor or unsupported clearing currency rail.
* **Resolution**: Evaluate alternative correspondent clearing hops via Nostro routing engine $\rightarrow$ re-route via active intermediary holding bank.

### 3. `ISO20022_VALIDATION_ERROR` (XSD Syntax / Schema Break)
* **Root Cause**: XML tag ordering error, forbidden character escaping (e.g. raw `&` instead of `&amp;`), or schema length violation.
* **Resolution**: Execute canonical XSD schema sanitizer $\rightarrow$ strip unescaped control chars and align tag sequence to CBPR+ standard.

### 4. `CUTOFF_MISSED` (Clearing Window Expired)
* **Root Cause**: Instruction arrived after national central bank RTGS gross settlement cutoff.
* **Resolution**: Flag for **Overnight Value-Date Roll** (Value Date $= T+1$) or re-route to 24/7 instant cross-border rail.

### 5. `CORRUPTED_MESSAGE_FORMAT` (Encoding / Truncation Break)
* **Root Cause**: UTF-8 vs ASCII code-page mismatch, truncated payload buffer from legacy mainframe adapter.
* **Resolution**: Extract raw message from upstream archive $\rightarrow$ re-encode into canonical UTF-8 XML document.

### 6. `INTERMEDIARY_BANK_REJECTION` (NACK from Clearing Hop)
* **Root Cause**: Intermediary correspondent bank rejected instruction (`pacs.002` negative acknowledgment) due to internal corridor restrictions.
* **Resolution**: Inspect `pacs.002` `<StsRsnInf>` error code $\rightarrow$ substitute with alternate correspondent clearing partner.

### 7. `NETWORK_TIMEOUT` (SWIFT gpi / Rail ACK Timeout)
* **Root Cause**: Outbound message dispatched but no confirmation ACK received within SLA window ($\Delta t > 15\text{ mins}$).
* **Resolution**: Query SWIFT gpi Tracker API via UETR $\rightarrow$ verify if message in-flight (avoid double dispatch) or trigger governed resend.

### 8. `QUEUE_PROCESSING_FAILURE` (Internal Engine Deadlock)
* **Root Cause**: Message stuck in message broker dead-letter queue (DLQ) due to transient database lock or memory bottleneck.
* **Resolution**: Re-validate transaction state $\rightarrow$ release from DLQ and replay into execution pipeline.

### 9. `PAYMENT_HELD_FOR_REPAIR` (Manual Operations Staging)
* **Root Cause**: Upstream core banking engine flagged instruction for manual operator intervention prior to clearing submission.
* **Resolution**: Review exception audit flags $\rightarrow$ execute requested manual field fine-tuning $\rightarrow$ submit to Checker.
