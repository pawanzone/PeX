# P0.5 Batch, Scale and Eurozone Report

Principle held throughout: AI recommends. Controls validate. Humans authorize when required. Bank systems execute.
PeX never executes or settles. All bank communication is SIMULATED (`bank_comm=SIMULATED`, `execution_owner=BANK`).

## What was built

| Area | Where |
|---|---|
| Streaming batch pipeline (json / jsonl / ndjson / json.gz; chunks of 500, one transaction per chunk; idempotent by exception_id and UETR; malformed records isolated to `failed/`) | `backend/app/services/batch_pipeline.py` |
| Repository batch mode (single session, in-memory audit hash chain, bounded case cache) | `backend/app/db/repository.py` |
| Endpoints | `POST /api/batch/upload`, `POST /api/batch/generate`, `GET /api/batch`, `GET /api/batch/{id}`, `/results`, `/summary`, `/bank-handoff`, `GET /api/cases/page`, `GET /api/summary/counts` |
| Synthetic generator (deterministic, MOD-97-valid IBANs, valid ABA, no fake US IBANs) | `backend/app/services/synthetic_batch.py`, `scripts/gen_synthetic_batch.py` |
| Eurozone overlay (SEPA SCT, SEPA Instant, T2, return codes, EU VoP, DQ-05) | `backend/app/services/eur_rail_overlay.py` |
| EUR fixtures (36 + manifest) | `e2e_fixtures/eur/`, built by `scripts/build_eur_fixtures.py` |
| Indexes, SQLite WAL | `db/init_db.py`, `db/session.py` |

Batch outputs per batch id: `outbox/{id}.results.jsonl`, `outbox/{id}.summary.json`, `outbox/{id}.bank_handoff.jsonl` (not written in SHADOW mode), `failed/{id}.failed.jsonl`. State is in `batch_io/state/{id}.json`; unfinished batches resume after a restart and duplicates are skipped.

### Run it
```
python scripts/gen_synthetic_batch.py --count 100000 --seed 7 --out batch_100k.jsonl.gz
# drop in the inbox, or POST /api/batch/upload, then GET /api/batch/{id}
PEX_SCALE_N=100000 pytest tests/test_batch_pipeline.py -k scale
```
Tunables: `PEX_CASE_CACHE_MAX` (20000), `PEX_PORT_RETENTION` (2000), `PEX_SQLITE_WAL`, `PEX_SCT_INST_LIMIT_EUR` (100000), `PEX_SCT_INST_TIMEOUT_MS` (10000).

## Test results

- `tests/test_batch_pipeline.py`: 20 passed, 1 skipped (scale test, opt-in).
- `tests/test_eur_pack.py`: 55 passed.
- Rest of suite vs HEAD: **no new failures** (final diff of failing tests, run with a temp `DATABASE_URL`, is empty).
- Pre-existing failures, identical at HEAD: `test_file_watcher_e2e::test_new_file_detection_and_pipeline_execution`, `test_batch_file_watcher_e2e::test_03_batch_different_records_different_outcomes` (both still expect SETTLED instead of SHADOW_RECORDED), `test_functional_adversarial` x2, `test_p0_batch_1 mst_036`, `test_p1_batch_3 mst_018 / mst_031`, `test_replit_readiness` lifecycle, `test_scenarios::iban_repair_001`, `test_stage4_evidence_conflict_retest`.

## Scale

100,000 records end to end, cloud container (2 vCPU), pipeline plus SQLite:

| Metric | Result |
|---|---|
| Wall time | 441 s |
| Throughput | 226.7 rec/s (267 early, 226 late as the DB grew) |
| Peak RSS | about 217-227 MB (flat; case cache stayed at 82) |
| Outcome | 100,000 processed, 0 failed, 0 duplicates; 50,617 STP-eligible (all SHADOW_RECORDED) |
| Audit chain | 200,153 events, verified intact (12.6 s) |
| `/api/summary/counts` | 53 ms |

On the VM (laptop class), 20k records ran at about 400-450 rec/s with about 190 MB peak.
Caveats: the 100k run predates the last runner, overlay, DQ-05 and watcher edits, so re-run before quoting externally. First-page latency of `/api/cases/page` was not measured (only an out-of-range offset: 1 s, empty result).

## Real logic vs seeded data

Real and deterministic: IBAN MOD-97, ABA checksum, SEPA Inst EUR-only and limit, 10 s timeout rule (unknown timeout state blocks; no blind retry), no hold or cut-off for Instant, return-code policy (only AC01 and AC04 can be STP; AC06, AM04, MS03, RR04 and unknown codes go to a human), EU VoP (only MATCH proceeds), CBPR+ structured address with a traceability guard, the 8-predicate STP conjunction. The overlay only ever tightens.

Seeded (a bank replaces via configuration): T2 and SEPA cut-offs, the Inst limit, reason-code table, sample bank/IBAN directories, the VoP account directory. The reference adapters judge evidence sufficiency by key presence only.

## Findings

1. **Fail-open fixed.** `e2e_runner` treated profiles without logic as r_det=r_uniq=v_det=True, so a DQ-05 record with one evidence key reached STP. Now fail-closed, except where the tenant has a published evidence config (keeps wave0b scenario 14 passing).
2. **DQ-05 resolver invents defaults** (street, postcode, town) when absent. Mitigated by the traceability guard; the resolver is unchanged. It is also naive: small city list, "Frankfurt am Main" becomes "Frankfurt". Fixed: unbound `town_name`, postcodes inside `<AdrLine>`.
3. **No runner logic for DQ-02, DQ-06, PR-03, PR-05**, so the generator covers only runner-implemented profiles plus templates.
4. **`input_adapter.ingest_payload` bug (not fixed, not my file):** `dda_data.model_dump()` on a string logs "'str' object has no attribute 'model_dump'" for DQ-01 records. Swallowed, but it floods logs.
5. **Cache-only endpoints:** `list_cases`, analytics, rules and stp_engine read the bounded cache, so after bulk ingest they see only a recent subset. Use `/api/cases/page` and `/api/summary/counts` for full data. `verify_chain` loads all audit events.
6. **Demo DB pollution.** Running pytest with `DATABASE_URL` unset wrote test cases into `pex_enterprise.db` (1100 cases, 2207 audit events). Cleaning rows would break the audit chain. **Run `scripts/reseed_demo_db.py` before the demo, and run tests with `DATABASE_URL` pointing at a temp DB.**
7. Existing tests rewrite tracked `e2e_fixtures/output/*.json`; restore with `git checkout -- e2e_fixtures/output` after test runs.
8. Generate is salted per call so repeated UI clicks do not yield 100% duplicates; `?repeatable=true` opts out.
