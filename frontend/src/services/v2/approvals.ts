/** Approvals queue + batch (STP) approval wrappers. Coded to docs/ui_v2_api_contract.md sections 4 and 7. */
import { v2Get, v2Post } from "./client";
import type { Money, Cutoff, Chip, Person } from "./case";

export interface ApprovalRow {
  case_id: string; cutoff?: Cutoff; exception?: { code?: string; label?: string; domain?: string }; amount?: Money;
  rail?: { key?: string; label?: string }; counterparty?: string; status?: string; variant?: string;
  submitted_by?: string | Person | null; submitted_at?: string; waiting_for?: string;
  can_approve?: boolean; cannot_approve_reason?: string | null;
  next_action?: { text?: string; type?: string }; evidence?: { status?: string; label?: string };
}
export interface ApprovalsPage { page?: number; page_size?: number; total?: number; items?: ApprovalRow[] }

export const getApprovals = (tier: string, page = 1, page_size = 25) =>
  v2Get<ApprovalsPage>("/approvals", { tier, page, page_size });

export interface StpItem {
  case_id: string; exception?: { code?: string; label?: string }; amount?: Money; rail?: { key?: string; label?: string };
  change?: { field?: string; original?: string; proposed?: string; highlight?: number[] | null; source?: string };
  chips?: Chip[];
}
export interface StpReview {
  policy?: { rule_id?: string; text?: string; limit?: { amount?: number; currency?: string } };
  eligible?: StpItem[];
  totals?: { selected?: number; eligible?: number; total_value?: Array<{ currency: string; amount: number }>; total_value_label?: string; largest?: { case_id?: string; amount?: Money } };
  not_eligible?: { total?: number; groups?: Array<{ reason?: string; code?: string; count?: number; cases?: Array<{ case_id: string; detail?: string }> }> };
  footnote?: string;
}
export interface StpApproveResult {
  requested?: number; handed_to_bank?: number; recorded?: number; skipped?: Array<{ case_id: string; reason?: string }>; mode?: string; message?: string;
}
export const getStpReview = () => v2Get<StpReview>("/stp/review");
export const approveStp = (case_ids: string[]) => v2Post<StpApproveResult>("/stp/approve", { case_ids });
