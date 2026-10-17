# P0.5 UI report

Scope: `demo_build/frontend` (React 18, Vite, Tailwind, TypeScript strict). Backend and git untouched.
Verification: `npx tsc --noEmit` clean, `npm run build` succeeds. No browser was available in the VM, so nothing was checked visually. Please click through once.

## How to run
```
cd frontend && npm ci && npm run dev      # http://localhost:5173, proxies /api to :8000
# backend: PEX_DEMO=true must be set, otherwise persona login is refused (the UI shows a banner)
```

## Changes by file
New:
- `src/lib/statusMeta.ts`: single source for lifecycle labels, tone, terminal/waiting flags, filter options, SLA colour (<1h red, 1-3h amber, >3h grey). DISPATCHED/HANDED_TO_BANK reads "Handed to bank, awaiting confirmation"; only EXECUTED_CONFIRMED and SETTLED read as bank-confirmed.
- `src/services/http.ts`: central fetch client, bearer token in one place (localStorage in try/catch, memory fallback), `ApiError`, 401/403 listener, download helper.
- `src/hooks/useSystemInfo.ts`, `useSummaryCounts.ts` (polling).
- `src/components/common/`: `StatusBadge`, `SimulatedChip` (+ `SimText` turns "[SIMULATED]" into a chip), `NotMeasured` / `MeasuredValue`, `Pagination`, `States` (empty, error with retry, loading), `CaseJourney` (vertical timeline, role icons, bank banner).
- `src/components/Batches/BatchesPage.tsx`: drag-drop JSON/JSONL upload, "Generate demo batch" (count, rails), list with 2s polling while QUEUED/PROCESSING, summary cards, results download.

Modified:
- `types/index.ts`: new lifecycle states, `SystemInfo`, `CasePage`, `SummaryCounts`, `BatchRecord`, optional maker/dispatch/LLM fields.
- `services/api.ts`: rebuilt on the central client, same exports kept. `fetchCasesPage` calls `/cases/page`, falls back to `/cases` (filtered in browser) if missing. `fetchSummaryCounts` falls back to deriving counts from `/cases`. Added system info and batch calls. Token no longer sent as a user id.
- `App.tsx`: no longer loads all cases. Auto-signs in default persona, shows a banner if login is disabled or rejected, header search runs the worklist search on Enter, badges from `/api/summary/counts`.
- `Layout/Header.tsx`: mode chip (SHADOW/ASSISTED/LIVE with tooltip), "Bank communication: SIMULATED", LLM chip. Removed the static "NO BANK TRAFFIC" chip.
- `Layout/Sidebar.tsx`: Batches tab; badges Repair=`actionable_repair`, Approvals=`pending_approvals_all`, Investigations=Investigation-queue count (not audit events). Static "ONLINE" replaced by "DEMO".
- `Worklist/ExceptionWorklist.tsx`: server paging (50), filters (queue, status, type, rail, currency), debounced search, sort + direction, empty/error states.
- `Approvals/ApprovalsWorkspace.tsx`: paged left list ("Needs approval" / "All"), SLA colours from real due time, `StatusBadge`, case journey below the decision bar, action bar with disabled-with-reason (maker-checker, already approved, over limit, no approval pending, SHADOW suppresses dispatch). Removed hardcoded "1h 45m", "MOD-97 PASS", "Dispatched & Settled!", "Settle Against Banking Rails", "Fully Settled & Reconciled". Dispatch button is "Hand to bank adapter" and the message says the bank must confirm.
- `Dashboard/CommandCenter.tsx`: "GLOBAL TIER-1" and fallback dates/96% confidence removed, bars scaled from data, resolution rate shows "Not measured" unless `measured:true`, velocity chart tagged DEMO DATA, peak throughput and SLA target "Not measured".
- `Analytics/OperationsAnalytics.tsx`: rewritten. Removed 94.2%, $1,482,000.00, 42s, hardcoded profile split and "100% enforced"/"Zero PII leakage" claims. Distributions come from counts; STP rate only when measured; avg resolution time and savings are "Not measured". Controls shown as design intent.

## Assumptions about backend contracts (verify when the batch/system work lands)
- `GET /api/cases/page` returns `{items,total,limit,offset}` and accepts `limit, offset, queue, status, profile, rail, currency, q, sort, order`.
- `GET /api/summary/counts` returns `total, by_status, by_queue, by_profile, by_rail, actionable_repair, pending_approvals_all`; optional `pending_approvals_my_desk` is used for the badge tooltip if present.
- Batch: `POST /api/batch/upload` (multipart `file`), `GET /api/batch` (array or `{items}`), `GET /api/batch/{id}`, `POST /api/batch/generate?count&seed&rails=a,b`, `GET /api/batch/{id}/results`. Field names `id/total_records/processed_records/failed_records` are also accepted. Adjust `services/api.ts` if the batch fork chose different routes.
- Approvals use `maker_id` on the case and `approval_history[].approver_id`. If absent, maker-checker is still enforced by the backend, the UI just will not pre-disable the button.

## Not done / left from the 14-screen target design
- Not visually verified, no component tests.
- Still static or unverified claims: `ArchitectureWorkflows` (all "ONLINE" statuses, "Zero autonomous execution" copy), `SwiftIsoCenter`, `ControlsGovernance`, `PaymentOntology`, `AiCopilot`, `PaymentIntake` were not audited or changed.
- `InvestigationsHub` still shows the audit stream rather than an Investigation-queue worklist.
- No "my desk" separation in the Approvals list (needs a backend filter on assignee), no bulk actions, no case search by IBAN/BIC, no role-specific home screens, no batch detail drill-down page, no per-case LLM disagreement panel (types are ready: `llm_status`, `llm_disagreement`).
- Bundle is one chunk (279 kB), no code splitting.
