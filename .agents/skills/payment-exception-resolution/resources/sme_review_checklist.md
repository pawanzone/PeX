# Institutional SME Review & Policy Sign-Off Checklist
**Governance Artifact**: `PeX-GOV-SME-CHECKLIST-v1.2`  
**Purpose**: Formal verification and regulatory compliance sign-off document for Banking SMEs, Compliance Officers, and Lead Operations Architects prior to promoting new exception logic into runtime execution.

---

## 1. Exception Type Governance Review

| Exception Playbook | SME Reviewer Role | Verification Focus | Status |
| :--- | :--- | :--- | :---: |
| **`SOP-114-IBAN`** | Lead Payments Architect | ISO 7064 MOD-97 algorithm precision, country length tables, zero hallucination | `[ ] PENDING / [✓] APPROVED` |
| **`SOP-115-BIC`** | SWIFT Network Specialist | ISO 9362 8-to-11 expansion, branch consolidation, clearing cutoff rules | `[ ] PENDING / [✓] APPROVED` |
| **`SOP-204-DUP`** | Fraud & Operational Risk SME | 4-point vector matching, burst detection window ($\Delta t \le 30\text{m}$), payroll exceptions | `[ ] PENDING / [✓] APPROVED` |
| **`SOP-301-SAN`** | Head of AML / Sanctions Compliance | OFAC/EU list fuzzy threshold ($85\%-97\%$), secondary identifier disambiguation | `[ ] PENDING / [✓] APPROVED` |
| **`SOP-302-KYC`** | Chief Compliance Officer (MLRO) | Wolfsberg CDD alignment, 30-day provisional waiver criteria, Dual-Auth escalation | `[ ] PENDING / [✓] APPROVED` |
| **`SOP-401-RET`** | Cash Management Operations Lead | ISO 20022 `pacs.004` return code dictionary (`AC04`, `AC06`, `AG01`), fee deductions | `[ ] PENDING / [✓] APPROVED` |

---

## 2. Institutional Decision Engine Control Verification

Please confirm that the runtime decision engine implements the following control parameters:

- [x] **Segregation of Duties**: Maker cannot approve own repairs; Level 2 Dual-Auth strictly enforced for $\ge \$250,000$.
- [x] **Deterministic Attribution Math**: Confidence calculated via 5 weighted pillars (+30% MOD-97, +25% SSI, +20% Velocity, +15% Rail, +6% Remittance).
- [x] **Cryptographic Audit Integrity**: SHA-256 continuous hash chain linking every operational step and user action.
- [x] **PII Protection**: Vault isolation ensuring zero plain account numbers or PII in external prompts.
- [x] **Return-to-Maker Workflow**: Clear escalation and rework loops for rejected or queried repairs.

---

## 3. Formal Sign-Off Authorization

```
SME Reviewer Name:     _______________________________________
Institutional Title:   _______________________________________
Department / Division: _______________________________________
Signature / Date:      _______________________________________  [2026-08-31]
```
