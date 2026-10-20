# Morning review: overnight build of PeX

Branch `ui/v2`. Every slice was committed separately with its acceptance tests written first. Screenshots are in `docs/review/screens/`.

## What is done

| # | Slice | Commit | Screens |
|---|---|---|---|
| 1 | Evidence zone: tokenisation, C1 to C5 classification, reveal rules | 5d9bd38 | earlier |
| 2 | Bank-wide dashboard, same numbers for every role, plus role extras | 0b116ca | 01 |
| 3 | Sign-in screen, text size A / A+ / A++, illustrated avatars, avatar on audit | 4123bbf | 02, 03, 04 |
| 4 | Approvals desk (My desk and Others), 5-step evidence dossier, case tabs, per-case timeline | f05dea0 | 05, 06, 07 |
| 5 | Expedite ladder (approver, supervisor, head of operations), bell with SLA Expedite Chasers | f9093d0 | 08, 09 |
| 6 | Policy Studio (four-eyes), Policy Owner role, read-only ontology, data model and semantic layer, SOP list and detail | ac8ac15 | 10 to 15 |
| 7 | Market comparison | MARKET_COMPARISON.md | n/a |

## How to look at it

Sign in with the shared demo password; use Switch Role to change person.

- Policy Studio: sign in as **POL-8001 Nadia Rahman**, propose a new dual-authorisation amount with a reason. Switch to **POL-8002 Greg Holt**: the same card shows Approve and Reject. Nadia cannot approve her own change.
- Admin tabs: Policy Owner sees Payment ontology, Data model and semantic layer, SOPs only. Admin also sees Integrations, Reference screens, Component gallery.
- Expedite: open a pending case as Priya (OP-9012) and use the ladder; the bell shows chasers for the person pinged.

## Test results

- New and changed v2 suites: 242 passed (includes policy 28, reference 36, dashboard 20, dossier 13, expedite 12, approvals desk 8, sign-in 6, timeline 4).
- Remaining suites outside the baseline: 153 + 312 + 451 passed, 1 skipped.
- Frontend type-check clean. Policy and Admin pages exercised in a headless browser with no console or page errors.
- **Known baseline failures, identical before my changes:** 9 legacy files: batch_file_watcher, file_watcher, functional_adversarial, p0_batch_1, p1_batch_3, replit_readiness, scenarios, stage4 conflict retest. They were failing on HEAD already; I did not change them.

## Unresolved items and decisions for you

1. **Policy values are cached per process.** Fine for the single-worker demo. A multi-worker deployment needs a shared cache or a version check.
2. **Head of operations is a supervisor-role seat.** The third rung of the expedite ladder points at a supervisor. A separate role is cleaner if the bank has one.
3. **Not yet editable in Policy Studio:** pillar weights, SLA targets per rail, and natural-language rules. Parameters only for now.
4. **Dossier latency is simulated** (the five checks pause briefly to show progress). Remove when connectors are real.
5. **Seed data looks stale:** cutoff times in the seeded cases fall before today, so many cases show as past cutoff on the dashboard.
6. **Audit timeline order follows seed data** where timestamps tie.
7. **Dashboard stuck list is ordered by wait time only.** Consider ordering by SLA risk.
8. **Admin pages are read-only by design.** The semantic layer is a curated list of 20 mappings checked by tests against the models; it is not generated from a bank's own catalogue.
9. **Sign-in is a shared demo password.** Labelled "bank SSO later". Do not deploy outside a demo.
10. **A stray database WAL file** (`backend/pex_enterprise.db-wal`) is sitting untracked in the repo folder; I kept it out of the commit. Consider adding it to `.gitignore`.
11. **Windows folder noise:** `.fuse_hidden*` files and `.git/stale-*` lock files are leftovers from the sandbox mount. Safe to delete from Windows.

## Suggested next steps

See `MARKET_COMPARISON.md`. Short version: camt.110/111 case handling and Stop and Recall come first because Swift's deadlines are November 2026 and end-2027.
