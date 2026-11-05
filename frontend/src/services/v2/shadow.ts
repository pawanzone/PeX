import { apiFetch } from "../http";
import { v2Get } from "./client";

export type Verdict = "AGREE" | "DIFFER" | "PEX_NO_PROPOSAL" | "ANALYST_NO_FIX" | "BOTH_NO_FIX";
export interface ShadowColumn { name: string; required: boolean; meaning: string }
export interface ShadowProfileRow { profile: string; compared: number; agree: number; released_correctly: number; released_wrongly: number; sent_to_person: number }
export interface Scorecard {
  compared: number; loaded_at: string | null;
  release: { would_release: number; released_correctly: number; released_wrongly: { count: number; differ: number; analyst_no_fix: number }; sent_to_person: number };
  verdicts: Array<{ verdict: Verdict; text: string; count: number }>;
  rates: { agree_rate: number | null; safe_release_rate: number | null };
  time: { minutes_on_released: number; released_cases: number; cases_with_minutes: number; minutes_all: number };
  by_profile: ShadowProfileRow[]; columns: ShadowColumn[]; note: string;
}
export interface ShadowCase {
  case_id: string; profile: string; amount: number | null; currency: string | null; field: string | null; pex_would_release: boolean; blocked_by: string | null; rule: string | null;
  pex_value: string | null; analyst_action: string; analyst_value: string | null; verdict: Verdict; verdict_text: string; minutes: number | null; resolved_at: string | null;
}
export interface UploadResult { accepted: number; replaced: number; rejected: Array<{ row: number; case_id: string; reason: string }> }

export const getScorecard = () => v2Get<Scorecard>("/shadow/scorecard");
export const getShadowCases = (release?: string) => v2Get<{ items: ShadowCase[]; total: number }>("/shadow/cases", { release });
export const uploadShadowFile = (file: File) => { const f = new FormData(); f.append("file", file); return apiFetch<UploadResult>("/v2/shadow/upload", { method: "POST", body: f }); };
export const clearShadow = () => apiFetch<{ cleared: number }>("/v2/shadow", { method: "DELETE" });

export interface ValueInputs { monthly_exceptions: number; minutes_per_case: number; cost_per_hour: number; review_minutes: number }
export interface ValueScenario { kind: "assumed" | "measured"; label: string; share: number; cases_per_month: number; hours_saved_month: number; cost_saved_month: number; hours_saved_year: number; cost_saved_year: number; wrong_releases?: number; caveat?: string; sample_size?: number }
export interface ValueModel { inputs: ValueInputs; scenarios: ValueScenario[]; measured_minutes_per_case: number | null; assumptions: string[] }
export const getValueModel = (i: ValueInputs) => v2Get<ValueModel>("/value-model", { ...i });
