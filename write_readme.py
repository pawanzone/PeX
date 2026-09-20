import os

readme_path = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\README.md"
with open(readme_path, "w", encoding="utf-8") as f:
    f.write('''# PeX — Payment Exception Resolution Platform

Institutional-grade, bank-agnostic, human-governed AI system for automated and assisted payment exception repair, compliance escalation, and delivery settlement across SWIFT CBPR+, ISO 20022 (`pacs.008`, `pacs.004`, `camt.056`), Fedwire, and SEPA rails.

---

## Key Architectural Principles

1. **Zero-Trust Privacy & Sensitive Data Boundary**:
   - Debtor and Creditor identities are tokenized into isolated pseudonyms (`TOK-PARTY-...`, `TOK-IBAN-...`).
   - Downstream AI Model Gateway contexts never receive raw PII or unmasked account numbers.
2. **Deterministic Evidence Planning**:
   - Collects corroborating records from Beneficiary Master Directory, SWIFT BIC Directory, Institutional Policies, and Historical Precedents.
3. **Pluggable Governed AI Reasoning**:
   - Model Gateway evaluates tokenized investigation dossiers and produces structured `DecisionRecommendation` contracts with ISO 7064 MOD-97 check digit validation.
4. **Enforced Segregation of Duties & Dual Authorization**:
   - Maker-Checker rules strictly forbid Operators from approving their own initiated repairs.
   - High-Value exceptions ($\ge \$250,000$) mandate Dual Authorization by two distinct officers (e.g. Operations Approver + Risk/Executive Approver).
5. **Continuous Cryptographic Provenance (SHA-256)**:
   - Every state change across all 20 lifecycle stages is hashed and chained into a tamper-evident audit trail with real-time integrity verification.
6. **Simulated Bank Dispatch with Idempotency**:
   - Safe execution of repaired payments against simulated clearing ledger with guaranteed idempotency keys and delivery receipts.

---

## System Architecture

```mermaid
flowchart TD
    subgraph Ingestion["1. Multi-Bank Ingestion"]
        BankA["Bank A (REST)"] --> Canon["Canonicalizer Service"]
        BankB["Bank B (Kafka)"] --> Canon
        BankC["Bank C (MQ pacs.008)"] --> Canon
    end

    subgraph Privacy["2. Tokenization Vault"]
        Canon --> Vault["Isolated Token Vault (TOK-*)"]
        Vault --> Context["Context Builder (Zero PII)"]
    end

    subgraph Evidence["3. Dynamic Evidence Retrieval"]
        BMD["Beneficiary Master Directory"] --> EVD["Evidence Planner"]
        SWIFT["SWIFT BIC / Directory"] --> EVD
        POL["Governance Policies"] --> EVD
        HIST["Historical Precedents"] --> EVD
        EVD --> Context
    end

    subgraph Reasoning["4. Governed Model Gateway"]
        Context --> AI["Deterministic Model Reasoner"]
        AI --> Contract["Decision Recommendation Contract"]
        Contract --> Gate["Decision Engine Governance Gate"]
    end

    subgraph Approval["5. HITL Approval Engine"]
        Gate --> MakerChecker["Maker-Checker RBAC Engine"]
        MakerChecker --> DualAuth{"Amount >= $250k?"}
        DualAuth -- Yes --> TwoOfficers["Dual Authorization (2 Approvers)"]
        DualAuth -- No --> OneOfficer["Single Approver (Ops)"]
    end

    subgraph Settlement["6. Action Dispatch & Audit"]
        TwoOfficers --> Exec["Simulated Action Executor"]
        OneOfficer --> Exec
        Exec --> Receipt["Delivery Receipt (Idempotent)"]
        Exec --> Audit["Continuous SHA-256 Audit Chain"]
    end
```

---

## Institutional RBAC Persona Matrix

| User ID | Persona Name | Role | Max Approval Limit | Key Responsibilities |
|---|---|---|---|---|
| `OP-8472` | **Amina Okafor** | `OPERATOR` | Maker Only ($0) | Payment Intake, Exception Triage, Investigation Initiation |
| `OP-9104` | **Priya Nair** | `OPERATOR` | Maker Only ($0) | Payment Intake, Secondary Verification |
| `APR-3191` | **Daniel Osei** | `OPERATIONS_APPROVER` | $500,000 | Repair Approval, Value Modification, Resubmission |
| `CMP-4419` | **Marisol Vega** | `COMPLIANCE_APPROVER` | Unlimited (Compliance) | Sanctions Hit Review, KYC Waivers, Regulatory Hold |
| `RSK-7714` | **Kenji Watanabe** | `RISK_APPROVER` | $2,000,000 | Dual Authorization Tier-2 Approver for High-Value Repairs |
| `ADM-0001` | **Alex Whitfield** | `ADMIN` | Unlimited | Governance Policy Management, Audit Integrity Recompute |

---

## Quick Start & Verification

### 1. Automated Test Suite (Pytest)
Run the 14 core unit, contract, tokenization, RBAC, and scenario tests:
```powershell
.\.venv\Scripts\pytest -v
```

### 2. Deterministic 10-Step Demo Runner
Run the automated end-to-end execution of Scenario `IBAN-REPAIR-001` (executes in under 2 seconds):
```powershell
.\.venv\Scripts\python scripts/run_demo.py
```

### 3. Start Backend API Server
```powershell
.\.venv\Scripts\python scripts/run_server.py
```
*Backend API documentation available at: `http://localhost:8000/docs`*

### 4. Start Enterprise Frontend (React + Vite)
```powershell
cd frontend
npm run dev
```
*Open `http://localhost:5173` to interact with the full institutional UI.*

---

## Frontend Views & Capabilities

1. **Command Center**: Global operational KPIs, At-Risk Value counter, SLA Resolution Velocity chart, and priority breach queue.
2. **Payment Intake**: 3-step origination simulator (`Validate` -> `Classify` -> `Govern`) with profile evidence gates.
3. **Exception Worklist**: Server-filtered exception operations desk supporting filtering across Queues, Profiles, Severity, and Lifecycle status.
4. **Role Approvals Workspace**: Split-pane master-detail workbench with structured AI reasoning, visual Before/After field diffs, corroborating evidence citations, and maker-checker approval triggers.
5. **Investigations Hub**: Real-time operational audit log with control trace tags.
6. **Operations Analytics**: SLA throughput distributions, profile break percentages, and straight-through repair metrics.
7. **SWIFT & ISO Center**: Connectivity and latency monitoring for payment hubs and clearing adapters.
8. **Controls & Governance**: Active guardrails matrix and on-demand SHA-256 cryptographic hash-by-hash chain verification.
9. **Payment Ontology**: 6-stage architecture pipeline and 7 canonical ISO 20022 / BIAN domain entities.
10. **AI Repair Copilot**: Conversational assistant grounded in SOP-114, SOP-207, SOP-301, and SOP-402 with token usage counters.
11. **Persona Switcher**: Instant switching between authenticated demo roles (`Amina`, `Daniel`, `Marisol`, `Kenji`).
''')

print("Wrote pex_platform/README.md")
