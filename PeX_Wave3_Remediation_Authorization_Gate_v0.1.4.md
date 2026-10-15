# PeX Phase 3 — Wave 3 Remediation Authorization Gate v0.1.4
## Governed Remediation Authorization Gate for Wave 3 Forensic Blockers (W3-FOR-01 & W3-FOR-03)

**Document Version:** v0.1.4  
**Status:** APPROVED — REMEDIATION AUTHORIZED  
**Governance Authority:** PeX Principal Solution Architect, Payments Domain Specialist, Test Assurance Lead, and Independent Governance Authority  
**Repository Working Directory:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Controlling Architecture Baseline:** `PeX_Phase3_Wave3_Industrialization_Architecture_and_Profile_Contract_v0.1.2.md` (FROZEN)  
**Controlling Implementation Authorization Gate:** `PeX_Wave3_Implementation_Authorization_Gate_v0.1.md` (FROZEN)  
**Controlling Forensic Review:** `PeX_Wave3_Implementation_Forensic_Reconciliation_v0.1.1.md` (Controlling Option C Determination)  
**Target Remediation Scope:** STRICTLY LIMITED to Authorized Workstream A (W3-FOR-03) & Authorized Workstream B (W3-FOR-01)  
**Production Autonomous STP Authorization:** **STRICTLY BLOCKED**  
**Execution Ownership Boundary:** `execution_owner = "BANK"` (Mandatory across all outputs)  

---

## 1. Document Control and Version History

### 1.1 Document Control Metadata
```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DOCUMENT CONTROL METADATA                                     │
├───────────────────────────────────┬──────────────────────────────────────────────────────────────┤
│ Dimension                         │ Detail                                                       │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Artifact Name                     │ PeX_Wave3_Remediation_Authorization_Gate_v0.1.4.md           │
│ Document Type                     │ Governed Remediation Authorization Gate                      │
│ Lifecycle State                   │ APPROVED — REMEDIATION AUTHORIZED                            │
│ Authorizing Roles                 │ Principal Solution Architect, Senior Payments Domain         │
│                                   │ Specialist, Test Assurance Lead, Governance Authority        │
│ Formal Approval Timestamp         │ 2026-10-15T12:18:06-04:00                                    │
│ Target Remediation Workstreams    │ Workstream A: W3-FOR-03 (TR-02 Read-Only State Isolation)    │
│                                   │ Workstream B: W3-FOR-01 (24+ Isolated Predicate Mutations)   │
│ Controlling Forensic Verdict      │ Option C — Forensic Acceptance Blocked (v0.1.1 Audit)        │
│ Date of Gate Formulation          │ October 8, 2026 (Approved October 15, 2026)                  │
│ Baseline Code Commit              │ 01026e2 (Working tree contains uncommitted Wave 2 & 3 code)  │
│ Reported Cumulative Test Baseline │ 785 passed / 0 failed / 3 warnings in 252.66s (Reported)     │
└───────────────────────────────────┴──────────────────────────────────────────────────────────────┘
```

### 1.2 Version History & Governance Change Log
```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    VERSION HISTORY & AUDIT TRAIL                                 │
├─────────┬──────────────┬────────────────────────┬────────────────────────────────────────────────┤
│ Version │ Date         │ Author / Role          │ Description of Governance Revisions            │
├─────────┼──────────────┼────────────────────────┼────────────────────────────────────────────────┤
│ v0.1    │ Oct 8, 2026  │ Principal Governance   │ Initial remediation gate draft following v0.1.1│
│         │              │ Reviewer               │ forensic Option C determination.               │
├─────────┼──────────────┼────────────────────────┼────────────────────────────────────────────────┤
│ v0.1.1  │ Oct 8, 2026  │ Principal Architecture │ Controlled governance corrections:             │
│         │              │ & Governance Reviewer  │ 1. Unified status to DRAFT — PENDING APPROVAL. │
│         │              │                        │ 2. Established Category A vs Category B rules. │
│         │              │                        │ 3. Hardened TR-02 read-only candidate criteria.│
├─────────┼──────────────┼────────────────────────┼────────────────────────────────────────────────┤
│ v0.1.2  │ Oct 8, 2026  │ Principal Solution     │ Second-pass corrections:                       │
│         │              │ Architect & Reviewer   │ 1. Reclassified scenario matrix as proposed.   │
│         │              │                        │ 2. Clarified decision vs ID determinism.       │
│         │              │                        │ 3. Refined no-live-connectivity stop condition.│
├─────────┼──────────────┼────────────────────────┼────────────────────────────────────────────────┤
│ v0.1.3  │ Oct 8, 2026  │ Principal Solution     │ Technical & governance corrections:            │
│         │              │ Architect & Reviewer   │ 1. Corrected TR-08 testing constraint relative │
│         │              │                        │    to Category A all-true baseline (R-01).     │
│         │              │                        │ 2. Defined 24-test requirement as executed     │
│         │              │                        │    qualifying scenarios, not functions (R-02). │
│         │              │                        │ 3. Made predicate verification interface-      │
│         │              │                        │    neutral without assuming attributes (R-03). │
│         │              │                        │ 4. Clarified E2E scenario, execution, and      │
│         │              │                        │    fixture terminology (R-04).                 │
│         │              │                        │ 5. Bounded provider-neutrality AST check to    │
│         │              │                        │    modified core production modules (R-05).    │
├─────────┼──────────────┼────────────────────────┼────────────────────────────────────────────────┤
│ v0.1.4  │ Oct 8, 2026  │ Principal Solution     │ Final technical & governance corrections:      │
│         │              │ Architect & Reviewer   │ 1. Corrected TR-08 authorization semantics:    │
│         │              │                        │    Removed unsupported blanket dual-           │
│         │              │                        │    authorization assumptions, preserving the   │
│         │              │                        │    zero-STP invariant and requiring alignment  │
│         │              │                        │    with frozen contract and bank policy (R-01).│
│         │              │                        │ 2. Clarified provider-neutrality scope:        │
│         │              │                        │    Distinguished modified-file dependency      │
│         │              │                        │    checks from architecture-wide claims (R-02).│
│         │              │                        │ 3. Verified regression protocol: Reframed      │
│         │              │                        │    regression commands and repository test     │
│         │              │                        │    paths as candidates requiring active        │
│         │              │                        │    verification against repo conventions (R-03)│
│         │              │                        │ 4. Preserved all prior valid corrections and   │
│         │              │                        │    the exact two-workstream scope.             │
└─────────┴──────────────┴────────────────────────┴────────────────────────────────────────────────┘
```

---

## 2. Executive Decision and Current Approval Status

### 2.1 Formal Decision Recommendation & Recorded Approval
Following the second-pass independent forensic audit (`PeX_Wave3_Implementation_Forensic_Reconciliation_v0.1.1.md`), which rendered **Option C — FORENSIC ACCEPTANCE BLOCKED**, this document defines the exact, bounded conditions under which engineering may remediate the two blocking P2 findings.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              REMEDIATION GATE DECISION RECORD                                    │
├──────────────────────────┬───────────────────────────────────────────────────────────────────────┤
│ Formal Decision          │ OPTION B — AUTHORIZED WITH CONDITIONS                                 │
├──────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ Approval Status          │ APPROVED — REMEDIATION AUTHORIZED                                     │
├──────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ Approval Authority       │ PeX Governance Authority (Explicit Approval Recorded 2026-10-15)       │
├──────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ Authorized Scope         │ Strictly limited to:                                                  │
│                          │ 1. Workstream A (W3-FOR-03): Refactor TR-02 candidate derivation to be│
│                          │    purely read-only; eliminate adapter state mutation in derivation.  │
│                          │ 2. Workstream B (W3-FOR-01): Implement >=24 isolated 8-predicate      │
│                          │    adversarial mutation scenarios covering all 8 predicates.          │
│                          │ 3. Wave 3 E2E Acceptance Hardening: Business-field, predicate-failure,│
│                          │    fail-closed, and TR-08 zero-autonomous-STP assertions.            │
├──────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ Explicit Exclusions      │ Zero scope expansion; zero profile additions; zero changes to 8-pred   │
│                          │ formula; zero modification of Phase 2, Wave 0A/0B, Wave 1, or Wave 2;│
│                          │ zero live payment/clearing execution; zero production autonomous STP. │
├──────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ Governance Directive     │ Remediation work is authorized strictly within Workstreams A and B.   │
│                          │ All changes must be verified against the 785-test baseline.           │
└──────────────────────────┴───────────────────────────────────────────────────────────────────────┘
```

> **GOVERNANCE DIRECTIVE — TAXONOMY ALIGNMENT RESOLUTION:**  
> The controlling specification for Wave 3 implementation, test fixtures, and engine dispatch is [`PeX_Phase3_Wave3_Industrialization_Architecture_and_Profile_Contract_v0.1.2.md`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/PeX_Phase3_Wave3_Industrialization_Architecture_and_Profile_Contract_v0.1.2.md) and [`PeX_Phase3_Governance_and_Delivery_Charter_v0.2.md`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/PeX_Phase3_Governance_and_Delivery_Charter_v0.2.md).  
> Under this controlling baseline:
> - `TR-01` = *KYC Expired* (Allocated to Wave 4)
> - `TR-02` = *Insufficient Funds* (Wave 3)
> - `TR-03` = *Nostro Shortfall* (Wave 3)
> - `TR-04` = *FX Rate Unavailable* (Wave 3)
> - `TR-05` = *Authorization Missing* (Allocated to Wave 4)
> - `TR-06` = *Limit Breach* (Wave 3)
> - `TR-07` = *Liquidity Constraint* (Wave 3)
> - `TR-08` = *Credit Exposure Breach* (Wave 3)  
>
> The earlier Generation 1 conceptual cards in `PeX_41_Exception_Taxonomy_SME_Architecture_Cards.md` represent historical drafting baselines and are formally superseded for Phase 3 execution by the Generation 2 contracts. No profile IDs in the codebase, fixtures, or contracts shall be re-keyed.

### 2.2 Explicit Separation of Governance Lifecycle States
PeX strictly segregates governance lifecycle states. Progression through one state does not imply completion of downstream states:

$$\Huge \text{Gate Recommended (Draft)} \longrightarrow \mathbf{\text{Gate Approved (CURRENT)}} \longrightarrow \mathbf{\text{Remediation Authorized}} \longrightarrow \text{Implementation Complete} \longrightarrow \text{Forensic Acceptance (v0.1.2)} \longrightarrow \text{Governance Sign-Off} \longrightarrow \text{Production Release (Blocked)}$$

- **State 1: Gate Formulation**: `COMPLETED` (v0.1 through v0.1.4).
- **State 2: Formal Gate Approval**: `COMPLETED` (Approved by Governance Authority on 2026-10-15).
- **State 3: Remediation Authorization (Current Active State)**: `ACTIVE` — Engineering authorized to execute Workstreams A & B.
- **State 4: Engineering Implementation**: In progress under authorized scope.
- **State 5: Independent Forensic Acceptance (Future Requirement)**: Re-audit under `PeX_Wave3_Implementation_Forensic_Reconciliation_v0.1.2.md`.
- **State 6: Multi-Profile Governance Sign-Off (Future Requirement)**: Cross-wave reconciliation under `PeX_Wave3_Multi_Profile_Semantic_Reconciliation_and_Governance_Signoff_v0.1.md`.
- **State 7: Production Release**: **STRICTLY BLOCKED**.

---

## 3. Purpose and Scope

### 3.1 Purpose
The purpose of this document is to establish a narrow, auditable, and enforceable governance firewall for remediating the two acceptance-blocking P2 defects identified during Wave 3 forensic review.

### 3.2 Proposed Remediation Scope
If formally approved by the designated Governance Authority, this gate will authorize engineering work on **EXACTLY TWO (2) WORKSTREAMS**:
1. **Proposed Workstream A (W3-FOR-03)**: Make `TreasuryExposureEngine.resolve_tr02_insufficient_funds` strictly read-only by eliminating in-memory state mutation during candidate derivation.
2. **Proposed Workstream B (W3-FOR-01)**: Author and execute at least 24 independently isolated predicate-mutation test scenarios covering all eight predicates ($E_{\text{suff}}, R_{\text{det}}, R_{\text{uniq}}, V_{\text{det}}, V_{\text{auth}}, P_{\text{bank}}, C_{\text{comp}}, X_{\text{pre}}$) across the six Wave 3 profiles (`TR-02`, `TR-03`, `TR-04`, `TR-06`, `TR-07`, `TR-08`).

---

## 4. Controlling Artifacts and Authority Hierarchy

### 4.1 Distinguishing Governance Authority from Evidence
PeX governance strictly distinguishes between **governing authorities** (which define normative requirements and constraints) and **evidence baselines** (which reflect observable implementation behavior to be verified):

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   AUTHORITY VS EVIDENCE HIERARCHY                                │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ GOVERNING AUTHORITIES (Normative Requirements & Bounded Scope):                                  │
│   1. PeX Evidence-Driven STP Architecture Baseline v1.1                                          │
│   2. PeX Phase 3 Industrialization Architecture v0.1.4                                           │
│   3. PeX Phase 3 Wave 3 Architecture & Profile Contract v0.1.2 (FROZEN ARCHITECTURE BASELINE)    │
│   4. PeX Wave 3 Implementation Authorization Gate v0.1 (FROZEN ACCEPTANCE CRITERIA)              │
│   5. PeX Wave 3 Remediation Authorization Gate v0.1.4 (THIS DOCUMENT — UPON FORMAL APPROVAL)     │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ CONTROLLING FORENSIC FINDINGS:                                                                   │
│   6. PeX Wave 3 Implementation Forensic Reconciliation v0.1.1 (Option C Determination)           │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ EVIDENCE ARTIFACTS (Observable Claims to be Verified):                                           │
│   7. PeX Wave 3 Implementation Report v0.1 (Historical Implementation Evidence)                  │
│   8. Repository Working Tree, Source Code, and Pytest Execution Output                           │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Invariant Precedence Rules:
1. The **Frozen Architecture Baseline (v0.1.2)** and **Implementation Authorization Gate (v0.1)** define the unalterable boundary.
2. The **Forensic Reconciliation (v0.1.1)** governs the exact findings that block acceptance.
3. Historical implementation reports and repository code are subject to audit; they do not possess authority to modify requirements.

---

## 5. Forensic Findings Being Remediated

The second-pass forensic audit (`PeX_Wave3_Implementation_Forensic_Reconciliation_v0.1.1.md`) cataloged four findings. The remediation scope proposed in this gate addresses the two acceptance-blocking P2 defects:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 WAVE 3 FORENSIC FINDINGS DISPOSITION                             │
├────────────┬──────────┬──────────┬────────────────────────────────────────┬──────────────────────┤
│ Finding ID │ Severity │ Profile  │ Finding Description                    │ Proposed Disposition │
├────────────┼──────────┼──────────┼────────────────────────────────────────┼──────────────────────┤
│ W3-FOR-01  │ P2       │ ALL W3   │ 8-Predicate mutation test density gap  │ WORKSTREAM B (BLOCK) │
│ W3-FOR-03  │ P2       │ TR-02    │ Core engine invokes adapter mutation   │ WORKSTREAM A (BLOCK) │
│ W3-FOR-02  │ P3       │ TR-02/03 │ Active verb phrases in candidate labels│ DEFERRED GOV CLEANUP │
│ W3-FOR-04  │ P3       │ REPORT   │ Implementation report baseline labels  │ DEFERRED GOV CLEANUP │
└────────────┴──────────┴──────────┴────────────────────────────────────────┴──────────────────────┘
```

- **W3-FOR-01 (P2 — Unmet Gate Criterion)**: Gate v0.1 Sections 18 & 20.8 required 24+ isolated mutation scenarios. Only 4 explicit tests exist in `tests/wave3/test_wave3_adversarial_predicates.py`, leaving $R_{\text{uniq}}, V_{\text{det}}, V_{\text{auth}}, C_{\text{comp}}$ unexercised in the Wave 3 directory.
- **W3-FOR-03 (P2 — Architectural State Contamination)**: `TreasuryExposureEngine.resolve_tr02_insufficient_funds` (`treasury_exposure_engine.py:345`) invokes `self.treasury_port.reserve_intraday_funds(...)` during candidate derivation, mutating `InMemoryTreasuryPositionAdapter._balances` prior to bank authorization.

---

## 6. Proposed Workstream A — TR-02 State Isolation

### 6.1 Objective
If approved, engineering will refactor `TreasuryExposureEngine.resolve_tr02_insufficient_funds` and associated reference adapters to guarantee that candidate derivation is **strictly read-only, functional, and side-effect free**.

### 6.2 Architectural Mandates:
1. **Zero State Mutation During Candidate Derivation**: Candidate derivation must **never** invoke `reserve_intraday_funds`, `release_intraday_reservation`, debit accounts, credit accounts, or alter any balance or hold dictionary.
2. **Pure Candidate Proposal Derivation**: When `eval_result["is_covered"]` is True, the engine must generate a structured candidate reservation proposal purely in memory without mutating port state.
3. **Semantic Decision Determinism vs Identifier Metadata**:
   - For identical input payloads and evidence, the **candidate resolution decision and structured business semantics** (e.g. `resolution_action`, `account_number`, `instructed_amount`, `currency`, `execution_owner`, `derivation_method`) must evaluate **deterministically**.
   - If candidate identifiers or proposal keys contain incidental random tokens (such as `uuid.uuid4()`), the implementation report must distinguish semantic decision equivalence from non-semantic metadata variation. The authorization gate does not prescribe a new identifier scheme.
4. **Shared Instance Independence**: Multiple evaluations sharing the same `TreasuryPositionPort` instance must never degrade available balances or cause subsequent candidate derivations to falsely report deficits.
5. **Decoupling Derivation from Bank Execution**: Bank reservation, hold placement, or ledger execution commands remain strictly outside candidate derivation, preserving the bank execution boundary (`execution_owner = "BANK"`).

### 6.3 Required Verification Tests:
Engineering must implement targeted regression tests in `tests/wave3/` (e.g. `test_wave3_tr02_state_isolation.py`) demonstrating:
- **Test A.1 (Repeated Evaluation State Invariance)**: Evaluate `resolve_tr02_insufficient_funds` 10 consecutive times against an account with available balance. Assert that `available_balance` and `holds_amount` remain completely unchanged after all 10 calls.
- **Test A.2 (Multi-Transaction State Independence)**: Evaluate two independent payment candidates against an account sharing the same adapter instance. Assert that both evaluations independently determine `is_covered = True` without the first evaluation draining funds for the second. *(Semantic note: Both candidates being individually covered against an unchanged position confirms read-only evaluation; it does not imply both can be concurrently funded or executed together in live settlement).*
- **Test A.3 (Evaluation Order Invariance)**: Evaluate payment candidates of varying sizes in forward and reverse sequence. Assert that candidate derivation decisions and adapter balances are completely invariant to evaluation order.
- **Test A.4 (Uninvoked Mutation Verification)**: Verify via mock/spy or state assertions that `reserve_intraday_funds` is zero times invoked during candidate derivation.

---

## 7. Proposed Workstream B — Predicate-Mutation Testing

### 7.1 Objective
If approved, engineering will expand `tests/wave3/` to contain **at least twenty-four (24) distinct, executed, qualifying Category A predicate-mutation scenarios**, proving that every one of the 8 canonical predicates independently blocks STP eligibility when forced to `False`.

### 7.2 The Canonical 8-Predicate Invariant:
$$\Huge \text{STP\_ELIGIBLE} = E_{\text{suff}} \land R_{\text{det}} \land R_{\text{uniq}} \land V_{\text{det}} \land V_{\text{auth}} \land P_{\text{bank}} \land C_{\text{comp}} \land X_{\text{pre}}$$

### 7.3 Normative Test-Isolation Definition
> [!IMPORTANT]
> **NORMATIVE RULE FOR ISOLATED PREDICATE MUTATION TESTS:**  
> A test qualifies as an **Independently Isolated Predicate-Mutation Test (Category A)** ONLY when:
> 1. The test establishes a valid baseline input in which **all eight predicates evaluate to `True`**.
> 2. The test applies **exactly one controlled mutation** targeting the specific predicate under test.
> 3. The test demonstrates that the **target predicate evaluates to `False`** while the **other seven predicates remain strictly `True`**.
> 4. The test verifies that **`STP_ELIGIBLE` evaluates to `False`** through the real evaluation path.
>
> Tests that cause multiple predicates to fail concurrently are valid **Compound Adversarial Tests (Category B)**; they provide defense-in-depth evidence but **do NOT count toward the minimum 24 isolated test requirement**.

### 7.4 Corrected TR-08 Authorization Semantics & Zero-STP Invariant (R-01):
The frozen architecture (`PeX_Phase3_Wave3_Industrialization_Architecture_and_Profile_Contract_v0.1.2.md` Section 9.6) mandates that `TR-08` (Credit Exposure Breach) **must never achieve autonomous STP** (`zero_auto_stp_on_credit_breach: True` / $P_{\text{bank}} = \text{False}$ autonomously).
- **Category A Baseline Boundary**: Because a standard Category A test requires establishing a baseline where all 8 predicates evaluate to `True` (including $P_{\text{bank}}=\text{True}$ permitting autonomous STP), a profile with an absolute zero-autonomous-STP invariant cannot establish an all-true autonomous STP baseline unless a specific non-autonomous evaluation path is modeled.
- **Invariant Testing Enforcement**: The TR-08 zero-STP invariant must be tested as a **Category B Compound / Invariant Test** unless the frozen profile contract demonstrably supports an isolated Category A evaluation path. TR-08 tests that cannot establish an all-true baseline must NOT be forced into Category A.
- **Workflow & Authorization Semantics**:
  - The test must verify that **autonomous STP is rejected**.
  - The evaluation result must follow the actual frozen profile contract and enforcement path (`PeX_Phase3_Wave3_Industrialization_Architecture_and_Profile_Contract_v0.1.2.md` Section 9.6: Mode 4 Senior Credit Officer review / PeX HITL Credit Review Workspace routing under `W3-BPD-06`).
  - The case must remain in the required safe, non-autonomous internal workflow or bank-controlled handoff, as applicable.
  - `execution_owner = "BANK"` remains strictly enforced for any applicable terminal handoff.
  - No live payment execution or external financial side effect occurs.
  - **No Unsupported Dual-Authorization Assumption**: The gate removes blanket wording that unconditionally mandates "dual authorization" or specific Maker-Checker steps for TR-08 unless that specific mechanism is explicitly mandated by the frozen architecture contract or authoritative bank policy. The unresolved operational workflow details beyond Mode 4 Senior Credit Officer adjudication remain designated as requiring formal contract or bank-policy verification.
- **Predicate Integrity**: Predicate meanings, safety controls, profile definitions, and frozen architectural boundaries must not be altered to make testing easier.

### 7.5 Counting Executed Qualifying Scenarios, Not Function Names:
The requirement is for **at least 24 distinct, executed, qualifying Category A scenarios**, not merely 24 function names.
- Parameterized tests may count as multiple scenarios only when each parameterized invocation independently satisfies all Category A requirements with its own distinct baseline, single mutation, target predicate, and execution evidence.
- A single test function containing multiple duplicate assertions does not satisfy the requirement.
- Compound Category B tests do not count toward the 24-test minimum.

### 7.6 Proposed Category A Scenario Candidates — Pending Contract Validation:
The following table outlines proposed candidate scenarios for Workstream B. These rows are **candidates requiring implementation validation** against existing contracts before they may be counted toward the 24-test threshold.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    PROPOSED CATEGORY A SCENARIO CANDIDATES (PENDING VALIDATION)                  │
├────┬───────────┬─────────┬───────────────────────────────────────┬───────────────────────────────┤
│ #  │ Predicate │ Profile │ Proposed Single-Mutation Candidate    │ Validation & Isolation Notes  │
├────┼───────────┼─────────┼───────────────────────────────────────┼───────────────────────────────┤
│ 1  │ E_suff    │ TR-02   │ Missing Core DDA Balance Record       │ Verify R_det doesn't co-fail  │
│ 2  │ E_suff    │ TR-03   │ Missing Nostro Position Statement     │ Verify R_det doesn't co-fail  │
│ 3  │ E_suff    │ TR-04   │ Missing FX Market Rate Quote Feed     │ Verify R_det doesn't co-fail  │
│ 4  │ E_suff    │ TR-06   │ Missing Limit Utilization Record      │ Verify R_det doesn't co-fail  │
│ 5  │ E_suff    │ TR-07   │ Missing Liquidity Reserve Record      │ Verify R_det doesn't co-fail  │
├────┼───────────┼─────────┼───────────────────────────────────────┼───────────────────────────────┤
│ 6  │ R_det     │ TR-02   │ Persistent Deficit without Pending Cr │ Verify E_suff remains True    │
│ 7  │ R_det     │ TR-03   │ Nostro Deficit exceeding Sweep Cap    │ Verify E_suff remains True    │
│ 8  │ R_det     │ TR-04   │ Stale Market Quote (Age > 60.0s TTL)  │ Verify E_suff remains True    │
│ 9  │ R_det     │ TR-07   │ Liquidity Reserve Buffer Exhausted    │ Verify E_suff remains True    │
├────┼───────────┼─────────┼───────────────────────────────────────┼───────────────────────────────┤
│ 10 │ R_uniq    │ TR-02   │ Conflicting Core Ledger Replicas (N>1)│ Demonstrates multi-candidate  │
│ 11 │ R_uniq    │ TR-03   │ Unreconciled Nostro Ledger Breaks     │ Demonstrates ambiguous recon  │
│ 12 │ R_uniq    │ TR-04   │ Dual Conflicting FX Rate Feeds        │ Demonstrates rate ambiguity   │
├────┼───────────┼─────────┼───────────────────────────────────────┼───────────────────────────────┤
│ 13 │ V_det     │ TR-02   │ Invalid Currency Decimal Syntax       │ Technical formatting failure  │
│ 14 │ V_det     │ TR-04   │ Inverted / Negative Currency Quote    │ Mathematical invalidity       │
│ 15 │ V_det     │ TR-06   │ Corrupted Limit Identifier Syntax     │ Schema syntax validation fail │
├────┼───────────┼─────────┼───────────────────────────────────────┼───────────────────────────────┤
│ 16 │ V_auth    │ TR-02   │ Non-Authoritative DDA Balance Feed    │ is_authoritative=False        │
│ 17 │ V_auth    │ TR-04   │ Non-Authoritative FX Pricing Source   │ is_authoritative=False        │
│ 18 │ V_auth    │ TR-06   │ Unverified Limit Authority Feed       │ is_authoritative=False        │
├────┼───────────┼─────────┼───────────────────────────────────────┼───────────────────────────────┤
│ 19 │ P_bank    │ TR-02   │ Amount Exceeds Auto-Pacing Policy Cap │ Policy threshold exceeded     │
│ 20 │ P_bank    │ TR-03   │ Amount Exceeds Auto-Sweep Policy Cap  │ Policy threshold exceeded     │
│ 21 │ P_bank    │ TR-04   │ FX Spread Exceeds Policy Max (50 bps) │ Spread tolerance exceeded     │
│ 22 │ P_bank    │ TR-07   │ Liquidity Pacing Exceeds Max Hold Sec │ Policy threshold exceeded     │
├────┼───────────┼─────────┼───────────────────────────────────────┼───────────────────────────────┤
│ 23 │ C_comp    │ TR-06   │ Counterparty Sanctions Match          │ Compliance constraint failed  │
│ 24 │ C_comp    │ TR-02   │ Blocked Corridor / Compliance Hold    │ Compliance constraint failed  │
├────┼───────────┼─────────┼───────────────────────────────────────┼───────────────────────────────┤
│ 25 │ X_pre     │ TR-02   │ Idempotency Lock Collision Active     │ Precondition locked           │
│ 26 │ X_pre     │ TR-07   │ Clearing Rail Emergency Settlement Hlt│ Precondition rail halted      │
└────┴───────────┴─────────┴───────────────────────────────────────┴───────────────────────────────┘
```

*(Note: Numeric thresholds such as 60.0s FX TTL and 50 bps spread are `TEST_ONLY` reference fixture values defined in `W3PolicyThresholds`, not universal bank policies).*

### 7.7 Category B — Compound Adversarial & Invariant Tests (Defense-in-Depth):
- **Test B.1 (TR-08 Zero-STP Absolute Invariant)**: Verifies that TR-08 credit breaches reject autonomous STP even when all evidence is present, enforcing safe routing to Mode 4 Senior Credit Officer review / HITL workspace with `execution_owner = "BANK"`.
- **Test B.2 (Simultaneous Missing Evidence and Stale Quote)**: Verifies multi-predicate fail-closed behavior ($E_{\text{suff}}=\text{False} \land R_{\text{det}}=\text{False}$).
- **Test B.3 (Policy Expired with Unverified Authority)**: Verifies compound policy and authority failure ($P_{\text{bank}}=\text{False} \land V_{\text{auth}}=\text{False}$).

### 7.8 Interface-Neutral Verification and Traceability Matrix:
Engineering must demonstrate single-predicate isolation through the actual evaluation path using existing observable outputs, diagnostic evidence, or appropriate test instrumentation within the approved scope.
The implementation report must provide a structured traceability matrix containing:
1. Unique Test ID (e.g. `TEST-ADV-W3-01`)
2. Target Wave 3 Profile ID (`TR-02` through `TR-08`)
3. Target Predicate Symbol ($E_{\text{suff}}$ through $X_{\text{pre}}$)
4. Baseline All-True State Confirmation
5. Single Controlled Mutation Applied
6. Observed Post-Mutation 8-Predicate State
7. Expected vs Observed `STP_ELIGIBLE` (`False`)
8. Internal Governed State / Safe Routing Verification
9. `execution_owner = "BANK"` Verification
10. Actual Test Reference and Reproducible Execution Evidence

---

## 8. Frozen Architecture and Invariants

Remediation must strictly preserve all frozen architecture baselines and core invariants:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FROZEN ARCHITECTURAL INVARIANTS                                  │
├──────────────────────────┬───────────────────────────────────────────────────────────────────────┤
│ Invariant Dimension      │ Non-Negotiable Architectural Rule                                     │
├──────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ 41-Profile Taxonomy      │ Strictly closed. Wave 3 = exactly TR-02, TR-03, TR-04, TR-06, TR-07,  │
│                          │ TR-08. Zero additional profiles authorized.                           │
│ 6 Capability Engines     │ TreasuryExposureEngine owns all 6 Wave 3 profiles. Zero engine shifts.│
│ 7 Pattern Families       │ Must use PAT-C, PAT-B, PAT-D, PAT-A. Zero new pattern families.       │
│ 8-Predicate Formula      │ Universal boolean conjunction formula is immutable. Zero bypasses.    │
│ TR-08 Zero-STP Rule      │ Credit Exposure Breach MUST NEVER achieve autonomous STP.             │
│ Bank Execution Boundary  │ execution_owner = "BANK" on 100% of terminal handoffs.                 │
│ Provider Neutrality      │ Zero vendor SDKs (AWS, Azure, GCP, LangChain, Kafka) in core modules. │
│ Production STP Block     │ Zero live payment release or clearing network integration authorized. │
└──────────────────────────┴───────────────────────────────────────────────────────────────────────┘
```

---

## 9. Explicitly Excluded Work

The following activities are **EXPLICITLY PROHIBITED** under this remediation authorization:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    EXPLICITLY EXCLUDED WORK                                      │
├───────────────────────────────────┬──────────────────────────────────────────────────────────────┤
│ Prohibited Item                   │ Operational Rationale                                        │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ 1. Taxonomy Expansion             │ Canonical 41-profile universe is frozen. No new profiles.    │
│ 2. Engine Refactoring             │ No modifications to AccountMaster, RoutingClearing, etc.     │
│ 3. Pattern Redesign               │ No new pattern families (no PAT-H).                          │
│ 4. Formula Alteration             │ 8-predicate formula cannot be modified, reordered, or relaxed│
│ 5. Prior-Wave Code Modification   │ Phase 2, Wave 0A/0B, Wave 1, Wave 2 code and tests are frozen│
│ 6. Production Connectivity        │ No live bank API, HSM, live clearing, or live DDA adapters.  │
│ 7. Production Autonomous STP      │ Production autonomous execution remains strictly forbidden.  │
│ 8. General Wave 3 Redesign        │ Remediation is limited strictly to W3-FOR-01 & W3-FOR-03.    │
│ 9. Weakening of Safety Controls   │ No lowering of thresholds or bypassing of governed reviews.  │
└───────────────────────────────────┴──────────────────────────────────────────────────────────────┘
```

---

## 10. Baseline and Regression Protocol

### 10.1 Pre-Remediation Baseline Capture:
- **Baseline Git Commit**: `01026e2`
- **Reported Cumulative Test Baseline**: **785 passed / 0 failed / 3 warnings in 252.66s** (Reported historical figure to be verified upon pre-change execution).
- **Reported Wave 3 Test Baseline**: **59 passed / 0 failed / 3 warnings in 17.18s** (Reported historical figure).

### 10.2 Regression Execution Protocol (Candidate Commands & Verification Mandate — R-03):
Engineering must follow a strict, verified regression protocol upon formal approval. The commands and paths below are **candidates to verify against repository configuration**, not unverified dogmas:

1. **Step 1: Repository Test Structure & Configuration Inspection**:
   - Engineering must inspect the actual repository structure and existing `pytest` configuration (e.g. `pytest.ini`, `pyproject.toml`, directory hierarchy) after approval and prior to running tests.
   - Verify that candidate test directories (`tests/`, `backend/tests/`) exist and represent the intended cumulative regression scope.
   - Use the repository's established virtual environment and test runner (`.\.venv\Scripts\python.exe -m pytest`).
2. **Step 2: Pre-Remediation Baseline Capture**:
   - Execute the verified candidate command: `pytest tests/ backend/tests/ -q` (or repository equivalent).
   - Record the exact command line executed, working directory, and actual discovered test counts/timings before making any code modifications.
3. **Step 3: Targeted Workstream A Suite**:
   - Execute TR-02 state isolation tests in `tests/wave3/` (e.g. `pytest tests/wave3/test_wave3_tr02_state_isolation.py -v`).
4. **Step 4: Targeted Workstream B Suite**:
   - Execute predicate mutation tests in `tests/wave3/` (verifying $\ge 24$ distinct qualifying Category A scenarios and applicable Category B invariant tests).
5. **Step 5: Full Wave 3 Suite**:
   - Execute all Wave 3 unit and adversarial test modules (`pytest tests/wave3/ -v`).
6. **Step 6: Canonical Wave 3 E2E Suite**:
   - Execute **12 E2E executions covering scenarios 31A–36B** (e.g. `pytest tests/wave3/test_wave3_e2e_scenarios.py -v`).
7. **Step 7: Full Cumulative Platform Regression**:
   - Execute the complete test suite across all discovered platform test directories (`pytest tests/ backend/tests/ -q`).
8. **Step 8: Discrepancy & Halt Protocol**:
   - If the candidate commands or prescribed paths do not match the repository structure or test runner conventions, engineering must halt and document the discrepancy before proceeding with the affected regression step.

### 10.3 Zero-Regression Requirement:
- All inherited baseline tests must remain **100% green**.
- Total cumulative test count will be reported based on actual runner output without predetermined extrapolation.
- Zero test failures, zero test errors, zero unhandled exceptions, zero new deprecation warnings.

---

## 11. Deliverables and Evidence Requirements

Upon completion of the proposed remediation work, engineering must deliver:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 REQUIRED REMEDIATION DELIVERABLES                                │
├────┬──────────────────────────────────┬──────────────────────────────────────────────────────────┤
│ #  │ Deliverable Artifact             │ Description & Required Verification Evidence             │
├────┼──────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ 1  │ Approved Remediation Gate        │ `PeX_Wave3_Remediation_Authorization_Gate_v0.1.4.md`     │
│    │                                  │ Formally approved by Governance Authority.               │
│ 2  │ TR-02 Read-Only Code Changes     │ Refactored `treasury_exposure_engine.py` with code trace │
│    │                                  │ proving zero adapter state mutation during derivation.   │
│ 3  │ TR-02 State Isolation Test Suite │ Focused tests in `tests/wave3/` proving repeated         │
│    │                                  │ evaluation invariance and instance isolation.            │
│ 4  │ Expanded Predicate Mutation Suite│ Test module in `tests/wave3/` containing >=24 distinct   │
│    │                                  │ Category A isolated mutation scenarios.                  │
│ 5  │ Full Regression Test Run Log     │ Pytest execution logs proving 100% green cumulative run. │
│ 6  │ Remediation Implementation Report│ `PeX_Wave3_Remediation_Implementation_Report_v0.1.md`    │
│    │                                  │ Documenting exact changes, traceability, and metrics.    │
│ 7  │ Post-Remediation Forensic Package│ Ready for independent read-only review under v0.1.2 audit│
└────┴──────────────────────────────────┴──────────────────────────────────────────────────────────┘
```

---

## 12. Acceptance Criteria

Remediation will be considered complete and ready for forensic re-audit only when all of the following exit criteria are independently verified:

### 12.1 Workstream A (W3-FOR-03) Exit Criteria:
1. `TreasuryExposureEngine.resolve_tr02_insufficient_funds` contains zero calls that mutate `self.treasury_port` state during candidate derivation.
2. `InMemoryTreasuryPositionAdapter.reserve_intraday_funds` is not invoked during candidate derivation.
3. 10 consecutive evaluations of an account leave available balances and holds completely unchanged.
4. Consecutive transactions sharing the same adapter instance evaluate without cross-transaction balance leakage.
5. All 12 E2E executions covering scenarios 31A–36B pass without regression.

### 12.2 Workstream B (W3-FOR-01) Exit Criteria:
1. Test suite contains **at least 24 independently isolated Category A qualifying scenarios**.
2. All 8 predicates ($E_{\text{suff}}, R_{\text{det}}, R_{\text{uniq}}, V_{\text{det}}, V_{\text{auth}}, P_{\text{bank}}, C_{\text{comp}}, X_{\text{pre}}$) have dedicated Category A scenarios proving fail-closed blocking behavior.
3. Every Category A scenario demonstrates that the single forced mutation results in `STP_ELIGIBLE = False` while other predicates evaluate `True`.
4. High AI confidence or plausible candidate data is proved incapable of overriding a failed predicate.
5. All 24+ Category A scenarios execute cleanly and pass through the real evaluation path.

### 12.3 Cumulative Program Exit Criteria (Distinguishing Dependency Checks from Architecture-Wide Claims — R-02):
1. **Regression Success**: Full cumulative regression suite passes with **zero failures and zero regressions** across all inherited tests.
2. **Remediation-Level Dependency Verification**:
   - AST static analysis confirms **zero new vendor SDK imports** (AWS, Azure, GCP, LangChain, Kafka, etc.) across the **actual inventory of modified production core modules**.
   - The implementation report must identify the exact modified production files analyzed, the static checks executed, any dependencies introduced, and reproducible evidence.
3. **Architecture-Wide Provider-Neutrality Scope Limitation**:
   - Passing a narrow AST check on modified remediation files confirms remediation-level dependency compliance; it must NOT be claimed as proof of architecture-wide provider neutrality unless an adequately scoped audit across all core modules is explicitly performed and evidenced.
4. **Execution Ownership**: `execution_owner = "BANK"` is asserted on 100% of positive resolution handoffs.
5. **Implementation Report**: `PeX_Wave3_Remediation_Implementation_Report_v0.1.md` is authored and submitted with complete traceability.

---

## 13. Roles and Approval Authority

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 GOVERNANCE & APPROVAL ROLES                                      │
├───────────────────────────────────┬──────────────────────────────────────────────────────────────┤
│ Role Title                        │ Governance Authority & Responsibilities                      │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Principal Solution Architect      │ Formulates and approves remediation gate; enforces boundary  │
│ Senior Payments Domain Engineer   │ Reviews domain semantics, RTGS, DDA, Nostro, and FX logic    │
│ Test Assurance Lead               │ Audits test isolation, predicate coverage, and regression    │
│ Independent Forensic Auditor      │ Performs independent post-remediation forensic audit (v0.1.2)│
│ Core Engineering Team             │ Executes authorized code refactoring and test implementation │
└───────────────────────────────────┴──────────────────────────────────────────────────────────────┘
```

---

## 14. Stop Conditions and Escalation

Engineering **MUST IMMEDIATELY HALT WORK AND ESCALATE TO GOVERNANCE** if any of the following conditions occur:

1. Remediation of TR-02 requires altering the canonical definition of `TR-02` or `PAT-C`.
2. The 8-predicate STP formula requires modification, relaxation, or predicate bypass.
3. The state isolation fix cannot be achieved without modifying inherited Phase 2, Wave 1, or Wave 2 files.
4. Testing cannot exercise the actual predicate-enforcement path without requiring live banking connectivity, live external financial systems, or external financial side effects.
   > **Note on Test Double Boundary**: Tests must exercise the actual predicate-enforcement and resolution-evaluation path without requiring live banking connectivity, live external financial systems, or external financial side effects. Existing ports, controlled fixtures, and test doubles may be used to isolate external dependencies, provided the test demonstrates the behavior of the actual enforcement path rather than a disconnected mock implementation.
5. Any remediation change introduces direct ledger mutation or external financial side effects.
6. The cumulative test suite experiences unresolvable regression failures in prior-wave tests.
7. Remediation requires adding new SPI ports or vendor SDK dependencies.
8. A new exception profile is deemed necessary to resolve a test scenario.
9. Pre-remediation baseline test execution diverges from reported historical passing tests.
10. Proposed changes exceed the authorized scope of `TreasuryExposureEngine`, reference treasury position adapter, and `tests/wave3/`.

---

## 15. Residual Risks and Limitations

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 RESIDUAL RISK & MITIGATION REGISTER                              │
├────┬────────────────────────────┬──────────┬─────────────────────────────────────────────────────┤
│ #  │ Identified Residual Risk   │ Severity │ Governed Mitigation Strategy                        │
├────┼────────────────────────────┼──────────┼─────────────────────────────────────────────────────┤
│ 1  │ Reference Adapter Drift    │ Medium   │ Clearly label in-memory adapters as TEST_ONLY.      │
│    │ vs Live Bank Ledger APIs   │          │ Live banking connectors deferred to production gate.│
│ 2  │ Test Suite Execution Time  │ Low      │ 24+ new tests add ~5-10s to pytest run. Optimize    │
│    │ Expansion                  │          │ in-memory fixture construction.                     │
│ 3  │ Downstream Wave Scope      │ Low      │ Strict governance firewall prevents Wave 4 leakage. │
│    │ Boundary Contamination     │          │ Waves 4-6 remain protected and unauthorized.        │
└────┴────────────────────────────┴──────────┴─────────────────────────────────────────────────────┘
```

---

## 16. Formal Authorization Decision Record

```
====================================================================================================
                             FORMAL REMEDIATION AUTHORIZATION RECORD
====================================================================================================
Formal Decision:                        OPTION B — AUTHORIZED WITH CONDITIONS

Decision Status:                        APPROVED — REMEDIATION AUTHORIZED

Designated Approver Role:               Principal Architecture & Governance Authority

Approver Identity:                      PeX Governance Authority

Approval Date:                          2026-10-15T12:18:06-04:00

Authorized Scope:                       1. Workstream A: Refactor TreasuryExposureEngine TR-02
                                           candidate derivation to be purely functional and
                                           read-only; eliminate reference adapter state mutation.
                                        2. Workstream B: Implement >=24 Category A isolated
                                           8-predicate mutation scenarios covering all 8 predicates.
                                        3. Wave 3 E2E Acceptance Hardening: Business-field,
                                           predicate-failure, fail-closed, and TR-08 zero-autonomous-
                                           STP assertions.
                                        4. Author PeX_Wave3_Remediation_Implementation_Report_v0.1.md.

Mandatory Conditions:                   1. Zero scope expansion beyond Workstream A and B.
                                        2. Zero live payment/clearing execution integration.
                                        3. Zero production autonomous STP enablement.
                                        4. 100% green execution across full cumulative test suite.
                                        5. Formal independent post-remediation forensic review required.

Governance Position:                    FORMALLY APPROVED. ENGINEERING AUTHORIZED TO COMMENCE WORK.
====================================================================================================
```

---

## 17. Post-Implementation Independent Forensic Review

Upon completion of remediation and publication of `PeX_Wave3_Remediation_Implementation_Report_v0.1.md`, an independent red-team reviewer will perform:
**`PeX_Wave3_Implementation_Forensic_Reconciliation_v0.1.2.md`**

The forensic reviewer will independently audit:
1. Code-level elimination of state mutation in `resolve_tr02_insufficient_funds`.
2. Traceability and execution of all 24+ Category A isolated predicate mutation scenarios.
3. Proof of single-predicate isolation across all 8 predicates.
4. Cumulative regression suite execution (asserting 100% green status).
5. AST provider neutrality verification across modified production core modules (distinguishing local dependency checks from architecture-wide claims).

If all criteria are met, the forensic reviewer will issue **OPTION A — FORENSICALLY ACCEPTED**, clearing Wave 3 for Governance Sign-Off (`PeX_Wave3_Multi_Profile_Semantic_Reconciliation_and_Governance_Signoff_v0.1.md`).

---

## 18. Final Governance Status

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   FINAL GOVERNANCE POSITION                                      │
├───────────────────────────────────┬──────────────────────────────────────────────────────────────┤
│ Dimension                         │ Authoritative Determination                                  │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Wave 3 Implementation Status      │ FORENSIC ACCEPTANCE BLOCKED (Remediation In Progress)        │
│ Governance Sign-Off Status        │ BLOCKED PENDING REMEDIATION & FORENSIC CLOSURE               │
│ Production Autonomous STP Status  │ STRICTLY BLOCKED (Zero Live Execution Authorized)            │
│ Live Payment Network Integration  │ STRICTLY PROHIBITED (Test / Simulation Only)                 │
│ Code Remediation Permission       │ APPROVED — REMEDIATION AUTHORIZED (Workstreams A & B)        │
│ Next Authorized Milestone         │ Engineering Execution of Workstreams A & B and Report v0.1   │
└───────────────────────────────────┴──────────────────────────────────────────────────────────────┘
```

> **GOVERNANCE DIRECTIVE:**  
> Explicit governance approval has been recorded on 2026-10-15. Engineering is authorized to commence implementation of Workstreams A and B in strict accordance with the bounded acceptance criteria and taxonomy clarifications set forth herein.
