# PeX UI v2 – API contract (`/api/v2`)

Status: **v1.0** (stable). Later changes are listed in *Change log* at the bottom.
All bank communication is **SIMULATED**. PeX never executes or settles a payment: the strongest state PeX reaches is
`DISPATCHED` ("Handed to bank, awaiting confirmation"). `EXECUTED_CONFIRMED`/`SETTLED` only come from the signed inbound bank signal (`/api/bank/outcome`).

## 0. Conventions
* Base: `/api/v2`. JSON. Auth: `Authorization: Bearer <token>` from `POST /api/auth/login {user_id}` (demo personas, `PEX_DEMO=true`). Identity is **always from the token**.
* Timestamps: ISO-8601 UTC (`2026-10-16T11:46:00+00:00`). Every response that depends on time carries `now`. Display strings (`time_left`, `hhmm`) are provided as UTC.
* Money: `{"amount": 8650.0, "currency": "GBP", "display": "GBP 8,650.00"}`.
* Cutoff: `{"at": ISO, "hhmm": "14:00", "seconds_left": 8040, "time_left": "2h 14m", "band": "under_1h|1_to_3h|over_3h|passed"}`.
* Chip: `{"label": "Invalid IBAN", "tone": "neutral|info|warn|danger|success"}`.
* Action: `{"key": "submit", "label": "Submit for approval", "kind": "primary|secondary|danger", "enabled": true, "disabled_reason": null, "endpoint": "/api/v2/cases/PEX-INV-0001/submit"}`.
* Paging: `?page=1&page_size=25` -> `{"page":1,"page_size":25,"total":87,"items":[...]}`.
* Idempotency: action POSTs accept optional header `Idempotency-Key`; a repeated key returns the first result (`"replayed": true`).
* **Errors** (all v2 routes): HTTP status + body
  `{"error": {"code": "SOD_VIOLATION", "message": "human readable", "field": null}, "detail": "human readable"}`.
  Codes: `AUTH_REQUIRED`(401) `FORBIDDEN`(403) `READ_ONLY_ROLE`(403) `SOD_VIOLATION`(403) `LIMIT_EXCEEDED`(403) `NOT_FOUND`(404)
  `INVALID_STATE`(409) `CONFLICT`(409) `VALIDATION`(422, `field` set when known) `SECOND_REVIEWER_REQUIRED`(409) `SECOND_ADMIN_REQUIRED`(403).

## 1. Roles and permissions
Roles (`user.role`): `OPERATOR` (Maker / analyst), `SUPERVISOR`, `OPERATIONS_APPROVER`, `COMPLIANCE_APPROVER` (Compliance Officer), `RISK_APPROVER` (tier 2), `AUDIT_RISK` (read only), `ADMIN`.
Personas (login ids): OP-9012 Priya Nair (Maker), OP-9020 Marcus Lee, OP-9021 Sofia Rossi, OP-9022 Chen Wei (analysts), SUP-2001 Elena Marsh (Supervisor),
APR-3191 Daniel Osei (Ops Approver, $250k), APR-3192 Mei Tan (Operations Approver, $250k), CMP-6001 Amara Okafor (Compliance Officer), RSK-7714 Kenji Watanabe (tier 2, $10M),
AUD-5001 Rhea Kapoor (Audit and Risk, read only), ADM-0001 Alex Whitfield, ADM-0002 Tomas Berg (Administrators). Old personas stay.

| Permission | OPERATOR | SUPERVISOR | OPS_APPROVER | COMPLIANCE | RISK | AUDIT_RISK | ADMIN |
|---|---|---|---|---|---|---|---|
| `case.read` | y | y | y | y | y | y | y |
| `case.work` (submit, request-info, reassess, start-verification, check-status, disambiguate, escalate) | y | y | – | – | – | – | – |
| `case.assign` (assign to me) | y | y | – | – | – | – | – |
| `case.reassign` | – | y | – | – | – | – | – |
| `case.approve` / `return` / `reject` (checker) | – | – | y | – | y | – | y* |
| `stp.approve` | – | – | y | – | y | – | – |
| `compliance.decide` | – | – | – | y | y | – | – |
| `audit.read` / `audit.export` | – | y (read) | – | – | – | y | y |
| `admin.read` | – | – | – | – | – | – | y |
| `admin.mode_change` / `admin.mode_approve` (second admin) | – | – | – | – | – | – | y |

\* ADMIN keeps legacy ability but is still subject to SoD and limits. SoD is enforced server side from the persisted `maker_id` AND same person identity (name/email).
Checker limit: persona `max_approval_amount` ($250k for ops approvers). Above it: `LIMIT_EXCEEDED` (escalate to tier 2). Amounts >= 250,000 are dual-authorisation (level 1 then a different tier-2 approver).
AUDIT_RISK is read only: every non-GET returns `READ_ONLY_ROLE` 403.

## 2. `GET /api/v2/me`
```json
{"user": {"user_id":"OP-9012","name":"Priya Nair","role":"OPERATOR","role_label":"Maker","title":"Payments Analyst","initials":"PN","email":"p.nair@pexbank.internal","max_approval_amount":0},
 "permissions": ["case.read","case.work","case.assign"],
 "nav": [{"key":"home","label":"Home","path":"/"},{"key":"worklist","label":"Worklist","path":"/worklist"}],
 "mode": "ASSISTED", "bank_comm": "SIMULATED", "demo": true, "now": "2026-10-16T11:46:00+00:00",
 "stp_limit": {"amount": 10000, "currency": "USD", "label": "Micro-repair limit"}}
```
Nav by role: OPERATOR Home, Worklist, Batches; SUPERVISOR Home, Worklist, Approvals, Compliance, Batches, Audit; OPS/RISK approver Home, Approvals, Worklist, Batches; COMPLIANCE Home, Compliance, Audit; AUDIT_RISK Audit; ADMIN Home, Batches, Audit, Admin.

## 3. `GET /api/v2/home`
`role_view` is `MAKER | SUPERVISOR | APPROVER | COMPLIANCE | AUDIT | ADMIN`.
**MAKER**
```json
{"role_view":"MAKER","now":"...","greeting":"Good morning, Priya",
 "act_now":[{"case_id":"PEX-RET-0035","exception":"Returned payment","amount":{...},"cutoff":{...},"next_action":"Review return","next_action_type":"RESOLVE_RETURN","reason":"Returned by approver","link":"/cases/PEX-RET-0035"}],
 "tiles":{"ready":24,"returned":2,"waiting":9,"pending":12,"done_today":31},
 "ready_by_cutoff":[{"band":"under_1h","label":"Under 1 hour","count":2},{"band":"1_to_3h","label":"1 to 3 hours","count":8},{"band":"over_3h","label":"Over 3 hours","count":14}],
 "waiting_on_others":[{"case_id":"PEX-BEN-0012","waiting_for":"Client reply","party":"Nordhavn Components A/S","since":"ISO","due":"ISO","overdue":false}],
 "returned_to_me":[{"case_id":"PEX-RET-0035","returned_by":"Daniel Osei","returned_at":"ISO","comment":"..."}]}
```
**SUPERVISOR**
```json
{"role_view":"SUPERVISOR","now":"...","title":"Operations overview",
 "tiles":{"open":95,"unassigned":14,"under_1h":7,"waiting_too_long":3,"pending_approval":12,"resolved_today":64},
 "cutoff_risk":[{"rail":"SWIFT CBPR+","rail_key":"SWIFT_CBPR+","next_cutoff":{...},"open":38,"at_risk":4}],
 "outcomes_today":{"executed_by_bank":58,"handed_to_bank_awaiting":6,"resolved_total":64,"resolved_without_manual_repair":22,"policy_approved":22,"percent_without_manual_repair":34.4,"note":"..."},
 "team_workload":[{"user_id":"OP-9020","name":"Marcus Lee","open":9,"under_1h":1,"returned":0,"oldest":"1h 12m","oldest_case_id":"...","can_reassign":true}],
 "approver_queue":[{"user_id":"APR-3191","name":"Daniel Osei","pending":7,"oldest":"22m"}],
 "compliance_note":"Compliance cases are managed in the Compliance workspace.",
 "needs_decision":[{"kind":"STATUS_CHECK_OVERDUE|UNASSIGNED|CONFLICT_UNRESOLVED","case_id":"PEX-TMO-0044","title":"Status check overdue 11m","action":{"label":"Escalate","key":"escalate"},"link":"/cases/..."}]}
```
**APPROVER**: `{"role_view":"APPROVER","tiles":{"pending":..,"mine_oldest":"..","above_my_limit":..,"batch_eligible":..},"queue":[worklist rows],"stp_batch":{"eligible":12,"total_value":[{"currency":"GBP","amount":..}]}}`.
**COMPLIANCE**: `{"role_view":"COMPLIANCE","tiles":{"open_holds":..,"escalated":..,"oldest":".."},"queue":[rows]}`. **AUDIT**: `{"role_view":"AUDIT","tiles":{"events_today":..,"blocked":..,"sod_checks_passed":..}}`. **ADMIN**: `{"role_view":"ADMIN","tiles":{"integrations":6,"degraded":1,"pending_mode_changes":..}}`.

## 4. Worklist
`GET /api/v2/worklist?tab=ready|returned|waiting|pending|done&page=&page_size=&exception_type=&rail=&currency=&cutoff_band=&evidence=&q=&sort=cutoff|amount|case&dir=asc|desc&view=<saved view id>&scope=mine|all`
* `scope` default: OPERATOR `mine`+unassigned; SUPERVISOR `all`. `evidence` = `complete|conflict|missing|compliance`.
* Tab rules: **ready** = open, no pending info/compliance, not returned, not waiting, not pending approval, not done (assignee me or unassigned). **returned** = RETURNED_FOR_REWORK assigned to me. **waiting** = request-information outstanding / STATUS_UNKNOWN. **pending** = PENDING_APPROVAL, AWAITING_SECOND_APPROVAL (submitted by me, or all for supervisor/approver). **done** = DISPATCHED, EXECUTED_CONFIRMED, SETTLED, REJECTED, SHADOW_RECORDED changed today.
```json
{"tab":"ready","counts":{"ready":24,"returned":2,"waiting":9,"pending":12,"done":31},"page":1,"page_size":25,"total":24,
 "facets":{"exception_types":[{"value":"DQ-01","label":"Invalid IBAN","count":9}],"rails":[{"value":"SWIFT_CBPR+","label":"SWIFT CBPR+","count":..}],"currencies":["GBP","EUR"]},
 "items":[{"case_id":"PEX-INV-0001","cutoff":{...},"exception":{"code":"DQ-01","label":"Invalid IBAN","domain":"DATA_QUALITY"},"amount":{...},
   "rail":{"key":"SWIFT_CBPR+","label":"SWIFT CBPR+"},"counterparty":"Harlow & Finch Components Ltd",
   "next_action":{"text":"Submit for approval","type":"SUBMIT"},"evidence":{"status":"complete","label":"Complete"},
   "status":"VALIDATED","variant":"DECISION","assignee":{"user_id":"OP-9012","name":"Priya Nair"},"selected_detail":null}]}
```
`GET /api/v2/worklist/{case_id}/preview` -> right pane: `{"case_id","why_flagged","change":{"field","original","proposed"}|null,"evidence_summary":"5 of 5 sources agree","controls":[{"label","state":"passed|pending|blocked"}],"next_action":{...},"actions":[Action]}`.
Saved views: `GET /api/v2/worklist/views` -> `[{"id":"v1","name":"Under 1h GBP","owner":"OP-9012","filters":{...},"sort":"cutoff","created_at":..}]`; `POST /api/v2/worklist/views {"name","filters":{tab,exception_type,rail,currency,cutoff_band,evidence,q},"sort"}` -> view; `DELETE /api/v2/worklist/views/{id}`.
`POST /api/v2/cases/{id}/assign {"assignee":"me"|"<user_id>"}` -> `{"case_id","assignee":{...},"previous":{...}}`; reassigning someone else requires SUPERVISOR; assigning to self requires `case.assign`.
Approvals queue (checker): `GET /api/v2/approvals?page&page_size&tier=1|2|all` -> same row shape + `submitted_by`, `submitted_at`, `waiting_for`(e.g. "22m"), `can_approve` bool, `cannot_approve_reason`. Compliance queue: `GET /api/v2/compliance/queue` -> rows with `screening_ref`, `raised_at`, `status`.

## 5. `GET /api/v2/cases/{id}/page`
Single payload. `variant` is DERIVED from real state: `DECISION | MISSING_INFO | CONFLICT | STATUS_UNKNOWN | COMPLIANCE_HOLD | APPROVAL | HANDED_TO_BANK | EXECUTED | GENERIC`.
Derivation order: SETTLED/EXECUTED_CONFIRMED -> EXECUTED; DISPATCHED -> HANDED_TO_BANK; STATUS_UNKNOWN -> STATUS_UNKNOWN; compliance domain/queue or sanctions status -> COMPLIANCE_HOLD;
PENDING_APPROVAL/AWAITING_SECOND_APPROVAL -> APPROVAL (viewer is a checker) else DECISION-readonly (`viewer_mode`); evidence CONTRADICTORY -> CONFLICT; evidence INSUFFICIENT/missing mandatory -> MISSING_INFO;
RECOMMENDED/VALIDATED/RETURNED with a validated repair -> DECISION; else GENERIC. `viewer_mode`: `maker|checker|compliance|read_only|supervisor`.
```json
{"case_id":"PEX-INV-0001","variant":"DECISION","viewer_mode":"maker","now":"...",
 "header":{"title":"Invalid IBAN","chips":[{"label":"Data quality","tone":"neutral"},{"label":"Invalid IBAN","tone":"neutral"},{"label":"Validated · not yet approved","tone":"info"}],
   "amount":{...},"cutoff":{...},"uetr":"...","rail":{"key":"SWIFT_CBPR+","label":"SWIFT CBPR+"},"creditor":"Harlow & Finch Components Ltd","debtor":"...","status":"VALIDATED","assignee":{...},"opened_at":"ISO"},
 "banner":{"tone":"info|warn|danger|success","title":"...","text":"..."}|null,
 "decision_brief":{"what_happened":"...","proposed_change":"...","evidence":"5 of 5 sources agree","controls":"Validation passed · one approver required","next":"Submit for approval"},
 "change_summary":{"what_changes":"Creditor IBAN corrected","field":"creditor_account.iban","original":{"value":"GB82 WEST 1234 5698 7654 23","status":"Failed validation","highlight":[22,23]},
   "proposed":{"value":"GB82 WEST 1234 5698 7654 32","status":"Passes validation","highlight":[22,23]},"source":"Standing instruction + BIC and IBAN directory","risk":"Low","policy_basis":"Micro-repair MR-01 · under 25,000 · one approver","if_you_approve":"PeX hands the repaired instruction to the bank payment system. The bank executes and confirms."}|null,
 "sod":{"status":"passed|failed|n/a","text":"You did not prepare this repair","maker":{"user_id":"OP-9012","name":"Priya Nair"},"viewer_is_maker":false},
 "handover":{"note":"...","by":{"user_id":"OP-9012","name":"Priya Nair"},"at":"ISO","attachment":{"name":"INV-2291.pdf"}|null}|null,
 "evidence_table":[{"id":"ev-1","check":"Creditor IBAN checksum","result":"Fails ISO 7064 mod-97","source":"Payment instruction","authority":"Originator","checked_at":"ISO","status":"pass|fail|agree|differs|missing|info","status_label":"Passed","can_view_source":true}],
 "evidence_summary":{"agree":5,"total":5,"label":"5 of 5 sources agree","status":"complete|conflict|missing"},
 "needed":null, "conflict":null, "status_unknown":null, "compliance":null, "request_information":null,
 "recommendation":{"summary":"...","reasoning":["..."],"confidence_label":"Advisory only","predicates":{"e_suff":true,...},"source":"DETERMINISTIC"}|null,
 "journey":{"steps":[{"key":"detected","label":"Detected","actor":"PeX","role":"System","at":"ISO","state":"done|current|pending|not_required|blocked","note":null}],
   "next_action":{"tone":"info|warn|success|danger","title":"Awaiting approval","text":"...","owner":"Approver"}, "audit_events":5,"audit_link":"/audit?case=PEX-INV-0001"},
 "actions":[Action],
 "blocked_actions":[{"label":"Resend payment","reason":"Locked: status unknown, resending could duplicate the payment"}]}
```
Variant specific blocks (null otherwise):
* **MISSING_INFO** `needed`: `{"rows":[{"item":"Beneficiary account (IBAN)","status":"missing|not_required|found","note":null}],"searched":[{"source":"Beneficiary master directory","result":"No record"},{"source":"Prior payments","result":"None found"}]}`; `request_information`: `{"to":{"party":"Nordhavn Components A/S","contact":"Lars Holm","role":"Relationship manager"},"methods":["Email","Phone","Portal"],"method":"Email","message":"...","draft_saved_at":null,"reply_due":"ISO","escalate_at":"ISO","state":"none|draft|sent|overdue|replied","sent_at":null}`. banner: "Required information is missing. PeX has not proposed a repair."
* **CONFLICT** `conflict`: `{"field":"Beneficiary account (IBAN)","sources":[{"name":"Payment instruction","value":"DE89 3704 0044 0532 0130 00","relation":"agrees|differs","authority":"Originator","tag":"Agree","changed_at":null},...],"note":"Both IBANs pass the checksum. Validation alone cannot decide which is correct.","why_blocked":["..."],"next_steps":[{"key":"start_verification","label":"Start verification","enabled":true},{"key":"request_information",...},{"key":"escalate","label":"Escalate to Senior Analyst"},{"key":"prepare_repair","label":"Prepare repair","enabled":false,"disabled_reason":"Locked until conflict is resolved"}],"disambiguation":{"candidates":[{"id":"H1","title":"...","value":"...","confidence":0.0,"source":"DETERMINISTIC"}],"endpoint":"/api/v2/cases/{id}/disambiguate"}|null}`
* **STATUS_UNKNOWN** `status_unknown`: `{"uetr":"...","do_not_resend":true,"known":[{"system":"Bank payment engine","says":"Sent 10:42","as_of":"ISO","state":"ok|unknown|warn"}],"next":[{"outcome":"Not sent","what_happens":"..."},{"outcome":"Accepted by network","..."},{"outcome":"Rejected","..."},{"outcome":"Delivered but misapplied","..."}],"last_check":{"at":"ISO","result":"..."}|null,"check_overdue_minutes":11}`
* **COMPLIANCE_HOLD** `compliance`: `{"alert":{"reference":"SCR-55821","source":"Bank screening system","list":"Sanctions list (bank-configured)","match_type":"Name potential match","raised_at":"ISO","open_url":null,"note":"Simulated: no link to a real screening system"},"party_comparison":[{"attribute":"Name","payment_party":"...","listed_entity":"...","result":"similar|same|differs|not_comparable","label":"Similar"}],"notes":[{"by":"...","at":"ISO","text":"..."}],"attachments":[{"name":"..."}],"decisions":[{"key":"release","label":"Release hold · false match"},{"key":"confirm_block","label":"Confirm match · block payment","needs_second_reviewer":true},{"key":"escalate","label":"Escalate to Senior Compliance"}],"reason_codes":[{"code":"FALSE_MATCH_NAME","label":"False match – different entity"}],"second_review":{"required":false,"state":"none|pending|done","first_reviewer":null},"footer":"The decision is recorded in PeX and passed to the bank. The bank screening system remains the system of record."}`. Non-compliance roles see `banner` "Do not contact the customer about this alert" and all repair actions disabled.
* **APPROVAL** viewer checker: `change_summary`, `sod`, `handover`, `evidence_table` populated, `decision_form`: `{"requires_review_ack":true,"return_reason_codes":[{"code":"EVIDENCE_INSUFFICIENT","label":"..."}],"reject_reason_codes":[...],"footnote":"Next: handed to bank system. Not yet executed.","level":1,"dual_auth":false,"limit_ok":true}`. If viewer is the maker: `sod.status="failed"`, approve disabled with reason.
* **HANDED_TO_BANK**: banner `info` "Handed to bank · waiting for bank confirmation", `handoff`: `{"handoff_id":"HND-48213","sent_at":"ISO","mode":"ASSISTED","bank_comm":"SIMULATED","awaiting":"Bank confirmation"}`; actions: `check_status`.
* **EXECUTED**: banner success, `bank`: `{"reference":"BK-7731902","confirmed_at":"ISO","clearing_system":"..."}`.

Journey steps (always 9, in order): `detected, evidence, recommendation, validated, maker_review, approval_1, approval_2, handed_to_bank, executed` (labels: Detected, Evidence gathered, Recommendation made, Validated, Maker review, Approval level 1, Approval level 2, Handed to bank, Executed by bank). `approval_2.state="not_required"` with `note="Policy: one approver under 250,000"` when not dual-auth. `executed` is `pending` until the bank signal.

Case journey standalone: `GET /api/v2/cases/{id}/journey` -> the `journey` object. Evidence source: `GET /api/v2/cases/{id}/evidence/{evidence_id}` -> `{"id","check","source","authority","checked_at","raw":{...masked},"note":"Simulated source view"}`. Audit for case: `GET /api/v2/audit/events?case_id=`.

## 6. Case actions (all POST, audited via `transition_case`, response `{"ok":true,"case_id":"...","status":"...","variant":"...","message":"...","next":{...},"page_url":"/api/v2/cases/{id}/page"}`)
| Endpoint | Role | Body | Notes |
|---|---|---|---|
| `/cases/{id}/submit` | maker | `{"handover_note":"required","attachment_name":null}` | state -> PENDING_APPROVAL; records `maker_id` = token user; 422 if note empty |
| `/cases/{id}/approve` | checker | `{"reviewed":true,"comment":null}` | `reviewed` must be true (422). SoD, limit, dual-auth (>=250k: -> AWAITING_SECOND_APPROVAL, second approver must differ). Final approval: ASSISTED/LIVE -> DISPATCHED via outbound port; SHADOW -> SHADOW_RECORDED (nothing sent) |
| `/cases/{id}/return` | checker | `{"reason_code":"...","comment":"..."}` both required | -> RETURNED_FOR_REWORK |
| `/cases/{id}/reject` | checker | `{"reason_code","comment"}` required | -> REJECTED |
| `/cases/{id}/request-information` | maker | `{"to":"Nordhavn Components A/S","method":"Email","message":"...","draft":false,"reply_due":null,"escalate_at":null}` | `draft:true` saves draft only. Sending sets waiting state, default reply due +2h, escalate +2h15m |
| `/cases/{id}/reassess` | maker | `{"note":null}` | re-runs evidence sufficiency on stored evidence (and any received reply); variant may change |
| `/cases/{id}/escalate` | maker/supervisor | `{"to":"SENIOR_ANALYST|SUPERVISOR|APPROVER","reason":"..."}` | -> ESCALATED where lifecycle allows, else records escalation flag |
| `/cases/{id}/start-verification` | maker | `{"note":null}` | opens verification (INVESTIGATING) with audit |
| `/cases/{id}/check-status` | maker/supervisor | `{}` | SIMULATED bank status check; never resends; returns `{"result":"STILL_UNKNOWN|ACCEPTED|NOT_SENT|...","checked_at":..}` |
| `/cases/{id}/request-bank-status` | maker/supervisor | `{"note":null}` | simulated request to bank operations; creates notification |
| `/cases/{id}/compliance/decision` | compliance | `{"decision":"release|confirm_block|escalate","reason_code":"...","comment":"..."}` | confirm_block requires a second reviewer (different compliance/risk user): first call -> `second_review.state="pending"`, 2nd by another user finalises (REJECTED); same user twice -> `SOD_VIOLATION` |
| `/cases/{id}/ping` | maker/supervisor | `{"note":null}` | expedite ping; target role: APPROVED->settlement ops, >=250k RISK_APPROVER, COMPLIANCE->COMPLIANCE_APPROVER, else OPERATIONS_APPROVER; stores `expedite_ping`, creates notification |
| `/cases/{id}/disambiguate` | maker | `{"candidate_id":"H2","rationale":"required"}` | audit `HYPOTHESIS_DISAMBIGUATION` |
| `/cases/{id}/assign` | see 4 | | |
Notifications: `GET /api/v2/notifications` -> `{"unread":2,"items":[{"id":"N-1","at":..,"kind":"PING|RETURNED|ASSIGNED|MODE_CHANGE|STATUS","case_id":"..","title":"..","text":"..","read":false}]}`; `POST /api/v2/notifications/{id}/read`.

## 7. Batch approval (STP)
`GET /api/v2/stp/review` (approver)
```json
{"policy":{"rule_id":"MR-01","text":"Micro-repair MR-01 · under 25,000 · validated · evidence complete","limit":{"amount":25000,"currency":"mixed"}},
 "eligible":[{"case_id":"PEX-STP-0103","exception":{"code":"DQ-06","label":"Missing purpose code"},"amount":{...},"rail":{...},
   "change":{"field":"purpose_code","original":"","proposed":"SUPP","highlight":null,"source":"Client standing instruction"},
   "chips":[{"label":"Validated","tone":"success"},{"label":"Evidence complete","tone":"success"},{"label":"No open hold","tone":"success"},{"label":"Within limit","tone":"success"}]}],
 "totals":{"selected":12,"eligible":12,"total_value":[{"currency":"GBP","amount":..}],"total_value_label":"136,620.00 (mixed currencies)","largest":{"case_id":"...","amount":{...}}},
 "not_eligible":{"total":3,"groups":[{"reason":"Evidence conflict","code":"EVIDENCE_CONFLICT","count":1,"cases":[{"case_id":"...","detail":"..."}]}]},
 "footnote":"Handoff requests will be sent to the bank payment system. Execution is confirmed by the bank."}
```
`POST /api/v2/stp/approve {"case_ids":[...]}` -> `{"requested":12,"handed_to_bank":12,"skipped":[{"case_id","reason"}],"mode":"ASSISTED","message":"12 handoff requests sent (simulated). Awaiting bank confirmation."}`; SHADOW mode: records only, `handed_to_bank:0,"recorded":12`.

## 8. Batches
`GET /api/v2/batches?page&page_size` -> `{"items":[{"batch_id","filename","status","status_label":"Partially processed|Processed|Processing|Failed","received_at","source":"Bank adapter|Upload|Synthetic","records":50,"accepted":41,"duplicate":4,"rejected":3,"needs_review":2}]}`.
`GET /api/v2/batches/{id}?tab=all|accepted|duplicate|rejected|needs_review&page&page_size`:
```json
{"batch_id":"...","filename":"exceptions_2026-10-16_0900.json","status":"COMPLETED","status_label":"Partially processed","received_at":"ISO","source":"Bank adapter","records":50,
 "stages":[{"key":"received","label":"Received","at":"ISO","state":"done"},{"key":"schema","label":"Schema checked"},{"key":"duplicates","label":"Duplicates checked"},{"key":"cases","label":"Cases created"},{"key":"archived","label":"Archived"}],
 "counts":{"received":50,"accepted":41,"duplicate":4,"rejected":3,"needs_review":2},
 "reconciliation":{"balanced":true,"text":"50 received = 41 accepted + 4 duplicate + 3 rejected + 2 needs review. Nothing lost."},
 "tab":"all","tab_counts":{"all":50,"accepted":41,"duplicate":4,"rejected":3,"needs_review":2},"page":1,"page_size":25,"total":50,
 "items":[{"record":17,"source_reference":"BNK-884102","case_id":null,"outcome":"rejected|accepted|duplicate|needs_review","outcome_label":"Rejected","detail":"Missing required field: creditor account","action":{"type":"download|view_case|review","label":"Download"}}],
 "outputs":{"bank_handoff_requests":{"sent":0,"text":"0 sent · cases not yet approved"},"archive":{"archived":true,"checksum":"sha256:...","verified":true,"at":"ISO"}},
 "actions":{"download_rejected":"/api/v2/batches/{id}/rejected?format=jsonl","reprocess":{"enabled":false,"reason":"Upload corrected records first","endpoint":"/api/v2/batches/{id}/reprocess"}}}
```
`GET /api/v2/batches/{id}/records/{record}` -> `{"record":17,"outcome","detail","errors":[...],"raw":{...},"case_id"}`. `GET /api/v2/batches/{id}/rejected?format=jsonl|csv|json` (download). `POST /api/v2/batches/{id}/reprocess` multipart `file` (corrected records) -> `{"batch_id":"<new>","parent_batch_id":"...","status":"QUEUED"}`. `POST /api/v2/batches/upload` multipart `file` -> `{"batch_id","status":"QUEUED"}` (wraps `/api/batch/upload`). Old `/api/batch/*` unchanged.
**Needs review** = record passes schema, is not an identical `exception_id`/`UETR`, but matches an existing case on payment reference + amount + creditor (or payment ref + amount + currency). It is processed into a case flagged `possible_duplicate_of`; outcome `needs_review`, detail "Possible duplicate · not identical (matches PEX-DUP-0051)".

## 9. Audit (roles SUPERVISOR, AUDIT_RISK, ADMIN, COMPLIANCE read)
`GET /api/v2/audit/events?date_from=&date_to=&event_type=&actor=&role=&exception_type=&rail=&q=&case_id=&page&page_size` ->
`{"total":..,"items":[{"id":"EV-1234","time":"ISO","case_id":"PEX-INV-0001","event":"Approved for bank handoff","event_type":"APPROVAL","actor":"Daniel Osei","actor_id":"APR-3191","role":"Operations Approver","outcome":"Approved|Submitted|Blocked|Held|Passed|Unknown","detail":"..."}],"facets":{"event_types":[],"roles":[],"actors":[]},"integrity":{"chain_valid":true,"events":..}}`.
`GET /api/v2/audit/events/{id}` -> `{"id","event","case_id","actor":{"user_id","name","role"},"time","before":"VALIDATED","after":"APPROVED","evidence_reviewed":5,"policy_version":"Micro-repair policy v3.2","sod":{"result":"Passed","text":"..."},"reason":"...","integrity":{"sealed":true,"verified":true,"hash":"abcd…","prev_hash":"…"},"tags":[...]}`.
`GET /api/v2/audit/export?format=csv&<same filters>` (CSV download). `GET /api/v2/audit/cases/{id}/report?format=json|csv`. `GET /api/v2/audit/control-reports` -> `[{"id":"SOD","name":"Separation of duties","passed":..,"failed":..,"period":"today"}]`; `GET /api/v2/audit/cases?q=&page=` for "Case reports" tab: `[{"case_id","exception","amount","status","events":5,"last_event":"ISO"}]`.

## 10. Admin (ADMIN only; GET also readable by SUPERVISOR for integrations)
`GET /api/v2/admin/integrations`:
```json
{"simulated":true,"banner":"All integrations are simulated in this build. No real bank system is contacted.",
 "tiles":{"connected":6,"healthy":5,"degraded":1,"live_writeback_enabled":{"count":1,"of":6}},
 "items":[{"id":"payment_engine","name":"Payment engine","purpose":"Exception events and status","type":"Payment engine","direction":"Read and handoff","mode":"ASSISTED","health":"healthy|degraded","health_note":null,"last_event":"ISO","queue":0,"simulated":true,"pending_mode_change":null,"action":{"label":"View","kind":"view|issue"}}],
 "modes":[{"mode":"SHADOW","text":"Read only. Nothing is sent."},{"mode":"ASSISTED","text":"A named human approves every handoff."},{"mode":"LIVE","text":"Approved policy may hand off. The bank still executes."}],
 "never_executes":"PeX never executes payments. The bank executes and confirms.",
 "handoffs_24h":{"sent":14,"acknowledged":12,"awaiting":2,"source":"computed from real handoffs"}}
```
`GET /api/v2/admin/handoffs?hours=24` -> list. `POST /api/v2/admin/mode-change-request {"integration_id","to_mode","reason"}` -> `{"id":"MC-1","state":"PENDING_SECOND_ADMIN","requested_by":..}`; `GET /api/v2/admin/mode-change-requests`; `POST /api/v2/admin/mode-change-request/{id}/approve` (must be a DIFFERENT admin else `SECOND_ADMIN_REQUIRED`) -> applied; `.../reject`.
`GET /api/v2/admin/roles` -> `{"roles":[{"role":"OPERATOR","label":"Maker","permissions":[..],"approval_limit":0,"users":[{"user_id","name"}]}],"authority_matrix":[{"role","limit","can":[..]}]}`.
`GET /api/v2/admin/policies` -> `{"thresholds":[{"key":"stp_limit","label":"STP / micro-repair limit","value":10000,"currency":"USD","editable":false}, {"key":"dual_auth_threshold","value":250000},{"key":"micro_repair_rule","value":"MR-01 ..."}],"rules":[existing /api/rules shape]}`. Existing `/api/rules/*` remains.
`GET /api/v2/admin/exception-types` -> `{"total":41,"items":[{"code":"DQ-01","label":"Invalid IBAN","domain":"DATA_QUALITY","queue":"Repair","stp_permissible":true,"stp_note":null,"open_cases":3}]}`.

## 11. Seed (demo)
`scripts/seed_ui_v2_demo.py` (also auto when DB is empty and `PEX_DEMO=true`, `PEX_SEED_V2=true`). Named cases PEX-INV-0001, PEX-BEN-0012, PEX-CON-0031, PEX-TMO-0044, PEX-SAN-0102, PEX-RET-0035, PEX-NAM-0027, PEX-REC-0079, PEX-DUP-0051, PEX-CUS-0067, PEX-SET-0039, PEX-STP-0101..0112 + 3 ineligible examples. Cutoffs are relative to seed time.

## Change log
* v1.0 – initial contract.
* v1.1 – as built (backend delivery):
  * Auth: `Authorization: Bearer <token from POST /api/auth/login>`; roles incl. SUPERVISOR and AUDIT_RISK (read only: every write returns 403 `FORBIDDEN`).
  * List endpoints return `items` (worklist, audit events, batch records, integrations). `GET /home` returns `role_view` (MAKER, SUPERVISOR, APPROVER, COMPLIANCE, AUDIT, ADMIN).
  * Worklist tabs: ready, returned, waiting, pending, done. Compliance cases are served by `GET /compliance/queue`, not a tab. `assignee` accepts a user id, `me`, `queue` or `none`.
  * APPROVAL variant is also returned to the maker viewer (read-only, with the SoD banner). `reassess` accepts `provided`.
  * `POST /stp/approve` returns `{batch_id, requested, handed_to_bank, recorded, skipped:[{case_id, reason}], mode, message}`. In SHADOW mode cases are recorded and nothing is sent. `GET /stp/review?case_ids=a,b` narrows the selection. The batch screen limit is `PEX_BATCH_APPROVAL_MAX` (default 25,000, payment currency, no FX); autonomous STP stays at `STP_MAX_AMOUNT`.
  * Error codes seen: AUTH_REQUIRED, FORBIDDEN, SOD_VIOLATION, LIMIT_EXCEEDED, INVALID_STATE, VALIDATION (422, with `field`), NOT_FOUND. `SECOND_REVIEWER_REQUIRED` is reserved and not emitted (compliance second review is a state, not an error).
  * Extra endpoints: `GET /audit/cases`, `GET /audit/control-reports`, `GET /admin/handoffs`, `GET /admin/mode-change-requests`, `POST /admin/mode-change-request/{id}/reject`, `GET /worklist/{case_id}/preview`, `GET /cases/{id}/evidence/{ev}`, `POST /batches/upload`, `GET /me` (permissions, nav).
  * Batches: outcomes accepted, duplicate, rejected, needs_review (non-identical record matching reference + amount + currency + creditor). Rejected download formats: jsonl (re-uploadable originals), json, csv. Reprocess creates an `RPR-` child batch linked by `parent_batch_id`.
  * Mode change: requester cannot approve; a different ADMIN must. Approving a `payment_engine` change sets the running operation mode.
  * Dual authorisation at >= 250,000 needs two different approvers, each within limit (above 250,000 only Risk/Admin personas qualify).
* v1.2 - integration pass (no endpoint shape changes):
  * Seed: baseline (82) cases get their SLA/cutoff re-spread to 3-9 h ahead of seed time so the demo clock looks live (previously already passed). Re-seed shortly before a demo: cutoffs are relative to seed time.
  * PEX-CON-0031 now has three sources (instruction and directory agree on DE89 3704 0044 0532 0130 00; invoice INV-4410 differs: DE02 1203 0000 0000 2020 51, both valid mod-97) with the three "why STP is blocked" reasons from the design.
  * Frontend nav now mirrors `GET /v2/me` nav per role; case links are readable by every role; a COMPLIANCE_HOLD case opened by a role without Compliance access stays on the case page (banner + disabled repair actions).
  * Example IBANs in sections 5 are illustrative; seeded values are real mod-97 values (e.g. PEX-INV-0001: GB29 NWBK 6016 1331 9268 91 fails, ...19 passes), `highlight` indexes refer to the grouped string.
