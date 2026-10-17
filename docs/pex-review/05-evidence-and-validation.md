# 05-evidence-and-validation.md — Evidence Gathering, Deterministic Validation and the 5-Step Proof

**Document Status:** COMPLETE / EVIDENCE-AUDITED  
**Auditor Mode:** Objective External Review  
**Target Codebase:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Date of Audit:** October 2026  

---

## 1. Evidence Acquisition, Normalization, Schema & Authority Ranking

### Evidence Schema & Model
Evidence is governed by the Wave 0A/0B contracts in `backend/app/schemas/contracts/evidence_schemas.py`:
- `EvidencePackageEnvelope`: Top-level container carrying `case_id`, `profile_id`, `evidence_items: List[EvidenceItem]`, `evidence_sufficient: bool`, `contradictions: List[str]`, and `envelope_hash: str`.
- `EvidenceItem`: Individual evidence record carrying:
  - `evidence_id`: String UUID (e.g. `EVD-TEL-4F2A11`)
  - `evidence_type`: Domain type (e.g. `CORE_DDA_ACCOUNT`, `SSI_DIRECTORY_ACCOUNT`, `WATCHLIST_HIT`)
  - `source_system`: Source identifier (e.g. `INGESTION_GATEWAY`, `CORE_BANKING_DDA`)
  - `trust_tier`: Hierarchical enum (`TIER_1_CORE_RECORD`, `TIER_2_REGULATORY_SCHEME`, `TIER_3_AUXILIARY_DIRECTORY`, `TIER_4_HEURISTIC_INFERENCE`)
  - `validation_status`: Enum (`AVAILABLE`, `STALE`, `CONTRADICTORY`, `UNAVAILABLE`)
  - `provenance_hash`: SHA-256 digest of normalized payload
  - `is_authoritative`: Boolean flag denoting whether the record is legally/operationally binding.

### Source-Authority Ranking in Code
Source-authority ranking is formally implemented in `backend/app/adapters/reference/reference_authority_adapter.py` via `ContextualAuthorityPort`:
- **Tier 1 (Statutory / Regulatory Sovereignty)**: `STATUTORY_OFAC_EU_REGISTRY` for `LEGAL_PROHIBITION` questions (`BINDING_LEGAL`).
- **Tier 2 (Core System of Record)**: `CORE_BANKING_DDA_MASTER` for `ACCOUNT_OWNERSHIP_BALANCE` questions (`BINDING_TRANSACTIONAL`).
- **Tier 3 (Enterprise Bank Policy)**: `BANK_RISK_POLICY_DB` for `BANK_OPERATIONAL_PERMISSION` (`BINDING_OPERATIONAL`).
- **Tier 4 (Auxiliary Directory / Heuristic)**: `SWIFT_REFERENCE_MASTER`, `FEDWIRE_ABA_DIRECTORY`, `HISTORICAL_TELEMETRY`.

---

## 2. Evidence Sufficiency and Conflict Detection Logic

### Sufficiency Evaluation
Implemented in `backend/app/adapters/reference/reference_evidence_adapter.py` (`evaluate_sufficiency`):
1. **Mandatory Field Requirement**: For each profile, mandatory evidence types are resolved (e.g. for `DQ-01`, mandatory types include `CORE_DDA_ACCOUNT` and `SSI_DIRECTORY_ACCOUNT`).
2. **Fail-Closed Rule**: If any mandatory evidence item is missing (`UNAVAILABLE`) or `STALE`, `envelope.evidence_sufficient` evaluates to `False`.

### Conflict & Contradiction Detection Logic
Implemented in `reference_evidence_adapter.py` (lines 58-135) and `backend/app/services/e2e_runner.py` (lines 176-195):
1. **Canonical Contradiction Flags**: Evaluates `contradictory_evidence_flag`, `contradiction_detected`, `has_contradictory_evidence`, `contradictory_account_status`.
2. **Cross-Source Account Contradiction**:
   ```python
   core_dda = ext.get("core_dda_account") or ext.get("verified_iban")
   ssi_acct = ext.get("ssi_directory_account") or ext.get("ssi_account")
   if core_dda and ssi_acct and clean(core_dda) != clean(ssi_acct):
       package_has_contradiction = True
       contradiction_reasons.append(f"Core DDA account ({core_dda}) contradicts SSI directory ({ssi_acct})")
   ```
3. **Execution Path & Resulting Status**:
   - When a contradiction is detected, participating evidence items are marked `validation_status = EvidenceValidationStatus.CONTRADICTORY`.
   - In `e2e_runner.py`, `r_uniq` (resolution uniqueness) evaluates to `False`.
   - STP fast-lane predicate check **fails closed**.
   - Case is routed to `PENDING_APPROVAL` with queue assignment `"Investigation"` or `"Repair"`, and `resolution_rec["action"] = "INVESTIGATION_HOLD"`.

---

## 3. Deterministic Validators Inventory

All deterministic validators reside in `backend/app/services/canonicalizer.py`:

| Validator Function | Standard & Algorithm | Code Location | Input & Expected Remainder / Result | Automated Tests |
| :--- | :--- | :--- | :--- | :--- |
| `validate_iban_mod97` | **ISO 7064 MOD-97-10**<br>Rearranges first 4 chars to end; converts letters to $A=10 \dots Z=35$; computes `int(num_str) % 97 == 1`. | `canonicalizer.py:54-72` | Input: `GB82WEST12345698765432`<br>Remainder: $1$ (Valid).<br>Input: `...765423`<br>Remainder: $28$ (Invalid). | `tests/test_canonicalization.py:25-60`<br>`tests/wave0b/` |
| `validate_iban_structure` | **ISO 13616 Structure**<br>Validates 2-letter ISO country code; matches official lengths for 50+ countries; verifies non-IBAN countries (US, JP, SG); checks domestic BBAN rules (German numeric, UK alphanumeric). | `canonicalizer.py:73-100` | Input: `DE89370400440532013000` (22 chars, numeric) -> Pass.<br>Input: `US82CHAS1234567890` -> Fail (US does not issue IBANs). | `tests/contracts/test_wave0a_contracts.py` |
| `validate_fedwire_imad` | **Federal Reserve FAIM 18-Char Standard**<br>Checks regex `^[0-9]{8}[A-Z0-9]{4}[0-9]{6}$`: 8 digits date + 4 alnum source + 6 digits sequence. | `canonicalizer.py:101-110` | Input: `20261016FIRM001234` (18 chars) -> Pass.<br>Input: `20261016FIRM00123` (17 chars) -> Fail. | `tests/wave1/` |
| `is_valid_iso20022_purpose_code` | **ISO 20022 ExternalPurpose1Code**<br>Validates 4-character purpose codes against official registry (`GDSV`, `COMC`, `SALA`, `TREA`, `CORT`, etc.). | `canonicalizer.py:111-116` | Input: `"GDSV"` -> True.<br>Input: `"INVALID"` -> False. | `tests/wave1/` |

---

## 4. The 5-Step Proofs: Forensic Audit of UI Evidence Claims

In the UI Cockpit and worklist, every recommended repair presents a "5-Step Validation Proof". Code inspection of `backend/app/services/data_loader.py` (lines 93-99) reveals what each step actually executes vs. what the UI claims:

| Step Number & Title | UI Badge Label | Real Implementation Function | External Source Queried | Return Value / Audit Reality | Mismatch / Auditor Note |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **Step 1: ISO 7064 MOD-97 Format Check** | `VALIDATED` | `validate_iban_mod97` exists in `canonicalizer.py`, but `data_loader.py:94` sets a **hardcoded string**! | None | Static string: `"Raw MOD-97 remainder = 1 (Deterministic Pass)"` | **CRITICAL DEFECT**: In `data_loader.py:85`, proposed IBAN `...760001` has a mathematical remainder of $28$ (Invalid!), yet the proof string hardcodes `"remainder = 1"`. The validator function was never called! |
| **Step 2: Beneficiary Master Directory SSI** | `100% SSI MATCH` | `query_ssi_counterparty` in `icd_staging_service.py` | `backend/app/data/icd_staging_store.json` (Static local file) | Static string: `"Matched active profile in SSI Central Directory (Ref #SSI-9912)"` | **MOCKED**: Lookups query a static local JSON file. Zero live connection to bank SSI database. |
| **Step 3: Confirmation of Payee (CoP)** | `NAME MATCHED` | None (No CoP API in codebase) | None | Static string: `"Beneficiary name 'Nordhavn Components A/S' matches destination account"` | **MOCKED**: Confirmation of Payee is simulated via string template interpolation. No UK Pay.UK or European CoP API exists. |
| **Step 4: Clearing Rail & Currency Fit** | `CBPR+ PASS` | Static rule evaluation in `rule_engine.py` | None | Static string: `"Target bank BIC active and accepts pacs.008 ISO 20022 messages"` | **DOMAIN MISMATCH**: For Fedwire USD payments, the step title claims "Clearing Rail Fit" but checks SWIFT CBPR+ EUR pacs.008 rules! |
| **Step 5: Behavioral Anomaly Guardrail** | `NO ANOMALIES` | Hardcoded data structure in `data_loader.py:98` | None | Static string: `"Zero velocity anomalies. Established 3.5yr counterparty relationship"` | **MOCKED**: The UI displays a dynamic z-score chart, but the underlying numbers are hardcoded mock metrics. |

---

## 5. Hypothesis Generation and AI/LLM Usage

### Hypothesis Ranking (Control "SR-03")
- **Implementation**: Defined in `backend/app/services/data_loader.py` (lines 100-104) and `backend/app/schemas/recommendation.py` (`HypothesisRankingItem`).
- **Scoring Reality**: Hypotheses are **hardcoded static dictionaries**. For example, in `INVALID_IBAN`:
  - `HYP-1`: "Alphanumeric transposition in check digit sequence" (Confidence: `0.96`, Status: `"SELECTED"`)
  - `HYP-2`: "Incompatible domestic routing scheme" (Confidence: `0.03`, Status: `"ELIMINATED"`)
  - `HYP-3`: "Counterparty account closure" (Confidence: `0.01`, Status: `"ELIMINATED"`)
- **Scoring Method**: The confidence scores are **not** computed by a probabilistic model or Bayesian inference. They are fixed floating-point numbers written into Python source files.

### AI / LLM Usage Audit
- **Model Identified in Headers**: `"apex-reasoner-deterministic-v1"` (`backend/app/services/model_gateway.py:35`).
- **Live LLM Provider Calls**: **ZERO**. Although `backend/app/config.py` defines `PEX_MODEL_GATEWAY_MODE` with options `"mock"`, `"gemini"`, `"openai"`, `model_gateway.py` does not contain SDK client calls to Google Gemini, OpenAI, or AWS Bedrock.
- **Token Accounting**: `model_gateway.py` (lines 36-37) hardcodes:
  ```python
  prompt_tokens=120,
  completion_tokens=45
  ```
  Every execution returns exactly 120 prompt tokens and 45 completion tokens.
- **Decision Gating**: The model recommendation confidence score is **never allowed to override** deterministic validation or bank policy. In `e2e_runner.py` and `rule_engine.py`, deterministic gates (`V_det`, `E_suff`, `R_uniq`) evaluate independently of the model recommendation.

---

## 6. Historical Precedents and Provenance Tracking

### Can Historical Precedents Override Authoritative Evidence?
- **Forensic Check**: Inspected `backend/app/services/rule_engine.py`, `canonicalizer.py`, and `e2e_runner.py`.
- **Finding**: **NO**. The code enforces strict hierarchical authority:
  - If authoritative evidence indicates an account is closed (`AC04`) or contradictory, historical precedents indicating past successful payments cannot override the current negative signal.
  - In `e2e_runner.py`, unresolved contradictions immediately set `r_uniq = False`, forcing human escalation regardless of historical frequency.

### Proposed Value Provenance & Verification Independence
- **Value Origin Tracking**: In `e2e_runner.py`, every proposed change records the specific source that provided the replacement value (`verified_iban` from Core DDA or `ssi_account` from SSI Directory).
- **Verification Independence Defect**:
  - In `e2e_runner.py` (line 190): `v_det` is verified independently using `canonicalizer.validate_iban_mod97`.
  - In `data_loader.py` (demo UI seed path): The proposed value is constructed via string interpolation (`f"...76{case_idx:04d}"`), and the string `"VALIDATED_MOD97_PASS"` is attached directly by the generator without independent execution of the check-digit algorithm.
