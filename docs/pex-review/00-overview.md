# 00-overview.md — Repository and Runtime Map

**Document Status:** COMPLETE / EVIDENCE-AUDITED  
**Auditor Mode:** Objective External Review  
**Target Codebase:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Date of Audit:** October 2026  

---

## 1. Repository Structure (Top Two Levels)

The PeX platform repository is structured across backend, frontend, test suites, synthetic data stores, and documentation fixtures:

| Directory Path | Level | Purpose / Contents |
| :--- | :--- | :--- |
| `backend/` | Level 1 | Python backend application root. |
| `backend/app/` | Level 2 | Core FastAPI application: schemas, services, API endpoints, database models, ports, and reference adapters. |
| `backend/tests/` | Level 2 | Backend-specific unit tests (`test_api.py`, `test_models.py`, `test_services.py`). |
| `frontend/` | Level 1 | Single-page cockpit frontend application. |
| `frontend/src/` | Level 2 | React/TypeScript components, views (Cockpit, Worklist, Approvals Desk, Investigations Hub, Audit Ledger), and styling. |
| `frontend/dist/` | Level 2 | Static bundled production build files (`index.html`, `assets/`). |
| `frontend/public/` | Level 2 | Public static assets and icons. |
| `tests/` | Level 1 | Comprehensive functional, contract, and adversarial test suites. |
| `tests/contracts/` | Level 2 | 39 Wave 0A/0B architectural contract and interface compliance tests. |
| `tests/wave0b/` | Level 2 | 33 Wave 0B foundational tests (idempotency, port isolation, canonicalization). |
| `tests/wave1/` | Level 2 | 135 Wave 1 profile tests covering Data Quality (DQ-01 to DQ-09) and initial processing. |
| `tests/wave2/` | Level 2 | 96 Wave 2 profile tests covering Processing (PR-01 to PR-09) and Settlement (ST-01 to ST-07). |
| `tests/wave3/` | Level 2 | 86 Wave 3 profile tests covering Treasury (TR-01 to TR-08) and Compliance (CO-01 to CO-08). |
| `tests/wave4/` | Level 2 | 62 Wave 4 adversarial red-team tests (adversarial injection, RBAC bypass, SOD tamper). |
| `e2e_fixtures/` | Level 1 | End-to-end batch file drops, schema fixtures, and runner outputs. |
| `e2e_fixtures/input/` | Level 2 | Monitored drop directory for inbound JSON/CSV exception batches (e.g. `BATCH-MIXED-001.json`). |
| `e2e_fixtures/output/` | Level 2 | Output directory where processed case records and reconciliation receipts are written. |
| `e2e_fixtures/archive/` | Level 2 | Processed input archive directory where ingested batch files are moved. |
| `synthetic_data/` | Level 1 | Pre-generated synthetic banking exception datasets. |
| `synthetic_data/PeX_POC_Synthetic_Data_v0.1/` | Level 2 | Seed JSON data files for payments, counterparties, accounts, and historical exceptions. |
| `docs/` | Level 1 | Repository documentation, specifications, and architecture reviews. |
| `docs/cxo_pages/` | Level 2 | HTML executive briefing visualizer pages. |
| `docs/pex-review/` | Level 2 | Formal independent architecture and product review documentation (this audit). |
| `scripts/` | Level 1 | Automation scripts for database initialization, synthetic generation, and batch runs. |
| `tools/` | Level 1 | Diagnostics, test harness generators, and legacy scaffolding utilities. |
| `validation_audit/` | Level 1 | Five-stream forensic validation audit reports generated during architectural verification. |
| `assets/` | Level 1 | Static graphic assets, branding, and iconography. |
| `.agents/` | Level 1 | Agent skill definitions (`.agents/skills/`). |
| `.venv/` | Level 1 | Local Python 3.11 virtual environment. |

---

## 2. Languages, Frameworks, Major Libraries & Versions

The runtime stack was inspected directly via `requirements.txt`, `frontend/package.json`, and running processes:

### Backend Stack
- **Python**: `3.11.0` (Active virtual environment at `.\.venv\Scripts\python.exe`)
- **Web Framework**: FastAPI `0.141.1` (Configured in `backend/app/main.py`)
- **ASGI Server**: Uvicorn `0.52.4` (Standard loop running on port `8000`)
- **Data Validation & Typing**: Pydantic `2.13.4`, Pydantic-Core `2.16.0` (Strict schema validation across `backend/app/schemas/`)
- **Database ORM**: SQLAlchemy `2.0.54` (Declarative models in `backend/app/db/models.py`)
- **HTTP Client**: HTTPX `0.27.0` (Async testing and HTTP client calls)
- **Testing**: Pytest `9.1.1` (Running against root `pytest.ini`)
- **Office / Document Exporters**: `python-docx 1.1.0`, `python-pptx 1.0.0`, `xlsxwriter 3.2.0`, `pillow 10.0.0`

### Frontend Stack
- **JavaScript Engine / Bundler**: Node.js runtime, Vite `5.1.6` (Configured in `frontend/vite.config.ts`)
- **UI Framework**: React `18.2.0`, React-DOM `18.2.0`
- **Language**: TypeScript `5.2.2` (Strict mode in `frontend/tsconfig.json`)
- **Styling**: TailwindCSS `3.4.1`, PostCSS `8.4.35`, Autoprefixer `10.4.18`
- **Iconography**: Lucide-React `0.344.0`

---

## 3. How to Build, Run, Seed and Test

### A. Environment Setup & Dependency Installation
```powershell
# 1. Virtual Environment Setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Frontend Dependencies & Build
cd frontend
npm install
npm run build
cd ..
```

### B. Database Initialization & Seeding
```powershell
# Set Python path to backend
$env:PYTHONPATH="backend"
$env:DATABASE_URL="sqlite:///./pex_enterprise.db"

# Seed baseline database (creates tables, seeds 88 cases, rules, and demo accounts)
.\.venv\Scripts\python.exe scripts/init_db.py
```
*Actual Command Result:* Successfully initialized SQLite tables in `pex_enterprise.db` (5 tables: `cases`, `approval_records`, `governed_actions`, `delivery_receipts`, `audit_events`).

### C. Launching the Platform
```powershell
# Start FastAPI backend with integrated static frontend and file watcher
$env:PYTHONPATH="backend"
$env:DATABASE_URL="sqlite:///./pex_demo.db"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
*Actual Command Result:* Running as background task. Listens on `http://127.0.0.1:8000`. Serving API routes on `/api/*` and bundled React UI at root `/`.

### D. Inbound Batch File Ingestion (Drop-Folder Workflow)
```powershell
# Drop an inbound exception batch into the monitored input folder
Copy-Item "e2e_fixtures/fixtures_staging/BATCH-MIXED-001.json" -Destination "e2e_fixtures/input/BATCH-MIXED-001.json"
```
*Actual Execution Result:* `backend/app/services/file_watcher.py` detects file arrival, canonicalizes each item, executes 8 validation predicates via `e2e_runner.py`, moves file to `e2e_fixtures/archive/`, and writes individual outputs plus `BATCH-MIXED-001.reconciliation.json` into `e2e_fixtures/output/`.

### E. Test Execution & Verified Test Run
```powershell
# Run full regression test suite
.\.venv\Scripts\pytest.exe -q
```
*Actual Execution Result (Timestamped 2026-10-16):*
- **Total Tests Collected**: **909 tests**
- **Passed**: **760 passed**
- **Failed**: **149 failed** (See breakdown in Section 6 below)
- **Duration**: 379.91s (6 minutes 19 seconds)

---

## 4. Services, Processes, Ports, Datastores & External Integrations

### Active Processes & Ports
- **Single Process**: Uvicorn daemon running Python 3.11 (`python.exe -m uvicorn app.main:app`).
- **Active Listening Port**: TCP `127.0.0.1:8000` (FastAPI backend + static React frontend).
- **Queues / Brokers (Active)**: **NONE**. No external RabbitMQ, Apache Kafka, IBM MQ, or AWS SQS broker is connected or running. Queueing is simulated via in-memory and SQLite query filters on the `assigned_queue` column.
- **External Calls**: **ZERO active network calls**. All outbound integrations (SWIFT network, Fedwire FAIM, OFAC watchlist API, Core Banking DDA, Confirmation of Payee) are routed through in-memory reference adapters or query static local JSON files (`backend/app/data/icd_staging_store.json`).

### Datastores
- **Active Primary Datastore**: Local SQLite file (`pex_demo.db` during demo/dev; `pex_enterprise.db` baseline).
- **Relational Schema**: 5 relational tables defined in `backend/app/db/models.py`:
  1. `cases` (Primary key `case_id`, stores JSON blobs for `raw_payload`, `canonical_payment`, `exception_details`, `recommendation_payload`)
  2. `approval_records` (Stores human approvals, role, comments, timestamp)
  3. `governed_actions` (Stores dispatch actions, status, payload)
  4. `delivery_receipts` (Stores simulated network delivery ACK/NAK)
  5. `audit_events` (Stores append-only event log with SHA-256 chain hash)
- **In-Memory Volatile Stores**:
  - `backend/app/services/data_loader.py` (`DataRepository` singleton storing cases, recommendations, audit logs in Python dictionaries).
  - `backend/app/core/tokenization.py` (`TokenVault` singleton storing `_raw_to_token` and `_token_to_raw` dictionaries).

---

## 5. Environment Variables & Feature Flags

Configured in `backend/app/config.py` (lines 13-43):

| Variable Name | Default Value | Description / Behavioral Impact | Real vs Mock Impact |
| :--- | :--- | :--- | :--- |
| `PEX_MODEL_GATEWAY_MODE` | `"mock"` | Options: `"mock"`, `"gemini"`, `"openai"`. Intended to switch AI reasoning backend. | **MOCKED**: `model_gateway.py` does not implement live Gemini or OpenAI network calls; it returns canned mock payloads regardless of mode. |
| `GEMINI_API_KEY` | `""` | API key for Google Gemini LLM. | **UNUSED** in code today. |
| `OPENAI_API_KEY` | `""` | API key for OpenAI GPT models. | **UNUSED** in code today. |
| `DATABASE_URL` | `"sqlite:///./pex_enterprise.db"` | SQLAlchemy connection string. | Switches between SQLite files or PostgreSQL. |
| `DUAL_AUTH_THRESHOLD` | `250000.0` | Monetary threshold in USD equivalent requiring Checker approval. | **IMPLEMENTED**: Enforced in `approval_engine.py` and `security.py`. |
| `JWT_SECRET` | `"pex-enterprise-secret-key-2026-sha256"` | HMAC-SHA256 signing secret for session tokens. | **IMPLEMENTED**: Enforced in `backend/app/core/security.py`. |
| `PEX_WATCHER_ENABLED` | `"true"` | Enables/disables inbound background folder watcher thread. | **IMPLEMENTED**: Checked at startup in `backend/app/main.py`. |
| `PEX_WATCHER_POLL_INTERVAL` | `"1.0"` | Polling frequency in seconds for folder watcher. | **IMPLEMENTED**: Regulates `file_watcher.py` loop. |
| `PEX_WATCHER_AUTO_ARCHIVE` | `"true"` | Moves processed input batches from `input/` to `archive/`. | **IMPLEMENTED**: Handled in `file_watcher.py`. |
| `PEX_INPUT_WATCH_DIR` | `e2e_fixtures/input` | Input drop folder path. | **IMPLEMENTED**: Monitored by `file_watcher.py`. |
| `PEX_OUTPUT_WATCH_DIR` | `e2e_fixtures/output` | Output drop folder path. | **IMPLEMENTED**: Target for reconciliation JSON. |
| `PEX_ARCHIVE_WATCH_DIR` | `e2e_fixtures/archive`| Archive folder path. | **IMPLEMENTED**: Target for processed input JSON. |

---

## 6. Test Inventory & Fresh Run Results

Fresh test run executed via `.\.venv\Scripts\pytest.exe -q` on 2026-10-16:
- **Total Test Files**: 32 test modules across `tests/` and `backend/tests/`.
- **Total Tests Collected**: 909 tests.
- **Pass Count**: 760 passed (83.6%).
- **Fail Count**: 149 failed (16.4%).

### Breakdown by Test Area:
1. `tests/contracts/` (**39 tests / 39 passed - 100%**):
   - Validates port-adapter interfaces, Wave 0A/0B contract schemas, Pydantic type consistency.
2. `tests/wave0b/` (**33 tests / 33 passed - 100%**):
   - Validates idempotent ingestion locks, canonicalization models, and deterministic MOD-97 logic.
3. `tests/wave1/` (**135 tests / 134 passed, 1 failed**):
   - Validates Data Quality (DQ-01 to DQ-09) and initial profile processing.
   - Failure: Scenario 27 CO-07 assertion failure on simulated compliance clearance.
4. `tests/wave2/` (**96 tests / 90 passed, 6 failed**):
   - Validates Processing (PR-01 to PR-09) and Settlement (ST-01 to ST-07).
   - Failures: PR-06 (message format corruption), ST-02 (beneficiary account frozen), ST-03 (liquidity break).
5. `tests/wave3/` (**86 tests / 77 passed, 9 failed**):
   - Validates Treasury (TR-01 to TR-08) and Compliance (CO-01 to CO-08).
   - Failures: TR-02 (nostro shortfall), TR-03 (FX rate timeout), TR-04, TR-06, TR-07, TR-08.
6. `tests/wave4/` (**62 tests / 36 passed, 26 failed**):
   - Adversarial red-team test suite.
   - Failures: Tests targeting edge-case adversarial inputs, prompt injection in remittance strings, and role bypass tests.
7. Root `tests/test_*.py` & `backend/tests/` (**458 tests / ~351 passed, 107 failed**):
   - **Root Cause of Bulk Failures**: `sqlite3.OperationalError: attempt to write a readonly database`. Because `pex_enterprise.db` is set to read-only on disk as an integrity baseline, legacy tests that instantiate `SessionLocal()` directly without mocking the database URL fail on write attempts.

### What is NOT Covered by Existing Tests:
- Live external network connections (no tests test actual network sockets, Kafka brokers, or HTTP endpoints outside localhost).
- Multi-user concurrent race conditions under heavy multi-threaded write volume.
- True LLM token usage, prompt hallucination, or non-deterministic response handling.
- Real hardware security modules (HSM) or cloud KMS key rotation.

---

## 7. Inventory of Existing Documentation in Repository

The repository contains extensive architecture documents, specifications, and sprint records:

### Core PRDs and Specifications
1. `PeX_Master_PRD_and_Technical_Blueprint.md` — The original 20-step lifecycle product and technical blueprint.
2. `PeX_41_Exception_Taxonomy_SME_Architecture_Cards.md` — Deep domain architecture cards for all 41 BIAN exception profiles.
3. `PeX_Payment_SME_Product_and_Technical_Walkthrough_Specification.md` — Detailed persona walkthrough across Maker, Approver, and Compliance flows.
4. `PeX_System_Integrity_and_Test_Charter_v1.0.md` — System integrity verification and testing standards.
5. `README.md` — Top-level project introduction and setup guide.
6. `VERSION_INVENTORY.md` — Component version registry and tracking file.

### Implementation Contracts & Architecture Deliverables
7. `PeX_Phase1_PRD_and_Engineering_Implementation_Contract_v1.0.md` — Phase 1 baseline contract.
8. `PeX_Phase2_Implementation_Contract_v1.2.md` & `v1.3.md` — Phase 2 implementation standards.
9. `PeX_Phase3_Industrialization_Architecture_v0.1.md` through `v0.1.4.md` — Phase 3 enterprise target state.
10. `PeX_Wave0A_Governance_and_Engineering_Authorization_Gate_v0.1.md` — Wave 0A port and adapter architectural contracts.
11. `PeX_Wave0B_Port_and_Adapter_Inventory_v0.1.md` — Complete catalog of 34 abstract ports and reference adapters.
12. `PeX_Wave1_Implementation_Report_v0.1.md` through `PeX_Wave3_Remediation_Implementation_Report_v0.1.md` — Sprint delivery and forensic acceptance reports for Waves 1, 2, and 3.

### Validation Audit Stream (Forensic Baseline)
13. `validation_audit/PEX_VALIDATION_FINDINGS.md` — Consolidated 34-point forensic validation matrix.
14. `validation_audit/domain_standards_audit.md` — External standards compliance audit (ISO 20022, SWIFT, Fedwire).
15. `validation_audit/enterprise_architecture_challenge.md` — Enterprise architecture scalability and boundary review.
16. `validation_audit/requirements_traceability_audit.md` — Requirements-to-code traceability matrix.
17. `validation_audit/implementation_code_audit.md` — Code-level implementation verification.
18. `validation_audit/functional_adversarial_review.md` — Functional, boundary, and red-team findings.
