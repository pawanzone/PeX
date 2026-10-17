# P0.5 / demo build progress log
Branch: demo/p05 (repo: pex_platform/demo_build, a clone; original repo untouched)
Started: 2026-10-17 ~00:50 local

## Status
- [x] clone + baseline (AG P0) ; fixtures restored from HEAD~1
- [x] config + router stubs committed
- [x] persisted maker_id/dispatch_status/bank fields (AG report claimed maker_id was added to CaseModel; it was NOT - SoD silently skipped after restart)

## Overnight status (Oct 17, 05:55 UTC)
Committed on `demo/p05`: P0.5 backend controls, local LLM gateway, revised UI, batch pipeline + Eurozone pack, execute-endpoint fix.
Verified: ~480 contract/wave tests + new hardening/batch/EUR/LLM tests pass; live smoke (1,000-record batch -> approve -> handoff -> simulated signed settlement; operator blocked from batch release).
Known: 10 legacy tests fail identically on AG baseline (fixtures/state); real Qwen never run (VM cannot reach Ollama); UI never rendered in a browser; 100k-record run (441s) predates last runner edits.
Run: reseed with scripts/reseed_demo_db.py; set PEX_DEMO=true PEX_OPERATION_MODE=ASSISTED PEX_BANK_CALLBACK_SECRET=<x> JWT_SECRET=<x>; point tests at a temp DATABASE_URL; `git checkout -- e2e_fixtures/output` after test runs.
Deck: agent stalled at artifact creation (likely waiting for approval) - to be redone.
