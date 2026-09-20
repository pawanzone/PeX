import os

src_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\src"

# 1. index.css
with open(os.path.join(src_dir, "index.css"), "w", encoding="utf-8") as f:
    f.write('''@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-slate-50 text-slate-900;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  code, pre {
    font-family: 'JetBrains Mono', monospace;
  }
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: #f1f5f9;
}
::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
''')

# 2. types/index.ts
with open(os.path.join(src_dir, "types", "index.ts"), "w", encoding="utf-8") as f:
    f.write('''export type UserRole =
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
''')

# 3. services/api.ts
with open(os.path.join(src_dir, "services", "api.ts"), "w", encoding="utf-8") as f:
    f.write('''import {
  UserPersona,
  PeXCase,
  DecisionRecommendation,
  AuditEvent,
  AnalyticsSummary,
} from "../types";

const API_BASE = "/api";

export async function fetchPersonas(): Promise<UserPersona[]> {
  const res = await fetch(`${API_BASE}/auth/personas`);
  return res.json();
}

export async function loginPersona(user_id: string): Promise<{ access_token: string; user: UserPersona }> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id }),
  });
  return res.json();
}

export async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  const res = await fetch(`${API_BASE}/analytics/summary`);
  return res.json();
}

export async function fetchVelocity(): Promise<Array<{ day: string; opened: number; resolved: number }>> {
  const res = await fetch(`${API_BASE}/analytics/velocity`);
  return res.json();
}

export async function fetchCases(params?: {
  queue?: string;
  status?: string;
  profile?: string;
  search?: string;
}): Promise<PeXCase[]> {
  const query = new URLSearchParams();
  if (params?.queue) query.set("queue", params.queue);
  if (params?.status) query.set("status", params.status);
  if (params?.profile) query.set("profile", params.profile);
  if (params?.search) query.set("search", params.search);

  const res = await fetch(`${API_BASE}/cases?${query.toString()}`);
  return res.json();
}

export async function fetchCaseDetail(case_id: string): Promise<{
  case: PeXCase;
  recommendation: DecisionRecommendation | null;
  approvals: any[];
}> {
  const res = await fetch(`${API_BASE}/cases/${case_id}`);
  return res.json();
}

export async function runInvestigation(case_id: string): Promise<{
  case_id: string;
  tokenized_context: any;
  recommendation: DecisionRecommendation;
  governance_gate: any;
}> {
  const res = await fetch(`${API_BASE}/cases/${case_id}/investigate`, {
    method: "POST",
  });
  return res.json();
}

export async function submitApproval(
  case_id: string,
  action: string,
  comments: string,
  token?: string
): Promise<any> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/approvals/submit`, {
    method: "POST",
    headers,
    body: JSON.stringify({ case_id, action, comments }),
  });
  return res.json();
}

export async function executeAction(case_id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/actions/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id }),
  });
  return res.json();
}

export async function initiatePayment(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/cases/initiate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function fetchAuditStream(): Promise<AuditEvent[]> {
  const res = await fetch(`${API_BASE}/audit/stream?limit=50`);
  return res.json();
}

export async function fetchGovernanceControls(): Promise<any> {
  const res = await fetch(`${API_BASE}/governance/controls`);
  return res.json();
}

export async function verifyAuditChain(): Promise<any> {
  const res = await fetch(`${API_BASE}/governance/audit-chain/verify`);
  return res.json();
}

export async function fetchAdapters(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/adapters/status`);
  return res.json();
}

export async function testAdapter(adapter_id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/adapters/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ adapter_id }),
  });
  return res.json();
}

export async function fetchSops(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/copilot/sops`);
  return res.json();
}

export async function sendCopilotChat(message: string, case_id?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/copilot/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, case_id }),
  });
  return res.json();
}

export async function fetchOntologyPipeline(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/ontology/pipeline`);
  return res.json();
}

export async function fetchOntologyEntities(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/ontology/entities`);
  return res.json();
}

export async function inspectCaseOntology(case_id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/ontology/inspect/${case_id}`);
  return res.json();
}
''')

print("Wrote index.css, types/index.ts, and services/api.ts")
