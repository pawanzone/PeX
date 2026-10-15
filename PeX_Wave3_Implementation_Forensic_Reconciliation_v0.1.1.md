# PeX Phase 3 — Wave 3 Implementation Forensic Reconciliation v0.1.1

**Document Role:** Principal Architecture, Governance & Independent Red-Team Reviewer  
**Audit Stage:** Second-Pass Forensic Challenge & Formal Acceptance Determination  
**Controlling Architecture Baseline:** `PeX_Phase3_Wave3_Industrialization_Architecture_and_Profile_Contract_v0.1.2.md`  
**Controlling Authorization Gate:** `PeX_Wave3_Implementation_Authorization_Gate_v0.1.md` (Option B — Authorized with Conditions)  
**Implementation Report Evaluated:** `PeX_Wave3_Implementation_Report_v0.1.md`  
**Prior Forensic Report Challenged:** `PeX_Wave3_Implementation_Forensic_Reconciliation_v0.1.md`  
**Audit Mode:** STRICT READ-ONLY FORENSIC RE-EXAMINATION & ADVERSARIAL CHALLENGE  
**Audit Date:** October 8, 2026  
**Final Forensic Verdict:** **OPTION C — FORENSIC ACCEPTANCE BLOCKED**  

---

## 1. Executive Verdict & Summary

An independent, adversarial second-pass forensic review of the **PeX Phase 3 — Wave 3 Engineering Implementation** was conducted to verify whether the evidence supported the initial v0.1 verdict (`OPTION B — ACCEPTANCE SURVIVES WITH NON-BLOCKING CORRECTIONS`).

Following code-level call-path tracing, test suite disassembly, and rigorous comparison against the frozen Authorization Gate, the second-pass review establishes that **Option B is untenable under PeX governance rules**.

### Final Forensic Verdict: **OPTION C — FORENSIC ACCEPTANCE BLOCKED**

This determination is mandated by two blocking **P2 defects**:

1. **Unmet Mandatory Acceptance Criterion (Finding W3-FOR-01 — P2 Blocking)**:
   The controlling Authorization Gate (`PeX_Wave3_Implementation_Authorization_Gate_v0.1.md`, Sections 18 and 20.8) explicitly mandates **at least 24 independently isolated predicate-mutation/adversarial test scenarios** covering all 8 predicates ($E_{\text{suff}} \land R_{\text{det}} \land R_{\text{uniq}} \land V_{\text{det}} \land V_{\text{auth}} \land P_{\text{bank}} \land C_{\text{comp}} \land X_{\text{pre}}$).
   The actual Wave 3 test directory (`tests/wave3/test_wave3_adversarial_predicates.py`) contains **only four (4) explicit adversarial tests**, covering only 4 predicates ($E_{\text{suff}}, R_{\text{det}}, P_{\text{bank}}, X_{\text{pre}}$). **Four predicates ($R_{\text{uniq}}, V_{\text{det}}, V_{\text{auth}}, C_{\text{comp}}$) have zero isolated mutation tests in the Wave 3 suite.** Under PeX governance, an unmet mandatory acceptance criterion cannot be unilaterally waived or downgraded to non-blocking.

2. **Core Candidate Derivation Invokes In-Memory State Mutation (Finding W3-FOR-03 — Reclassified P2 Blocking)**:
   Code inspection of `TreasuryExposureEngine.resolve_tr02_insufficient_funds` (`backend/app/services/engines/treasury_exposure_engine.py:345`) reveals that during positive candidate derivation, the core engine directly calls `self.treasury_port.reserve_intraday_funds(account_number, instructed_amount, currency)`.
   In `InMemoryTreasuryPositionAdapter` (`backend/app/adapters/reference/reference_treasury_position_adapter.py:83-84`), this method mutates the shared in-memory dictionary `self._balances`, decrementing `available_balance` and incrementing `holds_amount` **prior to any human approval or bank authorization**.
   This state mutation contaminates subsequent balance lookups on shared adapter instances, causing subsequent candidate derivations for the same account to falsely report balance deficits or trigger unwarranted pacing schedules. Candidate derivation must be purely functional and read-only.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 WAVE 3 SECOND-PASS FORENSIC VERDICT                              │
├──────────────────────────┬────────────────────────────┬────────────────────────────┬─────────────┤
│ Dimension                │ Prior v0.1 Determination   │ Second-Pass v0.1.1 Verdict │ Impact      │
├──────────────────────────┼────────────────────────────┼────────────────────────────┼─────────────┤
│ 8-Predicate Test Density │ P2 (Tolerated as non-block)│ P2 (ACCEPTANCE BLOCKING)   │ UNMET GATE  │
│ Reference State Mutation │ P3 (Tolerated as non-block)│ P2 (ACCEPTANCE BLOCKING)   │ STATE LEAK  │
│ Active-Verb Labels       │ P3 (Non-blocking)          │ P3 (Non-blocking)          │ RETAINED    │
│ Report Accounting Defect │ P3 (Non-blocking)          │ P3 (Non-blocking)          │ RETAINED    │
├──────────────────────────┼────────────────────────────┼────────────────────────────┼─────────────┤
│ FINAL AUDIT DECISION     │ OPTION B (Accepted)        │ OPTION C (BLOCKED)         │ GATE HALT   │
└──────────────────────────┴────────────────────────────┴────────────────────────────┴─────────────┘
```

---

## 2. Repository Identity & Evidence Limitations

### 2.1 Repository Metadata (VERIFIED FROM CODE)
- **Repository Working Directory**: `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`
- **Active Git Branch**: `phase3/wave1-implementation` (Working tree uncommitted with Wave 2 and Wave 3 modifications)
- **Baseline Git Commit**: `01026e2` (`chore(wave1): reconcile E2E scenario lineage 19-27, policy parameter status, and DQ-07 wording`)
- **Available Git Tags**: `pex-phase3-wave1-20261008`, `pex-phase3-wave0b-runtime-20261008`, `pex-phase3-wave0a-contracts-20261008`, `v1.9.4`
- **Cumulative Regression Result (VERIFIED BY EXECUTED TEST)**: **785 passed / 0 failed / 3 warnings in 252.66s**
- **Wave 3 Targeted Suite Result (VERIFIED BY EXECUTED TEST)**: **59 passed / 0 failed / 3 warnings in 17.18s**

### 2.2 Epistemic Classification of Findings
To ensure complete transparency, every claim in this report is classified under strict epistemic standards:
- **[VERIFIED FROM CODE]**: Confirmed by direct file inspection, exact line reference, and AST verification.
- **[VERIFIED BY EXECUTED TEST]**: Confirmed by active execution of pytest test commands against the virtual environment.
- **[REPORTED BUT NOT REPRODUCED]**: Stated in prior reports but lacking direct code-level test confirmation.
- **[INFERRED]**: Logical deduction derived from architectural principles.
- **[UNVERIFIED]**: Claims that cannot be proven from current repository contents.

---

## 3. Controlling Acceptance Requirements

The controlling governance hierarchy is immutable:
1. `PeX_Wave3_Implementation_Authorization_Gate_v0.1.md` (Authoritative Gate)
2. `PeX_Phase3_Wave3_Industrialization_Architecture_and_Profile_Contract_v0.1.2.md` (Frozen Baseline)
3. `PeX_Wave3_Implementation_Report_v0.1.md` (Claims to be audited)
4. `PeX_Wave3_Implementation_Forensic_Reconciliation_v0.1.md` (Challenged Prior Review)

### Frozen Acceptance Criteria (Authorization Gate v0.1, Section 20):
> **Criterion 8 (8-Predicate Mutation)**: *"All 8 predicates independently mutation tested and proved fail-closed."*  
> **Section 18 (Test Strategy)**: *"8-Predicate Mutation: 24+ permutations independently forcing every single predicate to False."*  
> **Criterion 11 (Bank Execution Boundary)**: *"execution_owner = 'BANK' asserted on 100% of positive handoffs."*  
> **Criterion 12 (Provider Neutrality)**: *"Static AST analysis proving 0 vendor SDK imports in core modules."*  
> **Criterion 14 (Zero Regression)**: *"100% green execution maintained across all 726 inherited baseline tests."*

---

## 4. Reopening W3-FOR-01: Eight-Predicate Mutation Coverage Matrix

The canonical PeX STP decision formula is:
$$\Huge \text{STP\_ELIGIBLE} = E_{\text{suff}} \land R_{\text{det}} \land R_{\text{uniq}} \land V_{\text{det}} \land V_{\text{auth}} \land P_{\text{bank}} \land C_{\text{comp}} \land X_{\text{pre}}$$

### 4.1 Independent Predicate Audit Matrix

| Predicate | Required False Condition | Test File & Exact Function | Isolation Demonstrated? | Executed? | Actual Assertion & Result | Evidence Ref | Gap / Status | Acceptance Impact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **$E_{\text{suff}}$** (Evidence Sufficiency) | Missing mandatory balance record | `tests/wave3/test_wave3_adversarial_predicates.py::test_adversarial_missing_evidence_fails_closed` (L13-37) | **YES** (Only $E_{\text{suff}}$ forced `False`) | **YES** | `assert out.stp_eligible is False`<br>`assert out.predicate_breakdown.e_suff is False` | Code L34-36 | **COVERED** (1/8) | Non-blocking |
| **$R_{\text{det}}$** (Resolution Determinism) | Stale/invalid FX rate quote | `tests/wave3/test_wave3_adversarial_predicates.py::test_adversarial_stale_fx_rate_fails_closed` (L39-67) | **YES** (Only $R_{\text{det}}$ forced `False`) | **YES** | `assert out.stp_eligible is False`<br>`assert out.predicate_breakdown.r_det is False` | Code L65-66 | **COVERED** (2/8) | Non-blocking |
| **$R_{\text{uniq}}$** (Resolution Uniqueness) | Ambiguous resolution candidates ($N > 1$) | **NONE** in `tests/wave3/` | **NO** | **NO** | No isolated assertion for $R_{\text{uniq}} = \text{False}$ | Missing | **UNMET GAP** | **BLOCKING** |
| **$V_{\text{det}}$** (Technical Validation) | Invalid currency decimal / schema syntax error | **NONE** in `tests/wave3/` | **NO** | **NO** | No isolated assertion for $V_{\text{det}} = \text{False}$ | Missing | **UNMET GAP** | **BLOCKING** |
| **$V_{\text{auth}}$** (Authority Validation) | Non-authoritative feed source rejected | **NONE** in `tests/wave3/` | **NO** | **NO** | No isolated assertion for $V_{\text{auth}} = \text{False}$ | Missing | **UNMET GAP** | **BLOCKING** |
| **$P_{\text{bank}}$** (Bank Policy) | TR-08 credit breach policy block | `tests/wave3/test_wave3_adversarial_predicates.py::test_adversarial_tr08_zero_auto_stp_invariant` (L69-112) | **PARTIAL** (TR-08 specific; general policy cap not isolated) | **YES** | `assert out.stp_eligible is False`<br>`assert out.predicate_breakdown.p_bank is False` | Code L108-109 | **PARTIAL** (3/8) | Non-blocking (for TR-08) |
| **$C_{\text{comp}}$** (Compliance) | Sanctions / capital control block in W3 | **NONE** in `tests/wave3/` | **NO** | **NO** | No isolated assertion for $C_{\text{comp}} = \text{False}$ in Wave 3 | Missing | **UNMET GAP** | **BLOCKING** |
| **$X_{\text{pre}}$** (Preconditions) | Idempotency lock collision | `tests/wave3/test_wave3_adversarial_predicates.py::test_adversarial_idempotency_collision_fails_closed` (L114-142) | **YES** (Only $X_{\text{pre}}$ forced `False`) | **YES** | `assert out.stp_eligible is False`<br>`assert out.predicate_breakdown.x_pre is False` | Code L140-141 | **COVERED** (4/8) | Non-blocking |

### 4.2 Predicate Mutation Density Accounting
- **A. Independently Isolated Predicate Mutation Tests in Wave 3**: **4 tests** ($E_{\text{suff}}, R_{\text{det}}, P_{\text{bank}}, X_{\text{pre}}$).
- **B. Additional Non-Isolated Adversarial Tests in Wave 3**: **0 tests**.
- **C. Required Scenarios by Authorization Gate**: **24+ scenarios**.
- **D. Missing Isolated Predicates in Wave 3**: **$R_{\text{uniq}}, V_{\text{det}}, V_{\text{auth}}, C_{\text{comp}}$ (4 of 8 predicates unevidenced)**.
- **E. Gate Requirement Compliance**: **FAIL (4 / 24 scenarios implemented = 16.7% coverage)**.

> [!CAUTION]
> **Governance Determination on W3-FOR-01**:  
> The prior forensic report acknowledged that only 4 tests existed but classified this as P2 and non-blocking under the rationale that the inherited 726 tests exercised predicates globally. That rationale is **forensically rejected**. The Authorization Gate explicitly established Criterion 8 as a mandatory condition for Wave 3 acceptance. Engineering must implement the full 24+ isolated mutation suite covering all 8 predicates across all 6 profiles before acceptance can be granted.

---

## 5. Reopening W3-FOR-03: Reference Adapter State Mutation Analysis

A forensic code-trace of `InMemoryTreasuryPositionAdapter.reserve_intraday_funds(...)` and its call paths was conducted across the codebase:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                   CALL PATH TRACE: TR-02 INTRADAY FUNDS RESERVATION                              │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Exception Ingested (TR-02 Insufficient Funds)                                                 │
│    │                                                                                             │
│ 2. E2EExecutionHarness.process_input(...)                                                        │
│    │                                                                                             │
│ 3. TreasuryExposureEngine.resolve_tr02_insufficient_funds(...) [L315]                             │
│    │                                                                                             │
│ 4. AvailableBalanceEvaluator.evaluate(balance, instructed_amount) -> is_covered = True            │
│    │                                                                                             │
│ 5. [STATE MUTATION OCCURS HERE IN CORE RESOLUTION]:                                              │
│    `reservation = self.treasury_port.reserve_intraday_funds(account_number, amount)` [L345]      │
│    │                                                                                             │
│ 6. InMemoryTreasuryPositionAdapter.reserve_intraday_funds(...) [L83-84]:                         │
│    `bal.available_balance -= amount`                                                             │
│    `bal.holds_amount += amount`                                                                  │
│    │                                                                                             │
│ 7. ResolutionCandidate generated (`CAND-TR02-RELEASE-...`) [L355-364]                            │
│    │                                                                                             │
│ 8. Handoff Envelope emitted (`execution_owner = 'BANK'`)                                         │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.1 Forensic Answers to Core Inquiries:
1. **Is the method reachable outside explicit test configurations?**  
   **YES [VERIFIED FROM CODE]**. It is called on line 345 of `backend/app/services/engines/treasury_exposure_engine.py` during normal execution of `resolve_tr02_insufficient_funds()` whenever `eval_result["is_covered"]` is True.
2. **Can core resolution invoke it while merely deriving a candidate?**  
   **YES [VERIFIED FROM CODE]**. The invocation occurs directly inside candidate derivation, before any decision envelope is serialized or presented to an operator.
3. **Does it mutate state before bank authorization?**  
   **YES [VERIFIED FROM CODE]**. The balance is decremented before the case has been reviewed, approved, or dispatched.
4. **Is the mutation purely a local test-double effect, or can it affect later PeX decisions?**  
   **IT AFFECTS LATER PEX DECISIONS [VERIFIED FROM CODE]**. Because `treasury_exposure_engine` is instantiated as a singleton (`treasury_exposure_engine = TreasuryExposureEngine()`), mutating `self._balances` alters the in-memory state for all subsequent evaluations of `ACCT-CORP-USD-001`.
5. **Can the mutated balance be mistaken for authoritative bank evidence on a subsequent evaluation?**  
   **YES [VERIFIED FROM CODE]**. A subsequent call to `get_account_balance("ACCT-CORP-USD-001")` returns the reduced `available_balance` ($450,000 - 5,000 = 445,000$).
6. **Can a candidate be reported as unfunded because the adapter changed its own state?**  
   **YES [VERIFIED FROM CODE]**. If two consecutive transactions of $250,000 are processed for an account with $450,000 available balance, the first candidate derivation mutates the balance to $200,000, causing the second candidate derivation to falsely evaluate as unfunded deficit ($200,000 < 250,000$) even though no bank transaction has settled.
7. **Does the interface model a read-only position lookup, or does it expose a command that reserves funds?**  
   **IT EXPOSES A COMMAND [VERIFIED FROM CODE]**. `TreasuryPositionPort` (`backend/app/ports/treasury_position_port.py:25`) declares `@abstractmethod def reserve_intraday_funds(...)` and `release_intraday_reservation(...)`, improperly mixing read-only query semantics with transactional ledger command semantics.
8. **Does the implementation violate the intended distinction between candidate derivation and bank execution?**  
   **YES [ARCHITECTURAL DEFECT]**. PeX candidate derivation must be pure and side-effect free. PeX cannot place ledger holds; it may only package a candidate proposal for the bank to execute.

> [!CAUTION]
> **Severity Reclassification**:  
> Finding W3-FOR-03 is reclassified from **P3** to **P2 (Acceptance-Blocking Architectural Defect)**. Core candidate derivation must be refactored to be completely read-only, deriving a candidate reservation descriptor without mutating port state.

---

## 6. Policy Defaults & Runtime Fail-Closed Analysis

`W3PolicyThresholds` in `backend/app/schemas/contracts/policy_schemas.py:67-110`:

```python
class W3PolicyThresholds(BaseModel):
    # TR-02 Insufficient Funds Pacing
    allow_auto_retry_pacing: bool = True
    max_pacing_retry_seconds: float = 1800.0
    min_available_balance_buffer: float = 0.0
    max_auto_pacing_amount: float = 100000.0

    # TR-03 Nostro Rebalancing Policy
    allow_auto_nostro_sweep: bool = True
    min_nostro_operating_balance: float = 1000000.0
    max_auto_sweep_amount: float = 500000.0
    allowed_sweep_funding_accounts: List[str] = ["NOSTRO-MASTER-EUR", "NOSTRO-CENTRAL-USD"]

    # TR-04 FX Rate & Spread Tolerance
    allow_auto_rate_booking: bool = True
    max_fx_rate_age_seconds: float = 60.0
    max_fx_spread_tolerance_bps: float = 50.0
    max_auto_fx_amount: float = 250000.0

    # TR-06 Limit Reset & Waiver Policy
    allow_intraday_limit_reset_pacing: bool = True
    max_limit_reset_pacing_seconds: float = 3600.0
    max_limit_waiver_threshold: float = 500000.0
    require_credit_officer_dual_auth: bool = True

    # TR-07 Liquidity Pacing Policy
    allow_auto_liquidity_pacing: bool = True
    min_liquidity_buffer: float = 5000000.0
    max_liquidity_hold_seconds: float = 7200.0
    priority_release_tier: str = "STANDARD_COMMERCIAL"

    # TR-08 Credit Exposure Policy (MANDATORY INVARIANT)
    zero_auto_stp_on_credit_breach: bool = True
    require_senior_risk_approver: bool = True
    max_dossier_compilation_seconds: float = 300.0
```

### 6.1 Policy Fail-Closed Verification:
- **Missing Policy Handling**: When `policy_envelope = None`, `reference_policy_adapter.py` returns `policy_allows_action = False`, `is_autonomous_stp_permitted = False`, forcing $P_{\text{bank}} = \text{False}$ [VERIFIED FROM CODE].
- **Production Status**: Production bank policy integration remains **deferred / test-only**. The current runtime operates under reference in-memory configuration marked `TEST_ONLY`.

---

## 7. Financial Execution Boundary Analysis

A comprehensive audit was performed across all suspect action strings and methods:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                             FINANCIAL EXECUTION BOUNDARY CLASSIFICATION                          │
├──────────────────────────────────┬──────────────────┬─────────────────────────────┬──────────────┤
│ Method / String Identifier       │ Code Location    │ Forensic Category           │ Runtime Risk │
├──────────────────────────────────┼──────────────────┼─────────────────────────────┼──────────────┤
│ "FUNDS_RESERVED_RELEASE_PAYMENT" │ engine.py:352    │ Category B (Misleading)     │ None (Label) │
│ "EXECUTE_NOSTRO_REBALANCING_SWP" │ engine.py:462    │ Category B (Misleading)     │ None (Label) │
│ reserve_intraday_funds(...)      │ ref_treasury:68  │ Category C (Adapter State)  │ P2 Block     │
│ book_fx_rate(...)                │ ref_fx:98        │ Category C (Adapter Return) │ None (Math)  │
│ assemble_credit_risk_dossier(..) │ ref_credit:64    │ Category D (Candidate Pkg)  │ None (Safe)  │
│ execution_owner = "BANK"         │ Universal        │ Core Invariant              │ Preserved    │
└──────────────────────────────────┴──────────────────┴─────────────────────────────┴──────────────┘
```

**Classification Definitions:**
- **Category A**: Documentation/label only.
- **Category B**: Domain model or output contract naming defect (misleading active verbs).
- **Category C**: Reference adapter state mutation (local test double).
- **Category D**: Core-engine candidate packaging (safe internal logic).
- **Category E**: External financial side effect (ZERO occurrences verified).

---

## 8. Six-Profile Reassessment

| Profile ID | Canonical Name | Pattern | Engine Ownership | Zero-STP Status | Boundary Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`TR-02`** | Insufficient Funds | PAT-C / PAT-B | `TreasuryExposureEngine` | Governed Pacing | **DEFECT**: Adapter state mutated at L345 |
| **`TR-03`** | Nostro Shortfall | PAT-C / PAT-B | `TreasuryExposureEngine` | Governed Sweep | **COMPLIANT**: Sweep candidate only |
| **`TR-04`** | FX Rate Unavailable | PAT-C / PAT-A | `TreasuryExposureEngine` | Governed Quote | **COMPLIANT**: Spread & age checked |
| **`TR-06`** | Limit Breach | PAT-C / PAT-D | `TreasuryExposureEngine` | Governed Reset | **COMPLIANT**: Waiver dossier generated |
| **`TR-07`** | Liquidity Constraint| PAT-C / PAT-B | `TreasuryExposureEngine` | Governed Pacing | **COMPLIANT**: Buffer checked |
| **`TR-08`** | Credit Exposure Brch| PAT-D | `TreasuryExposureEngine` | **ZERO AUTO-STP** | **COMPLIANT**: Dual-auth invariant held |

---

## 9. Taxonomy & Roadmap Report Defects (Finding W3-FOR-04)

`PeX_Wave3_Implementation_Report_v0.1.md` Table 1 contains accounting errors:
- **Phase 2 Baseline**: Labeled as "8 Core Profiles" instead of the canonical **11 Core Profiles**.
- **Wave 2 Scope**: Labeled as "6 Profiles" instead of the canonical **3 Profiles** (`PR-06`, `ST-02`, `ST-03`).
- **Remaining Scope**: Labeled as "Wave 4 (12 Profiles)" instead of being distributed across **Waves 4–6**.

### Authoritative Canonical Profile Accounting:
- **Phase 2 Active Baseline**: 11 Profiles
- **Wave 1 Industrialized**: 9 Profiles (`DQ-01`, `03`, `04`, `07`, `08`, `09`, `PR-01`, `02`, `04`, `CO-04`, `07`)
- **Wave 2 Industrialized**: 3 Profiles (`PR-06`, `ST-02`, `ST-03`)
- **Active Pre-Wave 3**: **23 Active Profiles**
- **Wave 3 Scope**: 6 Profiles (`TR-02`, `TR-03`, `TR-04`, `TR-06`, `TR-07`, `TR-08`)
- **Active Post-Wave 3 (Target)**: **29 Active Profiles**
- **Remaining Phase 3 Scope**: **12 Profiles** (Distributed across Waves 4, 5, 6)
- **Total Closed Taxonomy**: **41 Canonical Profiles**

---

## 10. Severity-Ranked Finding Register

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 WAVE 3 FORENSIC FINDING REGISTER                                 │
├────────────┬──────────┬──────────┬────────────────────────────────────────┬──────────────────────┤
│ Finding ID │ Severity │ Profile  │ Description                            │ Acceptance Status    │
├────────────┼──────────┼──────────┼────────────────────────────────────────┼──────────────────────┤
│ W3-FOR-01  │ P2       │ ALL W3   │ 8-Predicate mutation test density gap  │ ACCEPTANCE BLOCKING  │
│ W3-FOR-03  │ P2       │ TR-02    │ Core engine invokes adapter mutation   │ ACCEPTANCE BLOCKING  │
│ W3-FOR-02  │ P3       │ TR-02/03 │ Active verb phrases in candidate labels│ NON-BLOCKING         │
│ W3-FOR-04  │ P3       │ REPORT   │ Implementation report baseline labels  │ NON-BLOCKING         │
└────────────┴──────────┴──────────┴────────────────────────────────────────┴──────────────────────┘
```

### Detailed Finding Descriptions:

#### Finding W3-FOR-01: Eight-Predicate Mutation Test Density Deficit
- **Severity**: **P2 (Acceptance-Blocking Test Coverage Defect)**
- **Requirement**: Gate v0.1 Section 18 & 20.8 (24+ isolated mutation tests).
- **Actual State**: 4 tests in `tests/wave3/test_wave3_adversarial_predicates.py`. Zero isolated tests for $R_{\text{uniq}}, V_{\text{det}}, V_{\text{auth}}, C_{\text{comp}}$ in Wave 3.
- **Remediation**: Author 24+ isolated mutation test cases covering all 8 predicates across all 6 Wave 3 profiles.

#### Finding W3-FOR-03: Reference Adapter State Mutation During Candidate Derivation
- **Severity**: **P2 (Acceptance-Blocking Architectural Defect)**
- **Requirement**: Pure read-only candidate derivation; zero state mutation before bank authorization.
- **Actual State**: `treasury_exposure_engine.py:345` calls `reserve_intraday_funds(...)`, mutating `self._balances` and leaking state into subsequent evaluations.
- **Remediation**: Refactor `TreasuryExposureEngine.resolve_tr02_insufficient_funds` to derive candidate reservation payloads purely functionally without calling state-mutating methods. Remove or isolate state mutation from read ports.

#### Finding W3-FOR-02: Active Verb Phrases in Candidate Action Strings
- **Severity**: **P3 (Non-blocking Contract Vocabulary Defect)**
- **Requirement**: Candidate resolution labels should reflect proposed candidate actions.
- **Actual State**: Labels `"FUNDS_RESERVED_RELEASE_PAYMENT"` and `"EXECUTE_NOSTRO_REBALANCING_SWEEP"` suggest execution.
- **Remediation**: Reconcile naming in schema dictionaries to `"PROPOSED_FUNDS_RESERVATION_RELEASE"` and `"PROPOSED_NOSTRO_REBALANCING_SWEEP"`.

#### Finding W3-FOR-04: Implementation Report Taxonomy Baseline Accounting Labels
- **Severity**: **P3 (Non-blocking Documentation Traceability Defect)**
- **Requirement**: Accurate reporting of Phase 2 (11 profiles) and Wave 2 (3 profiles).
- **Actual State**: Report mislabels baseline totals.
- **Remediation**: Reconcile documentation table in Governance Signoff.

---

## 11. Required Remediation & Closure Evidence

To unblock Wave 3 Forensic Acceptance, engineering must complete an authorized remediation sprint providing the following evidence:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 REQUIRED REMEDIATION EVIDENCE MATRIX                             │
├────────────┬──────────────────────────────────────────┬──────────────────────────────────────────┤
│ Finding ID │ Remediation Scope                        │ Verifiable Closure Evidence              │
├────────────┼──────────────────────────────────────────┼──────────────────────────────────────────┤
│ W3-FOR-01  │ Expand `test_wave3_adversarial_          │ 24+ distinct pytest test cases passing,  │
│            │ predicates.py` to 24+ isolated scenarios │ isolating all 8 predicates across 6 profs│
│ W3-FOR-03  │ Refactor `resolve_tr02_insufficient_     │ Code trace showing zero mutation of      │
│            │ funds` to be purely functional/read-only │ `self._balances` during candidate derive │
│ W3-FOR-02  │ Reconcile candidate string labels        │ Updated action label strings in schemas  │
│ W3-FOR-04  │ Correct Table 1 in Implementation Report │ Reconciled accounting in governance doc  │
└────────────┴──────────────────────────────────────────┴──────────────────────────────────────────┘
```

---

## 12. Final Acceptance Decision & Governance State

### 12.1 Acceptance Determination
**OPTION C — FORENSIC ACCEPTANCE BLOCKED**

Forensic acceptance of Wave 3 cannot be certified because:
1. Mandatory Acceptance Criterion 8 is unmet (only 4 of 24+ required predicate mutation scenarios exist; 4 predicates unexercised in Wave 3).
2. Core resolution logic violates read-only candidate derivation principles by invoking adapter state mutation during candidate derivation.

### 12.2 Status Summary Table

| Governance Dimension | Status Determination | Forensic Evidence Basis |
| :--- | :--- | :--- |
| **Wave 3 Implementation Status** | **CODE COMPLETE WITH BLOCKING DEFECTS** | 6 profiles, 6 ports, 6 adapters implemented |
| **Tests Independently Verified** | **785 / 785 PASSED (100% Green)** | Cumulative suite green; regression zero |
| **Mandatory Predicate Mutation Criterion**| **FAILED / UNMET (4 / 24+ Tests)** | Finding W3-FOR-01 (P2 Blocking) |
| **Reference Adapter State Isolation** | **FAILED / STATE CONTAMINATION** | Finding W3-FOR-03 (P2 Blocking) |
| **Financial Execution Boundary** | **PRESERVED (`execution_owner='BANK'`)**| Zero external live financial side effects |
| **Forensic Acceptance Decision** | **OPTION C — BLOCKED** | Requires authorized remediation sprint |
| **Governance Sign-Off Status** | **BLOCKED PENDING REMEDIATION** | Cannot proceed to Signoff under Option C |
| **Production Autonomous STP Approval** | **STRICTLY BLOCKED** | Live execution forbidden |
| **Code Changes Authorized Under This Review**| **STRICTLY PROHIBITED (READ-ONLY)** | Governed firewall enforced |
| **Next Authorized Step** | **GOVERNANCE REMEDIATION GATE** | Issue Wave 3 Remediation Authorization |

---

## 13. Next Authorized Stage

Engineering is **NOT** authorized to modify code under this review turn.

The next governed step is for the Governance Authority to issue:
**`PeX_Wave3_Remediation_Authorization_Gate_v0.1.md`** (or formal remediation directive) authorizing engineering to fix W3-FOR-01 (expanding test mutation suite to 24+ scenarios) and W3-FOR-03 (making TR-02 candidate derivation read-only).
