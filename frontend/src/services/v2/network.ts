import { v2Get, v2Post } from "./client";
import type { Person } from "./case";

export type NetKind = "INVESTIGATION" | "RECALL";
export type NetDirection = "INBOUND" | "OUTBOUND";
export type NetStatus = "NEW" | "DRAFTED" | "PART_APPROVED" | "SENT" | "REPLY_RECEIVED" | "AWAITING_BANK_RETURN" | "CLOSED";

export interface NetRow {
  id: string; kind: NetKind; direction: NetDirection; status: NetStatus; status_label: string; uetr: string; counterparty_bic: string;
  amount: number | null; currency: string | null; reason_code: string | null; reason_label: string; created_at: string; due_at: string | null; overdue: boolean; linked_case_id: string | null;
}
export interface NetCounts { open: number; overdue: number; investigations: number; recalls: number; inbound: number; outbound: number; awaiting_bank: number }
export interface NetList {
  items: NetRow[]; counts: NetCounts; own_bic: string; response_hours: number; rule: string;
  codes: { investigation_reasons: Record<string, string>; recall_reasons: Record<string, string> };
}
export interface NetMessage { msg_type: string; title: string; xml: string | null; fields: Record<string, any> | null; outcome?: string; outcome_label?: string; draft?: boolean; reason_code?: string | null; text?: string; drafted_by?: Person | null }
export interface NetApproval { user_id: string; name: string; role: string; at: string; note: string }
export interface NetDetail extends NetRow {
  uetr_standard: boolean; case_ref: string | null; message_id: string | null; narrative: string; warnings: string[];
  linked_case: { case_id: string; status: string; amount: number | null; currency: string | null; rail: string | null; link: string } | null;
  request: NetMessage; response: NetMessage | null; approvals: NetApproval[]; approvals_needed: number; dual_amount: number;
  handoff: { state: string; requested_at?: string; reference?: string | null; note?: string; confirmed_at?: string } | null;
  timeline: Array<{ at: string; actor: string; action: string; text: string }>; money_moved: boolean;
  codes: { outcomes: Record<string, string>; reject_reasons: Record<string, string>; accept_reasons: Record<string, string> };
  actions: { can_draft: boolean; can_authorise: boolean; can_simulate_reply: boolean; can_record_return: boolean; can_close: boolean };
}

const e = encodeURIComponent;
export const getNetworkCases = (kind?: string, direction?: string) => {
  const q = new URLSearchParams(); if (kind) q.set("kind", kind); if (direction) q.set("direction", direction);
  const s = q.toString(); return v2Get<NetList>(`/network/cases${s ? "?" + s : ""}`);
};
export const getNetworkCase = (id: string) => v2Get<NetDetail>(`/network/cases/${e(id)}`);
export const receiveMessage = (xml: string) => v2Post<NetDetail>("/network/inbound", { xml });
export const receiveSample = (kind: NetKind, case_id?: string) => v2Post<NetDetail>("/network/inbound/sample", { kind, case_id });
export const raiseOutbound = (b: { kind: NetKind; case_id?: string; uetr?: string; reason_code: string; narrative: string; counterparty_bic: string }) => v2Post<NetDetail>("/network/outbound", b);
export const draftReply = (id: string, b: { outcome: string; reason_code?: string | null; text: string }) => v2Post<NetDetail>(`/network/cases/${e(id)}/draft`, b);
export const authoriseMessage = (id: string, note?: string) => v2Post<NetDetail>(`/network/cases/${e(id)}/authorise`, { note });
export const simulateReply = (id: string, outcome?: string) => v2Post<NetDetail>(`/network/cases/${e(id)}/simulate-reply`, { outcome });
export const recordBankReturn = (id: string, reference: string) => v2Post<NetDetail>(`/network/cases/${e(id)}/bank-return`, { reference });
export const closeNetworkCase = (id: string, note?: string) => v2Post<NetDetail>(`/network/cases/${e(id)}/close`, { note });
