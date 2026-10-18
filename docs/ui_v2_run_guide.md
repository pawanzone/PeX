# UI v2: run guide (Windows, PowerShell)

Everything here is the demo build: bank communication is SIMULATED, data is synthetic, personas replace real sign-in.

## 1. One-time setup
```powershell
cd C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\demo_build
git checkout ui/v2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd frontend
npm ci
cd ..
```
(If `pip` prints a `.deleteme` warning, ignore it as long as the install finishes; always call `python -m ...`.)

## 2. Start the backend (terminal 1)
Use a NEW database file so the demo data is seeded automatically (the old `pex_demo_run.db` is not touched):
```powershell
cd C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\demo_build\backend
..\.venv\Scripts\Activate.ps1
$env:DATABASE_URL="sqlite:///pex_v2_demo.db"
$env:PEX_DEMO="true"
$env:PEX_OPERATION_MODE="ASSISTED"
$env:PEX_BANK_CALLBACK_SECRET="demo-secret"
$env:JWT_SECRET="demo-jwt-secret"
$env:SIM_BANK_ACK_SECONDS="6"
python -m uvicorn app.main:app --port 8000
```
Check: http://127.0.0.1:8000/api/system/info shows JSON with mode ASSISTED and bank SIMULATED.

**Reset or refresh the demo data** (do this shortly before you demo, because cutoffs are relative to seed time):
stop the backend, delete `backend\pex_v2_demo.db*`, start again. Or, without deleting: `python ..\scripts\seed_ui_v2_demo.py --force` with the same environment variables set.

## 3. Start the frontend (terminal 2)
```powershell
cd C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\demo_build\frontend
npm run dev
```
Open http://localhost:5173 (it proxies `/api` to 127.0.0.1:8000). The first screen is the maker home as Priya Nair. Switch persona from the menu top right.

## 4. Personas
| Name | Role | Use for |
|---|---|---|
| Priya Nair | Maker (Operator) | 01, 03, 04-07, 12, batches |
| Marcus Lee, Sofia Rossi, Chen Wei | Analysts | team workload on the supervisor home |
| Elena Marsh | Supervisor | 02, assign/reassign, audit view |
| Mei Tan | Operations Approver (limit 250,000) | 08, 09 |
| Daniel Osei | Operations Approver (older persona) | same as Mei |
| Kenji Watanabe | Risk approver, tier 2 | PEX-RET-0035 (1.79M), second reviewer on compliance |
| Amara Okafor | Compliance Officer | 10 |
| Rhea Kapoor | Audit and Risk, read only | 13 (every write returns "read-only role") |
| Tomas Berg, Alex Whitfield | Administrators | 14 (two admins needed to change a mode) |

## 5. Suggested walk-through (about 20 minutes)
1. **Priya, Home (01):** act-now list, tiles, cutoff bands. Click a tile.
2. **Worklist (03):** tabs, filters, save a view, click a row for the preview.
3. **Cases (04-07):** `#/worklist/case/PEX-INV-0002` (submit needs a handover note), `PEX-BEN-0012` (request information, reassess), `PEX-CON-0031` (three sources, "Why STP is blocked", start verification), `PEX-TMO-0044` (Check status: first still unknown, second accepted; "Do not resend" blocked).
4. **Priya submits PEX-INV-0002** (note required) -> switch to **Mei Tan**, Approvals (08): tick "I reviewed", Approve. Case shows "Handed to bank, waiting for confirmation"; after about 6 seconds and a refresh it shows "Executed by bank" (journey 12 B then C). Priya cannot approve her own case (separation of duties).
5. **Mei, Approvals > Review low-risk batch (09):** 12 eligible micro-repairs (mixed currencies) and 3 not eligible with reasons (conflict, compliance hold, validation failed). Approve selected.
6. **Amara Okafor, Compliance (10):** open PEX-SAN-0102. No repair actions exist. Release hold, Confirm match (needs a second reviewer: Kenji Watanabe), Escalate.
7. **Rhea Kapoor, Audit (13):** filter, open an event (hash sealed and verified), export CSV.
8. **Tomas Berg, Admin > Integrations (14):** six simulated systems; request a mode change, then sign in as Alex Whitfield and approve it (the requester cannot).

## 6. Manual test: batch JSON input
1. Generate a test file (backend venv active, from the repo root):
   ```powershell
   cd C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\demo_build
   python scripts\make_ui_test_batch.py --out ui_test_batch.jsonl
   ```
   It is the generated demo format (same as `gen_synthetic_batch.py`): 44 valid records, 1 possible duplicate, 2 unknown exception type, 2 exact duplicates. You can re-run it for a new file; ids change each run.
2. As Priya: **Batches > Upload batch file** and choose `ui_test_batch.jsonl`. (Also accepted: `.json`, `.jsonl`, `.ndjson`, `.gz`. "Generate demo batch" on the same page creates synthetic data without a file.)
3. The batch appears as processing, then completes. Open it (11). Expected on a fresh database: **49 received = about 43-44 accepted + 2 duplicate + 2 rejected + 1-2 needs review**, with the reconciliation banner "Nothing lost" (the exact accepted/needs-review split varies by a record or two). Stages show Received, Schema checked, Duplicates checked, Cases created, Archived.
4. Tabs: Accepted (case ids link to the case page), Duplicate ("matches PEX-..."), Rejected ("Unknown exception type: ZZ-99"), Needs review ("Possible duplicate, not identical").
5. **Download rejected records**, open the file, change `"profile_id":"ZZ-99"` to `"DQ-01"`, save, then **Reprocess corrected records** and pick it. A child batch `RPR-...` is created (shown in the batch list) and its 2 records become cases.
6. Open Worklist: the new cases are there with variants derived from their evidence. Bank handoff requests in Outputs stay at 0 until someone approves a case.
7. Backend log may print `FolderInputAdapter ingestion note: 'str' object has no attribute 'model_dump'`: known, harmless to the result, to be fixed.

## 7. If something does not load
- Page blank or "could not load": open http://127.0.0.1:8000/api/system/info. If that fails the backend is not running or died (read terminal 1). If it works, hard-refresh the page.
- The Vite proxy points at `127.0.0.1:8000` on purpose (Node resolves `localhost` to IPv6 on your machine).
- Slow first load: note the Network tab timings (which request is slow) and send them.
- Sign-in problems after a server restart: pick a persona again from the top-right menu.

## 8. What is real and what is simulated
Real: the case lifecycle and state machine, maker-checker and separation of duties, approval limits and dual authorisation, hash-chained audit, evidence rules, batch pipeline, idempotency. Simulated: the bank payment engine and its acknowledgement (only a signed inbound bank signal can make a case "Executed"), sanctions screening, directories, core ledger, notifications delivery, all customer contact. PeX never executes or settles a payment itself.
