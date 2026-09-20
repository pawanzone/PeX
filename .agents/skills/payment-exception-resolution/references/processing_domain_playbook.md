# SME Playbook: Processing Exception Domain (9 Profiles)
**Domain Reference**: `BIAN-PROC-DOM-02`  
**Governing Standards**: ISO 20022 XML Schema Validation (XSD), SWIFT CBPR+ Clearing Rules, High-Value Clearing Rail Cutoffs (Fedwire / CHIPS / TARGET2 / CHAPS)  
**Assigned Queue**: `Investigation / Repair Queue`  
**Default Roles**: Payment Operations Analysts, Network Operations Engineers, Operations Approvers

---

## 1. Executive Summary & Domain Scope

The **Processing Domain** encompasses lifecycle errors occurring within message serialization, parsing, transport, duplicate burst detection, clearing rail network timeouts, and cutoff schedule adherence.

---

## 2. 9 Detailed Exception Profiles & SME Resolution Logic

### 1. `DUPLICATE_PAYMENT` (Burst / Replay Attack Suspected)
* **Detection Vector**: Same Creditor + Amount + Remittance + $\Delta t \le 30\text{m}$.
* **SME Heuristic**: Disambiguate ERP network retries (True Duplicate $\rightarrow$ Reject) from legitimate scheduled payroll / retainer runs (Release).

### 2. `ROUTING_FAILURE` (No Viable Clearing Corridor)
* **Root Cause**: Instruction specified an unreachable intermediary corridor or unsupported clearing currency rail.
* **SME Heuristic**: Evaluate alternative correspondent clearing hops via Nostro routing engine $\rightarrow$ re-route via active intermediary holding bank.

### 3. `ISO20022_VALIDATION_ERROR` (XSD Syntax / Schema Break)
* **Root Cause**: XML tag ordering error, forbidden character escaping (e.g. raw `&` instead of `&amp;`), or schema length violation.
* **SME Heuristic**: Execute canonical XSD schema sanitizer $\rightarrow$ strip unescaped control chars and align tag sequence to CBPR+ standard.

### 4. `CUTOFF_MISSED` (Clearing Window Expired)
* **Root Cause**: Instruction arrived after national central bank RTGS gross settlement cutoff (e.g. Target2 18:00 CET, Fedwire 18:30 EST).
* **SME Heuristic**: Flag for **Overnight Value-Date Roll** (Value Date $= T+1$) or re-route to 24/7 instant cross-border rail (e.g. FedNow / SEPA Instant).

### 5. `CORRUPTED_MESSAGE_FORMAT` (Encoding / Truncation Break)
* **Root Cause**: UTF-8 vs ASCII code-page mismatch, truncated payload buffer from legacy mainframe adapter.
* **SME Heuristic**: Extract raw message from upstream archive $\rightarrow$ re-encode into canonical UTF-8 XML document.

### 6. `INTERMEDIARY_BANK_REJECTION` (NACK from Clearing Hop)
* **Root Cause**: Intermediary correspondent bank rejected instruction (`pacs.002` negative acknowledgment) due to internal corridor restrictions.
* **SME Heuristic**: Inspect `pacs.002` `<StsRsnInf>` error code $\rightarrow$ substitute with alternate correspondent clearing partner.

### 7. `NETWORK_TIMEOUT` (SWIFT gpi / Rail ACK Timeout)
* **Root Cause**: Outbound message dispatched but no confirmation ACK received within SLA window ($\Delta t > 15\text{ mins}$).
* **SME Heuristic**: Query SWIFT gpi Tracker API via UETR $\rightarrow$ verify if message in-flight (Avoid double dispatch) or trigger governed resend.

### 8. `QUEUE_PROCESSING_FAILURE` (Internal Engine Deadlock)
* **Root Cause**: Message stuck in message broker dead-letter queue (DLQ) due to transient database lock or memory bottleneck.
* **SME Heuristic**: Re-validate transaction state $\rightarrow$ release from DLQ and replay into execution pipeline.

### 9. `PAYMENT_HELD_FOR_REPAIR` (Manual Operations Staging)
* **Root Cause**: Upstream core banking engine flagged instruction for manual operator intervention prior to clearing submission.
* **SME Heuristic**: Review exception audit flags $\rightarrow$ execute requested manual field fine-tuning $\rightarrow$ submit to Checker.
