# 14-open-questions.md — Product Owner and Institutional Open Questions

**Document Status:** COMPLETE / EVIDENCE-AUDITED  
**Auditor Mode:** Objective External Review  
**Target Codebase:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Date of Audit:** October 2026  

---

## 1. Overview and Decision Framework

An architectural review of the PeX platform reveals foundational business, regulatory, and technical assumptions that cannot be resolved solely by inspecting the source code. These decisions require explicit determination by the **Product Owner**, **Bank Chief Operations Officer (COO)**, **Chief Risk Officer (CRO)**, and **Enterprise Payment Architects**.

The open questions are structured across 5 institutional domains:
1. Product & Workflow Architecture
2. Controls, Compliance & Risk Governance
3. Data Contracts & Payment Hub Integration
4. Information Security, Key Management & Privacy
5. Commercial Model & Cloud Deployment

---

## 2. Product & Workflow Architecture

| Question ID | The Open Question | Why It Matters | Default Assumption in Code Today | Who Must Decide |
| :--- | :--- | :--- | :--- | :--- |
| **PROD-01** | **Should PeX maintain a `SETTLED` lifecycle state, or terminate strictly at `DISPATCHED`?** | Core architectural principle states *"PeX never executes or settles payments"*. If PeX marks cases `SETTLED` without an external clearing callback, bank accounting ledgers will desynchronize from PeX. | `file_watcher.py:575` and `action_executor.py:82` prematurely mark cases as `SETTLED` internally. | **Bank Head of Payments Operations & Lead Architect** |
| **PROD-02** | **Is Autonomous Zero-Touch STP legally permitted by the bank, or is 1-Click Batch Release mandatory?** | Full zero-touch automated repair without human eyes requires regulatory and policy sign-off under supervisory guidelines for automated payment intervention. | Code implements both: zero-touch for $\le \$10\text{k}$ in `file_watcher.py`, and 1-click batch release in `/api/stp`. | **Bank Chief Risk Officer & Regulatory Compliance Head** |
| **PROD-03** | **How should PeX measure "Agreement Rate" in Read-Only Shadow Mode?** | In shadow mode, human operators may choose different valid paths (e.g. wire cancellation vs beneficiary inquiry vs repair). If PeX recommends repair and the human cancels, is that a disagreement or an operational policy choice? | No agreement calculation engine exists in code today (`NOT PRESENT`). | **Product Owner & Operations Research Lead** |
| **PROD-04** | **Is PeX positioned primarily as a Data Repair Engine or an Investigation Tool?** | Incumbent tools (Pega Smart Investigate, Swift Case Management) focus on multi-bank messaging (camt.027/camt.029, MT199). PeX currently excels at field-level repair but has zero outbound inquiry messaging. | Code is 90% optimized for field-level data repair (IBAN, BIC, account, purpose code). | **Product Owner & Head of Sales / Go-To-Market** |

---

## 3. Controls, Compliance & Risk Governance

| Question ID | The Open Question | Why It Matters | Default Assumption in Code Today | Who Must Decide |
| :--- | :--- | :--- | :--- | :--- |
| **CTRL-01** | **Must Maker-Checker Segregation of Duties apply to micro-repairs ($< \$10,000$)?** | Enforcing dual authorization on low-value micro-syntax repairs eliminates STP benefits; waiving it creates single-operator fraud risk. | Code requires Checker approval for all manual repairs, but fails to enforce `approver != maker` server-side (DEF-03). | **Internal Audit & Payments Operations Committee** |
| **CTRL-02** | **Does a repaired beneficiary account require mandatory re-screening against sanctions?** | Under FATF Recommendation 16 (Travel Rule) and OFAC guidelines, altering the destination account number or beneficiary name modifies the payment risk profile. | Code does not automatically trigger secondary sanctions screening after an IBAN repair is applied. | **Head of Financial Crime Compliance (MLRO)** |
| **CTRL-03** | **What is the institutional authority ranking when Core DDA contradicts the SSI Directory?** | When Core Banking DDA says an account is valid but the counterparty's Standing Settlement Instructions specify a different account, routing to the wrong account causes misdirected funds. | `reference_evidence_adapter.py:85-95` flags a contradiction and blocks STP (`r_uniq = False`). | **Head of Payments Operations & Legal Counsel** |

---

## 4. Data Contracts & Payment Hub Integration

| Question ID | The Open Question | Why It Matters | Default Assumption in Code Today | Who Must Decide |
| :--- | :--- | :--- | :--- | :--- |
| **DATA-01** | **Will the bank provide pre-parsed JSON feeds, or must PeX parse raw ISO 20022 XML and SWIFT MT?** | Significant development effort (3–5 engineer months) is required if PeX must parse and serialize W3C XML (`pacs.008.001.10`) and SWIFT FIN MT103 envelopes directly. | Code assumes the bank's integration gateway pre-parses messages into JSON (`RawBankEvent`). | **Enterprise Solution Architect & Integration Team** |
| **DATA-02** | **What outbound transport protocol will the bank payment hub support for repair handoffs?** | Payment hubs (Finacle, Temenos, ACI, Swift Alliance Access) communicate via IBM MQ, Kafka, AS2, or REST. PeX must build matching adapters. | `action_executor.py` dispatches to an in-memory dictionary (`"SIMULATED_BANK_PAYMENT_HUB"`). | **Bank Core Banking & Payment Hub Lead Architect** |
| **DATA-03** | **How will the bank deliver clearing execution confirmations (ACK / NAK / pacs.002)?** | PeX needs an asynchronous inbound listener to transition cases from `DISPATCHED` to `CONFIRMED_EXECUTED` or `SETTLED`. | `action_executor.py` simulates immediate synchronous delivery receipts (`ACK-SIM-...`). | **Payment Clearing & Settlement Engineering Lead** |

---

## 5. Information Security, Key Management & Privacy

| Question ID | The Open Question | Why It Matters | Default Assumption in Code Today | Who Must Decide |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | **Can cleartext PII reside inside the PeX database in the bank's VPC, or is zero-PII mandatory?** | GDPR and banking secrecy regulations require strict data minimization. If zero-PII is legally mandated, canonical databases cannot store raw debtor/creditor names. | Code stores cleartext names and IBANs in `CanonicalPayment` alongside ephemeral tokens (DEF-06). | **Chief Information Security Officer (CISO) & Data Privacy Officer** |
| **SEC-02** | **Which enterprise Key Management Service (KMS) or HSM will govern tokenization?** | In-memory tokenization (`TokenVault`) loses state on restart. Enterprise production requires AWS KMS, HashiCorp Vault, or on-premise Thales/Luna HSM. | Code uses an in-memory Python dictionary with SHA-256 slicing. | **Enterprise Security Architect** |
| **SEC-03** | **What enterprise Identity Provider (IdP) must PeX integrate for Single Sign-On?** | The hardcoded persona switcher must be deactivated; bank users must authenticate via enterprise corporate credentials. | Code issues static JWTs using hardcoded secret `"pex-enterprise-secret-key-2026-sha256"`. | **Enterprise IAM / Directory Services Team** |

---

## 6. Commercial Model & Cloud Deployment

| Question ID | The Open Question | Why It Matters | Default Assumption in Code Today | Who Must Decide |
| :--- | :--- | :--- | :--- | :--- |
| **COMM-01** | **Is PeX deployed as a Dedicated Virtual Appliance per bank or as a Multi-Tenant SaaS?** | Multi-tenant SaaS requires row-level tenant security (`tenant_id`), multi-tenant database partitioning, and strict network isolation. | Database models have zero tenant columns (`Single-Tenant design`). | **Chief Technology Officer & Product Owner** |
| **COMM-02** | **How will PeX be priced (volume-based per exception vs. seat license vs. gain-share)?** | Governs product telemetry requirements and audit logging for billing reconciliation. | `stp_engine.py:633` hardcodes a synthetic `$42.50` savings multiplier per settled case. | **Commercial Director & Chief Executive Officer** |
