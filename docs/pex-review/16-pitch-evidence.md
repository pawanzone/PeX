# 16-pitch-evidence.md — Pitch Claims and Evidence Base

**Document Status:** COMPLETE / EVIDENCE-AUDITED  
**Auditor Mode:** Objective External Review  
**Target Codebase:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Date of Audit:** October 2026  

---

## 1. Candidate Positioning Claims Evaluation

The table below evaluates the 12 candidate commercial positioning claims against verified codebase evidence. Each claim is labeled strictly as **SUPPORTED**, **PARTIAL**, or **NOT SUPPORTED**:

| Positioning Claim | Audit Status | Code Evidence (File & Line / Command) | Single Biggest Caveat / Reality |
| :--- | :---: | :--- | :--- |
| **1. Vendor-Neutral Architecture** | **PARTIAL** | 34 abstract ports defined in [`backend/app/ports/`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/ports/). Canonical models in `canonical.py`. | **Zero vendor adapters exist today**. All 34 implementations in `adapters/reference/` are in-memory mocks using Python dicts and deques. |
| **2. Fast to Start in Shadow Mode** | **SUPPORTED** | Configured `PEX_OPERATION_MODE=SHADOW` in `config.py:24`; central choke point [`dispatch_to_bank_handoff()`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/outbound_port.py#L14) completely suppresses outbound network execution and transitions cases to `SHADOW_RECORDED`. | Demonstrates real fail-safe shadow mode. Live shadow-mode comparison dashboard against bank outcomes requires telemetry feed. |
| **3. Evidence-First Recommendations** | **SUPPORTED** | Evidence envelope contract in `evidence_schemas.py`; conflict detection in `reference_evidence_adapter.py:58-95`. | Lookups currently query static local JSON (`icd_staging_store.json`) rather than live bank systems. |
| **4. Deterministic Validation Independent of AI** | **SUPPORTED** | Real ISO 7064 MOD-97 math (`canonicalizer.py:54`), FAIM IMAD regex, and ISO purpose codes. | Runtime MOD-97 check verified; demo pair was broken in seed strings, now dynamically computed via P0-5. |
| **5. Works with ISO 20022 XML Schemas** | **NOT IMPLEMENTED** | Zero W3C XML parsers or serializers exist for `pacs.008`, `camt.056`, `camt.029`, or `camt.027`. | **NOT IMPLEMENTED (not Confirmed)**. Platform operates exclusively on JSON payloads; XML schemas exist only in documentation and comments. |
| **6. Strict Segregation of Duties (Maker-Checker)** | **SUPPORTED** | `maker_id` stamped at submission; `check_can_approve()` and `approval_engine.py` reject `approver_id == maker_id` even across persona switches. Dual-auth enforced at $250k. | Four-eyes governance is now strictly enforced server-side. |
| **7. Bank Retains Execution; PeX Never Settles** | **SUPPORTED** | Governed actions terminate in `HANDED_TO_BANK` with `AWAITING_BANK_ACK`; synthetic `ACK-SIM` removed. Only inbound authenticated `POST /api/bank/outcome` can set `SETTLED`. | Enforced by single `transition_case()` choke point with verified transition table. |
| **8. Evidence Sufficiency (E_suff) in STP** | **PARTIAL** | e2e_runner evaluates 8 predicates including $E_{\text{suff}}$ against dynamic evidence requirements. `/api/stp/eligible` and batch-release aligned to e2e gate. | **PARTIAL (not Confirmed)**: Evaluates pre-bundled JSON evidence packages; live dynamic acquisition from external bank core banking systems is simulated. |
| **9. MOD-97 Mathematical Checksum** | **SUPPORTED** | Dynamic runtime calculation in `canonicalizer.py:54` and `data_loader.py:84-98`. Seeded pair inverted defect resolved by P0-5 (original invalid remainder 49 -> repair valid remainder 1). | Fixed by P0-5 remediation; UI displays real calculated modulo remainder. |
| **10. Configurable Per Bank Without Code Changes** | **PARTIAL** | Dynamic policy rules synthesizable via NLP and stored in memory/DB (`rule_engine.py:74`). Unified threshold ($100k) configured in `BankRiskThresholds`. | Adding new user roles, tenant IDs, or connecting real bank payment hubs requires Python code modifications. |
| **11. Covers Multiple Domains Beyond Data Repair** | **PARTIAL** | 41 profiles defined across 5 domains in `canonical.py:29-83`. | Only 9 profiles execute real validation logic; 30 profiles return static seeded responses; 2 profiles are empty stubs. |
| **12. Immutable Provenance Audit Trail** | **SUPPORTED** | SHA-256 sequential hash pointer chain extended with P0-6 provenance fields (`before_value`, `after_value`, `policy_version`, `model_version`, `reason_code`, `maker_id`); tamper detection verified. | Sequential hash chain in SQLite; not a distributed Merkle DAG. |

---

## 2. What a Design-Partner Demo Can Truthfully Show Today

An enterprise technical sales demo must present only **`IMPLEMENTED`** capabilities to withstand scrutiny from bank architects:

| Demo Step & Case ID | What Is Shown | What Is Truthfully Executed in Backend | What Must Be Disclosed |
| :--- | :--- | :--- | :--- |
| **1. Drop-Folder Batch Ingestion** (`BATCH-MIXED-001.json`) | Dragging a 6-record mixed exception batch into `input/` folder. | `file_watcher.py` detects file arrival within 1 second, isolates malformed records, suppresses duplicates, and archives input. | Inbound feed is pre-parsed JSON, not raw SWIFT MT or ISO 20022 XML. |
| **2. Deterministic MOD-97 Validation** (`PEX-STAGE4-REC01-STP`) | Resolving an invalid IBAN with automated check digit calculation. | `canonicalizer.py:54-72` executes real ISO 7064 remainder math (`int(num_str) % 97 == 1`). | Demonstrates real algorithmic check digit validation. |
| **3. Evidence Conflict Fail-Closed Gate** (`PEX-STAGE4-REC04-CONFLICTING-EVIDENCE`) | Cross-source conflict (Core DDA vs SSI directory) automatically blocking STP. | `reference_evidence_adapter.py:85-95` detects contradictory accounts; `e2e_runner.py:188` sets `r_uniq = False`, routing to human review. | Demonstrates that PeX fails closed on ambiguous evidence. |
| **4. Natural Language Rule Synthesis & Live Simulation** | Typing: *"Fast-lane auto-approve GBP payments under £25k with confidence > 95%"* into Rule Studio. | `rule_engine.py:74-260` translates prompt into executable JSON AST; `simulate_impact()` calculates matches and exposure across cases. | Demonstrates real dynamic policy synthesis without code redeployment. |
| **5. Continuous Audit Trail Verification** | Inspecting the audit drawer and clicking "Verify Cryptographic Provenance". | `audit_service.verify_chain()` reads all SQLite events, recomputes SHA-256 digests, and validates sequential links. | Disclose as sequential SHA-256 hash pointer chain (not a Merkle DAG). |

---

## 3. Numbers in UI That Must NOT Be Used in a Sales Pitch

The following metrics displayed in the user interface or presentation decks are **not computed from real production data** and will fail external verification:

1. **"STP Rate: 64.2%"**: Hardcoded synthetic telemetry metric in [`stp_engine.py:610-645`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/stp_engine.py#L610-L645).
2. **"Average Resolution Speed: 4.2m"**: Hardcoded mock metric in telemetry responses.
3. **"Estimated Operational Savings ($42.50 per case)"**: Multiplies settled cases by an arbitrary, unvalidated `$42.50` constant in [`stp_engine.py:633`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/stp_engine.py#L633).
4. **"Live RTGS Cutoff Radar"**: Time buckets (`<1h`, `1-2h`) are computed dynamically in the React browser component using `setInterval` against client machine time, not live clearing house feeds.
5. **"Hypothesis Confidence Scores (96%, 3%, 1%)"**: Fixed floating-point numbers written into Python dictionary source files in [`data_loader.py:100-104`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/data_loader.py#L100-L104).
6. **"Processing Latency: 14ms"**: Static string literal in `data_loader.py`.
7. **"Raw MOD-97 Remainder = 1"**: Displayed on the seeded demo case in [`data_loader.py:94`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/data_loader.py#L94), despite the proposed IBAN having a real mathematical remainder of 28.

---

## 4. Minimum Changes for a Credible 15-Minute Zero-Simulation Demo

To conduct an unassailable 15-minute live technical walkthrough with an institutional bank review team, the engineering team must implement four targeted fixes:

1. **Fix the Inverted Demo IBAN Pair (`DEF-04`, Effort: S — 1 Day)**:
   - In [`backend/app/services/data_loader.py:84-85`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/data_loader.py#L84-L85), seed a truly invalid original IBAN (`GB82WEST12345698765423`, remainder 49) and a truly valid proposed repair (`GB82WEST12345698765432`, remainder 1).
   - In `data_loader.py:94`, call `validate_iban_mod97()` dynamically to display the real calculated remainder.
2. **Halt Case Lifecycle at `DISPATCHED` (`DEF-01`, Effort: S — 1 Day)**:
   - In [`action_executor.py:82`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/action_executor.py#L82), change `case["status"] = LifecycleStage.DISPATCHED.value`.
   - Update UI status badge to show "Dispatched to Bank Clearing" rather than "Settled".
3. **Enforce Maker $\neq$ Checker Identity (`DEF-03`, Effort: S — 1 Day)**:
   - In `approval_engine.py`, add: `if approver_id == case.get("maker_id"): return False, "Segregation of duties violation: Maker cannot authorize own case"`.
   - Demonstrates real, unbypassable four-eyes governance.
4. **Correct Navigation Badge Counts (`DEF-10`, Effort: S — 1 Day)**:
   - Update `frontend/src/App.tsx` navigation badges to reflect filtered queue counts (26 for Repair Queue, 88 for total cases, 25 for Approvals Desk).
