# UI v2 backend report

Branch `ui/v2` (working tree, nothing committed by the backend worker). Contract: `docs/ui_v2_api_contract.md` (v1.1).

## What works
* `/api/v2` for all 14 screens: home (6 role payloads), worklist (tabs, filters, saved views, preview, assign/reassign), approvals and compliance queues, case page for 9 variants derived from real state (any case, including batch-pipeline cases), journey, evidence view, notifications.
* Case actions: submit, approve, return, reject, request-information, reassess, escalate, start-verification, check-status, request-bank-status, compliance decision (second reviewer for confirm-block), ping, disambiguate. Optional `Idempotency-Key`.
* Controls enforced server-side: maker-checker and SoD (also by same name/email), approver limits, dual authorisation at >= 250,000 with distinct approvers, SoD/limit failures audited (APPROVAL_BLOCKED), compliance hold blocks repair actions, resend blocked in STATUS_UNKNOWN, audit role read only. Only the signed inbound bank signal sets EXECUTED_CONFIRMED/SETTLED (check-status uses the simulated bank through that path).
* STP batch review/approve (rule MR-01, limit `PEX_BATCH_APPROVAL_MAX` default 25,000), grouped not-eligible reasons, mode aware (SHADOW records only).
* Batches: list, detail with stages and reconciliation, records, rejected download (jsonl/json/csv), reprocess child batch, "Needs review" outcome, unknown profile rejection.
* Audit: events + filters, detail with hash check, CSV export, case report, control reports. Admin: 6 simulated integrations, handoffs, two-administrator mode change (applies to the running mode), roles, policies, 41 exception types.
* Personas added: Elena Marsh, Mei Tan, Marcus Lee, Sofia Rossi, Chen Wei, Amara Okafor, Rhea Kapoor (read only), Tomas Berg.
* Seed: `scripts/seed_ui_v2_demo.py [--force] [--demo-batch]`; auto-seeds an EMPTY database when `PEX_DEMO=true` (`PEX_SEED_V2`, default true). Existing databases are not touched unless the script is run. Creates 14 named cases (+ INV-0002, SET-0039 handed to bank, EXE-0088 executed, WAT-0090 waiting), 12 micro-repairs totalling 136,620 (mixed GBP/EUR/USD, includes an invalid-BIC fix) and 3 ineligible examples. The 82 existing cases stay (PEX-INV-0001 is replaced by the named case). `--demo-batch` pushes a synthetic ~50 record file through the real pipeline.

## Tests
* `tests/test_ui_v2_api.py`: 49 passed (~12 s). Covers variants, SoD, limits, dual auth, read-only audit role, compliance, STP eligibility/approval reasons, audit filters/export/report, mode-change second admin, needs-review duplicates, reprocess, unknown profile, a freshly generated batch whose cases all return a valid `/page` variant.
* Regressions: test_p05_hardening 12 passed; test_batch_pipeline 20 passed, 1 skipped; test_hitl_approval 3, test_audit_trail 7 passed; test_p0_remediation 15 passed with `PEX_ALLOW_LEGACY_TOKENS=true PEX_BANK_CALLBACK_SECRET=<any>` (it needs those, and a writable DB path: its hard-coded `scratch/` path gives a disk I/O error on the mounted folder here, so it was run from a copy pointing to /tmp).
* Pre-existing, unrelated: `test_file_watcher_e2e::test_new_file_detection_and_pipeline_execution` and `test_batch_file_watcher_e2e::test_03_batch_different_records_different_outcomes` fail identically on the HEAD checkout (expect SETTLED, mode gives SHADOW_RECORDED).

## Partial / assumptions
* Stage times for batches are approximate (stamped at stage boundaries). Evidence rows for old seeded cases are derived from the stored recommendation, not re-run.
* Dual authorisation above 250,000: Mei Tan (250k) cannot approve RET-0035 (AUD 1.79M); Kenji Watanabe (RSK-7714) plus ADM-0001 can. Tomas Berg has limit 0.
* Seeded hand-off PEX-SET-0039 uses `dispatch_status=HANDED_OFF_HOLD` so the simulated bank does not auto-confirm it; PEX-TMO-0044 is scripted (first check still unknown, second accepted, then signed confirmation).
* Audit timestamps for seeded events are seed time (the hash chain does not allow back-dating). Seeded IBANs are real MOD-97 values; the "invalid" ones are verified to fail.
* Compliance cases appear via `/compliance/queue`, not a worklist tab. Live write-back is shown as disabled/simulated. Batch limit (25,000) differs from autonomous STP (10,000) by design.

## Frontend must know
Bearer token auth; list payloads use `items`; `role_view` upper case; errors are `{error:{code,message,field},detail}`; write calls with the AUDIT_RISK token return 403; poll `/batches/{id}` until status is terminal.
