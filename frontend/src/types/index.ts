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
  | "INVESTIGATING"
  | "RECOMMENDED"
  | "PENDING_APPROVAL"
  | "AWAITING_SECOND_APPROVAL"
  | "APPROVED"
  | "REJECTED"
  | "ESCALATED"
  | "DISPATCHED"
  | "SETTLED"
  | "FAILED";

export type ExceptionProfile =
  | "INVALID_IBAN"
  | "INVALID_BIC"
  | "DUPLICATE_PAYMENT"
  | "SANCTIONS_SUSPECTED"
  | "KYC_EXPIRED"
  | "RETURNED_PAYMENT"
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

export interface PeXCase {
  case_id: string;
  payment_id: string;
  uetr: string;
  payment_ref: string;
  profile: ExceptionProfile;
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
  ai_confidence?: number;
  created_at: string;
  approval_history?: any[];
  settled_at?: string;
}

export interface ProposedFieldChange {
  field_path: string;
  original_value_masked: string;
  proposed_value_masked: string;
  raw_proposed_value?: string;
  justification: string;
  validation_status: string;
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
  model_identifier: string;
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
  prev_hash: string;
  current_hash: string;
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
}
