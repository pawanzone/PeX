# PeX — Phase 2 Implementation Contract v1.3
## Final Micro-Patched Architecture-to-Engineering Technical Specification & Binding Implementation Contract

**Document Identifier:** `PeX-CONTRACT-P2-IMPL-004`  
**Version:** v1.3 (Final Micro-Patched Successor to v1.2)  
**Status:** FINAL MICRO-PATCHED IMPLEMENTATION CONTRACT — LEVEL 1 IMPLEMENTATION AUTHORIZED  
**Operating Mode:** READ-ONLY / PRE-IMPLEMENTATION (Zero Production Code Modifications)  
**Author:** Principal Enterprise Architect, Payment Domain Architect & Lead Engineer  
**Date:** October 2026  
**Authoritative Source Hierarchy:**  
1. `PeX_Evidence_Driven_STP_Architecture_Baseline_v1.1.md` (Immutable Architecture Baseline)  
2. `PeX_41_Profile_Authority_Evidence_STP_Validation_Report_v1.1.md` (Immutable Fact/Authority Baseline)  
3. `PeX_41_Profile_Evidence_Contract_Matrix_Forensic_Reconciliation_v1.1.md` (Forensic Reconciliation Baseline)  
4. `PeX_Phase2_Contract_Forensic_Hardening_Report_v0.1.md` (Forensic Hardening Report)  
5. `PeX_Phase2_Final_Contract_Hardening_Report_v0.1.md` (Final Hardening Report)  
6. `PeX_Phase2_Controlled_Expansion_Plan_v0.1.md` (Expansion Plan)  
7. `PeX_Phase1_PR03_Implementation_Report_v0.1.md` (Verified Phase 1 Baseline)  
8. `PeX_Phase2_Implementation_Contract_v1.2.md` (Prior Contract Baseline)  

---

## 1. Document Control & Changelog (v1.2 $\to$ v1.3)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       CHANGELOG: v1.2 → v1.3 MICRO-PATCH                               │
├───────────────────────────────┬────────────────────────────────────────────────────────────────────────┤
│ MP-01: V_auth Semantic        │ • Corrected V_auth semantics for PR-05 and DQ-05.                      │
│        Correction             │ • Replaced informal "V_auth = True based on technical standards" with  │
│        (PR-05 & DQ-05)        │   rigorous, deterministic Boolean evaluation rules.                    │
│                               │ • Established that technical standards (W3C XSD, SWIFT X-set, UPU S42) │
│                               │   satisfy V_det (technical validity) ONLY and MUST NOT satisfy V_auth. │
│                               │ • PR-05 V_auth: True iff field transformation is explicitly governed by│
│                               │   bank-authorized transliteration policy for corridor/scheme.          │
│                               │ • DQ-05 V_auth: True iff structured address is corroborated against    │
│                               │   Bank Beneficiary/Client Master OR authorized by bank policy.         │
│                               │ • If authority condition is unconfigured or unverified, V_auth = False │
│                               │   and STP fails closed (defaulting to Maker-Checker).                  │
├───────────────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ MP-02: DQ-05 Uniqueness       │ • Decoupled deterministic parser execution from candidate uniqueness.  │
│        Semantic Correction    │ • Explicitly separated: Inbound Parsing -> Structural Normalization -> │
│                               │   Candidate Generation -> Candidate Uniqueness (R_uniq) ->             │
│                               │   Structural Validation (V_det) -> Authoritative Corroboration (V_auth)│
│                               │ • Enforced: R_uniq = True ONLY when exactly one sufficiently supported │
│                               │   candidate interpretation exists under destination country grammar.   │
│                               │ • Ambiguous input where multiple segmentations are plausible forces    │
│                               │   R_uniq = False -> HITL / Disambiguation (parser single output !=     │
│                               │   unique authoritative resolution).                                    │
├───────────────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ MP-03: PR-05 Character &      │ • Replaced ASCII-only regex stripping (`re.sub`) with an explicit,     │
│        Encoding Transformation│   governed 9-stage character/encoding transformation pipeline:         │
│        Model Correction       │   1. Raw byte acquisition -> 2. Encoding detection/validation ->       │
│                               │   3. Decoding -> 4. Illegal control char detection ->                  │
│                               │   5. Scheme/bank-approved charset validation -> 6. Authorized          │
│                               │   transliteration/normalization -> 7. Semantic preservation validation │
│                               │   -> 8. Candidate generation -> 9. Deterministic validation (V_det).   │
│                               │ • Explicitly protected business semantics: account numbers, amounts,   │
│                               │   decimal positions, payment references, UETRs, entity identifiers.    │
│                               │ • Semantic content loss forces R_det = False (halts autonomous STP).   │
│                               │ • Valid Unicode characters (Latin-1, Cyrillic, Kanji) within target    │
│                               │   scheme charset policy are preserved and never unconditionally        │
│                               │   stripped simply for being non-ASCII.                                 │
└───────────────────────────────┴────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Two-Level Implementation Governance Model

```
====================================================================================================
LEVEL 1 — ENGINEERING IMPLEMENTATION AUTHORIZED:
Engineering is authorized to build and verify Phase 2 platform services, resolvers, validation engines,
ports, adapters, and automated test suites in strict sequential order:
Phase 2A (PR-05 -> PR-08 -> DQ-05) -> Phase 2B (PR-01 -> DQ-08 -> DQ-02) -> Phase 2C (DQ-01 -> DQ-06 -> ST-01 -> CO-04)

LEVEL 2 — PRODUCTION AUTONOMOUS STP EXECUTION GATED:
Autonomous STP payment release in live production remains STRICTLY GATED / BLOCKED per profile until:
1. Production configuration parameters (monetary limits, corridor allowlists, transliteration rules)
   are explicitly supplied in the target production environment.
2. Live Bank Systems of Record (Core DDA, Bank SSI Master, Customer Master) are certified & integrated.
3. Bank Risk, Operations, and Compliance leadership provides formal sign-off.
====================================================================================================
```

---

## 3. Implementation Governance Rules & Non-Negotiable Axioms

Engineering teams implementing Phase 2 are strictly bound by the following axioms:

1. **Evidence Before AI:** AI models and LLMs are strictly investigative copilots. AI confidence scores **never** satisfy any STP predicate.
2. **"Invalid / Failed $\neq$ Correct Replacement":** Detecting a syntax or checksum fault proves only invalidity; deriving the true replacement requires deterministic derivation and live System of Record (SoR) corroboration.
3. **Historical Precedent $\neq$ Authority:** Past successful repairs rank candidate hypotheses; historical frequency **never** satisfies mandatory authority gates.
4. **No Business-Semantic Data Loss:** Normalization and byte sanitization must be strictly lossless. Any loss of alphanumeric text, decimal places, or business identifiers stops autonomous processing ($R_{\text{det}} = \text{False}$).
5. **Technical Standard $\neq$ Payment Instance Authority:** Technical standards (W3C XSD, SWIFT X-set, UPU S42) establish structural conformity ($V_{\text{det}}$). They **do not** attest to the commercial authorization, beneficiary ownership, or real-world validity of a payment instance ($V_{\text{auth}}$).
6. **Fail-Closed Production Configuration:** All bank-specific parameters (monetary ceilings, retry counts, corridor allowlists, transliteration rules) are `BANK_CONFIG_REQUIRED`. Any `DEMO_ONLY_DEFAULT` values are strictly for local testing and **must never be loaded as implicit production configuration**. If a required configuration parameter is missing at runtime, the platform must fail closed ($P_{\text{bank}} = \text{False} \wedge V_{\text{auth}} = \text{False}$, autonomous STP disabled).
7. **Bank Execution Boundary:** PeX produces structured handoff payloads and audit receipts. PeX **never** directly debits/credits bank accounts or clears RTGS networks.

---

## 4. The Canonical 8-Predicate STP Boolean Formula

Straight-Through Processing eligibility is evaluated exclusively via the boolean formula:

$$\mathbf{STP\_ELIGIBLE} = E_{\text{suff}} \wedge R_{\text{det}} \wedge R_{\text{uniq}} \wedge V_{\text{det}} \wedge V_{\text{auth}} \wedge P_{\text{bank}} \wedge C_{\text{comp}} \wedge X_{\text{pre}}$$

```
+----+--------------------------------+-------------------------------------------------------------------------+
| #  | Predicate                      | Technical Definition & Evaluation Invariant                             |
+----+--------------------------------+-------------------------------------------------------------------------+
| 1  | Evidence_Sufficient (E_suff)   | All mandatory evidence present, within configured freshness TTL,        |
|    |                                | meeting required Trust Tier, with zero unresolved contradictions.       |
| 2  | Resolution_Determined (R_det)  | Deterministic algorithm successfully generated candidate repair payload |
|    |                                | with zero business-semantic loss.                                       |
| 3  | Resolution_Unique (R_uniq)     | Exactly ONE candidate repair is supported (Count == 1). Multiple        |
|    |                                | plausible hypotheses or ambiguous inputs force R_uniq = False.          |
| 4  | Deterministic_Valid (V_det)    | Repaired payload conforms 100% to ISO 20022 schemas and regex formats.  |
| 5  | Authority_Valid (V_auth)       | Applicable authoritative/operational authority condition explicitly    |
|    |                                | satisfied (Bank DDA/SSI, SWIFTRef, CoP, or Bank Transliteration Policy).|
| 6  | Bank_Policy_Allows (P_bank)    | Transaction amount <= Bank STP limit; currency and corridor permitted.  |
|    |                                | (Fails closed if configuration is missing).                             |
| 7  | Compliance_Gate_Passed (C_comp)| Independent Sanctions, PEP, and AML screening returns PASS (0 hits).     |
| 8  | Execution_Precondition (X_pre) | Clearing cutoff active, idempotency lock held, route reachable.          |
+----+--------------------------------+-------------------------------------------------------------------------+
```

---

## 5. Bank vs PeX Execution Boundary

```
+-------------------------------------------------------+-------------------------------------------------------+
| PeX RESPONSIBILITY BOUNDARY                           | BANK RESPONSIBILITY BOUNDARY                          |
+-------------------------------------------------------+-------------------------------------------------------+
| 1. Ingest exception & gather evidence dossier         | 1. Ingest original payment & detect initial error     |
| 2. Evaluate evidence sufficiency & trust tiers        | 2. Provide authoritative Core DDA & SSI Master data   |
| 3. Deterministically derive unique repair candidate   | 3. Execute legal Compliance & Sanctions release       |
| 4. Validate syntax against W3C ISO 20022 schemas      | 4. Ingest repaired payload & handoff receipt          |
| 5. Corroborate candidate against live SoR connector   | 5. Post accounting debits/credits to client DDA       |
| 6. Evaluate 8-predicate boolean formula               | 6. Dispatch payment instruction to RTGS clearing      |
| 7. Emit structured handoff payload & audit receipt    | 7. Return final settlement ACK/NACK to PeX            |
+-------------------------------------------------------+-------------------------------------------------------+
```

---

## 6. Phase 2 Scope & Phased Implementation Sequencing

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       PHASE 2 SEQUENTIAL PHASING                                       │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ **PHASE 2A: Syntax, Byte & Message Integrity (No Production Bank Integration Required)**               │
│ 1. PR-05: Corrupted Message Format (Governed Character & Encoding Transformation Engine)              │
│ 2. PR-08: Queue Processing Failure (Broker DLQ State Reset & Idempotency)                              │
│ 3. DQ-05: Invalid Address Format (UPU S42 Postal Parser to ISO PostalAddress24)                        │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ **PHASE 2B: State, Ledger Authority & External Directories**                                           │
│ 4. PR-01: Duplicate Payment (24-Hour Settlement Hash Ledger Service)                                    │
│ 5. DQ-08: Invalid Routing Code (Central Bank Merger Directory Adapter)                                 │
│ 6. DQ-02: Invalid BIC / SWIFT (SWIFTRef Directory Connector & BIC8/11 Normalizer)                       │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ **PHASE 2C: Multi-Contract Bank Corroboration & Conditional STP**                                      │
│ 7. DQ-01: Invalid IBAN (MOD-97 Solver + ISO 13616 + Bank SSI Master / CoP)                            │
│ 8. DQ-06: Missing Purpose Code (ISO Purpose Code Set & Remittance Classifier)                          │
│ 9. ST-01: Returned Payment (pacs.004 Return Reconciler & Handoff Adapter)                              │
│ 10. CO-04: Restricted Corridor (Geopolitical Sanctions Embargo Engine & pacs.002 Auto-Block)           │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Phase 2A Profile Implementation Contracts

---

### PROFILE: `PR-05` — `CORRUPTED_MESSAGE_FORMAT`

#### 1. Business Purpose
Execute a governed, lossless character and encoding transformation pipeline on inbound payment payloads containing non-printable control characters, illegal byte sequences, or character set violations to ensure full compliance with target ISO 20022 and scheme character set specifications while strictly preserving business-semantic integrity.

#### 2. Exception Trigger
Parser rejection or transport error due to unparseable binary control characters (`0x00..0x1F` excluding standard whitespace), invalid UTF-8 byte sequences, or characters violating the target payment scheme character set (e.g. SWIFT CBPR+ X-Set or Z-Set).

#### 3. Input Contract
- Inbound raw byte stream / string payload.
- Parser error JSON specifying byte offset, detected encoding fault, and target schema/scheme.

#### 4. Evidence Contract
- **4.1 Mandatory Evidence:**
  1. `RAW_PAYLOAD_BYTES`: Inbound raw byte stream (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
  2. `TARGET_SCHEME_CHARSET_SPEC`: Target payment scheme character set specification (e.g., SWIFT CBPR+ X-Set, ISO 20022 UTF-8 XML subset) (`TrustTier: TIER_2_EXTERNAL_AUTHORITATIVE`).
  3. `BANK_TRANSLITERATION_POLICY`: Bank operational policy defining authorized transliterations, character substitutions, and corridor encoding rules (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
- **4.2 Conditional Evidence:** None.
- **4.3 Optional Evidence:** `HISTORICAL_ENCODING_LOG`: Past encoding repair records (`TrustTier: TIER_4`).
- **4.4 Evidence Trust Tier:** Tier 1 (Raw Stream & Bank Policy), Tier 2 (Scheme Charset Spec).
- **4.5 Evidence Authority:** 
  - **Technical Syntax Authority:** SWIFT Standards / W3C XML Charset Specification (establishes structural character conformity under $V_{\text{det}}$; **does NOT prove semantic authorization of original author**).
  - **Operational Transformation Authority:** Bank Transliteration Policy (`BANK_CONFIG_REQUIRED`; establishes operational authorization under $V_{\text{auth}}$).
- **4.6 Freshness:** Static specification / Active policy version.
- **4.7 Evidence Identity:** SHA-256 hash of raw inbound byte stream + Target Scheme ID.
- **4.8 Evidence Provenance:** Ingested directly from Bank Inbound Transport Port.
- **4.9 Missing Evidence Behavior:** If raw bytes cannot be read or `BANK_TRANSLITERATION_POLICY` is unconfigured in production, set $E_{\text{suff}} = \text{False} \wedge V_{\text{auth}} = \text{False}$ and route to Operations Suspense.
- **4.10 Contradictory Evidence Behavior:** If scheme specification conflicts with XML schema definition, the more restrictive standard applies.

#### 5. Resolution Contract
- **5.1 Root Cause:** Presence of non-printable control characters, malformed multibyte sequences, or characters outside the target payment scheme character set.
- **5.2 Governed 9-Stage Transformation Pipeline:**
  1. **Raw Byte Acquisition:** Capture exact raw inbound payload bytes with SHA-256 integrity hash.
  2. **Encoding Detection & Validation:** Detect character encoding (UTF-8, ISO-8859-1, Windows-1252); validate byte sequence well-formedness.
  3. **Decoding:** Deterministically decode bytes into Unicode text buffer. If decoding fails irrecoverably, set $R_{\text{det}} = \text{False}$.
  4. **Illegal Control-Character Removal:** Strip non-printable control characters ($0\text{x}00..0\text{x}08, 0\text{x}0\text{B}..0\text{x}0\text{C}, 0\text{x}0\text{E}..0\text{x}1\text{F}$) while preserving standard formatting whitespace (Space $0\text{x}20$, Tab $0\text{x}09$, CR $0\text{x}0\text{D}$, LF $0\text{x}0\text{A}$).
  5. **Scheme Character-Set Validation:** Inspect all characters against the target scheme character set. If all characters are natively valid in the target scheme, no transliteration is performed. Non-ASCII characters (e.g., Latin-1, Cyrillic, Kanji) valid under the scheme's UTF-8 profile **must never be stripped**.
  6. **Authorized Transliteration / Normalization:** If the target scheme mandates a restricted character set (e.g. SWIFT X-set), execute bank-authorized deterministic transliteration rules (e.g., Unicode NFKC normalization, diacritic folding: `é` $\to$ `e`, `ü` $\to$ `ue`, `ñ` $\to$ `n` per scheme transliteration matrix).
  7. **Semantic Preservation Validation:** Perform mandatory post-transformation invariance checks:
     - Account numbers, IBANs, and BICs: **Zero character alterations allowed**.
     - Monetary amounts and decimal points: **Zero character alterations allowed**.
     - Payment references, UETRs, End-to-End IDs: **Zero character alterations allowed**.
     - Business identifiers (tax IDs, LEIs): **Zero character alterations allowed**.
  8. **Candidate Generation:** If semantic validation passes, generate canonical repaired payload ($R_{\text{det}} = \text{True}$).
  9. **Deterministic Validation:** Validate candidate against target ISO 20022 XML schema ($V_{\text{det}}$).
- **5.3 Deterministic Logic:** Pipeline execution governed strictly by scheme rules and bank transliteration tables.
- **5.4 Candidate Ranking:** N/A (Single deterministic transformation pipeline).
- **5.5 Uniqueness Rule:** Exactly ONE candidate payload produced ($R_{\text{uniq}} = \text{True}$).
- **5.6 Ambiguity Handling:** If binary payload contains non-text binary assets (e.g. gzip, zip, image attachments), candidate generation fails ($R_{\text{det}} = \text{False}$).
- **5.7 Semantic Loss Handling:** If any stage of transformation alters numeric values, decimal positions, account numbers, or business references, the candidate is marked `INVALID` ($R_{\text{det}} = \text{False}$) and routed to human operations.

#### 6. Authority / Validation Contract
- **6.1 Structural Validation ($V_{\text{det}}$):** Conforms 100% to target ISO 20022 XML schema and W3C XML 1.0 character specifications.
- **6.2 Mathematical Validation ($V_{\text{det}}$):** Amount fields, account strings, and checksums match pre-sanitization values 100%.
- **6.3 Scheme Validation ($V_{\text{det}}$):** Conforms 100% to target scheme character set (SWIFT X-set / Z-set / UTF-8 profile).
- **6.4 External Authority:** W3C / SWIFT standards establish structural character conformity ($V_{\text{det}} = \text{True}$); they **do NOT** establish payment instance authority ($V_{\text{auth}}$).
- **6.5 Bank Authority ($V_{\text{auth}}$):** Boolean evaluation rule:
  $$V_{\text{auth}} = \begin{cases} \text{True} & \text{if } \text{bank\_policy.is\_transliteration\_authorized}(\text{corridor}, \text{scheme}, \text{field\_type}) == \text{True} \\ \text{False} & \text{otherwise (unconfigured, prohibited, or unverified)} \end{cases}$$
- **6.6 Current-State Validation:** Verify sanitized payload parses into canonical `PaymentExceptionRecord`.
- **6.7 Contradiction Handling:** If schema validation fails post-sanitization, set $V_{\text{det}} = \text{False}$.

#### 7. STP Policy Contract
- **7.1 STP Allowed?:** YES (Group 1 Autonomous STP Capable subject to Bank Policy).
- **7.2 Required Policy Conditions:** Sanitization must be 100% lossless regarding alphanumeric and business data; bank transliteration policy explicitly authorized.
- **7.3 Compliance Conditions:** Sanitized payload must undergo independent Sanctions & AML screening ($C_{\text{comp}} = \text{PASS}$).
- **7.4 Monetary Threshold:** `BANK_CONFIG_REQUIRED` (`DEMO_ONLY_DEFAULT — NOT PRODUCTION POLICY: $1,000,000 USD`). Fail-closed if unconfigured.
- **7.5 Corridor Conditions:** `BANK_CONFIG_REQUIRED` (Permitted corridor allowlist).
- **7.6 Maker-Checker:** Bypassed if all 8 predicates evaluate to True; required if semantic loss detected or transliteration unapproved.
- **7.7 HITL Conditions:** Triggered if byte stripping alters business-semantic fields or if $V_{\text{auth}} = \text{False}$.
- **7.8 Execution Preconditions:** Idempotency lock active; bank payment hub route open ($X_{\text{pre}} = \text{True}$).

#### 8. STP Predicate Evaluation
```
E_suff = True (Raw stream, scheme charset spec & bank transliteration policy present)
R_det  = True (Governed 9-step transformation executed with zero semantic loss)
R_uniq = True (Exactly one canonical repaired payload derived)
V_det  = True (Target ISO 20022 schema & scheme charset validated)
V_auth = True (Bank operational policy explicitly authorizes character transformation for corridor)
P_bank = True (Amount <= Bank policy ceiling; fails closed if unconfigured)
C_comp = True (Sanctions/AML screening PASS)
X_pre  = True (Idempotency locked, route operational)
---------------------------------------------------------
STP_ELIGIBLE = True -> Emit Repaired Payload to Bank Output Port (Subject to Level 2 Production Gating)
```

#### 9. Output Contract
Sanitized ISO 20022 XML payload containing valid UTF-8 text conforming to target scheme character set with zero non-printable control characters.

#### 10. Bank Handoff Contract
Serialized XML payload written to Bank Output Port with SHA-256 integrity receipt and diff summary.

#### 11. Audit / Provenance Requirements
Log raw payload hash, transformed payload hash, bytes modified count, transliteration rule IDs, and stage transitions in SHA-256 linear hash ledger.

#### 12. Failure States
`INSUFFICIENT_EVIDENCE` (Unreadable stream / unconfigured policy) $\to$ `RESOLUTION_FAILED` (Binary corruption / non-text) $\to$ `SEMANTIC_LOSS_SUSPENSE` (Alphanumeric/amount altered) $\to$ `COMPLIANCE_HOLD`.

#### 13. Security Requirements
Zero PII leakage during transformation; tokenized account numbers preserved untouched.

#### 14. Test Requirements
1. Happy path: Non-printable control bytes stripped from remittance text while preserving valid text.
2. Happy path: Multibyte Unicode characters (Latin-1, Cyrillic, Kanji) preserved when valid under target scheme UTF-8 profile.
3. Happy path: Bank-authorized transliteration (e.g. `München` $\to$ `Muenchen` or `München` $\to$ `Munchen` per scheme rules) executes with zero semantic loss.
4. Negative: Binary payload (gzip) fails gracefully to human review ($R_{\text{det}} = \text{False}$).
5. Negative: Any alteration to amount digits or decimal positions halts processing ($R_{\text{det}} = \text{False}$).
6. Negative: Unconfigured or missing bank transliteration policy forces $V_{\text{auth}} = \text{False} \wedge P_{\text{bank}} = \text{False}$ (fails closed to Maker-Checker).
7. Adversarial: Prompt injection embedded in raw stream sanitized safely as literal text without execution.

#### 15. Phase 1 Reuse
`ResolutionEngine`, `AuthorityValidationEngine`, `EvidenceSTPEvaluator`, `FolderOutputAdapter`, `AuditService`.

#### 16. New Phase 2 Capability
`GovernedCharacterEncodingTransformer` (P0 platform component).

#### 17. External Dependency
SWIFT MT/MX Character Set Specifications (X-Set, Z-Set, UTF-8 Profile).

#### 18. Bank Discovery Dependency
Bank accepted character sets and authorized transliteration matrices (`BANK_DISCOVERY_REQUIRED`).

#### 19. Open Questions
Bank policy on non-Latin Unicode characters in debtor/creditor name fields across domestic vs cross-border clearing rails (`BANK_DISCOVERY_REQUIRED`).

#### 20. Implementation & Production STP Status
- **Platform Implementation Status:** **PLATFORM IMPLEMENTATION READY (Phase 2A Slice 1)**.
- **Production STP Status:** **BLOCKED / NOT ENABLED** (Gated pending bank transliteration policy & monetary threshold configuration).

---

### PROFILE: `PR-08` — `QUEUE_PROCESSING_FAILURE`

#### 1. Business Purpose
Safely recover and re-process payment messages stalled in Dead Letter Queues (DLQs) due to consumer deadlocks, transient message broker timeouts, or connection drops without creating duplicate disbursements or re-enqueuing poison pills.

#### 2. Exception Trigger
Message moved to Dead Letter Queue (DLQ) by message broker (RabbitMQ, IBM MQ, Kafka) after retry threshold exhaustion with transient error code.

#### 3. Input Contract
- Dead-lettered message payload with transport metadata (DLQ headers, retry count, original exchange/topic).
- Broker error log / reason code.

#### 4. Evidence Contract
- **4.1 Mandatory Evidence:**
  1. `DLQ_MESSAGE_PAYLOAD`: Inbound dead-lettered message (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
  2. `BROKER_DLQ_METADATA`: DLQ routing headers, retry counter, death reason (`TrustTier: TIER_1`).
  3. `IDEMPOTENCY_STATE_RECORD`: Current transaction state in Core Settlement Ledger (`TrustTier: TIER_1`).
- **4.2 Conditional Evidence:** None.
- **4.3 Optional Evidence:** Historical DLQ recovery statistics (`TrustTier: TIER_4`).
- **4.4 Evidence Trust Tier:** Tier 1 (Bank Messaging Hub & Core Settlement Ledger).
- **4.5 Evidence Authority:** Bank Messaging Architecture SOP & Core Settlement Ledger (proves message state & non-settlement; **does NOT prove payload correctness**).
- **4.6 Freshness:** Real-time event-driven query.
- **4.7 Evidence Identity:** Message Broker Message-ID + Payment UETR.
- **4.8 Evidence Provenance:** Captured from Bank Messaging Adapter and verified against Settlement Hash Store.
- **4.9 Missing Evidence Behavior:** If idempotency state cannot be verified from Core Ledger, immediately halt and route to Operations.
- **4.10 Contradictory Evidence Behavior:** If broker metadata indicates un-processed but Core Ledger indicates settled, **immediately block re-enqueue** and mark as `POTENTIAL_DUPLICATE`.

#### 5. Resolution Contract
- **5.1 Root Cause:** Transient broker deadlock, consumer lock starvation, or temporary network partition during message handoff.
- **5.2 Candidate Generation:** Validate payload integrity, clear consumer lock state, reset message retry counter, and prepare clean re-enqueue instruction.
- **5.3 Deterministic Logic:**
  ```python
  if idempotency_state == "UNPROCESSED" and is_poison_pill(payload) == False and retry_count < MAX_RETRIES:
      candidate = create_re_enqueue_instruction(payload, target_queue="PAYMENT_INGESTION")
  ```
- **5.4 Candidate Ranking:** N/A (Single deterministic state action).
- **5.5 Uniqueness Rule:** Exactly one re-enqueue instruction generated ($R_{\text{uniq}} = \text{True}$).
- **5.6 Ambiguity Handling:** If idempotency record is locked or pending settlement, candidate generation fails ($R_{\text{det}} = \text{False}$).
- **5.7 Invalid Candidate Handling:** If payload is a confirmed poison pill (malformed unparseable binary), route to Permanent Suspense Queue.

#### 6. Authority / Validation Contract
- **6.1 Structural Validation:** Validate message schema and header integrity.
- **6.2 Mathematical Validation:** Payload SHA-256 hash must match original dispatch hash 100%.
- **6.3 Scheme Validation:** Message broker protocol compliance (AMQP 1.0 / JMS / Kafka Protocol).
- **6.4 External Authority:** N/A (Internal bank infrastructure state).
- **6.5 Bank Authority:** Bank Core Settlement Ledger confirms transaction is `UNSETTLED` ($V_{\text{auth}} = \text{True}$).
- **6.6 Current-State Validation:** Confirm consumer deadlock lock has been released in Redis/DB.
- **6.7 Contradiction Handling:** If ledger indicates debit posted, reject re-enqueue ($V_{\text{auth}} = \text{False}$).

#### 7. STP Policy Contract
- **7.1 STP Allowed?:** YES (Group 1 Autonomous STP Capable subject to Bank Policy).
- **7.2 Required Policy Conditions:** Max retry limit `BANK_CONFIG_REQUIRED` (`DEMO_ONLY_DEFAULT — NOT PRODUCTION POLICY: <= 3 retries`); Core Ledger confirms zero settlement debit.
- **7.3 Compliance Conditions:** Standard compliance clearance preserved ($C_{\text{comp}} = \text{PASS}$).
- **7.4 Monetary Threshold:** `BANK_CONFIG_REQUIRED` (`DEMO_ONLY_DEFAULT — NOT PRODUCTION POLICY: $1,000,000 USD`).
- **7.5 Corridor Conditions:** All active payment queues.
- **7.6 Maker-Checker:** Bypassed for transient retry $\le 3$; mandatory Maker-Checker for retry $>3$ or poison pills.
- **7.7 HITL Conditions:** Triggered upon 3 consecutive consumer nacks or state lock conflict.
- **7.8 Execution Preconditions:** Message broker target queue operational; consumer lock cleared ($X_{\text{pre}} = \text{True}$).

#### 8. STP Predicate Evaluation
```
E_suff = True (DLQ payload, metadata & unsettled ledger verified)
R_det  = True (Lock cleared & re-enqueue instruction derived)
R_uniq = True (Single target queue routing)
V_det  = True (Message format and headers valid)
V_auth = True (Core Settlement Ledger attests UNSETTLED)
P_bank = True (Retry count <= max and amount <= ceiling; fails closed if unconfigured)
C_comp = True (Sanctions screening status preserved PASS)
X_pre  = True (Target queue active, consumer lock cleared)
---------------------------------------------------------
STP_ELIGIBLE = True -> Re-enqueue to Bank Payment Queue (Subject to Level 2 Production Gating)
```

#### 9. Output Contract
Clean re-enqueue message with cleared lock state, updated retry header, and original payload.

#### 10. Bank Handoff Contract
Dispatch to Bank Messaging Hub (RabbitMQ / IBM MQ / Kafka) with tracking receipt.

#### 11. Audit / Provenance Requirements
Log DLQ reason, retry count, consumer ID, clearance timestamp, and SHA-256 hash chain in Audit Ledger.

#### 12. Failure States
`LEDGER_STATE_CONFLICT` (Already settled) $\to$ `POISON_PILL_DETECTED` $\to$ `RETRY_EXHAUSTION_SUSPENSE` $\to$ `BROKER_UNREACHABLE`.

#### 13. Security Requirements
Ensure re-enqueued message retains original authentication context without privilege escalation.

#### 14. Test Requirements
1. Happy path: Stalled DLQ message with retry=1 re-enqueued successfully.
2. Failure: Message already marked SETTLED in Core Ledger is blocked from re-enqueue ($V_{\text{auth}} = \text{False}$).
3. Failure: Retry count exceeds bank limit halts and escalates to Operations ($P_{\text{bank}} = \text{False}$).
4. Failure: Poison pill payload (syntax crash) routes to permanent dead letter suspense ($R_{\text{det}} = \text{False}$).
5. Adversarial: Replay attack attempting duplicate processing is intercepted by idempotency lock.

#### 15. Phase 1 Reuse
`STPEligibilityDecision`, `EvidenceDossier`, `AuditService`, `HexagonalAdapters`.

#### 16. New Phase 2 Capability
`MessageBrokerQueueResetAdapter` & `IdempotencyLockManager` (P0 platform component).

#### 17. External Dependency
None (Internal bank messaging hub).

#### 18. Bank Discovery Dependency
Broker type (IBM MQ vs RabbitMQ vs Kafka), DLQ header conventions, max retry policy.

#### 19. Open Questions
Bank retry backoff schedule (exponential vs fixed interval) (`BANK_CONFIG_REQUIRED`).

#### 20. Implementation & Production STP Status
- **Platform Implementation Status:** **PLATFORM IMPLEMENTATION READY (Phase 2A Slice 2)**.
- **Production STP Status:** **BLOCKED / NOT ENABLED** (Gated pending message broker integration and retry limits).

---

### PROFILE: `DQ-05` — `INVALID_ADDRESS_FORMAT`

#### 1. Business Purpose
Parse and normalize legacy unstructured free-text postal address lines (`<AdrLine>`) into discrete, structured ISO 20022 tags (`<StrtNm>`, `<BldgNb>`, `<PstCd>`, `<TwnNm>`, `<Ctry>`) to comply with the global PMPG / ISO 20022 November 2026 mandate while enforcing unambiguous candidate uniqueness and bank authority corroboration.

#### 2. Exception Trigger
Inbound ISO 20022 validation failure or clearing network NACK due to unstructured address lines or missing mandatory discrete postal tags.

#### 3. Input Contract
- Raw XML payment payload with unstructured `<AdrLine>` tags.
- Schema validation error JSON citing PMPG / CBPR+ address structuring mandate.

#### 4. Evidence Contract
- **4.1 Mandatory Evidence:**
  1. `RAW_PAYLOAD_ADDRESS_LINES`: Inbound unstructured address strings (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
  2. `UPU_S42_POSTAL_STANDARD`: Universal Postal Union international address format grammar (`TrustTier: TIER_2_EXTERNAL_AUTHORITATIVE`).
  3. `ISO_3166_COUNTRY_CODE_LIST`: Authoritative 2-character country code list (`TrustTier: TIER_2_EXTERNAL_AUTHORITATIVE`).
  4. `BANK_ADDRESS_NORMALIZATION_POLICY`: Bank operational policy authorizing automated address restructuring for specific clearing rails/countries (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
- **4.2 Conditional Evidence:** 
  1. `BENEFICIARY_MASTER_RECORD`: Client / Beneficiary Master address record (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
  2. `NATIONAL_POSTAL_DIRECTORY`: Country-specific postal directory (e.g. USPS, Royal Mail PAF) if country is US/GB (`TrustTier: TIER_2`).
- **4.3 Optional Evidence:** `HISTORICAL_ADDRESS_NORMALIZATIONS`: Past address parsing records (`TrustTier: TIER_4`).
- **4.4 Evidence Trust Tier:** Tier 1 (Raw Payload & Bank Policy/Master), Tier 2 (UPU S42, ISO 3166, Postal Directories).
- **4.5 Evidence Authority:** 
  - **Structural Syntax Authority:** Universal Postal Union S42 Standard (establishes postal syntax and structural tag grammar under $V_{\text{det}}$; **does NOT prove real-world resident occupancy, customer identity, or account ownership**).
  - **Business / Operational Authority:** Bank Beneficiary/Client Master OR Bank Address Normalization Policy (`BANK_CONFIG_REQUIRED`; establishes operational authorization under $V_{\text{auth}}$).
- **4.6 Freshness:** Static UPU grammar / Active policy version / Monthly postal directory sync.
- **4.7 Evidence Identity:** SHA-256 hash of address lines + Country Code.
- **4.8 Evidence Provenance:** Parsed from inbound payment payload and evaluated against UPU grammar.
- **4.9 Missing Evidence Behavior:** If Country Code (`<Ctry>`) cannot be identified or `BANK_ADDRESS_NORMALIZATION_POLICY` is unconfigured, set $E_{\text{suff}} = \text{False} \wedge V_{\text{auth}} = \text{False}$ and route to Disambiguation/Ops.
- **4.10 Contradictory Evidence Behavior:** If parsed postal code contradicts country format, halt and route to Operations.

#### 5. Resolution Contract
- **5.1 Root Cause:** Address presented as unstructured free-text string instead of discrete ISO 20022 tags.
- **5.2 Distinct Resolution Pipeline Stages:**
  1. **Inbound Parsing:** Tokenize raw `<AdrLine>` strings into atomic candidate segments (tokens, numbers, delimiters).
  2. **Structural Normalization:** Map parsed tokens to candidate ISO 20022 tags (`<StrtNm>`, `<BldgNb>`, `<PstCd>`, `<TwnNm>`, `<Ctry>`) using UPU S42 grammar rules for the destination country.
  3. **Candidate Generation:** Construct potential candidate `PostalAddress24` XML structures.
  4. **Candidate Uniqueness Evaluation ($R_{\text{uniq}}$):**
     - **Deterministic Evaluation Rule:** Evaluate whether exactly ONE candidate interpretation is objectively and unambiguously supported by the grammar.
     - If the address allows multiple plausible segmentations (e.g., ambiguous street name vs building number vs apartment number, or ambiguous town vs postal code boundary), **$R_{\text{uniq}} = \text{False}$**.
     - A parser producing a single arbitrary choice among multiple plausible segmentations **MUST NOT** be treated as a unique resolution.
     - Multiple plausible interpretations force $R_{\text{uniq}} = \text{False} \to$ route to HITL Disambiguation.
  5. **Structural Validation ($V_{\text{det}}$):** Conformance verification against W3C ISO 20022 `PostalAddress24` XSD schema.
  6. **Authoritative Corroboration ($V_{\text{auth}}$):** Corroborate structured elements against Bank Beneficiary/Client Master or verify bank operational policy authorization.
- **5.3 Deterministic Logic:** UPU S42 country-specific grammar parsing engine with strict ambiguity detection.
- **5.4 Candidate Ranking:** N/A (Only uniquely unambiguous candidates proceed to autonomous evaluation).
- **5.5 Uniqueness Rule:** $R_{\text{uniq}} = \text{True}$ ONLY when exactly one candidate interpretation is valid and unambiguous under the country grammar.
- **5.6 Ambiguity Handling:** If street name cannot be separated from building number unambiguously, or if multiple postal codes match, set $R_{\text{uniq}} = \text{False}$ and route to human operations.
- **5.7 Invalid Candidate Handling:** If parsed text violates target field length limits ($\le 70$ chars for street, $\le 16$ chars for building number), candidate marked `INVALID` ($R_{\text{det}} = \text{False}$).

#### 6. Authority / Validation Contract
- **6.1 Structural Validation ($V_{\text{det}}$):** Validated against W3C ISO 20022 `PostalAddress24` XSD schema.
- **6.2 Mathematical Validation ($V_{\text{det}}$):** Postal code format check (e.g. US 5/9-digit regex, UK outward/inward code regex).
- **6.3 Scheme Validation ($V_{\text{det}}$):** PMPG / SWIFT CBPR+ discrete address mandate compliance.
- **6.4 External Authority:** UPU S42 international postal grammar (establishes structural syntax conformity under $V_{\text{det}}$; **does NOT validate beneficiary identity or payment authority**).
- **6.5 Bank Authority ($V_{\text{auth}}$):** Boolean evaluation rule:
  $$V_{\text{auth}} = \begin{cases} \text{True} & \text{if } \text{is\_corroborated\_by\_client\_master}(\text{address}) \vee \text{bank\_policy.is\_address\_restructuring\_authorized}(\text{country}, \text{rail}) \\ \text{False} & \text{otherwise (uncorroborated, unauthorized, or unconfigured)} \end{cases}$$
- **6.6 Current-State Validation:** Verify that parsed country code is active in ISO 3166-1 alpha-2.
- **6.7 Contradiction Handling:** If country code is sanctioned under OFAC, trip Compliance Gate ($C_{\text{comp}} = \text{FAIL}$).

#### 7. STP Policy Contract
- **7.1 STP Allowed?:** YES (Group 1 Autonomous STP Capable subject to Bank Policy).
- **7.2 Required Policy Conditions:** Output must conform 100% to `PostalAddress24` XSD; exactly one unambiguous interpretation ($R_{\text{uniq}} = \text{True}$); bank address policy authorized.
- **7.3 Compliance Conditions:** Parsed Country and Town must undergo Sanctions screening ($C_{\text{comp}} = \text{PASS}$).
- **7.4 Monetary Threshold:** `BANK_CONFIG_REQUIRED` (`DEMO_ONLY_DEFAULT — NOT PRODUCTION POLICY: $1,000,000 USD`).
- **7.5 Corridor Conditions:** All active non-sanctioned corridors.
- **7.6 Maker-Checker:** Bypassed if parsing is unambiguous and authorized under bank policy; required if country ambiguous or multiple segmentations exist.
- **7.7 HITL Conditions:** Triggered if country code cannot be derived, multiple candidate interpretations exist ($R_{\text{uniq}} = \text{False}$), or $V_{\text{auth}} = \text{False}$.
- **7.8 Execution Preconditions:** ISO 20022 XML document envelope intact ($X_{\text{pre}} = \text{True}$).

#### 8. STP Predicate Evaluation
```
E_suff = True (Raw address lines, UPU grammar, ISO 3166 & bank address policy verified)
R_det  = True (Deterministic UPU postal parsing & structural normalization executed)
R_uniq = True (Exactly one unambiguous candidate interpretation supported under country grammar)
V_det  = True (Conforms 100% to PostalAddress24 XSD schema)
V_auth = True (Corroborated by Bank Beneficiary Master or explicitly authorized by bank address policy)
P_bank = True (Amount <= Bank policy ceiling; fails closed if unconfigured)
C_comp = True (Sanctions screening on parsed jurisdiction PASS)
X_pre  = True (XML payload structure operational)
---------------------------------------------------------
STP_ELIGIBLE = True -> Emit Repaired XML to Bank Output Port (Subject to Level 2 Production Gating)
```

#### 9. Output Contract
Repaired ISO 20022 XML document containing fully structured `<PstlAdr>` block with `<StrtNm>`, `<BldgNb>`, `<PstCd>`, `<TwnNm>`, `<Ctry>`.

#### 10. Bank Handoff Contract
Serialized XML payload written to Bank Output Port with SHA-256 integrity receipt.

#### 11. Audit / Provenance Requirements
Log raw address string, parsed discrete fields, ambiguity score, UPU grammar version, and stage transitions in SHA-256 ledger.

#### 12. Failure States
`UNPARSEABLE_COUNTRY_SUSPENSE` $\to$ `AMBIGUOUS_ADDRESS_DISAMBIGUATION` ($R_{\text{uniq}}=\text{False}$) $\to$ `POSTAL_SCHEMA_VIOLATION` $\to$ `SANCTIONED_JURISDICTION_BLOCK`.

#### 13. Security Requirements
Ensure address parsing does not alter beneficiary names or expose PII in debug logs.

#### 14. Test Requirements
1. Happy path: Unambiguous US address string parsed into discrete tags conforming to XSD with bank policy authorization $\implies$ STP proceeds.
2. Happy path: Unambiguous UK postal address with alphanumeric postcode parsed cleanly.
3. Failure (Ambiguity): Multi-line address with ambiguous street/building segmentation produces multiple plausible interpretations $\implies$ $R_{\text{uniq}} = \text{False} \implies$ routes to Disambiguation/HITL.
4. Failure (Uncorroborated): Address parsed into XSD format but bank address policy is unconfigured $\implies$ $V_{\text{auth}} = \text{False} \wedge P_{\text{bank}} = \text{False} \implies$ fails closed to Maker-Checker.
5. Negative: Address missing valid country code halts and routes to Ops ($E_{\text{suff}} = \text{False}$).
6. Negative: Extremely long street address ($>70$ chars) handled without silent truncation.
7. Adversarial: Prompt injection embedded in address line parsed strictly as literal data.

#### 15. Phase 1 Reuse
`ResolutionEngine`, `AuthorityValidationEngine`, `EvidenceSTPEvaluator`, `FolderOutputAdapter`, `AuditService`.

#### 16. New Phase 2 Capability
`UPUPostalAddressNormalizer` (P0 platform component).

#### 17. External Dependency
UPU S42 Postal Grammar / ISO 3166-1 Country Code List.

#### 18. Bank Discovery Dependency
Bank policy on handling optional building number vs street name concatenation.

#### 19. Open Questions
Non-Latin character transliteration rules for Asian/Middle-Eastern postal addresses (`BANK_DISCOVERY_REQUIRED`).

#### 20. Implementation & Production STP Status
- **Platform Implementation Status:** **PLATFORM IMPLEMENTATION READY (Phase 2A Slice 3)**.
- **Production STP Status:** **BLOCKED / NOT ENABLED** (Gated pending bank policy configuration and postal directory integration).

---

## 8. Phase 2B Profile Implementation Contracts

---

### PROFILE: `PR-01` — `DUPLICATE_PAYMENT`

#### 1. Business Purpose
Detect and deterministically suppress exact duplicate payment instructions (identical transaction hash and UETR) to prevent double settlement debits, while routing similar but distinct payments (potential duplicates) to human operations.

#### 2. Exception Trigger
Core Banking or Payment Hub duplicate alert triggered by UETR collision or transaction fingerprint match within a 24-hour sliding settlement window.

#### 3. Input Contract
- Inbound payment payload with UETR, debtor account, amount, currency, and timestamp.
- Bank Payment Hub duplicate detection flag.

#### 4. Evidence Contract
- **4.1 Mandatory Evidence:**
  1. `INBOUND_PAYLOAD_HASH`: SHA-256 hash of complete business payload (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
  2. `SETTLEMENT_LEDGER_RECORD`: 24-hour sliding window settlement record matching UETR (`TrustTier: TIER_1`).
  3. `ORIGINAL_DEBIT_STATUS`: Confirmation that original transaction was debited/settled (`TrustTier: TIER_1`).
- **4.2 Conditional Evidence:** `INVOICE_REFERENCE_MATCH`: Invoice reference extracted from `<RmtInf>` (`TrustTier: TIER_1`).
- **4.3 Optional Evidence:** Historical duplicate frequency for corporate client (`TrustTier: TIER_4`).
- **4.4 Evidence Trust Tier:** Tier 1 (Bank Core Ledger & Settlement Hash Store).
- **4.5 Evidence Authority:** Bank Core Settlement Ledger (proves prior settlement execution; **does NOT prove customer commercial intent**).
- **4.6 Freshness:** Real-time query across sliding window (`BANK_CONFIG_REQUIRED`; `DEMO_ONLY_DEFAULT: 24 hours`).
- **4.7 Evidence Identity:** Payment UETR + SHA-256 Payload Hash.
- **4.8 Evidence Provenance:** Verified directly against Bank Settlement Hash Ledger.
- **4.9 Missing Evidence Behavior:** If settlement ledger is unreachable, set $E_{\text{suff}} = \text{False}$ and suspend case (do NOT guess).
- **4.10 Contradictory Evidence Behavior:** If UETR matches but amounts or beneficiaries differ, mark as `COLLISION_ANOMALY` and route to Investigation.

#### 5. Resolution Contract
- **5.1 Root Cause:** Re-transmission of identical payment file or message replay by debtor ERP/AP system.
- **5.2 Candidate Generation:**
  - **Exact Duplicate:** Identical UETR + Exact SHA-256 Hash Collision + Settled State $\implies$ **Deterministic Cancellation & Suppression Instruction**.
  - **Potential Duplicate:** Same Amount + Same Beneficiary + Distinct Invoice / Distinct UETR $\implies$ **Route to Maker-Checker Worklist**.
- **5.3 Deterministic Logic:**
  ```python
  if uetr_match and hash_collision and original_settled:
      resolution = "DETERMINISTIC_DUPLICATE_SUPPRESSION"
  else:
      resolution = "POTENTIAL_DUPLICATE_HUMAN_REVIEW"
  ```
- **5.4 Candidate Ranking:** N/A (Binary classification: Exact vs Potential).
- **5.5 Uniqueness Rule:** Exactly one suppression directive derived ($R_{\text{uniq}} = \text{True}$).
- **5.6 Ambiguity Handling:** Any variation in invoice number or amount forces $R_{\text{uniq}} = \text{False}$ and routes to HITL.
- **5.7 Invalid Candidate Handling:** If original payment was returned/cancelled, candidate marked `INVALID` and routed to Ops.

#### 6. Authority / Validation Contract
- **6.1 Structural Validation:** Validate duplicate cancellation schema (`pacs.002` / internal cancellation receipt).
- **6.2 Mathematical Validation:** Exact decimal amount match between duplicate and original.
- **6.3 Scheme Validation:** UCC Article 4A-205 duplicate payment rules / CPMI Finality principles.
- **6.4 External Authority:** N/A (Bank internal settlement ledger authority).
- **6.5 Bank Authority:** Bank Core Settlement Ledger attests prior execution ($V_{\text{auth}} = \text{True}$).
- **6.6 Current-State Validation:** Confirm original payment state is `SETTLED` or `IN_FLIGHT_CLEARING`.
- **6.7 Contradiction Handling:** If original payment failed/rejected, duplicate suppression is blocked ($V_{\text{auth}} = \text{False}$).

#### 7. STP Policy Contract
- **7.1 STP Allowed?:** YES (Group 1 Autonomous STP Capable for Exact Duplicates subject to Bank Policy).
- **7.2 Required Policy Conditions:** Suppression permitted ONLY for exact UETR + SHA-256 hash collisions.
- **7.3 Compliance Conditions:** Standard compliance clearance preserved ($C_{\text{comp}} = \text{PASS}$).
- **7.4 Monetary Threshold:** `BANK_CONFIG_REQUIRED` (`DEMO_ONLY_DEFAULT — NOT PRODUCTION POLICY: $1,000,000 USD`).
- **7.5 Corridor Conditions:** All active payment corridors.
- **7.6 Maker-Checker:** Bypassed for exact collisions; mandatory for potential duplicates.
- **7.7 HITL Conditions:** Triggered if invoice number differs or amount delta $>0$.
- **7.8 Execution Preconditions:** Idempotency cancellation lock acquired ($X_{\text{pre}} = \text{True}$).

#### 8. STP Predicate Evaluation
```
E_suff = True (Inbound hash, ledger record & debit status verified)
R_det  = True (Exact duplicate suppression instruction derived)
R_uniq = True (Deterministic cancellation directive)
V_det  = True (Cancellation payload valid)
V_auth = True (Core Settlement Ledger confirms prior settlement)
P_bank = True (Exact collision allowed under bank policy; fails closed if unconfigured)
C_comp = True (Sanctions screening PASS)
X_pre  = True (Cancellation idempotency lock active)
---------------------------------------------------------
STP_ELIGIBLE = True -> Emit Duplicate Suppression Receipt (Subject to Level 2 Production Gating)
```

#### 9. Output Contract
Duplicate Suppression Notification / Cancellation `pacs.002` XML with reference to original settled UETR.

#### 10. Bank Handoff Contract
Handoff cancellation directive to Bank Payment Hub; prevent outbound dispatch to clearing.

#### 11. Audit / Provenance Requirements
Log original UETR, duplicate UETR, SHA-256 collision digest, timestamp delta, and suppression reason in SHA-256 ledger.

#### 12. Failure States
`POTENTIAL_DUPLICATE_SUSPENSE` $\to$ `ORIGINAL_TX_NOT_FOUND` $\to$ `SETTLEMENT_STORE_UNAVAILABLE`.

#### 13. Security Requirements
Prevent duplicate suppression from being exploited to censor legitimate distinct payments.

#### 14. Test Requirements
1. Happy path: Exact duplicate (same UETR, same hash) suppressed autonomously.
2. Failure: Same amount and beneficiary but distinct invoice ref routes to Maker-Checker.
3. Failure: Same amount but original payment was rejected/cancelled routes to Ops.
4. Adversarial: Hash collision attack with modified beneficiary intercepted and blocked.
5. Replay: Re-submitting identical cancellation instruction returns cached receipt safely.

#### 15. Phase 1 Reuse
`EvidenceSTPEvaluator`, `STPPolicyConfig`, `FolderOutputAdapter`, `AuditService`.

#### 16. New Phase 2 Capability
`SettlementHashLedgerService` (P0 platform component).

#### 17. External Dependency
None (Internal bank settlement store).

#### 18. Bank Discovery Dependency
Sliding window duration (24h vs 48h), duplicate matching key definition.

#### 19. Open Questions
Bank policy on fee handling for suppressed duplicate wires (`BANK_CONFIG_REQUIRED`).

#### 20. Implementation & Production STP Status
- **Platform Implementation Status:** **PLATFORM IMPLEMENTATION READY WITH BANK CONDITIONS (Phase 2B Slice 4)**.
- **Production STP Status:** **BLOCKED / NOT ENABLED** (Gated pending live Settlement Hash Store integration).

---

### PROFILE: `DQ-08` — `INVALID_ROUTING_CODE`

#### 1. Business Purpose
Detect retired or merged domestic bank routing transit numbers (e.g. US ABA Routing Transit Numbers or UK Sort Codes) and deterministically map them to active successor routing codes using authoritative Central Bank merger directories.

#### 2. Exception Trigger
Clearing network validation failure or directory lookup miss due to a retired, merged, or defunct routing transit number.

#### 3. Input Contract
- Raw payment payload with invalid/retired routing code in `<CdtrAgt><FinInstnId><ClrSysMmbId>`.
- Inbound clearing network NACK error JSON.

#### 4. Evidence Contract
- **4.1 Mandatory Evidence:**
  1. `RETIRED_ROUTING_CODE`: Inbound 9-digit ABA or 6-digit Sort Code (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
  2. `CENTRAL_BANK_MERGER_DIRECTORY`: Official Federal Reserve E-Payments Routing Directory or Bank of England Sorting Code Merger Table (`TrustTier: TIER_2_EXTERNAL_AUTHORITATIVE`).
- **4.2 Conditional Evidence:** `RECEIVING_INSTITUTION_ACTIVE_STATUS`: Active node reachability on target rail (`TrustTier: TIER_2`).
- **4.3 Optional Evidence:** Historical routing code substitutions (`TrustTier: TIER_4`).
- **4.4 Evidence Trust Tier:** Tier 1 (Raw Payload), Tier 2 (Federal Reserve / Bank of England Directory).
- **4.5 Evidence Authority:** Federal Reserve Reg J / Fedwire Directory / BoE Directory (proves legal bank succession; **does NOT prove individual client account transfer**).
- **4.6 Freshness:** Daily/weekly directory sync (`BANK_CONFIG_REQUIRED`).
- **4.7 Evidence Identity:** Retired Routing Transit Number.
- **4.8 Evidence Provenance:** Acquired via Central Bank Reference Data Connector.
- **4.9 Missing Evidence Behavior:** If retired routing code has no entry in the official merger table, set $E_{\text{suff}} = \text{False}$ and route to Ops.
- **4.10 Contradictory Evidence Behavior:** If merger directory contains split successor institutions (1:N mapping), immediately set $R_{\text{uniq}} = \text{False}$ and route to Disambiguation.

#### 5. Resolution Contract
- **5.1 Root Cause:** Payer used outdated bank routing number for an institution that underwent corporate acquisition or merger.
- **5.2 Candidate Generation:** Look up retired routing number in authoritative merger table; extract active successor routing code.
- **5.3 Deterministic Logic:** Successor mapping from 1:1 merger table entry.
- **5.4 Candidate Ranking:** N/A (1:1 deterministic mapping).
- **5.5 Uniqueness Rule:** Exactly ONE active successor routing code exists ($R_{\text{uniq}} = \text{True}$).
- **5.6 Ambiguity Handling:** If retired entity split into multiple branch routing codes, set $R_{\text{uniq}} = \text{False}$ and route to human operations.
- **5.7 Invalid Candidate Handling:** If successor routing code fails national checksum, candidate marked `INVALID` ($R_{\text{det}} = \text{False}$).

#### 6. Authority / Validation Contract
- **6.1 Structural Validation:** Validate target routing format (9-digit string for US, 6-digit string for UK).
- **6.2 Mathematical Validation:** 9-digit ABA Mod-10 Checksum:
  $$3(d_1+d_4+d_7) + 7(d_2+d_5+d_8) + (d_3+d_6+d_9) \equiv 0 \pmod{10}$$
- **6.3 Scheme Validation:** FedLine / Fedwire / CHAPS directory active reachability check.
- **6.4 External Authority:** Federal Reserve E-Payments Directory attestation (validates successor bank routing code under $V_{\text{auth}}$).
- **6.5 Bank Authority:** N/A (External clearing network routing authority).
- **6.6 Current-State Validation:** Confirm successor institution is active on requested clearing rail.
- **6.7 Contradiction Handling:** If successor institution is sanctioned, trip Compliance Gate ($C_{\text{comp}} = \text{FAIL}$).

#### 7. STP Policy Contract
- **7.1 STP Allowed?:** YES (Group 1 Autonomous STP Capable subject to Bank Policy).
- **7.2 Required Policy Conditions:** Successor routing code verified active in live directory; 1:1 merger entry.
- **7.3 Compliance Conditions:** Successor financial institution screened for sanctions ($C_{\text{comp}} = \text{PASS}$).
- **7.4 Monetary Threshold:** `BANK_CONFIG_REQUIRED` (`DEMO_ONLY_DEFAULT — NOT PRODUCTION POLICY: $1,000,000 USD`).
- **7.5 Corridor Conditions:** Active domestic clearing rails (Fedwire, CHIPS, CHAPS).
- **7.6 Maker-Checker:** Bypassed for verified 1:1 merger mapping; required if merger ambiguous.
- **7.7 HITL Conditions:** Triggered if retired code is not in merger directory or maps to multiple entities.
- **7.8 Execution Preconditions:** Target clearing rail operational ($X_{\text{pre}} = \text{True}$).

#### 8. STP Predicate Evaluation
```
E_suff = True (Retired code and Central Bank Merger Directory verified)
R_det  = True (Deterministic successor mapping derived)
R_uniq = True (1:1 single active successor)
V_det  = True (9-digit ABA Mod-10 checksum valid)
V_auth = True (Federal Reserve Merger Directory verification confirmed)
P_bank = True (Amount <= Bank policy ceiling; fails closed if unconfigured)
C_comp = True (Successor institution sanctions screening PASS)
X_pre  = True (FedLine/CHAPS route operational)
---------------------------------------------------------
STP_ELIGIBLE = True -> Emit Repaired Routing XML to Bank Output Port (Subject to Level 2 Production Gating)
```

#### 9. Output Contract
Repaired ISO 20022 XML payload containing active successor routing code in `<ClrSysMmbId><MmbId>`.

#### 10. Bank Handoff Contract
Serialized XML payload written to Bank Output Port with SHA-256 integrity receipt.

#### 11. Audit / Provenance Requirements
Log retired routing code, successor routing code, merger directory release date, and stage transitions in Audit Ledger.

#### 12. Failure States
`MERGER_NOT_FOUND_SUSPENSE` $\to$ `SPLIT_MERGER_DISAMBIGUATION` $\to$ `CHECKSUM_FAILED` $\to$ `SANCTIONED_BANK_HOLD`.

#### 13. Security Requirements
Ensure routing directory updates are cryptographically authenticated from Central Bank source.

#### 14. Test Requirements
1. Happy path: Merged US bank ABA mapped to active successor with valid Mod-10 checksum.
2. Happy path: Retired UK Sort Code mapped to successor Sort Code.
3. Negative: Retired routing code not in merger directory halts and routes to Ops.
4. Negative: 1:N split merger routes to Disambiguation ($R_{\text{uniq}} = \text{False}$).
5. Adversarial: Corrupted merger entry failing Mod-10 checksum rejected immediately.

#### 15. Phase 1 Reuse
`ResolutionEngine`, `AuthorityValidationEngine`, `EvidenceSTPEvaluator`, `FolderOutputAdapter`, `AuditService`.

#### 16. New Phase 2 Capability
`CentralBankMergerDirectoryAdapter` (P0 platform component).

#### 17. External Dependency
Federal Reserve E-Payments Routing Directory / Bank of England Sort Code Directory.

#### 18. Bank Discovery Dependency
Central Bank directory update frequency and local caching policy.

#### 19. Open Questions
Real-time FedLine directory API connectivity vs local batch table sync (`BANK_DISCOVERY_REQUIRED`).

#### 20. Implementation & Production STP Status
- **Platform Implementation Status:** **PLATFORM IMPLEMENTATION READY WITH BANK CONDITIONS (Phase 2B Slice 5)**.
- **Production STP Status:** **BLOCKED / NOT ENABLED** (Gated pending live Central Bank directory sync).

---

### PROFILE: `DQ-02` — `INVALID_BIC`

#### 1. Business Purpose
Normalize and correct invalid or inactive SWIFT Business Identifier Codes (BICs) by standardizing 8-character BICs to 11 characters (`XXX` head office) or replacing inactive branch BICs with active successor head-office BICs using the official SWIFTRef directory.

#### 2. Exception Trigger
SWIFT network NACK (`N10` / `N03`) or directory lookup failure indicating BIC does not exist, is inactive, or has incorrect format.

#### 3. Input Contract
- Raw payment payload with invalid/inactive `<BICFI>`.
- Inbound SWIFT NACK error JSON.

#### 4. Evidence Contract
- **4.1 Mandatory Evidence:**
  1. `INBOUND_BIC_STRING`: Inbound 8 or 11 character BIC (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
  2. `SWIFTREF_DIRECTORY_ENTRY`: Official ISO 9362 SWIFTRef Directory record (`TrustTier: TIER_2_EXTERNAL_AUTHORITATIVE`).
- **4.2 Conditional Evidence:** `RAIL_REACHABILITY_STATUS`: Target rail connectivity (SWIFT CBPR+, TARGET2, CHAPS) for the specific currency (`TrustTier: TIER_2`).
- **4.3 Optional Evidence:** Historical routing logs for counterparty BIC (`TrustTier: TIER_4`).
- **4.4 Evidence Trust Tier:** Tier 1 (Raw Payload), Tier 2 (SWIFTRef / ISO 9362).
- **4.5 Evidence Authority:** ISO 9362 / SWIFTRef Directory (proves institutional registration and head-office status under $V_{\text{auth}}$; **does NOT prove branch-specific currency clearing agreements**).
- **4.6 Freshness:** Monthly full directory sync with daily delta updates (`BANK_CONFIG_REQUIRED`).
- **4.7 Evidence Identity:** BIC String + Target Currency.
- **4.8 Evidence Provenance:** Acquired via SWIFTRef Directory Connector.
- **4.9 Missing Evidence Behavior:** If BIC is completely absent from SWIFTRef, set $E_{\text{suff}} = \text{False}$ and route to Operations.
- **4.10 Contradictory Evidence Behavior:** If SWIFTRef lists BIC as active but clearing rail reports unreachable, halt and route to Disambiguation.

#### 5. Resolution Contract
- **5.1 Root Cause:** Payer supplied 8-character BIC requiring `XXX` suffix, or used closed sub-branch BIC.
- **5.2 Candidate Generation:**
  - Case 1 (8-char BIC): Append `XXX` default head-office branch code.
  - Case 2 (Inactive Branch): Map closed branch to active institution head-office BIC (`INSTUS33XXX`).
- **5.3 Deterministic Logic:** BIC8-to-BIC11 normalizer or SWIFTRef successor mapping.
- **5.4 Candidate Ranking:** N/A (1:1 deterministic mapping).
- **5.5 Uniqueness Rule:** Exactly ONE active successor BIC derived ($R_{\text{uniq}} = \text{True}$).
- **5.6 Ambiguity Handling:** If institution was split or successor ambiguous, set $R_{\text{uniq}} = \text{False}$ and route to HITL.
- **5.7 Invalid Candidate Handling:** If candidate fails ISO 9362 regex, mark `INVALID` ($R_{\text{det}} = \text{False}$).

#### 6. Authority / Validation Contract
- **6.1 Structural Validation:** Validate against ISO 9362 regex: `^[A-Z]{6}[A-Z2-9][A-NP-Z0-9]([A-Z0-9]{3})?$`.
- **6.2 Mathematical Validation:** ISO 9362 country code (positions 5-6) must match active ISO 3166-1 alpha-2.
- **6.3 Scheme Validation:** SWIFT CBPR+ directory reachability check.
- **6.4 External Authority:** SWIFTRef Directory verification confirming institutional active status ($V_{\text{auth}} = \text{True}$).
- **6.5 Bank Authority:** N/A (External messaging directory authority).
- **6.6 Current-State Validation:** Confirm BIC is reachable on requested clearing rail for transaction currency.
- **6.7 Contradiction Handling:** If institution is on financial sanctions list, trip Compliance Gate ($C_{\text{comp}} = \text{FAIL}$).

#### 7. STP Policy Contract
- **7.1 STP Allowed?:** YES (Group 2 Conditionally Permissible STP subject to Bank Policy).
- **7.2 Required Policy Conditions:** Successor BIC verified active in SWIFTRef and reachable on target rail.
- **7.3 Compliance Conditions:** Successor BIC screened for financial sanctions ($C_{\text{comp}} = \text{PASS}$).
- **7.4 Monetary Threshold:** `BANK_CONFIG_REQUIRED` (`DEMO_ONLY_DEFAULT — NOT PRODUCTION POLICY: $25,000 USD`).
- **7.5 Corridor Conditions:** Active SWIFT corridors.
- **7.6 Maker-Checker:** Bypassed for standard 8-to-11 char normalization under configured policy limit; required if amount $\ge \text{threshold}$ or branch replacement.
- **7.7 HITL Conditions:** Triggered if BIC is unknown or rail unreachable.
- **7.8 Execution Preconditions:** SWIFT clearing gateway operational ($X_{\text{pre}} = \text{True}$).

#### 8. STP Predicate Evaluation
```
E_suff = True (Inbound BIC, SWIFTRef record & rail reachability verified)
R_det  = True (Deterministic 8-to-11 / Head-Office mapping derived)
R_uniq = True (Single active successor BIC)
V_det  = True (ISO 9362 format regex valid)
V_auth = True (SWIFTRef Directory active status verified)
P_bank = True (Amount <= Bank policy ceiling; fails closed if unconfigured)
C_comp = True (Financial institution sanctions screening PASS)
X_pre  = True (SWIFT gateway route operational)
---------------------------------------------------------
STP_ELIGIBLE = True -> Emit Repaired BIC XML to Bank Output Port (Subject to Level 2 Production Gating)
```

#### 9. Output Contract
Repaired ISO 20022 XML payload containing active 11-character BIC in `<CdtrAgt><FinInstnId><BICFI>`.

#### 10. Bank Handoff Contract
Serialized XML payload written to Bank Output Port with SHA-256 integrity receipt.

#### 11. Audit / Provenance Requirements
Log original BIC, repaired BIC, SWIFTRef version, rail reachability status, and stage transitions in Audit Ledger.

#### 12. Failure States
`UNKNOWN_BIC_SUSPENSE` $\to$ `RAIL_UNREACHABLE_HOLD` $\to$ `POLICY_THRESHOLD_BREACH` $\to$ `SANCTIONS_HOLD`.

#### 13. Security Requirements
Ensure SWIFTRef database is protected against unauthorized tampering.

#### 14. Test Requirements
1. Happy path: 8-character BIC normalized to 11 characters (`XXX`) and validated.
2. Happy path: Inactive branch BIC replaced with active head-office BIC under configured threshold.
3. Negative: Completely fictitious BIC not in SWIFTRef halts and routes to Ops.
4. Negative: Active BIC unreachable for requested currency routes to Ops.
5. Adversarial: Corrupted BIC with invalid country characters rejected by regex validation.

#### 15. Phase 1 Reuse
`ResolutionEngine`, `AuthorityValidationEngine`, `EvidenceSTPEvaluator`, `FolderOutputAdapter`, `AuditService`.

#### 16. New Phase 2 Capability
`SWIFTRefDirectoryConnector` (P0 platform component).

#### 17. External Dependency
SWIFTRef Global Directory Data Feed / ISO 9362 Registry.

#### 18. Bank Discovery Dependency
SWIFTRef subscription type (API vs Local Database dump) and sync SLA.

#### 19. Open Questions
Currency-specific branch clearing exceptions in correspondent banking (`BANK_DISCOVERY_REQUIRED`).

#### 20. Implementation & Production STP Status
- **Platform Implementation Status:** **PLATFORM IMPLEMENTATION READY WITH BANK CONDITIONS (Phase 2B Slice 6)**.
- **Production STP Status:** **BLOCKED / NOT ENABLED** (Gated pending live SWIFTRef directory integration).

---

## 9. Phase 2C Profile Implementation Contracts

---

### PROFILE: `DQ-01` — `INVALID_IBAN`

#### 1. Business Purpose
Detect and correct invalid International Bank Account Numbers (IBANs) caused by single-character transpositions, check-digit mistypes, or missing country prefixes by combining mathematical solvers with mandatory Tier 1 Bank SSI Master / Confirmation of Payee (CoP) corroboration.

#### 2. Exception Trigger
ISO 7064 MOD-97-10 check digit calculation failure ($r \neq 1$) or clearing network IBAN format rejection.

#### 3. Input Contract
- Raw payment payload with corrupted `<IBAN>` in `<CdtrAcct><Id><IBAN>`.
- Inbound XSD or scheme check digit error JSON.

#### 4. Evidence Contract
- **4.1 Mandatory Evidence:**
  1. `RAW_PAYLOAD_IBAN`: Corrupted IBAN string (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
  2. `ISO_13616_IBAN_REGISTRY`: National IBAN structure and character length specification (`TrustTier: TIER_2_EXTERNAL_AUTHORITATIVE`).
  3. `BANK_SSI_MASTER_RECORD`: Debtor/Creditor verified Standard Settlement Instruction (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
- **4.2 Conditional Evidence:** `CONFIRMATION_OF_PAYEE_TOKEN`: Live CoP / EU VoP matching response (`TrustTier: TIER_2_EXTERNAL_AUTHORITATIVE`).
- **4.3 Optional Evidence:** `HISTORICAL_REPAIR_PATTERN`: Past successful IBAN corrections (`TrustTier: TIER_4`).
- **4.4 Evidence Trust Tier:** Tier 1 (Raw Payload & Bank SSI Master), Tier 2 (ISO 13616 & CoP), Tier 3 (MOD-97 Solver).
- **4.5 Evidence Authority:** 
  - **Mathematical Validity:** ISO 7064 MOD-97-10 (proves checksum syntax only under $V_{\text{det}}$).
  - **Account Ownership Authority:** Bank SSI Master / Core DDA / Confirmation of Payee (**MANDATORY to prove account ownership & active status under $V_{\text{auth}}$**).
- **4.6 Freshness:** Real-time query for CoP / Daily cache for SSI Master (`BANK_CONFIG_REQUIRED`).
- **4.7 Evidence Identity:** Corrupted IBAN + Beneficiary Legal Name + Currency.
- **4.8 Evidence Provenance:** Ingested via Bank Evidence Gateway and verified against Bank SSI Master.
- **4.9 Missing Evidence Behavior:** If Bank SSI Master has no record and CoP is unavailable, set $E_{\text{suff}} = \text{False} \wedge V_{\text{auth}} = \text{False}$ and route to Operations (Zero guessing).
- **4.10 Contradictory Evidence Behavior:** If MOD-97 math candidate contradicts Bank SSI Master record, **Bank SSI Master wins** or routes to Investigation.

#### 5. Resolution Contract
- **5.1 Root Cause:** Data entry error: check-digit mistyped, adjacent digits transposed, or leading zeros omitted.
- **5.2 Candidate Generation:** Execute deterministic ISO 7064 permutation algorithm: generate all possible single-transposition and single-digit substitution permutations that satisfy $\text{MOD-97} = 1$.
- **5.3 Deterministic Logic:** Intersect mathematical candidates with active Bank SSI Master records for the beneficiary name.
- **5.4 Candidate Ranking:** Rank candidate matching Bank SSI Master record as primary.
- **5.5 Uniqueness Rule:** Exactly ONE candidate satisfies BOTH $\text{MOD-97} = 1$ AND Bank SSI Master match ($R_{\text{uniq}} = \text{True}$).
- **5.6 Ambiguity Handling:** If multiple permutations satisfy MOD-97 and no SSI record matches, set $R_{\text{uniq}} = \text{False}$ and route to Disambiguation Worklist.
- **5.7 Invalid Candidate Handling:** If candidate fails national BBAN length or modulus rules, candidate marked `INVALID` ($R_{\text{det}} = \text{False}$).

#### 6. Authority / Validation Contract
- **6.1 Structural Validation:** Validate against ISO 13616 national length and character format regex.
- **6.2 Mathematical Validation:** Full ISO 7064 MOD-97-10 Checksum:
  $$\text{Integer}(\text{rearranged string}) \pmod{97} = 1$$
- **6.3 Scheme Validation:** SWIFTRef IBAN format check.
- **6.4 External Authority:** Confirmation of Payee (CoP / EU VoP) match response.
- **6.5 Bank Authority:** Bank SSI Master attestation confirming beneficiary account ownership ($V_{\text{auth}} = \text{True}$).
- **6.6 Current-State Validation:** Confirm beneficiary account is active and open in core ledger.
- **6.7 Contradiction Handling:** If repaired account is flagged on sanctions watchlist, trip Compliance Gate ($C_{\text{comp}} = \text{FAIL}$).

#### 7. STP Policy Contract
- **7.1 STP Allowed?:** YES (Group 2 Conditionally Permissible STP subject to Bank Policy).
- **7.2 Required Policy Conditions:** MOD-97 = 1 AND exact Bank SSI Master / CoP match verified.
- **7.3 Compliance Conditions:** Full Sanctions & PEP screening on repaired account ($C_{\text{comp}} = \text{PASS}$).
- **7.4 Monetary Threshold:** `BANK_CONFIG_REQUIRED` (`DEMO_ONLY_DEFAULT — NOT PRODUCTION POLICY: $25,000 USD`).
- **7.5 Corridor Conditions:** SEPA, UK Faster Payments, and cross-border SWIFT IBAN corridors.
- **7.6 Maker-Checker:** Bypassed for verified SSI match under policy ceiling; required for amounts $\ge \text{threshold}$ or new counterparties.
- **7.7 HITL Conditions:** Triggered if $N > 1$ candidates or SSI record absent.
- **7.8 Execution Preconditions:** Idempotency lock active ($X_{\text{pre}} = \text{True}$).

#### 8. STP Predicate Evaluation
```
E_suff = True (Raw IBAN, ISO 13616 spec & Bank SSI Master verified)
R_det  = True (Deterministic MOD-97 permutation solver executed)
R_uniq = True (Single unique candidate matching Bank SSI Master)
V_det  = True (ISO 7064 MOD-97 check == 1)
V_auth = True (Bank SSI Master attestation verified)
P_bank = True (Amount <= Bank policy ceiling; fails closed if unconfigured)
C_comp = True (Sanctions/AML screening on repaired account PASS)
X_pre  = True (Idempotency lock active, corridor operational)
---------------------------------------------------------
STP_ELIGIBLE = True -> Emit Repaired IBAN XML to Bank Output Port (Subject to Level 2 Production Gating)
```

#### 9. Output Contract
Repaired ISO 20022 XML payload containing verified IBAN in `<CdtrAcct><Id><IBAN>`.

#### 10. Bank Handoff Contract
Serialized XML payload written to Bank Output Port with SHA-256 integrity receipt.

#### 11. Audit / Provenance Requirements
Log corrupted IBAN, repaired IBAN, MOD-97 calculation proof, SSI Master record ID, and stage transitions in Audit Ledger.

#### 12. Failure States
`MOD97_AMBIGUITY_SUSPENSE` ($N>1$) $\to$ `SSI_NOT_FOUND_HOLD` $\to$ `POLICY_THRESHOLD_BREACH` $\to$ `SANCTIONS_HOLD`.

#### 13. Security Requirements
Ensure raw IBANs are masked in UI logs and detokenized securely at outbound dispatch boundary.

#### 14. Test Requirements
1. Happy path: Single transposition repaired, passes MOD-97, matches Bank SSI, executes STP under policy ceiling.
2. Failure: MOD-97 solver produces 2 valid mathematical permutations $\implies$ $R_{\text{uniq}} = \text{False}$, routes to Disambiguation.
3. Failure: Valid MOD-97 IBAN but absent from Bank SSI Master $\implies$ $E_{\text{suff}} = \text{False} \wedge V_{\text{auth}} = \text{False}$, routes to Ops.
4. Failure: Amount exceeds configured policy ceiling $\implies$ $P_{\text{bank}} = \text{False}$, routes to Maker-Checker.
5. Adversarial: Corrupted IBAN matching a sanctioned entity is blocked by $C_{\text{comp}}$ gate.

#### 15. Phase 1 Reuse
`EvidenceSufficiencyEngine`, `EvidenceSTPEvaluator`, `STPPolicyConfig`, `FolderOutputAdapter`, `AuditService`.

#### 16. New Phase 2 Capability
`ISO7064Mod97Solver` & `BankSSIMasterAdapter` (P0 platform component).

#### 17. External Dependency
ISO 13616 IBAN Registry / Pay.UK CoP / EU VoP Gateway.

#### 18. Bank Discovery Dependency
Bank SSI Master API interface, CoP gateway credentials, STP monetary limit.

#### 19. Open Questions
Bank policy on Confirmation of Payee name matching tolerance (Exact vs Close Match) (`BANK_CONFIG_REQUIRED`).

#### 20. Implementation & Production STP Status
- **Platform Implementation Status:** **PLATFORM IMPLEMENTATION READY WITH BANK CONDITIONS (Phase 2C Slice 7)**.
- **Production STP Status:** **BLOCKED / NOT ENABLED** (Gated pending Bank SSI Master & CoP Gateway integration).

---

### PROFILE: `DQ-06` — `MISSING_PURPOSE_CODE`

#### 1. Business Purpose
Classify and populate mandatory ISO 20022 External Purpose Codes (`<Purp><Cd>`) from unstructured remittance text (`<RmtInf><Ustrd>`) for cross-border and statutory reporting corridors under bank-configured commercial trade policy.

#### 2. Exception Trigger
Inbound validation failure or Central Bank regulatory rejection due to missing mandatory purpose code in cross-border payment instruction.

#### 3. Input Contract
- Raw payment payload with missing `<Purp>` tag and non-empty `<RmtInf><Ustrd>`.
- Inbound clearing network BoP validation error JSON.

#### 4. Evidence Contract
- **4.1 Mandatory Evidence:**
  1. `REMITTANCE_UNSTRUCTURED_TEXT`: Unstructured remittance advice string (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
  2. `ISO_EXTERNAL_PURPOSE_CODE_SET`: Official ISO 20022 External Code Set for Purpose (`TrustTier: TIER_2_EXTERNAL_AUTHORITATIVE`).
  3. `BANK_TRADE_CORRIDOR_POLICY`: Bank commercial trade policy defining authorized purpose code mappings and amount limits (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
- **4.2 Conditional Evidence:** `CENTRAL_BANK_BOP_MAPPING_RULES`: Statutory Balance of Payments classification rules (`TrustTier: TIER_2`).
- **4.3 Optional Evidence:** `HISTORICAL_PURPOSE_ASSIGNMENTS`: Past purpose codes for recurring payor (`TrustTier: TIER_4`).
- **4.4 Evidence Trust Tier:** Tier 1 (Remittance Advice & Bank Policy), Tier 2 (ISO Code Set / BoP Rules), Tier 3 (Keyword Classifier).
- **4.5 Evidence Authority:** 
  - **Technical Code Set Authority:** ISO 20022 External Purpose Code List / Central Bank BoP Rules (proves code membership in active standard under $V_{\text{det}}$; **does NOT prove underlying economic intent**).
  - **Commercial / Trade Authority:** Bank Trade Corridor Policy (`BANK_CONFIG_REQUIRED`; establishes operational authorization under $V_{\text{auth}}$).
- **4.6 Freshness:** Static ISO code catalog / Quarterly statutory update.
- **4.7 Evidence Identity:** Remittance Text + Corridor Currency.
- **4.8 Evidence Provenance:** Parsed from inbound payment payload.
- **4.9 Missing Evidence Behavior:** If remittance text is empty, contains no recognized keywords, or bank trade policy is unconfigured, set $E_{\text{suff}} = \text{False} \wedge V_{\text{auth}} = \text{False}$ and route to Operations.
- **4.10 Contradictory Evidence Behavior:** If remittance text contains conflicting keywords (e.g. "SALARY AND DIVIDEND"), set $R_{\text{uniq}} = \text{False}$ and route to Disambiguation.

#### 5. Resolution Contract
- **5.1 Root Cause:** Payer omitted mandatory 4-character purpose code during corporate file preparation.
- **5.2 Candidate Generation:** Execute semantic classification / keyword rules (e.g., "SALARY/PAYROLL" $\to$ `SALA`, "SUPPLIER INVOICE" $\to$ `GDSV`, "DIVIDEND" $\to$ `DIVI`, "PENSION" $\to$ `PENS`).  
  **Hardening Rule:** Keyword matching is strictly a **Semantic Candidate Generator**. It does NOT establish legal economic purpose authority.
- **5.3 Deterministic Logic:** Deterministic dictionary rule match against ISO 20022 purpose code set.
- **5.4 Candidate Ranking:** Rank candidate matches based on rule specificity.
- **5.5 Uniqueness Rule:** Exactly ONE purpose code matches remittance text ($R_{\text{uniq}} = \text{True}$).
- **5.6 Ambiguity Handling:** If text is vague (e.g. "PAYMENT") or matches multiple codes, set $R_{\text{uniq}} = \text{False}$ and route to Operations.
- **5.7 Invalid Candidate Handling:** If derived code is deprecated in ISO code list, mark `INVALID` ($R_{\text{det}} = \text{False}$).

#### 6. Authority / Validation Contract
- **6.1 Structural Validation:** Validate against ISO 20022 4-character alphanumeric uppercase code format (`^[A-Z]{4}$`).
- **6.2 Mathematical Validation:** N/A.
- **6.3 Scheme Validation:** Membership verification against active ISO 20022 External Purpose Code Set ($V_{\text{det}} = \text{True}$).
- **6.4 External Authority:** ISO 20022 External Code Set confirms that candidate code is valid and active under $V_{\text{det}}$.
- **6.5 Bank Authority ($V_{\text{auth}}$):** Boolean evaluation rule:
  $$V_{\text{auth}} = \begin{cases} \text{True} & \text{if } \text{bank\_policy.is\_purpose\_population\_authorized}(\text{corridor}, \text{derived\_code}) == \text{True} \\ \text{False} & \text{otherwise (unconfigured, unauthorized corridor, or unverified)} \end{cases}$$
- **6.6 Current-State Validation:** Confirm purpose code is active in current regulatory release.
- **6.7 Contradiction Handling:** If purpose code implies sanctioned goods, trip Compliance Gate ($C_{\text{comp}} = \text{FAIL}$).

#### 7. STP Policy Contract
- **7.1 STP Allowed?:** YES (Group 2 Conditionally Permissible STP subject to Bank Policy).
- **7.2 Required Policy Conditions:** Unambiguous keyword match; purpose code active in ISO code set; corridor authorized under bank commercial trade policy.
- **7.3 Compliance Conditions:** Purpose code screened against sanctions keyword red flags ($C_{\text{comp}} = \text{PASS}$).
- **7.4 Monetary Threshold:** `BANK_CONFIG_REQUIRED` (`DEMO_ONLY_DEFAULT — NOT PRODUCTION POLICY: $25,000 USD`).
- **7.5 Corridor Conditions:** Permitted for approved commercial trade corridors (`BANK_CONFIG_REQUIRED`).
- **7.6 Maker-Checker:** Bypassed for verified keyword matches under configured policy limit; required for amounts $\ge \text{threshold}$.
- **7.7 HITL Conditions:** Triggered if remittance text is ambiguous, unclassified, or exceeds policy ceiling.
- **7.8 Execution Preconditions:** ISO 20022 XML document envelope intact ($X_{\text{pre}} = \text{True}$).

#### 8. STP Predicate Evaluation
```
E_suff = True (Remittance text, ISO Purpose Code Set & Bank Trade Policy verified)
R_det  = True (Deterministic keyword dictionary mapping executed)
R_uniq = True (Single unambiguous purpose code derived)
V_det  = True (Conforms to 4-character ISO purpose format)
V_auth = True (ISO External Code Set valid + Bank Policy authorizes commercial trade category)
P_bank = True (Amount <= Bank policy ceiling; fails closed if unconfigured)
C_comp = True (Sanctions screening PASS)
X_pre  = True (XML payload structure operational)
---------------------------------------------------------
STP_ELIGIBLE = True -> Emit Repaired Purpose XML to Bank Output Port (Subject to Level 2 Production Gating)
```

#### 9. Output Contract
Repaired ISO 20022 XML payload containing populated `<Purp><Cd>` tag.

#### 10. Bank Handoff Contract
Serialized XML payload written to Bank Output Port with SHA-256 integrity receipt.

#### 11. Audit / Provenance Requirements
Log raw remittance text, mapped purpose code, dictionary rule ID, and stage transitions in Audit Ledger.

#### 12. Failure States
`AMBIGUOUS_REMITTANCE_SUSPENSE` $\to$ `PURPOSE_CODE_DEPRECATED` $\to$ `POLICY_THRESHOLD_BREACH`.

#### 13. Security Requirements
Ensure remittance parser is sandboxed against prompt injection or script execution.

#### 14. Test Requirements
1. Happy path: Single candidate + valid code set + bank policy authorization satisfied $\implies$ STP proceeds under policy ceiling.
2. Failure (Uncorroborated): Keyword candidate generated but corridor is not authorized under bank trade policy $\implies$ $V_{\text{auth}} = \text{False} \implies$ halts and routes to Ops.
3. Failure (Ambiguity): Remittance containing "SALARY AND DIVIDEND" produces multiple plausible candidates $\implies$ $R_{\text{uniq}} = \text{False} \implies$ routes to Disambiguation.
4. Failure (Threshold): Amount exceeds configured policy ceiling $\implies$ $P_{\text{bank}} = \text{False} \implies$ routes to Maker-Checker.
5. Adversarial: Malicious prompt injection in remittance text ignored; parser extracts clean code.

#### 15. Phase 1 Reuse
`ResolutionEngine`, `AuthorityValidationEngine`, `EvidenceSTPEvaluator`, `FolderOutputAdapter`, `AuditService`.

#### 16. New Phase 2 Capability
`ISOPurposeCodeMapper` (P0 platform component).

#### 17. External Dependency
ISO 20022 External Purpose Code Catalog.

#### 18. Bank Discovery Dependency
Bank-specific keyword dictionary extensions and corridor exemption rules.

#### 19. Open Questions
National Central Bank Balance of Payments reporting threshold variations (`BANK_DISCOVERY_REQUIRED`).

#### 20. Implementation & Production STP Status
- **Platform Implementation Status:** **PLATFORM IMPLEMENTATION READY WITH BANK CONDITIONS (Phase 2C Slice 8)**.
- **Production STP Status:** **BLOCKED / NOT ENABLED** (Gated pending bank trade corridor policy & keyword dictionary configuration).

---

### PROFILE: `ST-01` — `RETURNED_PAYMENT`

#### 1. Business Purpose
Ingest inbound return payment messages (`pacs.004`), reconcile them with the original outbound transaction (`pacs.008`) via UETR matching, and prepare a deterministic re-credit handoff instruction for the Bank Payment Hub and Core DDA without directly posting ledger entries.

#### 2. Exception Trigger
Inbound `pacs.004` Payment Return message received from correspondent bank or clearing network with return reason code (e.g. `AC01`, `AC04`, `RC01`, `MD07`).

#### 3. Input Contract
- Inbound `pacs.004` XML return payload.
- Transport metadata from clearing gateway.

#### 4. Evidence Contract
- **4.1 Mandatory Evidence:**
  1. `INBOUND_PACS004_PAYLOAD`: Inbound return XML (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
  2. `ORIGINAL_PACS008_RECORD`: Original outbound payment record matching `<OrgnlUETR>` (`TrustTier: TIER_1`).
  3. `ORIGINAL_DEBTOR_DDA_ACCOUNT`: Verified debtor account from original payment (`TrustTier: TIER_1`).
- **4.2 Conditional Evidence:** `RETURN_REASON_CODE`: External return code specification (`TrustTier: TIER_2`).
- **4.3 Optional Evidence:** Historical return statistics for beneficiary corridor (`TrustTier: TIER_4`).
- **4.4 Evidence Trust Tier:** Tier 1 (Bank Core Ledger & Original Payment Store), Tier 2 (SWIFT Return Rules).
- **4.5 Evidence Authority:** Bank Core Settlement Ledger & SWIFT CBPR+ Return Processing Rules (proves return reconciliation; **PeX produces re-credit instruction, Bank executes accounting**).
- **4.6 Freshness:** Real-time upon `pacs.004` ingestion.
- **4.7 Evidence Identity:** Inbound `pacs.004` UETR + Original `pacs.008` UETR.
- **4.8 Evidence Provenance:** Ingested via Bank Inbound Transport Adapter and verified against Core Ledger.
- **4.9 Missing Evidence Behavior:** If original `pacs.008` UETR cannot be found in settlement ledger, set $E_{\text{suff}} = \text{False}$ and route to Recon Desk.
- **4.10 Contradictory Evidence Behavior:** If returned principal amount exceeds original payment amount, halt and route to Investigation.

#### 5. Resolution Contract
- **5.1 Root Cause:** Receiving bank or beneficiary returned payment due to closed account, incorrect details, or regulatory refusal.
- **5.2 Candidate Generation:** Reconcile original debtor DDA account; construct structured `BANK_RE_CREDIT_INSTRUCTION` payload.
- **5.3 Deterministic Logic:** 1:1 UETR match $\implies$ Generate re-credit instruction to original debtor account with return reason metadata.
- **5.4 Candidate Ranking:** N/A (1:1 deterministic reconciliation).
- **5.5 Uniqueness Rule:** Exactly ONE original debtor account on file for the matched UETR ($R_{\text{uniq}} = \text{True}$).
- **5.6 Ambiguity Handling:** If original payment was funded from multiple source accounts, route to Operations.
- **5.7 Invalid Candidate Handling:** If debtor account has since been closed, route to `ST-02: ACCOUNT_CLOSED` sub-profile.

#### 6. Authority / Validation Contract
- **6.1 Structural Validation:** Validate inbound `pacs.004` schema and outbound re-credit JSON schema.
- **6.2 Mathematical Validation:** Return principal amount $\le$ Original payment principal amount.
- **6.3 Scheme Validation:** SWIFT CBPR+ Return reason code validation.
- **6.4 External Authority:** SWIFT CBPR+ Return standards.
- **6.5 Bank Authority:** Bank Core Settlement Ledger attestation confirming original debit ($V_{\text{auth}} = \text{True}$).
- **6.6 Current-State Validation:** Confirm original debtor DDA account is active and open.
- **6.7 Contradiction Handling:** If return remittance contains sanctions red flags, trip Compliance Gate ($C_{\text{comp}} = \text{FAIL}$).

#### 7. STP Policy Contract
- **7.1 STP Allowed?:** YES (Group 1 Autonomous STP Capable for Standard Returns subject to Bank Policy).
- **7.2 Required Policy Conditions:** Original UETR matches 100%; return principal amount $\le$ original amount; debtor DDA open.
- **7.3 Compliance Conditions:** Return narrative screened for sanctions flags ($C_{\text{comp}} = \text{PASS}$).
- **7.4 Monetary Threshold:** `BANK_CONFIG_REQUIRED` (`DEMO_ONLY_DEFAULT — NOT PRODUCTION POLICY: $1,000,000 USD`).
- **7.5 Corridor Conditions:** All active payment corridors.
- **7.6 Maker-Checker:** Bypassed for verified UETR reconciliation; required if original transaction unconfirmed.
- **7.7 HITL Conditions:** Triggered if UETR missing or debtor account closed.
- **7.8 Execution Preconditions:** Core DDA posting adapter operational ($X_{\text{pre}} = \text{True}$).

#### 8. STP Predicate Evaluation
```
E_suff = True (Inbound pacs.004, original pacs.008 & debtor DDA verified)
R_det  = True (Deterministic re-credit handoff instruction derived)
R_uniq = True (Single original debtor account)
V_det  = True (pacs.004 schema and amount valid)
V_auth = True (Core Settlement Ledger attestation verified)
P_bank = True (Amount <= Bank policy ceiling; fails closed if unconfigured)
C_comp = True (Sanctions screening on return narrative PASS)
X_pre  = True (Core DDA posting route operational)
---------------------------------------------------------
STP_ELIGIBLE = True -> Emit Re-Credit Handoff to Bank Payment Hub (Subject to Level 2 Production Gating)
```

#### 9. Output Contract
Structured `BANK_RE_CREDIT_INSTRUCTION` JSON/XML containing original UETR, debtor DDA account, returned amount, return reason code, and audit digest.

#### 10. Bank Handoff Contract
Handoff to Bank Payment Hub / Core DDA; **Bank executes accounting debit/credit postings**.

#### 11. Audit / Provenance Requirements
Log `pacs.004` UETR, original `pacs.008` UETR, returned amount, return reason code, debtor DDA, and stage transitions in Audit Ledger.

#### 12. Failure States
`ORIGINAL_UETR_NOT_FOUND` $\to$ `DEBTOR_ACCOUNT_CLOSED` $\to$ `AMOUNT_OVERFLOW_SUSPENSE` $\to$ `COMPLIANCE_HOLD`.

#### 13. Security Requirements
Prevent unauthorized modification of destination debtor account during re-credit handoff.

#### 14. Test Requirements
1. Happy path: Inbound `pacs.004` matches original `pacs.008` UETR; generates clean re-credit handoff payload.
2. Failure: `pacs.004` with unknown UETR halts and routes to Recon Desk ($E_{\text{suff}} = \text{False}$).
3. Failure: Return amount greater than original payment amount fails mathematical validation.
4. Failure: Debtor account closed since original wire routes to `ST-02` workflow.
5. Adversarial: Return payload with tampered debtor account rejected by Core Ledger match.

#### 15. Phase 1 Reuse
`EvidenceSufficiencyEngine`, `EvidenceSTPEvaluator`, `FolderOutputAdapter`, `AuditService`.

#### 16. New Phase 2 Capability
`pacs004ReturnReconciler` (P0 platform component).

#### 17. External Dependency
SWIFT CBPR+ `pacs.004` Return XML Schema.

#### 18. Bank Discovery Dependency
Bank accounting SOP for return fee deductions and Nostro mirror ledger accounts.

#### 19. Open Questions
Accounting treatment of foreign exchange spread differences on cross-currency returns (`BANK_DISCOVERY_REQUIRED`).

#### 20. Implementation & Production STP Status
- **Platform Implementation Status:** **PLATFORM IMPLEMENTATION READY WITH BANK CONDITIONS (Phase 2C Slice 9)**.
- **Production STP Status:** **BLOCKED / NOT ENABLED** (Gated pending Core DDA re-credit posting interface integration).

---

### PROFILE: `CO-04` — `RESTRICTED_CORRIDOR`

#### 1. Business Purpose
Detect payments attempting to transact with comprehensively sanctioned, embargoed, or restricted geopolitical jurisdictions (e.g. OFAC comprehensive embargoes) and execute mandatory, deterministic statutory blocking/rejection via `pacs.002` reject instructions without human bypass.

#### 2. Exception Trigger
Sanctions screening or routing engine detection of comprehensive embargoed country code (ISO 3166-1 alpha-2) in debtor, creditor, intermediary bank, or destination country fields.

#### 3. Input Contract
- Raw payment payload with ISO 3166-1 country code in `<Cdtr><PstlAdr><Ctry>`, `<Dbtr><PstlAdr><Ctry>`, or `<CdtrAgt><FinInstnId>`.
- Inbound clearing network transaction.

#### 4. Evidence Contract
- **4.1 Mandatory Evidence:**
  1. `INBOUND_PAYLOAD_COUNTRIES`: All extracted ISO 3166-1 country codes from transaction (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
  2. `OFAC_COMPREHENSIVE_SANCTIONS_LIST`: Authoritative statutory list of comprehensively embargoed jurisdictions (`TrustTier: TIER_2_EXTERNAL_AUTHORITATIVE`).
  3. `BANK_CORRIDOR_RESTRICTION_MATRIX`: Bank compliance corridor policy table (`TrustTier: TIER_1_BANK_AUTHORITATIVE`).
- **4.2 Conditional Evidence:** `SPECIFIC_OFAC_LICENSE`: General or specific OFAC license exception on file (`TrustTier: TIER_1`).
- **4.3 Optional Evidence:** None.
- **4.4 Evidence Trust Tier:** Tier 1 (Raw Payload & Bank Corridor Policy), Tier 2 (OFAC / EU Statutory Embargo Lists).
- **4.5 Evidence Authority:** OFAC Comprehensive Sanctions Programs / UN & EU Statutory Embargoes (proves statutory illegality of transfer; **mandates blocking/rejection under $V_{\text{auth}}$**).
- **4.6 Freshness:** Daily statutory sanctions sync (`BANK_CONFIG_REQUIRED`).
- **4.7 Evidence Identity:** Extracted ISO 3166 Country Code + Corridor Identifier.
- **4.8 Evidence Provenance:** Ingested via Bank Compliance Gateway and verified against Statutory Sanctions Matrix.
- **4.9 Missing Evidence Behavior:** If destination country cannot be determined from payload, set $E_{\text{suff}} = \text{False}$ and route to Compliance Desk.
- **4.10 Contradictory Evidence Behavior:** If bank corridor policy permits but statutory OFAC list prohibits, **Statutory OFAC list strictly overrides**.

#### 5. Resolution Contract
- **5.1 Root Cause:** Payment instruction routed to or originating from a comprehensively embargoed territory under statutory sanctions.
- **5.2 Candidate Generation:** Generate deterministic statutory rejection / auto-block directive (`pacs.002` reject with reason code `RR04` / `NARR`).
- **5.3 Deterministic Logic:** Exact ISO 3166-1 country code match against active Embargo List $\implies$ **Deterministic Auto-Block / Reject Directive**.
- **5.4 Candidate Ranking:** N/A (Binary statutory determination).
- **5.5 Uniqueness Rule:** Exactly ONE rejection directive derived ($R_{\text{uniq}} = \text{True}$).
- **5.6 Ambiguity Handling:** If a specific OFAC license is claimed in `<RmtInf>`, set $R_{\text{uniq}} = \text{False}$ and route to MLRO / Compliance Officer.
- **5.7 Invalid Candidate Handling:** N/A.

#### 6. Authority / Validation Contract
- **6.1 Structural Validation:** Validate outbound `pacs.002` XML reject payload schema.
- **6.2 Mathematical Validation:** ISO 3166-1 alpha-2 2-letter uppercase format check.
- **6.3 Scheme Validation:** SWIFT CBPR+ rejection code `RR04` (Regulatory Reason).
- **6.4 External Authority:** OFAC / Statutory Embargo List attestation ($V_{\text{auth}} = \text{True}$).
- **6.5 Bank Authority:** Bank Compliance Corridor Matrix attestation.
- **6.6 Current-State Validation:** Confirm country is currently listed on active embargo registry.
- **6.7 Contradiction Handling:** Compliance Gate explicitly evaluates to FAIL ($C_{\text{comp}} = \text{FAIL}$), triggering the Auto-Block workflow.

#### 7. STP Policy Contract
- **7.1 STP Allowed?:** YES (Group 2 Conditionally Permissible — **MANDATORY STATUTORY AUTO-BLOCK**).
- **7.2 Required Policy Conditions:** Country match on embargo list; zero OFAC license on file.
- **7.3 Compliance Conditions:** Triggers automated rejection / freezing directive ($C_{\text{comp}} = \text{FAIL}$).
- **7.4 Monetary Threshold:** \$0.00 (Zero monetary threshold; applies universally to all amounts).
- **7.5 Corridor Conditions:** Comprehensive embargoed territories.
- **7.6 Maker-Checker:** Bypassed for statutory rejection; required if asset freezing / escrow order mandated.
- **7.7 HITL Conditions:** Triggered if customer provides OFAC general license documentation.
- **7.8 Execution Preconditions:** Payment Hub reject port active ($X_{\text{pre}} = \text{True}$).

#### 8. STP Predicate Evaluation
```
E_suff = True (Country codes and Statutory Embargo List verified)
R_det  = True (Deterministic statutory rejection instruction derived)
R_uniq = True (Single pacs.002 rejection directive)
V_det  = True (pacs.002 schema valid)
V_auth = True (OFAC Statutory Embargo attestation verified)
P_bank = True (Zero tolerance statutory auto-block policy)
C_comp = False (Sanctions Gate FAIL -> Triggers Auto-Block Handoff)
X_pre  = True (Payment hub reject adapter active)
---------------------------------------------------------
STP_ELIGIBLE = True (For Auto-Block) -> Emit pacs.002 Reject XML to Bank Hub (Subject to Level 2 Production Gating)
```

#### 9. Output Contract
Deterministic `pacs.002` Payment Rejection XML with reason code `RR04` and regulatory narrative.

#### 10. Bank Handoff Contract
Handoff to Bank Payment Hub to cancel wire and block clearing; alert Bank MLRO.

#### 11. Audit / Provenance Requirements
Log country code, matched embargo list authority, timestamp, `pacs.002` reject hash, and stage transitions in Audit Ledger.

#### 12. Failure States
`STATUTORY_AUTO_BLOCK_EMITTED` $\to$ `OFAC_LICENSE_SUSPENSE` $\to$ `COUNTRY_CODE_UNRESOLVED`.

#### 13. Security Requirements
Ensure embargo rules cannot be bypassed or disabled by unauthorized operators.

#### 14. Test Requirements
1. Happy path: Wire to comprehensively sanctioned country generates deterministic `pacs.002` auto-block.
2. Happy path: Intermediary bank in sanctioned country blocked automatically.
3. Negative: Unresolved country string halts and routes to Compliance Desk.
4. Exception: Remittance citing valid OFAC license halts auto-block and routes to MLRO.
5. Adversarial: Attempt to modify country code in transit intercepted by SHA-256 ledger.

#### 15. Phase 1 Reuse
`ResolutionEngine`, `AuthorityValidationEngine`, `EvidenceSTPEvaluator`, `FolderOutputAdapter`, `AuditService`.

#### 16. New Phase 2 Capability
`GeopoliticalEmbargoEngine` (P0 platform component).

#### 17. External Dependency
OFAC Comprehensive Sanctions List / EU Statutory Embargo Database.

#### 18. Bank Discovery Dependency
Bank legal policy on automated rejection (`pacs.002`) vs funds freezing in escrow.

#### 19. Open Questions
Multi-jurisdictional sanctions conflicts (EU Blocking Statute vs US OFAC) (`BANK_DISCOVERY_REQUIRED`).

#### 20. Implementation & Production STP Status
- **Platform Implementation Status:** **PLATFORM IMPLEMENTATION READY WITH BANK CONDITIONS (Phase 2C Slice 10)**.
- **Production STP Status:** **BLOCKED / NOT ENABLED** (Gated pending live OFAC sanctions list sync).

---

## 10. Profile Implementation & Production STP Governance Matrix

```
+----+-------------+------------------------------------+---------------------------------------------------+-----------------------------------------+---------------------------------+
| #  | Profile ID  | Profile Name                       | Platform Implementation Status                    | Key Bank Discovery / Config Dependency  | Production STP Status           |
+----+-------------+------------------------------------+---------------------------------------------------+-----------------------------------------+---------------------------------+
| 1  | `PR-05`     | Corrupted Message Format           | **PLATFORM IMPLEMENTATION READY**                 | Bank Accepted Transliteration Policy    | **BLOCKED / NOT ENABLED**       |
| 2  | `PR-08`     | Queue Processing Failure           | **PLATFORM IMPLEMENTATION READY**                 | Message Broker DLQ Bindings & Retries   | **BLOCKED / NOT ENABLED**       |
| 3  | `DQ-05`     | Invalid Address Format             | **PLATFORM IMPLEMENTATION READY**                 | Building Number vs Street Split Policy  | **BLOCKED / NOT ENABLED**       |
| 4  | `PR-01`     | Duplicate Payment                  | **PLATFORM IMPLEMENTATION READY WITH CONDITIONS** | 24h Settlement Hash Store & Fee Policy  | **BLOCKED / NOT ENABLED**       |
| 5  | `DQ-08`     | Invalid Routing Code               | **PLATFORM IMPLEMENTATION READY WITH CONDITIONS** | FedLine / BoE Merger Directory Sync     | **BLOCKED / NOT ENABLED**       |
| 6  | `DQ-02`     | Invalid BIC / SWIFT                | **PLATFORM IMPLEMENTATION READY WITH CONDITIONS** | SWIFTRef Directory Feed Subscription    | **BLOCKED / NOT ENABLED**       |
| 7  | `DQ-01`     | Invalid IBAN                       | **PLATFORM IMPLEMENTATION READY WITH CONDITIONS** | Bank SSI Master API & CoP Gateway       | **BLOCKED / NOT ENABLED**       |
| 8  | `DQ-06`     | Missing Purpose Code               | **PLATFORM IMPLEMENTATION READY WITH CONDITIONS** | Bank Commercial Trade Policy Allowlist  | **BLOCKED / NOT ENABLED**       |
| 9  | `ST-01`     | Returned Payment                   | **PLATFORM IMPLEMENTATION READY WITH CONDITIONS** | Core DDA Re-credit Posting API Protocol | **BLOCKED / NOT ENABLED**       |
| 10 | `CO-04`     | Restricted Corridor                | **PLATFORM IMPLEMENTATION READY WITH CONDITIONS** | OFAC Statutory Embargo Daily Sync       | **BLOCKED / NOT ENABLED**       |
+----+-------------+------------------------------------+---------------------------------------------------+-----------------------------------------+---------------------------------+
```

---

## 11. Final Authorization Statement

```
====================================================================================================
FINAL GOVERNANCE DIRECTIVE:
Phase 2 Implementation Contract v1.3 is formally approved as the authoritative, binding technical baseline.

ENGINEERING IMPLEMENTATION (LEVEL 1):
Engineering is authorized to build and verify Phase 2 platform services and test suites in sequential order
(Phase 2A -> Phase 2B -> Phase 2C).

PRODUCTION STP EXECUTION (LEVEL 2):
Production autonomous payment release remains GATED / BLOCKED until live bank configurations,
System of Record integrations, and compliance certifications are completed and signed off.
====================================================================================================
```
