# 🏛️ PeX — Five-Page CXO Executive Architecture Story

**Document ID:** `PEX-CXO-FIVE-PAGE-STORY-v1.0`  
**Target Audience:** Large-Bank CXOs (COO, CIO, CTO, Head of Payments, Head of Cash Management)  
**Governing Baseline:** PeX `v1.9.4` (`9e9184b`) / Enterprise Architecture `v0.2` / Cloud Reference Architecture `v0.2`  
**Format:** 5-Page Connected Executive One-Pager Canvas (16:9 Landscape)  
**Date:** September 29, 2026  

---

## Executive Narrative Overview

```text
PAGE 1: WHY?              ➔ Payment exceptions are a resolution problem — not simply a transaction problem.
         ↓
PAGE 2: WHAT?             ➔ A structured resolution intelligence layer — built around 41 exception profiles.
         ↓
PAGE 3: HOW?              ➔ From exception event to governed resolution and final business outcome.
         ↓
PAGE 4: HOW IT FITS?      ➔ Non-intrusive integration. Bank-controlled data. Technology-stack neutrality.
         ↓
PAGE 5: WHY TRUST / SCALE?➔ Governed. Traceable. Reusable across heterogeneous bank environments.
```

---

# Page 1: Why Banks Need PeX

### Title & Subtitle
* **Headline:** **Why Banks Need PeX**
* **Subtitle:** *Payment exceptions are a resolution problem — not simply a transaction-processing problem.*

---

### Panel Layout & Core Content

#### Panel 1: Bank Operations Today (The Investigation Reality)
* **Status Quo:** Manual investigation across fragmented operational teams and siloed applications.
* **Key Observations:**
  * **SME Dependency:** Critical resolution knowledge is trapped in individual operators' heads and local spreadsheets (70%+ manual/macro reliance).
  * **System Lookups:** Operators perform 6–10 disconnected lookups across Core Banking, DDA, Sanctions, and Clearing engines for a single break.
  * **Coordination Overhead:** Resolution relies on asynchronous email chains, manual ticketing handoffs, and unstructured chat channels.
  * **Operational Handoffs:** Multiple tier-1/tier-2 handoffs inflate cycle times and risk SLA breach penalties.

#### Panel 2: Why the Problem is Hard (Dimensions of Complexity)
* **Multi-Rail Fragmentation:** Disparate messaging syntaxes and rules across SWIFT MT/MX, Fedwire, CHAPS, TARGET2, ACH, and RTP.
* **Broad Exception Taxonomy:** Exceptions span data syntax errors, sanction false-positives, missing LEI/BIC, duplicate pacs.008, account format discrepancies, and liquidity cutoffs.
* **Disjointed Bank Estates:** Payment Hub, Core Banking (DDA), Compliance/Sanctions, Reference Data, and Clearing Rails operate as independent silos with distinct lifecycles.
* **Core Insight:** *"An exception rarely belongs to one system, one rule, or one team."*

#### Panel 3: The Need (Common Resolution Intelligence)
* **The Structural Gap:** Payment engines process transactions linearly; they do not possess contextual resolution intelligence when breaks occur.
* **The Solution Architecture:**
  * **Bridge the Disconnect:** Interpose an intelligent resolution layer between fragmented exception events and bank execution systems.
  * **Synthesize Context:** Unify historical resolution patterns, peripheral bank evidence, and real-time rail rules into an integrated decision framework.
  * **Enterprise Consistency:** Deliver uniform resolution logic across retail, commercial, and correspondent banking lines.

---

### Bottom Story / Evolution Bar
$$\text{PEOPLE-DRIVEN (Manual effort \& SME silos)} \longrightarrow \text{PROCESS-DRIVEN (Basic task automation)} \longrightarrow \text{WORKFLOW-DRIVEN (Standardized ticketing)} \longrightarrow \mathbf{RESOLUTION\text{-}INTELLIGENCE\text{ (Intelligent + Governed Resolution)}}$$

---

### Executive Takeaway
**Banks need more than case management or workflow routing. They need structured resolution intelligence for payment exceptions.**

---

### Speaker Notes (Page 1)
1. **Strategic Intent:** Establish that payment breaks are inherently a *resolution intelligence* deficit, not a flaw in core payment hubs or rails.
2. **Presenter Emphasis:** Highlight Panel 2—emphasize that breaks cross payment rails, compliance systems, and core ledgers simultaneously, which is why point automation fails.
3. **Transition to Page 2:** Once the CXO aligns on the multi-dimensional complexity, transition to Page 2 to reveal what PeX actually is and how it structures this chaos into 41 canonical profiles.
4. **Likely CXO Questions:** *"Why can't our existing Payment Hub or CRM handle this?"* $\to$ Answer: Payment hubs focus on linear throughput and clearing; CRMs manage tickets, not payment semantics, ISO 20022 schemas, or deterministic banking controls.

---

# Page 2: What Is PeX?

### Title & Subtitle
* **Headline:** **What Is PeX?**
* **Subtitle:** *A structured Payment Exception Resolution intelligence layer — built around 41 exception profiles.*

---

### Panel Layout & Core Content

#### Panel 1: The 41 Canonical Exception Universe
* **Comprehensive Scope:** Spans all 41 BIAN-aligned payment exception categories across 5 functional domains:
  1. **Account & Routing (12 profiles):** Invalid IBAN/BBAN, closed DDA, missing correspondent BIC, routing table mismatch.
  2. **Data & Formatting (9 profiles):** ISO 20022 XML syntax, truncation in MT103 fields, invalid charge codes (OUR/BEN/SHA).
  3. **Compliance & Sanctions (8 profiles):** OFAC 50% disambiguation, PEP false-positive elimination, FATF Travel Rule gaps.
  4. **Liquidity & Timing (6 profiles):** Clearing cut-off breach, debit cap exceeded, value date mismatch, cover payment delay.
  5. **Duplicate & Processing (6 profiles):** Duplicate UETR detection, pacs.004 return processing, camt.056 recall handling.
* **Core Semantics:** 41 Exception Profiles $\longrightarrow$ Common Exception Semantics $\longrightarrow$ Reusable Resolution Patterns.

#### Panel 2: What PeX Adds (Logical Capabilities)
* **Exception Intelligence:** Ingests raw alerts, parses multi-rail payloads, and derives the root-cause exception profile.
* **Evidence & Context:** Asynchronously queries peripheral bank systems (DDA, Sanctions, Client Master) via read-only ICD adapters.
* **Multi-Hypothesis Elimination:** Evaluates and mathematically scores competing resolution hypotheses.
* **Deterministic Validation:** Applies 100% authoritative banking rules before any proposal is submitted.
* **Controlled Human Authorization:** Enforces strict Maker-Checker Segregation of Duties (\$0 threshold) and Dual-Auth ($\ge \$250\text{k}$).
* **Audit & Provenance:** Cryptographically seals every decision node into an immutable SHA-256 Merkle-like chain.

#### Panel 3: Why This Is More Than AI (Compact Contrast)
| Dimension | Generic AI / LLM Alone | PeX Resolution Platform |
| :--- | :--- | :--- |
| **Reasoning Scope** | Generates unconstrained probabilistic text | Structured resolution context + typed `ReasoningResult` |
| **Centricity** | Prompt-centric & heuristic | 41 Canonical Exception Profile-centric |
| **Governance** | Advisory only; prone to hallucinations | Advisory AI strictly bound by deterministic banking rules |
| **Data Context** | Generic LLM prompt context | Canonical payment models + live peripheral ICD evidence |
| **Outcome** | Raw unstructured output | Governed operational outcome & compliant dispatch packet |
| **Traceability** | Limited opacity & prompt logging | End-to-end cryptographic SHA-256 provenance chain |

---

### Bottom Story / Evolution Bar
$$\mathbf{41\text{ CANONICAL PROFILES}} + \mathbf{BANKING\text{ }ONTOLOGY} + \mathbf{CANONICAL\text{ }MODEL} + \mathbf{PERIPHERAL\text{ }EVIDENCE} \longrightarrow \mathbf{COMMON\text{ }RESOLUTION\text{ }INTELLIGENCE}$$

---

### Executive Takeaway
**PeX is not "AI for payments." It is an enterprise-grade, deterministic resolution capability built around a defined exception universe.**

---

### Speaker Notes (Page 2)
1. **Strategic Intent:** Position PeX as an authoritative, domain-grounded platform rather than a generic generative AI tool.
2. **Presenter Emphasis:** Point to the 41 Canonical Exception Profiles in Panel 1. This proves PeX has mapped the complete landscape of banking breaks.
3. **Contrast Table:** Walk through Panel 3 to reassure Risk and Compliance CXOs that AI never executes payments directly—it operates within hard deterministic guardrails.
4. **Transition to Page 3:** Now that the CXO understands what PeX covers, transition to Page 3 to show the step-by-step resolution lifecycle.
5. **Likely CXO Questions:** *"Are the 41 profiles hardcoded or extensible?"* $\to$ Answer: They are canonical templates defined in our extensible domain ontology, allowing custom bank rules to inherit from standardized baselines.

---

# Page 3: How PeX Resolves an Exception

### Title & Subtitle
* **Headline:** **How PeX Resolves a Payment Exception**
* **Subtitle:** *From exception event to governed resolution and final business outcome.*

---

### Panel Layout & Core Content

#### Panel 1: The Resolution Journey (Ingestion to Intelligence)
* **Step 1: Event Ingest & Normalize:** Ingests raw MT/MX/ISO break from Payment Hub; normalizes into canonical `PaymentExceptionCase`.
* **Step 2: Profile Classification:** Maps break to 1 of 41 canonical profiles; derives root cause and missing attributes.
* **Step 3: Evidence Corroboration:** Asynchronously retrieves external corroborating evidence (DDA status, client directory, SWIFTRef).
* **Step 4: AI Hypothesis Reasoning:** Model Gateway generates structured `ReasoningResult` with confidence scores and repair suggestions.

#### Panel 2: The Controlled Decision Boundary (Governance & Authorization)
* **Deterministic Rules Gate:** 100% deterministic rule engine validates proposed repair against clearing schemes and bank policy. Rules *always* override AI.
* **Policy & Sanctions Re-Check:** Automated rescreening against watchlists to verify no new compliance risk is introduced.
* **Human-in-the-Loop (HITL):** Operator reviews side-by-side evidence, deterministic validations, and AI rationale on an intuitive canvas.
* **Segregation of Duties:** Hard \$0 Maker-Checker enforcement (Maker $\ne$ Checker). Dual-Authorization required for transfers $\ge \$250\text{k}$.
* **Core Rule:** *"AI recommends. Controls validate. Humans authorize. Systems execute."*

#### Panel 3: Controlled Execution & Final Outcome
* **Contract Generation:** Generates schema-compliant repair message (e.g., ISO 20022 `pacs.008` amendment, `camt.029` resolution).
* **Transport Dispatch (`DISPATCHED`):** Securely dispatches packet to clearing rail via bank-controlled egress gateway; logs network transport ACK.
* **Final Settlement Confirmation (`SETTLED`):** Case transitions to `SETTLED` *only* upon authoritative receipt of `pacs.002 ACCP` or internal DDA posting confirmation.
* **Case Closure & Merkle Sealing:** Seals complete 20-step lifecycle into immutable audit log and releases locks.

---

### Bottom Story / Evolution Bar
$$\mathbf{EVENT} \longrightarrow \mathbf{INTELLIGENCE} \longrightarrow \mathbf{DETERMINISTIC\text{ }CONTROL} \longrightarrow \mathbf{HUMAN\text{ }AUTHORIZATION} \longrightarrow \mathbf{CONTROLLED\text{ }EXECUTION} \longrightarrow \mathbf{FINAL\text{ }SETTLEMENT} \longrightarrow \mathbf{MERKLE\text{ }AUDIT}$$

---

### Executive Takeaway
**PeX closes the loop — from exception detection through investigation, governed decision, controlled execution, and final settlement.**

---

### Speaker Notes (Page 3)
1. **Strategic Intent:** Demonstrate the rigorous, end-to-end execution path and resolve any executive anxiety regarding automated execution.
2. **Presenter Emphasis:** Highlight the clear 4-tier separation in Panel 2: *AI recommends. Controls validate. Humans authorize. Systems execute.*
3. **Settlement Nuance:** Stress Panel 3—PeX does not declare victory on a simple network ACK; it tracks through to final, legal `pacs.002 ACCP` settlement.
4. **Transition to Page 4:** With the operational lifecycle clear, transition to Page 4 to demonstrate how PeX integrates seamlessly into existing bank infrastructure without "rip-and-replace."
5. **Likely CXO Questions:** *"What happens if the AI suggests an invalid account format?"* $\to$ Answer: The deterministic engine immediately flags and rejects it during the validation step before it ever reaches the human checker.

---

# Page 4: How PeX Fits Around the Bank

### Title & Subtitle
* **Headline:** **PeX Fits Around the Bank**
* **Subtitle:** *Non-intrusive integration. Bank-controlled data. Technology-stack neutrality.*

---

### Panel Layout & Core Content

#### Panel 1: The Existing Bank Ecosystem
* **Zero Disruption:** PeX wraps around the bank's existing core assets without requiring core replacement or invasive re-architecture.
* **Connected Systems:** Operates seamlessly alongside:
  * Payment Hubs (Finastra, ACI, Volante, FIS)
  * Core Banking & DDA Ledgers (SAP, Temenos, Thought Machine, Mambu)
  * Clearing & Market Infrastructure (SWIFT Alliance, Fedline, CHAPS, EBA Clearing)
  * Compliance, Sanctions & Watchlists (Fircosoft, Actimize, LexisNexis Bridger)
  * Enterprise Reference Data & Client Directory

#### Panel 2: Standardized Integration Contracts (ICDs)
* **Pluggable Hexagonal Adapters:** Clear interface boundaries decouples PeX from underlying protocols:
  * **REST / JSON APIs:** Synchronous case ingestion and operator interaction.
  * **Enterprise Messaging:** IBM MQ, MSMQ, RabbitMQ for legacy transaction queues.
  * **Event Streaming:** Apache Kafka, AWS SQS FIFO, GCP Pub/Sub, Azure Service Bus.
  * **File & Batch Transfer:** SFTP, ISO 20022 bulk XML, MT bulk files.
* **Principle:** Standardized integration contracts guarantee zero vendor lock-in.

#### Panel 3: Protected Data & AI Boundary (Zero-PII Isolation)
* **Token Vault Enclave:** Raw PII (names, IBANs, tax IDs) is tokenized at the bank ingress boundary.
* **Enclave Security:** Mappings are stored in an isolated, FIPS 140-2 Level 3 KMS-encrypted enclave. PeX core processes surrogate tokens exclusively.
* **Model Gateway Isolation:** Advisory LLMs never see raw PII. 
* **Data Sovereignty Affirmation:** 
  * *PeX does not use customer or payment data to train foundation models.*
  * *All model-provider data retention remains subject to bank-approved tenant policies.*

#### Panel 4: Technology Neutrality & Multi-Cloud Parity
* **Banking Infrastructure:** Mainframe (z/OS), Distributed On-Prem, Private Cloud, Hybrid Cloud.
* **Payment Formats:** SWIFT MT (103, 199, 202), ISO 20022 MX (pacs, camt, pain), Fedwire FAIM, ACH NACHA.
* **Cloud & Hosting Parity:** 100% feature parity across AWS, Google Cloud Platform, Microsoft Azure, or On-Premise Kubernetes.
* **LLM Flexibility:** Pluggable Model Gateway supports AWS Bedrock, GCP Vertex AI, Azure OpenAI, or Private Self-Hosted Models.

---

### Bottom Story / Evolution Bar
$$\mathbf{EXISTING\text{ }BANK\text{ }ESTATE} \longrightarrow \mathbf{STANDARDIZED\text{ }ICDs\text{ }\&\text{ }ADAPTERS} \longrightarrow \mathbf{PeX\text{ }RESOLUTION\text{ }CORE} \longrightarrow \mathbf{BANK\text{-}CONTROLLED\text{ }EXECUTION}$$

---

### Executive Takeaway
**PeX adds a powerful resolution capability around the bank's existing technology estate — without requiring technology standardization.**

---

### Speaker Notes (Page 4)
1. **Strategic Intent:** Overcome CIO/CTO fear of complex multi-year integration programs or vendor lock-in.
2. **Presenter Emphasis:** Highlight Panel 3—the Zero-PII Token Vault architecture and clear affirmation that bank data is never used for LLM model training.
3. **Enterprise Reality:** Emphasize Panel 4—PeX works whether the bank runs on mainframes, modern cloud, or hybrid microservices.
4. **Transition to Page 5:** Now that technical feasibility and security are established, move to Page 5 to address governance, traceability, and enterprise scale.
5. **Likely CXO Questions:** *"Do we need to upgrade our core banking platform to use PeX?"* $\to$ Answer: No. PeX integrates via non-intrusive read-only ICD adapters and existing payment queues.

---

# Page 5: Why PeX Can Be Trusted and Scaled

### Title & Subtitle
* **Headline:** **Why PeX Can Be Trusted and Scaled**
* **Subtitle:** *Governed. Traceable. Reusable across heterogeneous bank environments.*

---

### Panel Layout & Core Content

#### Panel 1: Embedded Governance & Segregation of Duties
* **Intrinsic Controls:** Governance is woven directly into the resolution pipeline, not bolted on after execution.
* **Maker-Checker (\$0 Limit):** Strict mathematical verification ensuring the operator creating a repair cannot authorize it.
* **Dual-Authorization:** High-value thresholds ($\ge \$250\text{k}$) trigger mandatory two-supervisor dual-signoff.
* **Immutable Compliance:** Configurable bank policy rules prevent STP execution on sensitive jurisdictions or watchlist alerts.

#### Panel 2: End-to-End Cryptographic Traceability Chain
* **11-Stage Verification Trail:** Every exception lifecycle is tracked through an unbroken cryptographic audit trail:
$$\text{Bank Event} \to \text{Exception ID} \to \text{Canonical Model} \to \text{Corroborated Evidence} \to \text{AI Reasoning} \to \text{Deterministic Validation} \to \text{Policy Decision} \to \text{Maker-Checker Auth} \to \text{Dispatch Contract} \to \text{Final Settlement} \to \text{Merkle Provenance}$$
* **WORM Regulatory Compliance:** SHA-256 Merkle hash chain stored in 7-year unalterable WORM storage for instant regulatory examination.

#### Panel 3: Semantic Ontology & Canonical Data Model
* **Harmonized Domain Language:** Abstract disparate legacy bank representations into unified canonical semantics:
$$\begin{matrix} \text{Bank A (Mainframe/MT)} \\ \text{Bank B (Modern Cloud/MX)} \\ \text{Bank C (Regional ACH/Hub)} \end{matrix} \implies \left[\begin{array}{c} \mathbf{PeX\text{ }ONTOLOGY} \\ \mathbf{CANONICAL\text{ }MODEL} \end{array}\right] \implies \begin{array}{c} \text{Unified Resolution Context} \\ \text{\& Reusable Decision Rules} \end{array}$$
* **Silo Elimination:** Allows different product lines (Corporate, Wealth, Retail) to share identical resolution logic.

#### Panel 4: Enterprise Reusability & Multi-Entity Scaling
* **Cross-Entity Reusability:** Deploy once; reuse across global subsidiaries, correspondent branches, and business units.
* **Continuous Operational Learning:** Approved resolution patterns enrich the bank's canonical knowledge graph without retraining foundation weights.
* **Linear Cost Scaling:** Dramatically scales payment exception volumes without linear headcount expansion.

---

### Bottom Story / Evolution Bar
$$\mathbf{COMMON\text{ }INTELLIGENCE} + \mathbf{BANK\text{-}CONTROLLED\text{ }DATA} + \mathbf{DETERMINISTIC\text{ }GOVERNANCE} + \mathbf{HUMAN\text{ }ACCOUNTABILITY} + \mathbf{FULL\text{ }TRACEABILITY} \longrightarrow \mathbf{SCALABLE\text{ }RESOLUTION\text{ }CAPABILITY}$$

---

### Executive Closing Proposition
> **"PeX turns fragmented payment exceptions into a common, governed resolution capability — using AI where it adds intelligence, deterministic controls where they must remain authoritative, humans where accountability is required, and bank-controlled interfaces for execution."**
> 
> *Common resolution intelligence. Bank-controlled execution. Full traceability.*

---

### Speaker Notes (Page 5)
1. **Strategic Intent:** Provide the final confidence bridge for the CXO—proving PeX is audit-proof, regulator-ready, and architected for enterprise-scale multi-entity reuse.
2. **Presenter Emphasis:** Walk through the 11-step cryptographic traceability chain in Panel 2. Regulators love that every decision node can be mathematically reconstructed.
3. **Closing Summary:** Deliver the final executive proposition: PeX does not replace the bank's systems—it unifies them with an intelligent, governed, and traceable resolution capability.
4. **Likely CXO Questions:** *"How do we prove to regulators that the AI didn't make an unauthorized decision?"* $\to$ Answer: Every step records the exact deterministic rule checks and human authorizer signatures in the tamper-evident Merkle hash chain.
