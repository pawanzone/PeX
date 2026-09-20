---
name: payment-exception-resolution
description: >-
  Standardized SME operational runbook and decision guidelines for validating, repairing,
  and governing payment exceptions across ISO 20022 and SWIFT CBPR+ rails. Covers all 41
  market exception profiles across 5 domains: Data Quality, Processing, Compliance,
  Client/Treasury, and Settlement/Returns.
---

# Payment Exception Validation & Repair Skill (SME Golden Standard - 41 Market Profiles)

This skill serves as the **Golden Canonical Knowledge Base** for Subject Matter Experts (SMEs), Payment Operations Leads, Risk Officers, and Compliance Approvers. The runtime decision engine, AI Copilot, and Maker-Checker approval desks rely on these exact validation procedures, attribution formulas, and governance thresholds.

---

## 1. Core Operating Principles & Governance Guardrails

Every payment exception processed under this framework must adhere to four immutable institutional guardrails:

1. **Zero Financial Hallucination / Zero Blind Autocorrect**:
   * No payment instruction may be modified without deterministic evidence grounding (MOD-97 mathematical proof, SWIFT directory lookup, or Master SSI match).
2. **Strict Segregation of Duties (Maker-Checker RBAC)**:
   * **Operator / Maker**: Initiates investigation, runs AI reasoner, fine-tunes evidence notes, and submits.
   * **Operations Approver (Checker)**: Verifies repair diff, validates attribution math, and signs Level 1 approval (up to $250k).
   * **Compliance Approver**: Exclusive clearance authority for Sanctions false-positives and KYC waivers.
   * **Risk Approver (Dual-Auth)**: Mandatory secondary sign-off for high-value transactions ($\ge \$250,000$).
3. **Continuous SHA-256 Cryptographic Custody**:
   * Every lifecycle transition (Ingestion $\rightarrow$ AI Repair $\rightarrow$ Rework $\rightarrow$ Level 1 $\rightarrow$ Level 2 $\rightarrow$ Settlement) is cryptographically linked to the previous block hash.
4. **Tokenized PII Vault Isolation**:
   * Plaintext account holder names and raw account numbers never enter public LLM prompts or client-side plain storage.

---

## 2. Standardized 100% Attribution Scoring Model

When an AI reasoner or operator evaluates a proposed repair, confidence is calculated deterministically across five weighted pillars:

| Pillar | Verification Criteria | Weight | Evidence Required |
| :--- | :--- | :---: | :--- |
| **Pillar 1: Mathematical Proof** | ISO 7064 MOD-97 checksum / Syntax validation | **+30%** | String conversion modulo 97 equals 1 / XSD valid |
| **Pillar 2: Directory Grounding** | Counterparty Master Directory SSI Match | **+25%** | 100% exact SSI match for beneficiary entity |
| **Pillar 3: Historical Settlement Velocity** | Historical transaction corridor precedent | **+20%** | $\ge 5$ successful settlements in prior 90 days |
| **Pillar 4: Rail & Currency Coherence** | Corridor clearing rail compatibility | **+15%** | Clearing rail (TARGET2/Fedwire/CHAPS) supports currency |
| **Pillar 5: Remittance Grounding** | Commercial invoice / unstructured remittance match | **+6%** | Invoice number matches debtor AP ledger |
| **Ambiguity Penalty** | Unresolved homonyms or missing counterparty docs | **-0% to -40%** | Flagged when secondary identifiers disagree |

$$\text{Total Confidence} = \sum (\text{Pillars 1 to 5}) - \text{Deductions} \quad (\text{Threshold for 1-Tier Approval: } \ge 85\%)$$

---

## 3. Comprehensive 5-Domain SME Playbooks (41 Market Profiles)

Detailed, SME-validated procedures for all 41 exception profiles are organized into 5 domain reference books:

* 📊 **[Data Quality Domain Playbook (9 Profiles)](./references/data_quality_domain_playbook.md)**
  * `INVALID_IBAN`, `INVALID_BIC`, `MISSING_BENEFICIARY_DATA`, `MISSING_REMITTANCE_INFO`, `INVALID_ADDRESS_FORMAT`, `MISSING_PURPOSE_CODE`, `INVALID_ACCOUNT_NUMBER`, `INVALID_ROUTING_CODE`, `BENEFICIARY_NAME_MISMATCH` (Confirmation of Payee).

* ⚙️ **[Processing Exception Domain Playbook (9 Profiles)](./references/processing_domain_playbook.md)**
  * `DUPLICATE_PAYMENT`, `ROUTING_FAILURE`, `ISO20022_VALIDATION_ERROR`, `CUTOFF_MISSED`, `CORRUPTED_MESSAGE_FORMAT`, `INTERMEDIARY_BANK_REJECTION`, `NETWORK_TIMEOUT`, `QUEUE_PROCESSING_FAILURE`, `PAYMENT_HELD_FOR_REPAIR`.

* 📋 **[Compliance Exception Domain Playbook (8 Profiles)](./references/compliance_domain_playbook.md)**
  * `SANCTIONS_SUSPECTED`, `AML_ALERT`, `PEP_MATCH`, `RESTRICTED_CORRIDOR`, `ADVERSE_MEDIA_MATCH`, `HIGH_RISK_JURISDICTION`, `REGULATORY_REPORTING_REQUIRED` (BoP), `CUSTOMER_WATCHLIST_MATCH`.

* 👤 **[Client & Treasury Exception Domain Playbook (8 Profiles)](./references/client_treasury_domain_playbook.md)**
  * `KYC_EXPIRED`, `INSUFFICIENT_FUNDS`, `NOSTRO_SHORTFALL`, `FX_RATE_UNAVAILABLE`, `AUTHORIZATION_MISSING`, `LIMIT_BREACH`, `LIQUIDITY_CONSTRAINT`, `CREDIT_EXPOSURE_BREACH`.

* 🔁 **[Settlement & Returns Exception Domain Playbook (7 Profiles)](./references/settlement_returns_domain_playbook.md)**
  * `RETURNED_PAYMENT`, `ACCOUNT_CLOSED` (AC04), `BENEFICIARY_ACCOUNT_FROZEN` (AC06), `RECONCILIATION_BREAK`, `SETTLEMENT_FAILURE`, `FUNDS_TRAPPED_AT_CORRESPONDENT`, `UNMATCHED_CREDIT`.

---

## 4. SME Review & Verification Protocol

Before new validation heuristics or thresholds are deployed into the runtime engine:
1. SMEs review the updated playbook in `references/`.
2. Complete the formal [SME Sign-Off Checklist](./resources/sme_review_checklist.md).
3. Commit the approved version to version control (`.agents/skills/payment-exception-resolution/`).
4. The runtime platform ingests the updated rules directly into its deterministic decision pipeline.
