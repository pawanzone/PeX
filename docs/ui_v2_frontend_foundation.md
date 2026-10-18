# PeX UI v2 — frontend foundation

Branch `ui/v2`. Scope: `frontend/` only. Gate: `npx tsc --noEmit` clean; `npm run build` green (verified in a Linux copy because the mounted `node_modules` holds Windows binaries).

## What exists
- **Shell** (`src/shell/`): navy sidebar with 7 areas (Home, Worklist, Approvals, Compliance, Batches, Audit, Admin), top bar (search -> `#/worklist?q=`, mode and bank chips from `/api/system/info`, "Demo data" chip, clock, persona menu). Persona menu uses `/auth/personas` + `/auth/login`; last choice remembered in localStorage (`pex.v2.persona`), default APR-3191. Role-aware nav in `nav.ts` (convenience only; server enforces). Hidden areas show a "Not available for your role" banner on direct URL.
- **Router** (`src/lib/router.ts`): hash routes `#/home`, `#/worklist`, `#/worklist/case/<id>`, `#/approvals`, `#/compliance`, `#/compliance/case/<id>`, `#/batches`, `#/batches/<id>`, `#/audit`, `#/admin/<section>`; `routes.*` helpers, `useRoute`, `useQueryParam`, `navigate`.
- **Tokens**: `tailwind.config.js` (navy, surface, `pex.*` semantic colours, `rounded-card`, `shadow-card`, mono font) and `src/styles/tokens.css`.
- **Components** (`src/components/v2`, import from the barrel): PageHeader, Breadcrumbs, Tile, StatusPill, Banner, Tabs (with counts, arrow keys), FilterBar, FilterSelect, SavedViewsMenu, DataTable (selectable), EvidenceTable, FieldDiff, SourceCard, ConfirmCheckbox, ReasonCommentFields, CaseHeader, NextActionCard, CaseJourney (data-driven; variants awaiting_approval/handed_to_bank/executed), ActionBar (disabled actions carry visible reasons), Modal (focus trap, Esc), Avatar, KeyValueList, CountdownText, Loading/Empty/ErrorState, Toast (`ToastProvider`, `useToast`).
- **API client** (`src/services/v2/client.ts`): `v2Get/v2Post/v2Put` under `/api/v2`, `useV2` (stale-safe, `unavailable` flag for 404/501), `useAction`. Reuses `http.ts` tokens. **No endpoint wrappers yet**: `docs/ui_v2_api_contract.md` did not exist when this was built; add wrappers in `services/v2/index.ts` once it lands.
- **Screen stubs** (`src/screens/*.tsx`): Home, Worklist, CaseView, Approvals, Compliance (takes `id`), Batches, BatchDetail (takes `id`), Audit, AdminIntegrations. Each is a placeholder naming its target design. Screen owners replace only their own file; routing is in `src/App.tsx`.
- **Admin** (`src/screens/Admin.tsx`): tabs Integrations (stub), Reference screens (old AG app, moved to `src/legacy/LegacyApp.tsx`, unchanged apart from import paths, `h-full`, and no forced re-login when a token exists), Component gallery (`#/admin/components`).

## Accessibility
Skip link; ARIA tabs/menus/dialog; visible focus ring; status always has a text label (colour never alone); disabled actions state why.

## Not matched / caveats
- Not viewed in a browser (no browser on the build VM). Visual fidelity to the 14 PNGs is by token and structure only.
- Legacy app is nested inside Admin > Reference; it keeps its own sidebar/header. Its persona label follows the v2 persona, but its own persona modal still works.
- `areaAllowed` guesses roles for any new persona roles (unknown roles: no Admin; Compliance only if the role name contains COMPLIANCE or SUPERVISOR). Revisit when the backend personas land.
- Gallery journey data is illustrative, not from the contract.
