import {
  UserPersona,
  PeXCase,
  DecisionRecommendation,
  AuditEvent,
  AnalyticsSummary,
  SystemInfo,
  CasePage,
  SummaryCounts,
  BatchRecord,
} from "../types";
import { apiFetch, apiDownload, setToken, ApiError } from "./http";

export { ApiError } from "./http";


// ---------------------------------------------------------------- auth

export async function fetchPersonas(): Promise<UserPersona[]> {
  return apiFetch<UserPersona[]>("/auth/personas");
}

/** Demo persona login. Stores the returned token so every later request is authenticated. */
export async function loginPersona(user_id: string): Promise<{ access_token: string; user: UserPersona }> {
  const res = await apiFetch<{ access_token: string; user: UserPersona }>("/auth/login", {
    method: "POST",
    json: { user_id },
  });
  if (res?.access_token) setToken(res.access_token);
  return res;
}

/** Sign-in screen: user + shared demo password. */
export async function signinPersona(user_id: string, password: string): Promise<{ access_token: string; user: UserPersona }> {
  const res = await apiFetch<{ access_token: string; user: UserPersona }>("/auth/signin", { method: "POST", json: { user_id, password } });
  if (res?.access_token) setToken(res.access_token);
  return res;
}

export function clearSession(): void { setToken(null); }

// ---------------------------------------------------------------- system

export async function fetchSystemInfo(): Promise<SystemInfo> {
  return apiFetch<SystemInfo>("/system/info");
}

// ---------------------------------------------------------------- analytics

export async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  return apiFetch<AnalyticsSummary>("/analytics/summary");
}

export async function fetchVelocity(): Promise<Array<{ day: string; opened: number; resolved: number }>> {
  return apiFetch("/analytics/velocity");
}

export async function fetchSummaryCounts(): Promise<SummaryCounts> {
  try {
    return await apiFetch<SummaryCounts>("/summary/counts");
  } catch (e) {
    if (!(e instanceof ApiError) || !e.unavailable) throw e;
    // Legacy backend without /summary/counts: derive from the unpaged list (small demo data only).
    const all = await fetchCases();
    const tally = (f: (c: PeXCase) => string) => all.reduce<Record<string, number>>((m, c) => { const k = f(c); m[k] = (m[k] || 0) + 1; return m; }, {});
    const st = (c: PeXCase) => String(c.status).replace("LifecycleStage.", "");
    return {
      total: all.length,
      by_status: tally(st),
      by_queue: tally((c) => c.queue),
      by_profile: tally((c) => String(c.profile)),
      by_rail: tally((c) => c.payment_rail),
      actionable_repair: all.filter((c) => c.queue === "Repair" && !["SETTLED", "REJECTED", "APPROVED", "DISPATCHED", "HANDED_TO_BANK"].includes(st(c))).length,
      pending_approvals_all: all.filter((c) => ["PENDING_APPROVAL", "AWAITING_SECOND_APPROVAL"].includes(st(c))).length,
    };
  }
}

// ---------------------------------------------------------------- cases

export interface CaseQuery {
  limit?: number;
  offset?: number;
  queue?: string;
  status?: string;
  profile?: string;
  rail?: string;
  currency?: string;
  q?: string;
  sort?: string;
  order?: "asc" | "desc";
}

/**
 * Server-side paged case list. Falls back to the legacy unpaged /cases endpoint (filtered and
 * sliced in the browser) if /cases/page is not available on this backend build.
 */
export async function fetchCasesPage(params: CaseQuery = {}): Promise<CasePage> {
  const limit = params.limit ?? 50;
  const offset = params.offset ?? 0;
  try {
    return await apiFetch<CasePage>("/cases/page", {
      query: { ...params, limit, offset },
    });
  } catch (e) {
    if (!(e instanceof ApiError) || !e.unavailable) throw e;
    const all = await fetchCases({
      queue: params.queue,
      status: params.status,
      profile: params.profile,
      search: params.q,
    });
    const filtered = all.filter((c) => {
      if (params.currency && params.currency !== "All" && c.currency !== params.currency) return false;
      if (params.rail && params.rail !== "All" && c.payment_rail !== params.rail) return false;
      return true;
    });
    return { items: filtered.slice(offset, offset + limit), total: filtered.length, limit, offset };
  }
}

export async function fetchCases(params?: {
  queue?: string;
  status?: string;
  profile?: string;
  search?: string;
}): Promise<PeXCase[]> {
  return apiFetch<PeXCase[]>("/cases", { query: params });
}

export async function fetchCaseDetail(case_id: string): Promise<{
  case: PeXCase;
  recommendation: DecisionRecommendation | null;
  approvals: any[];
}> {
  return apiFetch(`/cases/${encodeURIComponent(case_id)}`);
}

export async function runInvestigation(case_id: string): Promise<{
  case_id: string;
  tokenized_context: any;
  recommendation: DecisionRecommendation;
  governance_gate: any;
}> {
  return apiFetch(`/cases/${encodeURIComponent(case_id)}/investigate`, { method: "POST" });
}

/** Token argument kept for source compatibility; the bearer token is attached centrally. */
export async function submitApproval(
  case_id: string,
  action: string,
  comments: string,
  _token?: string
): Promise<any> {
  return apiFetch("/approvals/submit", { method: "POST", json: { case_id, action, comments }, tolerant: true });
}

export async function executeAction(case_id: string, _token?: string, actor_id?: string): Promise<any> {
  return apiFetch("/actions/execute", { method: "POST", json: { case_id, actor_id }, tolerant: true });
}

export async function initiatePayment(payload: any): Promise<any> {
  return apiFetch("/cases/initiate", { method: "POST", json: payload });
}

// ---------------------------------------------------------------- audit / governance

export async function fetchAuditStream(): Promise<AuditEvent[]> {
  return apiFetch("/audit/stream", { query: { limit: 50 } });
}

export async function fetchGovernanceControls(): Promise<any> {
  return apiFetch("/governance/controls");
}

export async function verifyAuditChain(): Promise<any> {
  return apiFetch("/governance/audit-chain/verify");
}

export async function fetchAdapters(): Promise<any[]> {
  return apiFetch("/adapters/status");
}

export async function testAdapter(adapter_id: string): Promise<any> {
  return apiFetch("/adapters/test", { method: "POST", json: { adapter_id } });
}

export async function fetchSops(): Promise<any[]> {
  return apiFetch("/copilot/sops");
}

export async function sendCopilotChat(message: string, case_id?: string): Promise<any> {
  return apiFetch("/copilot/chat", { method: "POST", json: { message, case_id } });
}

export async function fetchOntologyPipeline(): Promise<any[]> {
  return apiFetch("/ontology/pipeline");
}

export async function fetchOntologyEntities(): Promise<any[]> {
  return apiFetch("/ontology/entities");
}

export async function inspectCaseOntology(case_id: string): Promise<any> {
  return apiFetch(`/ontology/inspect/${encodeURIComponent(case_id)}`);
}

// ---------------------------------------------------------------- batches

export async function uploadBatch(file: File): Promise<{ batch_id: string; status: string }> {
  const fd = new FormData();
  fd.append("file", file);
  return apiFetch("/batch/upload", { method: "POST", body: fd });
}

export async function fetchBatches(): Promise<BatchRecord[]> {
  const res = await apiFetch<any>("/batch");
  return Array.isArray(res) ? res : res?.items ?? [];
}

export async function fetchBatch(batch_id: string): Promise<BatchRecord> {
  return apiFetch(`/batch/${encodeURIComponent(batch_id)}`);
}

export async function generateBatch(count: number, rails: string[], seed = 1): Promise<{ batch_id: string }> {
  return apiFetch("/batch/generate", {
    method: "POST",
    query: { count, seed, rails: rails.join(",") },
  });
}

export function downloadBatchResults(batch_id: string): Promise<void> {
  return apiDownload(`/batch/${encodeURIComponent(batch_id)}/results`, `${batch_id}.results.jsonl`);
}
