# 09-audit-and-provenance.md — Audit Ledger and Cryptographic Provenance

**Document Status:** COMPLETE / EVIDENCE-AUDITED  
**Auditor Mode:** Objective External Review  
**Target Codebase:** `C:\Users\pawan\.gemini\antigravity\scratch\pex_platform`  
**Date of Audit:** October 2026  

---

## 1. Audit Event Schema and Event Capture

The audit event model is defined in [`backend/app/schemas/audit.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/schemas/audit.py#L6-L23) and persisted in [`backend/app/db/models.py:65-85`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/db/models.py#L65-L85) (`AuditEventModel`).

### Schema Fields Inventory

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `event_index` | `int` | Sequential global integer index (0-based, monotonically increasing). |
| `timestamp` | `datetime` | Timestamp of event capture (UTC). |
| `case_id` | `str` | Unique case identifier (e.g. `PEX-STAGE4-REC01-STP`). |
| `correlation_id` | `str` | Inbound payload hash or trace UUID linking related events. |
| `stage_name` | `str` | Lifecycle stage name (e.g. `INTAKE`, `CANONICALIZATION`, `AI_REASONING`, `HITL_APPROVAL`, `SETTLEMENT`). |
| `actor_id` | `str` | User persona ID (`OP-9012`, `APR-3191`) or system process (`SYSTEM_INBOUND_WATCHER`, `SYSTEM_STP`). |
| `actor_role` | `str` | Role string (`OPERATOR`, `OPERATIONS_APPROVER`, `SYSTEM`). |
| `action_name` | `str` | Action code (e.g. `CASE_INGESTED`, `MOD97_VERIFIED`, `REPAIR_AUTHORIZED`, `DISPATCH_EMITTED`). |
| `details` | `str` | Structured text narrative describing the event context. |
| `control_tags` | `List[str]` | Operational tags (e.g. `["Control: SR-01", "MOD-97 Pass", "Tier 1"]`). |
| `amount` | `Optional[float]` | Transaction amount at risk. |
| `currency` | `Optional[str]` | 3-letter ISO currency code. |
| `debtor_account` | `Optional[str]` | Masked or raw debtor account. |
| `creditor_account`| `Optional[str]` | Masked or raw creditor account. |
| `prev_hash` | `str` | SHA-256 digest of the immediately preceding audit event. |
| `current_hash` | `str` | SHA-256 digest of the current serialized event payload. |

### How Before/After Values, Policies and Models Are Captured
- **Structural Finding**: The `AuditEvent` schema **does not have discrete columns** for `before_value`, `after_value`, `policy_version`, `model_version`, or `reason_codes`.
- **Reality in Code**: These parameters are formatted into the text string `details` or appended as string tags in `control_tags`. For example:
  ```python
  details = f"Proposed repair field creditor_account.iban modified from '{orig}' to '{repaired}'. Reason: MOD-97 pass."
  control_tags = [f"Policy: {policy_id}", f"Model: {model_id}"]
  ```
- **Auditor Note**: To perform automated regulatory reporting or programmatic before/after diff analysis, an external consumer must parse string narratives rather than querying structured relational attributes.

---

## 2. Cryptographic SHA-256 Ledger vs. "Merkle" Claims

The project documentation repeatedly references a *"Tamper-Evident Merkle-Sealed Provenance Ledger"*. Forensic inspection of [`backend/app/core/hashing.py`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/core/hashing.py) reveals:

### Exact Hashing & Chaining Implementation
```python
# backend/app/core/hashing.py:10-38
def calculate_event_hash(
    event_index: int,
    timestamp_iso: str,
    case_id: str,
    stage_name: str,
    actor_id: str,
    action_name: str,
    details: str,
    prev_hash: str,
    amount: Optional[Union[float, int, str]] = None,
    currency: Optional[str] = None,
    debtor_account: Optional[str] = None,
    creditor_account: Optional[str] = None,
    extra_payload: Optional[Dict[str, Any]] = None
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
    # Deterministic canonical serialization
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
```

### Forensic Comparison: Marketing Claims vs. Code Reality

| Dimension | Documented Claim | Code Implementation Reality | Auditor Verdict |
| :--- | :--- | :--- | :--- |
| **Data Structure** | "Merkle DAG / Merkle Tree" | **Linear Singly-Linked Hash Chain** (`prev_hash` pointer). No tree nodes, no binary tree branching, no Merkle root. | **MARKETING OVERSTATEMENT** |
| **Tamper Detection**| "Tamper-evident verification" | [`verify_audit_chain`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/core/hashing.py#L40-L70) sequentially recalculates SHA-256 hashes and verifies link integrity. | **REAL / IMPLEMENTED** |
| **Cryptographic Sealing**| "Sealed ledger" | Records are stored as standard mutable SQLite rows (`audit_events` table). Any database admin can update rows and recompute hashes. | **PARTIAL** (No HSM or WORM storage) |
| **Digital Signatures** | "PKI-signed provenance" | Zero asymmetric cryptography (no RSA, ECDSA, or Ed25519 signatures). Zero X.509 certificates. | **NOT PRESENT** |
| **External Timestamping**| "RFC 3161 trusted timestamping" | Uses local server clock (`datetime.utcnow()`). | **NOT PRESENT** |

### Plain Statement of Implementation
The platform implements a **sequential SHA-256 hash pointer chain in SQLite**, structurally identical to a git commit chain or a blockchain transaction log. It detects accidental corruption or unauthorized insertions during sequential scans. However, the claim that it is a **"Merkle DAG"** or a **"cryptographically sealed ledger"** is factually inaccurate.

---

## 3. Narrative Generation, Clocks and Timezone Handling

### Free-Text Narratives vs. Code Generation
- Audit event narratives are generated via **templated string interpolation** in Python service classes:
  - Ingestion: [`file_watcher.py:561`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/file_watcher.py#L561): `f"Inbound exception record {e2e_input.exception_id} from {file_path.name} ingested..."`
  - Approval: [`approval_engine.py:80`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/approval_engine.py#L80): `f"Approver {approver_name} ({approver_role}) authorized repair..."`
  - Dispatch: [`action_executor.py:72`](file:///C:/Users/pawan/.gemini/antigravity/scratch/pex_platform/backend/app/services/action_executor.py#L72): `f"Governed action {action_type} successfully reconciled..."`
- Human actors can also append arbitrary free-text comments via the `comments` field during approval submissions.

### Clock Source and Timezone Handling
- **Clock Source**: The system reads the local host operating system clock.
- **Timezone**: Standardized on **UTC** across all services:
  - In newer services: `datetime.now(timezone.utc).isoformat()`
  - In legacy services: `datetime.utcnow().isoformat()`
- **Vulnerability**: There is no enforcement of monotonic clocks (`time.monotonic()`) or network time protocol (NTP) drift monitoring. If the host system clock rolls backward, subsequent audit event timestamps can precede earlier events in the hash chain.
