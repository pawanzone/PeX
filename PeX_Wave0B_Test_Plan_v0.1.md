# PeX Wave 0B — Test Plan v0.1
## Test Strategy, Scenario Expansion & Verification Methodology

======================================================================
1. TEST STRATEGY & QUALITY OBJECTIVES
======================================================================

The Wave 0B Test Plan guarantees that all platform runtime components, hexagonal adapters, dynamic configuration engines, multi-mode acquisition flows, and HITL closed loops operate with 100% deterministic correctness and zero regression against the 462 Phase 2 and Wave 0A test baseline.

### Primary Objectives:
1. **Zero Regression**: Preserve 462 / 462 green tests across all Phase 2 and Wave 0A test suites.
2. **Dynamic Configuration Verification**: Prove that bank configurations loaded from JSON dynamically govern evidence requirements, trust tiers, and conditional logic.
3. **Fail-Closed Governance Verification**: Prove that invalid bank configurations (e.g. attempting to remove sanctions screening, lower trust tiers below baseline, or bypass maker-checker) are rejected at compilation time.
4. **Multi-Mode Acquisition Verification**: Test evidence acquisition across Modes 1 (Inbound), 2 (API Connector), 3 (Bank Push), and 4 (HITL).
5. **HITL Closed-Loop Verification**: Test operator submission of missing evidence and subsequent instant re-evaluation leading to deterministic resolution.
6. **E2E Scenario Expansion**: Implement and execute 6 new canonical E2E test scenarios (Scenarios 13–18) covering multi-mode acquisition and dynamic bank config overrides.

---

======================================================================
2. TEST SUITE STRUCTURE & TEST FILES
======================================================================

| Test Category | Target Test File | Target Scope & Verification Criteria |
|---|---|---|
| **Dynamic Config & Resolver** | `tests/wave0b/test_dynamic_config_resolver.py` | Validates JSON schema parsing, tenant/profile resolution, inheritance fallback, and configuration caching. |
| **Governance Compiler** | `tests/wave0b/test_governance_compiler.py` | Validates fail-closed compiler checks, regulatory invariant protections, trust tier constraints, and signature verification. |
| **Conditional Expressions** | `tests/wave0b/test_conditional_expressions.py` | Validates AST sandboxed evaluation of context variables (`amount`, `corridor`, `currency`, `error_code`) without code execution risk. |
| **Evidence Store & Deduplication** | `tests/wave0b/test_evidence_store.py` | Validates content-addressable storage, SHA-256 deduplication, dossier hash generation, and query methods. |
| **Multi-Mode Acquisition** | `tests/wave0b/test_acquisition_modes.py` | Validates Mode 1 (pre-gathered payload), Mode 2 (connector callback), Mode 3 (bank push event), and Mode 4 (HITL submission). |
| **HITL Closed Loop & Re-Eval** | `tests/wave0b/test_hitl_closed_loop.py` | Validates gap dossier generation, operator field validation, submission handling, re-evaluation invocation, and state transitions. |
| **E2E Dynamic Execution** | `tests/wave0b/test_e2e_dynamic_execution.py` | Validates end-to-end execution of Scenarios 13–18 using dynamic JSON configurations and reference adapters. |
| **Provider Neutrality** | `tests/contracts/test_provider_neutrality.py` | Verifies zero forbidden cloud/vendor imports in all new Wave 0B source files. |

---

======================================================================
3. NEW E2E SCENARIOS (SCENARIOS 13–18)
======================================================================

### Scenario 13: High-Value Wire with Tier 1 Account Statement (Mode 1 + Dynamic Threshold)
- **Profile**: `DQ-01` (Invalid IBAN)
- **Tenant Config**: Custom threshold requiring `ACCOUNT_STATEMENT` (Tier 1) for amounts $> \$100,000$.
- **Condition**: Wire amount is $\$250,000$. Mode 1 provides Core DDA + Account Statement.
- **Expected Outcome**: $E_{\text{suff}} = \text{True}$, deterministic repair, `STP_ELIGIBLE = True`, `BANK_HANDOFF_READY`.

### Scenario 14: Cross-Border Currency Corridor with Regulatory Certificate (Mode 3 Push)
- **Profile**: `DQ-06` (Cross-Border Missing Remittance / Regulatory Code)
- **Tenant Config**: Specific corridor (EUR $\to$ BRL) requiring Central Bank Regulatory Certificate.
- **Condition**: Mode 1 lacks certificate ($E_{\text{suff}} = \text{False}$, `AWAITING_EVIDENCE`). Bank pushes certificate via Mode 3.
- **Expected Outcome**: Re-evaluation succeeds, $E_{\text{suff}} = \text{True}$, `STP_ELIGIBLE = True`, `BANK_HANDOFF_READY`.

### Scenario 15: Operator IBAN Correction via HITL Closed-Loop (Mode 4 Interactive)
- **Profile**: `DQ-08` (Routing/BIC Discrepancy)
- **Tenant Config**: Requires Operator confirmation when multiple branch BICs match.
- **Condition**: Mode 1 evidence ambiguous. Case enters `HITL_PENDING`. Operator submits verified IBAN/BIC via Mode 4.
- **Expected Outcome**: Immediate re-evaluation triggers. Case transitions to `RESOLVED` / `BANK_HANDOFF_READY` with Maker-Checker audit.

### Scenario 16: Automated Core Banking Query (Mode 2 Progressive Fallback)
- **Profile**: `PR-01` (Duplicate Payment Suspicion)
- **Tenant Config**: Allows Mode 2 inquiry to Core Banking for transaction ledger confirmation.
- **Condition**: Reference Core Banking adapter returns cleared transaction status.
- **Expected Outcome**: $E_{\text{suff}} = \text{True}$, duplicate confirmed, exception marked `REJECTED_DUPLICATE` with bank handoff.

### Scenario 17: Multi-Tenant Config Isolation & Inheritance
- **Profile**: `DQ-01` (Invalid IBAN)
- **Tenant Config**: Tenant A requires 3 evidence items; Tenant B uses default canonical 2 items.
- **Condition**: Same payment payload submitted under Tenant A vs Tenant B.
- **Expected Outcome**: Tenant A holds for 3rd item; Tenant B resolves immediately. Proves dynamic tenant isolation with zero cross-tenant contamination.

### Scenario 18: Governance Compiler Fail-Closed Rejection
- **Profile**: `CO-04` (Sanctions False Positive Disambiguation)
- **Tenant Config**: Malicious/erroneous bank config attempting to mark `SANCTIONS_DISAMBIGUATION_DOSSIER` as `mandatory: false` or lower trust tier to Tier 4.
- **Condition**: Candidate config submitted to `GovernanceCompiler`.
- **Expected Outcome**: Compiler rejects with `GovernanceValidationError` (`REJECT_REGULATORY_RULE_DOWNGRADE`). Execution fails closed.

---

======================================================================
4. EXECUTION & VERIFICATION PROTOCOL
======================================================================

1. Execute unit test suites iteratively per Slice.
2. Execute full test suite via `.venv\Scripts\python.exe -m pytest`.
3. Assert total passed tests $\ge 462 + N$ (where $N \ge 35$ new tests).
4. Verify zero test failures and zero skipped regressions.
5. Generate automated test run output and capture in `PeX_Wave0B_Regression_Test_Report_v0.1.md`.
