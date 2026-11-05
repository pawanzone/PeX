"""SQLAlchemy 2.0 ORM Models for PeX Enterprise Database."""
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    LargeBinary,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Index,
)
from app.db.base import Base

class UserModel(Base):
    """User directory & RBAC personas."""
    __tablename__ = "users"

    user_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(256), nullable=False, index=True)
    role = Column(String(64), nullable=False, index=True)  # OPERATOR, OPERATIONS_APPROVER, COMPLIANCE_APPROVER, RISK_APPROVER, ADMIN
    title = Column(String(128), nullable=False)
    department = Column(String(128), nullable=False)
    avatar_initials = Column(String(8), nullable=False, default="PX")
    badge_color = Column(String(32), nullable=False, default="blue")
    max_approval_amount = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RolePermissionModel(Base):
    """Fine-grained permission scopes for RBAC."""
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(64), nullable=False, index=True)
    permission_scope = Column(String(128), nullable=False)
    description = Column(String(256), nullable=True)

class CaseModel(Base):
    """Canonical Payment Exception Cases across all 41 Market Profiles."""
    __tablename__ = "cases"

    case_id = Column(String(64), primary_key=True, index=True)
    payment_id = Column(String(64), nullable=False, index=True)
    uetr = Column(String(128), nullable=False, index=True)
    payment_ref = Column(String(128), nullable=False, index=True)
    profile = Column(String(64), nullable=False, index=True)
    domain = Column(String(64), nullable=False, index=True)
    secondary_profiles = Column(JSON, default=list)
    error_code = Column(String(64), nullable=False)
    reason = Column(Text, nullable=False)
    amount = Column(Float, nullable=False, index=True)
    currency = Column(String(8), nullable=False, index=True)
    payment_rail = Column(String(64), nullable=False)
    debtor_party = Column(JSON, nullable=False)
    debtor_account = Column(JSON, nullable=False)
    creditor_party = Column(JSON, nullable=False)
    creditor_account = Column(JSON, nullable=False)
    queue = Column(String(64), nullable=False, index=True)
    status = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False, index=True)
    priority = Column(String(32), nullable=False, index=True)
    sla_due_at = Column(String(64), nullable=False)
    dual_auth_required = Column(Boolean, default=False)
    ai_confidence = Column(Float, nullable=True)
    created_at = Column(String(64), nullable=False)
    settled_at = Column(String(64), nullable=True)
    approval_history = Column(JSON, default=list)
    audit_timeline = Column(JSON, default=list)
    guided_questions = Column(JSON, default=list)
    expedite_ping = Column(JSON, nullable=True)
    # P0.5: persisted control fields (previously lived only in the in-memory dict and were lost on restart)
    maker_id = Column(String(64), nullable=True, index=True)
    dispatch_status = Column(String(64), nullable=True, index=True)
    handed_off_at = Column(String(64), nullable=True)
    bank_ack_reference = Column(String(128), nullable=True)
    bank_clearing_system = Column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_cases_domain_status", "domain", "status"),
        Index("ix_cases_queue_status", "queue", "status"),
    )

class AuditEventModel(Base):
    """Immutable Continuous Cryptographic Provenance Ledger (SHA-256 Chaining)."""
    __tablename__ = "audit_events"

    event_index = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(64), nullable=False, index=True)
    correlation_id = Column(String(128), nullable=False, index=True)
    stage_name = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(64), nullable=False)
    actor_role = Column(String(64), nullable=False)
    action_name = Column(String(128), nullable=False)
    timestamp = Column(String(64), nullable=False)
    details = Column(Text, nullable=False)
    control_tags = Column(JSON, default=list)
    amount = Column(Float, nullable=True)
    currency = Column(String(8), nullable=True)
    debtor_account = Column(String(64), nullable=True)
    creditor_account = Column(String(64), nullable=True)
    prev_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False, index=True)

class TokenVaultModel(Base):
    """Zero-trust Tokenization Vault & PII Surrogate Mapping."""
    __tablename__ = "token_vault_mappings"

    raw_hash = Column(String(64), primary_key=True, index=True)
    raw_value = Column(String(256), nullable=False)
    token_value = Column(String(64), nullable=False, unique=True, index=True)
    token_type = Column(String(32), nullable=False, default="PARTY")  # PARTY, IBAN, ACC, PAN
    created_at = Column(DateTime, default=datetime.utcnow)

class RecommendationModel(Base):
    """AI Guided Decisions & Evidentiary Grounding Contracts."""
    __tablename__ = "recommendations"

    recommendation_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), nullable=False, index=True)
    action_type = Column(String(64), nullable=False)
    confidence_score = Column(Float, nullable=False)
    rationale = Column(Text, nullable=False)
    proposed_changes = Column(JSON, default=list)
    corroborating_evidence = Column(JSON, default=list)
    risk_evaluation = Column(JSON, nullable=False)
    guided_questions = Column(JSON, default=list)
    step_by_step_assessment = Column(JSON, default=list)
    hypothesis_ranking = Column(JSON, default=list)
    anomaly_guardrails = Column(JSON, default=list)
    consequence_simulation = Column(JSON, nullable=True)
    applied_policies = Column(JSON, default=list)
    ambiguity_detected = Column(Boolean, default=False)
    ambiguity_message = Column(Text, nullable=True)
    model_identifier = Column(String(64), default="mock-governed-reasoner-v1")
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    generated_at = Column(DateTime, default=datetime.utcnow)

class ApprovalRecordModel(Base):
    """Role-gated Maker-Checker and Dual Authorization Signatures."""
    __tablename__ = "approval_records"

    approval_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), nullable=False, index=True)
    recommendation_id = Column(String(64), nullable=False)
    approver_id = Column(String(64), nullable=False, index=True)
    approver_name = Column(String(128), nullable=False)
    approver_role = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    comments = Column(Text, nullable=False)
    approved_changes = Column(JSON, default=list)
    step_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

class GovernedActionModel(Base):
    """Idempotent Outbound Wire & Settlement Contracts."""
    __tablename__ = "governed_actions"

    action_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), nullable=False, index=True)
    approval_ids = Column(JSON, default=list)
    action_type = Column(String(64), nullable=False)
    target_system = Column(String(128), default="SIMULATED_BANK_PAYMENT_HUB")
    idempotency_key = Column(String(128), nullable=False, unique=True, index=True)
    dispatch_payload = Column(JSON, nullable=False)
    status = Column(String(32), default="PENDING")
    dispatched_at = Column(DateTime, nullable=True)
    settled_at = Column(DateTime, nullable=True)

class DeliveryReceiptModel(Base):
    """External Bank Settlement ACKs and Delivery Receipts."""
    __tablename__ = "delivery_receipts"

    receipt_id = Column(String(64), primary_key=True, index=True)
    action_id = Column(String(64), nullable=False, index=True)
    case_id = Column(String(64), nullable=False, index=True)
    bank_ack_reference = Column(String(128), nullable=False, unique=True, index=True)
    status = Column(String(64), default="SETTLED_CONFIRMED")
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON, default=dict)

class RawBankEventModel(Base):
    """Raw Ingested Bank Payloads (Bank A, Bank B, Bank C)."""
    __tablename__ = "raw_bank_events"

    event_id = Column(String(64), primary_key=True, index=True)
    source_bank_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    raw_payload = Column(JSON, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)

class PolicyRuleModel(Base):
    """Governed Business Policy Rules & Dynamic Thresholds (Maker-Checker Lifecycle)."""
    __tablename__ = "policy_rules"

    rule_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    natural_language_prompt = Column(Text, nullable=False)
    category = Column(String(64), nullable=False, default="APPROVAL_GATING") # APPROVAL_GATING, STP_FAST_LANE, ROUTING, SLA_URGENCY
    domain = Column(String(64), nullable=False, default="ALL")
    conditions = Column(JSON, nullable=False, default=dict)
    actions = Column(JSON, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="ACTIVE") # ACTIVE, PENDING_APPROVAL, DRAFT, REJECTED, RETIRED
    version = Column(String(16), default="1.0")
    impact_summary = Column(String(256), nullable=True)
    maker_id = Column(String(64), nullable=True)
    maker_name = Column(String(128), nullable=True)
    maker_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    checker_id = Column(String(64), nullable=True)
    checker_name = Column(String(128), nullable=True)
    checker_comments = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)

class ICDConfigurationModel(Base):
    """Governed External Bank & Clearing Node Integrations (ICD Adapter Registry)."""
    __tablename__ = "icd_configurations"

    icd_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    institution_name = Column(String(128), nullable=False)
    bic = Column(String(32), nullable=False, index=True)
    rail = Column(String(64), nullable=False, default="SWIFT_CBPR+") # FEDWIRE, SWIFT_CBPR+, TARGET2, CHAPS
    adapter_type = Column(String(64), nullable=False, default="DIRECTORY_LOOKUP") # DIRECTORY_LOOKUP, NOSTRO_ALM, SANCTIONS_GATEWAY, CORE_LEDGER
    endpoint_url = Column(String(256), nullable=False)
    latency_ms = Column(Integer, default=12)
    status = Column(String(32), nullable=False, default="ACTIVE") # ACTIVE, PENDING_APPROVAL, DRAFT, DISABLED
    config_payload = Column(JSON, default=dict)
    maker_id = Column(String(64), nullable=True)
    maker_name = Column(String(128), nullable=True)
    maker_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    checker_id = Column(String(64), nullable=True)
    checker_name = Column(String(128), nullable=True)
    checker_comments = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)



class BankOutcomeModel(Base):
    """Idempotency + evidence record for every inbound bank outcome signal."""
    __tablename__ = "bank_outcomes"

    idempotency_key = Column(String(160), primary_key=True)
    case_id = Column(String(64), nullable=False, index=True)
    outcome = Column(String(32), nullable=False)
    bank_reference = Column(String(128), nullable=False)
    clearing_system = Column(String(64), nullable=True)
    received_at = Column(String(64), nullable=False)
    signature_verified = Column(Boolean, default=False)


# ---------------------------------------------------------------------------------------------
# UI v2 extension tables (additive; nothing above is changed)
# ---------------------------------------------------------------------------------------------
class CaseExtModel(Base):
    """Per-case UI v2 working data (assignee, cutoff, evidence rows, handover note, request-info state...)."""
    __tablename__ = "v2_case_ext"

    case_id = Column(String(64), primary_key=True, index=True)
    data = Column(JSON, nullable=False, default=dict)
    updated_at = Column(String(64), nullable=True)


class V2SavedViewModel(Base):
    __tablename__ = "v2_saved_views"

    id = Column(String(32), primary_key=True)
    owner_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    filters = Column(JSON, nullable=False, default=dict)
    sort = Column(String(32), nullable=True)
    created_at = Column(String(64), nullable=False)


class V2NotificationModel(Base):
    __tablename__ = "v2_notifications"

    id = Column(String(32), primary_key=True)
    target_user_id = Column(String(64), nullable=True, index=True)
    target_role = Column(String(64), nullable=True, index=True)
    kind = Column(String(32), nullable=False)
    case_id = Column(String(64), nullable=True, index=True)
    title = Column(String(256), nullable=False)
    text = Column(Text, nullable=True)
    created_at = Column(String(64), nullable=False)
    read_by = Column(JSON, nullable=False, default=list)


class V2PolicyChangeModel(Base):
    """One proposed or applied change to a platform rule (Rules & Policy Studio). The ACTIVE row per key is the value in force."""
    __tablename__ = "v2_policy_changes"

    id = Column(String(32), primary_key=True)
    key = Column(String(64), nullable=False, index=True)
    value = Column(JSON, nullable=False)
    prev_value = Column(JSON, nullable=True)
    status = Column(String(16), nullable=False, index=True)        # PENDING | ACTIVE | SUPERSEDED | REJECTED | WITHDRAWN
    reason = Column(String(512), nullable=True)
    proposed_by = Column(String(64), nullable=False)
    proposed_at = Column(String(64), nullable=False)
    decided_by = Column(String(64), nullable=True)
    decided_at = Column(String(64), nullable=True)
    decision_note = Column(String(512), nullable=True)
    effective_from = Column(String(64), nullable=True)
    impact = Column(JSON, nullable=True)


class V2ModeChangeModel(Base):
    __tablename__ = "v2_mode_changes"

    id = Column(String(32), primary_key=True)
    integration_id = Column(String(64), nullable=False, index=True)
    from_mode = Column(String(16), nullable=False)
    to_mode = Column(String(16), nullable=False)
    reason = Column(Text, nullable=True)
    state = Column(String(32), nullable=False, default="PENDING_SECOND_ADMIN")
    requested_by = Column(String(64), nullable=False)
    requested_at = Column(String(64), nullable=False)
    decided_by = Column(String(64), nullable=True)
    decided_at = Column(String(64), nullable=True)


class V2IntegrationModel(Base):
    """Simulated integration registry (mode is the only mutable field and only via a two-admin change)."""
    __tablename__ = "v2_integrations"

    id = Column(String(64), primary_key=True)
    mode = Column(String(16), nullable=False, default="SHADOW")
    health = Column(String(16), nullable=False, default="healthy")
    health_note = Column(String(256), nullable=True)
    queue = Column(Integer, nullable=False, default=0)
    last_event_at = Column(String(64), nullable=True)


class V2IdempotencyModel(Base):
    __tablename__ = "v2_idempotency"

    key = Column(String(190), primary_key=True)
    response = Column(JSON, nullable=False, default=dict)
    created_at = Column(String(64), nullable=False)


class V2NetworkCaseModel(Base):
    """An investigation (camt.110/111) or recall (camt.056/029) exchanged with another bank, tied to a payment by UETR."""
    __tablename__ = "v2_network_cases"

    id = Column(String(32), primary_key=True)
    kind = Column(String(16), nullable=False, index=True)           # INVESTIGATION | RECALL
    direction = Column(String(8), nullable=False, index=True)       # INBOUND | OUTBOUND
    status = Column(String(24), nullable=False, index=True)
    uetr = Column(String(64), nullable=False, index=True)
    counterparty_bic = Column(String(16), nullable=False)
    case_ref = Column(String(64), nullable=True)                    # the case id the requester uses; echoed in our reply
    message_id = Column(String(64), nullable=True, index=True)
    response_message_id = Column(String(64), nullable=True, index=True)
    amount = Column(Float, nullable=True)
    currency = Column(String(3), nullable=True)
    reason_code = Column(String(8), nullable=True)
    narrative = Column(Text, nullable=True)
    created_at = Column(String(40), nullable=False)
    due_at = Column(String(40), nullable=True)
    closed_at = Column(String(40), nullable=True)
    request_xml = Column(Text, nullable=False)
    response_xml = Column(Text, nullable=True)
    response_outcome = Column(String(8), nullable=True)
    response_reason = Column(String(8), nullable=True)
    response_text = Column(Text, nullable=True)
    drafted_by = Column(String(64), nullable=True)
    approvals = Column(JSON, nullable=True)
    handoff = Column(JSON, nullable=True)
    timeline = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)
    linked_case_id = Column(String(64), nullable=True, index=True)


class V2AttachmentModel(Base):
    """A file a maker attaches to a case (for example the client's invoice). Kept with a SHA-256 fingerprint; every open is audited."""
    __tablename__ = "v2_attachments"

    id = Column(String(32), primary_key=True)
    case_id = Column(String(64), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    content_type = Column(String(80), nullable=False)
    size = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    data = Column(LargeBinary, nullable=False)
    uploaded_by = Column(String(32), nullable=False)
    uploaded_at = Column(String(40), nullable=False)
    linked = Column(Boolean, nullable=False, default=False)         # true once it is tied to a submitted handover note


class V2ShadowRowModel(Base):
    """What the bank's analyst actually did on one case, loaded for the shadow scorecard. One row per case; loading again replaces it."""
    __tablename__ = "v2_shadow_rows"

    case_id = Column(String(64), primary_key=True)
    action = Column(String(16), nullable=False)                    # FIXED | REJECTED | ESCALATED | RETURNED
    value = Column(String(1024), nullable=True)                    # the value the analyst applied (FIXED only)
    minutes = Column(Float, nullable=True)
    analyst_ref = Column(String(64), nullable=True)
    resolved_at = Column(String(64), nullable=True)
    loaded_by = Column(String(64), nullable=False)
    loaded_at = Column(String(64), nullable=False)
