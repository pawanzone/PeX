import { v2Get, v2Post } from "./client";
import type { Person } from "./case";

export interface Impact { cases_affected: number; summary: string; cases: Array<{ case_id: string; amount: number; currency?: string; now: string; was: string }>; old?: number | string; new?: number | string }
export interface PolicyChange {
  id: string; key: string; label: string; value: number | string; prev_value: number | string; status: "PENDING" | "ACTIVE" | "SUPERSEDED" | "REJECTED" | "WITHDRAWN";
  reason?: string; proposed_by?: Person | null; proposed_at: string; decided_by?: Person | null; decided_at?: string | null; note?: string | null; impact: Impact;
}
export interface PolicyParam {
  key: string; label: string; group: string; unit: string; min: number; max: number; step: number; kind: "amount" | "int" | "choice"; description: string; used_by: string; options?: Array<{ value: string; label: string; meaning: string }>;
  default: number | string; value: number | string; pending: PolicyChange | null; history: PolicyChange[];
}
export interface PolicyParams { params: PolicyParam[]; now: string; rule: string }
export const getPolicyParams = () => v2Get<PolicyParams>("/policy/params");
export const previewPolicy = (key: string, value: number | string) => v2Post<Impact>("/policy/preview", { key, value });
export const proposePolicy = (key: string, value: number | string, reason: string) => v2Post<PolicyChange>("/policy/changes", { key, value, reason });
export const decidePolicy = (id: string, how: "approve" | "reject" | "withdraw", note?: string) => v2Post<PolicyChange>(`/policy/changes/${encodeURIComponent(id)}/${how}`, { note });
