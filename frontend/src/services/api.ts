import {
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

export async function executeAction(case_id: string, token?: string, actor_id?: string): Promise<any> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}/actions/execute`, {
    method: "POST",
    headers,
    body: JSON.stringify({ case_id, actor_id }),
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
