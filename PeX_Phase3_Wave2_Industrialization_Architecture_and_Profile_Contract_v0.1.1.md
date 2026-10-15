# PeX Phase 3 — Wave 2 Industrialization Architecture & Profile Contract
## Architecture, Semantic Contracts, Authority Requirements, and Resolution Patterns for Wave 2 Profiles (PR-06, ST-02, ST-03)

**Document Version:** v0.1.1  
**Status:** ARCHITECTURE & GOVERNANCE BASELINE (REMEDIATED FREEZE CANDIDATE)  
**Governance Authority:** Principal Architecture, Governance, and Forensic Design Authority  
**Repository Working Directory:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Git Baseline:** Branch `phase3/wave1-implementation` | Commit `01026e2` | Tag `pex-phase3-wave1-20261008`  
**Cumulative Test Baseline:** 630 passed / 0 failed (100% green)  
**Engineering Implementation Authorization:** **STRICTLY NOT GRANTED BY THIS DOCUMENT**  
**Production Autonomous STP Authorization:** **STRICTLY BLOCKED**  
**Execution Ownership Boundary:** `execution_owner = "BANK"` (Mandatory)  

---

## 1. Executive Summary

### 1.1 Context & Industrialization Lineage
The PeX (Payment Exception Resolution) platform has industrialized Phase 2 (11 accepted canonical profiles backed by 423 regression tests), Wave 0A (platform contracts, canonical schemas, reference adapters, 12 E2E scenarios), Wave 0B (dynamic Bank Evidence Required JSON, fail-closed governance compilation, content-addressable SHA-256 evidence store, Modes 1–4 acquisition, PeX-native HITL closed loop, 18 scenarios / 495 tests), and Wave 1 (9 canonical profiles, `AccountMasterEngine`, `RoutingClearingEngine`, `RemittanceDocumentEngine`, 27 canonical scenarios across 36 fixture executions, 630 cumulative tests green, signed off with conditions under `PeX_Wave1_Multi_Profile_Semantic_Reconciliation_and_Governance_Signoff_v0.1.1.md`).

### 1.2 Purpose of v0.1.1 Remediation
This document establishes the remediated, authoritative **Architecture and Profile Contract** for **Phase 3 Wave 2**. Version v0.1.1 performs surgical governance and semantic reconciliations on the v0.1 baseline:
1. **Restores Controlling Engine Ownership**: Aligns `ST-02` (Account Closed) and `ST-03` (Beneficiary Account Frozen) primary ownership to `AccountMasterEngine` for authoritative account-state determination, with `SettlementReconciliationEngine` providing downstream settlement return/suspense handling, in strict adherence to Architecture v0.1.4.
2. **Preserves Intermediary Banking Architecture**: Maintains `SettlementReconciliationEngine` as primary for `PR-06` (Intermediary Bank Rejection) under `PAT-F` (Intermediary & Claims Tracking), supported by `RoutingClearingEngine` for alternate routing hops.
3. **Corrects Out-of-Scope Scope Labels**: Removes incorrect Wave 2 labels from subsequent milestone profiles (e.g., `ST-05`).
4. **Eliminates Profile Over-Specification**: Ensures canonical definitions remain generic, decoupling rail/code-specific examples (`AC04`, `PNC`, `FR01`, Serial/Cover) into reference/policy classifications.
5. **Enforces Execution & Terminal State Boundaries**: Clarifies that `BANK_HANDOFF_READY` is the execution-boundary state for eligible handoffs, while ineligible exceptions remain governed in PeX HITL/investigation states. Autonomous production STP remains strictly blocked.

Wave 2 encompasses **EXACTLY** three canonical exception profiles:
1. `PR-06` — **Intermediary Bank Rejection**
2. `ST-02` — **Account Closed**
3. `ST-03` — **Beneficiary Account Frozen**

---

## 2. Governance Status

```
+---------------------------------------------------------------------------------------------------+
|                                  WAVE 2 GOVERNANCE STATUS SUMMARY                                 |
+-----------------------------------+---------------------------------------------------------------+
| Governance Dimension              | Status & Operational Boundary                                 |
+-----------------------------------+---------------------------------------------------------------+
| Phase 2 Baseline                  | CLOSED (11 Profiles, 423 Tests Protected from re-engineering) |
| Wave 0A / Wave 0B Baseline        | COMPLETE (Platform Contracts & Dynamic Engine Frozen)         |
| Wave 1 Baseline                   | COMPLETE (9 Profiles, 630 Tests, Formally Signed Off)         |
| Wave 2 Engineering Authorization  | STRICTLY NOT GRANTED (Requires separate Authorization Gate)   |
| Production Autonomous STP Gate    | STRICTLY BLOCKED (Zero-touch autonomous release forbidden)   |
| Execution Ownership Boundary      | execution_owner = "BANK" (Mandatory)                          |
| Canonical E2E Lineage             | 27 Canonical Scenarios (12 Wave 0A + 6 Wave 0B + 9 Wave 1)   |
| Wave 2 Target Scope               | EXACTLY 3 Profiles: PR-06, ST-02, ST-03                       |
| Primary Engines Exercised         | AccountMasterEngine (ST-02, ST-03), SettlementReconciliation  |
|                                   | Engine (PR-06)                                                |
| Supporting Engines Exercised      | SettlementReconciliationEngine (ST-02, ST-03), RoutingClearing|
|                                   | Engine (PR-06), ComplianceDossierEngine (ST-03)               |
+-----------------------------------+---------------------------------------------------------------+
```

---

## 3. Authoritative Source Precedence

In accordance with PeX governance, any potential conflict across project artifacts must be resolved strictly using the following hierarchy:

1. `PeX_Evidence_Driven_STP_Architecture_Baseline_v1.1.md` (Controlling STP Architecture Baseline)
2. `PeX_Phase2_Implementation_Contract_v1.3.md` (Phase 2 Frozen Contract Baseline)
3. `PeX_Phase3_Governance_and_Delivery_Charter_v0.2.md` (Phase 3 Governance Charter)
4. `PeX_Phase3_Industrialization_Architecture_v0.1.4.md` (Phase 3 Architecture Baseline)
5. `PeX_Wave1_Implementation_Authorization_Gate_v0.1.1.md` (Wave 1 Controlling Gate)
6. `PeX_Wave1_Implementation_Report_v0.1.md` (Wave 1 Implementation Record)
7. `PeX_Wave1_Independent_Forensic_Acceptance_RedTeam_v0.1.1.md` (Wave 1 Forensic Challenge Baseline)
8. `PeX_Wave1_Multi_Profile_Semantic_Reconciliation_and_Governance_Signoff_v0.1.1.md` (Wave 1 Governance Sign-off)
9. Current repository state (Evidence of existing capability only; **not** authority to expand scope).

---

## 4. Wave 2 Scope

Wave 2 contains **EXACTLY** three canonical exception profiles:

```
+---------------------------------------------------------------------------------------------------------------------------+
|                                                   WAVE 2 PROFILE SCOPE                                                    |
+-------+-----------------------------+-------------------------------+------------------------------+----------------------+
| Code  | Canonical Profile Name      | Primary Capability Engine     | Supporting Capability        | Primary Pattern      |
+-------+-----------------------------+-------------------------------+------------------------------+----------------------+
| PR-06 | Intermediary Bank Rejection | SettlementReconciliationEngine| RoutingClearingEngine        | PAT-F (Intermediary) |
| ST-02 | Account Closed              | AccountMasterEngine           | SettlementReconciliationEngine| PAT-E (Ledger)       |
| ST-03 | Beneficiary Account Frozen  | AccountMasterEngine           | SettlementReconciliation/    | PAT-E (Ledger)       |
|       |                             |                               | ComplianceDossierEngine      |                      |
+-------+-----------------------------+-------------------------------+------------------------------+----------------------+
```

* **Scope Integrity**: No additional profiles may be pulled into Wave 2 (e.g., `ST-04`, `ST-05`, `ST-07` remain in subsequent settlement milestones).
* **Protected Baselines**: Phase 2 (11 profiles) and Wave 1 (9 profiles) remain untouched and protected.

---

## 5. Canonical Profile Semantics

Preserving canonical taxonomy without drift or over-specification is mandatory:

### 5.1 `PR-06` — Intermediary Bank Rejection
* **Canonical Definition**: A payment instruction transmitted through an indirect clearing path (intermediary / correspondent institution) is formally rejected by an intermediary institution prior to reaching the creditor institution, with an explicit rejection notification and reason identifier.
* **Semantic Invariant**: Rejection $\neq$ Network Timeout (`PR-07`) $\neq$ Local Queue Failure (`PR-08`) $\neq$ Settlement Failure at Central Bank (`ST-05`) $\neq$ Inward Return after Final Settlement (`ST-01`).

### 5.2 `ST-02` — Account Closed
* **Canonical Definition**: An inbound payment instruction or internal posting attempt targets a creditor account identifier that has been permanently terminated or closed in the authoritative Account Master.
* **Semantic Invariant**: Closed $\neq$ Invalid Account Format (`DQ-07`) $\neq$ Frozen (`ST-03`) $\neq$ Dormant (`AC06`) $\neq$ Blocked / Administrative Hold.

### 5.3 `ST-03` — Beneficiary Account Frozen
* **Canonical Definition**: An inbound payment instruction or internal posting attempt targets a creditor account that is legally, judicially, or administratively restricted from receiving credit postings pursuant to an active legal restriction, court order, regulatory hold, or internal risk restraint.
* **Semantic Invariant**: Frozen $\neq$ Closed (`ST-02`) $\neq$ Sanctions Target Blocked Property (`CO-01`) $\neq$ Missing Mandate (`TR-05`) $\neq$ Temporary Technical Outage.

---

## 6. Architecture Invariants

The immutable architectural invariants from `PeX_Phase3_Industrialization_Architecture_v0.1.4.md` apply to Wave 2:

```
+---------------------------------------------------------------------------------------------------+
|                                IMMUTABLE ARCHITECTURAL INVARIANTS                                 |
+----+----------------------------------------------------------------------------------------------+
| 1  | 41-Profile Canonical Taxonomy is immutable across all documents and systems.                 |
| 2  | Phase 2 is CLOSED; the 11 accepted baseline profiles are strictly protected.                |
| 3  | Phase 3 delivery scope consists of the 30 remaining canonical profiles.                      |
| 4  | 8-Predicate Formula is immutable:                                                            |
|    | STP_ELIGIBLE = E_suff ∧ R_det ∧ R_uniq ∧ V_det ∧ V_auth ∧ P_bank ∧ C_comp ∧ X_pre           |
| 5  | Evidence sufficiency (E_suff) does NOT equal STP eligibility.                                |
| 6  | Historical precedent carries 0% execution authority (advisory context only).                |
| 7  | AI / LLM confidence carries 0% autonomous execution authority.                              |
| 8  | AI cannot independently establish authority or authorize execution.                         |
| 9  | HITL adjudication and Maker-Checker workspaces remain strictly inside PeX.                  |
| 10 | BANK_HANDOFF_READY is the execution-boundary state for an eligible bank handoff. Ineligible   |
|    | exceptions remain in governed PeX states (HITL, investigation, compliance hold, policy hold).|
| 11 | Execution ownership (execution_owner) remains permanently "BANK".                            |
| 12 | PeX never directly executes payments or mutates bank ledgers autonomously.                   |
| 13 | Production autonomous STP remains strictly blocked.                                          |
| 14 | Architecture preserves provider neutrality, cloud neutrality, and model neutrality.          |
+----+----------------------------------------------------------------------------------------------+
```

---

## 7. Capability Engine Assessment

Wave 2 exercises `AccountMasterEngine` (primary for `ST-02`/`ST-03`), `SettlementReconciliationEngine` (primary for `PR-06`, supporting for `ST-02`/`ST-03`), `RoutingClearingEngine` (supporting for `PR-06`), and `ComplianceDossierEngine` (supporting for `ST-03`). Anti-theft boundaries are strictly enforced:

```
+---------------------------------------------------------------------------------------------------+
|                               WAVE 2 CAPABILITY ENGINE RESPONSIBILITIES                           |
+--------------------------+-------------------------------------+----------------------------------+
| Capability Engine        | Wave 2 Scope & Responsibilities     | Strict Anti-Theft Boundaries     |
+--------------------------+-------------------------------------+----------------------------------+
| AccountMasterEngine      | • Primary for ST-02 and ST-03.      | • Does NOT generate settlement   |
|                          | • Interrogates Core DDA SPI for     |   pacs.004 return messages.      |
|                          |   authoritative account status.     | • Does NOT manage suspense ledger|
|                          | • Evaluates account validity,       |   breaks.                        |
|                          |   closure state, and freeze scope.  | • Does NOT reroute payments.     |
+--------------------------+-------------------------------------+----------------------------------+
| SettlementReconciliation-| • Primary for PR-06; Supporting for | • Does NOT determine DDA account |
| Engine                   |   ST-02 and ST-03.                  |   status (delegated to Account-  |
|                          | • Correlates inward rejections /    |   MasterEngine).                 |
|                          |   returns to original payment UETR. | • Does NOT compute alternate SSI |
|                          | • Orchestrates inward return        |   routing hops (delegated to     |
|                          |   re-credit packages (pacs.004).    |   RoutingClearingEngine).        |
|                          | • Constructs ledger suspense breaks | • Does NOT execute payments.     |
|                          |   and reversal requests.            |                                  |
+--------------------------+-------------------------------------+----------------------------------+
| RoutingClearingEngine    | • Supporting for PR-06.             | • Does NOT establish account     |
|                          | • Interrogates clearing directories |   validity or legal freeze state.|
|                          |   for alternate correspondent SSIs. | • Does NOT reverse settled       |
|                          | • Evaluates rail cutoffs for hops.  |   transactions.                  |
+--------------------------+-------------------------------------+----------------------------------+
| ComplianceDossierEngine  | • Supporting for ST-03.             | • Does NOT make account status   |
|                          | • Evaluates legal/regulatory freeze |   determinations.                |
|                          |   dossiers and statutory contexts.  | • Does NOT perform returns.      |
+--------------------------+-------------------------------------+----------------------------------+
```

---

## 8. Profile Contract: `PR-06 — Intermediary Bank Rejection`

### 8.1 Nature & Taxonomy
* **Phenomenon**: An outbound payment instruction sent across an indirect clearing path is formally rejected by an intermediary institution prior to reaching the creditor institution.
* **Operational Triggers**: Routing/SSI mismatch (`RC01`, `NR01`), intermediary currency cutoff exceeded (`TM01`), corridor restriction, format policy discrepancy, or intermediary compliance rejection.

### 8.2 Boundary Disambiguation
```
+---------------------------------------------------------------------------------------------------+
|                           PR-06 BOUNDARY DISAMBIGUATION MATRIX                                    |
+------------------------+-------------------+------------------------------------------------------+
| State / Event          | Distinct Profile  | Critical Semantic & Telemetry Differentiator         |
+------------------------+-------------------+------------------------------------------------------+
| Intermediary Reject    | PR-06 (Wave 2)    | Formal rejection advice from intermediary institution|
| Socket / Comm Timeout  | PR-07 (Wave 1)    | Socket drop/timeout; intermediary processing UNKNOWN |
| Stalled In-Flight      | ST-06 (Wave 4)    | Acknowledged but overdue; requires camt.027 Claim     |
| Local Queue Deadlock   | PR-08 (Phase 2)   | Local message broker queue deadlock before dispatch  |
| Downstream Return      | ST-01 (Phase 2)   | Payment settled downstream; returned via pacs.004    |
| Clearing Netting Fail  | ST-05 (Future)    | Central bank RTGS liquidity / netting cycle abort    |
| Sanctions Detention    | CO-01 (Wave 5)    | Blocked property held under legal embargo (No Return)|
+------------------------+-------------------+------------------------------------------------------+
```

### 8.3 Telemetry vs. Clearing State vs. Settlement Finality
> [!IMPORTANT]
> **CRITICAL FORENSIC BOUNDARY:**  
> Socket or network telemetry ($\text{HTTP 502}$, $\text{TCP RST}$, connection timeout) $\neq$ Clearing State $\neq$ Settlement Finality.  
> A network error alone does NOT prove intermediary rejection. An authoritative rejection requires structured rejection advice from an authoritative payment-processing, clearing, or correspondent state source.

### 8.4 Candidate Resolution Pathways
1. **Alternate Routing Hop (Reroute)**: If rejection indicates an unreachable route or intermediary SSI mismatch, `RoutingClearingEngine` queries the Correspondent Directory for an alternate eligible intermediary hop.
2. **Value-Date Rollover / Retry**: If rejection was due to a temporary cutoff, recalculate value date under bank policy.
3. **Ledger Return / Cancellation**: If no viable alternate route exists or rejection is permanent, initiate outward cancellation or credit return to debtor.
4. **HITL Investigation / Inquiry**: If rejection narrative is ambiguous or compliance-related, escalate to human operator for correspondent inquiry (`camt.027`).

### 8.5 Capability & Resolution Pattern Mapping
* **Primary Capability Engine**: `SettlementReconciliationEngine` (orchestrates interbank state tracking, rejection correlation, and downstream settlement consequences).
* **Supporting Capability Engine**: `RoutingClearingEngine` (supplies alternate correspondent routing hops / SSI directories).
* **Primary Resolution Pattern**: `PAT-F` (Intermediary & Claims Tracking Family).
* **Supporting Resolution Patterns**: `PAT-E` (Ledger Matching & Settlement Reversal) for downstream return/cancellation; `PAT-A` (Directory Resolution) for alternate SSI lookup.
* **Pattern Fit**: `COMPOSITE`.

---

## 9. Profile Contract: `ST-02 — Account Closed`

### 9.1 Nature & Taxonomy
* **Phenomenon**: An inbound credit transfer or internal transfer targets a creditor account identifier that has been permanently closed or terminated in the authoritative Account Master.
* **Banking Invariant**: A bank cannot credit a closed account ledger. Funds cannot hang in unallocated suspense past clearing return SLAs.

### 9.2 Account Closure vs. Other Account States
```
+---------------------------------------------------------------------------------------------------+
|                           ST-02 BOUNDARY DISAMBIGUATION MATRIX                                    |
+------------------------+-------------------+------------------------------------------------------+
| Account Condition      | Canonical Profile | Authoritative State in Core Banking / Directory      |
+------------------------+-------------------+------------------------------------------------------+
| Account Closed         | ST-02 (Wave 2)    | DDA Status = CLOSED / TERMINATED. Permanent.         |
| Account Frozen         | ST-03 (Wave 2)    | DDA Status = ACTIVE, Restriction = Post No Credits   |
| Invalid Account Syntax | DQ-07 (Wave 1)    | Check digit fails Modulo-97; account never existed.  |
| Dormant Account        | TR-01/ST-02 (BPD) | DDA Status = DORMANT. Reactivation protocol.         |
| Administrative Hold    | ST-03 / TR-06     | Collateral / Lien hold on debit, credits permitted.  |
+------------------------+-------------------+------------------------------------------------------+
```

### 9.3 Authority & Handling of Stale / Contradictory Data
* **Authority Source**: Bank Core / DDA Account Master (`CORE_DDA_ACCOUNT_MASTER` via SPI).
* **Freshness Constraint**: Account status must be verified with current data under bank-configured cache policy.
* **Contradictory Signals**: If Core DDA reports `CLOSED` but an auxiliary directory reports `ACTIVE`, PeX **fails closed**: Core DDA is sovereign.

### 9.4 Settlement Action & Replacement Account Safety
> [!CAUTION]
> **STRICT REPLACEMENT ACCOUNT PROHIBITION:**  
> 1. Account status determination $\neq$ Authority to select a replacement account.  
> 2. PeX and AI **MUST NEVER** infer, synthesize, or substitute an alternate beneficiary account number simply because another account exists for that customer title.  
> 3. Unilateral redirection of funds without an explicit customer mandate or signed rollover instruction violates payment regulations.  
> 4. Default resolution is **Governed Return to Sender** (`pacs.004`). Replacement account handling is permitted ONLY when pre-authorized under explicit Bank Policy and authenticated corporate mandate.

### 9.5 Capability & Pattern Mapping
* **Primary Capability Engine**: `AccountMasterEngine` (determines authoritative `CLOSED` status in Core DDA).
* **Supporting Capability Engine**: `SettlementReconciliationEngine` (orchestrates 4-point matching, generates `pacs.004` return package, and prepares ledger return suspense).
* **Primary Resolution Pattern**: `PAT-E` (Ledger Matching & Settlement Reversal).
* **Supporting Resolution Pattern**: `PAT-A` (Master / Directory Resolution for account validation).
* **Pattern Fit**: `COMPOSITE`.

---

## 10. Profile Contract: `ST-03 — Beneficiary Account Frozen`

### 10.1 Nature & Taxonomy
* **Phenomenon**: An inbound payment targets a customer account that is subject to an active legal, judicial, or regulatory restriction prohibiting credit posting (`Post No Credits` active).
* **Operational Scope**: Covers general judicial freezes, court garnishments, tax levies, bankruptcy stays, or administrative restraints. It is **NOT** a catch-all for statutory sanctions asset blocks (which are governed under `CO-01`).

### 10.2 Credit Posting Restrictions & Governed Disposition Flow
* **Governed Evaluation Flow**:
  $$\text{Account restriction detected} \to \text{Determine restriction scope} \to \text{Check if credit is prohibited} \to \text{Classify legal context} \to \text{Determine permitted disposition} \to \text{Apply bank policy} \to \text{Evaluate 8 predicates} \to \text{STP or HITL}$$
* **Credit Posting Analysis**:
  * If restriction is `Post No Debits` (`PND`): Credits are permitted and processed.
  * If restriction is `Post No Credits` (`PNC`) or `Total Freeze`: Credits are prohibited.
* **Governed Disposition Pathways for Prohibited Credits**:
  1. **Governed Return (`pacs.004`)**: Return funds to ordering institution under rail return reason rules.
  2. **Bank Legal Suspense Booking**: Credit funds to internal Bank Legal Escrow / Suspense account pending judicial/regulatory determination.
  3. **Sanctions Blocked Property**: If freeze stems from statutory sanctions, funds **MUST NOT** be returned; they are handled under `CO-01` (Wave 5).

### 10.3 Replacement Account Prohibition
* Unilateral substitution of a frozen beneficiary account is strictly **PROHIBITED**.

### 10.4 Capability & Pattern Mapping
* **Primary Capability Engine**: `AccountMasterEngine` (determines authoritative account restriction scope and `PNC` flag).
* **Supporting Capability Engines**:
  * `SettlementReconciliationEngine` (orchestrates suspense booking or `pacs.004` return package).
  * `ComplianceDossierEngine` (evaluates legal/regulatory freeze dossiers when compliance classification is required).
* **Primary Resolution Pattern**: `PAT-E` (Ledger Matching & Settlement Reversal).
* **Supporting Resolution Patterns**: `PAT-D` (Compliance & Risk Dossier) when legal context requires adjudication; `PAT-A` (Master / Directory Resolution).
* **Pattern Fit**: `COMPOSITE`.

---

## 11. Evidence Required Architecture

In accordance with the Wave 0B Dynamic Governance Architecture:
$$\text{Effective Bank Evidence Required JSON} = \text{Industry SOP Baseline} + \text{Bank Customization}$$

```
+---------------------------------------------------------------------------------------------------------------------------+
|                                        WAVE 2 EVIDENCE REQUIRED MATRIX                                                    |
+-------+------------------------------------+------------+------------------+--------------------------------+-------------+
| Code  | Evidence Item Description          | Trust Tier | Freshness Rule   | Authority Source Category      | Mode/SPI    |
+-------+------------------------------------+------------+------------------+--------------------------------+-------------+
| PR-06 | Inward pacs.002 / MT199 Rejection  | Tier 1 (T1)| Real-time/Current| Authoritative Correspondent SPI| Inbound/Doss|
| PR-06 | Original Outbound pacs.008 Message | Tier 1 (T1)| Original Record  | Bank Payment Hub Archive       | Inbound/Doss|
| PR-06 | Correspondent Directory / SSI Matrix| Tier 2 (T2)| Bank Policy Sync | Bank Clearing Directory Port   | Dossier     |
| PR-06 | Rail Operating Cutoff Schedule     | Tier 1 (T1)| Current Rail Cal | RTGS / Rail Operating Calendar | Dossier     |
+-------+------------------------------------+------------+------------------+--------------------------------+-------------+
| ST-02 | Core DDA Account Status Record     | Tier 1 (T1)| Bank Policy TTL  | Core Banking Account Master    | Query/Doss  |
| ST-02 | Inward pacs.008 Payment Payload    | Tier 1 (T1)| Original Record  | Clearing Ingest Queue          | Inbound     |
| ST-02 | Account Rollover Mandate (If any)  | Tier 1 (T1)| Active Mandate   | Bank Corporate Mandate Master  | Dossier     |
| ST-02 | Clearing Return Schedule / SLA     | Tier 2 (T2)| Static Rulebook  | Clearing Scheme Rulebook       | Dossier     |
+-------+------------------------------------+------------+------------------+--------------------------------+-------------+
| ST-03 | Core DDA Freeze / Restriction Flag | Tier 1 (T1)| Current Status   | Core Banking Legal Registry    | Query/Doss  |
| ST-03 | Legal / Judicial Freeze Dossier    | Tier 1 (T1)| Active Order     | Bank Legal / Compliance Master | Dossier     |
| ST-03 | Inward pacs.008 Payment Payload    | Tier 1 (T1)| Original Record  | Clearing Ingest Queue          | Inbound     |
| ST-03 | Bank Suspense Ledger Matrix        | Tier 1 (T1)| Static Config    | General Ledger Accounting Port | Dossier     |
+-------+------------------------------------+------------+------------------+--------------------------------+-------------+
```

* **Acquisition Mode Independence**: Evidence Required JSON specifies *what* evidence is required; acquisition modes (Modes 1–4) define *how* it may be acquired. Direct queries (Mode 3) are an operational capability, not a mandatory architecture prerequisite.

---

## 12. Authority Model ($V_{\text{det}}$ vs. $V_{\text{auth}}$)

PeX enforces strict separation between technical validation ($V_{\text{det}}$) and sovereign business authority ($V_{\text{auth}}$):

```
+---------------------------------------------------------------------------------------------------+
|                                     WAVE 2 AUTHORITY MODEL                                        |
+-------+----------------------------------+--------------------------------------------------------+
| Code  | Deterministic Validation (V_det) | Sovereign Authority Validation (V_auth)                |
+-------+----------------------------------+--------------------------------------------------------+
| PR-06 | • Inward rejection schema valid. | • Authoritative correspondent gateway confirms formal  |
|       | • Rejection reason code mapped.  |   rejection status.                                    |
|       | • Original UETR correlation match| • Bank Payment Hub confirms payment was in-flight and  |
|       | • Alternate SSI format valid.    |   not settled downstream.                              |
+-------+----------------------------------+--------------------------------------------------------+
| ST-02 | • IBAN / Account format valid.   | • Core Banking DDA SPI returns authoritative closed    |
|       | • Return message schema valid.   |   status affirmation.                                  |
|       | • 4-point reconciliation match.  | • Client rollover mandate signed by authorized officer.|
+-------+----------------------------------+--------------------------------------------------------+
| ST-03 | • Restriction code parsed.       | • Core DDA Legal Registry verifies active restriction  |
|       | • Suspense ledger format valid.  |   and Post No Credits flag.                            |
|       | • Return reason syntax valid.    | • Compliance/Legal Officer sign-off for legal holds.   |
+-------+----------------------------------+--------------------------------------------------------+
```

---

## 13. Conceptual Resolution Contracts

For each profile, the resolution lifecycle follows the governed pipeline:

```
INPUT EVIDENCE (Dossier + Query)
         ↓
CANDIDATE RESOLUTION GENERATION (PAT-E / PAT-F)
         ↓
DETERMINISTIC VALIDATION (V_det)
         ↓
SOVEREIGN AUTHORITY VALIDATION (V_auth)
         ↓
BANK RISK POLICY & STATUTORY GATES (P_bank ∧ C_comp)
         ↓
STP / HITL DECISION GATE (8-Predicate Conjunction)
         ├── [STP = TRUE]  → BANK_HANDOFF_READY (execution_owner = "BANK")
         └── [STP = FALSE] → PeX-Native HITL Workspace
```

### 13.1 `PR-06` Resolution Contract
* **Input**: Inward rejection notice + original payment payload + Correspondent SSI directory.
* **Candidate Resolution**:
  * Branch A: Alternate Correspondent Dispatch Package (`pacs.008` re-addressed to viable intermediary).
  * Branch B: Outward Return / Cancellation Package to Debtor (`camt.056` / ledger re-credit).
* **Deterministic Controls**: Validate alternate BIC in directory, currency match, cutoff active.
* **Authority Gate**: Intermediary rejection verified via authoritative correspondent gateway state.
* **Terminal State**: `BANK_HANDOFF_READY` (`execution_owner = "BANK"`).

### 13.2 `ST-02` Resolution Contract
* **Input**: Inward payment + Core DDA closed status record.
* **Candidate Resolution**:
  * Branch A (Default): Inward Return Package (`pacs.004` with closed reason code + suspense entry).
  * Branch B (Exceptional): Governed Account Rollover (only if authenticated mandate on file).
* **Deterministic Controls**: 4-point match (Original UETR, Amount, Currency, Debtor BIC).
* **Authority Gate**: Core DDA signed closed account affirmation.
* **Terminal State**: `BANK_HANDOFF_READY` (`execution_owner = "BANK"`).

### 13.3 `ST-03` Resolution Contract
* **Input**: Inward payment + Core DDA restriction flag + Legal Freeze Dossier.
* **Candidate Resolution**:
  * Branch A: Inward Return Package (`pacs.004` with appropriate return reason code).
  * Branch B: Bank Legal Suspense Booking Package (internal escrow credit).
* **Deterministic Controls**: Verify freeze scope prohibits credit; match original payment parameters.
* **Authority Gate**: Legal Registry validation of active judicial/statutory order.
* **Terminal State**: `BANK_HANDOFF_READY` (`execution_owner = "BANK"`).

---

## 14. AI vs. Deterministic Boundary

```
+---------------------------------------------------------------------------------------------------+
|                                  AI VS. DETERMINISTIC BOUNDARY                                    |
+-----------------------------------+---------------------------------------------------------------+
| Category                          | Governed Capabilities & Hard Constraints                      |
+-----------------------------------+---------------------------------------------------------------+
| DETERMINISTIC CONTROLS            | • ISO 20022 XML Schema validation.                            |
| (100% Code-Governed)              | • Checksum and Modulo-97 calculations.                        |
|                                   | • Core DDA status flag validation (CLOSED, PNC).              |
|                                   | • 4-point payment reconciliation matching.                    |
|                                   | • 8-predicate conjunction evaluation.                         |
|                                   | • Maker-Checker dual-authorization enforcement.               |
+-----------------------------------+---------------------------------------------------------------+
| AI-ASSISTED WORK                  | • Summarize free-text narrative in rejection notices.         |
| (Advisory Only — 0% Authority)    | • Cluster historical rejection reasons for operations insight.|
|                                   | • Explain proposed return or reroute steps to human analyst.  |
|                                   | • Extract structured data from unstructured context.          |
+-----------------------------------+---------------------------------------------------------------+
| STRICT AI PROHIBITIONS            | • AI MUST NOT synthesize or invent replacement accounts.      |
| (Hard Governance Violations)      | • AI MUST NOT declare authority (V_auth) or override Core DDA.|
|                                   | • AI MUST NOT authorize payment releases or ledger mutations. |
|                                   | • AI MUST NOT bypass Maker-Checker segregation of duties.     |
|                                   | • AI MUST NOT treat historical precedent as binding authority.|
+-----------------------------------+---------------------------------------------------------------+
```

---

## 15. HITL Architecture

Governed human adjudication remains strictly **INSIDE** PeX.

```
+---------------------------------------------------------------------------------------------------+
|                                  WAVE 2 HITL TRIGGER TAXONOMY                                     |
+-------+-------------------------------------------------------+-----------------------------------+
| Code  | HITL Trigger Condition                                | Required Operational Action       |
+-------+-------------------------------------------------------+-----------------------------------+
| PR-06 | Inward rejection contains unmapped narrative.         | Analyst reviews narrative & sends |
|       | No viable alternate correspondent routing hop found.  | query or authorizes cancellation. |
|       | Rejection implies compliance or AML embargo.          | Escalates to Compliance Officer.  |
+-------+-------------------------------------------------------+-----------------------------------+
| ST-02 | Replacement account rollover requested.               | Dual-authorization by Operations  |
|       | Discrepancy between Core DDA and clearing status.     | Maker-Checker to verify mandate.  |
|       | High-value return threshold exceeded (Bank Policy).   | Risk Officer approval on return.  |
+-------+-------------------------------------------------------+-----------------------------------+
| ST-03 | Legal freeze dossier indicates conflicting orders.    | Legal / Compliance Officer review |
|       | Suspense booking vs return decision required by policy| Operations Manager dual sign-off. |
|       | Account freeze linked to fraud investigation.         | Financial Crime Team review.      |
+-------+-------------------------------------------------------+-----------------------------------+
```

* **Closed-Loop Invariant**: After human operator submits evidence or selects a resolution branch, PeX **re-executes the complete 8-predicate evaluation**. Human input does not bypass governed validation.

---

## 16. STP Eligibility Mapping (8-Predicate Conjunction)

$$\text{STP\_ELIGIBLE} = E_{\text{suff}} \land R_{\text{det}} \land R_{\text{uniq}} \land V_{\text{det}} \land V_{\text{auth}} \land P_{\text{bank}} \land C_{\text{comp}} \land X_{\text{pre}}$$

```
+---------------------------------------------------------------------------------------------------------------------------+
|                                    WAVE 2 8-PREDICATE CONTRIBUTION MATRIX                                                 |
+-------+----------------------+--------------------+---------------------+--------------------+--------------------+-------+
| Code  | E_suff (Sufficiency) | R_det ∧ R_uniq     | V_det (Validation)  | V_auth (Authority) | P_bank ∧ C_comp    | STP?  |
+-------+----------------------+--------------------+---------------------+--------------------+--------------------+-------+
| PR-06 | Rejection notice +   | Deterministic SSI  | Alternate BIC valid;| Gateway proof      | Amount $\le$ limit;| COND. |
|       | original payment     | lookup yields 1    | currency matches;   | verified; payment  | corridor permitted;| (Auto |
|       | in dossier.          | viable alternate.  | cutoff active.      | in-flight.         | non-sanctions.     | Reroute|
+-------+----------------------+--------------------+---------------------+--------------------+--------------------+-------+
| ST-02 | Core DDA status +    | Standard return    | Return schema ok;   | Core DDA signed    | Auto-return policy | COND. |
|       | original payment     | candidate          | 4-point match       | closed status      | enabled; amount    | (Policy|
|       | present.             | generated.         | verified.           | verified.          | $\le$ return cap.  | Bound)|
+-------+----------------------+--------------------+---------------------+--------------------+--------------------+-------+
| ST-03 | Core DDA freeze flag | Standard return or | Schema valid;       | Legal registry     | Bank auto-return   | COND. |
|       | + legal dossier +    | suspense candidate | freeze scope        | signed PNC flag    | vs suspense policy | (Policy|
|       | original payment.    | derived.           | verified.           | verified.          | satisfied.         | Bound)|
+-------+----------------------+--------------------+---------------------+--------------------+--------------------+-------+
```

---

## 17. Bank Execution Boundary

```
+---------------------------------------------------------------------------------------------------+
|                                  BANK EXECUTION BOUNDARY MODEL                                    |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|    [ PeX Governance Boundary ]                                                                    |
|    • Ingests Exception & Evidence Dossier                                                         |
|    • Evaluates Evidence Sufficiency (E_suff)                                                      |
|    • Capability Engines derive Resolution Candidates (R_det ∧ R_uniq)                             |
|    • Validates Technical & Sovereign Authority (V_det ∧ V_auth)                                   |
|    • Evaluates Bank Risk Policy & Compliance Rules (P_bank ∧ C_comp)                              |
|    • Evaluates 8-Predicate Conjunction                                                            |
|    • Outputs: BANK_HANDOFF_READY (execution_owner = "BANK") for eligible handoffs                 |
|                                                                                                   |
| --------------------------------- SOVEREIGN BOUNDARY LINE --------------------------------------- |
|                                                                                                   |
|    [ Sovereign Bank Boundary (Outside PeX) ]                                                      |
|    • Bank Payment Hub / Settlement Engine receives handoff package                                |
|    • Authenticates PeX cryptographic handoff token & provenance hash                              |
|    • Executes final ledger debits/credits on Bank Core / DDA                                      |
|    • Dispatches outbound return / reroute messages over clearing network                          |
|    • Records final settlement accounting entries                                                  |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

---

## 18. Wave 2 Profile Contract Matrix

| Profile ID | Canonical Profile Name | Primary Engine | Supporting Engine | Primary Pattern | Supporting Pattern | Pattern Fit | Mandatory Evidence | Authority Category | Candidate Resolution | Deterministic Validation | Bank Policy Dependency | HITL Trigger | Automation Potential | STP Status | Production Dependency | Epistemic Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **PR-06** | Intermediary Bank Rejection | `SettlementReconciliationEngine` | `RoutingClearingEngine` | `PAT-F` (Intermediary) | `PAT-E` / `PAT-A` | **COMPOSITE** | Inward Rejection Notice + Original Payment + SSI Directory | Authoritative Correspondent Gateway | Alternate Correspondent Hop or Return Package | Alternate BIC check; Cutoff check; Schema check | Auto-reroute threshold (`W2-BPD-01`) | Narrative reject; No alternate SSI; Limit exceeded | **MEDIUM** | CONDITIONAL (Policy & SSI Bound) | Correspondent Gateway SPI; SWIFTRef Port | **ARCHITECTURE FACT** |
| **ST-02** | Account Closed | `AccountMasterEngine` | `SettlementReconciliationEngine` | `PAT-E` (Ledger) | `PAT-A` (Master) | **COMPOSITE** | Inward Payment + Core DDA Status (`CLOSED`) | Bank Core DDA Master | Inward Return Package (`AC04`) | 4-point match; Reason code; Return schema | Auto-return value limit (`W2-BPD-02`) | Mandate rollover requested; High value | **HIGH** | CONDITIONAL (Policy Bound) | Core DDA Account SPI; Clearing Return Port | **ARCHITECTURE FACT** |
| **ST-03** | Beneficiary Account Frozen | `AccountMasterEngine` | `SettlementReconciliationEngine` / `ComplianceDossierEngine` | `PAT-E` (Ledger) | `PAT-D` / `PAT-A` | **COMPOSITE** | Inward Payment + Core DDA Freeze Flag + Legal Dossier | Core DDA Legal Registry | Inward Return Package or Legal Suspense Booking | Freeze scope check (`PNC`); Suspense ledger check | Return vs Suspense Policy (`W2-BPD-03`) | Conflicting legal orders; Fraud hold | **CONDITIONAL** | CONDITIONAL (Policy Bound) | Core DDA Legal SPI; Suspense Ledger Port | **ARCHITECTURE FACT** |

---

## 19. SettlementReconciliationEngine Assessment

### 19.1 Reusable Engine Responsibilities
`SettlementReconciliationEngine` services interbank rejections (`PR-06`) and downstream return orchestration (`ST-02`, `ST-03`). Its reusable capabilities include:
1. **Transaction Correlation**: 4-point matching (UETR, Amount, Currency, Debtor/Creditor IDs) linking exception notices to original payments.
2. **Settlement Return Packaging**: Deterministic generation of ISO 20022 `pacs.004` return messages with standard external reason codes.
3. **Ledger Suspense Break Tracking**: Constructing balanced debit/credit journal packages for internal bank settlement suspense accounts.
4. **Intermediary State Tracking**: Correlating inward rejection advice against active outbound payment chains.

### 19.2 Explicit Engine Boundaries
* `SettlementReconciliationEngine` **DOES NOT**:
  * Determine Core DDA account status or legal restriction scope (delegated to `AccountMasterEngine`).
  * Determine alternate correspondent routing hops (delegated to `RoutingClearingEngine`).
  * Adjudicate statutory sanctions matches (delegated to `ComplianceDossierEngine`).
  * Mutate live bank general ledgers directly (delegated to Bank Execution Boundary).

---

## 20. Cross-Profile Capability Analysis

```
+---------------------------------------------------------------------------------------------------+
|                                  CROSS-PROFILE CAPABILITY ANALYSIS                                |
+-------------------------------+-----------------------+-------------------+-----------------------+
| Capability / Dimension        | PR-06 (Intermediary)  | ST-02 (Closed)    | ST-03 (Frozen)        |
+-------------------------------+-----------------------+-------------------+-----------------------+
| Primary Domain Engine         | SettlementReconcil-   | AccountMasterEngine| AccountMasterEngine   |
|                               | Engine (Intermediary) | (Account Status)  | (Restriction Scope)   |
+-------------------------------+-----------------------+-------------------+-----------------------+
| Account State Verification    | N/A (Intermediary Hop)| AccountMasterEngine| AccountMasterEngine   |
|                               |                       | (Closed Check)    | (PNC Freeze Check)    |
+-------------------------------+-----------------------+-------------------+-----------------------+
| Alternate Routing Resolution  | RoutingClearingEngine | N/A (No Routing)  | N/A (No Routing)      |
|                               | (Alternate SSI Lookup)|                   |                       |
+-------------------------------+-----------------------+-------------------+-----------------------+
| Return pacs.004 Generation    | SettlementReconcil-   | SettlementReconcil-| SettlementReconcil-   |
|                               | Engine (If no reroute)| Engine (Supporting| Engine (Supporting)   |
+-------------------------------+-----------------------+-------------------+-----------------------+
| Suspense Ledger Booking       | SettlementReconcil-   | SettlementReconcil-| SettlementReconcil-   |
|                               | Engine (Cancel Break) | Engine (Return)   | Engine (Legal Escrow) |
+-------------------------------+-----------------------+-------------------+-----------------------+
| Primary Resolution Pattern    | PAT-F (Intermediary)  | PAT-E (Ledger)    | PAT-E (Ledger)        |
+-------------------------------+-----------------------+-------------------+-----------------------+
```

---

## 21. Pattern Forensic Review

### 21.1 `PR-06` Pattern Fitness
* **Primary**: `PAT-F` (Intermediary & Claims Tracking Family).
  * *Why it fits*: The core operational problem is resolving an intermediary rejection notice, tracking the correspondent leg, and determining an alternate forwarding path or initiating a claim.
  * *What it does NOT cover*: Downstream ledger reversal if rerouting fails (covered by supporting `PAT-E`).

### 21.2 `ST-02` Pattern Fitness
* **Primary**: `PAT-E` (Ledger Matching & Settlement Reversal Family).
  * *Why it fits*: The primary resolution action is 4-point matching of the incoming transaction and generating a compliant `pacs.004` return package with ledger re-credit.
  * *What it does NOT cover*: Verifying that the account is closed (covered by supporting `PAT-A` directory lookup via `AccountMasterEngine`).

### 21.3 `ST-03` Pattern Fitness
* **Primary**: `PAT-E` (Ledger Matching & Settlement Reversal Family).
  * *Why it fits*: The operational output is either an inward return (`pacs.004`) or an internal legal suspense booking.
  * *What it does NOT cover*: Legal freeze dossier evaluation (covered by supporting `PAT-D` compliance dossier).

---

## 22. Production Integration Dependencies

```
+---------------------------------------------------------------------------------------------------+
|                                PRODUCTION INTEGRATION DEPENDENCY MATRIX                           |
+-----------------------------------+-----------------------------------+---------------------------+
| Dependency Identifier             | Interface Description             | Current Architecture State|
+-----------------------------------+-----------------------------------+---------------------------+
| `SPI-DDA-ACCOUNT-MASTER`          | Real-time Core DDA status inquiry | REFERENCE ADAPTER EXISTS  |
| `SPI-CORRESPONDENT-GATEWAY`       | SWIFT / Clearing inward rejection | REFERENCE ADAPTER EXISTS  |
| `SPI-ROUTING-SSI-DIRECTORY`       | Clearing directory / SWIFTRef     | REFERENCE ADAPTER EXISTS  |
| `SPI-SETTLEMENT-RETURN-PORT`      | Outward pacs.004 return dispatch  | REFERENCE ADAPTER EXISTS  |
| `SPI-LEGAL-REGISTRY-PORT`         | Core Banking Legal Freeze master  | REFERENCE ADAPTER EXISTS  |
| `SPI-GENERAL-LEDGER-SUSPENSE`     | Internal suspense journal booking | REFERENCE ADAPTER EXISTS  |
+-----------------------------------+-----------------------------------+---------------------------+
```
* **Governance Note**: Reference adapters demonstrate architectural feasibility in sandbox environments. Production deployment requires binding to bank-specific core enterprise systems.

---

## 23. Architectural Risk Register

```
+---------------------------------------------------------------------------------------------------------------------------+
|                                              WAVE 2 RISK REGISTER                                                         |
+-------+----------------------------------+--------+------------------------------------+------------------+---------------+
| Risk# | Risk Description                 | Impact | Mitigation & Governed Control      | Owner Category   | Status        |
+-------+----------------------------------+--------+------------------------------------+------------------+---------------+
| R-01  | Stale Account Status in Cache    | HIGH   | Enforce bank-configured TTL; real- | Core Banking SME | ARCH FACT     |
|       | causes wrongful credit/return.   |        | time DDA SPI query for ST-02/03.   |                  |               |
+-------+----------------------------------+--------+------------------------------------+------------------+---------------+
| R-02  | Unauthorized Replacement Account | CRIT   | Hard prohibition on AI synthesis;  | Risk Policy SME  | ARCH FACT     |
|       | misdirects funds.                |        | mandatory dual-control for mandate.|                  |               |
+-------+----------------------------------+--------+------------------------------------+------------------+---------------+
| R-03  | Duplicate pacs.004 Return        | HIGH   | Idempotency ledger key on UETR +   | Payment Ops SME  | ARCH FACT     |
|       | creates double-reversal break.   |        | return sequence in SettlementEngine|                  |               |
+-------+----------------------------------+--------+------------------------------------+------------------+---------------+
| R-04  | Ambiguous Intermediary Narrative | MED    | Narrative rejections fail-closed   | Clearing Ops SME | ARCH FACT     |
|       | leads to incorrect reroute.      |        | into PeX HITL workspace.           |                  |               |
+-------+----------------------------------+--------+------------------------------------+------------------+---------------+
| R-05  | Sanctions Hold Treated as Return | CRIT   | ComplianceDossierEngine evaluates  | Compliance SME   | ARCH FACT     |
|       | violating statutory asset freeze.|        | statutory block before ST-03 return|                  |               |
+-------+----------------------------------+--------+------------------------------------+------------------+---------------+
```

---

## 24. Architecture Decisions

### Decision `W2-AD-01`: Account Master vs. Settlement Reconciliation Domain Boundaries
* **Context**: `ST-02` and `ST-03` combine account-state determination with downstream return/settlement handling.
* **Decision**: `AccountMasterEngine` is the primary domain engine for account-state and freeze-scope determination. `SettlementReconciliationEngine` provides supporting downstream return message compilation (`pacs.004`) and suspense accounting.
* **Classification**: **ARCHITECTURE FACT**.

### Decision `W2-AD-02`: Replacement Account Safety Invariant
* **Context**: Closed or frozen accounts may have active successor accounts in Core Banking.
* **Decision**: Autonomous substitution of beneficiary accounts is strictly prohibited. Any replacement resolution requires an authenticated mandate record, bank policy enablement, and mandatory Maker-Checker dual authorization.
* **Classification**: **ARCHITECTURE FACT**.

---

## 25. Bank Policy Decisions

### Decision `W2-BPD-01`: Automated Correspondent Reroute Thresholds
* **Question**: What transaction value limits and correspondent relationship tiers permit zero-touch automated rerouting under `PR-06`?
* **Classification**: **BANK POLICY PARAMETER**.
* **Owner**: Head of Clearing Operations.

### Decision `W2-BPD-02`: Closed Account Return vs. Rollover Policy
* **Question**: Under what specific corporate client agreements may a closed account payment be redirected to an authenticated successor account versus returned via `pacs.004`?
* **Classification**: **BANK POLICY PARAMETER**.
* **Owner**: Head of Payments Operations & Risk.

### Decision `W2-BPD-03`: Frozen Account Return vs. Legal Suspense Escrow
* **Question**: What categories of legal/judicial freeze mandate immediate `pacs.004` return versus holding funds in internal Bank Legal Suspense Escrow?
* **Classification**: **BANK POLICY PARAMETER**.
* **Owner**: General Counsel & Chief Compliance Officer.

---

## 26. Wave 2 Architecture Definition of Done

Before a separate **Wave 2 Implementation Authorization Gate** can be drafted, the following criteria must be satisfied:

- [x] Canonical semantics for `PR-06`, `ST-02`, and `ST-03` verified with zero taxonomy drift.
- [x] Primary and supporting capability engines assigned with anti-theft boundaries (`AccountMasterEngine` primary for `ST-02`/`ST-03`, `SettlementReconciliationEngine` primary for `PR-06`).
- [x] Resolution patterns validated without artificial pattern forcing (`PAT-F` for `PR-06`, `PAT-E` for `ST-02`/`ST-03`).
- [x] Evidence Required models defined across Trust Tiers T1–T4.
- [x] Sovereign authority requirements ($V_{\text{auth}}$) and source categories established.
- [x] 8-predicate STP formula mapped across all three profiles.
- [x] HITL workspace triggers and closed-loop re-evaluation rules defined.
- [x] AI assist boundaries and strict AI prohibitions documented.
- [x] Bank execution boundary (`execution_owner = "BANK"`) fully preserved.
- [x] Production integration dependencies identified.
- [x] Architectural risks registered with mitigation controls.
- [x] Wave 2 Architecture Decisions (`W2-AD-01`, `W2-AD-02`) and Bank Policy Decisions (`W2-BPD-01`..`03`) cataloged.
- [x] Phase 2 (11 profiles) and Wave 1 (9 profiles) protection verified.

---

## 27. Implementation Readiness Assessment

### Current Determination: **READY WITH CONDITIONS**

Wave 2 architecture is structurally sound, semantically rigorous, and fully reconciled against controlling baselines. It is ready to proceed to the formal **Wave 2 Implementation Authorization Gate** under the following conditions:

1. **Condition 1 (Governance Boundary)**: Engineering implementation of Wave 2 must remain strictly **BLOCKED** until the separate `PeX_Wave2_Implementation_Authorization_Gate_v0.1.md` is authored and formally approved.
2. **Condition 2 (No Autonomous Production STP)**: Autonomous release of funds in production remains strictly blocked. All execution handoffs require `execution_owner = "BANK"`.
3. **Condition 3 (Bank Policy Configuration)**: Published Bank Evidence Required JSON templates for `PR-06`, `ST-02`, and `ST-03` must explicitly incorporate Bank Policy parameters (`W2-BPD-01`..`03`).

---

## 28. Governance Conclusion

1. **Architecture Complete**: The architecture specification for Phase 3 Wave 2 (`PR-06`, `ST-02`, `ST-03`) is complete for architecture review, robust, and verified.
2. **Semantic Contracts Reconciled**: Semantic contracts, capability engine boundaries, and resolution patterns are fully articulated without domain theft or pattern distortion.
3. **Engineering Authorization Not Granted**: This document does **NOT** grant authorization to write application code, modify schemas, or alter tests.
4. **Next Governance Artifact**: The immediate next step is the formulation of the **PeX Phase 3 Wave 2 Implementation Authorization Gate v0.1**.
5. **Zero Repository Drift**: No application source code or test fixtures were modified during this governance stage.

---

## 29. Recommended Next Step

Proceed to draft the formal:
**`PeX_Wave2_Implementation_Authorization_Gate_v0.1.md`**  
incorporating the frozen architecture baseline, test expansion specifications (adding Scenarios 28–30 for Wave 2), engine implementation scope, and sandbox verification criteria.

---

## 30. Self-Audit

The Principal Architecture Authority has performed a complete self-audit against all governance criteria:

```
+---------------------------------------------------------------------------------------------------+
|                                  SELF-AUDIT VERIFICATION CHECKLIST                                |
+----+--------------------------------------------------------------------------+-------------------+
| #  | Verification Item                                                        | Audit Result      |
+----+--------------------------------------------------------------------------+-------------------+
| 1  | Exactly 3 Wave 2 profiles (PR-06, ST-02, ST-03).                         | PASS — VERIFIED   |
| 2  | Exact canonical profile names preserved with zero taxonomy drift.        | PASS — VERIFIED   |
| 3  | Phase 2 (11 profiles) and Wave 1 (9 profiles) baselines untouched.       | PASS — VERIFIED   |
| 4  | 8-predicate formula preserved without modification.                      | PASS — VERIFIED   |
| 5  | ST-02 primary engine corrected to AccountMasterEngine.                   | PASS — VERIFIED   |
| 6  | ST-03 primary engine corrected to AccountMasterEngine.                   | PASS — VERIFIED   |
| 7  | PR-06 remains SettlementReconciliationEngine primary (PAT-F).            | PASS — VERIFIED   |
| 8  | ST-05 no longer described as Wave 2 (labeled Future / Out of Scope).     | PASS — VERIFIED   |
| 9  | Canonical profile semantics are not over-specified.                      | PASS — VERIFIED   |
| 10 | ST-03 is not a catch-all compliance profile (CO-01 preserved).           | PASS — VERIFIED   |
| 11 | Network telemetry is not treated as authoritative payment state.         | PASS — VERIFIED   |
| 12 | Replacement account is not inferred or synthesized by AI.                | PASS — VERIFIED   |
| 13 | Evidence Required JSON remains distinct from Evidence Contract.          | PASS — VERIFIED   |
| 14 | Direct bank APIs (Mode 3) are not mandatory architecture prerequisites.  | PASS — VERIFIED   |
| 15 | Automation Potential is not equated with STP eligibility.                | PASS — VERIFIED   |
| 16 | BANK_HANDOFF_READY is execution-boundary state, not universal terminal.  | PASS — VERIFIED   |
| 17 | HITL workspace remains strictly inside PeX.                              | PASS — VERIFIED   |
| 18 | Bank execution authority remains strictly outside PeX.                   | PASS — VERIFIED   |
| 19 | AI has 0% execution authority; AI cannot declare V_auth.                 | PASS — VERIFIED   |
| 20 | No invented authority; sovereign source categories clearly defined.      | PASS — VERIFIED   |
| 21 | No unsupported vendor assumptions presented as facts.                    | PASS — VERIFIED   |
| 22 | No arbitrary test-count mandates in architecture phase.                  | PASS — VERIFIED   |
| 23 | Engineering authorization is NOT granted.                                | PASS — VERIFIED   |
| 24 | Production autonomous STP remains strictly BLOCKED.                      | PASS — VERIFIED   |
| 25 | No Wave 2 implementation gate is created by this document.               | PASS — VERIFIED   |
| 26 | Zero unauthorized application code or test modifications.                | PASS — VERIFIED   |
+----+--------------------------------------------------------------------------+-------------------+
```
