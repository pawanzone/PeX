# Personal data protection in PeX v2

**Rule:** names, IBANs and account numbers are tokenised (TOK-PARTY-..., TOK-IBAN-..., TOK-ACC-...) in everything the v2 API returns. Real values show only to a person who asks to reveal them, with a reason, for 10 minutes. Every reveal is audited.

## Where it sits in the 8-step workflow
1. Receive and validate. 2. **Tokenize personal data.** 3-5. Work on tokens. 6. Maker and approver; **Reveal** available here. 7. Hand to bank: the only place real values go back out (to the bank). 8. Bank outcome and audit (reveals are in the audit trail).
Diagram: `docs/pex_8_step_workflow.png`.

## What is built
- `backend/app/services/v2/pii.py`: builds the per-case list of real values and replaces them with vault tokens in every JSON answer under `/api/v2` (case page, worklists, approvals, audit events). Fails closed.
- `POST /api/v2/cases/{id}/pii/reveal` (reason of at least 10 characters) and `/pii/hide`. Permission `pii.reveal`: Maker, Supervisor, Operations Approver, Compliance Officer, Risk Approver, Audit and Risk. **Administrator cannot reveal.**
- A reveal belongs to one person and one case, expires after 10 minutes, and writes `PII_REVEALED` / `PII_HIDDEN` audit events.
- While masked, character-position highlights on IBAN changes are withheld (positions would not line up with a token).
- Case page shows a protection bar with "Reveal real values" and "Hide now".
- Switch off with `PEX_PII_MASKING=false` (demo/debug only).

## Not built yet (be clear about this)
- The vault is in-memory and the real values are still held in the case record in the same database. Production needs a separate encrypted vault service, key management and per-field encryption.
- Audit export (CSV) and free text typed by users outside the case's known values are not scrubbed.
- Real values are not yet fetched from the vault at hand-off; the simulated bank gate uses the case record.
- Deterministic checks (IBAN checksum) read real values inside the process; the boundary is logical, not physical.
