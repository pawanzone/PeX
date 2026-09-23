# PeX — Platform Version & Release Inventory

**Authoritative Governance Ledger for PeX (Payment Exception Resolution Platform)**  
**Repository:** `pex_platform`  
**Current Production-Grade Prototype Version:** `v1.9.0`  
**Status:** **P0 Remediation Batch 1 Complete (63 / 63 Passing Tests)**  
**Last Updated:** September 23, 2026

---

## 1. Release Inventory Table

| Version Tag | Release Date | Scope & Milestone Description | Test Suite Status | Checkpoint Artifact |
|---|---|---|---|---|
| **`v1.9.0`** | **2026-09-23** | **P0 Batch 1 Remediation:** Cryptographic audit hash invariant (`MST-009`), 7 adversarial tampering tests (`MST-034`), STP engine Session import (`MST-037`), STP fast-lane repair preservation (`MST-036`), Frontend dispatch auth & SoD (`MST-035`), Rule/ICD auto-approve Maker-Checker governance (`MST-038`), Canonicalizer domain propagation (`MST-039`), Pytest discovery & root hygiene (`MST-033`). | **63 / 63 PASSED (100%)** | `backups/rollback_checkpoint_p0_batch1_v1_9_0_20260923.zip` |
| **`v1.8.4`** | 2026-09-21 | **Canonical DB & Semantic Layer:** SQLite persistent engine, 233 initial cases seed, 19 policy rules, 5 ICD clearing nodes, MISC menu architecture navigation. | 46 / 46 PASSED | `backups/rollback_checkpoint_pre_db_20260920.zip` |
| **`v1.8.3`** | 2026-09-21 | **Smart Role Synthesis & Rule Studio:** Approver role synthesis, category two-way sync, clean-slate Draft New Rule workflow. | 43 / 43 PASSED | `backups/rollback_checkpoint_pre_rule_studio_v1_4_20260921.zip` |
| **`v1.8.2`** | 2026-09-21 | **3-Step Rule Pipeline:** Streamlined Draft New Rule with live syntax AST auto-compilation. | 43 / 43 PASSED | - |
| **`v1.8.1`** | 2026-09-21 | **Context-Aware Dynamic Actions:** Adaptive table action buttons (Review & Submit / Run Triage / Rework). | 43 / 43 PASSED | - |
| **`v1.8.0`** | 2026-09-21 | **Disambiguation & Fast-Lane Table:** Multi-Hypothesis Disambiguation UI, zero-scroll table layout, synchronous AST refresh. | 43 / 43 PASSED | `backups/rollback_checkpoint_pre_rule_studio_v1_4_20260921.zip` |
| **`v1.7.8`** | 2026-09-21 | **20-Step Lifecycle Blueprint:** BA & Payment SME technical walkthrough and 20-step lifecycle diagram in Architecture Studio. | 39 / 39 PASSED | - |
| **`v1.7.7`** | 2026-09-20 | **Typography & Legibility Overhaul:** High-contrast palette, font-size boost, real-time font scale switcher. | 39 / 39 PASSED | - |
| **`v1.7.6`** | 2026-09-20 | **RTGS Radar Alignment:** Cutoff radar card click routing aligned to open RTGS cases. | 39 / 39 PASSED | - |
| **`v1.7.5`** | 2026-09-20 | **AI Reasoner Live Toasts:** Live reasoner synthesis modal, global toasts, and progress indicators. | 39 / 39 PASSED | - |
| **`v1.7.4`** | 2026-09-20 | **Investigations Forensic Hub:** Case search, multi-dimensional filtering, and grouped forensic trace lifecycle view. | 39 / 39 PASSED | - |
| **`v1.7.3`** | 2026-09-20 | **Dashboard Filter Reconciliation:** Dimensional filter counts, dynamic rail toggles, and role task scope clarity. | 39 / 39 PASSED | - |
| **`v1.7.2`** | 2026-09-20 | **Interactive Click-Routing:** SLA cutoff filtering and zero-scroll responsive case table. | 39 / 39 PASSED | - |
| **`v1.7.1`** | 2026-09-20 | **BIAN Mathematical Reconciliation:** 4-way mathematical reconciliation formulas and normalized domain mapping. | 39 / 39 PASSED | - |
| **`v1.7.0`** | 2026-09-20 | **3-Tier Role-Adaptive Hero Cockpit:** Live RTGS cutoffs radar and 1-line BIAN domain strip. | 39 / 39 PASSED | - |
| **`v1.6.1`** | 2026-09-20 | **Granular Operational SOPs:** Restored operational playbooks alongside 5 BIAN domain playbooks. | 34 / 34 PASSED | - |
| **`v1.6.0`** | 2026-09-20 | **5 BIAN Domain Playbooks:** Interactive color-coded markdown & JSON architecture viewer. | 34 / 34 PASSED | - |
| **`v1.5.0`** | 2026-09-19 | **Governed STP & Fast-Lane Release Engine:** Autonomous zero-touch execution (<=$10k) and supervised batch release. | 34 / 34 PASSED | - |
| **`v1.4.0`** | 2026-09-19 | **Policy-as-Code Studio:** Natural language to JSON AST synthesis, impact simulation, and Maker-Checker governance. | 28 / 28 PASSED | `backups/rollback_checkpoint_pre_rule_studio_v1_4_20260921.zip` |
| **`v1.3.0`** | 2026-09-18 | **Dual Authorization & Tier-2 Gating:** Risk and Compliance Approver dual-key approval for high-value/sanctions cases. | 22 / 22 PASSED | - |
| **`v1.2.0`** | 2026-09-18 | **Role-Gated Approvals Engine:** Maker-Checker human-in-the-loop sign-off and audit trail tracking. | 18 / 18 PASSED | `backups/rollback_checkpoint_pre_subtabs_v1_2_20260920.zip` |
| **`v1.1.0`** | 2026-09-17 | **Zero-PII Vault & Tokenization:** Format-preserving surrogate tokenization for IBAN, PAN, names, and accounts. | 12 / 12 PASSED | - |
| **`v1.0.0`** | 2026-09-16 | **Canonical Core Foundation:** 41 BIAN exception profiles, 5 market domains, ISO 20022/SWIFT ingestion engine. | 8 / 8 PASSED | - |

---

## 2. Current Version (`v1.9.0`) Technical Details

### Master Remediation Register Mapping
- **Authoritative Baseline:** `validation_audit/PEX_MASTER_REMEDIATION_REGISTER_FINAL.md`
- **P0 Remediation Report:** `validation_audit/PEX_P0_REMEDIATION_BATCH_1_REPORT.md`

### Components Modified & Hardened in `v1.9.0`
1. **Cryptographic Provenance Engine (`backend/app/core/hashing.py`)**:
   - Deterministically incorporates `amount` (formatted as `.2f`), `currency`, `debtor_account`, and `creditor_account` into the SHA-256 hash payload.
   - Preserves genesis hash stability and canonical key ordering (`sort_keys=True, separators=(',', ':')`).
2. **Adversarial Cryptographic Tampering Suite (`tests/test_audit_trail.py`)**:
   - 7 automated adversarial attack vectors executing on every build.
3. **STP Fast-Lane Autonomous Engine (`backend/app/services/stp_engine.py`)**:
   - Resolved missing `Session` import.
   - Preserves AI repair recommendations into `approved_changes` on approval history and embeds `repaired_fields` into outbound wire contracts.
4. **Governed Action Dispatch Endpoint (`backend/app/api/endpoints/actions.py`)**:
   - Replaced default user fallback with strict token/actor verification.
   - Enforces `HTTP 401 Unauthorized` for missing/invalid credentials and `HTTP 403 Forbidden` for Operator persona (SoD).
5. **Governed Rules & ICD Endpoints (`backend/app/api/endpoints/rules.py` & `backend/app/db/repository.py`)**:
   - Eliminated unchecked `auto_approve=True` bypass.
   - Enforces Checker role and Maker != Checker Segregation of Duties.
6. **Canonicalization Engine (`backend/app/services/canonicalizer.py`)**:
   - Automatically derives and attaches `ExceptionDomain` across all 5 payment domains.
7. **Workspace & Test Discovery Isolation (`pytest.ini` & `tools/diagnostics/`)**:
   - Relocated 13 root diagnostic scripts into `tools/diagnostics/` and established explicit testpaths.

---

## 3. Test Suite Verification Summary (v1.9.0)

```
============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\pawan\.gemini\antigravity\scratch\pex_platform
configfile: pytest.ini

tests/test_audit_trace.py .                                              [  1%]
tests/test_audit_trail.py .......                                        [ 12%]
tests/test_canonicalization.py .                                         [ 14%]
tests/test_contracts.py ...                                              [ 19%]
tests/test_functional_adversarial.py ..................                  [ 47%]
tests/test_hitl_approval.py ...                                          [ 52%]
tests/test_p0_batch_1_remediation.py ..........                          [ 68%]
tests/test_scenarios.py ...                                              [ 73%]
tests/test_tokenization.py .                                             [ 74%]
backend/tests/test_disambiguation_and_rule_edit.py ...                    [ 79%]
backend/tests/test_rules_e2e.py ........                                 [ 92%]
backend/tests/test_stp_e2e.py .....                                      [100%]

======================= 63 passed, 40 warnings in 4.82s =======================
```
