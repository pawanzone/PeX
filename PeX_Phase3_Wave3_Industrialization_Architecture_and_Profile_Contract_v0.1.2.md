# PeX Phase 3 — Wave 3 Industrialization Architecture & Profile Contract
## Architecture, Semantic Contracts, Authority Requirements, and Resolution Patterns for Wave 3 Profiles (TR-02, TR-03, TR-04, TR-06, TR-07, TR-08)

**Document Version:** v0.1.2 (Freeze-Ready Remediated Architecture Baseline)  
**Status:** WAVE 3 ARCHITECTURE & PROFILE CONTRACT — REMEDIATED / READY FOR AUTHORIZATION REVIEW  
**Governance Authority:** Principal Architecture, Governance, and Forensic Design Authority  
**Repository Working Directory:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Git Baseline:** Branch `phase3/wave2-implementation` | Tag `pex-phase3-wave2-20261008`  
**Cumulative Test Baseline:** 726 passed / 0 failed / 3 warnings (Inherited Baseline from Prior Waves)  
**Engineering Implementation Authorization:** **STRICTLY NOT GRANTED BY THIS DOCUMENT**  
**Wave 3 Implementation Status:** **NOT STARTED / NOT AUTHORIZED**  
**Production Autonomous STP Authorization:** **STRICTLY BLOCKED**  
**Execution Ownership Boundary:** `execution_owner = "BANK"` (Mandatory across all outputs)  

---

## 1. Executive Summary

### 1.1 Context & Industrialization Lineage
The PeX (Payment Exception Resolution) platform has progressively industrialized prior wave baselines:
1. **Phase 2 Baseline**: 11 canonical profiles (`DQ-01`, `DQ-02`, `DQ-05`, `DQ-06`, `DQ-08`, `PR-01`, `PR-03`, `PR-05`, `PR-08`, `CO-04`, `ST-01`) backed by 423 regression tests (Closed & Frozen).
2. **Wave 0A Baseline**: Platform contracts, canonical schemas, reference adapters, and Scenarios 1–12.
3. **Wave 0B Baseline**: Dynamic Bank Evidence Required JSON, fail-closed governance compilation, content-addressable SHA-256 evidence store, Modes 1–4 acquisition, PeX-native HITL closed loop, and Scenarios 13–18.
4. **Wave 1 Baseline**: 9 canonical profiles (`DQ-03`, `DQ-04`, `DQ-07`, `DQ-09`, `PR-02`, `PR-04`, `PR-07`, `PR-09`, `CO-07`) across `AccountMasterEngine`, `RoutingClearingEngine`, and `RemittanceDocumentEngine`, backed by 630 regression tests (Signed Off under `PeX_Wave1_Multi_Profile_Semantic_Reconciliation_and_Governance_Signoff_v0.1.1.md`).
5. **Wave 2 Baseline**: 3 canonical profiles (`PR-06`, `ST-02`, `ST-03`) across `SettlementReconciliationEngine` and `AccountMasterEngine`, introducing 4 SPI ports, 6 E2E canonical scenarios (Scenarios 28A–30B), 96 dedicated tests (726 cumulative tests green). Implementation complete; governance sign-off ready with conditions under `PeX_Wave2_Multi_Profile_Semantic_Reconciliation_and_Governance_Signoff_v0.1.2.md`.

### 1.2 Purpose of This Document
This document establishes the authoritative, freeze-ready **Architecture and Profile Contract** for **Phase 3 Wave 3**. Wave 3 addresses the **Treasury, Liquidity, and Exposure Management** domain by specifying **EXACTLY SIX** canonical exception profiles under the primary ownership of the existing **`TreasuryExposureEngine`**:

1. `TR-02` — **Insufficient Funds**
2. `TR-03` — **Nostro Shortfall**
3. `TR-04` — **FX Rate Unavailable**
4. `TR-06` — **Limit Breach**
5. `TR-07` — **Liquidity Constraint**
6. `TR-08` — **Credit Exposure Breach**

> [!IMPORTANT]
> **GOVERNANCE MATURITY INVARIANT:**  
> $$\text{Architecture Validated} \neq \text{Implementation Validated} \neq \text{Forensic Acceptance} \neq \text{Governance Sign-Off} \neq \text{Production Release}$$  
> This artifact defines the architectural specifications, semantic boundaries, evidence contracts, provider-neutral SPI ports, policy envelopes, and provisional resolution patterns for Wave 3. It serves as the controlling architecture baseline for the subsequent `PeX_Wave3_Implementation_Authorization_Gate_v0.1.md`. **Engineering implementation authorization is strictly NOT granted by this document.**

---

## 2. Governance Status

```
+----------------------------------------------------------------------------------------------------+
|                                  WAVE 3 GOVERNANCE STATUS SUMMARY                                  |
+-----------------------------------+----------------------------------------------------------------+
| Governance Dimension              | Status & Operational Boundary                                  |
+-----------------------------------+----------------------------------------------------------------+
| Phase 2 Baseline (11 Profiles)    | CLOSED & FROZEN (Strict No-Reengineering Protection)           |
| Wave 0A / Wave 0B Baseline        | COMPLETE (Platform Contracts & Dynamic Engine Layer Frozen)    |
| Wave 1 Baseline (9 Profiles)      | COMPLETE & SIGNED OFF (Signed off under MPSR-GS v0.1.1)        |
| Wave 2 Baseline (3 Profiles)      | IMPLEMENTATION COMPLETE (Ready with Conditions under v0.1.2)   |
| Wave 3 Engineering Authorization  | STRICTLY NOT GRANTED (Requires separate Authorization Gate)    |
| Wave 3 Implementation Status      | NOT STARTED / NOT AUTHORIZED                                   |
| Production Autonomous STP Gate    | STRICTLY BLOCKED (Zero-touch autonomous release forbidden)    |
| Execution Ownership Boundary      | execution_owner = "BANK" (Mandatory across all outputs)        |
| Cumulative Verified Tests         | 726 passed / 0 failed / 3 warnings (Inherited from Prior Waves)|
| Active Reconciled Profiles        | 23 Profiles (11 Phase 2 + 9 Wave 1 + 3 Wave 2)                |
| Wave 3 Target Scope               | EXACTLY 6 Profiles: TR-02, TR-03, TR-04, TR-06, TR-07, TR-08  |
| Primary Engine Exercised          | TreasuryExposureEngine (Primary for all 6 Wave 3 Profiles)     |
| Supporting Engines Exercised      | AccountMasterEngine, RoutingClearingEngine, ComplianceDossier, |
|                                   | SettlementReconciliationEngine                                 |
| Closed Canonical Universe         | EXACTLY 41 Profiles (23 Active + 18 Remaining = 41 Total)      |
+-----------------------------------+----------------------------------------------------------------+
```

---

## 3. Authoritative Source Precedence

In accordance with Section 3 of the Phase 3 Delivery Charter, all architectural determinations, authority boundaries, and resolution patterns in this document are governed strictly by the following hierarchy:

```mermaid
flowchart TD
    H1["1. PeX Evidence-Driven STP Architecture Baseline v1.1"] --> H2["2. PeX Phase 3 Industrialization Architecture v0.1.4"]
    H2 --> H3["3. PeX Phase 3 Governance & Delivery Charter v0.2"]
    H3 --> H4["4. PeX Wave 2 Multi-Profile Semantic Reconciliation v0.1.2 (FROZEN)"]
    H4 --> H5["5. PeX Phase 3 Wave 2 Architecture & Profile Contract v0.1.2 (FROZEN)"]
    H5 --> H6["6. PeX Wave 2 Implementation Authorization Gate v0.1.1 (FROZEN)"]
    H6 --> H7["7. PeX Wave 2 Implementation Report v0.1.1 (Evidence Baseline)"]
    H7 --> H8["8. PeX Wave 2 Independent Forensic Acceptance Red-Team Review v0.1.1"]
    H8 --> H9["9. PeX Wave 1 Multi-Profile Semantic Reconciliation v0.1.1"]
    H9 --> H10["10. Repository State (Evidence of Current Software Capability Only)"]
```

---

## 4. Wave 3 Scope & Closed Canonical Taxonomy

Wave 3 encompasses **EXACTLY SIX** canonical exception profiles within the Client/Treasury domain:

```
+---------------------------------------------------------------------------------------------------------------------------+
|                                                   WAVE 3 PROFILE SCOPE                                                    |
+-------+-----------------------------+-------------------------------+------------------------------+----------------------+
| Code  | Canonical Profile Name      | Primary Capability Engine     | Supporting Capability        | Provisional Pattern  |
+-------+-----------------------------+-------------------------------+------------------------------+----------------------+
| TR-02 | Insufficient Funds          | TreasuryExposureEngine        | AccountMasterEngine          | PAT-C [PROPOSED]     |
| TR-03 | Nostro Shortfall            | TreasuryExposureEngine        | SettlementReconciliationEng  | PAT-C [PROPOSED]     |
| TR-04 | FX Rate Unavailable         | TreasuryExposureEngine        | RoutingClearingEngine        | PAT-C [PROVISIONAL]  |
| TR-06 | Limit Breach                | TreasuryExposureEngine        | ComplianceDossierEngine      | PAT-C / D [PROVISION]|
| TR-07 | Liquidity Constraint        | TreasuryExposureEngine        | RoutingClearingEngine        | PAT-C [PROPOSED]     |
| TR-08 | Credit Exposure Breach      | TreasuryExposureEngine        | ComplianceDossierEngine      | PAT-D [PROVISIONAL]  |
+-------+-----------------------------+-------------------------------+------------------------------+----------------------+
```

### Taxonomy Invariants:
- **Scope Integrity**: Wave 3 consists **ONLY** of `TR-02`, `TR-03`, `TR-04`, `TR-06`, `TR-07`, and `TR-08`.
- **Other Waves Protected**: `TR-01`, `TR-05`, and `ST-06` belong strictly to Wave 4. `CO-01`, `CO-02`, `CO-03`, `CO-05`, `CO-06`, and `CO-08` belong strictly to Wave 5. `ST-04`, `ST-05`, and `ST-07` belong strictly to Wave 6.
- **Closed 41-Profile Universe**: No other profiles exist. The 41 canonical profiles break down into **23 active profiles** (Phase 2, Wave 1, Wave 2) and **18 remaining profiles** (Waves 3, 4, 5, 6).

---

## 5. Critical Treasury Semantic Discipline & Epistemic Separation

To prevent domain model collapse and unauthorized semantic promotion, PeX strictly separates architectural layers:

```
CANONICAL PROFILE MEANING
        ↓
ARCHITECTURE FACT
        ↓
CANDIDATE RESOLUTION
        ↓
EVIDENCE REQUIREMENT
        ↓
AUTHORITY REQUIREMENT
        ↓
BANK POLICY
        ↓
ILLUSTRATIVE / TEST VALUE
        ↓
PRODUCTION INTEGRATION DEPENDENCY
        ↓
OPEN DECISION
```

```mermaid
flowchart TD
    subgraph ClientLevel["Client / Account Level"]
        TR02["TR-02: Insufficient Funds\n(Debtor Available Funding Deficit)"]
        TR06["TR-06: Limit Breach\n(Applicable Configured Operational Limit Exceeded)"]
    end

    subgraph CorrespondentLevel["Correspondent / Corridor Level"]
        TR03["TR-03: Nostro Shortfall\n(Correspondent Account Settlement Capacity Shortfall)"]
        TR04["TR-04: FX Rate Unavailable\n(Required Currency Pair Pricing Quote Missing / Stale / Out of Tolerance)"]
    end

    subgraph EnterpriseLevel["Enterprise / Liquidity / Credit Level"]
        TR07["TR-07: Liquidity Constraint\n(Available Liquidity Insufficient Across Applicable Context)"]
        TR08["TR-08: Credit Exposure Breach\n(Applicable Credit Ceiling / Facility / Counterparty Exposure Exceeded)"]
    end
```

### Granular Semantic Boundaries:
1. **`TR-02` (Insufficient Funds)**:
   - *Canonical Meaning*: Insufficient available funding relevant to the payment/account context to execute the payment instruction.
   - *Epistemic Boundaries*: DDA/Core Banking is an authority-source category or implementation example. Specific overdraft agreements, sweep mechanisms, and reason codes (e.g. MS03 / AM04) are illustrative test/rail references, not mandatory architectural semantics.
2. **`TR-03` (Nostro Shortfall)**:
   - *Canonical Meaning*: Insufficient available settlement balance or funding capacity in the bank's Nostro/correspondent clearing context in the target currency corridor.
   - *Epistemic Boundaries*: Message formats (such as `camt.053`), specific sweep accounts, and target operating balances are illustrative bank policy or production integration dependencies. PeX derives a governed rebalancing/pacing candidate and does not execute fund movements.
3. **`TR-04` (FX Rate Unavailable)**:
   - *Canonical Meaning*: Required foreign exchange conversion rate or pricing quote for a cross-currency payment is missing, expired/stale, outside tolerance bands, or unquoted.
   - *Epistemic Boundaries*: Specific time-to-live thresholds, spread tolerances, and currency amount caps are test/reference defaults subject to bank policy decisions. External market data feeds are illustrative candidate integrations.
4. **`TR-06` (Limit Breach)**:
   - *Canonical Meaning*: Payment instruction exceeds an applicable configured operational risk limit (e.g. account, client, corridor, product, channel, or transaction limit).
   - *Epistemic Boundaries*: The exact limit hierarchy and waiver thresholds are bank-defined. Operational limits are distinct from institutional counterparty credit facility limits (`TR-08`).
5. **`TR-07` (Liquidity Constraint)**:
   - *Canonical Meaning*: A liquidity constraint is a condition in which available liquidity relevant to payment processing or settlement is insufficient or otherwise constrained under the applicable bank, account, currency, portfolio, clearing, or settlement context.
   - *Epistemic Boundaries*: Central Bank RTGS reserve pacing is an **ILLUSTRATIVE / RAIL-SPECIFIC EXAMPLE** and not a universal definition. The architecture supports clearing liquidity, settlement liquidity, currency liquidity, portfolio liquidity, correspondent liquidity, reserve buffer, and other bank-defined liquidity constraints.
6. **`TR-08` (Credit Exposure Breach)**:
   - *Canonical Meaning*: Payment instruction causes total outstanding credit exposure to breach an applicable credit facility, counterparty ceiling, or institutional credit risk ceiling.
   - *Epistemic Boundaries*: **Autonomous STP approval or override of a credit exposure breach is prohibited.** All credit breaches require human credit officer adjudication. Human authorization re-evaluates all predicates to enable a governed bank handoff but does not confer direct execution authority to PeX.

---

## 6. Primary Capability Engine: `TreasuryExposureEngine` Architecture

The `TreasuryExposureEngine` is one of the **six primary capability engines** defined in the Phase 3 industrialization architecture:

```
+----------------------------------------------------------------------------------------------------+
|                               SIX PRIMARY CAPABILITY ENGINES (PHASE 3)                             |
+---+------------------------------+----------------------------------+------------------------------+
| # | Capability Engine            | Domain Authority                 | Industrialization Wave       |
+---+------------------------------+----------------------------------+------------------------------+
| 1 | AccountMasterEngine          | Account validity, status, CoP/VoP| Phase 2 / Wave 1 / Wave 2    |
| 2 | RoutingClearingEngine        | Clearing rails, cutoffs, hops    | Phase 2 / Wave 1             |
| 3 | RemittanceDocumentEngine     | Invoices, remittance, reporting  | Phase 2 / Wave 1             |
| 4 | ComplianceDossierEngine      | Sanctions, AML, legal dossiers   | Phase 2 / Wave 2 / Wave 5    |
| 5 | TreasuryExposureEngine       | Balance, Nostro, FX, limits, liq | Phase 3 Wave 3 (THIS WAVE)   |
| 6 | SettlementReconciliationEng  | Inward returns, reroute, suspense| Phase 2 / Wave 2             |
+---+------------------------------+----------------------------------+------------------------------+
```

### 6.1 `TreasuryExposureEngine` Core Responsibilities
- **Balance & Position Evaluation**: Evaluates real-time available balances vs. ledger balances and active intraday reservations based on authoritative evidence.
- **Nostro Position Evaluation**: Evaluates correspondent account positions, pending settlement credits, and candidate rebalancing packages.
- **FX Rate & Pricing Validation**: Evaluates market data rate quotes against freshness rules and configured spread tolerance bands.
- **Operational Limit Evaluation**: Evaluates transaction amounts against applicable configured limit definitions.
- **Liquidity Constraint Evaluation**: Evaluates available liquidity across applicable clearing, settlement, or currency contexts.
- **Credit Exposure Packaging**: Compiles credit risk exposure dossiers for human credit officer adjudication.
- **Pacing & Retry Candidate Derivation**: Derives governed queue pacing candidates for temporary intraday liquidity or limit reset cycles.

### 6.2 Strict Anti-Theft Boundaries for `TreasuryExposureEngine`
- **No Account Master Mutation**: Does not create, modify, or close accounts (belongs strictly to `AccountMasterEngine`).
- **No Clearing Rail Selection**: Does not determine clearing corridor reachability or intermediary BICs (belongs to `RoutingClearingEngine`).
- **No Sanctions Screening**: Does not adjudicate OFAC/AML sanctions alerts (belongs to `ComplianceDossierEngine`).
- **No Ledger Journal Mutation**: Does not post direct debits/credits or mutate core bank GLs (belongs to bank accounting systems).

### 6.3 Supporting Engine Roles for Wave 3 Profiles
```
+----------------------------------------------------------------------------------------------------+
|                               WAVE 3 SUPPORTING ENGINE ROLES MATRIX                                |
+-------+--------------------------+-----------------------------------------------------------------+
| Code  | Supporting Engine        | Specific Supporting Technical & Architectural Capability        |
+-------+--------------------------+-----------------------------------------------------------------+
| TR-02 | AccountMasterEngine      | May support validation of account standing, currency alignment, |
|       |                          | and reference overdraft / sweep mandate agreements where applied|
+-------+--------------------------+-----------------------------------------------------------------+
| TR-03 | SettlementReconciliation | May support correlation of settlement and position evidence     |
|       | Engine                   | (source format and delivery rail are bank-specific dependencies)|
+-------+--------------------------+-----------------------------------------------------------------+
| TR-04 | RoutingClearingEngine    | May support verification of clearing rail operating hours and   |
|       |                          | value-date settlement windows where cross-currency hops apply.  |
+-------+--------------------------+-----------------------------------------------------------------+
| TR-06 | ComplianceDossierEngine  | May support packaging operational limit waiver dossiers for     |
|       |                          | governed Credit Officer dual authorization where required.      |
+-------+--------------------------+-----------------------------------------------------------------+
| TR-07 | RoutingClearingEngine    | May support evaluating rail schedules and cutoff windows where  |
|       |                          | liquidity constraint relates to clearing rail queues.           |
+-------+--------------------------+-----------------------------------------------------------------+
| TR-08 | ComplianceDossierEngine  | Assembles formal credit exposure dossiers for human Senior      |
|       |                          | Credit Officer adjudication (Autonomous STP Prohibited).        |
+-------+--------------------------+-----------------------------------------------------------------+
```

---

## 7. Resolution Pattern Families & Wave 3 Provisional Mappings

The Phase 3 architecture defines **seven (7) bounded resolution pattern families**. Wave 3 profiles map provisionally into existing pattern families without pattern forcing:

```
+----------------------------------------------------------------------------------------------------+
|                                    RESOLUTION PATTERN FAMILIES                                     |
+---------+-----------------------------------+------------------------------------------------------+
| Family  | Pattern Family Name               | Bounded Sub-Behaviors & Scope                        |
+---------+-----------------------------------+------------------------------------------------------+
| PAT-A   | Reference, Rule & Structural      | Master DDA, Directory, Tag Derivation, CoP / Syntax. |
| PAT-B   | Temporal & Queue Recalculation    | Cutoff Date Roll (T+1), Socket Retry, Queue Unblock. |
| PAT-C   | Threshold & Balance Pacing Family | Balance Inquiry, Liquidity Pacing, Nostro Sweep Sync,|
|         |                                   | FX Spread Booking, and Intraday Limit Reset Pacing.  |
| PAT-D   | Compliance & Risk Dossier         | Legal Dossier Package, Sanctions, Credit Risk Dossier|
|         | Adjudication Family               | for Governed Human Dual-Authorization.               |
| PAT-E   | Ledger Matching & Settlement      | Return Matching, Return Packaging, GL Suspense Break.|
| PAT-F   | Intermediary & Claims Tracking    | Inward Reject Tracking, Alternate Hop Route.        |
| PAT-G   | Mandate & Entitlement Clearance   | Corporate Signatory Mandates, KYC Entitlements.      |
+---------+-----------------------------------+------------------------------------------------------+
```

### Wave 3 Provisional Resolution Pattern Allocations:
1. **`TR-02` (Insufficient Funds)**:
   - *Primary Pattern*: `PAT-C` (Threshold & Balance Pacing Family) `[PROPOSED]`
   - *Supporting Pattern*: `PAT-B` (Temporal Queue Recalculation) `[PROPOSED]`
2. **`TR-03` (Nostro Shortfall)**:
   - *Primary Pattern*: `PAT-C` (Threshold & Balance Pacing Family) `[PROPOSED]`
   - *Supporting Pattern*: `PAT-B` (Temporal Queue Recalculation) `[PROPOSED]`
3. **`TR-04` (FX Rate Unavailable)**:
   - *Primary Pattern*: `PAT-C` (Threshold & Balance Pacing Family) `[PROVISIONAL]`
   - *Supporting Pattern*: `PAT-A` (Reference Rule / Market Data Derivation) `[PROVISIONAL]`
4. **`TR-06` (Limit Breach)**:
   - *Composite Resolution*:
     - *Primary*: `PAT-C` (Threshold & Balance Pacing) `[PROVISIONAL]`
     - *Supporting / Escalation*: `PAT-D` (Risk Dossier Adjudication) `[PROVISIONAL]`
5. **`TR-07` (Liquidity Constraint)**:
   - *Primary Pattern*: `PAT-C` (Threshold & Balance Pacing Family) `[PROPOSED]`
   - *Supporting Pattern*: `PAT-B` (Temporal Queue Recalculation) `[PROPOSED]`
6. **`TR-08` (Credit Exposure Breach)**:
   - *Primary Pattern*: `PAT-D` (Compliance & Risk Dossier Adjudication Family) `[PROVISIONAL]`
   - *Supporting Pattern*: `PAT-C` (Threshold & Balance Tracking) `[PROVISIONAL]`

---

## 8. Reusable Treasury Capability Model

Wave 3 defines reusable, domain-generic capability components within `TreasuryExposureEngine`:

```
+----------------------------------------------------------------------------------------------------+
|                               REUSABLE TREASURY CAPABILITY INVENTORY                               |
+---+------------------------------------+----------------------------------+------------------------+
| # | Reusable Capability Component      | Functional Scope                 | Consuming Profiles     |
+---+------------------------------------+----------------------------------+------------------------+
| 1 | AvailableBalanceEvaluator          | Available funding vs ledger check| TR-02, TR-06           |
| 2 | NostroPositionEvaluator            | Correspondent balance & credits  | TR-03                  |
| 3 | FXRatePricingEvaluator             | Rate freshness & spread bounds   | TR-04                  |
| 4 | OperationalLimitEvaluator          | Configured limit rule evaluation | TR-06                  |
| 5 | CreditExposureEvaluator            | Credit exposure ceiling check    | TR-08                  |
| 6 | LiquidityConstraintEvaluator       | Liquidity constraint evaluation  | TR-07                  |
| 7 | PacingRetryCandidateDeriver        | Governed retry pacing candidate  | TR-02, TR-06, TR-07    |
| 8 | FundingCandidatePackager           | Funding / rebalancing candidate  | TR-03                  |
| 9 | RiskDossierAssembler               | Credit / risk waiver dossier     | TR-06, TR-08           |
| 10| TemporalCorrelationEvaluator       | Temporal reset & timing check    | TR-02, TR-04, TR-07    |
+---+------------------------------------+----------------------------------+------------------------+
```

---

## 9. Wave 3 Canonical Profile Contracts

### 9.1 TR-02 — Insufficient Funds

```
====================================================================================================
CANONICAL PROFILE CARD: TR-02 (Insufficient Funds)
====================================================================================================
Canonical Profile ID:       TR-02
Canonical Profile Name:     Insufficient Funds
Problem Meaning:            Inbound or outbound payment instruction exceeds the currently available
                            funding balance in the debtor / ordering customer account context.
Trigger Condition:          Authoritative balance inquiry returns available_balance < payment_amount,
                            or payment hub flags insufficient funds (e.g. illustrative MS03 / AM04 codes).
Primary Engine:             TreasuryExposureEngine
Supporting Engine(s):       AccountMasterEngine (optional validation of account standing & mandate agreements)
Resolution Pattern Family:  Primary: PAT-C (Threshold & Balance Pacing Family) [PROPOSED]
                            Supporting: PAT-B (Temporal Queue Recalculation) [PROPOSED]
Why Pattern Fits:           Evaluates available balance against bank intraday pacing policy. If expected
                            clearing credits or intraday funding buffers exist and amount <= policy threshold,
                            derives a governed pacing retry candidate (PAT-C). If deficit persists beyond
                            pacing window or overdraft is unauthorized, routes to internal HITL review.
Evidence Required:          AccountBalanceRecord (ledger_balance, available_balance, currency, as_of_timestamp),
                            IntradayReservationRecord (active_holds, pending_credits, available_headroom),
                            DeterministicCorrelationMatch (uetr, amount, currency, debtor_account).
Evidence Acquisition Modes: Mode 1 (Bank Pre-Supplied Position), Mode 2 (Authorized Automated System Query),
                            Mode 3 (Bank File/Feed), Mode 4 (Human-Assisted HITL Acquisition).
Evidence Trust Tier(s):     Tier 1 (Authoritative Core Banking / Accounting Ledger Position).
Resolution Determination:   R_det = True when either a valid pacing retry candidate is derived OR
                            an authorized funding candidate is derived. (False if unresolvable deficit).
Resolution Uniqueness:      R_uniq = True when single pacing schedule or single authorized funding account is resolved.
Technical Validation:       V_det = True when payment amount and currency align with account configuration.
Authority Validation:       V_auth = True when TreasuryPositionPort confirms authoritative position and
                            client agreement authorizes intraday queuing / overdraft buffer.
Bank Policy Dependency:     W3-BPD-01 attached to BankPolicyEnvelope:
                            - allow_auto_retry_pacing: True [TEST / REFERENCE CONFIGURATION]
                            - max_pacing_retry_seconds: 1800.0 [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
                            - min_available_balance_buffer: 0.0 [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
                            - max_auto_pacing_amount: 100000.0 [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
Compliance Dependency:      C_comp = True; account is in good standing and not subject to sanctions/fraud holds.
Execution Preconditions:    X_pre = True; account is active and clearing rail remains within operating window.
Non-Negotiable Boundaries:  1. Zero Direct Mutation: PeX derives pacing and reservation candidates; PeX does
                               NOT execute ledger debits, overdraft bookings, or payment releases directly.
                            2. AI Prohibition: AI has no decision authority and cannot synthesize balances.
HITL Trigger Conditions:    Deficit exceeds configured policy cap, pacing window expires without funding, missing account
                            authority, or account subject to administrative hold.
STP Automation Potential:   High (for policy-compliant temporary intraday timing mismatches with incoming credits).
STP Eligibility Condition:  E_suff ∧ R_det ∧ R_uniq ∧ V_det ∧ V_auth ∧ P_bank ∧ C_comp ∧ X_pre == True.
Bank Execution Boundary:    execution_owner = "BANK"; handoff reaches BANK_HANDOFF_READY only when all predicates True.
AI Role:                    Observational pattern matching on historical deposit timing only (no decision authority).
Semantic Status:            REMEDIATED SPECIFICATION (Pre-Implementation Baseline)
====================================================================================================
```

---

### 9.2 TR-03 — Nostro Shortfall

```
====================================================================================================
CANONICAL PROFILE CARD: TR-03 (Nostro Shortfall)
====================================================================================================
Canonical Profile ID:       TR-03
Canonical Profile Name:     Nostro Shortfall
Problem Meaning:            Outbound cross-border payment instruction cannot settle because the bank's
                            Nostro / correspondent account context lacks sufficient available settlement
                            currency balance or intraday settlement capacity.
Trigger Condition:          Nostro position inquiry returns nostro_available_balance < payment_amount,
                            or payment hub suspends dispatch due to correspondent settlement queue depletion.
Primary Engine:             TreasuryExposureEngine
Supporting Engine(s):       SettlementReconciliationEngine (supports correlation of position & credit evidence)
Resolution Pattern Family:  Primary: PAT-C (Threshold & Balance Pacing Family) [PROPOSED]
                            Supporting: PAT-B (Temporal Queue Recalculation) [PROPOSED]
Why Pattern Fits:           Evaluates Nostro liquidity position against bank treasury rebalancing agreements.
                            If pending incoming correspondent credits exist or authorized automated sweep
                            agreements are active, derives a Nostro rebalancing candidate (PAT-C).
Evidence Required:          NostroPositionRecord (nostro_bic, currency, available_balance, minimum_operating_target),
                            PendingCorrespondentCreditRecord (expected_credits, settlement_rail, arrival_window),
                            DeterministicCorrelationMatch (uetr, amount, currency, target_correspondent_bic).
Evidence Acquisition Modes: Mode 1 (Bank Pre-Supplied Position), Mode 2 (Authorized Automated System Query),
                            Mode 3 (Bank File/Feed), Mode 4 (Treasury Desk Mode 4 Rebalancing Authorization).
Evidence Trust Tier(s):     Tier 1 (Authoritative Treasury Management System / Nostro Ledger).
Resolution Determination:   R_det = True when a valid Nostro rebalancing candidate or pacing window is derived.
Resolution Uniqueness:      R_uniq = True when single funding source or single pacing window is resolved.
Technical Validation:       V_det = True when currency and correspondent BIC comply with clearing corridor rules.
Authority Validation:       V_auth = True when NostroPositionPort confirms authoritative correspondent position
                            and treasury policy authorizes automated Nostro rebalancing candidate derivation.
Bank Policy Dependency:     W3-BPD-02 attached to BankPolicyEnvelope:
                            - allow_auto_nostro_sweep: True [TEST / REFERENCE CONFIGURATION]
                            - min_nostro_operating_balance: 1000000.0 [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
                            - max_auto_sweep_amount: 500000.0 [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
                            - allowed_sweep_funding_accounts: ["NOSTRO-MASTER-EUR", "NOSTRO-CENTRAL-USD"] [ILLUSTRATIVE / TEST DEFAULT]
Compliance Dependency:      C_comp = True; correspondent institution and corridor are not subject to sanctions.
Execution Preconditions:    X_pre = True; funding Nostro account is active and interbank transfer corridor is open.
Non-Negotiable Boundaries:  1. Zero Direct Execution: PeX packages Nostro rebalancing candidates; bank treasury
                               desk / payment hub executes interbank liquidity transfers and funding wires.
                            2. Reachability != Solvency: Directory presence of a Nostro account != funded position.
HITL Trigger Conditions:    Shortfall exceeds policy cap, no viable funding Nostro account available, pending credit
                            fails to arrive within SLA, or correspondent bank under liquidity freeze.
STP Automation Potential:   Medium (for standard intraday rebalancing between pre-authorized correspondent accounts).
STP Eligibility Condition:  E_suff ∧ R_det ∧ R_uniq ∧ V_det ∧ V_auth ∧ P_bank ∧ C_comp ∧ X_pre == True.
Bank Execution Boundary:    execution_owner = "BANK"; handoff reaches BANK_HANDOFF_READY only when all predicates True.
AI Role:                    Observational liquidity flow forecasting only (no decision authority).
Semantic Status:            REMEDIATED SPECIFICATION (Pre-Implementation Baseline)
====================================================================================================
```

---

### 9.3 TR-04 — FX Rate Unavailable

```
====================================================================================================
CANONICAL PROFILE CARD: TR-04 (FX Rate Unavailable)
====================================================================================================
Canonical Profile ID:       TR-04
Canonical Profile Name:     FX Rate Unavailable
Problem Meaning:            Cross-currency payment instruction cannot be processed because the required
                            foreign exchange conversion rate / pricing quote is missing, stale (expired TTL),
                            exceeds allowable spread tolerance, or the currency pair is unquoted.
Trigger Condition:          FX pricing gateway returns RATE_UNAVAILABLE, STALE_RATE, or rate timestamp
                            exceeds configured maximum allowed age.
Primary Engine:             TreasuryExposureEngine
Supporting Engine(s):       RoutingClearingEngine (optional verification of currency rail operating windows)
Resolution Pattern Family:  Primary: PAT-C (Threshold & Balance Pacing Family) [PROVISIONAL]
                            Supporting: PAT-A (Reference Rule / Market Data Derivation) [PROVISIONAL]
Why Pattern Fits:           Queries bank-authorized FX market data feeds for a refreshed rate quote. If a fresh
                            quote is obtained within bank spread tolerance and amount <= policy threshold,
                            derives an FX pricing candidate (PAT-C). If rate is unquoted, routes to internal HITL review.
Evidence Required:          FXRateQuoteRecord (currency_pair, base_rate, bid_rate, ask_rate, quote_timestamp, rate_source),
                            FXSpreadPolicyRecord (max_allowed_spread_bps, max_rate_age_seconds, allow_auto_booking),
                            DeterministicCorrelationMatch (uetr, instructed_amount, instructed_ccy, settlement_ccy).
Evidence Acquisition Modes: Mode 1 (Bank Pre-Supplied Market Quote), Mode 2 (Authorized Automated System Query),
                            Mode 3 (Bank Feed), Mode 4 (FX Trader Mode 4 Special Rate Submission).
Evidence Trust Tier(s):     Tier 2 (Official Bank FX Pricing Engine / Market Data Provider).
Resolution Determination:   R_det = True when a valid, unexpired rate quote within spread tolerance is derived.
Resolution Uniqueness:      R_uniq = True when single authoritative rate quote is resolved for the currency pair.
Technical Validation:       V_det = True when computed target settlement amount satisfies currency decimal rules.
Authority Validation:       V_auth = True when FXPricingPort confirms quote is from a bank-approved pricing source.
Bank Policy Dependency:     W3-BPD-03 attached to BankPolicyEnvelope:
                            - allow_auto_rate_booking: True [TEST / REFERENCE CONFIGURATION]
                            - max_fx_rate_age_seconds: 60.0 [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
                            - max_fx_spread_tolerance_bps: 50.0 [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
                            - max_auto_fx_amount: 250000.0 [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
Compliance Dependency:      C_comp = True; currency corridor is not subject to FX capital controls or sanctions.
Execution Preconditions:    X_pre = True; foreign exchange dealing market is open for the instructed currency pair.
Non-Negotiable Boundaries:  1. No Phantom Rates: AI and historical lookup engines are STRICTLY PROHIBITED from
                               inventing, synthesizing, or interpolating FX rates.
                            2. Stale Rate Fail-Closed: Stale rate quotes exceeding TTL evaluate to E_suff = False.
HITL Trigger Conditions:    FX market data feed down, spread exceeds policy tolerance, currency pair illiquid/unquoted,
                            transaction amount > policy cap, or rate age exceeds allowable window.
STP Automation Potential:   High (for major/minor currency pairs with active live streaming market data feeds).
STP Eligibility Condition:  E_suff ∧ R_det ∧ R_uniq ∧ V_det ∧ V_auth ∧ P_bank ∧ C_comp ∧ X_pre == True.
Bank Execution Boundary:    execution_owner = "BANK"; handoff reaches BANK_HANDOFF_READY only when all predicates True.
AI Role:                    Observational market volatility telemetry only (no decision authority).
Semantic Status:            REMEDIATED SPECIFICATION (Pre-Implementation Baseline)
====================================================================================================
```

---

### 9.4 TR-06 — Limit Breach

```
====================================================================================================
CANONICAL PROFILE CARD: TR-06 (Limit Breach)
====================================================================================================
Canonical Profile ID:       TR-06
Canonical Profile Name:     Limit Breach
Problem Meaning:            Payment instruction exceeds an applicable configured operational risk limit,
                            including account limit, daily cap, corridor threshold, product cap, or channel limit.
Trigger Condition:          Limit management system returns LIMIT_EXCEEDED, DAILY_CAP_BREACHED, or
                            VELOCITY_THRESHOLD_REACHED.
Primary Engine:             TreasuryExposureEngine
Supporting Engine(s):       ComplianceDossierEngine (supports operational limit waiver dossier packaging)
Resolution Pattern Family:  Composite: Primary PAT-C (Threshold & Balance Pacing) [PROVISIONAL] /
                                       Supporting PAT-D (Compliance & Risk Dossier Adjudication) [PROVISIONAL]
Why Pattern Fits:           Evaluates whether the breach is due to a temporary intraday cycle that will clear
                            upon scheduled limit reset (PAT-C Pacing). If the breach is a hard operational limit,
                            compiles an operational limit waiver dossier for Credit Officer dual authorization (PAT-D).
Evidence Required:          LimitUtilizationRecord (limit_id, limit_type, current_utilization, limit_cap, reset_schedule),
                            ClientLimitProfileRecord (debtor_entity, approved_facility, waiver_preauthorization),
                            DeterministicCorrelationMatch (uetr, amount, currency, debtor_account).
Evidence Acquisition Modes: Mode 1 (Pre-Supplied Limit Waiver), Mode 2 (Authorized Automated System Query),
                            Mode 3 (Bank Feed), Mode 4 (Credit Risk Officer Mode 4 Limit Waiver Submission).
Evidence Trust Tier(s):     Tier 1 (Authoritative Bank Limit Management System).
Resolution Determination:   R_det = True when either an intraday reset pacing window is derived OR
                            a structured limit waiver dossier is assembled. (False if unresolvable breach).
Resolution Uniqueness:      R_uniq = True when single reset schedule or single waiver authority package is resolved.
Technical Validation:       V_det = True when transaction parameters align with limit governance schemas.
Authority Validation:       V_auth = True when LimitManagementPort confirms limit rules; waiver requires Credit Approver.
Bank Policy Dependency:     W3-BPD-04 attached to BankPolicyEnvelope:
                            - allow_intraday_limit_reset_pacing: True [TEST / REFERENCE CONFIGURATION]
                            - max_limit_reset_pacing_seconds: 3600.0 [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
                            - max_limit_waiver_threshold: 500000.0 [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
                            - require_credit_officer_dual_auth: True [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
Compliance Dependency:      C_comp = True; limit breach is operational and not triggered by AML structuring flags.
Execution Preconditions:    X_pre = True; account limit reset cycle active and debtor in good standing.
Non-Negotiable Boundaries:  1. Zero Autonomous Limit Override: PeX is STRICTLY PROHIBITED from increasing,
                               bypassing, or overriding operational limits autonomously.
                            2. Mandatory Maker-Checker for Waivers: Limit waivers require human dual-authorization.
HITL Trigger Conditions:    Hard limit breach exceeding pacing buffer, amount > policy waiver cap, unapproved facility,
                            or limit reset failure.
STP Automation Potential:   Low-to-Medium (STP viable only for transient intraday reset pacing; waivers require HITL).
STP Eligibility Condition:  E_suff ∧ R_det ∧ R_uniq ∧ V_det ∧ V_auth ∧ P_bank ∧ C_comp ∧ X_pre == True.
Bank Execution Boundary:    execution_owner = "BANK"; handoff reaches BANK_HANDOFF_READY only when all predicates True.
AI Role:                    Observational limit utilization analytics only (no decision authority).
Semantic Status:            REMEDIATED SPECIFICATION (Pre-Implementation Baseline)
====================================================================================================
```

---

### 9.5 TR-07 — Liquidity Constraint

```
====================================================================================================
CANONICAL PROFILE CARD: TR-07 (Liquidity Constraint)
====================================================================================================
Canonical Profile ID:       TR-07
Canonical Profile Name:     Liquidity Constraint
Problem Meaning:            A liquidity constraint is a condition in which available liquidity relevant
                            to payment processing or settlement is insufficient or otherwise constrained
                            under the applicable bank, account, currency, portfolio, clearing, or settlement context.
Trigger Condition:          Liquidity management system returns LIQUIDITY_BUFFER_CONSTRAINED, QUEUE_HELD,
                            or liquidity headroom falls below configured operating threshold.
Primary Engine:             TreasuryExposureEngine
Supporting Engine(s):       RoutingClearingEngine (optional evaluation of clearing windows & cutoff buffers)
Resolution Pattern Family:  Primary: PAT-C (Threshold & Balance Pacing Family) [PROPOSED]
                            Supporting: PAT-B (Temporal Queue Recalculation) [PROPOSED]
Why Pattern Fits:           Applies bank liquidity pacing algorithms to place the payment in an intraday
                            liquidity pacing queue (PAT-C). Releases the payment candidate once clearing
                            inflows or liquidity facilities restore required buffer headroom.
Evidence Required:          LiquidityReserveRecord (clearing_rail, currency, current_reserve_balance, minimum_buffer_target),
                            QueueStatusRecord (active_queue_depth, priority_tier, expected_inflow_volume),
                            DeterministicCorrelationMatch (uetr, amount, currency, priority_level).
Evidence Acquisition Modes: Mode 1 (Bank Pre-Supplied Reserve Status), Mode 2 (Authorized Automated System Query),
                            Mode 3 (Bank Feed), Mode 4 (Liquidity Desk Officer Mode 4 Release Authorization).
Evidence Trust Tier(s):     Tier 1 (Authoritative Bank Liquidity Management / Clearing Position).
Resolution Determination:   R_det = True when a valid liquidity pacing queue candidate and release schedule are derived.
Resolution Uniqueness:      R_uniq = True when single clearing priority queue and pacing window are resolved.
Technical Validation:       V_det = True when payment priority parameters satisfy clearing format specifications.
Authority Validation:       V_auth = True when LiquidityReservePort confirms liquidity position and
                            treasury policy authorizes automated liquidity pacing release candidate derivation.
Bank Policy Dependency:     W3-BPD-05 attached to BankPolicyEnvelope:
                            - allow_auto_liquidity_pacing: True [TEST / REFERENCE CONFIGURATION]
                            - min_liquidity_buffer: 5000000.0 [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
                            - max_liquidity_hold_seconds: 7200.0 [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
                            - priority_release_tier: "STANDARD_COMMERCIAL" [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
Compliance Dependency:      C_comp = True; clearing corridor is operational and not subject to sovereign sanctions.
Execution Preconditions:    X_pre = True; clearing operational window open; liquidity replenishment active.
Non-Negotiable Boundaries:  1. Zero Direct Dispatch: PeX manages pacing candidates; bank payment hub releases
                               instructions into clearing network queues.
                            2. Cutoff Protection: Liquidity pacing must fail closed to HITL before clearing cutoff.
HITL Trigger Conditions:    Liquidity buffer exhausted beyond max hold window, payment approaching rail
                            cutoff buffer, transaction amount exceeds systemic pacing threshold, or high-priority wire.
STP Automation Potential:   High (for automated intraday queue pacing during peak clearing cycles).
STP Eligibility Condition:  E_suff ∧ R_det ∧ R_uniq ∧ V_det ∧ V_auth ∧ P_bank ∧ C_comp ∧ X_pre == True.
Bank Execution Boundary:    execution_owner = "BANK"; handoff reaches BANK_HANDOFF_READY only when all predicates True.
AI Role:                    Observational queue throughput analytics only (no decision authority).
Semantic Status:            REMEDIATED SPECIFICATION (Pre-Implementation Baseline)
====================================================================================================
```

---

### 9.6 TR-08 — Credit Exposure Breach

```
====================================================================================================
CANONICAL PROFILE CARD: TR-08 (Credit Exposure Breach)
====================================================================================================
Canonical Profile ID:       TR-08
Canonical Profile Name:     Credit Exposure Breach
Problem Meaning:            Payment instruction causes total outstanding credit exposure to breach an applicable
                            credit facility, counterparty ceiling, or institutional credit risk ceiling.
Trigger Condition:          Credit risk management system returns COUNTERPARTY_EXPOSURE_BREACH, FACILITY_CAP_EXCEEDED,
                            or RISK_RATING_DOWNGRADE_HOLD.
Primary Engine:             TreasuryExposureEngine
Supporting Engine(s):       ComplianceDossierEngine (assembles credit risk adjudication package)
Resolution Pattern Family:  Primary: PAT-D (Compliance & Risk Dossier Adjudication Family) [PROVISIONAL]
                            Supporting: PAT-C (Threshold & Balance Tracking) [PROVISIONAL]
Why Pattern Fits:           Assembles an authoritative Credit Risk Dossier containing exposure utilization,
                            guarantee records, and risk rating metrics (PAT-D). Routes cases to Senior Credit
                            Approver for governed human dual-authorization.
Evidence Required:          CounterpartyExposureRecord (counterparty_bic, credit_rating, total_facility_limit, current_exposure),
                            CreditFacilityRecord (facility_id, collateral_coverage, expiry_date, approval_tier),
                            DeterministicCorrelationMatch (uetr, amount, currency, counterparty_bic).
Evidence Acquisition Modes: Mode 1 (Bank Pre-Supplied Credit Dossier), Mode 2 (Authorized Automated System Query),
                            Mode 3 (Bank Feed), Mode 4 (Senior Credit Officer Mode 4 Credit Approval Submission).
Evidence Trust Tier(s):     Tier 1 (Authoritative Enterprise Credit Risk Management System).
Resolution Determination:   R_det = True when a complete, verified Credit Risk Dossier is compiled for human review.
Resolution Uniqueness:      R_uniq = True when single counterparty credit hierarchy is resolved.
Technical Validation:       V_det = True when exposure metrics align with bank credit risk schemas.
Authority Validation:       V_auth = False for autonomous execution; V_auth = True ONLY upon Senior Credit Officer approval.
Bank Policy Dependency:     W3-BPD-06 attached to BankPolicyEnvelope:
                            - zero_auto_stp_on_credit_breach: True [MANDATORY INVARIANT: Autonomous STP Prohibited]
                            - require_senior_risk_approver: True [MANDATORY]
                            - max_dossier_compilation_seconds: 300.0 [TEST / REFERENCE DEFAULT — Bank Policy Decision Required]
Compliance Dependency:      C_comp = True; counterparty is not on credit watch, insolvency hold, or sanctions list.
Execution Preconditions:    X_pre = True; credit facility is active and credit officer approval token is verified.
Non-Negotiable Boundaries:  1. Autonomous STP approval or override of a credit exposure breach is prohibited.
                            2. AI Prohibition: AI has no decision authority and cannot waive credit exposure.
HITL Trigger Conditions:    Credit exposure breaches route to internal PeX HITL Credit Review Workspace.
STP Automation Potential:   Autonomous STP Prohibited (Governed Human Adjudication — Mandatory Approver Sign-off).
STP Eligibility Condition:  Evaluates to FALSE autonomously; requires Mode 4 Senior Credit Officer authorization.
Bank Execution Boundary:    execution_owner = "BANK"; handoff reaches BANK_HANDOFF_READY only upon full predicate validation.
AI Role:                    Observational risk rating summary extraction only (no decision authority).
Semantic Status:            REMEDIATED SPECIFICATION (Pre-Implementation Baseline)
====================================================================================================
```

---

## 10. Evidence Acquisition, Trust Tiers & Provider-Neutral SPI Architecture

### 10.1 Provider-Neutral SPI Port Catalog for Wave 3

Wave 3 introduces **six (6) new provider-neutral SPI ports**, expanding the PeX port catalog from 11 to **17 abstract interfaces**:

```
+----------------------------------------------------------------------------------------------------+
|                               PROVIDER-NEUTRAL SPI PORT INVENTORY                                  |
+----+-----------------------------+------------------------------------+------------------+---------+
| #  | SPI Port Identifier         | Abstract Domain Interface Name     | Introducing Wave | Status  |
+----+-----------------------------+------------------------------------+------------------+---------+
| 1  | SPI-ACCOUNT-MASTER-PORT     | AccountMasterPort                  | Wave 0A / Wave 1 | PROVEN  |
| 2  | SPI-ROUTING-DIRECTORY-PORT  | RoutingDirectoryPort               | Wave 0A / Wave 1 | PROVEN  |
| 3  | SPI-REMITTANCE-DOCUMENT     | RemittanceDocumentPort             | Wave 0A / Wave 1 | PROVEN  |
| 4  | SPI-CLEARING-CALENDAR-PORT  | ClearingCalendarPort               | Wave 1           | PROVEN  |
| 5  | SPI-GATEWAY-SOCKET-PROBE    | GatewaySocketProbePort             | Wave 1           | PROVEN  |
| 6  | SPI-REPAIR-QUEUE-PORT       | RepairQueuePort                    | Wave 1           | PROVEN  |
| 7  | SPI-REGULATORY-DIRECTORY    | RegulatoryDirectoryPort            | Wave 1           | PROVEN  |
| 8  | SPI-CORRESPONDENT-GATEWAY   | CorrespondentGatewayPort           | Wave 2           | PROVEN  |
| 9  | SPI-SETTLEMENT-RETURN-PORT  | SettlementReturnPort               | Wave 2           | PROVEN  |
| 10 | SPI-LEGAL-REGISTRY-PORT     | LegalRegistryPort                  | Wave 2           | PROVEN  |
| 11 | SPI-GENERAL-LEDGER-SUSPENSE | GeneralLedgerSuspensePort          | Wave 2           | PROVEN  |
| 12 | SPI-TREASURY-POSITION-PORT  | TreasuryPositionPort               | Wave 3           | SPECIFIED|
| 13 | SPI-NOSTRO-POSITION-PORT    | NostroPositionPort                 | Wave 3           | SPECIFIED|
| 14 | SPI-FX-PRICING-PORT         | FXPricingPort                      | Wave 3           | SPECIFIED|
| 15 | SPI-LIMIT-MANAGEMENT-PORT   | LimitManagementPort                | Wave 3           | SPECIFIED|
| 16 | SPI-CREDIT-RISK-PORT        | CreditRiskPort                     | Wave 3           | SPECIFIED|
| 17 | SPI-LIQUIDITY-RESERVE-PORT  | LiquidityReservePort               | Wave 3           | SPECIFIED|
+----+-----------------------------+------------------------------------+------------------+---------+
```

### 10.2 Evidence Trust Tiers for Treasury
- **Tier 1 (Authoritative Core & Treasury Systems)**: Feeds from Core Banking, Treasury Management Systems (TMS), Nostro Ledgers, Limit Engines, and Enterprise Credit Risk Platforms.
- **Tier 2 (Official Market & Clearing Data)**: Streaming FX market data pricing feeds, clearing liquidity position feeds, and clearing rail operating schedules.
- **Tier 3 (Client ERP & Counterparty Assertions)**: Client-provided funding notifications, commercial remittance payloads, and indicative FX quotes (requires verification).
- **Tier 4 (Historical Precedent Context)**: Historical deposit timing patterns, past liquidity cycles (advisory only; no execution authority).

### 10.3 Evidence Freshness & TTL Rules (Test / Reference Defaults)
- Real-time balances (`TR-02`, `TR-03`): Maximum age $\le 30\text{ seconds}$ `[TEST / REFERENCE DEFAULT]`.
- FX Rates (`TR-04`): Maximum age $\le 60\text{ seconds}$ `[TEST / REFERENCE DEFAULT]`.
- Operational Limits (`TR-06`): Maximum age $\le 300\text{ seconds}$ `[TEST / REFERENCE DEFAULT]`.
- Liquidity Buffer (`TR-07`): Maximum age $\le 120\text{ seconds}$ `[TEST / REFERENCE DEFAULT]`.
- Credit Risk Exposure (`TR-08`): Maximum age $\le 600\text{ seconds}$ `[TEST / REFERENCE DEFAULT]`.

---

## 11. Authority Model & Interface Separation ($V_{\text{auth}}$)

```mermaid
flowchart LR
    Port["Provider-Neutral SPI Port (Interface Contract)"] --> Adapter["Reference In-Memory Adapter (TEST_ONLY Harness)"]
    Port -.-> LiveBank["Live Bank System of Record (Production Authority Category)"]
    LiveBank === Auth{"Authority Validation (V_auth)"}
    Adapter -.-> HarnessAuth["Test Authority Assertion (TEST_ONLY)"]
```

### Key Epistemic Principles:
1. **SPI Port $\neq$ Authority**: An SPI port (`TreasuryPositionPort`, `FXPricingPort`, etc.) is an abstract interface contract. It defines data structures and query signatures but does not confer authority.
2. **Authority Resides in the System of Record**: $V_{\text{auth}}$ is satisfied only when the bank-designated system of record (Core Banking, TMS, Dealing Desk, Credit Risk Committee) authorizes the transaction or state.
3. **Reference Adapters**: Reference adapters are in-memory harnesses for test hermeticity (`environment = "TEST_ONLY"`). Live production $V_{\text{auth}}$ requires binding to enterprise production connectors.

---

## 12. Bank Policy Envelope & Parameterization ($P_{\text{bank}}$)

Wave 3 establishes the `W3PolicyThresholds` schema attached to `BankPolicyEnvelope`. All values are classified as **TEST / REFERENCE DEFAULTS** subject to institutional policy configuration:

```
+----------------------------------------------------------------------------------------------------+
|                               WAVE 3 BANK POLICY ENVELOPE (W3-BPD)                                 |
+----+-----------------------------+------------------------------------+------------------+---------+
| #  | Policy Parameter Identifier | Target Profile / Domain            | Reference Default| Status  |
+----+-----------------------------+------------------------------------+------------------+---------+
| 1  | W3-BPD-01                   | TR-02 (Insufficient Funds Pacing)  | Max Pacing: 1800s| TEST    |
|    |                             |                                    | Cap: $100,000.00 | DEFAULT |
+----+-----------------------------+------------------------------------+------------------+---------+
| 2  | W3-BPD-02                   | TR-03 (Nostro Rebalancing Policy)  | Target: $1,000k  | TEST    |
|    |                             |                                    | Cap: $500,000.00 | DEFAULT |
+----+-----------------------------+------------------------------------+------------------+---------+
| 3  | W3-BPD-03                   | TR-04 (FX Rate & Spread Tolerance) | Max Age: 60s     | TEST    |
|    |                             |                                    | Spread: 50 bps   | DEFAULT |
+----+-----------------------------+------------------------------------+------------------+---------+
| 4  | W3-BPD-04                   | TR-06 (Limit Reset & Waiver Policy)| Max Pacing: 3600s| TEST    |
|    |                             |                                    | Cap: $500,000.00 | DEFAULT |
+----+-----------------------------+------------------------------------+------------------+---------+
| 5  | W3-BPD-05                   | TR-07 (Liquidity Pacing Policy)    | Min Buffer: $5M  | TEST    |
|    |                             |                                    | Max Hold: 7200s  | DEFAULT |
+----+-----------------------------+------------------------------------+------------------+---------+
| 6  | W3-BPD-06                   | TR-08 (Credit Exposure Policy)     | Auto-STP Blocked | MANDAT- |
|    |                             |                                    | Dual-Auth: TRUE  | ORY     |
+----+-----------------------------+------------------------------------+------------------+---------+
```

> **FAIL-CLOSED POLICY INVARIANT:**  
> If bank policy is missing, unparseable, or expired, $P_{\text{bank}}$ evaluates strictly to `False`, forcing the transaction into internal HITL review.

---

## 13. 8-Predicate STP Conjunction Formula Invariant

The canonical STP decision formula remains absolute, immutable, and non-bypassable across all Wave 3 profiles:

$$\Huge \text{STP\_ELIGIBLE} = E_{\text{suff}} \land R_{\text{det}} \land R_{\text{uniq}} \land V_{\text{det}} \land V_{\text{auth}} \land P_{\text{bank}} \land C_{\text{comp}} \land X_{\text{pre}}$$

```
+----------------------------------------------------------------------------------------------------+
|                                 8-PREDICATE CONJUNCTION INVARIANT                                  |
+---+-----------------------------+------------------------------------------------------------------+
| # | Predicate Symbol            | Wave 3 Contextual Evaluation Scope                               |
+---+-----------------------------+------------------------------------------------------------------+
| 1 | E_suff (Evidence Sufficient)| Authoritative position, FX quote, limit, or reserve data present |
| 2 | R_det (Resolution Determin) | Valid pacing schedule, sweep, FX booking, or waiver candidate    |
| 3 | R_uniq (Resolution Unique)  | Exactly one resolution candidate derived without ambiguity       |
| 4 | V_det (Technical Validation)| Payment currency decimals, message formatting, schema validation |
| 5 | V_auth (Authority Validated)| Authoritative system confirms balance/pricing/credit authority   |
| 6 | P_bank (Bank Policy Satis)  | Amount <= policy cap; spread <= tolerance; buffer >= minimum     |
| 7 | C_comp (Compliance Passed)  | Sanctions/AML cleared; zero capital control or structuring flags |
| 8 | X_pre (Preconditions Met)   | Clearing rail open; dealing desk active; clearing window open    |
+---+-----------------------------+------------------------------------------------------------------+
```

---

## 14. Human-in-the-Loop (HITL) Closed-Loop Model

```mermaid
flowchart TD
    Ingest["Inward Exception Ingestion (TR-02..08)"] --> Eval["8-Predicate STP Evaluation Engine"]
    Eval -- "All 8 Predicates True" --> Handoff["BANK_HANDOFF_READY (execution_owner = 'BANK')"]
    Eval -- "Any Predicate False" --> HITLState["Internal Governed State (e.g. TREASURY_HOLD / CREDIT_REVIEW)"]
    HITLState --> Operator["Operator / Trader / Risk Officer Submits Mode 4 Evidence"]
    Operator --> ReEval["Re-evaluate Exact Same 8-Predicate Conjunction Engine"]
    ReEval -- "All 8 Predicates True" --> Handoff
    ReEval -- "Predicates Still False" --> HITLState
```

### Verified Closed-Loop Invariants:
1. **Zero External Ejection**: Exceptions remain inside PeX throughout the remediation lifecycle.
2. **Re-Evaluation Parity**: Human-supplied Mode 4 evidence passes through the exact same 8-predicate evaluation pipeline.
3. **Terminal State Realism**: Only eligible handoffs reach `BANK_HANDOFF_READY`. Ineligible cases remain inside PeX in appropriate internal governed states (`HITL_REQUIRED`, `TREASURY_HOLD`, `CREDIT_REVIEW`, `MAKER_CHECKER_PENDING`, `INVESTIGATION_REQUIRED`, `POLICY_HOLD`, `UNRESOLVED`).

---

## 15. AI Boundary & Zero Decision Authority

- **No Decision Authority**: AI models possess no decision authority and no bypass capability across any of the 8 predicates.
- **Strict Prohibitions**: AI may NOT invent balances, invent FX rates, invent liquidity, override limits, approve credit exposure, establish authority, bypass policy, release payments, or mutate bank systems.
- **Allowed AI Roles**: AI may classify, extract, summarize, search historical evidence, identify patterns, rank candidates, and explain evidence.
- **Telemetry-Only Scoring**: `ai_confidence` is observational telemetry only and does not participate in the boolean conjunction gate.

---

## 16. Bank Execution Boundary & Immutability of `execution_owner = "BANK"`

- **Mandatory Handoff Invariant**: All positive resolution fixtures terminate with `execution_owner = "BANK"`.
- **PeX Capability Boundary**: PeX may detect exceptions, acquire evidence, normalize data, evaluate rules, derive candidate resolutions, package evidence, route HITL tasks, and prepare governed bank handoffs.
- **PeX Execution Prohibitions**: PeX may NOT execute payments, release payments, post ledger entries, move funds, book FX, execute Nostro sweeps, override limits, approve credit, or mutate bank systems.
- **Production Autonomous STP Strictly Blocked**: Autonomous straight-through release into clearing networks is strictly forbidden.

---

## 17. Cross-Profile Treasury Interactions & Governed Multi-Exception Evaluation

Multiple treasury exception profiles may coexist for a single payment. PeX correlates and evaluates them using:
- Payment identity and lifecycle state
- Evidence sufficiency across required dimensions
- Authoritative system state
- Applicable resolution contracts
- Bank policy and risk governance rules
- Rail and process operating context

```
+----------------------------------------------------------------------------------------------------+
|                       CROSS-PROFILE TREASURY MULTI-EXCEPTION DYNAMICS                              |
+--------------------------+-------------------------------------------------------------------------+
| Exception Pair           | Interaction Dynamics & Governance Evaluation Context                    |
+--------------------------+-------------------------------------------------------------------------+
| TR-02 vs TR-03           | TR-02 concerns debtor funding; TR-03 concerns Nostro clearing capacity. |
| (Debtor vs Nostro Funds) | Precedence, sequencing, suppression, or co-resolution is a              |
|                          | BANK POLICY / ARCHITECTURE DECISION REQUIRED.                           |
+--------------------------+-------------------------------------------------------------------------+
| TR-02 vs TR-07           | TR-02 is account-level; TR-07 is clearing channel liquidity pacing.     |
| (Debtor vs Channel Liq)  | Precedence, sequencing, suppression, or co-resolution is a              |
|                          | BANK POLICY / ARCHITECTURE DECISION REQUIRED.                           |
+--------------------------+-------------------------------------------------------------------------+
| TR-04 vs TR-02           | TR-04 concerns FX pricing quote; TR-02 concerns settlement debit balance|
| (FX Rate vs Funding)     | Precedence, sequencing, suppression, or co-resolution is a              |
|                          | BANK POLICY / ARCHITECTURE DECISION REQUIRED.                           |
+--------------------------+-------------------------------------------------------------------------+
| TR-06 vs TR-08           | TR-06 is operational limit; TR-08 is credit exposure ceiling.          |
| (Limit vs Credit Risk)   | Precedence, sequencing, suppression, or co-resolution is a              |
|                          | BANK POLICY / ARCHITECTURE DECISION REQUIRED.                           |
+--------------------------+-------------------------------------------------------------------------+
| TR-07 vs TR-08           | TR-07 is liquidity pacing; TR-08 is institutional credit breach.        |
| (Liquidity vs Credit)    | Precedence, sequencing, suppression, or co-resolution is a              |
|                          | BANK POLICY / ARCHITECTURE DECISION REQUIRED.                           |
+--------------------------+-------------------------------------------------------------------------+
```

---

## 18. Wave 3 Architecture & Bank Policy Decisions Required

### 18.1 Architecture Decisions Required Prior to Implementation
1. **`ADR-W3-01` (Treasury Position Data Freshness & Intraday Reservation Abstraction)**: Formalize data models for available balance vs ledger balance vs active intraday reservations across multi-currency accounts.
2. **`ADR-W3-02` (Multi-Tier Limit & Exposure Hierarchy Modeling)**: Define canonical schemas representing account-level, client-level, corridor-level, and counterparty-level risk limits.
3. **`ADR-W3-03` (FX Market Data Feed Staleness & Spread Tolerance Model)**: Formalize rate quote TTL verification and spread calculation against bank reference rate curves.
4. **`ADR-W3-04` (Multi-Exception Treasury Correlation & Queue Orchestration)**: Establish the execution engine pipeline sequence when an instruction encounters concurrent FX, funding, and limit exceptions.

### 18.2 Bank Policy Decisions Required Prior to Implementation
1. **`POL-W3-01` (Insufficient Funds Pacing Window)**: Bank operations must establish max pacing duration (e.g. illustrative 30 mins) and maximum auto-pacing amount caps.
2. **`POL-W3-02` (Nostro Rebalancing Policy)**: Bank treasury desk must define approved rebalancing funding accounts and minimum operating target balances.
3. **`POL-W3-03` (FX Rate Freshness & Spread Tolerance)**: Bank dealing desk must configure max quote age (e.g. illustrative 60s) and allowable spread tolerance bands.
4. **`POL-W3-04` (Operational Limit Reset & Waiver Governance)**: Bank risk management must define dual-authorization thresholds for limit waivers.
5. **`POL-W3-05` (Liquidity Pacing Buffers)**: Bank treasury must establish minimum clearing reserve buffers and queue priority rules.
6. **`POL-W3-06` (Credit Risk Approver Dual Authorization)**: Bank credit committee must designate authorized Senior Credit Approvers (Autonomous STP Prohibited).

---

## 19. Production Integration Dependencies (Illustrative & Candidate Targets)

The target enterprise technologies listed below are **ILLUSTRATIVE / CANDIDATE / NON-BINDING EXAMPLES** for future production integration. The core PeX architecture remains strictly provider-neutral:

```
+----------------------------------------------------------------------------------------------------+
|                         PROTOTYPE-TO-PRODUCTION INTEGRATION BOUNDARIES                             |
+---+------------------------------------+----------------------------------+------------------------+
| # | Boundary Name                      | Abstract SPI Port in PeX         | Candidate Target (Ill.)|
+---+------------------------------------+----------------------------------+------------------------+
| 1 | Core Banking Balance Feed          | TreasuryPositionPort             | Core Banking Platform  |
| 2 | Nostro / Correspondent Position    | NostroPositionPort               | TMS / Bank Ledger Feed |
| 3 | Live FX Market Data Pricing Feed   | FXPricingPort                    | Market Data Provider   |
| 4 | Operational Limit Management Engine| LimitManagementPort              | Bank Limit Engine / DDA|
| 5 | Enterprise Credit Risk Platform    | CreditRiskPort                   | Enterprise Risk Engine |
| 6 | Clearing Liquidity Reserve Feed    | LiquidityReservePort             | Clearing / RTGS Hub    |
+---+------------------------------------+----------------------------------+------------------------+
```

---

## 20. Wave 3 Testing Strategy & Architecture (Pre-Implementation)

The testing architecture for Wave 3 must cover 20 discrete test dimensions prior to acceptance:

```
+----------------------------------------------------------------------------------------------------+
|                                  WAVE 3 TESTING ARCHITECTURE                                       |
+----+----------------------------------+------------------------------------------------------------+
| #  | Test Category                    | Testing Scope & Verification Focus                         |
+----+----------------------------------+------------------------------------------------------------+
| 1  | Treasury Engine Unit Tests       | Core resolution logic across TR-02, 03, 04, 06, 07, 08     |
| 2  | Wave 3 Port Contract Tests       | 6 new SPI abstract port contracts and reference adapters   |
| 3  | Evidence Sufficiency Tests       | Freshness, TTL expiration, and missing evidence handling   |
| 4  | Contradictory Evidence Tests     | Conflicting balance / limit feeds fail closed to HITL      |
| 5  | Stale FX Rate Tests              | Rates exceeding configured TTL fail closed immediately     |
| 6  | Limit Breach Pacing Tests        | Transient reset cycle pacing vs hard limit escalation      |
| 7  | Credit Exposure Zero-STP Tests   | Fail-closed verification for TR-08 without Approver token  |
| 8  | Bank Policy Envelope Tests       | Missing or unparseable policy envelope forces fail-closed  |
| 9  | 8-Predicate Mutation Matrix      | 24+ permutations verifying every single predicate failure  |
| 10 | Provider-Neutrality AST Tests    | AST analysis proving 0 vendor SDK imports in Wave 3 ports  |
| 11 | Closed-Loop HITL Re-evaluation   | Mode 4 operator evidence re-evaluates exact 8 predicates   |
| 12 | Segregation of Duties (SoD)      | Maker cannot Checker credit risk / limit waiver handoffs   |
| 13 | Cross-Profile Interaction Tests  | Concurrent FX, balance, limit, and Nostro exception tests  |
| 14 | Canonical E2E Positive Scenarios | Scenarios 31A, 32A, 33A, 34A, 35A, 36A                     |
| 15 | Canonical E2E Negative Scenarios | Scenarios 31B, 32B, 33B, 34B, 35B, 36B                     |
| 16 | Cumulative Regression Suite      | 100% green execution across prior 726 baseline tests       |
+----+----------------------------------+------------------------------------------------------------+
```

---

## 21. Proposed Future Implementation Scenarios (Scenarios 31A–36B)

Wave 3 specifies **twelve (12) proposed future implementation scenarios** (Scenarios 31A through 36B), continuing sequentially from Wave 2 (which concluded at Scenario 30B). These scenarios represent future test designs and have not yet been executed or verified:

```
+----------------------------------------------------------------------------------------------------+
|                               PROPOSED FUTURE E2E SCENARIOS                                        |
+----+-------------+-------+--------------------------------------+----------------------------------+
| #  | Scenario ID | Code  | Scenario Name & Test Focus           | Expected Governed Output State   |
+----+-------------+-------+--------------------------------------+----------------------------------+
| 1  | Scenario 31A| TR-02 | Insufficient Funds [Intraday Pacing] | STP_ELIGIBLE=True / HANDOFF_READY|
| 2  | Scenario 31B| TR-02 | Unfunded Deficit [Fail-Closed HITL]  | STP_ELIGIBLE=False / HITL_REQUIRED|
| 3  | Scenario 32A| TR-03 | Nostro Shortfall [Sweep Rebalancing] | STP_ELIGIBLE=True / HANDOFF_READY|
| 4  | Scenario 32B| TR-03 | Unfunded Nostro [Treasury Hold]      | STP_ELIGIBLE=False / TREASURY_HOLD|
| 5  | Scenario 33A| TR-04 | FX Rate Available [Fresh Market Rate]| STP_ELIGIBLE=True / HANDOFF_READY|
| 6  | Scenario 33B| TR-04 | Stale FX Rate [Fail-Closed Market]   | STP_ELIGIBLE=False / HITL_REQUIRED|
| 7  | Scenario 34A| TR-06 | Limit Reset Pacing [Intraday Cycle]  | STP_ELIGIBLE=True / HANDOFF_READY|
| 8  | Scenario 34B| TR-06 | Hard Limit Breach [Credit Dossier]   | STP_ELIGIBLE=False / CREDIT_REVIEW|
| 9  | Scenario 35A| TR-07 | Liquidity Buffer [Pacing Release]    | STP_ELIGIBLE=True / HANDOFF_READY|
| 10 | Scenario 35B| TR-07 | Liquidity Exhaustion [Channel Hold]  | STP_ELIGIBLE=False / LIQUIDITY_HLD|
| 11 | Scenario 36A| TR-08 | Credit Exposure Dossier [Governed PKG| STP_ELIGIBLE=False / APPROVER_HOLD|
| 12 | Scenario 36B| TR-08 | Critical Counterparty Breach [Hold]  | STP_ELIGIBLE=False / CREDIT_FREEZE|
+----+-------------+-------+--------------------------------------+----------------------------------+
```

---

## 22. Definition of Done (Required for Future Implementation Acceptance)

Before Wave 3 implementation can be formally accepted, all of the following criteria are **REQUIRED FOR FUTURE IMPLEMENTATION ACCEPTANCE**:

1. **Profile Implementation**: All six profiles (`TR-02`, `TR-03`, `TR-04`, `TR-06`, `TR-07`, `TR-08`) implemented within `TreasuryExposureEngine`.
2. **SPI Ports & Reference Adapters**: All six new SPI ports (`SPI-TREASURY-POSITION`, `SPI-NOSTRO-POSITION`, `SPI-FX-PRICING`, `SPI-LIMIT-MANAGEMENT`, `SPI-CREDIT-RISK`, `SPI-LIQUIDITY-RESERVE`) and in-memory reference adapters implemented.
3. **Evidence Schemas**: Pydantic evidence schemas defined and published in `backend/app/schemas/contracts/`.
4. **Dynamic Configuration**: Wave 3 profiles registered in `InMemoryConfigurationAdapter` with schema, TTL, and trust tier validation.
5. **Bank Policy Envelope**: `W3PolicyThresholds` implemented and integrated into `BankPolicyEnvelope`.
6. **Immutable 8-Predicate Conjunction**: Mathematical conjunction enforced across all six profiles.
7. **HITL Closed-Loop**: Internal PeX HITL workspace integration with zero predicate bypass on resubmission.
8. **AI Boundary**: No autonomous decision authority; zero synthetic balance/FX/credit creation.
9. **Bank Execution Boundary**: `execution_owner = "BANK"` asserted on all terminal handoffs.
10. **Provider Neutrality AST Verification**: Provider neutrality AST verification required (0 vendor SDK imports in Wave 3 ports and adapters).
11. **E2E Canonical Scenarios**: All 12 proposed canonical scenario fixtures (31A–36B) verified passing upon implementation.
12. **Zero Regression**: 100% green execution across all 726 cumulative baseline tests maintained.
13. **Forensic Acceptance**: Independent forensic red-team acceptance review required.
14. **Semantic Reconciliation**: Multi-profile cross-wave semantic reconciliation required.
15. **Governance Sign-Off**: Formal governance sign-off required before production release.

---

## 23. Phase 2, Wave 1, and Wave 2 Protection Invariants

- **Phase 2 Protected**: 11 profiles (`DQ-01`, `DQ-02`, `DQ-05`, `DQ-06`, `DQ-08`, `PR-01`, `PR-03`, `PR-05`, `PR-08`, `CO-04`, `ST-01`) remain closed, frozen, and protected against re-engineering.
- **Wave 1 Protected**: 9 profiles (`DQ-03`, `DQ-04`, `DQ-07`, `DQ-09`, `PR-02`, `PR-04`, `PR-07`, `PR-09`, `CO-07`) remain closed, frozen, and protected.
- **Wave 2 Protected**: 3 profiles (`PR-06`, `ST-02`, `ST-03`) remain closed, frozen, and protected under the sign-off baseline `v0.1.2`.
- **Zero Drift**: No modification to earlier profile semantics, schemas, tests, or capability engine assignments.

---

## 24. Document Governance Status & Next Governed Step

```
====================================================================================================
                                  GOVERNANCE STATUS SUMMARY
====================================================================================================
Wave 3 Architecture & Profile Contract: REMEDIATED / READY FOR AUTHORIZATION REVIEW
Wave 3 Scope:                           EXACTLY SIX PROFILES:
                                        TR-02, TR-03, TR-04, TR-06, TR-07, TR-08
Engineering Implementation Authorization: NOT GRANTED
Wave 3 Implementation:                  NOT STARTED / NOT AUTHORIZED
Production Autonomous STP:              STRICTLY BLOCKED
Execution Owner:                        BANK
----------------------------------------------------------------------------------------------------
Next Governed Step:                     PeX_Wave3_Implementation_Authorization_Gate_v0.1.md
====================================================================================================
```

> **GOVERNANCE DIRECTIVE:**  
> Wave 3 Architecture and Profile Contract is **REMEDIATED (v0.1.2)** and ready for authorization gate review. Engineering implementation remains **STRICTLY NOT AUTHORIZED** until the formal `PeX_Wave3_Implementation_Authorization_Gate_v0.1.md` is drafted, reviewed, and approved.
