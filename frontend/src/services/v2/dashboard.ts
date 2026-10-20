import { v2Get } from "./client";

export type DashTone = "neutral" | "info" | "warn" | "danger" | "success";
export interface DashCutoff { at?: string; hhmm?: string; seconds_left?: number; time_left?: string; band?: string }
export interface DashOwner { user_id?: string | null; name: string; role: string }
export interface DashCase {
  case_id: string; exception: string; amount?: number; currency?: string; stage: string; stage_key: string;
  with: DashOwner; cutoff?: DashCutoff | null; link: string; minutes?: number; waiting?: string; reason?: string;
}
export interface Dashboard {
  now: string;
  scope: { label: string; note: string };
  headline: Array<{ key: string; label: string; value: number; tone: DashTone; hint: string }>;
  sla: { bands: Array<{ band: string; label: string; count: number }>; breached: number; under_1h: number };
  at_risk: DashCase[];
  stuck: DashCase[]; stuck_total: number;
  stages: Array<{ key: string; label: string; hint: string; count: number; oldest: string; oldest_case_id?: string | null }>;
  ageing: Array<{ band: string; label: string; count: number }>;
  rails: Array<{ rail: string; open: number; at_risk: number; next_cutoff?: DashCutoff | null }>;
  workload: Array<{ user_id?: string | null; name: string; role: string; open: number; at_risk: number }>;
  outcomes_today: { executed_by_bank: number; awaiting_bank_confirmation: number; rejected_or_failed: number; resolved: number; note: string };
  attention: { evidence_conflicts: number; evidence_missing: number; independent_review_pending: number; expedite_pings_active: number; unassigned: number };
  role_extras: { title: string; items: Array<{ label: string; value: number | string }>; link?: string };
}

export const fetchDashboard = (stuck_limit = 10) => v2Get<Dashboard>("/dashboard", { stuck_limit });
