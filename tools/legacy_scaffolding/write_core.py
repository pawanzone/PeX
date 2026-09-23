import os

base_backend = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\backend\app"

files = {}

# 1. config.py
files["config.py"] = """\"\"\"PeX Enterprise Platform Configuration.\"\"\"
import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SYNTHETIC_DATA_DIR = BASE_DIR / "synthetic_data" / "PeX_POC_Synthetic_Data_v0.1"
if not SYNTHETIC_DATA_DIR.exists():
    SYNTHETIC_DATA_DIR = BASE_DIR / "synthetic_data"

class Settings(BaseModel):
    PROJECT_NAME: str = "PeX Enterprise Payment Exception Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Model Gateway Configuration
    MODEL_GATEWAY_MODE: str = os.getenv("PEX_MODEL_GATEWAY_MODE", "mock") # "mock", "gemini", "openai"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Governance & Dual Authorization Threshold
    DUAL_AUTH_THRESHOLD: float = 250000.0  # USD equivalent
    
    # Security
    JWT_SECRET: str = os.getenv("JWT_SECRET", "pex-enterprise-secret-key-2026-sha256")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Data Path
    DATA_DIR: Path = SYNTHETIC_DATA_DIR

settings = Settings()
"""

# 2. schemas/bank_events.py
files["schemas/bank_events.py"] = """\"\"\"Raw Bank Ingestion Event Schemas for Bank A, Bank B, and Bank C.\"\"\"
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class BankAEventPayload(BaseModel):
    payment_reference: str
    error_code: str
    error_message: str
    amount: float
    currency: str
    debtor_name: str
    debtor_account: str
    creditor_name: str
    creditor_iban: str
    creditor_bic: Optional[str] = None
    settlement_rail: str = "SWIFT_CBPR"
    timestamp: Optional[str] = None

class BankBEventHeader(BaseModel):
    msg_type: str = "MT103_NACK"
    source_channel: str = "KAFKA_LEGACY"
    trn: str

class BankBEventBody(BaseModel):
    amount: float
    ccy: str
    ordering_customer: str
    ordering_account: str
    beneficiary_customer: str
    beneficiary_iban: str
    failure_reason: str
    exception_code: str

class BankBEventPayload(BaseModel):
    header: BankBEventHeader
    body: BankBEventBody

class BankCEventPayload(BaseModel):
    message_id: str
    format: str = "ISO20022_WRAPPER"
    camt_code: str = "camt.056.001.08"
    uetr: str
    debtor: Dict[str, Any]
    creditor: Dict[str, Any]
    amount: Dict[str, Any]
    return_reason: Dict[str, Any]

class RawBankEvent(BaseModel):
    event_id: str = Field(..., description="Unique Bank Source Event ID")
    source_bank_id: str = Field(..., description="e.g. BANK_A, BANK_B, BANK_C, GLOBAL_ROUTING")
    event_type: str = Field(..., description="e.g. PAYMENT_EXCEPTION, SETTLEMENT_FAILURE, SANCTIONS_ALERT")
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload: Dict[str, Any]
"""

# 3. schemas/canonical.py
files["schemas/canonical.py"] = """\"\"\"Canonical ISO 20022 / SWIFT / BIAN Data Models for PeX.\"\"\"
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class LifecycleStage(str, Enum):
    INGESTED = "INGESTED"
    CANONICALIZED = "CANONICALIZED"
    INVESTIGATING = "INVESTIGATING"
    RECOMMENDED = "RECOMMENDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    AWAITING_SECOND_APPROVAL = "AWAITING_SECOND_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    DISPATCHED = "DISPATCHED"
    SETTLED = "SETTLED"
    FAILED = "FAILED"

class ExceptionProfile(str, Enum):
    INVALID_IBAN = "INVALID_IBAN"
    INVALID_BIC = "INVALID_BIC"
    DUPLICATE_PAYMENT = "DUPLICATE_PAYMENT"
    SANCTIONS_SUSPECTED = "SANCTIONS_SUSPECTED"
    KYC_EXPIRED = "KYC_EXPIRED"
    RETURNED_PAYMENT = "RETURNED_PAYMENT"
    GENERAL_EXCEPTION = "GENERAL_EXCEPTION"

class ExceptionSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ExceptionPriority(str, Enum):
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class CanonicalParty(BaseModel):
    party_id: str
    party_name: str
    party_type: str  # DEBTOR, CREDITOR, INTERMEDIARY, INSTRUCTING_AGENT
    country: str
    identifier_type: Optional[str] = "NAME"
    identifier_value: Optional[str] = None
    token_ref: Optional[str] = None

class CanonicalAccount(BaseModel):
    account_id: str
    account_number: Optional[str] = None
    iban: Optional[str] = None
    currency: str
    bank_bic: Optional[str] = None
    bank_name: Optional[str] = None
    token_ref: Optional[str] = None

class CanonicalPayment(BaseModel):
    payment_id: str
    uetr: str
    instruction_id: str
    end_to_end_id: Optional[str] = None
    amount: float
    currency: str
    payment_rail: str  # SWIFT, CBPR+, FEDWIRE, SEPA, TARGET2
    debtor_party: CanonicalParty
    debtor_account: CanonicalAccount
    creditor_party: CanonicalParty
    creditor_account: CanonicalAccount
    settlement_date: Optional[str] = None
    source_bank_id: str
    raw_source_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CanonicalException(BaseModel):
    exception_id: str
    case_id: str
    profile: ExceptionProfile
    error_code: str
    reason: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    severity: ExceptionSeverity = ExceptionSeverity.MEDIUM
    priority: ExceptionPriority = ExceptionPriority.NORMAL
    sla_due_at: datetime
    at_risk_amount: float
    assigned_queue: str = "Repair"  # Repair, Compliance, Investigation, Treasury

class CaseSummary(BaseModel):
    case_id: str
    payment_ref: str
    uetr: str
    profile: ExceptionProfile
    error_code: str
    reason: str
    amount: float
    currency: str
    counterparty: str
    queue: str
    status: LifecycleStage
    severity: ExceptionSeverity
    priority: ExceptionPriority
    sla_due_at: datetime
    dual_auth_required: bool = False
    ai_confidence: Optional[float] = None
    created_at: datetime
"""

# 4. schemas/context.py
files["schemas/context.py"] = """\"\"\"Tokenized Investigation Context & Evidence Schemas.\"\"\"
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.canonical import ExceptionProfile

class EvidenceItem(BaseModel):
    evidence_id: str
    evidence_type: str  # BENEFICIARY_PROFILE, ACCOUNT_DIRECTORY, HISTORICAL_CASE, POLICY_RULE, SCREENING_HIT, KYC_RECORD
    source_connector: str
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    provenance_id: str
    is_mandatory: bool = False
    data: Dict[str, Any]
    relevance_score: float = 1.0

class PolicyRule(BaseModel):
    policy_id: str
    profile: ExceptionProfile
    rule_code: str
    rule_description: str
    mandatory_evidence: List[str]
    auto_repair_eligible: bool
    max_amount_threshold: float
    required_confidence_threshold: float

class HistoricalPrecedent(BaseModel):
    precedent_case_id: str
    profile: ExceptionProfile
    similarity_score: float
    applied_action: str
    outcome: str
    rationale: str

class TokenizedParty(BaseModel):
    token_id: str
    party_role: str
    country: str

class TokenizedAccount(BaseModel):
    token_id: str
    currency: str
    masked_identifier: str
    bank_bic: Optional[str] = None

class TokenizedPaymentContext(BaseModel):
    payment_id: str
    uetr: str
    amount: float
    currency: str
    debtor_party: TokenizedParty
    debtor_account: TokenizedAccount
    creditor_party: TokenizedParty
    creditor_account: TokenizedAccount
    payment_rail: str

class TokenizedInvestigationContext(BaseModel):
    context_id: str
    case_id: str
    profile: ExceptionProfile
    tokenized_payment: TokenizedPaymentContext
    evidence_items: List[EvidenceItem]
    policies: List[PolicyRule]
    historical_cases: List[HistoricalPrecedent]
    screening_matches: List[Dict[str, Any]] = []
    kyc_summary: Optional[Dict[str, Any]] = None
    assembled_at: datetime = Field(default_factory=datetime.utcnow)
    token_usage_estimated: int = 0
"""

# 5. schemas/recommendation.py
files["schemas/recommendation.py"] = """\"\"\"AI Recommendation & Decision Contract Schemas.\"\"\"
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.canonical import ExceptionSeverity

class ActionType(str, Enum):
    REPAIR_IBAN = "REPAIR_IBAN"
    REPAIR_BIC = "REPAIR_BIC"
    ESCALATE = "ESCALATE"
    HOLD = "HOLD"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REQUEST_KYC = "REQUEST_KYC"
    REPAIR_AND_RESUBMIT = "REPAIR_AND_RESUBMIT"
    RETURN_PAYMENT = "RETURN_PAYMENT"
    REJECT = "REJECT"

class ProposedFieldChange(BaseModel):
    field_path: str  # e.g. creditor_account.iban
    original_value_masked: str  # e.g. GB82WEST12345698765432
    proposed_value_masked: str  # e.g. GB82WEST12345698765431
    raw_proposed_value: Optional[str] = None # Filled only post-detokenization in vault
    justification: str
    validation_status: str = "VALIDATED"  # MOD-97 check, Directory check

class CorroboratingEvidenceRef(BaseModel):
    evidence_id: str
    evidence_type: str
    citation: str

class RiskEvaluation(BaseModel):
    risk_level: ExceptionSeverity
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_factors: List[str]
    dual_auth_required: bool

class DecisionRecommendation(BaseModel):
    recommendation_id: str
    case_id: str
    action_type: ActionType
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    proposed_changes: List[ProposedFieldChange] = []
    corroborating_evidence: List[CorroboratingEvidenceRef] = []
    risk_evaluation: RiskEvaluation
    model_identifier: str = "mock-governed-reasoner-v1"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)
"""

# 6. schemas/approval.py
files["schemas/approval.py"] = """\"\"\"Role-Gated Human Approval Schemas & Contracts.\"\"\"
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.recommendation import ActionType, ProposedFieldChange

class UserRole(str, Enum):
    OPERATOR = "OPERATOR"
    OPERATIONS_APPROVER = "OPERATIONS_APPROVER"
    COMPLIANCE_APPROVER = "COMPLIANCE_APPROVER"
    RISK_APPROVER = "RISK_APPROVER"
    ADMIN = "ADMIN"

class ApprovalAction(str, Enum):
    APPROVE = "APPROVE"
    MODIFY = "MODIFY"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"

class ApprovalSubmission(BaseModel):
    case_id: str
    action: ApprovalAction
    comments: str
    override_changes: Optional[List[ProposedFieldChange]] = None

class ApprovalRecord(BaseModel):
    approval_id: str
    case_id: str
    recommendation_id: str
    approver_id: str
    approver_name: str
    approver_role: UserRole
    action: ApprovalAction
    comments: str
    approved_changes: List[ProposedFieldChange] = []
    step_number: int = 1  # 1 for Primary, 2 for Dual
    created_at: datetime = Field(default_factory=datetime.utcnow)
"""

# 7. schemas/action.py
files["schemas/action.py"] = """\"\"\"Governed Action Execution & Delivery Receipts.\"\"\"
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.recommendation import ActionType

class ActionStatus(str, Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    SETTLED = "SETTLED"
    FAILED = "FAILED"

class GovernedActionContract(BaseModel):
    action_id: str
    case_id: str
    approval_ids: list[str]
    action_type: ActionType
    target_system: str = "SIMULATED_BANK_PAYMENT_HUB"
    idempotency_key: str
    dispatch_payload: Dict[str, Any]
    status: ActionStatus = ActionStatus.PENDING
    dispatched_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None

class DeliveryReceipt(BaseModel):
    receipt_id: str
    action_id: str
    case_id: str
    bank_ack_reference: str
    status: str = "SETTLED_CONFIRMED"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any]
"""

# 8. schemas/audit.py
files["schemas/audit.py"] = """\"\"\"Cryptographic Provenance & Continuous Audit Schemas.\"\"\"
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class AuditEvent(BaseModel):
    event_index: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    case_id: str
    correlation_id: str
    stage_name: str  # e.g. INTAKE, CANONICALIZATION, TOKENIZATION, EVIDENCE_GATHERING, AI_REASONING, HITL_APPROVAL, ACTION_DISPATCH, SETTLEMENT
    actor_id: str
    actor_role: str
    action_name: str
    details: str
    control_tags: List[str] = []
    prev_hash: str
    current_hash: str

class ProvenanceChain(BaseModel):
    case_id: str
    chain_head_hash: str
    total_events: int
    is_valid: bool = True
    events: List[AuditEvent]

class HashVerificationResult(BaseModel):
    chain_head: str
    total_events_checked: int
    is_intact: bool
    verified_at: datetime = Field(default_factory=datetime.utcnow)
"""

# 9. schemas/auth.py
files["schemas/auth.py"] = """\"\"\"Authentication, Personas, and Session Schemas.\"\"\"
from typing import Optional, List
from pydantic import BaseModel
from app.schemas.approval import UserRole

class UserPersona(BaseModel):
    user_id: str
    name: str
    email: str
    role: UserRole
    title: str
    department: str
    avatar_initials: str
    badge_color: str
    max_approval_amount: float
    is_demo_active: bool = False

class LoginRequest(BaseModel):
    user_id: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPersona
"""

# 10. core/hashing.py
files["core/hashing.py"] = """\"\"\"Cryptographic SHA-256 Hash Chain Utility for Immutable Provenance.\"\"\"
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

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

def verify_audit_chain(events: List[Dict[str, Any]]) -> bool:
    if not events:
        return True
    
    for i, event in enumerate(events):
        expected_prev = GENESIS_HASH if i == 0 else events[i-1]["current_hash"]
        if event.get("prev_hash") != expected_prev:
            return False
        
        computed_hash = calculate_event_hash(
            event_index=event["event_index"],
            timestamp_iso=event["timestamp"] if isinstance(event["timestamp"], str) else event["timestamp"].isoformat(),
            case_id=event["case_id"],
            stage_name=event["stage_name"],
            actor_id=event["actor_id"],
            action_name=event["action_name"],
            details=event["details"],
            prev_hash=expected_prev
        )
        if event.get("current_hash") != computed_hash:
            return False
            
    return True
"""

# 11. core/tokenization.py
files["core/tokenization.py"] = """\"\"\"Tokenization Vault & PII Isolation Boundary.\"\"\"
import hashlib
from typing import Dict, Tuple, Optional

class TokenVault:
    \"\"\"
    Isolated Tokenization Vault.
    Maintains bidirectional pseudonym mapping.
    Zero-trust boundary: AI context receives ONLY TOK-* surrogates.
    \"\"\"
    def __init__(self):
        self._raw_to_token: Dict[str, str] = {}
        self._token_to_raw: Dict[str, str] = {}

    def preload_tokens(self, token_records: list[dict]):
        for row in token_records:
            raw = row.get("raw_value") or row.get("original_value", "")
            token = row.get("token_value") or row.get("token", "")
            if raw and token:
                self._raw_to_token[raw] = token
                self._token_to_raw[token] = raw

    def tokenize(self, raw_value: str, token_type: str = "PARTY") -> str:
        if not raw_value:
            return ""
        
        clean_raw = raw_value.strip().replace(" ", "").upper()
        if clean_raw in self._raw_to_token:
            return self._raw_to_token[clean_raw]
        
        # Deterministic token generation
        h = hashlib.sha256(clean_raw.encode("utf-8")).hexdigest()[:12].upper()
        token = f"TOK-{token_type}-{h}"
        self._raw_to_token[clean_raw] = token
        self._token_to_raw[token] = clean_raw
        return token

    def detokenize(self, token: str) -> Optional[str]:
        return self._token_to_raw.get(token)

    def mask_identifier(self, identifier: str) -> str:
        \"\"\"Helper for display masking e.g. GB82****765432.\"\"\"
        clean = identifier.strip().replace(" ", "")
        if len(clean) <= 6:
            return clean
        return f"{clean[:4]}****{clean[-4:]}"

# Singleton instance
token_vault = TokenVault()
"""

# 12. core/security.py
files["core/security.py"] = """\"\"\"RBAC Roles, Personas & Authorization Logic.\"\"\"
from typing import List, Dict, Optional
from app.schemas.approval import UserRole
from app.schemas.auth import UserPersona

DEMO_PERSONAS: Dict[str, UserPersona] = {
    "OP-8472": UserPersona(
        user_id="OP-8472",
        name="Amina Okafor",
        email="a.okafor@pexbank.internal",
        role=UserRole.OPERATOR,
        title="Payment Operations Analyst",
        department="Triage & Investigation",
        avatar_initials="AO",
        badge_color="blue",
        max_approval_amount=0.0,
        is_demo_active=True
    ),
    "OP-1001": UserPersona(
        user_id="OP-1001",
        name="Priya Nair",
        email="p.nair@pexbank.internal",
        role=UserRole.OPERATOR,
        title="Senior Payment Analyst",
        department="Payment Repair Operations",
        avatar_initials="PN",
        badge_color="blue",
        max_approval_amount=0.0
    ),
    "APR-3191": UserPersona(
        user_id="APR-3191",
        name="Daniel Osei",
        email="d.osei@pexbank.internal",
        role=UserRole.OPERATIONS_APPROVER,
        title="Operations Approval Officer",
        department="Payment Exceptions",
        avatar_initials="DO",
        badge_color="emerald",
        max_approval_amount=250000.0
    ),
    "CMP-5502": UserPersona(
        user_id="CMP-5502",
        name="Marisol Vega",
        email="m.vega@pexbank.internal",
        role=UserRole.COMPLIANCE_APPROVER,
        title="Sanctions & AML Officer",
        department="Financial Crime Compliance",
        avatar_initials="MV",
        badge_color="amber",
        max_approval_amount=1000000.0
    ),
    "RSK-7714": UserPersona(
        user_id="RSK-7714",
        name="Kenji Watanabe",
        email="k.watanabe@pexbank.internal",
        role=UserRole.RISK_APPROVER,
        title="Chief Risk Officer (Payments)",
        department="Enterprise Risk Management",
        avatar_initials="KW",
        badge_color="purple",
        max_approval_amount=10000000.0
    ),
    "ADM-0001": UserPersona(
        user_id="ADM-0001",
        name="Alex Whitfield",
        email="a.whitfield@pexbank.internal",
        role=UserRole.ADMIN,
        title="Platform Administrator",
        department="Platform Governance",
        avatar_initials="AW",
        badge_color="slate",
        max_approval_amount=10000000.0
    )
}

def get_persona(user_id: str) -> Optional[UserPersona]:
    return DEMO_PERSONAS.get(user_id)

def check_can_approve(role: UserRole, amount: float, queue: str) -> Tuple[bool, str]:
    if role == UserRole.OPERATOR:
        return False, "Operators cannot approve repairs (Maker-Checker policy violation)."
    
    if queue == "Compliance" and role not in [UserRole.COMPLIANCE_APPROVER, UserRole.ADMIN]:
        return False, "Only Compliance Approvers can clear Compliance queue exceptions."
        
    if amount >= 250000.0 and role not in [UserRole.RISK_APPROVER, UserRole.ADMIN, UserRole.OPERATIONS_APPROVER]:
        return False, "High value transactions (>= $250k) require dual authorization from Risk/Operations."
        
    return True, "Authorized"
"""

# Write all files
for rel_path, content in files.items():
    full_path = os.path.join(base_backend, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {rel_path}")

print("All schemas and core modules created successfully.")
