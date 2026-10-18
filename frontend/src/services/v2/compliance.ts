/** Compliance endpoints (docs/ui_v2_api_contract.md sections 4, 5, 6). Defensive about missing fields. */
import { v2Get, v2Post } from "./client";

export interface Money { amount?: number; currency?: string; display?: string }
export interface Cutoff { at?: string; hhmm?: string; seconds_left?: number; time_left?: string; band?: string }
export interface Chip { label: string; tone?: string }
export interface V2Action { key: string; label: string; kind?: string; enabled?: boolean; disabled_reason?: string | null; endpoint?: string }

export interface ComplianceQueueRow {
  case_id: string;
  cutoff?: Cutoff;
  exception?: { code?: string; label?: string; domain?: string };
  amount?: Money;
  rail?: { key?: string; label?: string };
  counterparty?: string;
  screening_ref?: string;
  raised_at?: string;
  status?: string;
  next_action?: { text?: string; type?: string };
  assignee?: { user_id?: string; name?: string } | null;
}
export interface ComplianceQueue { items: ComplianceQueueRow[]; total?: number }

export interface JourneyStepV2 { key: string; label: string; actor?: string; role?: string; at?: string; state: "done" | "current" | "pending" | "not_required" | "blocked"; note?: string | null }
export interface JourneyV2 {
  steps: JourneyStepV2[];
  next_action?: { tone?: string; title?: string; text?: string; owner?: string };
  audit_events?: number; audit_link?: string;
}
export interface PartyRow { attribute: string; payment_party?: string; listed_entity?: string; result?: "similar" | "same" | "differs" | "not_comparable" | string; label?: string }
export interface ComplianceBlock {
  alert?: { reference?: string; source?: string; list?: string; match_type?: string; raised_at?: string; open_url?: string | null; note?: string };
  party_comparison?: PartyRow[];
  notes?: Array<{ by?: string; at?: string; text?: string }>;
  attachments?: Array<{ name: string }>;
  decisions?: Array<{ key: string; label: string; needs_second_reviewer?: boolean }>;
  reason_codes?: Array<{ code: string; label: string }>;
  second_review?: { required?: boolean; state?: "none" | "pending" | "done" | string; first_reviewer?: string | null };
  footer?: string;
}
export interface ComplianceCasePage {
  case_id: string;
  variant: string;
  viewer_mode?: string;
  header?: {
    title?: string; chips?: Chip[]; amount?: Money; cutoff?: Cutoff; uetr?: string; status?: string;
    rail?: { label?: string }; creditor?: string; debtor?: string;
  };
  banner?: { tone?: string; title?: string; text?: string } | null;
  compliance?: ComplianceBlock | null;
  journey?: JourneyV2;
  actions?: V2Action[];
  blocked_actions?: Array<{ label: string; reason: string }>;
}

export const getComplianceQueue = async (): Promise<ComplianceQueue> => {
  const r: any = await v2Get("/compliance/queue");
  if (Array.isArray(r)) return { items: r, total: r.length };
  return { items: r?.items ?? [], total: r?.total ?? (r?.items?.length ?? 0) };
};
export const getCasePage = (id: string) => v2Get<ComplianceCasePage>(`/cases/${encodeURIComponent(id)}/page`);
export type ComplianceDecisionKey = "release" | "confirm_block" | "escalate";
export const postComplianceDecision = (id: string, body: { decision: ComplianceDecisionKey; reason_code: string; comment: string }) =>
  v2Post<{ ok?: boolean; message?: string; status?: string }>(`/cases/${encodeURIComponent(id)}/compliance/decision`, body);
