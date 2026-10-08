# PeX Phase 3 — Industrialization Architecture v0.1.2
## Architecture & Capability Design for the 30 Remaining Canonical Exception Profiles
### Governed Forensic Semantic Reconciliation

**Version:** v0.1.2  
**Status:** Architecture Forensic Reconciliation / Design Only  
**Purpose:** Phase 3 Industrialization Architecture Specification & Semantic Alignment  
**Engineering Authorization:** NOT GRANTED  
**Authoritative Baseline:** `PeX_Evidence_Driven_STP_Architecture_Baseline_v1.1.md`, `PeX_Phase2_Implementation_Contract_v1.3.md`, `PeX_Evidence_Acquisition_and_Resolution_Contract_v0.3.1.md`, `PeX_Wave0B_Implementation_Report_v0.1.md`, `PeX_Phase3_Industrialization_Architecture_v0.1.1.md`  

---

======================================================================
1. EXECUTIVE SUMMARY
======================================================================

### 1.1 Where We Are Now
The PeX (Payment Exception Resolution) platform has successfully:
1. **Closed Phase 2**: 11 of 41 canonical profiles implemented, forensically accepted, and backed by 423 green regression tests.
2. **Completed Wave 0A**: Established core platform contracts, canonical schemas, reference adapters, and the 12-scenario E2E execution test harness.
3. **Completed Wave 0B**: Delivered dynamic published Bank Evidence Required JSON resolution, fail-closed governance compilation, deterministic sandboxed expression evaluation, content-addressable SHA-256 evidence storage, multi-mode acquisition (Modes 1–4), PeX-native HITL closed loop, and an expanded 18-scenario canonical execution suite backed by 495 / 495 green tests.

### 1.2 The Industrialization Objective
The objective of Phase 3 Industrialization is **not** to build 30 separate, bespoke, siloed profile engines. Rather, the objective is to answer the primary architectural question:

> **"How should PeX implement the remaining 30 exception profiles using the smallest practical set of reusable, governed capability engines while preserving profile-specific evidence, authority, resolution, HITL, and STP semantics?"**

### 1.3 Semantic Reconciliation in v0.1.2
Version v0.1.2 corrects forensic semantic naming drift identified in earlier drafts where specific implementation mechanisms (e.g., "Amount Formatting / Decimals", "Value Date Past Cutoff / Rollover") were conflated with canonical profile taxonomy identities (e.g., `PR-05 Corrupted Message Format`, `PR-03 ISO 20022 Validation Error`). This artifact strictly restores the authoritative 41-profile taxonomy names and introduces rigorous conceptual distinctions between:
- **Canonical Profile**: Immutable BIAN/ISO payment exception identity.
- **Implementation Capability**: Technical algorithmic or transformation mechanism.
- **Resolution Pattern**: Reusable resolution behavior (`PAT-A` through `PAT-G`).
- **Evidence Contract**: Formal schema and trust tier establishing sufficiency ($E_{\text{suff}}$).
- **Authority Contract**: Sovereign source of record validating truth ($V_{\text{auth}}$).

### 1.4 Core Architectural Invariants Preserved
1. **The 41-Profile Taxonomy is Immutable**: Canonical names and profile codes are permanent.
2. **Phase 2 is Closed & Protected**: Phase 2 profiles and contracts cannot be refactored or re-engineered.
3. **The 8-Predicate STP Formula is Immutable**:
   $$\text{STP\_ELIGIBLE} = E_{\text{suff}} \land R_{\text{det}} \land R_{\text{uniq}} \land V_{\text{det}} \land V_{\text{auth}} \land P_{\text{bank}} \land C_{\text{comp}} \land X_{\text{pre}}$$
4. **Evidence Sufficiency $\ne$ STP Eligibility**: $E_{\text{suff}}$ is a necessary prerequisite, not a sufficient condition.
5. **Zero Autonomous Authority for AI**: LLM/AI confidence carries exactly $0\%$ autonomous execution authority.
6. **Bank Sovereign Execution Boundary**: Terminal state is `BANK_HANDOFF_READY` with `execution_owner = "BANK"`.
7. **Production Autonomous STP is Blocked**: This is a Design & Planning document; Wave 1 engineering is NOT AUTHORIZED.

---

======================================================================
2. PHASE 2 NO-REENGINEERING BOUNDARY & PROTECTED PROFILES
======================================================================

> **PHASE 2 NO-REENGINEERING BOUNDARY RULE:**  
> **Phase 3 industrialization must consume accepted Phase 2 contracts and implementations and must not refactor, rename, reclassify, redistribute, or behaviorally alter Phase 2 profile ownership unless a separately authorized architecture decision is issued.**

### 2.1 Protected Phase 2 Profiles Inventory
The 11 accepted and forensically verified Phase 2 profiles are strictly protected under their canonical taxonomy identities:

```
+---------------------------------------------------------------------------------------------------+
|                             PHASE 2 PROTECTED PROFILES (11 BASELINE)                              |
+-------+-------------------------------+-----------------------------------+-----------------------+
| Code  | Canonical Profile Name        | Phase 2 Implementation Context     | Governance Status     |
+-------+-------------------------------+-----------------------------------+-----------------------+
| DQ-01 | Invalid IBAN                  | Modulo-97-10 Checksum Derivation  | PROTECTED / ACCEPTED  |
| DQ-02 | Invalid BIC / SWIFT           | 8-to-11 Head Office Normalization | PROTECTED / ACCEPTED  |
| DQ-05 | Invalid Address Format        | Structured Postal Address Repair  | PROTECTED / ACCEPTED  |
| DQ-06 | Missing Purpose Code          | Purpose Code Mapping & Insertion  | PROTECTED / ACCEPTED  |
| DQ-08 | Invalid Routing Code          | Routing / Transit Discrepancy Fix | PROTECTED / ACCEPTED  |
| PR-01 | Duplicate Payment             | Hash Collision Suppression        | PROTECTED / ACCEPTED  |
| PR-03 | ISO 20022 Validation Error    | Schema / Syntax Validation Repair | PROTECTED / ACCEPTED  |
| PR-05 | Corrupted Message Format      | Governed Character Transformation | PROTECTED / ACCEPTED  |
| PR-08 | Queue Processing Failure      | Idempotent Queue Unblock & Retry  | PROTECTED / ACCEPTED  |
| CO-04 | Restricted Corridor           | Corridor Disambiguation Gate      | PROTECTED / ACCEPTED  |
| ST-01 | Returned Payment              | Return pacs.004 Re-Credit Package | PROTECTED / ACCEPTED  |
+-------+-------------------------------+-----------------------------------+-----------------------+
```

### 2.2 Boundary Distinctions
Phase 3 architecture explicitly distinguishes between three operational concepts:
- **A. Existing Phase 2 Profile Consumption**: The 11 accepted Phase 2 profiles execute via their existing verified pipelines and contracts. They are not being redesigned.
- **B. New Phase 3 Profile Implementation**: The 30 remaining un-implemented profiles that constitute the Phase 3 delivery scope.
- **C. Shared Capability Reuse**: Reusable capability engines (e.g. `RoutingClearingEngine`, `AccountMasterEngine`) provide shared domain logic that may be consumed by both existing Phase 2 profiles and new Phase 3 profiles without altering Phase 2 profile semantics or ownership.

---

======================================================================
3. CURRENT PEX BASELINE & PLATFORM RUNTIME
======================================================================

```
+---------------------------------------------------------------------------------------------------+
|                                   PEX PLATFORM STATE BASELINE                                      |
+--------------------------+------------------------------------------------------------------------+
| Phase 2 Status           | CLOSED (11 Profiles Accepted & Protected)                              |
+--------------------------+------------------------------------------------------------------------+
| Wave 0A Status           | COMPLETE (Platform Contracts, Schemas, 12 Canonical Scenarios)         |
+--------------------------+------------------------------------------------------------------------+
| Wave 0B Status           | COMPLETE (Dynamic Config Resolver, Governance Compiler, AST Sandbox,   |
|                          | Evidence Store, Multi-Mode Acquisition, HITL Closed-Loop, 18 Scenarios)|
+--------------------------+------------------------------------------------------------------------+
| Test Baseline            | 495 / 495 Tests Green (100% Pass Rate across 39 Test Modules)          |
+--------------------------+------------------------------------------------------------------------+
| Remaining Scope          | 30 Canonical Profiles across 5 BIAN Domains                            |
+--------------------------+------------------------------------------------------------------------+
| Production STP           | BLOCKED (Design & Planning Gate Only)                                  |
+--------------------------+------------------------------------------------------------------------+
```

---

======================================================================
4. REMAINING 30 PROFILES INVENTORY (CANONICAL TAXONOMY)
======================================================================

```
+---------------------------------------------------------------------------------------------------+
|                                 30 REMAINING CANONICAL PROFILES                                    |
+----------------------+---------+------------------------------------------------------------------+
| Domain               | Code    | Canonical Profile Name                                           |
+----------------------+---------+------------------------------------------------------------------+
| Data Quality (4)     | DQ-03   | Missing Beneficiary Data                                         |
|                      | DQ-04   | Missing Remittance Info                                          |
|                      | DQ-07   | Invalid Account Number                                           |
|                      | DQ-09   | Beneficiary Name Mismatch                                        |
+----------------------+---------+------------------------------------------------------------------+
| Processing (5)       | PR-02   | Routing Failure                                                  |
|                      | PR-04   | Cutoff Missed                                                    |
|                      | PR-06   | Intermediary Bank Rejection                                      |
|                      | PR-07   | Network Timeout                                                  |
|                      | PR-09   | Payment Held for Repair                                          |
+----------------------+---------+------------------------------------------------------------------+
| Compliance (7)       | CO-01   | Sanctions Screening Hit                                          |
|                      | CO-02   | AML Alert                                                        |
|                      | CO-03   | PEP Match                                                        |
|                      | CO-05   | Adverse Media Match                                              |
|                      | CO-06   | High-Risk Jurisdiction                                           |
|                      | CO-07   | Regulatory Reporting Required                                    |
|                      | CO-08   | Customer Watchlist Match                                         |
+----------------------+---------+------------------------------------------------------------------+
| Client / Treasury (8)| TR-01   | KYC Expired                                                      |
|                      | TR-02   | Insufficient Funds                                               |
|                      | TR-03   | Nostro Shortfall                                                 |
|                      | TR-04   | FX Rate Unavailable                                              |
|                      | TR-05   | Authorization Missing                                            |
|                      | TR-06   | Limit Breach                                                     |
|                      | TR-07   | Liquidity Constraint                                             |
|                      | TR-08   | Credit Exposure Breach                                           |
+----------------------+---------+------------------------------------------------------------------+
| Settlement /         | ST-02   | Account Closed                                                   |
| Returns (6)          | ST-03   | Beneficiary Account Frozen                                       |
|                      | ST-04   | Reconciliation Break                                             |
|                      | ST-05   | Settlement Failure                                               |
|                      | ST-06   | Funds Trapped at Correspondent                                   |
|                      | ST-07   | Unmatched Credit                                                 |
+----------------------+---------+------------------------------------------------------------------+
```

---

======================================================================
5. INDUSTRIALIZATION PRINCIPLES, CONCEPTUAL DISTINCTIONS & PIPELINE
======================================================================

### 5.1 The Core Operating Axiom
The PeX platform operates on the authoritative principle:

> **"Evidence determines eligibility. History informs the fix. Controls validate the repair. Policy determines whether it can STP. The bank retains execution control."**

### 5.2 Mandatory Conceptual Distinctions
To eliminate architecture and semantic ambiguity, PeX enforces five distinct concept levels:
1. **Canonical Profile (`ProfileID`)**: The authoritative business taxonomy identity (e.g., `PR-05 Corrupted Message Format`, `PR-03 ISO 20022 Validation Error`). Immutable across all documents and systems.
2. **Implementation Capability (`CapabilityEngine`)**: The technical algorithmic, data access, or transformation mechanism (e.g., ISO 7064 Modulo-97 calculator, XML XSD validator, character sanitizer).
3. **Resolution Pattern (`ResolutionPattern`)**: The generalized resolution behavior (`PAT-A` through `PAT-G`) classifying how candidates are derived and validated.
4. **Evidence Contract (`EvidenceModel`)**: The structured schema, required trust tier, and acquisition mode defining evidence completeness and determining $E_{\text{suff}}$.
5. **Authority Contract (`AuthoritySource`)**: The sovereign System of Record (DDA, SWIFTRef, RTGS, Screening Engine) that independently validates truth ($V_{\text{auth}}$).

### 5.3 Resolution Orchestration & Governed Execution Pipeline
To prevent monolithic coupling while maintaining strict determinism, an explicit **Resolution Orchestration / Resolution Contract** layer is introduced between domain capability engines and 8-predicate evaluation:

$$\text{Canonical Inbound Exception}$$
$$\Downarrow$$
$$\text{Dynamic Evidence Acquisition (Modes 1, 2, 3, 4)}$$
$$\Downarrow$$
$$\text{Evidence Sufficiency Evaluation } (E_{\text{suff}})$$
$$\Downarrow$$
$$\text{Domain Capability Engine(s) Execution}$$
$$\Downarrow$$
$$\text{Resolution Candidate Generation (Proposed Value / Action)}$$
$$\Downarrow$$
$$\mathbf{Resolution\ Orchestration\ /\ Resolution\ Contract\ (Composition\ \&\ Uniqueness)}$$
$$\Downarrow$$
$$\text{Deterministic Resolution Derivation } (R_{\text{det}} \land R_{\text{uniq}})$$
$$\Downarrow$$
$$\text{Authority Validation } (V_{\text{det}} \land V_{\text{auth}})$$
$$\Downarrow$$
$$\text{Bank Policy \& Compliance Gates } (P_{\text{bank}} \land C_{\text{comp}})$$
$$\Downarrow$$
$$\text{Preconditions \& Idempotency Lock } (X_{\text{pre}})$$
$$\Downarrow$$
$$\mathbf{8\text{-}Predicate\ STP\ Evaluation\ Conjunction}$$
$$\Downarrow$$
$$\begin{cases} \mathbf{STP\_ELIGIBLE = TRUE} & \longrightarrow \mathbf{BANK\_HANDOFF\_READY} \text{ (Zero-Touch Autonomous Handoff)} \\ \mathbf{STP\_ELIGIBLE = FALSE} & \longrightarrow \mathbf{PE\_X\ NATIVE\ HITL\ WORKSPACE} \text{ (Maker-Checker / Adjudication)} \end{cases}$$

---

======================================================================
6. REUSABLE CAPABILITY ENGINE INVENTORY
======================================================================

Six primary reusable domain capability engines are currently identified for the industrialization of the 30 remaining profiles:

```mermaid
flowchart TD
    subgraph Runtime["Wave 0B Platform Runtime Infrastructure"]
        ConfigResolver[DynamicEvidenceConfigResolver]
        GovCompiler[GovernanceCompiler]
        ExprEngine[ConditionalExpressionEngine]
        EvStore[EvidenceStoreService]
        AcqGateway[AcquisitionGateway]
        HitlService[HITLWorkflowService]
    end

    subgraph DomainEngines["Six Primary Domain Capability Engines (Identified)"]
        E1[1. AccountMasterEngine]
        E2[2. RoutingClearingEngine]
        E3[3. RemittanceDocumentEngine]
        E4[4. ComplianceDossierEngine]
        E5[5. TreasuryExposureEngine]
        E6[6. SettlementReconciliationEngine]
    end

    subgraph ResContract["Governing Resolution Layer"]
        Orchestration[Resolution Orchestration / Resolution Contract Layer]
    end

    subgraph Evaluation["Final 8-Predicate Eligibility Gate"]
        Formula["8-Predicate Evaluation (E_suff ∧ R_det ∧ R_uniq ∧ V_det ∧ V_auth ∧ P_bank ∧ C_comp ∧ X_pre)"]
    end

    Runtime --> DomainEngines
    DomainEngines -->|Generate Candidates| Orchestration
    Orchestration -->|Derives R_det & R_uniq| Formula
```

### 6.1 Engine 1: `AccountMasterEngine`
- **Purpose**: Unified account validation, status inquiry, modulo-97 calculation, Confirmation of Payee (VoP) matching, and account restriction handling.
- **Phase 3 Profiles Implemented**: `DQ-03`, `DQ-07`, `DQ-09`, `ST-02`, `ST-03`, `TR-01`.
- **Phase 2 Profiles Supported / Consumed**: `DQ-01`, `DQ-02`, `DQ-05`.
- **Primary Inputs**: Account Number (IBAN/BBAN/Transit), Creditor Name, Currency, Branch BIC.
- **Evidence Dependencies**: `CORE_DDA_ACCOUNT` (Tier 1), `NATIONAL_DIRECTORY` (Tier 2).
- **Authority Dependencies**: Core Banking DDA Port / Confirmation of Payee Directory.
- **Deterministic Logic**: ISO 7064 Modulo 97-10 solver, national check digit algorithms, exact/fuzzy string distance scoring.
- **AI Role (Advisory Only)**: Entity alias extraction and trading name mapping. Zero authority.
- **HITL Role**: Disambiguation cockpit when multiple valid accounts match or name distance score is ambiguous.
- **Belongs in**: Core PeX Domain Service (`backend/app/services/engines/account_master_engine.py`).

### 6.2 Engine 2: `RoutingClearingEngine`
- **Purpose**: Clearing rail selection, correspondent routing transit hop derivation, cutoff schedule management, and network retry coordination.
- **Phase 3 Profiles Implemented**: `PR-02`, `PR-04`, `PR-07`, `PR-09`.
- **Phase 2 Profiles Supported / Consumed**: `DQ-08`, `PR-03`, `PR-08`.
- **Primary Inputs**: Debtor BIC, Creditor BIC, Currency, Amount, Rail Code, Timestamp.
- **Evidence Dependencies**: `SWIFTREF_DIRECTORY` (Tier 2), `RAIL_SCHEDULE_MASTER` (Tier 1), `IDEMPOTENCY_LOCK` (Tier 1).
- **Authority Dependencies**: Clearing Rail Port / SWIFTRef Adapter / Gateway Socket Probe.
- **Deterministic Logic**: Routing graph shortest-path traversal, cutoff calendar calculation, value-date roll forward ($T+1$), idempotent retry dispatch.
- **AI Role**: None.
- **HITL Role**: Manual routing override when all correspondent paths are blocked.
- **Belongs in**: Core PeX Domain Service (`backend/app/services/engines/routing_clearing_engine.py`).

### 6.3 Engine 3: `RemittanceDocumentEngine`
- **Purpose**: Ingestion, unbundling, parsing, and semantic extraction of structured and unstructured remittance data, invoices, and EDI payloads.
- **Phase 3 Profiles Implemented**: `DQ-03`, `DQ-04`, `CO-07`.
- **Phase 2 Profiles Supported / Consumed**: None (New Phase 3 Capability).
- **Primary Inputs**: Unstructured remittance text, PDF/OCR invoice payloads, EDI 820 documents.
- **Evidence Dependencies**: `ERP_INVOICE_PAYLOAD` (Tier 3), `PURPOSE_CODE_DIRECTORY` (Tier 2).
- **Authority Dependencies**: Client ERP Port / Central Bank Regulatory Directory.
- **Deterministic Logic**: Regular expression pattern matching for PO/Invoice numbers, ISO 20022 XML structured tag serialization (`RmtInf/Strd`).
- **AI Role (Advisory Only)**: Probabilistic NLP extraction of invoice attributes from freeform unstructured narratives.
- **HITL Role**: Operator confirmation when extracted remittance confidence is below threshold.
- **Belongs in**: Core PeX Domain Service (`backend/app/services/engines/remittance_document_engine.py`).

### 6.4 Engine 4: `ComplianceDossierEngine`
- **Purpose**: Aggregation of screening hits, entity disambiguation dossiers, statutory corridor matrix validation, and compliance officer adjudication packaging.
- **Phase 3 Profiles Implemented**: `CO-01`, `CO-02`, `CO-03`, `CO-05`, `CO-06`, `CO-07`, `CO-08`.
- **Phase 2 Profiles Supported / Consumed**: `CO-04`, `DQ-06`.
- **Primary Inputs**: Debtor/Creditor Names, Country Codes, Corridor, DOB, LEI, Watchlist Hits.
- **Evidence Dependencies**: `SANCTIONS_WATCHLIST` (Tier 2), `PEP_DATABASE` (Tier 2), `ADVERSE_MEDIA` (Tier 3), `CLIENT_KYC` (Tier 1).
- **Authority Dependencies**: Compliance Screening Port / Watchlist System of Record.
- **Deterministic Logic**: 32-year entity disambiguation matching (Exact Name + DOB + Country), statutory embargo checks.
- **AI Role (Advisory Only)**: Collate adverse media summaries, cluster entity aliases, rank false positive likelihood.
- **HITL Role**: Compliance Officer Dual-Authorization Desk for hold releases and statutory block executions.
- **Belongs in**: Core PeX Domain Service (`backend/app/services/engines/compliance_dossier_engine.py`).

### 6.5 Engine 5: `TreasuryExposureEngine`
- **Purpose**: Balance inquiry, liquidity reservation, Nostro monitoring, FX rate booking, limit enforcement, and credit exposure tracking.
- **Phase 3 Profiles Implemented**: `TR-02`, `TR-03`, `TR-04`, `TR-05`, `TR-06`, `TR-07`, `TR-08`.
- **Phase 2 Profiles Supported / Consumed**: None (New Phase 3 Capability).
- **Primary Inputs**: Account Number, Amount, Currency, Debtor Limit, Nostro Identifier, FX Pair.
- **Evidence Dependencies**: `CORE_DDA_BALANCE` (Tier 1), `NOSTRO_LEDGER` (Tier 1), `FX_RATE_MATRIX` (Tier 1), `CREDIT_LIMIT` (Tier 1).
- **Authority Dependencies**: Core Banking DDA Port / Treasury Management Port / Market Data Adapter.
- **Deterministic Logic**: Balance reservation calculation, FX spread calculation, cumulative limit aggregation, liquidity cap pacing.
- **AI Role (Advisory Only)**: Intraday liquidity cash flow forecasting.
- **HITL Role**: Credit Officer / Corporate Client Portal sign-off for limit uplifts and mandate clearances.
- **Belongs in**: Core PeX Domain Service (`backend/app/services/engines/treasury_exposure_engine.py`).

### 6.6 Engine 6: `SettlementReconciliationEngine`
- **Purpose**: Daily clearing statement reconciliation, inward return matching, debtor re-credit generation, trapped fund tracking, and unmatched credit resolution.
- **Phase 3 Profiles Implemented**: `PR-06`, `ST-02`, `ST-03`, `ST-04`, `ST-05`, `ST-06`, `ST-07`.
- **Phase 2 Profiles Supported / Consumed**: `PR-01`, `ST-01`.
- **Primary Inputs**: Inward `pacs.004` / `pacs.002`, `camt.053` statement, Original Debit UETR, Settlement Journal.
- **Evidence Dependencies**: `INWARD_RETURN` (Tier 1), `ORIGINAL_DEBIT` (Tier 1), `CAMT053_STATEMENT` (Tier 1), `GPI_TRACKER` (Tier 2).
- **Authority Dependencies**: Settlement Ledger Port / SWIFT GPI Tracker Port / Accounting Port.
- **Deterministic Logic**: Exact 4-point matching (UETR + Amount + Currency + Value Date), ledger re-credit instruction creation, `camt.027` Claim for Non-Receipt generation.
- **AI Role (Advisory Only)**: Many-to-one batch break matching suggestions.
- **HITL Role**: Operations investigation worklist for orphan breaks and unmatchable credits.
- **Belongs in**: Core PeX Domain Service (`backend/app/services/engines/settlement_reconciliation_engine.py`).

---

======================================================================
7. RESOLUTION PATTERN INVENTORY
======================================================================

All 30 remaining profiles map into **7 canonical resolution patterns**:

```
+---------------------------------------------------------------------------------------------------+
|                                  CANONICAL RESOLUTION PATTERNS                                    |
+---------+-----------------------------------+--------------------+--------------------------------+
| Pattern | Pattern Name                      | Primary Logic      | Associated Profiles            |
+---------+-----------------------------------+--------------------+--------------------------------+
| PAT-A   | Directory / Master Lookup &       | Deterministic SoR  | DQ-03, DQ-07, PR-02, CO-07     |
|         | Substitution                      | lookup & checksum  |                                |
+---------+-----------------------------------+--------------------+--------------------------------+
| PAT-B   | Schedule / Value Date / Queue     | Operating calendar | PR-04, PR-07, PR-09            |
|         | Recalculation                     | roll & retry lock  |                                |
+---------+-----------------------------------+--------------------+--------------------------------+
| PAT-C   | Threshold / Balance Reservation   | Account balance /  | TR-02, TR-03, TR-04, TR-07     |
|         | & Pacing Retry                    | rate availability  |                                |
+---------+-----------------------------------+--------------------+--------------------------------+
| PAT-D   | Compliance Dossier Assembly &     | Entity match &     | CO-01, CO-02, CO-03, CO-05,    |
|         | Officer Adjudication              | statutory review   | CO-06, CO-08                   |
+---------+-----------------------------------+--------------------+--------------------------------+
| PAT-E   | Return Matching & Debtor          | 4-point matching & | ST-02, ST-03, ST-04, ST-05,    |
|         | Re-Credit Ledger Reversal         | accounting package | ST-07                          |
+---------+-----------------------------------+--------------------+--------------------------------+
| PAT-F   | Correspondent Inquiry & Claims    | SWIFT GPI status & | PR-06, ST-06                   |
|         | Tracking Dispatch                 | camt.027 claim     |                                |
+---------+-----------------------------------+--------------------+--------------------------------+
| PAT-G   | Client Mandate & Signatory        | Mandate evaluation | DQ-09, TR-01, TR-05, TR-06,    |
|         | Dual-Authorization Clearance      | & Mode 4 portal    | TR-08                          |
+---------+-----------------------------------+--------------------+--------------------------------+
```

---

======================================================================
8. PROFILE-TO-CAPABILITY MATRIX (30 REMAINING PROFILES)
======================================================================

> **CRITICAL GOVERNANCE NOTE ON AUTOMATION POTENTIAL:**  
> **Automation Potential is an architectural classification of algorithmic feasibility, NOT runtime STP authorization.** A profile classified with High Automation Potential may still fail one or more of the 8 predicates at runtime. Runtime STP eligibility is determined exclusively by the 8-predicate formula.

| Profile | Domain | Canonical Profile Name | Primary Engine | Resolution Pattern | Required Evidence | Authority Source | Automation Potential | Wave | Open Decisions / Risks |
|---|---|---|---|---|---|---|---|---|---|
| **DQ-03** | Data Quality | Missing Beneficiary Data | `AccountMasterEngine` | PAT-A | `CLIENT_MASTER_RECORD` (T1) | Core Banking / GLEIF | **HIGH** | **Wave 1** | Client directory match policy |
| **DQ-04** | Data Quality | Missing Remittance Info | `RemittanceDocumentEngine` | PAT-A | `ERP_INVOICE_PAYLOAD` (T3) | Client ERP / EDI | **HIGH** | **Wave 1** | OCR / EDI format mapping |
| **DQ-07** | Data Quality | Invalid Account Number | `AccountMasterEngine` | PAT-A | `CORE_DDA_ACCOUNT` (T1) | Core DDA Master | **HIGH** | **Wave 1** | Modulo table configuration |
| **DQ-09** | Data Quality | Beneficiary Name Mismatch | `AccountMasterEngine` | PAT-G | `CORE_DDA_ACCOUNT_TITLE` (T1)| CoP / VoP Scheme | **MEDIUM** | **Wave 1** | Bank Decision: VoP fuzzy thresholds |
| **PR-02** | Processing | Routing Failure | `RoutingClearingEngine` | PAT-A | `SWIFTREF_DIRECTORY` (T2) | SWIFTRef / SSI Master | **HIGH** | **Wave 1** | Fallback correspondent hierarchy |
| **PR-04** | Processing | Cutoff Missed | `RoutingClearingEngine` | PAT-B | `RAIL_SCHEDULE_MASTER` (T1)| Central Bank Cutoff | **HIGH** | **Wave 1** | Bank Decision: Cutoff buffer window |
| **PR-06** | Processing | Intermediary Bank Rejection | `SettlementReconciliationEngine`| PAT-F | `INWARD_PACS002_REJECTION` (T1)| Inward SWIFT / Portal | **MEDIUM** | **Wave 2** | Intermediary reason code mapping |
| **PR-07** | Processing | Network Timeout | `RoutingClearingEngine` | PAT-B | `GATEWAY_SOCKET_LOG` (T1) | Gateway Socket Probe | **HIGH** | **Wave 1** | Socket timeout threshold |
| **PR-09** | Processing | Payment Held for Repair | `RoutingClearingEngine` | PAT-B | `PARSER_SYNTAX_ERROR_LOG` (T1)| Canonical Schema XSD | **HIGH** | **Wave 1** | Canonical XSD versioning |
| **CO-01** | Compliance | Sanctions Screening Hit | `ComplianceDossierEngine` | PAT-D | `SANCTIONS_SCREENING_ALERT` (T2)| OFAC / National Feeds | **0% (HITL)** | **Wave 5** | Regulatory: Officer dual-auth |
| **CO-02** | Compliance | AML Alert | `ComplianceDossierEngine` | PAT-D | `AML_ALERT_DOSSIER` (T1) | Bank AML Monitoring | **0% (HITL)** | **Wave 5** | Regulatory: Mandatory human review |
| **CO-03** | Compliance | PEP Match | `ComplianceDossierEngine` | PAT-D | `PEP_SCREENING_ALERT` (T2) | World-Check / DowJones | **0% (HITL)** | **Wave 5** | Regulatory: EDD sign-off |
| **CO-05** | Compliance | Adverse Media Match | `ComplianceDossierEngine` | PAT-D | `ADVERSE_MEDIA_ALERT` (T3) | Adverse Media Feed | **0% (HITL)** | **Wave 5** | Bank Decision: Media risk threshold |
| **CO-06** | Compliance | High-Risk Jurisdiction | `ComplianceDossierEngine` | PAT-D | `FATF_JURISDICTION_MATRIX` (T2)| FATF List / Treasury | **CONDITIONAL** | **Wave 5** | General license exemption policy |
| **CO-07** | Compliance | Regulatory Reporting Required | `RemittanceDocumentEngine` | PAT-A | `PURPOSE_CODE_DIRECTORY` (T2)| Central Bank Directives | **HIGH** | **Wave 1** | Regulatory purpose code mapping |
| **CO-08** | Compliance | Customer Watchlist Match | `ComplianceDossierEngine` | PAT-D | `INTERNAL_WATCHLIST_RECORD` (T1)| Internal Fraud Database | **0% (HITL)** | **Wave 5** | Bank Decision: Fraud escalation rules |
| **TR-01** | Client/Treasury | KYC Expired | `AccountMasterEngine` | PAT-G | `CUSTOMER_KYC_RECORD` (T1) | Bank Customer Master | **LOW** | **Wave 4** | Bank Decision: KYC grace period policy |
| **TR-02** | Client/Treasury | Insufficient Funds | `TreasuryExposureEngine` | PAT-C | `CORE_DDA_BALANCE_RECORD` (T1)| Core DDA / Credit Line | **HIGH** | **Wave 3** | Balance inquiry SLA & freshness |
| **TR-03** | Client/Treasury | Nostro Shortfall | `TreasuryExposureEngine` | PAT-C | `NOSTRO_ACCOUNT_LEDGER` (T1) | Treasury TMS / Nostro | **HIGH** | **Wave 3** | Nostro sweep feed integration |
| **TR-04** | Client/Treasury | FX Rate Unavailable | `TreasuryExposureEngine` | PAT-C | `TREASURY_FX_RATE_MATRIX` (T1)| Bank FX Engine | **HIGH** | **Wave 3** | FX spread & slippage tolerance |
| **TR-05** | Client/Treasury | Authorization Missing | `AccountMasterEngine` | PAT-G | `SIGNATORY_MANDATE_MATRIX` (T1)| Mandates Master / Portal | **0% (HITL)** | **Wave 4** | Corporate portal outreach protocol |
| **TR-06** | Client/Treasury | Limit Breach | `TreasuryExposureEngine` | PAT-G | `CLIENT_LIMIT_RECORD` (T1) | Bank Limit Engine | **LOW** | **Wave 3** | Credit risk waiver rules |
| **TR-07** | Client/Treasury | Liquidity Constraint | `TreasuryExposureEngine` | PAT-C | `CENTRAL_BANK_RESERVES` (T1) | RTGS Reserve Account | **HIGH** | **Wave 3** | RTGS liquidity pacing algorithm |
| **TR-08** | Client/Treasury | Credit Exposure Breach | `TreasuryExposureEngine` | PAT-G | `COUNTERPARTY_LIMIT_RECORD` (T1)| Credit Risk System | **0% (HITL)** | **Wave 3** | Credit Risk Maker-Checker |
| **ST-02** | Settlement/Ret | Account Closed | `SettlementReconciliationEngine`| PAT-E | `INWARD_PACS004_RETURN` (T1) | Inward Clearing Return | **HIGH** | **Wave 2** | Return matching tolerance |
| **ST-03** | Settlement/Ret | Beneficiary Account Frozen | `SettlementReconciliationEngine`| PAT-E | `INWARD_RETURN_NOTICE` (T1) | Clearing Return / Legal | **CONDITIONAL** | **Wave 2** | Legal attachment policy |
| **ST-04** | Settlement/Ret | Reconciliation Break | `SettlementReconciliationEngine`| PAT-E | `DAILY_CAMT053_STATEMENT` (T1)| RTGS Clearing Statement | **MEDIUM** | **Wave 2** | End-of-day statement feed timing |
| **ST-05** | Settlement/Ret | Settlement Failure | `SettlementReconciliationEngine`| PAT-E | `SETTLEMENT_REJECTION_LOG` (T1)| ACH / RTGS Operator | **HIGH** | **Wave 2** | Multilateral netting reset rules |
| **ST-06** | Settlement/Ret | Funds Trapped at Correspondent | `SettlementReconciliationEngine`| PAT-F | `SWIFT_GPI_TRACKER_RECORD` (T2)| SWIFT GPI Tracker | **HIGH** | **Wave 4** | SWIFT GPI inquiry SLA window |
| **ST-07** | Settlement/Ret | Unmatched Credit | `SettlementReconciliationEngine`| PAT-E | `INWARD_SETTLEMENT_CREDIT` (T1)| Inward Clearing Gateway | **MEDIUM** | **Wave 2** | Unclaimed credit hold duration |

---

======================================================================
9. EVIDENCE & AUTHORITY ARCHITECTURE
======================================================================

### 9.1 Single Published Bank Evidence Model
Evidence requirements are configured through single, published Bank Evidence Required JSON documents per `(tenant_id, profile_id)`.
- **Evidence Required JSON**: Configuration data defining effective evidence requirements, trust tier floors, acquisition modes, and conditional rules.
- **Evidence Contract**: The binding architectural contract defining formal states, trust/authority interpretation, provenance, cryptographic hashing, and contribution to $E_{\text{suff}}$.
- **Core Invariant**: $E_{\text{suff}} \ne \text{STP\_ELIGIBLE}$. Evidence sufficiency is an isolated prerequisite.

### 9.2 Evidence Trust Hierarchy & Freshness Guidelines
*(Note: Freshness values below are illustrative starting guidelines; final freshness is profile-, bank-, source-, and policy-dependent).*

```
+---------------------------------------------------------------------------------------------------+
|                                 EVIDENCE TRUST TIER ALLOCATION                                    |
+------+-----------------------+----------------------------------+---------------------------------+
| Tier | Classification        | Authoritative Evidence Types     | Illustrative Freshness TTL      |
+------+-----------------------+----------------------------------+---------------------------------+
| 1    | Bank Core Authoritative| CORE_DDA_ACCOUNT, BALANCE_RECORD,| 12 to 24 Hours                  |
|      |                       | NOSTRO_LEDGER, ORIGINAL_DEBIT    | (Real-time for balances)        |
+------+-----------------------+----------------------------------+---------------------------------+
| 2    | National / Directory  | SWIFTRef, FedLine, VoP Directory,| 24 to 72 Hours                  |
|      | Authoritative         | OFAC SDN, Central Bank Schedules | (Daily delta update)            |
+------+-----------------------+----------------------------------+---------------------------------+
| 3    | Client ERP / Document | ERP_INVOICE, REMITTANCE_ADVICE,  | 7 Days                          |
|      |                       | ADVERSE_MEDIA_ALERT              | (Per-case snapshot)             |
+------+-----------------------+----------------------------------+---------------------------------+
| 4    | AI / Historical       | HISTORICAL_REPAIR_PRECEDENT,     | Advisory Context Only           |
|      | Precedent             | STATISTICAL_SIMILARITY           | (0% Authority Gate Weight)      |
+------+-----------------------+----------------------------------+---------------------------------+
```

---

======================================================================
10. BANK POLICY VS. ARCHITECTURE DECISIONS
======================================================================

PeX strictly maintains the boundary between platform architecture decisions and bank-configurable policy decisions:

```
+---------------------------------------------------------------------------------------------------+
|                               ARCHITECTURE VS BANK POLICY BOUNDARY                                 |
+--------------------------------------------------+------------------------------------------------+
| ARCHITECTURE DECISIONS (Immutable in Platform)   | BANK-SPECIFIC POLICY DECISIONS (Configurable)  |
+--------------------------------------------------+------------------------------------------------+
| 1. 41-Profile Canonical Taxonomy                 | 1. Autonomous STP Currency & Amount Limits     |
| 2. 8-Predicate Conjunction Formula               | 2. Confirmation of Payee (VoP) Fuzzy Thresholds|
| 3. Provider-Neutral Hexagonal Ports & Adapters   | 3. Mandatory Maker-Checker Approval Roles      |
| 4. Content-Addressable SHA-256 Evidence Store    | 4. Maximum Evidence Freshness TTL Parameters   |
| 5. Terminal State BANK_HANDOFF_READY             | 5. Permitted Correspondent Routing Hierarchies |
| 6. Execution Ownership Permanently "BANK"        | 6. Real-time Balance Inquiry SLA Tolerances    |
| 7. AI 0% Autonomous Release Authority Bound     | 7. Specific Statutory Sanctions Hold Rules     |
| 8. Sandboxed Deterministic Expression Engine     | 8. Custom Operational Worklist Escalations     |
+--------------------------------------------------+------------------------------------------------+
```

---

======================================================================
11. VENDOR & PRODUCT REFERENCES DISCLAIMER
======================================================================

> **PROVIDER NEUTRALITY STATEMENT:**  
> **All named products, vendors, core banking platforms, screening engines, cloud providers, and ledger systems referenced throughout this document (including Finacle, Temenos, SAP Banking, SWIFTRef, FedLine, Actimize, Fircosoft, World-Check, Murex, Calypso, Wallstreet, AWS KMS, HashiCorp Vault, and QLDB) are illustrative examples only and do not constitute architecture commitments or mandatory dependencies.**  
>  
> PeX is 100% provider-neutral, cloud-neutral, and model-neutral. All integrations are defined as abstract Python SPIs in `backend/app/ports/` with zero vendor SDK lock-in in domain, port, or core service packages.

---

======================================================================
12. WAVE 1–6 RECOMMENDED INDUSTRIALIZATION ROADMAP
======================================================================

```mermaid
flowchart LR
    W1["Wave 1: Data Quality & Routing (9 Profiles)"] --> W2["Wave 2: Intermediary & Settlement (6 Profiles)"]
    W1 --> W3["Wave 3: Treasury & Liquidity (6 Profiles)"]
    W2 & W3 --> W4["Wave 4: Entitlements & KYC (3 Profiles)"]
    W4 --> W5["Wave 5: Financial Crime & Compliance (6 Profiles)"]
    W5 --> W6["Wave 6: 41-Profile Convergence & Production Hardening"]
```

### 12.1 Wave 1: Data Quality & Routing Foundation (9 Profiles)
- **Target Profiles**: `DQ-03`, `DQ-04`, `DQ-07`, `DQ-09`, `PR-02`, `PR-04`, `PR-07`, `PR-09`, `CO-07`.
- **Capability Engines Introduced**: `AccountMasterEngine`, `RoutingClearingEngine`, `RemittanceDocumentEngine`.
- **Rationale**: Highest volume, highest automation potential, lowest regulatory risk. Establishes the core master data and routing infrastructure used by all downstream waves.
- **Implementation Sequencing**:
  - *Parallel Group A*: `DQ-07` (Invalid Account Number), `DQ-03` (Missing Beneficiary Data), `DQ-09` (Beneficiary Name Mismatch) via `AccountMasterEngine`.
  - *Parallel Group B*: `PR-04` (Cutoff Missed), `PR-07` (Network Timeout), `PR-09` (Payment Held for Repair), `PR-02` (Routing Failure) via `RoutingClearingEngine`.
  - *Sequence Group C*: `DQ-04` (Missing Remittance Info) and `CO-07` (Regulatory Reporting Required) via `RemittanceDocumentEngine`.

### 12.2 Wave 2: Intermediary Banking & Settlement Reconciliation (6 Profiles)
- **Target Profiles**: `PR-06`, `ST-02`, `ST-03`, `ST-04`, `ST-05`, `ST-07`.
- **Capability Engines Introduced**: `SettlementReconciliationEngine`.

### 12.3 Wave 3: Treasury, Liquidity & Balance Management (6 Profiles)
- **Target Profiles**: `TR-02`, `TR-03`, `TR-04`, `TR-06`, `TR-07`, `TR-08`.
- **Capability Engines Introduced**: `TreasuryExposureEngine`.

### 12.4 Wave 4: Client Entitlements, KYC & Signatory Mandates (3 Profiles)
- **Target Profiles**: `TR-01`, `TR-05`, `ST-06`.
- **Capability Engines Introduced**: Signatory Mandate Engine, Correspondent Claim Tracker (`camt.027`).

### 12.5 Wave 5: Financial Crime & Compliance Screening Industrialization (6 Profiles)
- **Target Profiles**: `CO-01`, `CO-02`, `CO-03`, `CO-05`, `CO-06`, `CO-08`.
- **Capability Engines Introduced**: `ComplianceDossierEngine`.

### 12.6 Wave 6: Global 41-Profile Convergence & Enterprise Hardening
- **Scope**: Cross-domain regression validation across all 41 profiles, high-throughput multi-tenant stress testing, and deployment hardening.

---

======================================================================
13. WAVE 1 DEFINITION OF DONE — ARCHITECTURE GATE
======================================================================

Before a future Wave 1 implementation can be accepted, all of the following criteria must be completely satisfied:

### A. Architecture
- [ ] Profile contract definitions approved for all 9 Wave 1 profiles under canonical names.
- [ ] Evidence contracts and trust tier bindings approved.
- [ ] Authority sources identified and mapped to abstract ports.
- [ ] Resolution patterns confirmed (`PAT-A`, `PAT-B`, `PAT-G`).
- [ ] Capability engine ownership confirmed (`AccountMasterEngine`, `RoutingClearingEngine`, `RemittanceDocumentEngine`).

### B. Configuration
- [ ] Single published Bank Evidence Required JSON models defined for all 9 profiles.
- [ ] Bank customization parameters and conditional expressions tested.
- [ ] Fail-closed validation rules enforced via `GovernanceCompiler`.

### C. Implementation
- [ ] 3 capability engines implemented in `backend/app/services/engines/`.
- [ ] Provider-neutral AST checks pass with 0 forbidden vendor SDK imports.
- [ ] Phase 2 protected profiles remain 100% untouched.

### D. Testing
- [ ] Unit tests, contract tests, negative tests, and adversarial tests implemented.
- [ ] Evidence insufficiency and authority contradiction tests passing.
- [ ] E2E dynamic JSON execution validated for all 9 profiles.
- [ ] 100% green pass rate across cumulative regression suite ($\ge 550$ tests).
- [ ] Exact 8-predicate formula evaluated without alteration.

### E. Forensic
- [ ] Independent forensic review conducted and approved.
- [ ] Semantic boundary review confirms zero profile overlap or responsibility theft.
- [ ] 41-profile taxonomy integrity confirmed.

### F. Governance
- [ ] Zero unresolved P0/P1/P2 architecture findings.
- [ ] Formal Wave 1 engineering completion report published.
- [ ] Explicit human governance sign-off achieved.

### G. Runtime Safety
- [ ] Zero direct payment execution in PeX.
- [ ] `BANK_HANDOFF_READY` remains terminal state with `execution_owner = "BANK"`.
- [ ] Maker-Checker controls preserved.
- [ ] Production autonomous STP remains separately blocked.

---

======================================================================
14. RISKS & OPEN DECISIONS CLASSIFICATION
======================================================================

```
+---------------------------------------------------------------------------------------------------+
|                                  RISKS & OPEN DECISIONS MATRIX                                    |
+-------------------------------------+---------------------------------+---------------------------+
| Item Description                    | Classification                  | Resolution Pathway        |
+-------------------------------------+---------------------------------+---------------------------+
| Confirmation of Payee (VoP) string  | Bank Policy / Configuration     | Bank-specific risk policy |
| distance threshold for DQ-09        | Decision                        | sign-off in published JSON|
+-------------------------------------+---------------------------------+---------------------------+
| Real-time Core DDA balance inquiry  | Production Integration          | Core Banking connector    |
| latency and caching SLA for TR-02   | Dependency                      | SLA agreement             |
+-------------------------------------+---------------------------------+---------------------------+
| Corporate Client Mandate Portal     | Production Integration          | Client portal webhook /   |
| outreach authentication for TR-05   | Dependency                      | SSO standard definition   |
+-------------------------------------+---------------------------------+---------------------------+
| SWIFT GPI Tracker API connectivity | External Source Dependency      | SWIFT GPI Alliance Cloud  |
| and SLA for ST-06                   |                                 | port adapter              |
+-------------------------------------+---------------------------------+---------------------------+
| Statutory AML Hold mandates         | Architecture Risk / Compliance  | Enforced as immutable     |
| prohibiting autonomous STP          | Baseline                        | fail-closed gate (C_comp) |
+-------------------------------------+---------------------------------+---------------------------+
| End-of-day camt.053 settlement feed | Performance / SLA Risk          | Asynchronous batch        |
| delivery timing for ST-04           |                                 | reconciliation buffer     |
+-------------------------------------+---------------------------------+---------------------------+
```

---

======================================================================
15. 41-PROFILE SEMANTIC RECONCILIATION TABLE (MANDATORY TABLE 1)
======================================================================

The following table provides the comprehensive forensic semantic reconciliation for all 41 canonical exception profiles across the platform, verifying canonical taxonomy alignment, engine assignments, resolution patterns, and status:

| Profile ID | Canonical Profile Name | Delivery Phase | Current Engine Assignment | Resolution Pattern | Semantic Status | Reconciliation Notes / Former Alias Remediation |
|---|---|---|---|---|---|---|
| **DQ-01** | Invalid IBAN | Phase 2 Baseline | `AccountMasterEngine` (Consumed) | PAT-A | **PASS** | Formerly aliased as "Invalid IBAN Checksum"; canonical name restored. |
| **DQ-02** | Invalid BIC / SWIFT | Phase 2 Baseline | `AccountMasterEngine` (Consumed) | PAT-A | **PASS** | Formerly aliased as "Invalid BIC Routing"; canonical name restored. |
| **DQ-03** | Missing Beneficiary Data | Phase 3 (Wave 1) | `AccountMasterEngine` / `RemittanceDocumentEngine` | PAT-A | **PASS** | Aligned to master record and ERP payload resolution. |
| **DQ-04** | Missing Remittance Info | Phase 3 (Wave 1) | `RemittanceDocumentEngine` | PAT-A | **PASS** | Ingests structured/unstructured invoice data. |
| **DQ-05** | Invalid Address Format | Phase 2 Baseline | `AccountMasterEngine` (Consumed) | PAT-A | **PASS** | Formerly aliased as "Missing Beneficiary Address"; canonical name restored. |
| **DQ-06** | Missing Purpose Code | Phase 2 Baseline | `ComplianceDossierEngine` (Consumed) | PAT-A | **PASS** | Formerly aliased as "Cross-Border Missing Purpose / Regulatory Code"; canonical name restored. |
| **DQ-07** | Invalid Account Number | Phase 3 (Wave 1) | `AccountMasterEngine` | PAT-A | **PASS** | Modulo validation and national account rules. |
| **DQ-08** | Invalid Routing Code | Phase 2 Baseline | `RoutingClearingEngine` (Consumed) | PAT-A | **PASS** | Formerly aliased as "Routing Code / Transit Discrepancy"; canonical name restored. |
| **DQ-09** | Beneficiary Name Mismatch | Phase 3 (Wave 1) | `AccountMasterEngine` | PAT-G | **PASS** | Confirmation of Payee / VoP verification. |
| **PR-01** | Duplicate Payment | Phase 2 Baseline | `SettlementReconciliationEngine` (Consumed) | PAT-E | **PASS** | Formerly aliased as "Duplicate Payment Detection & Suppression"; canonical name restored. |
| **PR-02** | Routing Failure | Phase 3 (Wave 1) | `RoutingClearingEngine` | PAT-A | **PASS** | Clearing rail and correspondent hop substitution. |
| **PR-03** | ISO 20022 Validation Error | Phase 2 Baseline | `RoutingClearingEngine` (Consumed) | PAT-B | **PASS** | Corrected from erroneous alias "Value Date Past Cutoff / Rollover". Value date/cutoff belongs strictly to PR-04. |
| **PR-04** | Cutoff Missed | Phase 3 (Wave 1) | `RoutingClearingEngine` | PAT-B | **PASS** | Value-date roll forward and schedule recalculation. |
| **PR-05** | Corrupted Message Format | Phase 2 Baseline | `RemittanceDocumentEngine` (Consumed) | PAT-A | **PASS** | Corrected from implementation alias "Amount Formatting / Decimals". Governed character transformation restored. |
| **PR-06** | Intermediary Bank Rejection | Phase 3 (Wave 2) | `SettlementReconciliationEngine` | PAT-F | **PASS** | Inward pacs.002 rejection parsing and alternate routing. |
| **PR-07** | Network Timeout | Phase 3 (Wave 1) | `RoutingClearingEngine` | PAT-B | **PASS** | Socket probe verification and idempotent unblock. |
| **PR-08** | Queue Processing Failure | Phase 2 Baseline | `RoutingClearingEngine` (Consumed) | PAT-B | **PASS** | Formerly aliased as "Queue Processing Failure / Deadlock Recovery"; canonical name restored. |
| **PR-09** | Payment Held for Repair | Phase 3 (Wave 1) | `RoutingClearingEngine` | PAT-B | **PASS** | Canonical syntax error unblocking. |
| **CO-01** | Sanctions Screening Hit | Phase 3 (Wave 5) | `ComplianceDossierEngine` | PAT-D | **PASS** | OFAC / statutory watchlist dossier adjudication. |
| **CO-02** | AML Alert | Phase 3 (Wave 5) | `ComplianceDossierEngine` | PAT-D | **PASS** | Transaction monitoring alert dossier aggregation. |
| **CO-03** | PEP Match | Phase 3 (Wave 5) | `ComplianceDossierEngine` | PAT-D | **PASS** | Politically exposed person enhanced due diligence. |
| **CO-04** | Restricted Corridor | Phase 2 Baseline | `ComplianceDossierEngine` (Consumed) | PAT-D | **PASS** | Formerly aliased as "Restricted Corridor / Sanctions False Positive Disambiguation"; canonical name restored. |
| **CO-05** | Adverse Media Match | Phase 3 (Wave 5) | `ComplianceDossierEngine` | PAT-D | **PASS** | Negative news feed clustering and officer pack. |
| **CO-06** | High-Risk Jurisdiction | Phase 3 (Wave 5) | `ComplianceDossierEngine` | PAT-D | **PASS** | FATF country risk matrix verification. |
| **CO-07** | Regulatory Reporting Required | Phase 3 (Wave 1) | `RemittanceDocumentEngine` | PAT-A | **PASS** | Central bank regulatory purpose tag derivation. |
| **CO-08** | Customer Watchlist Match | Phase 3 (Wave 5) | `ComplianceDossierEngine` | PAT-D | **PASS** | Internal fraud and security watchlist check. |
| **TR-01** | KYC Expired | Phase 3 (Wave 4) | `AccountMasterEngine` | PAT-G | **PASS** | Customer KYC refresh verification. |
| **TR-02** | Insufficient Funds | Phase 3 (Wave 3) | `TreasuryExposureEngine` | PAT-C | **PASS** | Balance reservation and pacing re-evaluation. |
| **TR-03** | Nostro Shortfall | Phase 3 (Wave 3) | `TreasuryExposureEngine` | PAT-C | **PASS** | Nostro account balance monitoring and sweep. |
| **TR-04** | FX Rate Unavailable | Phase 3 (Wave 3) | `TreasuryExposureEngine` | PAT-C | **PASS** | Treasury FX matrix spread verification. |
| **TR-05** | Authorization Missing | Phase 3 (Wave 4) | `AccountMasterEngine` | PAT-G | **PASS** | Signatory mandate dual-authorization check. |
| **TR-06** | Limit Breach | Phase 3 (Wave 3) | `TreasuryExposureEngine` | PAT-G | **PASS** | Client exposure limit verification. |
| **TR-07** | Liquidity Constraint | Phase 3 (Wave 3) | `TreasuryExposureEngine` | PAT-C | **PASS** | RTGS reserve account pacing. |
| **TR-08** | Credit Exposure Breach | Phase 3 (Wave 3) | `TreasuryExposureEngine` | PAT-G | **PASS** | Counterparty risk exposure clearance. |
| **ST-01** | Returned Payment | Phase 2 Baseline | `SettlementReconciliationEngine` (Consumed) | PAT-E | **PASS** | Formerly aliased as "Returned Payment Re-Credit"; canonical name restored. |
| **ST-02** | Account Closed | Phase 3 (Wave 2) | `SettlementReconciliationEngine` / `AccountMasterEngine` | PAT-E | **PASS** | Inward pacs.004 return matching and ledger reversal. |
| **ST-03** | Beneficiary Account Frozen | Phase 3 (Wave 2) | `SettlementReconciliationEngine` / `AccountMasterEngine` | PAT-E | **PASS** | Legal attachment notice return handling. |
| **ST-04** | Reconciliation Break | Phase 3 (Wave 2) | `SettlementReconciliationEngine` | PAT-E | **PASS** | Daily camt.053 ledger statement matching. |
| **ST-05** | Settlement Failure | Phase 3 (Wave 2) | `SettlementReconciliationEngine` | PAT-E | **PASS** | Clearing settlement reject reversal. |
| **ST-06** | Funds Trapped at Correspondent | Phase 3 (Wave 4) | `SettlementReconciliationEngine` | PAT-F | **PASS** | SWIFT GPI tracker and camt.027 claim dispatch. |
| **ST-07** | Unmatched Credit | Phase 3 (Wave 2) | `SettlementReconciliationEngine` | PAT-E | **PASS** | Inward unmatched credit ledger suspense. |

---

======================================================================
16. PHASE 2 PROTECTED PROFILE RECONCILIATION TABLE (MANDATORY TABLE 2)
======================================================================

The following table forensically reconciles the 11 accepted Phase 2 profiles, confirming their immutable canonical taxonomy identities, accepted implementation context, and strict protected status:

```
+---------------------------------------------------------------------------------------------------------------------------+
|                                  PHASE 2 PROTECTED PROFILE SEMANTIC RECONCILIATION                                        |
+-------+----------------------------+-----------------------------------+--------------------+-----------------------------+
| Code  | Canonical Profile Name     | Phase 2 Implementation Context    | Resolution Pattern | Boundary Status             |
+-------+----------------------------+-----------------------------------+--------------------+-----------------------------+
| DQ-01 | Invalid IBAN               | Modulo-97-10 Checksum Derivation  | PAT-A              | PROTECTED / NO REENGINEERING|
| DQ-02 | Invalid BIC / SWIFT        | 8-to-11 Head Office Normalization | PAT-A              | PROTECTED / NO REENGINEERING|
| DQ-05 | Invalid Address Format     | Structured Postal Address Repair  | PAT-A              | PROTECTED / NO REENGINEERING|
| DQ-06 | Missing Purpose Code       | Purpose Code Mapping & Insertion  | PAT-A              | PROTECTED / NO REENGINEERING|
| DQ-08 | Invalid Routing Code       | Routing / Transit Discrepancy Fix | PAT-A              | PROTECTED / NO REENGINEERING|
| PR-01 | Duplicate Payment          | Hash Collision Suppression        | PAT-E              | PROTECTED / NO REENGINEERING|
| PR-03 | ISO 20022 Validation Error | Schema / Syntax Validation Repair | PAT-B              | PROTECTED / NO REENGINEERING|
| PR-05 | Corrupted Message Format   | Governed Character Transformation | PAT-A              | PROTECTED / NO REENGINEERING|
| PR-08 | Queue Processing Failure   | Idempotent Queue Unblock & Retry  | PAT-B              | PROTECTED / NO REENGINEERING|
| CO-04 | Restricted Corridor        | Corridor Disambiguation Gate      | PAT-D              | PROTECTED / NO REENGINEERING|
| ST-01 | Returned Payment           | Return pacs.004 Re-Credit Package | PAT-E              | PROTECTED / NO REENGINEERING|
+-------+----------------------------+-----------------------------------+--------------------+-----------------------------+
```

---

======================================================================
17. GOVERNANCE STATUS STATEMENT
======================================================================

```
======================================================================
PHASE 3 INDUSTRIALIZATION ARCHITECTURE
STATUS: DESIGN / FORENSIC SEMANTIC RECONCILIATION ONLY

ENGINEERING AUTHORIZATION:
NOT GRANTED BY THIS DOCUMENT

WAVE 1 ENGINEERING:
NOT AUTHORIZED

PRODUCTION STP:
BLOCKED

PHASE 2:
CLOSED AND PROTECTED FROM RE-ENGINEERING

41-PROFILE TAXONOMY:
IMMUTABLE

8-PREDICATE STP FORMULA:
IMMUTABLE

BANK EXECUTION BOUNDARY:
IMMUTABLE

WAVE 0A:
COMPLETED / ACCEPTED BASELINE

WAVE 0B:
COMPLETED / ACCEPTED BASELINE
======================================================================
```

**Next Governance Action:**
1. Review and approve this reconciled Industrialization Architecture (v0.1.2).
2. Confirm the resolution of bank policy parameters in published Bank Evidence Required JSON models.
3. Issue a formal, separate **Wave 1 Implementation Authorization Gate** document.
4. Only upon explicit human engineering authorization may Wave 1 engineering commence.

---

======================================================================
18. v0.1.1 → v0.1.2 SEMANTIC RECONCILIATION SUMMARY
======================================================================

1. **Canonical Taxonomy Restoration**: Corrected all profile names across all matrices, tables, and narrative sections to match the exact immutable 41-profile BIAN/ISO taxonomy.
2. **`PR-03` Semantic Correction**: Reconciled `PR-03` to `ISO 20022 Validation Error` (eliminating the erroneous "Value Date Past Cutoff / Rollover" alias, which belongs strictly to `PR-04 Cutoff Missed`).
3. **`PR-05` Semantic Correction**: Reconciled `PR-05` to `Corrupted Message Format` (clarifying that "Amount Formatting / Decimals" was an implementation context, while the canonical profile covers governed message/character transformations).
4. **Data Quality Alias Remediation**: Reconciled `DQ-01 Invalid IBAN`, `DQ-02 Invalid BIC / SWIFT`, `DQ-05 Invalid Address Format`, `DQ-06 Missing Purpose Code`, `DQ-08 Invalid Routing Code`, and `DQ-09 Beneficiary Name Mismatch` to their authoritative canonical names.
5. **Processing & Compliance Alias Remediation**: Reconciled `PR-01 Duplicate Payment`, `PR-08 Queue Processing Failure`, `CO-04 Restricted Corridor`, and `ST-01 Returned Payment` to their authoritative canonical names.
6. **Mandatory Conceptual Distinctions Formulated**: Formally defined the 5 conceptual layers (Canonical Profile, Implementation Capability, Resolution Pattern, Evidence Contract, Authority Contract) in Section 5.2.
7. **Mandatory Reconciliation Tables Delivered**: Generated Section 15 (`41-Profile Semantic Reconciliation Table`) and Section 16 (`Phase 2 Protected Profile Semantic Reconciliation Table`) providing 100% complete traceability across all 41 profiles and confirming the Phase 2 protection boundary.
