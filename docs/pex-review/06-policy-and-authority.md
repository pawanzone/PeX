# 06-policy-and-authority.md — Policy Engine and Authority Matrix

**Document Status:** COMPLETE / EVIDENCE-AUDITED  
**Auditor Mode:** Objective External Review  
**Target Codebase:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Date of Audit:** October 2026  

---

## 1. Policy & Rules Engine ("Rule & Policy Studio", "BRMS")

### Real Implementation vs. UI Simulation
The platform contains a functioning, dynamic business rule engine in [`backend/app/services/rule_engine.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/rule_engine.py#L1-L469) (`DynamicRuleEngine`):
- **Natural Language Parsing & Synthesis**: [`synthesize_rule`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/rule_engine.py#L74-L260) uses regular expressions to parse monetary amounts ([`parse_numeric_amount`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/rule_engine.py#L37)), confidence scores ([`parse_confidence_percentage`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/rule_engine.py#L57)), currencies, country aliases, and exception profiles. It translates text prompts into executable Abstract Syntax Tree (AST) JSON clauses.
- **Rule Simulation**: [`simulate_impact`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/rule_engine.py#L355-L407) evaluates candidate AST rules against all in-memory benchmark cases, calculating matched counts, total exposure, and sample case diffs.
- **Live Runtime Evaluation**: [`evaluate_case_policies`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/rule_engine.py#L409-L466) evaluates active rules for inbound payments and sets `dual_auth_required`, `required_tiers`, `tier_roles`, `fast_lane_eligible`, and `target_queue`.

### Where Rules Are Stored and Versioned
- **Storage Location**: Governed rules are stored in the data repository cache [`repo._policy_rules`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/data_loader.py). In the SQLite database, rules are seeded into persistent tables or loaded via [`/api/rules`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/api/endpoints/rules.py).
- **Rule Versioning**: Rules carry a string attribute `version` (default `"1.0"`, `"1.1"`), but there is **no automated GitOps versioning, branch comparison, or historical rollback engine** implemented in code. Updating a rule overwrites its dictionary in memory.

---

## 2. Maker-Checker Segregation of Duties (SoD)

### How SoD is Enforced (Post-P0 Remediation)
Segregation of Duties is implemented across [`backend/app/core/security.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/core/security.py#L71-L105) (`check_can_approve`) and [`backend/app/services/approval_engine.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/approval_engine.py):
1. **Operator Role Restriction**: An `OPERATOR` role cannot submit approvals:
   ```python
   if role == UserRole.OPERATOR:
       return False, "Operators cannot approve repairs (Maker-Checker policy violation)."
   ```
2. **Approval Monetary Limits**: Approvers cannot authorize amounts exceeding their configured limits (e.g. Operations Approver is capped at $250,000 USD).
3. **Queue Gating**: Only Compliance Approvers, Risk Approvers, or Admins can clear Compliance queue cases.
4. **Server-Enforced Maker $\neq$ Checker Identity (P0-3 Remediation)**:
   - When a maker submits a repair via `/api/cases/{id}/submit-to-checker`, the backend stamps `case.maker_id = analyst_id`.
   - `check_can_approve()` receives `maker_id=case.get("maker_id")`. If `approver_id == maker_id`:
     ```python
     if maker_id and user_id == maker_id:
         return False, "Maker cannot approve own case (Segregation of Duties policy violation)."
     ```
   - For two-tier approvals, `approval_engine.py` also validates that `tier_2_approver != tier_1_approver`.
   - **Protection against Persona Switching**: Even if an operator switches persona in the UI header from `OP-9012` to `APR-3191`, the persistent `case.maker_id` ensures that the identical user identity is blocked from self-approving.

---

## 3. Approval Thresholds and Dual Authorization

### Threshold Configuration
- Configured in [`backend/app/config.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/config.py#L22):
  ```python
  DUAL_AUTH_THRESHOLD: float = 250000.0  # USD equivalent
  ```
- Evaluated in [`rule_engine.py:452`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/rule_engine.py#L452):
  ```python
  if amount >= 250000.0 and not dual_auth_required:
      dual_auth_required = True
      required_tiers = 2
      tier_roles = ["OPERATIONS_APPROVER", "RISK_APPROVER"]
  ```

### What "Dual Auth Required" Means in the Data Model
When `dual_auth_required = True`:
1. First eye authorization transitions the case from `PENDING_APPROVAL` to `AWAITING_SECOND_APPROVAL` ([`approval_engine.py:95`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/approval_engine.py)).
2. The case is re-queued for second-tier authorization (`tier_roles = ["RISK_APPROVER"]` or `ADMIN`).
3. Outbound dispatch is blocked until both approval records are appended to `CaseModel.approval_history` by two distinct approvers.

---

## 4. STP and "Fast-Lane" Eligibility Rule in Code

### The Exact STP Qualification Rule (Unified Under P0-2)
Governed in [`backend/app/services/stp_engine.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/stp_engine.py) and [`e2e_runner.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/e2e_runner.py#L140-L220). Under **P0 Remediation (P0-2)**, both batch ingestion and REST endpoints (`/api/stp/eligible`, `/api/stp/batch-release`) enforce the **identical 8-predicate gate**:

$$\text{STP\_Eligible} = E_{\text{suff}} \land P_{\text{allow}} \land R_{\text{det}} \land R_{\text{uniq}} \land V_{\text{det}} \land V_{\text{auth}} \land \neg C_{\text{hold}} \land A_{\text{limit}}$$

1. $E_{\text{suff}}$ (**Evidence Sufficiency**): All mandatory evidence items are present and non-stale.
2. $P_{\text{allow}}$ (**Policy Allowed**): Rule engine allows auto-repair for this profile/amount.
3. $R_{\text{det}}$ (**Deterministic Derivation**): Repair value derived via deterministic rule/lookup.
4. $R_{\text{uniq}}$ (**Resolution Uniqueness**): Zero conflicting directory accounts or ambiguity.
5. $V_{\text{det}}$ (**Deterministic Validation**): Mathematical MOD-97 check or ISO schema passes.
6. $V_{\text{auth}}$ (**Authority Verification**): Resolution source is verified authoritative.
7. $\neg C_{\text{hold}}$ (**Zero Compliance Hold**): Domain != Compliance, no sanctions/AML alert.
8. $A_{\text{limit}}$ (**Amount Limit**): Transaction amount $\le \$100,000.00$ (unified bank policy threshold).

### Threshold Reconciliation (P0-2)
- **Previous Divergent Values**:
  - `file_watcher.py`: $10,000.00 (Autonomous cap)
  - `/api/stp/eligible`: $25,000.00 (Batch cap)
  - `e2e_runner.py` / `policy_adapter.py`: $100,000.00 ($A_{\text{limit}}$ cap)
- **Reconciled Reality**: Reconciled to a single unified **$100,000.00** threshold defined in `BankRiskThresholds.max_stp_amount` and applied uniformly across `file_watcher.py`, `stp_engine.py`, `reference_policy_adapter.py`, and `e2e_runner.py`.

### Operational Patterns: Zero-Touch vs. Supervised Batch Release
1. **Autonomous Zero-Touch STP**: Inbound batch files meeting all 8 predicates are processed and dispatched directly to `HANDED_TO_BANK` (or `SHADOW_RECORDED` in shadow mode).
2. **Supervised 1-Click Fast-Lane Batch Release**: In the UI cockpit, operators view the pre-qualified queue and trigger bulk handoff via [`/api/stp/batch-release`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/api/endpoints/stp.py).

### What "1-Click Release" Does Technically (Post-P0 Remediation)
Inspecting [`stp_engine.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/stp_engine.py):
- **What is Written to Database**:
  1. Inserts `ApprovalRecordModel` recording the batch approver's identity and timestamp.
  2. Inserts `GovernedActionModel` with `target_system="SWIFT_CBPR_FASTLANE_GATEWAY"`, `status="HANDED_TO_BANK"`.
  3. Transitions case via `transition_case()` to `LifecycleStage.HANDED_TO_BANK.value` with `AWAITING_BANK_ACK` (no synthetic `ACK-SIM-` receipts).
  4. Appends audit event with full provenance payload (policy version, model version, actor, maker_id) and updates SHA-256 chain.
- **External Hand-off**: In LIVE mode, routes through `dispatch_to_bank_handoff()`; in SHADOW mode, suppresses external transmission and records `SHADOW_RECORDED`.

## 5. Compliance and Sanctions Cases Handling

### Routing & Desk Gating
- Handled in [`file_watcher.py:580-582`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/file_watcher.py#L580-L582): If `domain == "COMPLIANCE"` or profile is in `["SANCTIONS_SUSPECTED", "AML_ALERT", "PEP_MATCH", "KYC_EXPIRED", "RESTRICTED_CORRIDOR"]`, the case is routed to `target_queue = "Compliance"`.

### Role Visibility & Action Restrictions
- **Server-Side Gate**: [`backend/app/core/security.py:76-77`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/core/security.py#L76-L77):
  ```python
  if queue == "Compliance" and role not in [UserRole.COMPLIANCE_APPROVER, UserRole.ADMIN, UserRole.RISK_APPROVER]:
      return False, "Only Compliance & Risk Approvers can clear Compliance queue exceptions."
  ```
- **Generic Repair Flows Blocked**: An operator cannot execute field repairs on a compliance-held transaction. The UI displays the case in read-only mode for operators.

### Available Compliance Dispositions
Defined in [`backend/app/schemas/approval.py:17-25`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/schemas/approval.py#L17-L25):
1. `CLEAR_FALSE_POSITIVE`: Authorizes release after confirming homonym disambiguation.
2. `GRANT_KYC_WAIVER`: Grants temporary 30-day processing waiver for lapsed counterparty KYC.
3. `REJECT`: Blocks payment permanently due to confirmed sanctions/embargo violation.
4. `ESCALATE`: Refers case to Financial Intelligence Unit (FIU) for Suspicious Activity Report (SAR) filing.

---

## 6. Authority Limits Per Role (Server-Side Enforcement)

Monetary limits are defined in [`backend/app/core/security.py:59-65`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/core/security.py#L59-L65):

| Role String | Code Authority Limit (USD) | Enforced Location | Rejection Message if Exceeded |
| :--- | :---: | :--- | :--- |
| `OPERATOR` | **$0.00** | `security.py:72` | *"Operators cannot approve repairs (Maker-Checker policy violation)."* |
| `OPERATIONS_APPROVER` | **$250,000.00** | `security.py:84` | *"Approval limit exceeded: Transaction amount exceeds OPERATIONS_APPROVER maximum authorized limit ($250,000.00)."* |
| `COMPLIANCE_APPROVER` | **$5,000,000.00** | `security.py:84` | *"Approval limit exceeded: Transaction amount exceeds COMPLIANCE_APPROVER limit ($5,000,000.00)."* |
| `RISK_APPROVER` | **$10,000,000.00** | `security.py:84` | Standard limit evaluation; transactions > $10M require Board/Executive escalation. |
| `ADMIN` | **$10,000,000.00** | `security.py:84` | Administrative override limit. |

Enforcement occurs **server-side** inside `check_can_approve()` during every approval invocation in [`approval_engine.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/approval_engine.py). It is not merely a UI button disablement.

---

## 7. Per-Bank Configurability vs. Code Changes

### What is Configurable Today Without Code Changes
- Dynamic policy rules (via `/api/rules/submit` REST API or UI Rule Studio).
- STP monetary thresholds (via rule conditions).
- Dual-authorization trigger amounts (via rule actions or `DUAL_AUTH_THRESHOLD` environment variable).
- File watcher directories and poll intervals (via environment variables).

### What Requires Code Changes Today
- **Adding New Roles**: `UserRole` is a hardcoded Python `Enum` in [`approval.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/schemas/approval.py). Adding a new bank-specific role (e.g. `TREASURY_ANALYST`) requires updating Python enum files.
- **Tenant Isolation**: There is no tenant ID in database models; multi-bank deployment requires schema changes.
- **Connecting Real Bank Directories**: Mapping to a bank's real Core Banking or Sanctions APIs requires writing new Python classes implementing the abstract ports in [`backend/app/ports/`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/ports/).
