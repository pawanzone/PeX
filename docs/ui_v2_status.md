# UI v2 status (branch `ui/v2`)

Written by the integration pass, Sun 18 Oct 2026 (early morning). Read this first.

## How far was this verified? (honest)
| Check | Done | Not done |
|---|---|---|
| Backend `/api/v2` | Live smoke over HTTP with real login tokens for 6 personas (maker, approver, supervisor, compliance, audit, admin): every endpoint family, state changes, SoD/limit/read-only rules, simulated bank ack -> EXECUTED only after the bank signal, batch upload/detail/rejected download/reprocess, STP batch approval, audit export, two-admin mode change. `tests/test_ui_v2_api.py` 49 pass; `test_p05_hardening` 12 pass; `test_batch_pipeline` 20 pass, 1 skipped. | Load/volume testing of v2 endpoints. Real LLM. |
| Frontend code | `tsc --noEmit` clean; `vite build` passes (Linux copy); Vite dev server serves `/` and proxies `/api/v2` to 127.0.0.1:8000. | Windows build not run by me (you run `npm ci`). |
| Frontend behaviour | Every screen (36 persona/route combinations incl. all 9 case variants, Approvals, Compliance, Batches, Batch detail, Audit, 4 Admin tabs) was RENDERED in jsdom against the live backend: no exceptions, no `undefined`/`NaN`/`[object Object]` in the output, no console errors. Every action wrapper was called against the live backend with the payloads the UI sends. | **No real browser was ever used.** Layout, colours, spacing, fonts, responsiveness, click-through behaviour and the file pickers have not been seen by anyone. Treat visual fidelity to the 14 mockups as unverified. |

## The 14 screens
Persona = who to sign in as (top-right menu). Case ids exist after seeding (see run guide). "Built" means: code exists, renders against live data, actions work through the API. It does not mean pixel-matched.

| # | Mockup | Route | Sign in as | Status | Known gaps |
|---|---|---|---|---|---|
| 01 | Home, maker | `#/home` | Priya Nair | Built | "Open worklist" links only; cutoff times are UTC |
| 02 | Home, supervisor | `#/home` | Elena Marsh | Built | Assign/Escalate/Review buttons navigate, they do not act from Home; Team workload "Reassign" opens the filtered worklist (assign dialog not wired) |
| 03 | Worklist | `#/worklist` | Priya Nair / Elena Marsh | Built | Preview pane highlights any differing characters (not only check digits); saved-view name uses `window.prompt` |
| 04 | Case, validated not yet approved | `#/worklist/case/PEX-INV-0002` (or `PEX-STP-0103`) | Priya Nair | Built | PEX-INV-0001 is seeded as already submitted, so it shows the approval variant (08), not 04 |
| 05 | Case, missing information | `#/worklist/case/PEX-BEN-0012` | Priya Nair | Built | Attach document unavailable (no upload endpoint); "needed" rows use the backend note |
| 06 | Case, conflicting evidence | `#/worklist/case/PEX-CON-0031` | Priya Nair | Built | Disambiguation candidates exist only on CON-0031 (NAM-0027 has none) |
| 07 | Case, status unknown | `#/worklist/case/PEX-TMO-0044` | Priya Nair | Built | Scripted simulated bank: 1st check still unknown, 2nd accepted |
| 08 | Approvals, checker decision | `#/approvals?case=PEX-INV-0001` | Mei Tan | Built | PEX-RET-0035 (AUD 1.79M) shows "limit exceeded" for Mei Tan by design; needs Kenji Watanabe + an administrator |
| 09 | Batch approval modal | Approvals > "Review low-risk batch" | Mei Tan | Built | Total shown as mixed currencies with no FX conversion; limit 25,000 per item (`PEX_BATCH_APPROVAL_MAX`) |
| 10 | Compliance hold | `#/compliance/case/PEX-SAN-0102` | Amara Okafor | Built | Screening system is simulated; "Open in screening system" link is a stub; confirm-block needs a second reviewer (Kenji Watanabe) |
| 11 | Batch detail | `#/batches/<id>` | Priya Nair | Built | Stage timestamps are approximate; counts depend on the file (see run guide) |
| 12 | Case journey A/B/C | A `PEX-INV-0001` (Mei Tan or Priya) · B `PEX-SET-0039` · C `PEX-EXE-0088` | any | Built | Avatars are initials, not photos |
| 13 | Audit events | `#/audit` | Rhea Kapoor (read only) | Built | Exception-type and rail filter option lists are hard-coded in the UI |
| 14 | Admin integrations | `#/admin/integrations` | Tomas Berg (+ Alex Whitfield as second admin) | Built | All six systems are simulated; Live write-back is display only |

Admin sub-tabs (Roles and permissions, Policies, Exception types) are read-only. Old AG screens (Command Center, Intake, Analytics, Investigations, SWIFT/ISO, Ontology, Governance, Architecture, Copilot) are kept, unchanged, under Admin > Reference screens.

## Fixed during integration
- Seeded baseline cases carried cutoffs that had already passed (Worklist/Home showed "Passed"): the seed now re-spreads them 3-9 h ahead. Re-seed shortly before a demo.
- PEX-CON-0031 had two sources; the design shows three (instruction + directory agree, invoice differs). Rebuilt with real valid IBANs.
- A maker opening a compliance-hold case got "Not available for your role"; now sees the case with the "do not contact the customer" banner and disabled repair actions.
- Sidebar visibility now mirrors the server's per-role navigation (e.g. makers no longer see Audit, which returned 403). Case links work for every role.
- Default persona is now Priya Nair (maker) so the first screen is design 01.
- New script `scripts/make_ui_test_batch.py` for the manual batch JSON test.

## Things I noticed and did not change
- Releasing a compliance hold moves the case straight to "Handed to bank (simulated)". Product question: should a released hold go back through approval first?
- Log noise `FolderInputAdapter ingestion note: 'str' object has no attribute 'model_dump'` during batch processing: caught, case creation unaffected, in code this branch did not touch (`FolderInputAdapter`). Needs a proper look.
- Two older file-watcher e2e tests fail identically on the baseline (they expect SETTLED, get SHADOW_RECORDED); `test_p0_remediation` needs `PEX_ALLOW_LEGACY_TOKENS=true` and a writable DB path.
- Repo noise not to commit: `.fuse_hidden*`, `backend/pex_demo_run.db-shm/-wal`, `pex_enterprise.db-wal`, stale `.git/stale-*` lock files.
- The earlier "first page load took almost a minute" was not reproduced here: the backend answers in 10-50 ms after a 3 s start. Most likely Vite's first dependency pre-bundle or antivirus scanning `node_modules` on Windows. If it recurs, send the browser Network tab timings.

## Not production-ready yet
Auth is demo personas with signed tokens (no SSO, no password, no session expiry UX). Everything bank-facing is simulated (payment engine, screening, directories, core ledger). SQLite single node, in-process workers, no queueing or retry policy. No real LLM tested (local Qwen path exists but was never run). No multi-tenant isolation. No accessibility audit, no cross-browser or mobile test, no automated browser tests. Audit chain is real but not externally anchored. Time is shown in UTC. Policy thresholds are read-only in the UI. No performance test of the v2 screens at 100k cases (the batch pipeline was run at 100k earlier, before these changes).
