import { v2Get } from "./client";

export interface Money { amount: number; currency: string; display: string }
export interface Cutoff { at?: string; hhmm?: string; seconds_left?: number; time_left?: string; band?: string }

export interface ActNowItem { case_id: string; exception: string; amount?: Money; cutoff?: Cutoff; next_action: string; next_action_type?: string; reason?: string; link?: string }
export interface WaitingItem { case_id: string; waiting_for: string; party?: string; since?: string; due?: string; overdue?: boolean }
export interface ReturnedItem { case_id: string; returned_by: string; returned_at?: string; comment?: string }
export interface MakerHome {
  role_view: "MAKER"; now?: string; greeting?: string;
  act_now?: ActNowItem[];
  tiles?: { ready: number; returned: number; waiting: number; pending: number; done_today: number };
  ready_by_cutoff?: Array<{ band: string; label: string; count: number }>;
  waiting_on_others?: WaitingItem[]; returned_to_me?: ReturnedItem[];
}
export interface SupervisorHome {
  role_view: "SUPERVISOR"; now?: string; title?: string;
  tiles?: { open: number; unassigned: number; under_1h: number; waiting_too_long: number; pending_approval: number; resolved_today: number };
  cutoff_risk?: Array<{ rail: string; rail_key?: string; next_cutoff?: Cutoff; open: number; at_risk: number }>;
  outcomes_today?: { executed_by_bank: number; handed_to_bank_awaiting: number; resolved_total: number; resolved_without_manual_repair?: number; policy_approved?: number; percent_without_manual_repair?: number; note?: string };
  team_workload?: Array<{ user_id: string; name: string; open: number; under_1h: number; returned: number; oldest?: string; oldest_case_id?: string; can_reassign?: boolean }>;
  approver_queue?: Array<{ user_id: string; name: string; pending: number; oldest?: string }>;
  compliance_note?: string;
  needs_decision?: Array<{ kind: string; case_id?: string; title: string; action?: { label: string; key: string }; link?: string }>;
}
export interface OtherHome { role_view: "APPROVER" | "COMPLIANCE" | "AUDIT" | "ADMIN"; tiles?: Record<string, number | string>; queue?: any[]; stp_batch?: { eligible: number; total_value?: Array<{ currency: string; amount: number }> }; [k: string]: unknown }
export type HomePayload = MakerHome | SupervisorHome | OtherHome;

export const fetchHome = () => v2Get<HomePayload>("/home");
