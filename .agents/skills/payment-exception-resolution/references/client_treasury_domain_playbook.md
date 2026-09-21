# SME Playbook: Client & Treasury Exception Domain (8 Profiles)
**Domain Reference**: `BIAN-TREA-DOM-04`  
**Governing Standards**: Basel III Intraday Liquidity Monitoring (BCBS 248), Wolfsberg Group AML / CDD Principles, ISO 20022 camt.052 / camt.053 Real-Time Balance Reporting, FX Global Code  
**Assigned Queue**: `Treasury / Risk Queue`  
**Default Roles**: Treasury Liquidity Managers, Risk Approvers (Kenji Watanabe), Relationship Managers

---

## 1. Executive Summary & Domain Scope

The **Client & Treasury Domain** manages intraday liquidity adequacy, Nostro account positioning, foreign exchange rate availability, corporate mandate authorizations, and counterparty credit lines.

---

## 2. Customer Due Diligence (CDD) Review Cycles & Provisional Waivers (SOP-302)

| Counterparty Risk Category | Mandatory Review Frequency | Grace Period Allowed | Waiver Eligibility |
| :--- | :--- | :---: | :---: |
| **Low Risk (Tier 1 Corporates)** | Every 36 Months | 30 Calendar Days | Eligible for 1-time 30-day provisional waiver |
| **Medium Risk (Commercial SMEs)** | Every 24 Months | 15 Calendar Days | Eligible with Relationship Manager sign-off |
| **High Risk / PEP / Correspondent**| Every 12 Months | 0 Days (Hard Freeze) | Ineligible for waiver — Full KYC refresh required |

### 4 Criteria for Granting 30-Day Provisional KYC Waiver
1. **Active Refresh in Progress**: Onboarding team formally initiated documentation refresh within preceding 14 days.
2. **Clean Historical Conduct**: Zero Suspicious Activity Reports (SARs) or regulatory inquiries in preceding 24 months.
3. **Low-Risk Corridor**: Payment corridor (e.g. USD/EUR, GBP/AUD) involves zero FATF high-risk jurisdictions.
4. **Exposure Gating**: If wire amount $\ge \$250,000.00$, mandatory Tier-2 Dual Authorization by Risk Approver (`Kenji Watanabe`) is enforced.

```json
{
  "kyc_waiver_assessment": {
    "case_id": "PEX-INV-0042",
    "counterparty_name": "Apex Global Treasury (US)",
    "risk_tier": "LOW_RISK_TIER_1",
    "cdd_last_completed": "2023-08-15",
    "clean_history_months": 36,
    "provisional_waiver_granted": true,
    "waiver_duration_days": 30,
    "dual_auth_required": false,
    "action_type": "GRANT_KYC_WAIVER",
    "approver_role": "COMPLIANCE_APPROVER"
  }
}
```

---

## 3. Intraday Nostro Liquidity Positioning & FX Binding

* **Intraday Nostro Sweep**: Trigger automated sweep from central reserve pool when local Nostro balance drops below settlement threshold.
* **FX Rate Binding**: For cross-currency wires where primary rate server timed out, bind live market quote from backup liquidity aggregator within $\pm 2\text{ bps}$ of mid-market.

---

## 4. 8 Detailed Exception Profiles & SME Resolution Logic

### 1. `KYC_EXPIRED` (Periodic CDD Past Due)
* **Root Cause**: Periodic Customer Due Diligence review past due.
* **Resolution**: Apply `SOP-302` criteria: Low-risk corporate + clean 24-month conduct + refresh underway $\rightarrow$ grant 30-day provisional waiver.

### 2. `INSUFFICIENT_FUNDS` (Debtor Ledger Shortfall)
* **Root Cause**: Ordering customer account balance is insufficient to cover wire amount plus clearing fees.
* **Resolution**: Check corporate daylight overdraft line or intraday credit facility. If covered $\rightarrow$ execute temporary liquidity hold release; otherwise hold for end-of-day deposit.

### 3. `NOSTRO_SHORTFALL` (Corridor Liquidity Deficit)
* **Root Cause**: Bank's own Nostro account at destination correspondent lacks sufficient currency balance to settle the outgoing gross wire.
* **Resolution**: Trigger automated **Intraday Nostro Sweep** from central liquidity pool or execute FX spot swap to fund corridor $\rightarrow$ release wire.

### 4. `FX_RATE_UNAVAILABLE` (Cross-Currency Rate Lock Failure)
* **Root Cause**: FX rate service timed out or currency market closed for non-deliverable cross-currency pair.
* **Resolution**: Fetch fallback live market quote from secondary FX aggregator $\rightarrow$ bind guaranteed rate quote $\rightarrow$ re-calculate settlement amount.

### 5. `AUTHORIZATION_MISSING` (Corporate Mandate Sign-Off Incomplete)
* **Root Cause**: Commercial customer ERP initiated payment without required secondary corporate officer digital signature under company banking mandate.
* **Resolution**: Generate secure automated authorization request to corporate treasury portal $\rightarrow$ release upon signature capture.

### 6. `LIMIT_BREACH` (Single Transaction / Daily Cap Exceeded)
* **Root Cause**: Wire amount exceeds corporate customer's authorized single-wire limit or daily aggregate ceiling.
* **Resolution**: Route to Corporate Relationship Manager and Risk Approver for temporary one-off limit exception authorization.

### 7. `LIQUIDITY_CONSTRAINT` (Intraday Central Bank Reserve Target)
* **Root Cause**: Outbound high-value wire would breach bank's intraday minimum reserve buffer at central bank.
* **Resolution**: Queue payment for next clearing cycle window (Netting batch) to optimize liquidity outflow.

### 8. `CREDIT_EXPOSURE_BREACH` (Counterparty Credit Risk Threshold)
* **Root Cause**: Total unsettled exposure to beneficiary financial institution exceeds risk management ceiling.
* **Resolution**: Verify collateral margin $\rightarrow$ route to Credit Risk Officer for margin release approval.
