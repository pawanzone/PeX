import { v2Get, v2Post } from "./client";
import type { Money, Cutoff, Person } from "./case";

export interface ChaserItem {
  id: string; case_id: string; level: number; level_title: string; status: "UNREAD" | "ACKNOWLEDGED"; auto: boolean; at: string; age_minutes: number; note: string;
  sender: { user_id?: string | null; name: string; role: string };
  ack_by?: Person | null; ack_at?: string | null;
  exception?: { label?: string }; amount?: Money; cutoff?: Cutoff; rail?: { label?: string }; link: string;
}
export interface ExpediteInbox { unread: number; items: ChaserItem[]; sent: ChaserItem[]; now: string; policy: { cooldown_minutes: number; auto_escalate_minutes: number } }
export const getExpedite = () => v2Get<ExpediteInbox>("/expedite");
export const ackExpedite = (id: string) => v2Post<{ ok: boolean }>(`/expedite/${encodeURIComponent(id)}/ack`);

export interface LadderLevel { level: number; title: string; sent: boolean; at?: string | null; status?: string | null; auto: boolean; ack_by?: Person | null; cooldown_minutes_left: number }
export interface CaseExpedite { case_id: string; levels: LadderLevel[]; next_level: number; can_ping: boolean; reason?: string | null }
export const getCaseExpedite = (id: string) => v2Get<CaseExpedite>(`/cases/${encodeURIComponent(id)}/expedite`);
export const pingCase = (id: string, note: string, level?: number) => v2Post<{ message?: string }>(`/cases/${encodeURIComponent(id)}/ping`, { note, level });
