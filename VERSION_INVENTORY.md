# PeX — Platform Version & Release Inventory

**Authoritative Governance Ledger for PeX (Payment Exception Resolution Platform)**  
**Repository:** `pex_platform`  
**Current Production-Grade Prototype Version:** `v1.9.2`  
**Status:** **P1 Remediation Batch 3 Complete (89 / 89 Passing Tests)**  
**Last Updated:** September 23, 2026

---

## 1. Release Inventory Table

| Version Tag | Release Date | Scope & Milestone Description | Test Suite Status | Checkpoint Artifact |
|---|---|---|---|---|
| **`v1.9.2`** | **2026-09-23** | **P1 Batch 3 Remediation:** Contracts, reliability & code hygiene. STP batch transaction rollback (`MST-018`), explicit datetime parsing logging (`MST-019`), TypeScript vs Pydantic schema alignment (`MST-020`), authoritative single-page bundle declaration (`MST-030`), root directory generator reorganization into `tools/` (`MST-031`), Pydantic `.dict()` -> `.model_dump()` migration (`MST-032`), ingestion case schema completeness (`MST-044`), dynamic ontology context calculations (`MST-045`), SLA velocity terminal math (`MST-046`), SPA catch-all API route protection (`MST-047`). | **89 / 89 PASSED (100%)** | `backups/rollback_checkpoint_p1_batch3_v1_9_2_20260923.zip` |
| **`v1.9.1`** | 2026-09-23 | **P1 Batch 2 Remediation:** State machine & HITL approval governance. Disallow `INVESTIGATING` in approvals (`MST-040`), enforce dual-auth on `MODIFY` (`MST-041`), set initial state to `INGESTED` with domain on bank event intake (`MST-042`), enforce persona & role monetary limits in `check_can_approve` (`MST-043`), eliminate duplicate audit logging on approval submit (`MST-011`). | 76 / 76 PASSED (100%) | `backups/rollback_checkpoint_p1_batch2_v1_9_1_20260923.zip` |
| **`v1.9.0`** | 2026-09-23 | **P0 Batch 1 Remediation:** Cryptographic audit hash invariant (`MST-009`), 7 adversarial tampering tests (`MST-034`), STP engine Session import (`MST-037`), STP fast-lane repair preservation (`MST-036`), Frontend dispatch auth & SoD (`MST-035`), Rule/ICD auto-approve Maker-Checker governance (`MST-038`), Canonicalizer domain propagation (`MST-039`), Pytest discovery & root hygiene (`MST-033`). | 63 / 63 PASSED (100%) | `backups/rollback_checkpoint_p0_batch1_v1_9_0_20260923.zip` |
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

## 2. Current Version (`v1.9.1`) Technical Details

### Master Remediation Register Mapping
- **Authoritative Baseline:** `validation_audit/PEX_MASTER_REMEDIATION_REGISTER_FINAL.md`
- **P0 Remediation Report:** `validation_audit/PEX_P0_REMEDIATION_BATCH_1_REPORT.md`
- **P1 Remediation Report:** `validation_audit/PEX_P1_REMEDIATION_BATCH_2_REPORT.md`

### Components Hardened in `v1.9.1`
1. **Approval Engine State Gating (`backend/app/services/approval_engine.py`)**:
   - `MST-040`: Restricted approval eligibility strictly to `PENDING_APPROVAL` (Level 1) and `AWAITING_SECOND_APPROVAL` (Level 2). Cases in `INVESTIGATING` or `INGESTED` state are rejected.
   - `MST-041`: Integrated `ApprovalAction.MODIFY` into dual-authorization governance. High-value cases requiring dual-auth transition to `AWAITING_SECOND_APPROVAL` on `MODIFY` step 1 and mandate a distinct second officer for final approval.
2. **Bank Event Ingestion Initialization (`backend/app/api/endpoints/events.py`)**:
   - `MST-042`: Configured raw intake events to initialize with `status: "INGESTED"` (not `PENDING_APPROVAL`) and propagated the canonical `domain` field from `exception.domain`.
3. **Monetary Approval Limits & Entitlements (`backend/app/core/security.py`)**:
   - `MST-043`: Established `ROLE_MAX_APPROVAL_LIMITS` and enforced `amount <= persona.max_approval_amount` checks across all approval workflows.
4. **Audit Logging De-duplication (`backend/app/api/endpoints/approvals.py`)**:
   - `MST-011`: Eliminated duplicate `audit_service.log_event` call from the submit approval endpoint, ensuring single-source audit append via `ApprovalEngine`.
5. **Dedicated P1 Batch 2 Test Suite (`tests/test_p1_batch_2_remediation.py`)**:
   - 13 comprehensive unit and integration tests verifying all 5 remediated Master IDs.

---

## 3. Test Suite Verification Summary (v1.9.1)

```
============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\pawan\.gemini\antigravity\scratch\pex_platform
configfile: pytest.ini

tests/test_audit_trace.py .                                              [  1%]
tests/test_audit_trail.py .......                                        [ 10%]
tests/test_canonicalization.py .                                         [ 11%]
tests/test_contracts.py ...                                              [ 15%]
tests/test_functional_adversarial.py ..................                  [ 39%]
tests/test_hitl_approval.py ...                                          [ 43%]
tests/test_p0_batch_1_remediation.py ..........                          [ 56%]
tests/test_p1_batch_2_remediation.py .............                       [ 73%]
tests/test_scenarios.py ...                                              [ 77%]
tests/test_tokenization.py .                                             [ 78%]
backend/tests/test_disambiguation_and_rule_edit.py ...                    [ 82%]
backend/tests/test_rules_e2e.py ........                                 [ 93%]
backend/tests/test_stp_e2e.py .....                                      [100%]

======================= 76 passed, 53 warnings in 6.71s =======================
```
