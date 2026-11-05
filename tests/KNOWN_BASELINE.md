# Test baseline and assurance summary (5 Nov 2026)

Run each file with a fresh database (`runall.sh`-style: one database per test file). Result after the baseline clean-up: every file passes. Three tests are marked as expected failures with the reason in the test itself.

## What the suite covers
- Straight-through rules: the 8 fixed predicates, the profile ceiling, release mode and the zero-touch limit (`test_release_mode`, `test_stp_*`).
- Policy Studio: four-eyes, audit, validation (`test_release_mode`, policy tests).
- The profile and control library, the integration contract and 9 reference lookups (`test_library`, `test_contract`, `test_reference_connectors`).
- 41 profile packs end to end, frozen as goldens (`test_profile_goldens`).
- Shadow scorecard and value model (`test_shadow_scorecard`, `test_value_model`).
- Network cases, approvals, audit chain, tokenisation, access control, batch intake, adversarial and red-team cases.

## What was fixed in this clean-up
| File | Was | Fix |
|---|---|---|
| test_batch_file_watcher_e2e, test_file_watcher_e2e, test_stage4_evidence_conflict_retest | expected SETTLED | default mode is SHADOW: expect SHADOW_RECORDED, and no settled time (PeX never settles; the bank does) |
| test_functional_adversarial, test_scenarios, test_replit_readiness | expected a settlement receipt | no receipt before the bank confirms; the hand-off test runs in ASSISTED mode and expects "handed off" |
| test_p1_batch_3_remediation | batch of an evidence-less case expected to release; root-folder and `tools/` layout | expects the fail-closed refusal with nothing changed; root may hold only the builder and conftest.py; the missing `tools/` folders are no longer checked |
| test_profile_goldens | two golden entries (ST-02, ST-03 "missing evidence") for fixtures that were renamed to "..._missing_with_conflict"; the new names already had goldens | removed the two orphaned entries; nothing else in the file changed |
| test_p0_remediation | collection error | the test now creates its scratch folder (it was a missing folder, not a disk problem) |

## Still open (expected failures)
| Item | Why | What closes it |
|---|---|---|
| `test_mst_036` and two tests in `backend/tests/test_stp_e2e.py` (expected failures) | the cases carry no mandatory evidence, and the fail-closed rules correctly refuse them | give each an evidence fixture; the marks are strict, so a fix is noticed |
