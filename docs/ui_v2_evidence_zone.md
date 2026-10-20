# Evidence zone: where real personal data is handled

Rule: real values exist only inside the zone. Everything that leaves it (screens, audit rows, notifications, the AI input, the confidence engine) holds tokens and derived facts.

## How a value travels (steps 1 to 4 of the 8-step workflow)
1. **Receive and validate.** The bank event arrives as JSON. Raw values go straight to step 2.
2. **Tokenize.** Names, IBANs and accounts become `TOK-<TYPE>-<12 hex>` tokens from a keyed vault (HMAC, `PEX_TOKEN_KEY`). The same value always gets the same token, so "three earlier payments to this beneficiary" still works.
3. **Classify and plan evidence.** Works on tokens, codes and bands.
4. **Gather evidence.** Each source is a connector with one interface. The connector answers with real values inside the zone. The zone runs the checks (mod-97, name similarity, exact match, history count) and returns tokens plus facts, for example `similarity 0.65`, `agrees with instruction: false`.

Real values leave the zone only (a) to a person with an audited reveal, (b) to the bank at hand-off, (c) in approved external look-ups.

## Data classes
| Class | Covers | Who can reveal |
|---|---|---|
| C1 | names, addresses, IBAN/account, private IDs, tax IDs, phone, email, KYC documents | Operator, Supervisor, Ops/Risk/Compliance approvers, Audit and Risk (reason, logged). Never Admin |
| C2 | remittance text, instructions, notes, invoices, emails | same as C1 |
| C3 | sanctions and screening hits, suspicious-activity indicators | Compliance only |
| C4 | UETR, end-to-end id, case id | shown as is on screens; tokenised for the AI |
| C5 | BIC, currency, dates, status and reason codes | not personal data |

The exact amount stays in the zone. The AI receives a band (for example `1k to 10k GBP`).

## Connectors
`simulated` is the default: ISO 20022-shaped answers, including conflicts. Set `PEX_CONNECTOR_MODES="CUSTM=real,COPVOP=real"` and register an adapter with `zone.register_real(key, factory)` once a bank takes part. A connector set to real with no adapter fails closed; nothing falls back silently.

## What is enforced where
- Stored evidence, conflicts and needed-information blocks are sealed when saved (`zone.seal_ext`).
- Every audit row is sealed at the single write point (`repository.log_audit_event`). Notifications are sealed when created.
- API answers are tokenised on the way out; a reveal puts back only the classes the role may see, and only when every case in the answer is revealed.
- `GET /api/v2/cases/{id}/ai-view` shows exactly what a model receives. It stays tokenised during a reveal. `zone.llm_input()` runs a guard that fails closed if a real value is present.

## Not done yet
- The case record and the proposed repair keep real values because the bank hand-off needs them. They are protected at the API, not encrypted at rest.
- The vault is a table in the same database. A separate vault service with its own key custody is the production step.
- Attached documents (PDF, e-mail files) are not parsed; only text fields are sealed.
- Audit rows written before this change are not rewritten, so an existing database still holds some real values in old rows. A fresh seed has none. The CSV export reads the stored rows.
- The simulated connectors cover directory, VoP, history, invoice and screening. Other systems in the evidence matrix are not simulated yet.
