# PeX Wave 0B — Architecture Delta Report v0.1
## Platform Runtime & Infrastructure Enablement — Delta from Wave 0A Baseline

======================================================================
1. EXECUTIVE SUMMARY & GOVERNANCE CONTEXT
======================================================================

- **Authorization Baseline**: `PeX_Wave0B_Implementation_Authorization_Gate_v0.1.1.md` (OPTION A Authorized)
- **Authoritative Architecture**: `PeX_Evidence_Acquisition_and_Resolution_Contract_v0.3.1.md`
- **Starting Git Commit**: `3ee708d` (on branch `phase3/wave0b-runtime-infrastructure`)
- **Baseline Regression Test Suite**: 462 / 462 passed (100% green)

Wave 0A established the architectural contracts, E2E JSON scaffolding, and structural proof for 12 canonical scenarios across the 41-profile taxonomy. However, Wave 0A relied on in-memory dictionary scaffolding (`mandatory_map` inside `e2e_runner.py`) and simulated static resolution.

Wave 0B transitions the PeX platform from static contract validation to a **fully dynamic, runtime-driven platform engine** supporting:
1. Single Published Bank Evidence Required JSON per `(tenant_id, profile_id)`.
2. Provider-neutral ports & reference adapters for multi-tenant configuration, evidence persistence, core banking inquiries, and ledger handoffs.
3. Multi-mode evidence acquisition engine across 4 acquisition modes (Modes 1, 3, 4 operational; Mode 2 progressive).
4. PeX-native HITL closed loop with real-time dynamic gap computation, guided operator evidence provision, and immediate deterministic re-evaluation.
5. Strict enforcement of all architectural invariants: 8-predicate formula, bank execution boundary (`BANK_HANDOFF_READY` / `execution_owner = "BANK"`), fail-closed governance compiler, and zero cloud vendor SDK lock-in.

---

======================================================================
2. ARCHITECTURE COMPONENT DELTA MATRIX
======================================================================

| Component / Subsystem | Wave 0A Baseline (Static Scaffold) | Wave 0B Runtime (Dynamic Platform) | Architectural Impact & Rationale |
|---|---|---|---|
| **Evidence Configuration** | Hardcoded `mandatory_map` dictionary in `e2e_runner.py` | `DynamicEvidenceConfigResolver` via `ConfigurationStorePort` loading published JSON configurations | Enables bank-configurable evidence policies without code modifications or redeployment. Zero 3-way merging. |
| **Governance Validation** | Manual inspection / schema validation only | Automated `GovernanceCompiler` with fail-closed compiler rules rejecting regulatory/trust tier bypass | Guarantees banks cannot weaken regulatory mandates or downgrade trust tiers. |
| **Expression Evaluation** | Simple static boolean lookups | Sandboxed, AST-based `ConditionalExpressionEngine` supporting context variables (`amount`, `corridor`, `currency`, `error_code`) | Enables deterministic conditional evidence requirements without code execution vulnerabilities. |
| **Evidence Store** | Ephemeral context dictionaries | Typed `EvidenceStorePort` and `ReferenceEvidenceStoreAdapter` with SHA-256 content-addressing and deduplication | Prevents duplicate evidence ingestion, guarantees audit immutability, and supports multi-mode gathering. |
| **Acquisition Gateway** | Mode 1 only (pre-bundled payload in input fixture) | `AcquisitionGateway` coordinating Modes 1 (Inbound), 2 (API Connector), 3 (Bank Push), and 4 (HITL) | Provides unified evidence acquisition across batch, automated callback, and human workflows without live external API dependency. |
| **HITL Integration** | Static human queue status simulation | `HITLWorkflowService` generating dynamic gap dossiers, tracking operator evidence uploads, and triggering re-evaluation | Integrates human operators directly into the evidence sufficiency loop with instant deterministic re-evaluation. |
| **Re-Evaluation Engine** | Single-pass evaluation in harness | State-managed re-evaluation lifecycle preserving idempotency and 8-predicate invariants across iterations | Guarantees evidence additions deterministically advance or hold case state without duplicate side-effects. |
| **Core Banking & Ledger Handoff** | Simulated stub objects in memory | Formal `CoreBankingPort`, `AccountingLedgerPort`, `ClearingHandoffPort` with typed payload contracts | Defines immutable boundary: PeX prepares and signs `BANK_HANDOFF_READY` payload; Bank core executes accounting. |
| **Audit & Provenance** | Wave 0A JSON audit records | Cryptographic SHA-256 Merkle-like chaining across evidence ingestion, evaluation, and HITL actions | Guarantees forensic immutability and tamper-evidence across the entire case lifecycle. |

---

======================================================================
3. DATA CONTRACT & SCHEMA EVOLUTION
======================================================================

### 3.1 New JSON Schemas & Pydantic Models (`backend/app/schemas/contracts/evidence_config_schemas.py`)
1. `EvidenceRuleDefinition`: Model for individual rule configuration (evidence type, mandatory/optional flag, min trust tier, condition expression, acquisition modes, freshness TTL).
2. `HitlFieldDefinition`: Definition for interactive operator input fields in Mode 4 (field ID, label, type, validation regex, required flag).
3. `HitlActionDefinition`: Definition of operator actions (e.g., `REQUEST_CUSTOMER_CONFIRMATION`, `SUPPLY_CORRECTED_IBAN`, `OVERRIDE_NON_CRITICAL`).
4. `BankEvidenceRequiredConfig`: Complete root configuration document per `(tenant_id, profile_id)` containing version, rules list, HITL workflow config, and governance signatures.
5. `EvidenceItemModel`: Typed representation of an acquired evidence unit with source metadata, trust tier, hash, and payload.
6. `HitlEvidenceSubmissionRequest` / `HitlEvidenceSubmissionResponse`: Payloads for human operator evidence upload and immediate re-evaluation response.

### 3.2 Immutability of Phase 2 Canonical Models
All Wave 0A and Phase 2 canonical schemas (`backend/app/schemas/canonical.py`, `backend/app/schemas/bank_events.py`, `backend/app/schemas/recommendation.py`) remain **100% untouched and backward-compatible**. Wave 0B models extend platform capability via hexagonal port contracts without altering domain entity definitions.

---

======================================================================
4. 8-PREDICATE STP FORMULA & INVARIANT PRESERVATION
======================================================================

The 8-predicate formula remains strictly immutable:

$$\text{STP\_ELIGIBLE} = E_{\text{suff}} \land R_{\text{det}} \land R_{\text{uniq}} \land V_{\text{det}} \land V_{\text{auth}} \land P_{\text{bank}} \land C_{\text{comp}} \land X_{\text{pre}}$$

Wave 0B enforces the following mathematical and architectural constraints:
1. **$E_{\text{suff}}$ Isolation**: $E_{\text{suff}} = \text{True}$ is a prerequisite for evaluation of downstream predicates; it does **NOT** equal `STP_ELIGIBLE`.
2. **AI Confidence $\ne$ Authority**: AI confidence score carries exactly $0\%$ autonomous execution authority. Recommendations are advisory only.
3. **Execution Ownership**: Terminal execution state is `BANK_HANDOFF_READY`. `execution_owner` is permanently `"BANK"`. PeX never executes ledger updates or SWIFT transmissions directly.
4. **Deterministic Sandboxing**: Conditional expressions evaluate only allowed variables and operators without dynamic Python `eval()` or code execution.

---

======================================================================
5. PROVIDER NEUTRALITY & ZERO VENDOR LOCK-IN
======================================================================

Wave 0B strictly adheres to Hexagonal Architecture (Ports and Adapters):
- **Ports (`backend/app/ports/`)**: Pure Python abstract interfaces defining domain contracts.
- **Reference Adapters (`backend/app/adapters/reference/`)**: Self-contained, dependency-free reference implementations for testing and standalone execution.
- **Forbidden SDKs**: No imports of `boto3`, `google.cloud`, `azure`, `kafka`, `openai`, or `anthropic` in domain, port, or core service packages. AST validation test (`tests/contracts/test_provider_neutrality.py`) enforces this boundary in automated CI.

---

======================================================================
6. DELTA SUMMARY CONCLUSION
======================================================================

Wave 0B delivers the complete runtime infrastructure required for dynamic evidence-driven resolution while preserving 100% backward compatibility with all 462 Phase 2 and Wave 0A regression tests.
