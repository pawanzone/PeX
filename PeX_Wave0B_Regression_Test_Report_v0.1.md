# PeX Wave 0B — Full Regression Test Report v0.1
## Platform Runtime & Infrastructure Verification — 495 / 495 Tests Green

======================================================================
1. EXECUTIVE SUMMARY
======================================================================

- **Execution Date**: 2026-10-08
- **Git Branch**: `phase3/wave0b-runtime-infrastructure`
- **Starting Git Commit**: `3ee708d`
- **Python Environment**: Python 3.11.0 (Windows x86_64, pytest-9.1.1, pluggy-1.6.0)
- **Total Tests Collected**: 495 items
- **Total Tests Passed**: 495 / 495 (100.0% Pass Rate)
- **Failures / Errors**: 0
- **Phase 2 & Wave 0A Baseline Regressions**: 0 (462 / 462 preserved)
- **Wave 0B New Platform Tests**: 33 / 33 passed

```
================= 495 passed, 3 warnings in 143.60s (0:02:23) =================
```

---

======================================================================
2. TEST SUITE EXECUTION BREAKDOWN
======================================================================

| Module / Test File | Test Count | Status | Description / Scope |
|---|---|---|---|
| `tests\contracts\test_contract_validity.py` | 12 | PASS | Core contract schema validation |
| `tests\contracts\test_e2e_json_execution.py` | 12 | PASS | Wave 0A 12 Canonical Scenarios (DQ, PR, ST, CO) |
| `tests\contracts\test_fail_closed_behavior.py` | 7 | PASS | Fail-closed security & policy invariants |
| `tests\contracts\test_provider_neutrality.py` | 2 | PASS | AST-based forbidden cloud SDK import scan |
| `tests\contracts\test_security_adversarial.py` | 6 | PASS | Adversarial tokenization & tamper defense |
| `tests\test_audit_trace.py` | 1 | PASS | Audit provenance trace |
| `tests\test_audit_trail.py` | 7 | PASS | SHA-256 Merkle chain integrity |
| `tests\test_canonicalization.py` | 3 | PASS | Canonical payload formatting |
| `tests\test_co04_evidence_stp_e2e.py` | 25 | PASS | Phase 2 CO-04 Sanctions E2E |
| `tests\test_contracts.py` | 2 | PASS | Contract schemas |
| `tests\test_dq01_evidence_stp_e2e.py` | 30 | PASS | Phase 2 DQ-01 Invalid IBAN E2E |
| `tests\test_dq02_evidence_stp_e2e.py` | 25 | PASS | Phase 2 DQ-02 Invalid BIC E2E |
| `tests\test_dq05_evidence_stp_e2e.py` | 15 | PASS | Phase 2 DQ-05 Missing Beneficiary Address E2E |
| `tests\test_dq06_evidence_stp_e2e.py` | 30 | PASS | Phase 2 DQ-06 Purpose / Remittance Code E2E |
| `tests\test_dq08_evidence_stp_e2e.py` | 19 | PASS | Phase 2 DQ-08 Routing Code Discrepancy E2E |
| `tests\test_dq08_routing_evidence_stp_e2e.py` | 16 | PASS | Phase 2 DQ-08 Routing Transit Directory E2E |
| `tests\test_functional_adversarial.py` | 18 | PASS | Adversarial payload injection & tamper defense |
| `tests\test_hitl_approval.py` | 3 | PASS | Maker-Checker dual authorization |
| `tests\test_p0_batch_1_remediation.py` | 10 | PASS | Phase 2 P0 Remediation Batch 1 |
| `tests\test_p1_batch_2_remediation.py` | 13 | PASS | Phase 2 P1 Remediation Batch 2 |
| `tests\test_p1_batch_3_remediation.py` | 13 | PASS | Phase 2 P1 Remediation Batch 3 |
| `tests\test_p1_batch_4_remediation.py` | 14 | PASS | Phase 2 P1 Remediation Batch 4 |
| `tests\test_pr01_evidence_stp_e2e.py` | 19 | PASS | Phase 2 PR-01 Duplicate Payment E2E |
| `tests\test_pr03_evidence_stp_e2e.py` | 31 | PASS | Phase 2 PR-03 Value Date Past Cutoff E2E |
| `tests\test_pr05_evidence_stp_e2e.py` | 40 | PASS | Phase 2 PR-05 Amount Formatting E2E |
| `tests\test_pr08_evidence_stp_e2e.py` | 16 | PASS | Phase 2 PR-08 Queue Failure E2E |
| `tests\test_pr08_queue_recovery_evidence_stp_e2e.py` | 16 | PASS | Phase 2 PR-08 Queue Partition Recovery E2E |
| `tests\test_replit_readiness.py` | 8 | PASS | Environment readiness verification |
| `tests\test_scenarios.py` | 3 | PASS | Basic scenario regression |
| `tests\test_st01_evidence_stp_e2e.py` | 30 | PASS | Phase 2 ST-01 Returned Payment E2E |
| `tests\test_tokenization.py` | 2 | PASS | Token Vault PII masking |
| `backend\tests\test_disambiguation_and_rule_edit.py` | 3 | PASS | HITL Disambiguation & Rule Editing |
| `backend\tests\test_rules_e2e.py` | 6 | PASS | Rule engine E2E |
| `backend\tests\test_stp_e2e.py` | 5 | PASS | Autonomous STP Engine E2E |
| **`tests\wave0b\test_acquisition_modes.py`** | **4** | **PASS** | **Wave 0B Multi-Mode Acquisition (Modes 1, 2, 3, 4)** |
| **`tests\wave0b\test_conditional_expressions.py`** | **7** | **PASS** | **Wave 0B Sandboxed AST Expression Engine** |
| **`tests\wave0b\test_dynamic_config_resolver.py`** | **3** | **PASS** | **Wave 0B Dynamic Published Config Resolver** |
| **`tests\wave0b\test_e2e_dynamic_execution.py`** | **6** | **PASS** | **Wave 0B Canonical Scenarios 13–18 E2E** |
| **`tests\wave0b\test_evidence_store.py`** | **4** | **PASS** | **Wave 0B Content-Addressable Evidence Store** |
| **`tests\wave0b\test_governance_compiler.py`** | **6** | **PASS** | **Wave 0B Fail-Closed Governance Compiler** |
| **`tests\wave0b\test_hitl_closed_loop.py`** | **3** | **PASS** | **Wave 0B HITL Dynamic Gap & Re-Eval Loop** |
| **TOTAL** | **495** | **PASS** | **100% Green Suite** |

---

======================================================================
3. ARCHITECTURAL INVARIANT COMPLIANCE
======================================================================

1. **8-Predicate Formula**: $\text{STP\_ELIGIBLE} = E_{\text{suff}} \land R_{\text{det}} \land R_{\text{uniq}} \land V_{\text{det}} \land V_{\text{auth}} \land P_{\text{bank}} \land C_{\text{comp}} \land X_{\text{pre}}$ verified across all 18 canonical scenarios.
2. **Bank Execution Boundary**: `execution_owner = "BANK"` and terminal state `BANK_HANDOFF_READY` verified in 100% of successful resolutions.
3. **Provider Neutrality**: AST scanning verified 0 forbidden cloud SDK imports in domain, port, and core service layers.
4. **Fail-Closed Governance**: Configuration compiler strictly rejected all attempts to downgrade regulatory rules, lower trust tiers below floor, or bypass Maker-Checker.
