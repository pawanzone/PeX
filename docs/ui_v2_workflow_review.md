# UI v2 workflow review: AG's workflow guide vs what exists

Branch `ui/v2`. Source guide: `PEX-DOC-UI-WF-2026-v1.0` (AG's "Complete UI Workflows & Interaction Architecture Guide").
Facts come from code inspection (`git grep` on `demo/p05` and on the `ui/v2` working tree) and from `docs/ui_v2_status.md` and `docs/ui_v2_backend_report.md`.
Verification level: code reading plus the tests and HTTP smoke recorded in those two files. **No screen has been viewed in a real browser.**

## 1. Why you saw different screens than the guide describes

The guide describes the **generated frontend** built by `build_guided_frontend.py` (9,181 lines, a single generated app with a font-scale control, notification bell, expedite ping, rules studio, STP drawer and so on). The **React app** in `frontend/` (React 18, Vite, Tailwind) is a different code base. On `demo/p05` the React app had only these screens: Command Center, Intake, Worklist, Approvals, Batches, Investigations, Analytics, SWIFT/ISO, Ontology, Copilot, Controls & Governance, Architecture (see `frontend/src/components/Layout/Sidebar.tsx`).

A search of `demo/p05:frontend/src` finds no calls to `run-ai-repair`, `submit-to-checker`, `disambiguate-hypothesis`, `ping-approver`, `stp/batch-release`, `/rules/*` or `icd-configs`. Those backend endpoints exist (`backend/app/api/endpoints/cases.py`, `actions.py`, `stp.py`, `rules.py`), but the React app never offered them. So several guide workflows were backend-only in the React app, and the guide was not "implemented" there. The guide's header says "codebase-aligned"; for the React app that is not accurate.

## 2. Summary table

Legend. p05 = React app on `demo/p05`. v2 = React app on `ui/v2`. Decision: KEEP, CHANGED, REPLACED, DEFERRED.

| # | Guide workflow | In React p05? | In v2 now? | Decision |
|---|---|---|---|---|
| 1 | Auth, personas, RBAC | Partly: login modal, 9 personas | Yes: persona menu, 17 personas, role-aware nav | CHANGED (demo-only switcher) |
| 2 | Command Center, cutoff radar | Yes (`Dashboard/CommandCenter.tsx`), no radar | Yes, as Home (maker, supervisor); old screen under Admin > Reference | REPLACED by role Home |
| 3 | Payment Intake | Yes (`Intake/PaymentIntake.tsx`) | Old screen under Admin > Reference; batch upload on Batches | CHANGED (batch JSON is the main intake) |
| 4 | Exception Worklist | Yes, server-side filter/sort/page | Yes: tabs, saved views, preview, assign | KEEP (reshaped into tabs) |
| 5A | Maker flow (AI repair, submit with notes) | Backend only | Yes: submit needs handover note; no "Run AI repair" button | CHANGED |
| 5B | Hypothesis disambiguation | Backend only | Yes on conflict cases (rationale required) | KEEP |
| 5C | Checker approve / return / reject | Approve and reject only | Yes, incl. return, reason codes, reviewed checkbox | KEEP + extended |
| 5D | Compliance clear / KYC waiver | Backend only | Compliance screen: release hold, confirm match, escalate; no waiver | CHANGED |
| 5E | Tier-2 dual authorisation | Yes (AWAITING_SECOND_APPROVAL) | Yes, distinct approvers, 250,000 | KEEP |
| 5F | Outbound dispatch | Button "execute action" | No separate button: approval hands to simulated bank | REPLACED |
| 6 | Expedite ping, notification bell | Backend only | Backend only (`/ping`, `/notifications`); no UI | PARTIAL, UI DEFERRED |
| 7 | STP fast-lane drawer | Backend only | Yes: Batch approval modal; limit 25,000 supervised, 10,000 autonomous | CHANGED |
| 8 | Rules & Policy Studio | Backend only | Not in UI; read-only Policies tab | DEFERRED |
| 9 | Investigations ledger | Yes | Audit screen (filters, detail, export, integrity); old screen in Reference | REPLACED by Audit |
| 10 | Operations Analytics | Yes | Old screen under Admin > Reference | DEFERRED to Admin |
| 11 | SWIFT / ISO center | Yes | Old screen under Admin > Reference | DEFERRED to Admin |
| 12 | Skills Hub / SOPs | No (only SOP names in Copilot text) | No | DEFERRED |
| 13 | Ontology / 41 profiles | Yes | Old screen in Reference; Exception types tab (read-only) | KEEP under Admin |
| 14 | Trust Center, token vault | Partly (Governance: chain verify) | Old screen in Reference; Roles tab; no vault simulator | CHANGED / DEFERRED |
| 15 | AI Copilot | Yes | Old screen under Admin > Reference | KEEP (advisory) |
| 16 | Architecture | Yes | Old screen under Admin > Reference | KEEP under Admin |
| 17 | Persona matrix | n/a | Server-enforced rules; matrix differs (see section 17) | CHANGED |
| Shell | Header items (font scale, integrity pill, bell) | Partly | New header: search, chips, clock, persona; no font scale, no bell | CHANGED |

## 3. Workflow 1: Authentication, personas, RBAC
- **p05:** `Auth/LoginModal.tsx`, signed demo tokens in `backend/app/core/auth.py`, personas in `backend/app/core/security.py` (OP-9012, OP-1001, OP-9013, OP-8472, APR-3191, CMP-4420, CMP-5502, RSK-7714, ADM-0001).
- **v2:** persona menu in the header (`frontend/src/shell`), default persona Priya Nair. Eight personas added (Elena Marsh, Mei Tan, Marcus Lee, Sofia Rossi, Chen Wei, Amara Okafor, Rhea Kapoor read only, Tomas Berg). Nav visibility follows `GET /api/v2/me` (`backend/app/services/v2/core.py`).
- **Decision: CHANGED.** Segregation of duties and approver limits are kept and enforced server-side (persisted `maker_id`, also checked by name and email). The switcher is for demo only; production needs SSO, and the limits come from policy, not hard-coded personas. The guide lists six personas; v2 has more because the mockups imply supervisor, audit and administrator roles. Named differences: the mockup compliance officer is Amara Okafor, while the guide has Marisol Vega (CMP-4420, still present).

## 4. Workflow 2: Command Center and cutoff radar
- **p05:** `Dashboard/CommandCenter.tsx`. No clearing-rail radar with ticking countdowns found by grep.
- **v2:** `#/home` (`screens/home/MakerHome.tsx`, `SupervisorHome.tsx`), fed by `GET /api/v2/home`. Cutoff risk by rail and today's outcomes are computed from real data. Outcome bar separates bank-confirmed from handed-to-bank.
- **Decision: REPLACED** by role-specific Home, because makers and supervisors need different first screens. The old Command Center stays under Admin > Reference. Not carried over: "STP Realization Rate" and "SLA Breaches Prevented" cards, because the demo has no measured baseline (an unmeasured number would mislead). Cutoff times are UTC; the guide uses ET/CET/UK local rail cutoffs. Home buttons on the supervisor view only navigate.

## 5. Workflow 3: Payment Intake
- **p05:** `Intake/PaymentIntake.tsx` posts a single exception (`/api/events/ingest`).
- **v2:** the old form is under Admin > Reference. The main intake is batch JSON upload on `#/batches` (`POST /api/v2/batches/upload`, falls back to `/api/batch/upload`) plus "Generate demo batch".
- **Decision: CHANGED.** A bank ingests files and feeds, not hand-typed exceptions. Single-record entry remains as a reference/test tool.

## 6. Workflow 4: Exception Worklist
- **p05:** `Worklist/ExceptionWorklist.tsx` with server-side filter, sort and paging (`/api/cases/page`).
- **v2:** `#/worklist`, five tabs (Ready to work, Returned to me, Waiting for information, Pending approval, Done today), filters, saved views, preview pane, assign (`/api/v2/worklist*`).
- **Decision: KEEP** the idea (filter, sort, claim) in a tab layout aligned to the mockup. Not built: "Run AI Reasoner on All Open Cases" (batch synthesis button). Reason: in the batch pipeline, recommendations are produced at ingest; a manual "re-run on everything" button adds risk and no value in the demo. Expedite-ping badge, 2-EYE badge and AI confidence gauge are not shown in the v2 table.

## 7. Workflow 5A: Maker flow
- **p05:** backend `run-ai-repair` and `submit-to-checker` existed; React did not call them.
- **v2:** case page decision variant (`screens/case/CasePage.tsx`). `POST /api/v2/cases/{id}/submit` requires a handover note and optional attachment name, and records `maker_id`. Evidence table has a "view source" popup.
- **Decision: CHANGED.** No "Run AI Repair" button: recommendations arrive with the case (and "Reassess" is offered when evidence changes). The five-step dossier becomes a per-check evidence table with Authority and Status columns.

## 8. Workflow 5B: Hypothesis disambiguation
- **v2:** conflict variant (`PEX-CON-0031`) shows three source cards, a "why STP is blocked" list and a disambiguation form needing a rationale (`POST /api/v2/cases/{id}/disambiguate`, audited).
- **Decision: KEEP.** Gap: candidates exist only on seeded `PEX-CON-0031`.

## 9. Workflow 5C: Checker decision
- **p05:** approve and reject through `Approvals/ApprovalsWorkspace.tsx`.
- **v2:** `#/approvals`, decision panel with "I reviewed the evidence" checkbox, Approve for bank handoff, Return to Maker, Reject (reason code and comment required). Server-side checks: SoD, limit, second approver.
- **Decision: KEEP**, wording changed from "Authorize" to "Approve for bank handoff". The diff view highlights characters that differ, not only the check digits. The IBAN in AG's example (`GB82WEST12345698765423`) is the well-known GB82 test IBAN family; the backend seed uses values verified with MOD-97, and the report says the design's illustrative values may not validate.

## 10. Workflow 5D: Compliance and sanctions
- **p05:** backend `CLEAR_FALSE_POSITIVE` and `GRANT_KYC_WAIVER` in `approval_engine.py`; no React UI.
- **v2:** `#/compliance` and `#/compliance/case/<id>`: alert, party-versus-listed-entity table, decisions Release hold (false match), Confirm match and block (needs a second reviewer), Escalate. Each needs reason code and comment. No repair actions.
- **Decision: CHANGED.** Compliance holds never offer repair. KYC waiver is not in v2 (a waiver is a policy exception that needs its own approval design). Decided 18 Oct: clearing a hold returns the payment to the approval queue; a Risk Approver (not the person who cleared it) authorises any bank handoff.

## 11. Workflow 5E: Tier-2 dual authorisation
- **p05:** `AWAITING_SECOND_APPROVAL` supported (`state_machine.py`, `approval_engine.py`).
- **v2:** at or above 250,000 (`DUAL_AUTH_THRESHOLD`), two distinct approvers; the first cannot approve twice. `PEX-RET-0035` (AUD 1.79M) needs Kenji Watanabe plus an administrator.
- **Decision: KEEP.** Threshold is a USD-equivalent in config; the v2 logic compares the raw amount (no FX conversion). Production needs FX and a policy-driven threshold.

## 12. Workflow 5F: Outbound dispatch
- **p05:** an "execute action" button in the approvals view.
- **v2:** no separate dispatch button. Approving in ASSISTED or LIVE hands the case to the simulated bank through `services/outbound_port.py`; SHADOW records only (`SHADOW_RECORDED`).
- **Decision: REPLACED.** One handoff choke point. "Executed by bank" appears only after the signed inbound bank signal (`POST /api/bank/outcome`, `X-Bank-Signature`); a handed-to-bank case shows amber "awaiting bank confirmation". The guide's `HANDED_TO_BANK` with `AWAITING_BANK_ACK` is displayed as "Handed to bank". PeX never settles or executes.

## 13. Workflow 6: Expedite ping and notification bell
- **p05:** `POST /api/actions/ping-approver` exists (`actions.py`); no UI.
- **v2:** backend `POST /api/v2/cases/{id}/ping`, `GET /api/v2/notifications`, `POST /api/v2/notifications/{id}/read` exist and are covered by the backend work. A grep of `frontend/src/screens`, `shell` and `services/v2` finds no bell, no ping button and no wrapper.
- **Decision: KEEP the workflow; UI DEFERRED.** Add a header bell and a "Send reminder" action on pending cases. This is a gap against the guide.

## 14. Workflow 7: STP fast lane
- **p05:** `stp/eligible`, `stp/batch-release` in `api/endpoints/stp.py`; no React drawer.
- **v2:** "Review low-risk batch" modal on Approvals (`approvals/BatchApprovalModal.tsx`), `GET /api/v2/stp/review`, `POST /api/v2/stp/approve`, with grouped not-eligible reasons.
- **Decision: CHANGED.** The guide's single limit of $100,000 (and "unified risk envelope") is replaced by two configurable limits: autonomous STP `PEX_STP_MAX_AMOUNT` (default 10,000) and supervised one-click batch `PEX_BATCH_APPROVAL_MAX` (default 25,000, a human approves). The batch needs a named human; it is not autonomous. Total value is shown across mixed currencies without FX conversion.

## 15. Workflow 8: Rules and Policy Studio
- **p05:** backend endpoints in `rules.py` (synthesize, simulate, submit, approve, reject, ICD configs); no React screen.
- **v2:** no screen. Admin > Policies is read-only (thresholds, STP limit, dual-auth, micro-repair rule).
- **Decision: DEFERRED.** A natural-language-to-rule screen needs the rule engine behind change control before it belongs in a bank demo. Backend endpoints remain available.

## 16. Workflows 9 to 16, other screens
- **Investigations ledger (9):** replaced by `#/audit` (filters, detail with before/after, SoD result, hash check, CSV export, case report). The guide's Merkle chain banner exists in the old Governance screen (`verifyAuditChain`). Chain is real but not externally anchored.
- **Analytics (10), SWIFT/ISO (11), Ontology (13), Architecture (16):** old screens kept unchanged under Admin > Reference. Not audited for hard-coded values.
- **Skills Hub (12):** not in either React version; only `/api/copilot/sops` and `/skills/active` exist in the backend. DEFERRED.
- **Trust Center (14):** the old Governance screen has chain verification; the token-vault tokenizer demo is not in the React app. DEFERRED. The Roles tab on Admin shows the authority matrix from the server.
- **Copilot (15):** old screen kept. Local LLM gateway is advisory only and has never been run with a real model.

## 17. Persona matrix (guide section 19) vs v2
Server rules in v2 (`tests/test_ui_v2_api.py`): makers cannot approve; checkers cannot submit; approver limits apply; dual authorisation needs distinct approvers; Audit and Risk is read-only (writes return 403); compliance decisions are for compliance roles; only compliance can confirm-block with a second reviewer. Differences from the guide's matrix: the guide lets Compliance and Risk approvers approve ordinary payments up to their limits and gives Admin "Authorize" everywhere; v2 gives the administrator no approval authority (Tomas Berg limit 0), and the Rule Studio rows do not apply (no screen).

## 18. Shell and header (guide section 2)
New header: search box, mode and bank-simulated chips, "Demo data" chip, clock, persona menu. Not carried over: font-scale control (A A A) and notification bell, and the SHA-256 integrity pill (the integrity check is on the Audit screen). Batch Home buttons and the clock use UTC, not local time.

## 19. Gaps still open
1. Notification bell and expedite-ping UI (backend exists).
2. Rules and Policy Studio screen (backend exists); policy thresholds are read-only.
3. Skills Hub / SOP screen and token-vault demonstration.
4. KYC waiver action.
5. "Run AI reasoner on all cases" bulk action.
6. Highlight of check digits in the diff (the UI highlights any differing characters).
7. Supervisor Home action buttons only navigate; Team workload "Reassign" not wired.
8. FX conversion for thresholds and batch totals; times in UTC.
9. Reference screens (Analytics, SWIFT/ISO, Ontology, Architecture, Copilot) not audited for hard-coded status.
10. Nothing has been rendered in a real browser; visual fidelity to the 14 mockups is unverified.
11. Old AG generator `build_guided_frontend.py` and the React app remain two separate code bases; the guide should be rewritten against the React app.
