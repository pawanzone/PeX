# Known test baseline (22 Oct 2026, before the profile-pack refactor)

Run each file with a fresh database (see runfiles.sh). 42 of 51 files pass. These fail before any refactor work:

| File | Failing test | Cause (traced) |
|---|---|---|
| test_batch_file_watcher_e2e | test_03_batch_different_records_different_outcomes | expects SETTLED; default mode records SHADOW_RECORDED (stale expectation) |
| test_file_watcher_e2e | test_new_file_detection_and_pipeline_execution | same |
| test_functional_adversarial | test_normal_full_lifecycle_e2e, test_redteam_idempotency_flood_attack | expects SETTLED / "successfully executed"; gets DISPATCHED / SHADOW text (stale expectation) |
| test_p0_batch_1_remediation | test_mst_036_stp_fast_lane_preserves_repaired_fields | test case lacks mandatory evidence; fail-closed rules now reject it (stale test data) |
| test_p0_remediation | whole file (collection error) | SQLite "disk I/O error" on the mounted drive; environment, passes on a normal disk |
| test_p1_batch_3_remediation | test_mst_018_stp_batch_transaction_integrity, test_mst_031_root_workspace_cleanliness | stale batch expectation; extra file (conftest.py) in repo root |
| test_replit_readiness | test_replit_end_to_end_exception_resolution_lifecycle | result is None (to trace) |
| test_scenarios | test_scenario_iban_repair_001 | result is None (to trace) |
| test_stage4_evidence_conflict_retest | test_isolated_stage4_batch_e2e_retest | None where 1 expected (to trace) |

Goldens: tests/test_profile_goldens.py freezes 100 end-to-end outputs (all fixtures plus the profiles with no logic).
