import { v2Get, v2Post } from "./client";
import type { Money, Cutoff } from "./home";

export type WorkTab = "ready" | "returned" | "waiting" | "pending" | "done";
export interface WorkRow {
  case_id: string; cutoff?: Cutoff;
  exception?: { code?: string; label?: string; domain?: string };
  amount?: Money; rail?: { key: string; label: string }; counterparty?: string;
  next_action?: { text: string; type?: string }; evidence?: { status: string; label: string };
  status?: string; variant?: string; assignee?: { user_id: string; name: string } | null;
}
export interface WorkList {
  tab: WorkTab; counts: Record<WorkTab, number>; page: number; page_size: number; total: number;
  facets?: { exception_types?: Array<{ value: string; label: string; count?: number }>; rails?: Array<{ value: string; label: string; count?: number }>; currencies?: string[] };
  items: WorkRow[];
}
export interface WorkQuery { tab: WorkTab; page: number; page_size: number; exception_type?: string; rail?: string; currency?: string; cutoff_band?: string; evidence?: string; q?: string; sort?: string; dir?: string; scope?: string }
export const fetchWorklist = (q: WorkQuery) => v2Get<WorkList>("/worklist", q as any);

export interface Preview {
  case_id: string; why_flagged?: string; change?: { field: string; original?: string; proposed?: string } | null;
  evidence_summary?: string; controls?: Array<{ label: string; state: string }>; next_action?: { text?: string; type?: string; owner?: string };
  actions?: Array<{ key: string; label: string; enabled?: boolean; disabled_reason?: string | null }>;
}
export const fetchPreview = (id: string) => v2Get<Preview>(`/worklist/${encodeURIComponent(id)}/preview`);

export interface SavedViewDef { id: string; name: string; owner?: string; filters?: Record<string, string>; sort?: string }
export const fetchViews = () => v2Get<SavedViewDef[]>("/worklist/views");
export const saveView = (name: string, filters: Record<string, string>, sort?: string) => v2Post<SavedViewDef>("/worklist/views", { name, filters, sort });
export const assignCase = (id: string, assignee: string) => v2Post<{ case_id: string; assignee?: { name: string } }>(`/cases/${encodeURIComponent(id)}/assign`, { assignee });
