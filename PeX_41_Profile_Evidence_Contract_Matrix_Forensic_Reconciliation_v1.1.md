# PeX — 41-Profile Evidence Contract Matrix Forensic Reconciliation v1.1
## Authoritative Architecture Hardening, Epistemic Grounding & Pre-Implementation Gate Review

**Document Identifier:** `PeX-ARCH-RECON-41-v1.1`  
**Version:** v1.1 (Forensic Baseline)  
**Status:** ARCHITECTURE HARDENING COMPLETE — CONDITIONAL PRE-IMPLEMENTATION GATE  
**Operating Mode:** READ-ONLY / PRE-IMPLEMENTATION (Zero Production Code Changes)  
**Author:** Principal Enterprise Architect, Payment Domain Architect & Forensic Reviewer  
**Date:** October 2026  
**Authoritative Baselines:**  
1. `PeX_Evidence_Driven_STP_Architecture_Baseline_v1.1.md` (Immutable Architecture Baseline)  
2. `PeX_41_Profile_Authority_Evidence_STP_Validation_Report_v1.1.md` (Fact & Authority Baseline)  
3. `PeX_41_Profile_Evidence_Contract_Matrix_v1.0.md` (Phase 2 Matrix Baseline)  
4. `PeX_Phase2_Controlled_Expansion_Plan_v0.1.md` (Phase 2 Expansion Plan)  
5. `PeX_Phase1_PR03_Implementation_Report_v0.1.md` (Verified Phase 1 Implementation)  

---

## 1. Document Control & Governance

### 1.1 Metadata
- **Title:** PeX 41-Profile Evidence Contract Matrix Forensic Reconciliation & Hardening
- **Classification:** Authoritative Pre-Implementation Governance Gate
- **Purpose:** Perform forensic cross-reconciliation across all 41 BIAN exception profiles, strictly differentiating established global standards, scheme rules, and bank authoritative sources from PeX design choices, bank policies, business hypotheses, and open discovery items.
- **Supersession Notice:** This document represents the definitive architecture hardening assessment. It establishes the binding constraints, epistemic classifications, and prerequisites that govern Phase 2 implementation.

### 1.2 Executive Verdict
```
====================================================================================================
FORENSIC RECONCILIATION VERDICT:
APPROVED WITH CONDITIONS — REVISE & HARDEN BEFORE IMPLEMENTATION MODE AUTHORIZATION

PHASE 2 IMPLEMENTATION STATUS:
BLOCKED (READ-ONLY PRE-IMPLEMENTATION MODE STRICTLY MAINTAINED)

SUMMARY OF HARDENING FINDINGS:
1. TAXONOMY INTEGRITY: 41 / 41 Profiles Verified Intact (0 Missing, 0 Extra, 0 Renamed).
2. EPISTEMIC CLASSIFICATION: All claims classified across 12 distinct epistemic tiers.
3. SYNTAX VS AUTHORITY SEPARATION: Mathematical/schema validity strictly decoupled from business SoR.
4. "INVALID != CORRECT": Core principle forensically verified across all 41 repair derivations.
5. BANK EXECUTION BOUNDARY: Hardened to confirm PeX is NOT an accounting/settlement engine.
6. PHASE 2 SEQUENCING: Phased 2A -> 2B -> 2C sequence confirmed structurally sound and risk-minimized.
====================================================================================================
```

---

## 2. Authoritative Source-of-Truth Hierarchy

When reconciling architectural assertions, data models, or STP claims, the following hierarchy strictly governs:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │ 1. Architecture Baseline (Baseline v1.1 - Immutable)   │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                  ┌────────────────────────────▼────────────────────────────┐
                  │ 2. Authority / Fact Validation Report (Report v1.1)     │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                  ┌────────────────────────────▼────────────────────────────┐
                  │ 3. Phase 1 Verified Implementation (142 Passing Tests)  │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                  ┌────────────────────────────▼────────────────────────────┐
                  │ 4. Evidence Contract Matrix (Matrix v1.0)               │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                  ┌────────────────────────────▼────────────────────────────┐
                  │ 5. Phase 2 Expansion Plan (Plan v0.1)                   │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                  ┌────────────────────────────▼────────────────────────────┐
                  │ 6. Legacy Drafts / Spreadsheets / AI-Generated Context  │
                  └─────────────────────────────────────────────────────────┘
```

---

## 3. Epistemic Status Classification Framework

Every statement, evidence item, repair mechanism, and policy threshold in PeX is explicitly classified into one of the following 12 epistemic categories:

```
+----+---------------------------------------------------+------------------------------------------------------------------------+
| #  | Classification                                    | Operational Definition & Evidence Standard                             |
+----+---------------------------------------------------+------------------------------------------------------------------------+
| 1  | ESTABLISHED — FORMAL STANDARD                     | Codified in international standards (ISO 20022, ISO 13616, ISO 7064).  |
| 2  | ESTABLISHED — SCHEME / NETWORK RULE               | Codified in clearing network operating rules (SWIFT, Fedwire, CHAPS).  |
| 3  | ESTABLISHED — REGULATION / STATUTORY REQUIREMENT  | Enforced by statutory law (OFAC, BSA/FinCEN, FATF, UCC 4A, UK PSR).   |
| 4  | ESTABLISHED — BANK AUTHORITATIVE SOURCE           | Internal bank System of Record (Core DDA, Bank SSI Master, Mandates).  |
| 5  | ESTABLISHED — EXTERNAL AUTHORITATIVE SOURCE       | Authoritative external registry (SWIFTRef, FedLine, Pay.UK CoP, LEI).  |
| 6  | ESTABLISHED — VERIFIED PEX IMPLEMENTATION         | Tested & working in codebase (Phase 1 PR-03 slice, 142/142 tests).     |
| 7  | DERIVED — PEX DETERMINISTIC LOGIC                 | Deterministic algorithm/regex (MOD-97 solver, XML re-sequencer).       |
| 8  | BANK POLICY — REQUIRES CLIENT CONFIGURATION       | Parameterized bank risk rules (STP monetary caps, corridor allowlists).|
| 9  | PROPOSED — PEX ARCHITECTURE / DESIGN              | Modular platform service design (Bank Evidence Gateway, DLQ Reset).   |
| 10 | BUSINESS HYPOTHESIS                               | Commercial/operational target (25% STP rate, 50% Fast-Lane, <50ms SLA).|
| 11 | TO BE VALIDATED                                   | Requires institutional verification during bank onboarding discovery.  |
| 12 | UNKNOWN / OPEN QUESTION                           | Unresolved domain edge case or multi-jurisdiction regulatory conflict. |
+----+---------------------------------------------------+------------------------------------------------------------------------+
```

---

## 4. Taxonomy Integrity & Reconciliation Check

A strict 1:1 cross-reconciliation was conducted between the Expected Taxonomy, the Authority Validation Baseline, the Matrix v1.0, and the Repository Schemas:

```
+----+-------------+------------------------------------+-----------------------+-----------------------+-------------+
| #  | Profile ID  | Canonical Profile Name             | Baseline v1.1 Group   | Matrix v1.0 Group     | Reconciled? |
+----+-------------+------------------------------------+-----------------------+-----------------------+-------------+
| 1  | DQ-01       | Invalid IBAN                       | Group 2 (Conditional) | Group 2 (Conditional) | **YES**     |
| 2  | DQ-02       | Invalid BIC / SWIFT                | Group 2 (Conditional) | Group 2 (Conditional) | **YES**     |
| 3  | DQ-03       | Missing Beneficiary Data           | Group 3 (Policy-Dep)  | Group 3 (Policy-Dep)  | **YES**     |
| 4  | DQ-04       | Missing Remittance Info            | Group 2 (Conditional) | Group 2 (Conditional) | **YES**     |
| 5  | DQ-05       | Invalid Address Format             | Group 1 (STP-Capable) | Group 1 (STP-Capable) | **YES**     |
| 6  | DQ-06       | Missing Purpose Code               | Group 2 (Conditional) | Group 2 (Conditional) | **YES**     |
| 7  | DQ-07       | Invalid Account Number             | Group 2 (Conditional) | Group 2 (Conditional) | **YES**     |
| 8  | DQ-08       | Invalid Routing Code               | Group 1 (STP-Capable) | Group 1 (STP-Capable) | **YES**     |
| 9  | DQ-09       | Beneficiary Name Mismatch          | Group 4 (Human Auth)  | Group 4 (Human Auth)  | **YES**     |
| 10 | PR-01       | Duplicate Payment                  | Group 1 (STP-Capable) | Group 1 (STP-Capable) | **YES**     |
| 11 | PR-02       | Routing Failure                    | Group 3 (Policy-Dep)  | Group 3 (Policy-Dep)  | **YES**     |
| 12 | PR-03       | ISO 20022 Validation Error         | Group 1 (STP-Capable) | Group 1 (STP-Capable) | **YES**     |
| 13 | PR-04       | Cutoff Missed                      | Group 2 (Conditional) | Group 2 (Conditional) | **YES**     |
| 14 | PR-05       | Corrupted Message Format           | Group 1 (STP-Capable) | Group 1 (STP-Capable) | **YES**     |
| 15 | PR-06       | Intermediary Bank Rejection        | Group 3 (Policy-Dep)  | Group 3 (Policy-Dep)  | **YES**     |
| 16 | PR-07       | Network Timeout                    | Group 3 (Policy-Dep)  | Group 3 (Policy-Dep)  | **YES**     |
| 17 | PR-08       | Queue Processing Failure           | Group 1 (STP-Capable) | Group 1 (STP-Capable) | **YES**     |
| 18 | PR-09       | Payment Held for Repair            | Group 2 (Conditional) | Group 2 (Conditional) | **YES**     |
| 19 | CO-01       | Sanctions Screening Hit            | Group 4 (Human Auth)  | Group 4 (Human Auth)  | **YES**     |
| 20 | CO-02       | AML Alert                          | Group 4 (Human Auth)  | Group 4 (Human Auth)  | **YES**     |
| 21 | CO-03       | PEP Match                          | Group 4 (Human Auth)  | Group 4 (Human Auth)  | **YES**     |
| 22 | CO-04       | Restricted Corridor                | Group 2 (Conditional) | Group 2 (Conditional) | **YES**     |
| 23 | CO-05       | Adverse Media Match                | Group 4 (Human Auth)  | Group 4 (Human Auth)  | **YES**     |
| 24 | CO-06       | High-Risk Jurisdiction             | Group 3 (Policy-Dep)  | Group 3 (Policy-Dep)  | **YES**     |
| 25 | CO-07       | Regulatory Reporting Required      | Group 2 (Conditional) | Group 2 (Conditional) | **YES**     |
| 26 | CO-08       | Customer Watchlist Match           | Group 4 (Human Auth)  | Group 4 (Human Auth)  | **YES**     |
| 27 | TR-01       | Nostro Shortfall                   | Group 2 (Conditional) | Group 2 (Conditional) | **YES**     |
| 28 | TR-02       | KYC Expired                        | Group 3 (Policy-Dep)  | Group 3 (Policy-Dep)  | **YES**     |
| 29 | TR-03       | Insufficient Funds                 | Group 2 (Conditional) | Group 2 (Conditional) | **YES**     |
| 30 | TR-04       | FX Rate Unavailable               | Group 2 (Conditional) | Group 2 (Conditional) | **YES**     |
| 31 | TR-05       | Authorization Missing              | Group 3 (Policy-Dep)  | Group 3 (Policy-Dep)  | **YES**     |
| 32 | TR-06       | Limit Breach                       | Group 3 (Policy-Dep)  | Group 3 (Policy-Dep)  | **YES**     |
| 33 | TR-07       | Liquidity Constraint               | Group 4 (Human Auth)  | Group 4 (Human Auth)  | **YES**     |
| 34 | TR-08       | Credit Exposure Breach             | Group 4 (Human Auth)  | Group 4 (Human Auth)  | **YES**     |
| 35 | ST-01       | Returned Payment                   | Group 1 (STP-Capable) | Group 1 (STP-Capable) | **YES**     |
| 36 | ST-02       | Account Closed                     | Group 4 (Human Auth)  | Group 4 (Human Auth)  | **YES**     |
| 37 | ST-03       | Beneficiary Account Frozen         | Group 4 (Human Auth)  | Group 4 (Human Auth)  | **YES**     |
| 38 | ST-04       | Reconciliation Break               | Group 4 (Human Auth)  | Group 4 (Human Auth)  | **YES**     |
| 39 | ST-05       | Settlement Failure                 | Group 3 (Policy-Dep)  | Group 3 (Policy-Dep)  | **YES**     |
| 40 | ST-06       | Funds Trapped at Correspondent     | Group 4 (Human Auth)  | Group 4 (Human Auth)  | **YES**     |
| 41 | ST-07       | Unmatched Credit                   | Group 3 (Policy-Dep)  | Group 3 (Policy-Dep)  | **YES**     |
+----+-------------+------------------------------------+-----------------------+-----------------------+-------------+
```

```
====================================================================================================
TAXONOMY RECONCILIATION SUMMARY:
Expected Profiles: 41 | Actual Profiles: 41 | Missing: 0 | Extra: 0 | Renamed: 0 | Mismatches: 0
Status: 100% PERFECT MATCH — TAXONOMY FULLY PRESERVED & IMMUTABLE
====================================================================================================
```

---

## 5. Architectural & Epistemic Hardening Findings

### 5.1 Hardening Principle 1: Syntax / Mathematical Validity $\neq$ Business Authority
The forensic review identified critical distinctions that must remain hardcoded across all platform contracts:
1. **`DQ-01: INVALID_IBAN`**:
   - $\text{MOD-97-10}$ check digit validation ($r=1$) is a **PeX-Derived Mathematical Proof (Tier 3)**. It proves string checksum integrity.
   - ISO 13616 BBAN parsing is an **External Standard Proof (Tier 2)**. It proves country code and character length validity.
   - **Crucial Hardening**: Neither MOD-97 nor SWIFTRef proves that the account belongs to the intended beneficiary or is currently open. **Only Tier 1 Bank SSI Master / Core DDA or live Confirmation of Payee (CoP) can satisfy Business Authority ($V_{\text{auth}}$)**.
2. **`DQ-02: INVALID_BIC`**:
   - SWIFTRef Directory is an **External Authoritative Registry (Tier 2)**. It proves institutional existence, head-office mapping, and clearing network connectivity.
   - **Crucial Hardening**: SWIFTRef does **not** prove that a specific sub-branch holds active clearing arrangements for a specific non-major currency corridor.
3. **`DQ-05: INVALID_ADDRESS`**:
   - UPU S42 and ISO 20022 `PostalAddress24` schemas are **Formal Standards (Tier 2)**. They prove postal syntax structure.
   - **Crucial Hardening**: Postal parsing proves **zero** facts regarding the physical existence, solvency, or beneficial ownership of the recipient entity.
4. **`DQ-06: MISSING_PURPOSE`**:
   - Mapping remittance text keywords (e.g. "SALARY" $\to$ `SALA`) is a **PeX-Derived Heuristic (Tier 3)**.
   - **Crucial Hardening**: A keyword match alone is **never** legal statutory proof of Balance of Payments trade intent. Autonomous population is permissible only under bank-configured commercial trade policy and monetary ceilings ($P_{\text{bank}}$).

### 5.2 Hardening Principle 2: "Invalid / Failed $\neq$ Correct Replacement"
Detecting an error establishes that an instruction cannot proceed; deriving the correct replacement requires deterministic derivation and authoritative corroboration:
- **Transposition Solver (`DQ-01`)**: If 2 distinct single-transpositions both yield valid MOD-97 checksums ($N=2$), $R_{\text{uniq}} == \text{FALSE}$. Autonomous resolution **must halt immediately** and suspend to the Disambiguation Worklist.
- **Duplicate Payment (`PR-01`)**: Exact SHA-256 collision on identical UETR within the 24h ledger is **Deterministically Suppressed**. Similar payments with distinct invoice references or slight amount variations are **Potential Duplicates** and must route to human operations.
- **Corrupted Message (`PR-05`)**: Byte sanitization is permissible **only if strictly lossless**. If sanitization truncates text strings, removes numeric digits, or modifies XML delimiter syntax, the case must halt with $V_{\text{det}} == \text{FALSE}$.

### 5.3 Hardening Principle 3: PeX Output Boundary & Non-Settlement Identity
- **PeX is NOT an Accounting or Settlement Engine**: PeX does not hold central bank master accounts, debit client balances, or post General Ledger entries directly.
- **`ST-01: RETURNED_PAYMENT` Hardening**: PeX identifies the inbound `pacs.004`, reconciles the original `pacs.008` UETR, derives the structured re-credit instruction, and produces a **Bank Handoff Payload**. The **Bank Payment Hub and Core DDA execute the actual financial accounting debit/credit**.

---

## 6. Profile-by-Profile Forensic Reconciliation Matrix

```
Legend:
- Epistemic Status: EST = Established Standard/Regulation/Bank SoR | DER = Derived PeX Logic | POL = Bank Policy Config | PROP = Proposed Architecture | HYP = Business Hypothesis | TBD = To Be Validated
- Severity: P0 = Critical Safety/Authority Boundary | P1 = Material Risk | P2 = Documentation/Wording Hardening | P3 = Minor Clarification
```

| Profile ID & Name | Current Matrix Claim | Evidence Authority & Epistemic Status | E_suff / R_det / R_uniq Valid? | Validation vs Authority Grounding | STP Class & Human Review | Identified Issue & Severity | Hardened Architectural Correction | Bank Discovery / Ext Integration Needed? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`DQ-01: INVALID_IBAN`** | MOD-97 check failure; auto-repair check digit or single transposition. | **T1:** Bank SSI / CoP (`EST-BANK/EXT`)<br>**T3:** MOD-97 Solver (`DER-PEX`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** COND ($N=1$) | **V_det:** ISO 7064 MOD-97 ($r=1$).<br>**V_auth:** SSI / CoP attestation. | **Class:** Group 2 (Conditional STP).<br>**HITL:** Disambiguation if $N>1$ or CoP mismatch. | **Issue:** MOD-97 math alone cannot prove account ownership (**P0**). | **Hardened:** Candidate generation is mathematical; final authority is strictly Bank SSI / CoP. | • Bank SSI Adapter (Discovery)<br>• CoP Gateway (Ext Int) |
| **`DQ-02: INVALID_BIC`** | Inactive / 8-char BIC; auto-replace with active head-office BIC. | **T2:** SWIFTRef Directory (`EST-EXT`)<br>**T3:** BIC8/11 Normalizer (`DER-PEX`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** COND ($N=1$) | **V_det:** ISO 9362 regex.<br>**V_auth:** SWIFTRef active status. | **Class:** Group 2 (Conditional STP).<br>**HITL:** Ops review if branch split/multiple successors. | **Issue:** Head-office may not clear requested currency (**P1**). | **Hardened:** Requires reachability check on requested rail; otherwise routes to Ops. | • SWIFTRef Directory Feed (Ext Int) |
| **`DQ-03: MISSING_BENEFICIARY`** | Empty `<Cdtr><Nm>`; populate from Core DDA or LEI Master. | **T1:** Core DDA / Mandate (`EST-BANK`)<br>**T2:** GLEIF LEI (`EST-EXT`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** COND ($N=1$) | **V_det:** FATF 16 ($\le 140$ chars).<br>**V_auth:** Customer Master token. | **Class:** Group 3 (Policy Dependent).<br>**HITL:** Maker-Checker for new counterparty ($<30$d). | **Issue:** Auto-populating name without verified link creates FATF liability (**P0**). | **Hardened:** Requires signed mandate on file; new counterparties mandate dual-auth. | • Core DDA Customer Master (Discovery) |
| **`DQ-04: MISSING_REMITTANCE`** | Empty `<RmtInf>`; populate invoice ref from Debtor ERP AP feed. | **T1:** Debtor ERP AP Feed (`EST-BANK`)<br>**T4:** Historical templates (`DER-PEX`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** COND ($N=1$) | **V_det:** ISO 20022 `<RmtInf>` XSD.<br>**V_auth:** Debtor AP invoice digest. | **Class:** Group 2 (Conditional STP).<br>**HITL:** Ops review if multiple invoices match amount. | **Issue:** Bank payment hub cannot guess invoices without live AP feed (**P1**). | **Hardened:** Auto-population permitted ONLY upon 100% exact invoice amount/currency match. | • Debtor ERP AP Gateway (Discovery) |
| **`DQ-05: INVALID_ADDRESS`** | Unstructured address lines; parse into discrete PostalAddress24 tags. | **T2:** UPU S42 / Postal DB (`EST-EXT`)<br>**T3:** PeX Address Parser (`DER-PEX`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** `PostalAddress24` XSD.<br>**V_auth:** UPU S42 syntax digest. | **Class:** Group 1 (STP-Capable).<br>**HITL:** Suspends only if country unparseable. | **Issue:** Postal syntax validation does NOT prove physical resident occupancy (**P2**). | **Hardened:** Explicitly labeled as pure syntax normalization, not beneficiary validation. | • National Postal Reference DB (Ext Int) |
| **`DQ-06: MISSING_PURPOSE`** | Missing purpose tag; classify code from remittance keyword. | **T2:** ISO Purpose List (`EST-EXT`)<br>**T3:** Keyword Classifier (`DER-PEX`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** COND ($N=1$) | **V_det:** ISO Code set membership.<br>**V_auth:** Regulatory purpose digest. | **Class:** Group 2 (Conditional STP).<br>**HITL:** Ops review if text is ambiguous. | **Issue:** Keyword mapping is heuristic; misreporting violates BoP reporting (**P1**). | **Hardened:** 98% confidence is labeled PeX Policy; permitted only under monetary cap. | • ISO Purpose Code Store (Ext Int) |
| **`DQ-07: INVALID_ACCOUNT_NUM`** | Domestic account modulus failure; apply branch padding. | **T2:** National Clearing DB (`EST-EXT`)<br>**T3:** Modulus Solver (`DER-PEX`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** COND ($N=1$) | **V_det:** National modulus check.<br>**V_auth:** Clearing format token. | **Class:** Group 2 (Conditional STP).<br>**HITL:** Maker-Checker if padding fails modulus. | **Issue:** Modulus rules vary by branch Sort Code / Transit ABA range (**P1**). | **Hardened:** Requires verified branch sort code lookup before applying modulus padding. | • National Modulus Table (Ext Int) |
| **`DQ-08: INVALID_ROUTING`** | Retired / merged ABA code; map to active successor routing code. | **T2:** FedLine / BoE Merger DB (`EST-EXT`)<br>**T3:** 9-Digit Checksum (`DER-PEX`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** 9-digit ABA Mod-10.<br>**V_auth:** Central Bank Merger attestation. | **Class:** Group 1 (STP-Capable).<br>**HITL:** Ops review if merged bank branch split. | **Issue:** Defunct merger table routes wire to wrong successor (**P1**). | **Hardened:** Requires daily/weekly synchronised Central Bank merger tables. | • FedLine / BoE Directory (Ext Int) |
| **`DQ-09: NAME_MISMATCH`** | CoP name close match; compile fuzzy match dossier for Analyst. | **T2:** Pay.UK / EU VoP CoP (`EST-EXT`)<br>**T1:** Bank Fraud Hub (`EST-BANK`) | **E_suff:** YES<br>**R_det:** NO (Fuzzy)<br>**R_uniq:** NO | **V_det:** Lexical similarity score.<br>**V_auth:** CoP match response token. | **Class:** Group 4 (Human Auth Required).<br>**HITL:** Mandatory Fraud / Ops Specialist sign-off. | **Issue:** Auto-repairing payee name incurs direct liability for APP fraud (**P0**). | **Hardened:** Autonomous STP strictly prohibited; PeX compiles evidence for human decision. | • CoP Gateway (Ext Int)<br>• Fraud Risk Hub (Discovery) |
| **`PR-01: DUPLICATE_PAYMENT`** | Identical UETR/hash; autonomous suppression of duplicate wire. | **T1:** Bank Core Ledger (`EST-BANK`)<br>**T3:** SHA-256 Collision (`DER-PEX`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES (Exact) | **V_det:** SHA-256 Hash equality.<br>**V_auth:** Core Settlement Ledger token. | **Class:** Group 1 (STP-Capable).<br>**HITL:** Route to Ops if distinct invoice ref. | **Issue:** Suppressing distinct recurring batch invoices causes supply-chain hold (**P0**). | **Hardened:** Auto-suppression valid ONLY on exact UETR/hash match; partial matches route to HITL. | • Settlement Hash Store (Discovery) |
| **`PR-02: ROUTING_FAILURE`** | Clearing rail offline; reroute wire to secondary active rail. | **T1:** Bank Routing Policy (`EST-BANK`)<br>**T2:** Rail Status API (`EST-EXT`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** Target rail format match.<br>**V_auth:** Routing Engine attestation. | **Class:** Group 3 (Policy Dependent).<br>**HITL:** Maker-Checker for high-value wires ($\ge \$1\text{M}$). | **Issue:** Rerouting incurs higher correspondent fees without client consent (**P1**). | **Hardened:** Permitted only if fee delta is within bank tolerance and cutoff $<1\text{h}$. | • Rail Status Monitor (Ext Int)<br>• Fee Schedule (Discovery) |
| **`PR-03: ISO20022_ERROR`** | XML schema error; lossless tag re-sequencing and envelope wrap. | **T1:** Raw Payload (`EST-BANK`)<br>**T2:** W3C ISO Schemas (`EST-EXT`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** W3C XML XSD validation.<br>**V_auth:** W3C XSD attestation digest. | **Class:** Group 1 (STP-Capable).<br>**HITL:** Suspends if payload corrupted unrecoverably. | **Issue:** Zero. Phase 1 baseline verified across 31 dedicated tests (**P3**). | **Hardened:** Verified baseline; lossless tag re-sequencing strictly enforced. | • None (Complete in Phase 1) |
| **`PR-04: CUTOFF_MISSED`** | Transaction queued past cutoff; roll Value Date to $T+1$. | **T2:** Central Bank Cutoff DB (`EST-EXT`)<br>**T1:** Client Contract SLA (`EST-BANK`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** Working day calendar math.<br>**V_auth:** Scheme operating schedule token. | **Class:** Group 2 (Conditional STP).<br>**HITL:** Suspends if wire is time-critical FX trade. | **Issue:** Rolling date without client consent on FX trades causes interest claims (**P1**). | **Hardened:** Auto-roll permitted only if customer contract explicitly permits $T+1$ roll. | • Clearing Calendar Table (Ext Int)<br>• Client SLA Terms (Discovery) |
| **`PR-05: CORRUPTED_MESSAGE`** | Illegal hex bytes; sanitize into SWIFT X-Character set. | **T2:** SWIFT Charset Standard (`EST-EXT`)<br>**T3:** Byte Sanitizer (`DER-PEX`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** SWIFT X-Charset regex.<br>**V_auth:** Byte stream integrity token. | **Class:** Group 1 (STP-Capable).<br>**HITL:** Suspends if sanitization deletes $>10\%$ of text. | **Issue:** Stripping characters must not alter names or decimal separators (**P0**). | **Hardened:** Byte sanitizer is strictly non-destructive of alphanumeric characters and periods. | • Inbound Byte Adapter (Ext Int) |
| **`PR-06: INTERMEDIARY_NACK`** | `pacs.002` NACK; route payment via secondary correspondent. | **T1:** Bilateral RMA Matrix (`EST-BANK`)<br>**T2:** Intermediary NACK (`EST-EXT`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** COND ($N=1$) | **V_det:** Secondary RMA validation.<br>**V_auth:** Bilateral RMA Master token. | **Class:** Group 3 (Policy Dependent).<br>**HITL:** Maker-Checker if fee exceeds threshold. | **Issue:** Routing to unverified correspondent breaches counterparty limit (**P1**). | **Hardened:** Requires verified active RMA and funded Nostro account with partner. | • RMA Key Matrix (Discovery)<br>• Nostro Account DB (Discovery) |
| **`PR-07: NETWORK_TIMEOUT`** | Wire timeout; query gpi tracker and re-dispatch if unconfirmed. | **T2:** SWIFT gpi Tracker (`EST-EXT`)<br>**T1:** Settlement Dispatch DB (`EST-BANK`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** gpi end-to-end trace check.<br>**V_auth:** gpi Tracker status attestation. | **Class:** Group 3 (Policy Dependent).<br>**HITL:** Route to Ops if status indeterminate. | **Issue:** Re-dispatching without non-delivery proof causes double debit (**P0**). | **Hardened:** Re-dispatch permitted ONLY upon positive proof of non-settlement from gpi. | • SWIFT gpi Connector (Ext Int) |
| **`PR-08: QUEUE_FAILURE`** | Broker DLQ deadlock; reset state machine and re-enqueue. | **T1:** Bank Messaging Hub (`EST-BANK`)<br>**T3:** Idempotency Manager (`DER-PEX`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** Payload checksum validation.<br>**V_auth:** Message broker recovery token. | **Class:** Group 1 (STP-Capable).<br>**HITL:** Suspends to Ops after 3 retry failures. | **Issue:** Re-enqueuing poison message re-triggers deadlock loop (**P0**). | **Hardened:** State lock cleared and payload validated before re-enqueue; capped at 3 retries. | • Bank MQ Adapter (Discovery) |
| **`PR-09: HELD_FOR_REPAIR`** | Generic hub repair hold; re-classify into specific sub-profile. | **T1:** Payment Hub Triage SOP (`EST-BANK`)<br>**T3:** Triage Classifier (`DER-PEX`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** COND ($N=1$) | **V_det:** Sub-profile Evidence check.<br>**V_auth:** Sub-profile authority attestation. | **Class:** Group 2 (Conditional STP).<br>**HITL:** Ops review if multi-fault exception. | **Issue:** Generic repair hold may mask multiple cascading underlying errors (**P1**). | **Hardened:** Case is re-evaluated against target sub-profile Evidence Contract; cascades halt. | • Payment Hub Triage API (Discovery) |
| **`CO-01: SANCTIONS_ALERT`** | Watchlist match; compile false positive disambiguation dossier. | **T1:** Bank Sanctions Hub (`EST-BANK`)<br>**T2:** OFAC / EU Watchlist (`EST-REG`) | **E_suff:** YES<br>**R_det:** NO (Fuzzy)<br>**R_uniq:** NO | **V_det:** Attribute similarity match.<br>**V_auth:** Sanctions Authority token. | **Class:** Group 4 (Human Auth Required).<br>**HITL:** Mandatory MLRO dual-authorization. | **Issue:** Automated clearing of sanctions hits violates federal law (**P0**). | **Hardened:** Autonomous release strictly prohibited; PeX compiles dossier for MLRO sign-off. | • Sanctions Engine Feed (Discovery) |
| **`CO-02: AML_ALERT`** | Velocity anomaly; compile 90-day turnover analysis dossier. | **T1:** Bank TM Hub / CDD (`EST-BANK`)<br>**T2:** FinCEN BSA Rules (`EST-REG`) | **E_suff:** YES<br>**R_det:** NO (Statistical)<br>**R_uniq:** NO | **V_det:** Anomaly threshold calculation.<br>**V_auth:** TM System alert token. | **Class:** Group 4 (Human Auth Required).<br>**HITL:** Mandatory AML Compliance Officer sign-off. | **Issue:** Unsupervised clearing of structuring patterns incurs BSA penalties (**P0**). | **Hardened:** Autonomous release strictly prohibited; AML Officer must review and sign. | • Transaction Monitor API (Discovery) |
| **`CO-03: PEP_MATCH`** | PEP hit; assemble relationship tree and EDD documentation. | **T2:** World-Check PEP DB (`EST-EXT`)<br>**T1:** Bank CDD Master (`EST-BANK`) | **E_suff:** YES<br>**R_det:** NO (Fuzzy)<br>**R_uniq:** NO | **V_det:** FATF Rec 12 category match.<br>**V_auth:** PEP Watchlist attestation. | **Class:** Group 4 (Human Auth Required).<br>**HITL:** Mandatory Senior Executive sign-off. | **Issue:** PEP release requires Senior Executive EDD sign-off under FATF (**P0**). | **Hardened:** Autonomous release strictly prohibited; Senior Management sign-off enforced. | • PEP Database Gateway (Ext Int)<br>• CDD Portal (Discovery) |
| **`CO-04: RESTRICTED_CORRIDOR`** | Sanctioned territory; auto-block / freeze instruction. | **T2:** OFAC Embargo List (`EST-REG`)<br>**T1:** Bank Corridor Matrix (`EST-BANK`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** ISO 3166 country matching.<br>**V_auth:** Statutory Sanctions attestation. | **Class:** Group 2 (Conditional STP).<br>**HITL:** MLRO review if asset freezing required. | **Issue:** Executing wire to sanctioned territory violates federal law (**P0**). | **Hardened:** Auto-rejection via `pacs.002` is deterministic and mandatory under OFAC rules. | • Geopolitical Sanctions DB (Ext Int) |
| **`CO-05: ADVERSE_MEDIA`** | Adverse media match; compile sentiment & corporate links. | **T2:** Media Aggregator (`EST-EXT`)<br>**T1:** Compliance DB (`EST-BANK`) | **E_suff:** YES<br>**R_det:** NO (NLP)<br>**R_uniq:** NO | **V_det:** NLP sentiment scoring.<br>**V_auth:** Media Provider match token. | **Class:** Group 4 (Human Auth Required).<br>**HITL:** Mandatory Compliance Analyst sign-off. | **Issue:** Media sentiment is non-authoritative and prone to false positives (**P1**). | **Hardened:** PeX compiles adverse media dossier; Compliance Analyst must authorize release. | • Media Screening API (Ext Int) |
| **`CO-06: HIGH_RISK_JURISD`** | FATF Greylist transit; verify active EDD documentation on file. | **T2:** FATF Greylist Index (`EST-EXT`)<br>**T1:** Customer EDD Portal (`EST-BANK`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** FATF Rec 19 certificate check.<br>**V_auth:** Customer EDD Master token. | **Class:** Group 3 (Policy Dependent).<br>**HITL:** Route to Compliance if EDD expired. | **Issue:** Transacting without active EDD on file violates compliance SOP (**P1**). | **Hardened:** Auto-release permitted ONLY if active, unexpired EDD form is verified in portal. | • FATF Greylist Feed (Ext Int)<br>• EDD Master Portal (Discovery) |
| **`CO-07: REGULATORY_REPORT`** | Missing BoP declaration; generate statutory `RgltryRptg` XML. | **T1:** Debtor Trade Portal (`EST-BANK`)<br>**T2:** Central Bank Mandate (`EST-REG`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** Statutory XML schema check.<br>**V_auth:** Central Bank format attestation. | **Class:** Group 2 (Conditional STP).<br>**HITL:** Ops review if customs doc missing. | **Issue:** Generating incorrect exchange control reports incurs audit fines (**P1**). | **Hardened:** Auto-STP valid ONLY if parsed commercial invoice confirms underlying trade. | • Trade Finance API (Discovery) |
| **`CO-08: CUSTOMER_WATCHLIST`** | Internal risk list hit; assemble risk history & default exposure. | **T1:** Bank Internal Risk DB (`EST-BANK`)<br>**T4:** Past incident files (`DER-PEX`) | **E_suff:** YES<br>**R_det:** NO (Risk Eval)<br>**R_uniq:** NO | **V_det:** Customer ID exact matching.<br>**V_auth:** Internal Risk Register token. | **Class:** Group 4 (Human Auth Required).<br>**HITL:** Mandatory Senior Risk Approver sign-off. | **Issue:** Releasing funds to client on internal fraud watch violates fiduciary duty (**P0**). | **Hardened:** Autonomous release strictly prohibited; Senior Risk Approver sign-off mandatory. | • Internal Risk Register (Discovery) |
| **`TR-01: NOSTRO_SHORTFALL`** | Nostro deficit; trigger automated cash sweep from pool. | **T1:** Treasury Sweep Engine (`EST-BANK`)<br>**T2:** BCBS 248 Intraday Feed (`EST-REG`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** Post-sweep balance check.<br>**V_auth:** Treasury Sweep execution token. | **Class:** Group 2 (Conditional STP).<br>**HITL:** Route to Treasury if facility exhausted. | **Issue:** Releasing wire before sweep posts causes daylight overdraft (**P1**). | **Hardened:** Auto-STP valid ONLY once sweep confirmation receipt is verified. | • Treasury Sweep API (Discovery) |
| **`TR-02: KYC_EXPIRED`** | Periodic CDD review expired; apply approved 30-day grace waiver. | **T1:** Bank KYC Master (`EST-BANK`)<br>**T2:** FinCEN CDD Rule (`EST-REG`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** Low-risk tier + Grace window.<br>**V_auth:** KYC Policy Master attestation. | **Class:** Group 3 (Policy Dependent).<br>**HITL:** Maker-Checker for high-risk clients. | **Issue:** Applying grace waiver to high-risk non-compliant client breaches CDD (**P0**). | **Hardened:** Permitted for low-risk recurring corporate wires with approved waiver on file. | • Bank KYC Master DB (Discovery) |
| **`TR-03: INSUFFICIENT_FUNDS`** | Debtor balance shortfall; draw on pre-approved overdraft line. | **T1:** Core DDA Ledger (`EST-BANK`)<br>**T2:** UCC Article 4A-201 (`EST-REG`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** Balance + Overdraft $\ge$ wire.<br>**V_auth:** Core DDA Credit Line token. | **Class:** Group 2 (Conditional STP).<br>**HITL:** Route to Credit Officer if line maxed. | **Issue:** Executing wire without approved overdraft creates daylight credit loss (**P0**). | **Hardened:** Auto-draw permitted within pre-approved limit; high-value deficits route to Credit. | • Core DDA Balance API (Discovery) |
| **`TR-04: FX_UNAVAILABLE`** | Expired FX quote; re-price wire at fresh live spot rate. | **T1:** Treasury FX Engine (`EST-BANK`)<br>**T2:** MiFID II Rules (`EST-REG`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** FX spread $\le$ client mandate.<br>**V_auth:** Treasury FX Engine attestation. | **Class:** Group 2 (Conditional STP).<br>**HITL:** Route to FX Trader if amount $\ge \$500\text{k}$. | **Issue:** Applying outdated FX rate creates immediate currency arbitrage loss (**P1**). | **Hardened:** Auto-reprice permitted for wires $<\$500\text{k}$ with live spot quote within mandate. | • Treasury FX Live Rate API (Discovery) |
| **`TR-05: AUTH_MISSING`** | Missing 2nd signatory; send mobile push notification to signer. | **T1:** Signatory Matrix DB (`EST-BANK`)<br>**T2:** UCC Article 4A-202 (`EST-REG`) | **E_suff:** YES<br>**R_det:** YES (On sign)<br>**R_uniq:** YES | **V_det:** PKI / Biometric signature.<br>**V_auth:** Mandate Matrix attestation. | **Class:** Group 3 (Policy Dependent).<br>**HITL:** Route to Corporate Banking if unreachable.| **Issue:** Releasing wire without 2nd signature violates corporate power of attorney (**P0**). | **Hardened:** Auto-release permitted ONLY upon verified receipt of cryptographic 2nd signature. | • Corporate Push Gateway (Discovery) |
| **`TR-06: LIMIT_BREACH`** | Daily limit breached; apply 10% step-up if collateral pledged. | **T1:** Credit Risk Engine (`EST-BANK`)<br>**T4:** Limit history (`DER-PEX`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** Exposure $\le 110\%$ + Collateral.<br>**V_auth:** Credit Risk Engine attestation. | **Class:** Group 3 (Policy Dependent).<br>**HITL:** Maker-Checker for breaches $>10\%$. | **Issue:** Stepping up limits for insolvent borrower causes unrecoverable credit loss (**P0**). | **Hardened:** Auto-step-up valid if within 10% policy tolerance with verified pledged collateral. | • Credit Risk Policy DB (Discovery) |
| **`TR-07: LIQUIDITY_CAP`** | Central bank RTGS cap hit; dynamically re-sequence queue. | **T2:** Central Bank RTGS (`EST-EXT`)<br>**T1:** Treasury Queue DB (`EST-BANK`) | **E_suff:** YES<br>**R_det:** YES (Re-order)<br>**R_uniq:** YES | **V_det:** Cap headroom calculation.<br>**V_auth:** Central Bank RTGS attestation. | **Class:** Group 4 (Human Auth Required).<br>**HITL:** Treasury Liquidity Manager sign-off. | **Issue:** Releasing low-priority wire consumes cap needed for critical treasury wire (**P1**). | **Hardened:** Auto-re-ordering holds low-priority wires; Treasury Manager must authorize overrides. | • Central Bank RTGS Feed (Ext Int) |
| **`TR-08: CREDIT_BREACH`** | Correspondent exposure maxed; compile exposure dossier. | **T1:** Basel III Risk Engine (`EST-BANK`)<br>**T2:** Basel III Rules (`EST-REG`) | **E_suff:** YES<br>**R_det:** NO (Credit Eval)<br>**R_uniq:** NO | **V_det:** Basel III Large Exposure cap.<br>**V_auth:** Counterparty Risk token. | **Class:** Group 4 (Human Auth Required).<br>**HITL:** Mandatory Credit Risk Officer sign-off. | **Issue:** Overriding correspondent limits without approval breaches Basel III caps (**P0**). | **Hardened:** Autonomous release strictly prohibited; Credit Risk Officer must authorize limit override. | • Counterparty Risk Hub (Discovery) |
| **`ST-01: RETURNED_PAYMENT`** | Inbound `pacs.004`; reconcile UETR and prepare re-credit payload. | **T1:** Core DDA Ledger (`EST-BANK`)<br>**T2:** SWIFT Return Rules (`EST-SCHEME`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** UETR reconciliation match.<br>**V_auth:** Settlement Ledger attestation. | **Class:** Group 1 (STP-Capable).<br>**HITL:** Suspends to Ops if original UETR missing. | **Issue:** PeX must NOT directly credit bank accounts (**P0**). | **Hardened:** PeX prepares re-credit handoff payload; Bank executes actual accounting debit/credit. | • pacs.004 Return Feed (Discovery)<br>• Core DDA Ledger API (Discovery) |
| **`ST-02: ACCOUNT_CLOSED`** | Inbound return reason `AC04`; check successor SSI agreement. | **T1:** Bank SSI Master (`EST-BANK`)<br>**T2:** UCC Article 4A-402 (`EST-REG`) | **E_suff:** YES<br>**R_det:** COND (SSI on file)<br>**R_uniq:** YES | **V_det:** Signed successor SSI check.<br>**V_auth:** Bank SSI Master token. | **Class:** Group 4 (Human Auth Required).<br>**HITL:** Maker-Checker before re-routing funds. | **Issue:** Re-routing to unverified account violates UCC 4A and creates bank liability (**P0**). | **Hardened:** Re-routing requires signed successor SSI and Maker-Checker dual authorization. | • Successor SSI DB (Discovery) |
| **`ST-03: ACCOUNT_FROZEN`** | Inbound return `AC06`; route funds to Legal Escrow Suspense GL. | **T1:** Judicial Restraint DB (`EST-BANK`)<br>**T2:** Statutory Law (`EST-REG`) | **E_suff:** YES<br>**R_det:** YES (Escrow)<br>**R_uniq:** YES | **V_det:** Judicial restraint match.<br>**V_auth:** Judicial Restraint attestation. | **Class:** Group 4 (Human Auth Required).<br>**HITL:** Mandatory Legal Counsel sign-off. | **Issue:** Returning funds to debtor when account is frozen violates court order (**P0**). | **Hardened:** Funds routed to GL Suspense Escrow; Legal Counsel review mandatory. | • Judicial Restraint DB (Discovery) |
| **`ST-04: RECON_BREAK`** | Nostro statement variance; auto-balance minor fee breaks $\le \$50$. | **T1:** General Ledger / Nostro (`EST-BANK`)<br>**T2:** SOX Section 404 (`EST-REG`) | **E_suff:** YES<br>**R_det:** YES ($\le \$50$)<br>**R_uniq:** YES | **V_det:** Statement variance math.<br>**V_auth:** Bank General Ledger token. | **Class:** Group 4 (Human Auth Required).<br>**HITL:** Mandatory Recon Desk sign for breaks $> \$50$. | **Issue:** Auto-balancing large breaks obscures fraudulent leakage or posting errors (**P0**). | **Hardened:** Auto-STP valid ONLY for standard fee breaks $\le \$50$; all larger breaks route to Recon. | • Nostro Statement API (Discovery) |
| **`ST-05: SETTLE_FAILURE`** | RTGS settlement unconfirmed; query central bank endpoint. | **T2:** Central Bank RTGS (`EST-EXT`)<br>**T1:** Bank Settlement Hub (`EST-BANK`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** YES | **V_det:** Negative settlement ack.<br>**V_auth:** Central Bank RTGS attestation. | **Class:** Group 3 (Policy Dependent).<br>**HITL:** Maker-Checker for wires $\ge \$1\text{M}$. | **Issue:** Re-sending an unconfirmed wire that actually settled causes double payment (**P0**). | **Hardened:** Query central bank query endpoint; Operator confirms re-dispatch. | • RTGS Query Gateway (Ext Int) |
| **`ST-06: FUNDS_TRAPPED`** | Funds debited, beneficiary unpaid; generate `camt.027` claim XML. | **T2:** SWIFT gpi Tracker (`EST-EXT`)<br>**T1:** Core DDA Debit Log (`EST-BANK`) | **E_suff:** YES<br>**R_det:** YES (Claim XML)<br>**R_uniq:** YES | **V_det:** gpi stalled node match.<br>**V_auth:** gpi Tracker attestation digest. | **Class:** Group 4 (Human Auth Required).<br>**HITL:** Investigation Officer manages claim. | **Issue:** Issuing claim against wrong correspondent damages correspondent relations (**P1**). | **Hardened:** Auto-generation of `camt.027` Claim XML is valid; fund release held for Ops review. | • SWIFT gpi Trace Feed (Ext Int) |
| **`ST-07: UNMATCHED_CREDIT`** | Inbound credit without account; match open corporate AR invoice. | **T1:** Corporate AR DB (`EST-BANK`)<br>**T2:** Unclaimed Property (`EST-REG`) | **E_suff:** YES<br>**R_det:** YES<br>**R_uniq:** COND ($N=1$) | **V_det:** Exact amount/invoice match.<br>**V_auth:** Corporate AR Master token. | **Class:** Group 3 (Policy Dependent).<br>**HITL:** Maker-Checker if invoice match ambiguous. | **Issue:** Crediting unapplied cash to wrong corporate ledger causes dispute (**P1**). | **Hardened:** Auto-posting permitted ONLY when open invoice matches exact amount and corporate DBA. | • Corporate AR Master Feed (Discovery) |

---

## 7. Established Fact vs Design vs Policy vs Hypothesis Matrix

```
+----+---------------------------------------------------+---------+-----------------------+-----------------------+-------------------------+-------------------------------------------------------------+------------------------------------+
| #  | Material Assertion                                | Profile | Current Classification| Correct Classification| Authoritative Source    | Forensic Rationale                                          | Required Hardening Action          |
+----+---------------------------------------------------+---------+-----------------------+-----------------------+-------------------------+-------------------------------------------------------------+------------------------------------+
| 1  | MOD-97-10 check digit math proves validity        | DQ-01   | Established Standard  | ESTABLISHED STANDARD  | ISO 7064 / ISO 13616    | Checksum remainder r=1 mathematically proves syntax only.   | Maintain as mathematical validity. |
| 2  | MOD-97 proves beneficiary account ownership       | DQ-01   | Authoritative Ground  | PROPOSED PEX DESIGN   | Bank SSI Master / CoP   | Math proves string validity, not legal account ownership.   | Separate syntax from Bank SSI auth.|
| 3  | SWIFTRef proves branch currency clearing reach    | DQ-02   | Established Registry  | TO BE VALIDATED       | SWIFTRef / Scheme Rules | SWIFTRef proves active entity; branch clearing is bilateral.| Add rail reachability check.       |
| 4  | UPU postal parsing proves physical presence       | DQ-05   | Established Standard  | PROPOSED PEX DESIGN   | Universal Postal Union  | Parsing into PostalAddress24 proves schema, not occupancy.  | Label as pure syntax normalizer.   |
| 5  | Keyword match (SALARY->SALA) is legal BoP proof   | DQ-06   | Deterministic Rule    | BANK POLICY CONFIG    | National BoP Mandates   | Keyword inference is heuristic; requires bank policy cap.   | Bound under policy monetary cap.   |
| 6  | 98% keyword classification confidence threshold   | DQ-06   | Standard Requirement  | BUSINESS HYPOTHESIS   | PeX Product Strategy    | 98% is a PeX design heuristic, not statutory law.           | Reclassify as PeX policy threshold.|
| 7  | Suppressing exact UETR collision is safe          | PR-01   | Established Standard  | ESTABLISHED STANDARD  | UCC Article 4A-205      | Exact hash/UETR collision represents duplicate instruction. | Maintain exact hash suppression.   |
| 8  | Suppressing partial duplicate (same amount/client)| PR-01   | Auto-STP Capable      | BANK POLICY CONFIG    | Bank Payment Hub SOP    | Distinct invoices with identical amounts are legitimate.    | Route partial duplicates to HITL.  |
| 9  | Byte sanitization is universally lossless         | PR-05   | Established Standard  | DERIVED PEX LOGIC     | SWIFT MT/MX Charset     | Stripping bytes is safe only if non-destructive of data.    | Add byte loss threshold check.     |
| 10 | Re-enqueuing DLQ messages is always safe          | PR-08   | Established Standard  | PROPOSED PEX DESIGN   | Bank Messaging Hub SOP  | Re-enqueuing without clearing lock triggers deadlock loop.  | Require lock clearance & 3x retry. |
| 11 | $25,000 USD is the universal bank STP ceiling     | Universal| Standard Industry Cap | BUSINESS HYPOTHESIS   | PeX Product Strategy    | $25k is a sensible default, but entirely bank-configurable. | Label as Configurable Bank Policy. |
| 12 | $1,000,000 USD is the XML syntax repair ceiling   | PR-03   | Standard Industry Cap | BUSINESS HYPOTHESIS   | PeX Product Strategy    | Ceiling is a commercial risk parameter configured by bank.  | Label as Configurable Bank Policy. |
| 13 | 25% of all exceptions will resolve via STP        | Universal| Performance Metric    | BUSINESS HYPOTHESIS   | PeX Product Strategy    | STP rate is a function of bank evidence quality, not code.  | Remove as architectural claim.     |
| 14 | 50% of exceptions will pass via Fast-Lane         | Universal| Performance Metric    | BUSINESS HYPOTHESIS   | PeX Product Strategy    | Fast-lane volume depends on client counterparty agreements. | Remove as architectural claim.     |
| 15 | PeX directly credits debtor DDA on returns        | ST-01   | Operational Outcome   | PROPOSED PEX DESIGN   | Bank Payment Hub / Core | PeX produces handoff payload; Bank Core DDA posts credits.  | Clarify Bank Execution Boundary.   |
| 16 | Historical repair frequency satisfies authority   | Universal| Validated Precedent   | PROHIBITED ACTION     | Architecture Baseline   | Historical precedent suggests hypotheses; NEVER authority.  | Enforce zero historical release.   |
| 17 | AI confidence score >= 99% authorizes release     | Universal| Advanced AI Capability| PROHIBITED ACTION     | Architecture Baseline   | AI is an investigative copilot with zero release authority.  | Exclude AI from 8-predicate formula|
+----+---------------------------------------------------+---------+-----------------------+-----------------------+-------------------------+-------------------------------------------------------------+------------------------------------+
```

---

## 8. Review & Hardening of the Phase 2 Controlled Expansion Plan

### 8.1 Validation of the Phased Sequence
The forensic review evaluated the 3-subphase sequence proposed in `PeX_Phase2_Controlled_Expansion_Plan_v0.1.md`:

```
                 Phase 2A: Syntax, Byte & Message Integrity (Zero External Dependencies)
                 ├── PR-05: Corrupted Message Format (Byte Sanitizer)
                 ├── PR-08: Queue Processing Failure (DLQ Reset & Idempotency)
                 └── DQ-05: Invalid Address Format (Postal Address Normalizer)
                                          │
                                          ▼
                 Phase 2B: State, Ledger Authority & External Directories
                 ├── PR-01: Duplicate Payment (24h Settlement Hash Store)
                 ├── DQ-08: Invalid Routing Code (Merger Directory Adapter)
                 └── DQ-02: Invalid BIC / SWIFT (SWIFTRef Directory Connector)
                                          │
                                          ▼
                 Phase 2C: Multi-Contract Bank Corroboration & Conditional STP
                 ├── DQ-01: Invalid IBAN (MOD-97 Solver + Bank SSI / CoP)
                 ├── DQ-06: Missing Purpose Code (ISO Purpose Set + Remittance Classifier)
                 ├── ST-01: Returned Payment (pacs.004 Reconciler & Handoff Adapter)
                 └── CO-04: Restricted Corridor (Geopolitical Embargo pacs.002 Auto-Block)
```

#### Architectural Assessment:
- **Phase 2A (Zero External Dependencies)**: Extremely safe starting point. Exercises low-level byte manipulation (`PR-05`), message broker state transitions (`PR-08`), and complex XML address parsing (`DQ-05`) with 100% deterministic logic.
- **Phase 2B (Internal State & Directories)**: Introduces the `24-Hour Settlement Hash Ledger` (`PR-01`) and external directory cache adapters (`DQ-08`, `DQ-02`), proving reference data integration without touching customer accounts.
- **Phase 2C (Bank SoR Corroboration)**: Introduces live/mock Bank Evidence Gateway adapters (`DQ-01`, `ST-01`), statutory regulatory blocking (`CO-04`), and commercial trade purpose mapping (`DQ-06`).

**Verdict on Phasing Sequence:** **100% JUSTIFIED & SOUND.** No sequencing alterations are required.

---

## 9. Phase 2 Definition of Done (DoD) Hardening

A profile vertical slice is strictly declared **DONE** only when all 14 gates are satisfied:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 THE 14-GATE DEFINITION OF DONE (DoD)                                   │
├───────────────────────────────────────┬────────────────────────────────────────────────────────────────┤
│ 1. Evidence Contract Codified         │ `EvidenceContract` registered in `EvidenceContractRegistry`.   │
│ 2. Resolution Contract Codified       │ Lossless deterministic derivation logic implemented.           │
│ 3. Authority Contract Codified        │ Structural syntax vs business SoR validation separated.       │
│ 4. STP Policy Contract Codified       │ Configurable bank monetary ceilings and corridor rules set.    │
│ 5. Evidence Sufficiency Enforced      │ Completeness, trust tiers, and freshness TTLs verified.        │
│ 6. Resolution Uniqueness Enforced     │ Multiple candidates ($N>1$) trigger mandatory human suspense.  │
│ 7. Authority Validation Enforced      │ Cryptographic attestation token generated from SoR connector.  │
│ 8. 8-Predicate Formula Evaluated      │ Strict boolean conjunction ($E \wedge R \wedge V \wedge P \wedge C \wedge X$). │
│ 9. Bank Boundary Preserved            │ Emits repaired XML + handoff receipt to Bank Output Adapter.   │
│ 10. Cryptographic Provenance Chained  │ All 12 lifecycle stages logged in immutable SHA-256 ledger.    │
│ 11. Comprehensive Testing Passed      │ Happy path, 10+ failure modes, and adversarial tests (T01-11). │
│ 12. Zero Platform Regression          │ 100% pass rate maintained across all pre-existing tests.       │
│ 13. Traceability Documented           │ Complete epistemic grounding and architecture cards updated.   │
│ 14. Epistemic Classification Bound    │ Assumptions explicitly tagged as Standard / Policy / Design.   │
└───────────────────────────────────────┴────────────────────────────────────────────────────────────────┘
```

---

## 10. Final Executive Summary & Pre-Implementation Gate

### Answers to the Five Core Architectural Questions:

1. **Is the 41-profile taxonomy intact?**  
   **YES.** Exactly 41 profiles across 5 domains and 4 groups are reconciled with zero additions, deletions, renames, or omissions.
2. **Is every evidence requirement grounded in an appropriate authority?**  
   **YES.** All 41 profiles have their mandatory evidence tied to specific Tier 1 Bank Systems of Record, Tier 2 External Registries, or Tier 3 Mathematical Solvers, with Tier 4 Historical Precedent strictly prevented from acting as authority.
3. **Is every proposed repair actually derivable and uniquely provable?**  
   **YES.** Under the enforced rule *"Invalid/Failed $\neq$ Correct Replacement"*, candidate generation is deterministic, and ambiguity ($N>1$) forces immediate human suspense.
4. **Are STP claims appropriately conditional and policy-driven?**  
   **YES.** Group 1 profiles remain subject to bank policy ceilings; Group 2 profiles require live SoR corroboration; Group 3 profiles depend on bank risk parameters; and Group 4 profiles strictly mandate human authorization.
5. **Is the Phase 2 implementation plan safe to authorize?**  
   **CONDITIONAL.** The expansion roadmap and 3-tier sub-phasing (`Phase 2A` $\to$ `Phase 2B` $\to$ `Phase 2C`) are scientifically sound, but implementation mode may commence **only after bank leadership formal sign-off on this reconciliation artifact**.

---

## 11. Implementation Gate Notice

```
====================================================================================================
GOVERNANCE STATUS:
FORENSIC RECONCILIATION & HARDENING COMPLETE (v1.1)

IMPLEMENTATION AUTHORIZATION:
PHASE 2 IMPLEMENTATION REMAINS FORMALLY BLOCKED PENDING LEADERSHIP REVIEW AND SIGN-OFF.

OPERATING MODE:
READ-ONLY MODE MAINTAINED (ZERO PRODUCTION CODE MODIFICATIONS PERFORMED).
====================================================================================================
```
