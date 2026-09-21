# SME Playbook: Client & Treasury Exception Domain (8 Profiles)
**Domain Reference**: `BIAN-TREA-DOM-04`  
**Governing Standards**: Basel III Intraday Liquidity Monitoring (BCBS 248), ISO 20022 camt.052 / camt.053 Real-Time Balance Reporting, FX Global Code  
**Assigned Queue**: `Treasury / Risk Queue`  
**Default Roles**: Treasury Liquidity Managers, Risk Approvers (Kenji Watanabe), Relationship Managers

---

## 1. Executive Summary & Domain Scope

The **Client & Treasury Domain** manages intraday liquidity adequacy, Nostro account positioning, foreign exchange rate availability, corporate mandate authorizations, and counterparty credit lines.

---

## 2. 8 Detailed Exception Profiles & SME Resolution Logic

### 1. `KYC_EXPIRED` (Periodic CDD Past Due)
* **Root Cause**: Periodic Customer Due Diligence review past due.
* **SME Heuristic**: Apply `SOP-302` criteria: Low-risk corporate + clean 24-month conduct + refresh underway $\rightarrow$ grant 30-day provisional waiver.

### 2. `INSUFFICIENT_FUNDS` (Debtor Ledger Shortfall)
* **Root Cause**: Ordering customer account balance is insufficient to cover wire amount plus clearing fees.
* **SME Heuristic**: Check corporate daylight overdraft line or intraday credit facility. If covered by facility $\rightarrow$ execute temporary liquidity hold release; otherwise hold for end-of-day deposit.

### 3. `NOSTRO_SHORTFALL` (Corridor Liquidity Deficit)
* **Root Cause**: Bank's own Nostro account at destination correspondent lacks sufficient currency balance to settle the outgoing gross wire.
* **SME Heuristic**: Trigger automated **Intraday Nostro Sweep** from central liquidity pool or execute FX spot swap to fund corridor $\rightarrow$ release wire.

### 4. `FX_RATE_UNAVAILABLE` (Cross-Currency Rate Lock Failure)
* **Root Cause**: FX rate service timed out or currency market closed for non-deliverable cross-currency pair.
* **SME Heuristic**: Fetch fallback live market quote from secondary FX aggregator $\rightarrow$ bind guaranteed rate quote $\rightarrow$ re-calculate settlement amount.

### 5. `AUTHORIZATION_MISSING` (Corporate Mandate Sign-Off Incomplete)
* **Root Cause**: Commercial customer ERP initiated payment without required secondary corporate officer digital signature under company banking mandate.
* **SME Heuristic**: Generate secure automated authorization request to corporate treasury portal $\rightarrow$ release upon signature capture.

### 6. `LIMIT_BREACH` (Single Transaction / Daily Cap Exceeded)
* **Root Cause**: Wire amount exceeds corporate customer's authorized single-wire limit or daily aggregate ceiling.
* **SME Heuristic**: Route to Corporate Relationship Manager and Risk Approver for temporary one-off limit exception authorization.

### 7. `LIQUIDITY_CONSTRAINT` (Intraday Central Bank Reserve Target)
* **Root Cause**: Outbound high-value wire would breach bank's intraday minimum reserve buffer at central bank.
* **SME Heuristic**: Queue payment for next clearing cycle window (Netting batch) to optimize liquidity outflow.

### 8. `CREDIT_EXPOSURE_BREACH` (Counterparty Credit Risk Threshold)
* **Root Cause**: Total unsettled exposure to beneficiary financial institution exceeds risk management ceiling.
* **SME Heuristic**: Verify collateral margin $\rightarrow$ route to Credit Risk Officer for margin release approval.
