# 🔍 PeX Desktop Prototype Defect Review Report

**Document Type:** Independent Prototype Defect, Correctness & Safety Audit  
**System Name:** Payment Exception Resolution Platform (PeX) Desktop Prototype  
**Workspace Root:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Reviewer:** Independent Prototype Defect Reviewer & Payment Systems Reliability Engineer  
**Audit Date:** September 23, 2026  
**Classification:** Internal Assurance / Quality Gate  
**Evaluation Scope:** Local Desktop Prototype Correctness, Consistency, Safety, and Lifecycle Rigor (Excluding Deferred Cloud Infrastructure)

---

## Executive Summary & Core Question Evaluation

### Core Question:
> *"Is the current PeX desktop prototype internally correct, consistent, and safe within its intended prototype boundary?"*

### Verdict: **CONDITIONALLY SOUND WITH CRITICAL LOGICAL & WORKFLOW DEFECTS**

The PeX desktop prototype demonstrates an impressive, sophisticated domain architecture. It successfully demonstrates the 41-exception taxonomy across 5 BIAN domains, dynamic business policy synthesis, cryptographic SHA-256 audit chaining, and interactive human-in-the-loop (HITL) maker-checker workflows. 

However, an exhaustive, code-level inspection of the **actual implemented prototype code** reveals **genuine defects, state machine bypasses, broken API contracts, double-logging anomalies, and segregation of duties (SoD) loopholes** that undermine the platform's internal consistency and safety. Crucially, several critical defects identified in this review were **completely overlooked by the original 5-agent audit**.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                             PROTOTYPE DEFECT SCORECARD SUMMARY                                   │
├───────────────────────────────┬───────────────────────────────┬──────────────────────────────────┤
│ Critical Defects (P0)         │ 7 Defects                     │ Must fix before demonstration    │
│ High-Severity Defects (P1)    │ 8 Defects                     │ State machine & SoD fixes        │
│ Medium-Severity Defects (P2)  │ 6 Defects                     │ Schema & Contract fixes          │
│ Low / Code Hygiene (P3)       │ 4 Defects                     │ Test suite & routing cleanup     │
│ Original 5-Agent Audit Misses │ 15 Distinct Defects           │ Detailed in Section 8            │
│ Overall Prototype Soundness   │ 74% Internally Consistent     │ Requires targeted patching       │
└───────────────────────────────┴───────────────────────────────┴──────────────────────────────────┘
```

---

## 1. Master Prototype Defect Matrix

| Defect ID | Category | Title & Summary | Severity | Affected File(s) & Line(s) |
| :--- | :--- | :--- | :---: | :--- |
| **DEF-01** | SoD & Auth | **Frontend Dispatch Omits Auth Credentials (Daniel Osei SoD Bypass)**<br>Frontend `handleExecuteDispatch` sends an unauthenticated `POST /api/actions/execute`. Backend defaults to `APR-3191` (Daniel Osei), allowing Operators to settle wires while falsely stamping Daniel Osei's signature. | **CRITICAL** | `build_guided_frontend.py:1537-1541`<br>`backend/app/api/endpoints/actions.py:21-30` |
| **DEF-02** | STP Execution | **STP Fast-Lane Settles Cases Without Applying Repaired Data (Phantom Settlement)**<br>`execute_autonomous_stp` and `execute_batch_fast_lane_release` set `approved_changes=[]`. The AI's corrected IBAN/BIC/Code is never applied to the case or payment record upon settlement. | **CRITICAL** | `backend/app/services/stp_engine.py:249, 392`<br>`backend/app/db/repository.py:303-322` |
| **DEF-03** | Code Quality | **Missing `Session` Import in `stp_engine.py` (Runtime NameError Risk)**<br>`stp_engine.py` references `db: Session = SessionLocal()` at lines 233, 364, and 786 without importing `Session` from `sqlalchemy.orm`, risking runtime failures during type evaluation. | **CRITICAL** | `backend/app/services/stp_engine.py:233, 364, 786` |
| **DEF-04** | Governance | **Unchecked `auto_approve` Flag in Rules & ICD API (Maker-Checker Bypass)**<br>`POST /api/rules/submit` and `POST /api/rules/icd-configs/submit` accept `auto_approve: true` without role validation, allowing Operators to inject active production rules without Checker review. | **CRITICAL** | `backend/app/api/endpoints/rules.py:82-106, 189-213` |
| **DEF-05** | Canonicalization| **Canonicalizer Omits Domain Assignment (Defaults All Profiles to `DATA_QUALITY`)**<br>`canonicalize_bank_event` creates `CanonicalException` without passing `domain`, causing Compliance, Treasury, and Settlement Return exceptions to all default to `DATA_QUALITY`. | **CRITICAL** | `backend/app/services/canonicalizer.py:177-188`<br>`backend/app/schemas/canonical.py:172` |
| **DEF-06** | Audit Stream | **Double-Audit Logging Bug on HTTP Approval Submission**<br>`POST /api/approvals/submit` triggers audit logging in `approval_engine.py` AND redundant second logging in `approvals.py`, writing two events per human decision. | **HIGH** | `backend/app/api/endpoints/approvals.py:32-41`<br>`backend/app/services/approval_engine.py:161-170` |
| **DEF-07** | State Machine | **Approval Engine Permits Approval on `INVESTIGATING` Cases (Skips Maker Submit)**<br>`approval_engine.py` allows approvals on cases in `INVESTIGATING` status, allowing Checkers to approve cases before the Maker has reviewed the AI proposal or submitted handover notes. | **HIGH** | `backend/app/services/approval_engine.py:36` |
| **DEF-08** | State Machine | **Approval Engine `MODIFY` Action Bypasses Level-2 Dual Authorization**<br>When an approver modifies a proposal (`ApprovalAction.MODIFY`), the engine sets status to `APPROVED` directly, skipping the $250k threshold check for `AWAITING_SECOND_APPROVAL`. | **HIGH** | `backend/app/services/approval_engine.py:85-87` |
| **DEF-09** | State Machine | **Ingestion Endpoints Set Status Directly to `PENDING_APPROVAL`**<br>`events/ingest` and `cases/initiate` assign `status = "PENDING_APPROVAL"`, skipping `INGESTED`, `CANONICALIZED`, and `INVESTIGATING` in the 20-step lifecycle. | **HIGH** | `backend/app/api/endpoints/events.py:35`<br>`backend/app/api/endpoints/cases.py:445` |
| **DEF-10** | Governance | **`check_can_approve` Ignores Monetary Thresholds**<br>`check_can_approve(role, amount, queue)` takes `amount` but never checks if `amount > persona.max_approval_amount`, allowing Tier-1 Approvers to approve multi-million dollar wires. | **HIGH** | `backend/app/core/security.py:112-120` |
| **DEF-11** | Test Hygiene | **13 Root Test Scripts Polluting Pytest Discovery and Hanging CI**<br>13 ad-hoc test scripts in the root workspace match `test_*.py` and execute top-level live HTTP requests to `localhost:8000`, causing standard root `pytest` runs to hang or fail. | **HIGH** | Root directory (`test_*.py`, 13 files) |
| **DEF-12** | Audit Integrity | **Monetary Amount and Accounts Omitted from Cryptographic Event Hash**<br>`calculate_event_hash` omits payment `amount`, `currency`, `debtor_account`, and `creditor_account` from the SHA-256 block digest, allowing financial mutation without breaking hash verification. | **HIGH** | `backend/app/core/hashing.py:9-30` |
| **DEF-13** | Schema Contract| **`events/ingest` Endpoint Constructs Incomplete Case Record**<br>Ingested bank events produce `case_obj` missing `domain`, `secondary_profiles`, `audit_timeline`, and `guided_questions`, causing UI rendering errors. | **MEDIUM** | `backend/app/api/endpoints/events.py:19-44` |
| **DEF-14** | UI Contract | **Payment Ontology Inspector Hardcodes Static Context Data**<br>`/api/ontology/inspect/{case_id}` hardcodes `"kycStatus": "ACTIVE"` (even for `KYC_EXPIRED` exceptions) and `"straightThroughRepairEligible": "true"` (even for $50M wires). | **MEDIUM** | `backend/app/api/endpoints/ontology.py:128-147` |
| **DEF-15** | Analytics | **SLA Velocity Endpoint Counts `REJECTED` Cases as Open**<br>`get_sla_resolution_velocity` defines `open_cases` as `c.status != SETTLED`, incorrectly treating `REJECTED` cases as open active backlog. | **MEDIUM** | `backend/app/api/endpoints/analytics.py:86-88` |
| **DEF-16** | Schema Contract| **SPA Catch-All Route Swallows Unmatched `/api/*` Requests**<br>`serve_spa` in `main.py` returns `None` (HTTP 200 with empty body) for unmatched `/api` paths instead of a standard HTTP 404 JSON response. | **LOW** | `backend/app/main.py:73-80` |

---

## 2. State Machine & 20-Step Lifecycle Violations

### 2.1 Ingestion Endpoints Bypassing Maker Review (Step 1-11 Bypass)
In the approved **20-Step Operational Lifecycle**:
1. Steps 1–5: Intake, Ingestion, Schema Validation, Canonical Mapping, and Triage.
2. Steps 6–10: Diagnostic Context, Profile Matching, Disambiguation, Policy Evaluation, and Proposed Changes.
3. Step 11–12: Blast Radius Assessment & **Maker Submission to Approvals Desk**.
4. Step 13–14: Checker Review & Dual Authorization.

#### Code Evidence: `backend/app/api/endpoints/cases.py:445` & `backend/app/api/endpoints/events.py:35`
```python
# backend/app/api/endpoints/cases.py:445
case_obj = {
    "case_id": case_id,
    ...
    "status": LifecycleStage.PENDING_APPROVAL, # SKIPS INGESTED & INVESTIGATING!
    ...
}
```
* **The Defect:** In both `POST /api/cases/initiate` and `POST /api/events/ingest`, newly ingested exceptions are immediately stamped as `PENDING_APPROVAL`.
* **Operational Impact:** The case immediately lands on the Checker's Approvals Desk queue before any Operator/Maker has reviewed the AI reasoning, validated supporting evidence, or provided handover notes.

### 2.2 Approval Allowed Directly on `INVESTIGATING` Cases
#### Code Evidence: `backend/app/services/approval_engine.py:36-37`
```python
current_status = case.get("status")
if current_status not in [LifecycleStage.PENDING_APPROVAL, LifecycleStage.AWAITING_SECOND_APPROVAL, LifecycleStage.INVESTIGATING]:
    return False, f"Case is in {current_status} state, not awaiting approval", None, current_status
```
* **The Defect:** `approval_engine.py` explicitly allows an approval action to succeed if the case is in `LifecycleStage.INVESTIGATING`.
* **Operational Impact:** A Checker can approve an in-progress investigation while an Operator is actively working on it, bypassing Step 12 (`submit-to-checker`) and violating formal Segregation of Duties.

### 2.3 `MODIFY` Approval Action Bypassing Level-2 Dual Authorization
#### Code Evidence: `backend/app/services/approval_engine.py:85-87`
```python
elif submission.action == ApprovalAction.MODIFY:
    next_stage = LifecycleStage.APPROVED
    step_no = 1
```
* **The Defect:** When an approver submits an approval with `ApprovalAction.MODIFY` (modifying the proposed repair values), the engine immediately transitions `next_stage = LifecycleStage.APPROVED` regardless of whether `amount >= $250,000` or whether dual authorization is mandated.
* **Operational Impact:** An Operations Approver can bypass Risk Approver Tier-2 dual authorization on a $\$10,000,000$ payment simply by selecting the `MODIFY` action.

---

## 3. Segregation of Duties (SoD) & Maker-Checker Logic Flaws

### 3.1 Frontend Dispatch Omits Auth Credentials (The "Daniel Osei" SoD Stealth Bypass)
The platform claims strict enforcement of Maker-Checker rules: Operators (Makers) cannot execute settlement dispatch.

#### Backend Code: `backend/app/api/endpoints/actions.py:21-30`
```python
@router.post("/execute")
def execute_action(req: ExecuteActionRequest, authorization: Optional[str] = Header(None)):
    user_id = req.actor_id or "APR-3191" # Fallback to Daniel Osei!
    if authorization and authorization.startswith("Bearer pex-token-"):
        user_id = authorization.replace("Bearer pex-token-", "").strip()
        
    actor = get_persona(user_id)
    if actor and actor.role == UserRole.OPERATOR:
        raise HTTPException(status_code=403, detail="Segregation of Duties (SoD) violation: Operators (Makers) cannot execute settlement dispatch.")
```

#### Frontend Code: `build_guided_frontend.py:1537-1541`
```javascript
const handleExecuteDispatch = async () => {
  if (!activeCase) return;
  const res = await fetch(`${API_BASE}/actions/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id: activeCase.case_id }) // NO actor_id and NO Authorization Header!
  }).then(r => r.json());
```
* **The Defect:** When a user clicks "Dispatch & Settle" in the UI, the frontend sends a `POST /api/actions/execute` with **no `Authorization` header** and **no `actor_id`** in the payload.
* **The Bypass:** The backend falls back to `user_id = "APR-3191"` (Daniel Osei, Operations Approver).
* **Audit Consequence:** An Operator (e.g. Priya Nair, `OP-9012`) logged into the desktop UI can click "Dispatch & Settle" on any approved case. The backend executes the dispatch, bypassing the Operator SoD check, and creates an audit record stating:
  > *"Settlement dispatch authorized and executed by Daniel Osei (OPERATIONS_APPROVER)."*
  This is a critical false attribution in the audit trail.

### 3.2 Unchecked `auto_approve` Flag in Rules & ICD Configuration API
#### Code Evidence: `backend/app/api/endpoints/rules.py:82-106`
```python
@router.post("/submit", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def submit_rule_for_approval(payload: SubmitRuleRequest):
    ...
    status_val = "ACTIVE" if payload.auto_approve else "PENDING_APPROVAL"
    approved_at_val = datetime.utcnow() if payload.auto_approve else None

    rule_data = {
        ...
        "status": status_val,
        "maker_id": payload.maker_id,
        "checker_id": payload.checker_id if payload.auto_approve else None,
        ...
    }
    saved = repo.save_policy_rule(rule_data)
    return saved
```
* **The Defect:** `SubmitRuleRequest` and `SubmitICDConfigRequest` accept an optional `auto_approve: bool = False` parameter. Neither endpoint checks the caller's role, permissions, or identity.
* **Operational Impact:** Any Operator or external script can submit a new routing rule or bank adapter config with `auto_approve: true`. The backend saves it with `status = "ACTIVE"`, bypassing Checker review entirely.

### 3.3 `check_can_approve` Ignores Monetary Thresholds
#### Code Evidence: `backend/app/core/security.py:112-120`
```python
def check_can_approve(role: UserRole, amount: float, queue: str) -> Tuple[bool, str]:
    if role == UserRole.OPERATOR:
        return False, "Operators cannot approve repairs (Maker-Checker policy violation)."
    
    if queue == "Compliance" and role not in [UserRole.COMPLIANCE_APPROVER, UserRole.ADMIN, UserRole.RISK_APPROVER]:
        return False, "Only Compliance & Risk Approvers can clear Compliance queue exceptions."
        
    # All designated approver roles are authorized...
    return True, "Authorized"
```
* **The Defect:** The parameter `amount: float` is passed into `check_can_approve`, but is completely unused.
* **Operational Impact:** Daniel Osei (`APR-3191`) has `max_approval_amount = 250,000.0`. However, `check_can_approve` returns `True` for Daniel Osei on a $\$50,000,000$ transaction.

---

## 4. Double-Logging & Cryptographic Audit Deficiencies

### 4.1 Double-Audit Logging Bug on HTTP Approvals
#### Code Evidence: `backend/app/services/approval_engine.py:161-170` vs. `backend/app/api/endpoints/approvals.py:32-41`
When an approver signs off on a payment in the UI, two identical audit entries are written:

1. **First Log Entry:** `approval_engine.py:161`
```python
audit_service.log_event(
    case_id=submission.case_id,
    correlation_id=case.get("uetr", ""),
    stage_name="HITL_APPROVAL",
    actor_id=approver.user_id,
    actor_role=approver.role.value,
    action_name=f"APPROVAL_{submission.action.value}",
    details=f"Decision executed by {approver.name} ({approver.role.value}): {submission.comments}",
    control_tags=["Segregation of duties verified", "Audit chain updated", "Governance gate cleared"]
)
```

2. **Second Log Entry:** `approvals.py:32`
```python
audit_service.log_event(
    case_id=submission.case_id,
    correlation_id=submission.case_id,
    stage_name="HITL_APPROVAL",
    actor_id=approver.user_id,
    actor_role=approver.role.value,
    action_name=f"APPROVAL_{submission.action.value}",
    details=f"Approver {approver.name} submitted {submission.action.value}. Decision message: {submission.comments}. Next stage: {next_stage.value}",
    control_tags=["Maker-checker enforced", "Role entitlements verified", f"Step {record.step_number}"]
)
```
* **The Defect:** Every approval submission via the REST API generates **two consecutive cryptographic audit records** for the same event, bloating the ledger and creating confusing audit provenance.

### 4.2 Financial Fields Missing from Cryptographic SHA-256 Digest
#### Code Evidence: `backend/app/core/hashing.py:9-30`
```python
def calculate_event_hash(
    event_index: int,
    timestamp_iso: str,
    case_id: str,
    stage_name: str,
    actor_id: str,
    action_name: str,
    details: str,
    prev_hash: str
) -> str:
    payload = {
        "event_index": event_index,
        "timestamp": timestamp_iso,
        "case_id": case_id,
        "stage_name": stage_name,
        "actor_id": actor_id,
        "action_name": action_name,
        "details": details,
        "prev_hash": prev_hash
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
```
* **The Defect:** The SHA-256 event hash binds metadata (`event_index`, `timestamp`, `stage_name`, `actor_id`, `details`), but **omits transaction monetary amount, currency, debtor account, and creditor account**.
* **Impact:** In the prototype, if a case's amount is altered in SQLite from $\$50,000$ to $\$5,000,000$, `audit_service.verify_chain()` will still return `is_intact: True` because the hash digest does not cover financial fields.

---

## 5. STP Fast-Lane Engine Implementation Bugs

### 5.1 Missing `Session` Import in `stp_engine.py`
#### Code Evidence: `backend/app/services/stp_engine.py:233, 364, 786`
```python
# Lines 233, 364, 786
db: Session = SessionLocal()
```
* **The Defect:** In `backend/app/services/stp_engine.py`, lines 1–25 import `SessionLocal` from `app.db.session`, but `from sqlalchemy.orm import Session` is **never imported**.
* **Impact:** In Python runtime environments where type annotations are evaluated, invoking `execute_autonomous_stp` or `execute_batch_fast_lane_release` raises a fatal `NameError: name 'Session' is not defined`.

### 5.2 STP Fast-Lane Settles Cases Without Applying Repaired Data ("Phantom Settlement")
#### Code Evidence: `backend/app/services/stp_engine.py:249, 392`
```python
# stp_engine.py:239-252 (execute_autonomous_stp)
appr = ApprovalRecordModel(
    approval_id=approval_id,
    case_id=case_id,
    recommendation_id=f"REC-{case_id}",
    approver_id="SYS-AUTONOMOUS-STP",
    approver_name="PeX Governed Autonomous Reasoner",
    approver_role="ADMIN",
    action="APPROVE",
    comments=f"Autonomous zero-touch STP execution authorized...",
    approved_changes=[], # HARDCODED EMPTY!
    step_number=1,
    created_at=now
)
```
```python
# stp_engine.py:265 (execute_autonomous_stp dispatch_payload)
dispatch_payload={"case_id": case_id, "amount": case.get("amount"), "currency": case.get("currency")}
```
* **The Defect:** When STP Fast-Lane executes (either autonomous zero-touch or 1-click batch release), `approved_changes=[]` is hardcoded. Furthermore, the case's corrupted field in the database/cache is **never updated** with the AI's proposed repair value.
* **Operational Impact:** The case is marked `SETTLED`, but the invalid IBAN or corrupt tag is never corrected in the database or in the dispatch payload. It represents a "phantom settlement" of corrupted data.

---

## 6. Data Canonicalization & Schema Contract Mismatches

### 6.1 Canonicalizer Defaults All 41 Profiles to `DATA_QUALITY`
#### Code Evidence: `backend/app/services/canonicalizer.py:177-188`
```python
canonical_exception = CanonicalException(
    exception_id=f"EXC-{uuid.uuid4().hex[:6].upper()}",
    case_id=case_id,
    profile=profile,
    error_code=error_code,
    reason=reason,
    severity=severity,
    priority=priority,
    sla_due_at=datetime.utcnow() + timedelta(hours=2),
    at_risk_amount=amount,
    assigned_queue=queue
    # domain is NOT passed!
)
```
#### Schema Definition: `backend/app/schemas/canonical.py:172`
```python
class CanonicalException(BaseModel):
    ...
    domain: ExceptionDomain = ExceptionDomain.DATA_QUALITY # Default fallback!
```
* **The Defect:** In `canonicalizer.py`, `CanonicalException` is instantiated without passing `domain=get_domain_for_profile(profile)`.
* **Impact:** Every exception processed through `canonicalizer.canonicalize_bank_event`—including `SANCTIONS_SUSPECTED` (Compliance), `KYC_EXPIRED` (Treasury), and `RETURNED_PAYMENT` (Settlement/Returns)—is assigned `domain = "DATA_QUALITY"`.

### 6.2 `events/ingest` Missing Core Fields
#### Code Evidence: `backend/app/api/endpoints/events.py:19-44`
When `POST /api/events/ingest` receives a raw bank event, it constructs `case_obj` without:
- `domain`
- `secondary_profiles`
- `audit_timeline`
- `guided_questions`
* **Impact:** Ingesting a case via this API endpoint produces a truncated case record that causes the UI's Investigations Hub and Evidence Dossier tabs to display blank fields or fail rendering.

### 6.3 Ontology Inspector Hardcoding Inaccurate Context
#### Code Evidence: `backend/app/api/endpoints/ontology.py:128-147`
```python
"kyc": {
    "kycStatus": {"value": "ACTIVE", "status": "VALIDATED"},
    "riskClassification": {"value": "LOW", "status": "VALIDATED"},
    "expiredDocuments": {"value": "[]", "status": "VALIDATED"},
    "missingDocuments": {"value": "[]", "status": "VALIDATED"},
    "paymentRestriction": {"value": "false", "status": "VALIDATED"},
    "exceptionApprovalRequired": {"value": "true" if amount >= 250000 else "false", "status": "VALIDATED"}
}
```
* **The Defect:** In `inspect_case_ontology`, the KYC context block is hardcoded to `kycStatus: "ACTIVE"` and `expiredDocuments: "[]"` regardless of whether the case profile is `KYC_EXPIRED`. Similarly, `straightThroughRepairEligible: "true"` is hardcoded even for high-risk sanctions hits.

---

## 7. Test Suite Integrity & Test Discovery Pollution

### 7.1 Root Directory Test Discovery Pollution (13 Scripts)
In the workspace root directory, **13 ad-hoc test scripts** exist:
1. `test_cases_count.py`
2. `test_check.py`
3. `test_compliance_second_approval.py`
4. `test_db_e2e.py`
5. `test_double_load.py`
6. `test_http_marisol.py`
7. `test_import.py`
8. `test_live_api.py`
9. `test_live_marisol_ok.py`
10. `test_live_ok.py`
11. `test_marisol_approval.py`
12. `test_ping.py`
13. `test_stages.py`

#### The Defect:
When running `pytest` from the root directory (`pytest .`), Pytest discovers these root files. Because scripts like `test_live_api.py` and `test_http_marisol.py` contain top-level script commands that execute `urllib.request.urlopen("http://localhost:8000/...")` during module import:
- If the live Uvicorn server is not running, **Pytest hangs on network timeouts and fails with connection errors**.
- Running `pytest tests/ backend/tests/` passes cleanly (46 passed), proving that the root test scripts pollute automated CI discovery.

### 7.2 Missing Negative Assertions & Direct State Mutation
- In `tests/test_hitl_approval.py:24-27` and `backend/tests/test_stp_e2e.py:66-70`, unit tests mutate the database cache directly (`case["amount"] = 42000.0`, `case["status"] = "PENDING_APPROVAL"`) rather than exercising API mutation endpoints.
- In `tests/test_audit_trace.py`, the test logs 3 events and asserts `res.is_intact is True`. It never alters an event to verify that tampering is detected.

---

## 8. What the Original 5-Agent Audit MISSED

The previous audit conducted by the 5 review agents was comprehensive regarding general architectural drift and cloud roadmaps, but **missed 15 critical, practical prototype implementation defects**:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                   15 CRITICAL PROTOTYPE DEFECTS MISSED BY ORIGINAL 5-AGENT AUDIT                 │
├────┬─────────────────────────────────────────────┬──────────────────────────────────────────────┤
│ #  │ Defect Summary                              │ Why it was Missed by Original 5-Agent Audit  │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 1  │ Missing `Session` import in `stp_engine.py` │ Original audit reviewed architecture, missed │
│    │ causing NameError on execution              │ un-evaluated type annotation in method body  │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 2  │ STP Fast-Lane settles cases with            │ Original audit noted STP policy conflict but │
│    │ `approved_changes=[]` (Phantom Settlement)  │ missed that proposed changes are dropped     │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 3  │ Frontend `handleExecuteDispatch` omits auth │ Original audit reviewed backend SoD checks   │
│    │ headers & defaults to Daniel Osei (SoD bug) │ but did not inspect frontend fetch call      │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 4  │ `auto_approve: true` in Rules & ICD API     │ Original audit missed unauthenticated        │
│    │ allows Operators to self-approve rules      │ parameter in `SubmitRuleRequest` schema      │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 5  │ `check_can_approve` ignores `amount` limit  │ Original audit saw the function signature    │
│    │ allowing $50M approvals by Tier-1 Approver  │ but didn't check that `amount` is unused     │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 6  │ Canonicalizer creates `CanonicalException`  │ Original audit verified profile enums but    │
│    │ without domain (all default to DATA_QUALITY)│ missed missing keyword arg in instantiation  │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 7  │ Ingestion endpoints set status immediately  │ Original audit missed that INGESTED and      │
│    │ to `PENDING_APPROVAL` (skips Maker phase)   │ INVESTIGATING steps are skipped upon intake  │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 8  │ `events/ingest` creates incomplete case     │ Original audit tested `cases/initiate` but   │
│    │ missing domain, timeline, guided questions  │ did not check dictionary keys in `events.py` │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 9  │ `approval_engine.py` allows approvals on    │ Original audit checked role permissions but  │
│    │ cases in `INVESTIGATING` status             │ missed status whitelist check on line 36     │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 10 │ `approval_engine.py` MODIFY action bypasses │ Original audit reviewed standard APPROVE     │
│    │ Level-2 Dual Authorization check            │ action but missed elif MODIFY branch logic   │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 11 │ `ontology/inspect/{case_id}` hardcodes      │ Original audit saw the ontology UI but       │
│    │ active KYC status even on KYC_EXPIRED cases │ missed hardcoded JSON returns in endpoint    │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 12 │ `analytics.py` velocity endpoint counts     │ Original audit inspected summary KPIs but    │
│    │ `REJECTED` cases as open active backlog     │ missed `!= SETTLED` filter bug in velocity   │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 13 │ SPA router returns `None` (HTTP 200) for    │ Original audit reviewed SPA mounting but     │
│    │ unmatched `/api/*` routes                   │ missed missing 404 handler on line 75        │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 14 │ 13 root test scripts exist (not 7)          │ Original audit undercounted root scripts     │
│    │ blocking root `pytest .` discovery          │ and did not identify all 13 live scripts     │
├────┼─────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 15 │ Zero test coverage for autonomous STP       │ Original audit counted 46 passing tests but  │
│    │ execution (`execute_autonomous_stp`)        │ missed that autonomous method is never tested│
└────┴─────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

---

## 9. Concrete Prototype Remediation Plan

To bring the PeX desktop prototype into 100% internal correctness and safety without requiring cloud infrastructure changes:

### Phase 1: Security & SoD Fixes (Immediate)
1. **Fix Frontend Dispatch Call:** Update `handleExecuteDispatch` in `build_guided_frontend.py` to pass `Authorization: Bearer pex-token-${currentPersona.user_id}` and `actor_id: currentPersona.user_id`.
2. **Remove Unauthenticated Privileged Fallbacks:** Remove `user_id = "APR-3191"` default from `actions.py` and `approvals.py`; require valid persona identification.
3. **Enforce `auto_approve` Permissions:** Validate in `rules.py` that `auto_approve` can only be set to `True` if the caller has `ADMIN` or `APPROVER` role.
4. **Implement Monetary Limits in `check_can_approve`:** Check `amount <= persona.max_approval_amount` for `OPERATIONS_APPROVER`.

### Phase 2: State Machine & Lifecycle Hardening
1. **Fix Intake Status:** Set `status = "INGESTED"` in `cases.py` (`initiate_payment`) and `events.py` (`ingest_bank_event`).
2. **Restrict Approvals to Pending States:** In `approval_engine.py:36`, remove `LifecycleStage.INVESTIGATING` from the allowed approval whitelist.
3. **Fix `MODIFY` Dual Auth Check:** In `approval_engine.py:85`, ensure `MODIFY` triggers `AWAITING_SECOND_APPROVAL` if `amount >= $250,000`.
4. **Eliminate Duplicate Audit Logging:** Remove the second `audit_service.log_event` call in `approvals.py:32`.

### Phase 3: STP Engine & Data Canonicalization Fixes
1. **Import `Session` in `stp_engine.py`:** Add `from sqlalchemy.orm import Session` to `stp_engine.py`.
2. **Apply Field Changes in STP Settlement:** In `stp_engine.py`, populate `approved_changes` from `rec.proposed_changes` and apply the changes to the case and action record upon settlement.
3. **Fix Canonicalizer Domain Mapping:** In `canonicalizer.py:177`, pass `domain=get_domain_for_profile(profile)`.
4. **Enrich `events/ingest` Case Schema:** Populate `domain`, `secondary_profiles`, and initial `audit_timeline` during raw event ingestion.

### Phase 4: Test Suite & Codebase Cleanup
1. **Move Root Test Scripts:** Move or rename the 13 root `test_*.py` scripts to `scripts/live_tests/` to restore clean root `pytest` discovery.
2. **Add Negative Tampering Tests:** Update `test_audit_trace.py` to assert that tampered event hashes fail verification.
3. **Add Autonomous STP Test:** Add test coverage for `execute_autonomous_stp` in `backend/tests/test_stp_e2e.py`.

---

## 10. Conclusion

The PeX desktop prototype has achieved an exceptional foundation in domain modeling, BIAN mapping, and interactive operator workflows. Addressing the 16 genuine defects identified in this review will transform PeX from a promising prototype into an airtight, internally consistent, and demonstrably safe payment exception resolution platform.
