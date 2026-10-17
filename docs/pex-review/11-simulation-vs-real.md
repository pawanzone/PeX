# 11-simulation-vs-real.md — Master Simulation vs. Real Inventory

**Document Status:** COMPLETE / EVIDENCE-AUDITED  
**Auditor Mode:** Objective External Review  
**Target Codebase:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Date of Audit:** October 2026  

---

## 1. Master Simulation vs. Real Audit Table

The table below catalogs every component, metric, data feed, and feature in the PeX codebase, classifying whether it is real logic, seeded/canned data, or simulated, where it resides in code, how an enterprise would deactivate or replace it, and whether the UI transparently discloses it as simulated.

| Capability / Metric / Displayed Value | Classification | Where It Lives (Code File & Line) | How to Turn It Off / Productionize | Disclosed in UI as Demo? |
| :--- | :--- | :--- | :--- | :---: |
| **MOD-97-10 Check Digit Math** | **REAL** | [`backend/app/services/canonicalizer.py:54-72`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/canonicalizer.py#L54-L72) | Always active; executes mathematical remainder algorithm. | N/A (Real) |
| **ISO 13616 IBAN Structure Registry** | **REAL** | [`backend/app/services/canonicalizer.py:17-28, 73-100`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/canonicalizer.py#L17-L28) | Always active; embeds official ISO registry lengths. | N/A (Real) |
| **Fedwire FAIM 18-Char IMAD Check** | **REAL** | [`backend/app/services/canonicalizer.py:101-110`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/canonicalizer.py#L101-L110) | Always active; regex validation of FAIM structure. | N/A (Real) |
| **ISO 20022 Purpose Code Validation**| **REAL** | [`backend/app/services/canonicalizer.py:111-116`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/canonicalizer.py#L111-L116) | Always active; validates `ExternalPurpose1Code`. | N/A (Real) |
| **Rule Engine NLP & AST Evaluation** | **REAL** | [`backend/app/services/rule_engine.py:1-469`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/rule_engine.py) | Dynamic in-memory AST evaluator. | N/A (Real) |
| **Inbound Drop-Folder Batch Ingestion**| **REAL** | [`backend/app/services/file_watcher.py:1-620`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/file_watcher.py) | Set `PEX_WATCHER_ENABLED=false` in env. | N/A (Real) |
| **Cryptographic SHA-256 Hash Chaining**| **REAL** | [`backend/app/core/hashing.py:1-75`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/core/hashing.py) | Active in SQLite database persistence. | N/A (Real) |
| **Sample Data Generator ("Seed Cases")**| **SEEDED** | [`backend/app/services/data_loader.py:1-450`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/data_loader.py)<br>[`scripts/init_db.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/scripts/init_db.py) | Point `DATABASE_URL` to clean DB without running seed script. | **YES** (Button: "Seed Sample Cases") |
| **5-Step Proof MOD-97 Display Remainder**| **HARDCODED** | [`backend/app/services/data_loader.py:94`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/data_loader.py#L94)<br>`"Raw MOD-97 remainder = 1"` | Code refactor required: replace hardcoded string with dynamic validator result. | **NO** (Displays as validated proof) |
| **Confirmation of Payee (CoP) Results** | **MOCKED** | [`backend/app/services/data_loader.py:96`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/data_loader.py#L96)<br>`"NAME MATCHED"` | Implement live API adapter for UK Pay.UK / European CoP directory. | **NO** (Appears as live check) |
| **SSI & Beneficiary Directory Lookups** | **MOCKED** | [`backend/app/services/icd_staging_service.py:42-48`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/icd_staging_service.py#L42-L48)<br>Reads `icd_staging_store.json` | Replace `icd_staging_service.py` with live SQL/REST core banking adapter. | **NO** (Appears as live inquiry) |
| **SWIFT BIC & ABA Routing Lookups** | **MOCKED** | [`backend/app/services/icd_staging_service.py:27-40`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/icd_staging_service.py#L27-L40)<br>Reads `icd_staging_store.json` | Mount live SWIFTRef directory file or FedACH web service. | **NO** (Appears as live lookup) |
| **Sanctions & Watchlist Screening Hits**| **MOCKED** | [`backend/app/services/icd_staging_service.py:54-60`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/icd_staging_service.py#L54-L60)<br>Reads `icd_staging_store.json` | Replace with live Fircosoft/Actimize adapter implementing `RegulatoryScreeningPort`. | **NO** (Appears as real screening) |
| **Nostro & DDA Account Balances** | **MOCKED** | [`backend/app/adapters/reference/reference_nostro_position_adapter.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/adapters/reference/reference_nostro_position_adapter.py) | Implement live Core Banking DDA adapter for `NostroPositionPort`. | **NO** (Displays as exact balance) |
| **Risk Evaluation Scores & Mule Velocity**| **HARDCODED** | [`backend/app/services/data_loader.py:98`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/data_loader.py#L98)<br>[`model_gateway.py:31`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/model_gateway.py#L31) (`risk_score=0.75`) | Connect live transaction monitoring machine learning engine. | **NO** (Renders as live risk graph) |
| **AI LLM Gateway & Token Accounting** | **HARDCODED** | [`backend/app/services/model_gateway.py:36-37`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/model_gateway.py#L36-L37)<br>`prompt_tokens=120`, `completion=45` | Implement live API calls to Google Gemini or AWS Bedrock in `model_gateway.py`. | **NO** (Appears as real AI inference) |
| **Outbound Bank Execution & Receipts** | **MOCKED** | [`backend/app/services/action_executor.py:64-75`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/action_executor.py#L64-L75)<br>Synthetic `ACK-SIM-...` | Implement live payment engine webhook / MQ consumer. | **NO** (Displays as confirmed settlement) |
| **Autonomous STP Settlement Shortcut** | **SIMULATED** | [`backend/app/services/file_watcher.py:575`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/file_watcher.py#L575)<br>Sets `status = SETTLED` directly | Architectural fix: require external bank execution callback before setting `SETTLED`. | **NO** (Case marked settled in UI) |
| **Dispatch Latency Metric ("14ms")** | **HARDCODED** | [`backend/app/services/data_loader.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/data_loader.py)<br>`details={"latency": "14ms"}` | Compute real network RTT timing in outbound adapter. | **NO** (Displays as live telemetry) |
| **"Live RTGS Cutoff Radar" Clock** | **SIMULATED** | `frontend/src/components/CutoffRadar.tsx`<br>Uses `setInterval` on client clock | Feed real clearing rail cutoff calendar from `ClearingRailCalendarPort`. | **NO** (Title says "Live RTGS") |
| **Relative Ingestion Timers ("2m ago")** | **DYNAMIC UI** | Computed in React components against client time | Normal UI behavior. | N/A (Standard UI rendering) |
| **Persona Switching & Identity RBAC** | **DEMO ONLY** | [`frontend/src/components/PersonaSwitcher.tsx`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/frontend/src/components/PersonaSwitcher.tsx)<br>Alters HTTP headers | Integrate enterprise IdP via OAuth2/OIDC (Okta, Azure AD, Ping). | **YES** (Dropdown labeled "Demo Persona") |

---

## 2. Summary of Demo Disclosures to Product Reviewers

1. **What is Candidly Labeled as Demo**:
   - The **Persona Switcher** dropdown in the header is explicitly labeled with user names and roles for demonstration.
   - The **"Seed Sample Cases"** button in the administration panel is clearly designated as a data generator.
2. **What Appears Real But Is Simulated / Seeded**:
   - The **"Live RTGS Cutoff Radar"** presents itself as a live interbank market monitoring clock, but runs entirely off browser `setInterval` math.
   - The **5-Step Validation Proofs** render badges (`VALIDATED`, `NAME MATCHED`, `CBPR+ PASS`) that suggest live directory and CoP inquiries, but are populated from hardcoded static strings.
   - The **AI Model Token Metrics** (`120 prompt tokens`, `45 completion tokens`) suggest live LLM reasoning, but are static integers written into the Python source.
   - The **Bank Settlement Receipts** (`"ACK-SIM-..."`, `"SETTLED_CONFIRMED"`) suggest real payment engine reconciliation, but are synchronously generated in-memory within 1 millisecond.
