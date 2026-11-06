import { v2Get } from "./client";

export interface DirBucket { key: string; label: string; meaning: string; count: number; rule: string | null }
export interface DirFamily { family: string; name: string; open: number; pass_rules: number; blocked: number; no_proposal: number }
export interface DirRule { key: string; label: string; value: number | string; default: number | string; changed: boolean; pending: boolean }
export interface DirChange { key: string; label: string; value: number | string; prev_value: number | string | null; reason: string; proposed_by: { name?: string } | string; decided_by: { name?: string } | string | null; decided_at: string | null }
export interface Director {
  as_of: string; headline: string[]; data_note: string;
  automation: { open: number; buckets: DirBucket[]; blocked_total: number; by_family: DirFamily[]; zero_touch_limit: number; release_mode: { value: string; label: string; note: string } };
  control: {
    operation_mode: string; operation_mode_meaning: string; rules: DirRule[]; recent_changes: DirChange[]; pending_changes: number; never_straight_through: number; profiles_total: number;
    sme_review: { profiles_signed_off: number; profiles_total: number; controls_signed_off: number; controls_total: number; open_comments: number };
  };
  proof: { loaded: boolean; compared: number; would_release: number; released_correctly: number; released_wrongly: number; sent_to_person: number; safe_release_rate: number | null; agree_rate: number | null; minutes_on_released: number };
}
export const getDirector = () => v2Get<Director>("/director");
