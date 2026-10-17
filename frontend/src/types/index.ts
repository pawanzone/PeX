/**
 * PeX Frontend TypeScript Contracts & Domain Models
 * Synchronized with authoritative backend Pydantic schemas (app/schemas/).
 */

export type UserRole =
  | "OPERATOR"
  | "OPERATIONS_APPROVER"
  | "COMPLIANCE_APPROVER"
  | "RISK_APPROVER"
  | "ADMIN";

export interface UserPersona {
  user_id: string;
  name: string;
  email: string;
  role: UserRole;
  title: string;
  department: string;
  avatar_initials: string;
  badge_color: string;
  max_approval_amount: number;
  is_demo_active?: boolean;
}

export type LifecycleStage =
  | "INGESTED"
  | "CANONICALIZED"
  | "VALIDATED"
  | "INVESTIGATING"
  | "RECOMMENDED"
  | "PENDING_APPROVAL"
  | "AWAITING_SECOND_APPROVAL"
  | "RETURNED_FOR_REWORK"
  | "APPROVED"
  | "REJECTED"
  | "ESCALATED"
  | "DISPATCHED"
  | "HANDED_TO_BANK"
  | "EXECUTED_CONFIRMED"
  | "SETTLED"
  | "FAILED"
  | "STATUS_UNKNOWN"
  | "SHADOW_RECORDED";

export type ExceptionDomain =
  | "DATA_QUALITY"
  | "PROCESSING"
  | "COMPLIANCE"
  | "CLIENT_TREASURY"
  | "SETTLEMENT_RETURNS";

export type ExceptionProfile =
  // Domain 1: Data Quality (9 Profiles)
  | "INVALID_IBAN"
  | "INVALID_BIC"
  | "MISSING_BENEFICIARY_DATA"
  | "MISSING_REMITTANCE_INFO"
  | "INVALID_ADDRESS_FORMAT"
  | "MISSING_PURPOSE_CODE"
  | "INVALID_ACCOUNT_NUMBER"
  | "INVALID_ROUTING_CODE"
  | "BENEFICIARY_NAME_MISMATCH"
  // Domain 2: Processing (9 Profiles)
  | "DUPLICATE_PAYMENT"
  | "ROUTING_FAILURE"
  | "ISO20022_VALIDATION_ERROR"
  | "CUTOFF_MISSED"
  | "CORRUPTED_MESSAGE_FORMAT"
  | "INTERMEDIARY_BANK_REJECTION"
  | "NETWORK_TIMEOUT"
  | "QUEUE_PROCESSING_FAILURE"
  | "PAYMENT_HELD_FOR_REPAIR"
  // Domain 3: Compliance (8 Profiles)
  | "SANCTIONS_SUSPECTED"
  | "AML_ALERT"
  | "PEP_MATCH"
  | "RESTRICTED_CORRIDOR"
  | "ADVERSE_MEDIA_MATCH"
  | "HIGH_RISK_JURISDICTION"
  | "REGULATORY_REPORTING_REQUIRED"
  | "CUSTOMER_WATCHLIST_MATCH"
  // Domain 4: Client / Treasury (8 Profiles)
  | "KYC_EXPIRED"
  | "INSUFFICIENT_FUNDS"
  | "NOSTRO_SHORTFALL"
  | "FX_RATE_UNAVAILABLE"
  | "AUTHORIZATION_MISSING"
  | "LIMIT_BREACH"
  | "LIQUIDITY_CONSTRAINT"
  | "CREDIT_EXPOSURE_BREACH"
  // Domain 5: Settlement / Returns (7 Profiles)
  | "RETURNED_PAYMENT"
  | "ACCOUNT_CLOSED"
  | "BENEFICIARY_ACCOUNT_FROZEN"
  | "RECONCILIATION_BREAK"
  | "SETTLEMENT_FAILURE"
  | "FUNDS_TRAPPED_AT_CORRESPONDENT"
  | "UNMATCHED_CREDIT"
  // Fallback
  | "GENERAL_EXCEPTION";

export interface CanonicalParty {
  party_id: string;
  party_name: string;
  party_type: string;
  country: string;
  token_ref?: string;
}

export interface CanonicalAccount {
  account_id: string;
  account_number?: string;
  iban?: string;
  currency: string;
  bank_bic?: string;
  token_ref?: string;
}

export interface ApprovalRecord {
  approval_id: string;
  case_id: string;
  recommendation_id: string;
  approver_id: string;
  approver_name: string;
  approver_role: UserRole;
  action: string;
  comments: string;
  approved_changes: ProposedFieldChange[];
  step_number: number;
  created_at: string;
}

export interface PeXCase {
  case_id: string;
  payment_id: string;
  uetr: string;
  payment_ref: string;
  profile: ExceptionProfile;
  domain?: ExceptionDomain;
  secondary_profiles?: ExceptionProfile[];
  error_code: string;
  reason: string;
  amount: number;
  currency: string;
  payment_rail: string;
  debtor_party: CanonicalParty;
  debtor_account: CanonicalAccount;
  creditor_party: CanonicalParty;
  creditor_account: CanonicalAccount;
  queue: string;
  status: LifecycleStage;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  priority: "NORMAL" | "HIGH" | "CRITICAL";
  sla_due_at: string;
  dual_auth_required: boolean;
  at_risk_amount?: number;
  ai_confidence?: number;
  created_at: string;
  approval_history?: ApprovalRecord[];
  audit_timeline?: Array<{
    step_index: number;
    timestamp: string;
    actor_name: string;
    actor_role: string;
    badge_color: string;
    action_title: string;
    icon: string;
    summary: string;
  }>;
  settled_at?: string;
  maker_id?: string;
  dispatch_status?: string;
  bank_ack_reference?: string;
}

export interface ProposedFieldChange {
  field_path: string;
  original_value_masked: string;
  proposed_value_masked: string;
  raw_proposed_value?: string;
  justification: string;
  validation_status: string;
}

export interface StepAssessmentItem {
  step_index: number;
  stage_name: string;
  assessment_summary: string;
  is_passed: boolean;
  confidence_delta: number;
}

export interface HypothesisRankingItem {
  hypothesis_id: string;
  title: string;
  confidence: number;
  status: string;
}

export interface GuidedQuestionItem {
  category: string;
  question: string;
  investigation_tip: string;
}

export interface AnomalyGuardrailItem {
  guardrail_name: string;
  status: "PASSED" | "FLAGGED" | "BLOCKED";
  message: string;
}

export interface ConsequenceSimulation {
  liquidity_impact_usd: number;
  counterparty_risk_score: number;
  regulatory_scrutiny_level: string;
  downstream_clearing_rail: string;
}

export interface DecisionRecommendation {
  recommendation_id: string;
  case_id: string;
  action_type: string;
  confidence_score: number;
  rationale: string;
  proposed_changes: ProposedFieldChange[];
  corroborating_evidence: Array<{
    evidence_id: string;
    evidence_type: string;
    citation: string;
  }>;
  risk_evaluation: {
    risk_level: string;
    risk_score: number;
    risk_factors: string[];
    dual_auth_required: boolean;
  };
  guided_questions?: GuidedQuestionItem[];
  step_by_step_assessment?: StepAssessmentItem[];
  hypothesis_ranking?: HypothesisRankingItem[];
  anomaly_guardrails?: AnomalyGuardrailItem[];
  consequence_simulation?: ConsequenceSimulation;
  applied_policies?: string[];
  ambiguity_detected?: boolean;
  ambiguity_message?: string;
  model_identifier: string;
  model_version?: string;
  prompt_version?: string;
  llm_status?: string;
  llm_disagreement?: boolean;
  prompt_tokens: number;
  completion_tokens: number;
  generated_at: string;
}

export interface AuditEvent {
  event_index: number;
  timestamp: string;
  case_id: string;
  correlation_id: string;
  stage_name: string;
  actor_id: string;
  actor_role: string;
  action_name: string;
  details: string;
  control_tags: string[];
  amount?: number;
  currency?: string;
  debtor_account?: string;
  creditor_account?: string;
  prev_hash: string;
  current_hash: string;
}

export interface PolicyRule {
  rule_id: string;
  name: string;
  natural_language_prompt: string;
  category: string;
  domain: ExceptionDomain;
  conditions: Record<string, any>;
  actions: Record<string, any>;
  priority: number;
  status: "ACTIVE" | "DRAFT" | "DISABLED" | "PENDING_CHECKER_APPROVAL";
  maker_id: string;
  maker_name: string;
  checker_id?: string;
  checker_name?: string;
  dual_auth_threshold?: number;
  created_at: string;
  updated_at: string;
}

export interface AnalyticsSummary {
  open_cases: number;
  total_cases: number;
  resolved_cases: number;
  at_risk_value: number;
  critical_value: number;
  resolution_rate: number;
  due_under_1hr: number;
  queue_distribution: Record<string, number>;
  processing_date: string;
  telemetry_status: string;
  measured?: boolean;
}

export type OperationMode = "SHADOW" | "ASSISTED" | "LIVE";

export interface SystemInfo {
  version: string;
  operation_mode: OperationMode;
  bank_comm: string;
  demo: boolean;
  llm: { enabled: boolean; model?: string; reachable?: boolean | null };
}

export interface CasePage {
  items: PeXCase[];
  total: number;
  limit: number;
  offset: number;
}

export interface SummaryCounts {
  total: number;
  by_status: Record<string, number>;
  by_queue: Record<string, number>;
  by_profile: Record<string, number>;
  by_rail: Record<string, number>;
  actionable_repair: number;
  pending_approvals_all: number;
}

export type BatchStatus = "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface BatchRecord {
  batch_id: string;
  filename?: string;
  status: BatchStatus;
  total: number;
  processed: number;
  failed: number;
  duplicates: number;
  started_at?: string;
  finished_at?: string;
  records_per_sec?: number;
  summary?: {
    stp_eligible?: number;
    by_status?: Record<string, number>;
    by_queue?: Record<string, number>;
    [k: string]: any;
  };
}
