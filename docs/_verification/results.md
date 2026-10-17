# PeX Verification Run Results (V1 - V7)
**Target Database:** `scratch/writable_test.db` (Writable Copy)
**Database URL:** `sqlite:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/scratch/writable_test.db`

## V1: ISO 7064 MOD-97-10 Check Digit Verification
| IBAN | Remainder (`num_str % 97`) | `validate_iban_mod97()` | Mathematical Validity |
| :--- | :---: | :---: | :---: |
| `GB82WEST12345698765432` | **1** | `True` | **VALID (Remainder == 1)** |
| `GB82WEST12345698765423` | **49** | `False` | **INVALID** |
| `GB82WEST12345698760000` | **1** | `True` | **VALID (Remainder == 1)** |
| `GB82WEST12345698760001` | **28** | `False` | **INVALID** |

### V1 Findings & Demo Discrepancies:
1. **`GB82WEST12345698765432`**: Remainder = **1** (Valid).
2. **`GB82WEST12345698765423`**: Remainder = **49** (Invalid). Note: Doc 05 mistakenly stated remainder 28; the true mathematical remainder is **49**. Doc 05 is hereby corrected.
3. **`GB82WEST12345698760000`**: Remainder = **1** (Valid). In `backend/app/services/data_loader.py:84`, this is seeded as the **original (supposedly broken)** value (`creditor_account.iban`).
4. **`GB82WEST12345698760001`**: Remainder = **28** (Invalid). In `backend/app/services/data_loader.py:85`, this is seeded as the **proposed repair** value for `case_idx=1` (`...76{case_idx:04d}`).
5. **Seeded Proof vs Reality**: `data_loader.py:94` hardcodes the proof text: `"Raw MOD-97 remainder = 1 (Deterministic Pass)"`. In reality, the proposed repair value has remainder **28** and fails check digit validation! The seeded demo case inverts valid and invalid, repairing a mathematically valid IBAN into an invalid one while claiming remainder = 1.

## V2: E2E Runner Execution on Stage 4 Fixtures (REC01, REC03, REC04, REC05)
| Case ID | $E_{suff}$ | $P_{allow}$ | $R_{det}$ | $R_{uniq}$ | $V_{det}$ | $V_{auth}$ | $\neg C_{hold}$ | $A_{limit}$ | Final `stp_eligible` | Final Status in DB | Rejection Reason / Basis |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `PEX-STAGE4-REC01-STP` | True | True | True | True | True | True | True | True | **True** | `SETTLED` | All 8 canonical predicates satisfied (E_suff AND R_det AND R_uniq AND V_det AND V_auth AND P_bank AND C_comp AND X_pre). |
| `PEX-STAGE4-REC03-MISSING-EVIDENCE` | False | True | False | False | False | True | True | True | **False** | `INGESTED` | Evidence insufficient: missing mandatory ['CORE_DDA_ACCOUNT', 'ROUTING_DIRECTORY'] / stale [] / contradictory []; Deterministic resolution could not be derived.; Resolution is ambiguous with multiple candidate matches.; Deterministic validation / checksum failed. |
| `PEX-STAGE4-REC04-CONFLICTING-EVIDENCE` | False | True | True | False | True | True | True | True | **False** | `RECOMMENDED` | Evidence insufficient: missing mandatory ['CORE_DDA_ACCOUNT', 'ROUTING_DIRECTORY'] / stale [] / contradictory ['CORE_DDA_ACCOUNT', 'CONTRADICTORY_EVIDENCE_FLAG', 'SSI_DIRECTORY_ACCOUNT', 'ROUTING_DIRECTORY', 'CONTRADICTION_DETECTED']; Resolution is ambiguous due to contradictory evidence (CORE_DDA_ACCOUNT, CONTRADICTORY_EVIDENCE_FLAG, SSI_DIRECTORY_ACCOUNT, ROUTING_DIRECTORY, CONTRADICTION_DETECTED). |
| `PEX-STAGE4-REC05-INVALID-REPAIR` | True | True | True | True | False | True | True | True | **False** | `RECOMMENDED` | Deterministic validation / checksum failed. |

## V3: STP Eligibility Check Comparison (/api/stp vs e2e_runner)
### Code in `e2e_runner.py` (lines 160-220):
```python
# Evaluates formal 8-predicate gate: E_suff ∧ R_det ∧ R_uniq ∧ V_det ∧ V_auth ∧ P_bank ∧ C_comp ∧ X_pre
stp_eligible = bool(e_suff and r_det and r_uniq and v_det and v_auth and p_bank and c_comp and x_pre)
```
### Code in `stp_engine.py` (lines 237-268, used by `/api/stp/eligible` and `/api/stp/batch-release`):
```python
# Mode A: Autonomous Zero-Touch STP
if amount <= 10000.0 and confidence >= 0.98 and domain in ["DATA_QUALITY", "FORMAT_SYNTAX"]:
    return STPEligibilityItem(eligible=True, mode=STPMode.AUTONOMOUS, ...)
# Mode B: 1-Click Supervised Fast-Lane Batch
if amount <= 25000.0 and confidence >= 0.90 and domain in ["DATA_QUALITY", "FORMAT_SYNTAX", "PROCESSING", "ACCOUNT_DIRECTORY"]:
    return STPEligibilityItem(eligible=True, mode=STPMode.ONE_CLICK_BATCH, ...)
```
### V3 Audit Verdict:
**CONFIRMED MISMATCH**. `/api/stp/eligible` and `/api/stp/batch-release` do **NOT** evaluate the 8-predicate gate used by `e2e_runner`. Instead, they use amount and confidence heuristics (`amount <= 25000 and confidence >= 0.90`). They do not verify evidence sufficiency, cross-source contradictions, or mathematical check digits.

## V4: Case Status Lifecycle Trace Through Approval and Action Execution
- **Step 0 (Initial)**: Case `PEX-INV-0001` status = `PENDING_APPROVAL`, queue = `Repair`, amount = $42000.0
- **Step 1 (After `process_approval_action`)**: success = `True`, new_stage = `APPROVED`, case.status = `APPROVED`
- **Step 2 (After `execute_governed_action`)**: success = `True`, msg = `Action successfully executed and settled.`
  - `GovernedActionContract.status` = `SETTLED`
  - `DeliveryReceipt.status` = `SETTLED_CONFIRMED`
  - `Case.status` in repository = **`SETTLED`**

### V4 Reconciliation of Conflicting Statements in Earlier Docs:
- **Doc 03 stated**: Approved transitions to `DISPATCHED`.
- **Docs 06/07 stated**: Settled.
- **Code Reality**: In `backend/app/services/action_executor.py:82`, the code explicitly sets:
  `case["status"] = LifecycleStage.SETTLED.value`
  The state `DISPATCHED` is **completely bypassed** in `action_executor.py`! The case transitions directly from `APPROVED` to `SETTLED`. Doc 03 line references will be corrected accordingly.

## V5: Pytest Execution on Writable Database Copy
Running `pytest` across all test suites against `scratch/writable_test.db`...
```
ve4/test_wave4_adversarial_predicates.py::test_cat_a_10_v_det_tr01_validation_failure
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_11_v_det_tr05_syntax_failure
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_12_v_det_st06_validation_failure
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_13_v_auth_tr01_authority_unavailable
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_14_v_auth_tr05_authority_unavailable
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_15_v_auth_st06_authority_unavailable
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_16_p_bank_tr01_amount_exceeds_auto_threshold
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_17_p_bank_tr05_amount_exceeds_auto_threshold
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_18_c_comp_tr01_sanctions_match
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_19_c_comp_tr05_sanctions_match
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_20_c_comp_st06_sanctions_match
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_21_x_pre_tr01_idempotency_collision
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_22_x_pre_tr05_idempotency_collision
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_23_x_pre_st06_idempotency_collision
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_b_01_st06_zero_auto_stp_invariant
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_b_02_compound_tr01_missing_evidence_and_sar_flag
FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_b_03_compound_tr05_unauthorized_signer_and_unverified_authority
FAILED tests/wave4/test_wave4_e2e_scenarios.py::test_scenario_37a_tr01_kyc_expired_provisional_waiver
FAILED tests/wave4/test_wave4_e2e_scenarios.py::test_scenario_37b_tr01_kyc_expired_distressed_fail_closed
FAILED tests/wave4/test_wave4_e2e_scenarios.py::test_scenario_38a_tr05_authorization_missing_dual_auth_verified
FAILED tests/wave4/test_wave4_e2e_scenarios.py::test_scenario_38b_tr05_authorization_missing_unapproved_fail_closed
FAILED tests/wave4/test_wave4_e2e_scenarios.py::test_scenario_39a_st06_funds_trapped_camt056_inquiry_zero_auto_stp
FAILED tests/wave4/test_wave4_e2e_scenarios.py::test_scenario_39b_st06_funds_trapped_telemetry_missing_fail_closed
81 failed, 828 passed, 5 warnings in 307.61s (0:05:07)

```
**Total Pytest Failures on Writable DB:** 81
- **Environment (Read-only DB) Failures:** 0
- **Real Functional / Adversarial Failures:** 81

#### List of Real Failures:
- `FAILED tests/contracts/test_e2e_json_execution.py::TestE2EJsonExecution::test_dq01_sufficient_achieves_stp`
- `FAILED tests/contracts/test_e2e_json_execution.py::TestE2EJsonExecution::test_dq01_missing_evidence_fails_closed`
- `FAILED tests/contracts/test_e2e_json_execution.py::TestE2EJsonExecution::test_dq08_sufficient_achieves_stp`
- `FAILED tests/contracts/test_e2e_json_execution.py::TestE2EJsonExecution::test_dq08_ambiguous_matches_fails_closed`
- `FAILED tests/contracts/test_e2e_json_execution.py::TestE2EJsonExecution::test_pr01_duplicate_sufficient_suppresses_and_stps`
- `FAILED tests/contracts/test_e2e_json_execution.py::TestE2EJsonExecution::test_pr01_missing_history_fails_closed`
- `FAILED tests/contracts/test_e2e_json_execution.py::TestE2EJsonExecution::test_pr08_queue_failure_sufficient_recovers_stp`
- `FAILED tests/contracts/test_e2e_json_execution.py::TestE2EJsonExecution::test_pr08_broker_unreachable_fails_closed`
- `FAILED tests/contracts/test_e2e_json_execution.py::TestE2EJsonExecution::test_st01_returned_payment_sufficient_recredits_stp`
- `FAILED tests/contracts/test_e2e_json_execution.py::TestE2EJsonExecution::test_st01_missing_original_debit_fails_closed`
- `FAILED tests/contracts/test_e2e_json_execution.py::TestE2EJsonExecution::test_co04_license_exemption_sufficient_achieves_stp`
- `FAILED tests/contracts/test_e2e_json_execution.py::TestE2EJsonExecution::test_co04_prohibited_corridor_fails_closed`
- `FAILED tests/contracts/test_fail_closed_behavior.py::TestFailClosedBehavior::test_e2e_harness_fails_closed_when_any_predicate_false`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_positive_wave1_fixtures[Scenario 19: DQ-03 Missing Beneficiary Data [STP Path]-DQ-03_missing_beneficiary_sufficient.json-DQ-03]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_positive_wave1_fixtures[Scenario 20: DQ-04 Missing Remittance Info [STP Path]-DQ-04_missing_remittance_sufficient.json-DQ-04]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_positive_wave1_fixtures[Scenario 21: DQ-07 Invalid Account Number [STP Path]-DQ-07_invalid_account_sufficient.json-DQ-07]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_positive_wave1_fixtures[Scenario 22: DQ-09 Beneficiary Name Mismatch / VoP [STP Path]-DQ-09_beneficiary_name_mismatch_sufficient.json-DQ-09]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_positive_wave1_fixtures[Scenario 23: PR-02 Routing Failure [STP Path]-PR-02_routing_failure_sufficient.json-PR-02]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_positive_wave1_fixtures[Scenario 24: PR-04 Cutoff Missed [STP Path]-PR-04_cutoff_missed_sufficient.json-PR-04]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_positive_wave1_fixtures[Scenario 25: PR-07 Network Timeout [STP Path]-PR-07_network_timeout_sufficient.json-PR-07]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_positive_wave1_fixtures[Scenario 26: PR-09 Payment Held for Repair [STP Path]-PR-09_payment_held_for_repair_sufficient.json-PR-09]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_positive_wave1_fixtures[Scenario 27: CO-07 Regulatory Reporting Required [STP Path]-CO-07_regulatory_reporting_sufficient.json-CO-07]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_negative_wave1_fixtures[Scenario 19 (Neg): DQ-03 Ambiguous Beneficiary [Fail-Closed / HITL]-DQ-03_missing_beneficiary_ambiguous.json-DQ-03]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_negative_wave1_fixtures[Scenario 20 (Neg): DQ-04 Unparseable Remittance [Fail-Closed / HITL]-DQ-04_missing_remittance_unparseable.json-DQ-04]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_negative_wave1_fixtures[Scenario 21 (Neg): DQ-07 Account Not Found [Fail-Closed / HITL]-DQ-07_invalid_account_not_found.json-DQ-07]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_negative_wave1_fixtures[Scenario 22 (Neg): DQ-09 VoP No Match [Fail-Closed / HITL]-DQ-09_beneficiary_name_mismatch_no_match.json-DQ-09]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_negative_wave1_fixtures[Scenario 23 (Neg): PR-02 Unreachable Route [Fail-Closed / HITL]-PR-02_routing_failure_unreachable.json-PR-02]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_negative_wave1_fixtures[Scenario 24 (Neg): PR-04 Policy Prohibits Roll [Fail-Closed / HITL]-PR-04_cutoff_missed_policy_blocked.json-PR-04]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_negative_wave1_fixtures[Scenario 25 (Neg): PR-07 Idempotency Duplicate Prevention [Fail-Closed / Suspense]-PR-07_network_timeout_idempotency_collision.json-PR-07]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_negative_wave1_fixtures[Scenario 26 (Neg): PR-09 Unresolved Syntax [Fail-Closed / HITL]-PR-09_payment_held_for_repair_unresolved_syntax.json-PR-09]`
- `FAILED tests/wave1/test_wave1_e2e_scenarios.py::TestWave1E2EScenarios::test_negative_wave1_fixtures[Scenario 27 (Neg): CO-07 Missing Statutory License [Fail-Closed / Compliance Hold]-CO-07_regulatory_reporting_missing_statutory.json-CO-07]`
- `FAILED tests/wave2/test_wave2_e2e_scenarios.py::TestWave2E2EScenarios::test_positive_wave2_fixtures[Scenario 28A: PR-06 Intermediary Bank Rejection [STP Reroute Path]-PR-06_intermediary_bank_rejection_sufficient.json-PR-06]`
- `FAILED tests/wave2/test_wave2_e2e_scenarios.py::TestWave2E2EScenarios::test_positive_wave2_fixtures[Scenario 29A: ST-02 Account Closed [STP Governed Return Path]-ST-02_account_closed_sufficient.json-ST-02]`
- `FAILED tests/wave2/test_wave2_e2e_scenarios.py::TestWave2E2EScenarios::test_positive_wave2_fixtures[Scenario 30A: ST-03 Beneficiary Account Frozen [STP Governed Return Path]-ST-03_account_frozen_sufficient.json-ST-03]`
- `FAILED tests/wave2/test_wave2_e2e_scenarios.py::TestWave2E2EScenarios::test_negative_wave2_fixtures[Scenario 28B: PR-06 Unverified Telemetry [Fail-Closed / HITL]-PR-06_intermediary_bank_rejection_unverified_telemetry.json-PR-06]`
- `FAILED tests/wave2/test_wave2_e2e_scenarios.py::TestWave2E2EScenarios::test_negative_wave2_fixtures[Scenario 29B: ST-02 Contradictory Account Status [Fail-Closed / HITL]-ST-02_account_closed_contradictory.json-ST-02]`
- `FAILED tests/wave2/test_wave2_e2e_scenarios.py::TestWave2E2EScenarios::test_negative_wave2_fixtures[Scenario 30B: ST-03 Conflicting Judicial Orders [Fail-Closed / Compliance Hold]-ST-03_account_frozen_conflicting_order.json-ST-03]`
- `FAILED tests/wave3/test_wave3_e2e_scenarios.py::test_scenario_31a_tr02_sufficient_intraday_reservation`
- `FAILED tests/wave3/test_wave3_e2e_scenarios.py::test_scenario_31b_tr02_insufficient_deficit_fail_closed`
- `FAILED tests/wave3/test_wave3_e2e_scenarios.py::test_scenario_32a_tr03_nostro_shortfall_rebalancing`
- `FAILED tests/wave3/test_wave3_e2e_scenarios.py::test_scenario_32b_tr03_nostro_shortfall_unfunded_fail_closed`
- `FAILED tests/wave3/test_wave3_e2e_scenarios.py::test_scenario_33a_tr04_fx_rate_fresh_market_quote`
- `FAILED tests/wave3/test_wave3_e2e_scenarios.py::test_scenario_33b_tr04_fx_rate_stale_fail_closed`
- `FAILED tests/wave3/test_wave3_e2e_scenarios.py::test_scenario_34a_tr06_limit_breach_sufficient_headroom`
- `FAILED tests/wave3/test_wave3_e2e_scenarios.py::test_scenario_34b_tr06_limit_breach_hard_waiver_dossier`
- `FAILED tests/wave3/test_wave3_e2e_scenarios.py::test_scenario_35a_tr07_liquidity_constraint_sufficient`
- `FAILED tests/wave3/test_wave3_e2e_scenarios.py::test_scenario_35b_tr07_liquidity_constraint_exhausted`
- `FAILED tests/wave3/test_wave3_e2e_scenarios.py::test_scenario_36a_tr08_credit_exposure_dossier_zero_auto_stp`
- `FAILED tests/wave3/test_wave3_e2e_scenarios.py::test_scenario_36b_tr08_credit_exposure_distressed`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_01_e_suff_tr01_missing_mandatory_kyc`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_02_e_suff_tr05_missing_mandatory_mandate`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_03_e_suff_st06_missing_mandatory_tracker`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_04_r_det_tr01_no_refresh_in_progress`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_05_r_det_tr05_signature_pending`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_06_r_det_st06_unconfirmed_debit`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_07_r_uniq_tr01_ambiguous_candidates`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_08_r_uniq_tr05_ambiguous_candidates`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_09_r_uniq_st06_ambiguous_candidates`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_10_v_det_tr01_validation_failure`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_11_v_det_tr05_syntax_failure`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_12_v_det_st06_validation_failure`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_13_v_auth_tr01_authority_unavailable`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_14_v_auth_tr05_authority_unavailable`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_15_v_auth_st06_authority_unavailable`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_16_p_bank_tr01_amount_exceeds_auto_threshold`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_17_p_bank_tr05_amount_exceeds_auto_threshold`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_18_c_comp_tr01_sanctions_match`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_19_c_comp_tr05_sanctions_match`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_20_c_comp_st06_sanctions_match`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_21_x_pre_tr01_idempotency_collision`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_22_x_pre_tr05_idempotency_collision`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_a_23_x_pre_st06_idempotency_collision`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_b_01_st06_zero_auto_stp_invariant`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_b_02_compound_tr01_missing_evidence_and_sar_flag`
- `FAILED tests/wave4/test_wave4_adversarial_predicates.py::test_cat_b_03_compound_tr05_unauthorized_signer_and_unverified_authority`
- `FAILED tests/wave4/test_wave4_e2e_scenarios.py::test_scenario_37a_tr01_kyc_expired_provisional_waiver`
- `FAILED tests/wave4/test_wave4_e2e_scenarios.py::test_scenario_37b_tr01_kyc_expired_distressed_fail_closed`
- `FAILED tests/wave4/test_wave4_e2e_scenarios.py::test_scenario_38a_tr05_authorization_missing_dual_auth_verified`
- `FAILED tests/wave4/test_wave4_e2e_scenarios.py::test_scenario_38b_tr05_authorization_missing_unapproved_fail_closed`
- `FAILED tests/wave4/test_wave4_e2e_scenarios.py::test_scenario_39a_st06_funds_trapped_camt056_inquiry_zero_auto_stp`
- `FAILED tests/wave4/test_wave4_e2e_scenarios.py::test_scenario_39b_st06_funds_trapped_telemetry_missing_fail_closed`

## V6: Check Whether Any Code Path Prevents `approver == maker` (Same User ID)
One-line test script:
```python
check_can_approve(role=UserRole.OPERATIONS_APPROVER, amount=50000.0, queue='Repair', user_id='OP-9012')
```
**Result:** `can_approve = False`, `reason = 'Approval limit exceeded: Transaction amount ($50,000.00) exceeds OPERATIONS_APPROVER's maximum authorized approval limit ($0.00). Escalation required.'`

### V6 Audit Verdict:
**CONFIRMED**: Zero code paths check `approver_id != maker_id`. The parameter `maker_id` does not exist in `check_can_approve` or `ApprovalSubmission`. A user can act as Maker, switch persona to Approver, and approve their own work without error.

## V7: Provenance of UI Proofs, Hypotheses, Directory Results and AI Outputs
| UI Element / Component | Output Source Type | Specific Source File & Line | Evidence / Runtime Reality |
| :--- | :--- | :--- | :--- |
| **Step 1: MOD-97 Remainder Text** | Hardcoded String | `backend/app/services/data_loader.py:94` | Hardcodes `"Raw MOD-97 remainder = 1"` regardless of actual check digit result. |
| **Step 2: Beneficiary SSI Match** | Static JSON File | `backend/app/data/icd_staging_store.json` | Read by `backend/app/services/icd_staging_service.py:42-48`. Zero live SSI connection. |
| **Step 3: Confirmation of Payee (CoP)** | Hardcoded String | `backend/app/services/data_loader.py:96` | Interpolates template string `"NAME MATCHED"`. No live CoP API. |
| **Step 4: Clearing Rail & Currency Fit**| Hardcoded String | `backend/app/services/data_loader.py:97` | Hardcodes `"CBPR+ PASS"`. Checks CBPR+ even for Fedwire cases. |
| **Step 5: Behavioral Mule / Velocity** | Hardcoded String | `backend/app/services/data_loader.py:98` | Hardcodes `"Zero velocity anomalies. Established 3.5yr relationship"`. |
| **Hypotheses (HYP-1, 2, 3)** | Hardcoded List of Dictionaries | `backend/app/services/data_loader.py:100-104` | Static confidence numbers (`0.96`, `0.03`, `0.01`). |
| **AI Model Token Usage** | Hardcoded Static Integers | `backend/app/services/model_gateway.py:36-37` | Always returns `prompt_tokens=120, completion_tokens=45`. Zero live LLM calls. |
| **Sanctions Watchlist Lookup** | Static JSON File | `backend/app/data/icd_staging_store.json` | Read by `backend/app/services/icd_staging_service.py:54-60`. |
| **Fedwire ABA / SWIFT BIC Lookups** | Static JSON File | `backend/app/data/icd_staging_store.json` | Read by `backend/app/services/icd_staging_service.py:27-40`. |
| **Bank Delivery Receipts (ACK-SIM)** | In-Memory Mock Generator | `backend/app/services/action_executor.py:65-75` | Synchronously fabricates `DeliveryReceipt` with `status="SETTLED_CONFIRMED"`. |
| **E2E 8-Predicate Formula** | Real Runtime Pipeline | `backend/app/services/e2e_runner.py:140-220` | Real deterministic calculation over normalized evidence inputs. |
| **MOD-97 Validator Function** | Real Runtime Pipeline | `backend/app/services/canonicalizer.py:54-72` | Real mathematical calculation (`validate_iban_mod97`). |
| **Fedwire FAIM Validator Function** | Real Runtime Pipeline | `backend/app/services/canonicalizer.py:101-110` | Real regex validation. |
| **ISO 20022 Purpose Code Validator** | Real Runtime Pipeline | `backend/app/services/canonicalizer.py:111-116` | Real set membership test. |
| **Rule Engine NLP & AST Evaluation** | Real Runtime Pipeline | `backend/app/services/rule_engine.py:74-460` | Real regex parsing, AST synthesis, and case evaluation. |
| **SHA-256 Event Chaining** | Real Runtime Pipeline | `backend/app/core/hashing.py:10-70` | Real sequential SHA-256 calculation and link verification. |
