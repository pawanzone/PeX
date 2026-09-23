# PeX — Replit Setup & Operational Execution Guide

**Complete Operational Guide for Running PeX inside Replit**  
**Version:** `1.0.0` (Aligned with Release `v1.9.4`)  
**Date:** September 23, 2026  

---

## 1. Prerequisites & Environment Overview

PeX runs seamlessly in the standard Replit cloud environment without requiring any external cloud accounts, AWS/GCP/Azure credentials, or paid API keys.

- **Python Version:** 3.11.x
- **Node.js Version:** 20.x (Optional, only needed if rebuilding frontend from source)
- **Database:** SQLite 3 (Automatic zero-config local database file `pex_enterprise.db`)
- **AI Gateway Mode:** `mock` (Deterministic synthetic reasoner enabled by default)
- **Frontend:** Pre-built, production-optimized single-file SPA bundle served directly by FastAPI

---

## 2. Replit Configuration Files

The repository includes pre-configured Replit execution files:

### 2.1. `.replit`
```toml
modules = ["python-3.11", "nodejs-20"]
run = "python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000"

[nix]
channel = "stable-24_05"

[deployment]
run = ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
deploymentTarget = "autoscale"

[[ports]]
localPort = 8000
externalPort = 80
```

### 2.2. `replit.nix`
```nix
{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.nodejs_20
  ];
}
```

---

## 3. Step-by-Step Launch Instructions

### Step 1: Import Repository to Replit
1. Open [Replit](https://replit.com).
2. Click **Create Repl** -> **Import from Git**.
3. Paste the repository URL or upload the project files.

### Step 2: Install Python Dependencies
In the Replit Shell / Terminal, execute:
```bash
pip install -r requirements.txt
```

### Step 3: Verify Pre-Built Frontend Assets
PeX comes with a verified, authoritative single-page application bundle located at `frontend/dist/index.html`. No Node.js build step is required to run the application immediately.

*(Optional)* If you modify frontend React components in `frontend/src/`, recompile the bundle:
```bash
python build_guided_frontend.py
```

### Step 4: Launch the Unified Server
Click the green **Run** button in Replit, or run directly in the Shell:
```bash
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```
- Replit will automatically detect port `8000` and open the interactive Webview.
- The root URL `/` serves the full interactive PeX Operational Cockpit, Worklist, Approvals Desk, and Policy Studio.
- The API documentation is available at `/docs` (Swagger UI).

---

## 4. Verifying Health and Database Initialization

### 4.1. Health Check Endpoint
To verify server health and database connectivity, execute:
```bash
curl -s http://localhost:8000/api/health
```
**Expected Response:**
```json
{
  "status": "healthy",
  "project": "PeX Enterprise Payment Exception Platform",
  "version": "1.0.0",
  "database": {
    "dialect": "sqlite",
    "is_sqlite": true,
    "is_relational_postgres": false,
    "is_aws_postgres": false,
    "total_cases_loaded": 233,
    "total_rules_loaded": 19,
    "total_icd_nodes_loaded": 5
  },
  "model_gateway": {
    "mode": "mock",
    "ready": true
  }
}
```

---

## 5. Running Automated Verification Suites in Replit

To run the complete automated test suite (111 tests covering all remediations, security tokenization, Maker-Checker rules, and Replit readiness):

```bash
python -m pytest tests/ backend/tests/ -v
```

**Expected Result:**
```
====================== 111 passed, 5 warnings in 13.98s =======================
```

To run specifically the Replit Readiness test suite:
```bash
python -m pytest tests/test_replit_readiness.py -v
```

---

## 6. Environment Variables Reference (Optional Configuration)

All environment variables have safe, out-of-the-box defaults in Replit:

| Variable | Default Value | Description |
|---|---|---|
| `PEX_MODEL_GATEWAY_MODE` | `mock` | AI Reasoner mode (`mock`, `gemini`, `openai`). In `mock` mode, zero API keys are required. |
| `GEMINI_API_KEY` | `""` | Google Gemini API key (only needed if `PEX_MODEL_GATEWAY_MODE=gemini`). |
| `OPENAI_API_KEY` | `""` | OpenAI API key (only needed if `PEX_MODEL_GATEWAY_MODE=openai`). |
| `DATABASE_URL` | `sqlite:///./pex_enterprise.db` | Relational database connection string. |
| `JWT_SECRET` | `pex-enterprise-secret-key-2026-sha256` | Cryptographic secret for session token signing. |

---

## 7. Troubleshooting in Replit

| Issue | Root Cause | Resolution |
|---|---|---|
| **Port Conflict / Webview not loading** | Replit assigned a different default port. | Run with `--port 8000` or `--port 5000` as defined in `.replit`. |
| **Pydantic Validation Error** | Schema type mismatch. | Ensure Python 3.11 is active (`python --version`) and dependencies are installed from `requirements.txt`. |
| **Missing Cases in UI** | SQLite database file was not initialized. | The database automatically seeds on server startup (`backend/app/main.py`). If needed, delete `pex_enterprise.db` and restart uvicorn. |
| **API returns 404 for unknown routes** | Strict API routing guardrail (`MST-047`). | API endpoints must begin with `/api/`. All non-API GET routes are routed to the frontend SPA. |
