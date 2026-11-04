/** Case page + case action wrappers. Coded to docs/ui_v2_api_contract.md sections 5-6.
 *  Every field is optional: the backend may omit blocks that do not apply to a variant. */
import { v2Get, v2Post } from "./client";
import { apiDownload, apiFetch } from "../http";

export type Variant = "DECISION" | "MISSING_INFO" | "CONFLICT" | "STATUS_UNKNOWN" | "COMPLIANCE_HOLD" | "APPROVAL" | "HANDED_TO_BANK" | "EXECUTED" | "GENERIC";
export type ApiTone = "neutral" | "info" | "warn" | "danger" | "success";

export interface Money { amount?: number; currency?: string; display?: string }
export interface Cutoff { at?: string; hhmm?: string; seconds_left?: number; time_left?: string; band?: string }
export interface Chip { label: string; tone?: ApiTone }
export interface Person { user_id?: string; name?: string; role?: string }
export interface CaseAction { key: string; label: string; kind?: "primary" | "secondary" | "danger"; enabled?: boolean; disabled_reason?: string | null; endpoint?: string }

export interface FieldValue { value?: string; status?: string; highlight?: number[] | null }
export interface ChangeSummary {
  what_changes?: string; field?: string; original?: FieldValue; proposed?: FieldValue;
  source?: string; risk?: string; policy_basis?: string; if_you_approve?: string;
}
export interface EvidenceItem {
  id: string; check?: string; result?: string; source?: string; authority?: string; checked_at?: string;
  status?: string; status_label?: string; can_view_source?: boolean;
}
export interface JourneyStepDto {
  key: string; label: string; actor?: string | { name?: string; role?: string; initials?: string } | null; role?: string | null;
  at?: string | null; state?: "done" | "current" | "pending" | "not_required" | "blocked"; note?: string | null;
}
export interface JourneyDto {
  steps?: JourneyStepDto[];
  next_action?: { tone?: string; title?: string; text?: string; owner?: string } | null;
  audit_events?: number; audit_link?: string;
}
export interface DecisionForm {
  requires_review_ack?: boolean; return_reason_codes?: Array<{ code: string; label: string }>;
  reject_reason_codes?: Array<{ code: string; label: string }>; footnote?: string; level?: number; dual_auth?: boolean; limit_ok?: boolean;
}
export interface NeededDto {
  rows?: Array<{ item?: string; status?: string; note?: string | null; why?: string; why_needed?: string; source?: string; where?: string }>;
  searched?: Array<{ source?: string; result?: string }>;
}
export interface RequestInfoDto {
  to?: { party?: string; contact?: string; role?: string }; methods?: string[]; method?: string; message?: string;
  draft_saved_at?: string | null; reply_due?: string | null; escalate_at?: string | null; state?: string; sent_at?: string | null;
}
export interface ConflictSource { name?: string; value?: string; relation?: string; authority?: string; tag?: string; changed_at?: string | null; received_at?: string | null; checked_at?: string | null; note?: string }
export interface ConflictDto {
  field?: string; sources?: ConflictSource[]; note?: string; why_blocked?: string[];
  next_steps?: Array<{ key: string; label: string; detail?: string; enabled?: boolean; disabled_reason?: string }>;
  disambiguation?: { candidates?: Array<{ id: string; title?: string; value?: string; confidence?: number; source?: string }>; endpoint?: string } | null;
}
export interface StatusUnknownDto {
  uetr?: string; do_not_resend?: boolean;
  known?: Array<{ system?: string; says?: string; as_of?: string; state?: string }>;
  next?: Array<{ outcome?: string; what_happens?: string }>;
  last_check?: { at?: string; result?: string } | null; check_overdue_minutes?: number;
}

export interface DecisionRequestDto {
  title: string; target_label: string; decided_by: string; evidence_complete: boolean;
  options: Array<{ code: string; label: string }>; missing: string[]; conflicting: string[]; note: string;
  can_decide?: boolean; cannot_decide_reason?: string | null; endpoint?: string | null;
  recorded?: { option?: string; option_label?: string; state?: string; state_label?: string; by_name?: string; at?: string; comment?: string; final?: boolean } | null;
}

export interface CasePage {
  case_id: string; variant: Variant; viewer_mode?: string; now?: string;
  header?: {
    title?: string; chips?: Chip[]; amount?: Money; cutoff?: Cutoff; uetr?: string; rail?: { key?: string; label?: string };
    creditor?: string; debtor?: string; status?: string; assignee?: Person | null; opened_at?: string;
  };
  banner?: { tone?: ApiTone; title?: string; text?: string } | null;
  decision_brief?: { what_happened?: string; proposed_change?: string; evidence?: string; controls?: string; next?: string } | null;
  change_summary?: ChangeSummary | null;
  sod?: { status?: "passed" | "failed" | "n/a"; text?: string; maker?: Person; viewer_is_maker?: boolean } | null;
  handover?: { note?: string; by?: Person; at?: string; attachment?: { id?: string; name?: string; size?: number; sha256?: string } | null } | null;
  evidence_table?: EvidenceItem[];
  evidence_summary?: { agree?: number; total?: number; label?: string; status?: string } | null;
  needed?: NeededDto | null; conflict?: ConflictDto | null; status_unknown?: StatusUnknownDto | null; compliance?: unknown;
  request_information?: RequestInfoDto | null; decision_form?: DecisionForm | null;
  handoff?: { handoff_id?: string; sent_at?: string; mode?: string; bank_comm?: string; awaiting?: string } | null;
  bank?: { reference?: string; confirmed_at?: string; clearing_system?: string } | null;
  pii?: { masking: boolean; protected: boolean; can_reveal: boolean; revealed_until?: string | null; reveal_minutes: number; min_reason_length: number; reveal_classes?: { class: string; name: string }[]; restricted_note?: string | null; ai_view_endpoint?: string; reveal_endpoint: string; hide_endpoint: string } | null;
  confidence?: {
    profile: string; profile_id: string; family: string; family_name: string; coverage_pct: number; confidence_pct: number; raw_pct: number; penalty_pct: number;
    threshold: number; extra_approval: boolean; applies: boolean; label: string; reasons: string[]; gates_missing: string[]; standards: string;
    pillars: Record<string, { name: string; weight: number; score_pct: number }>;
    items: Array<{ name: string; role: string; weight: number; pillar: string; pillar_name: string; gate: boolean; state: string; source_class: string; source: string; connection: string; basis?: "check" | "instruction" | "none" | "assumed"; check_id?: string | null; check?: string | null }>;
    linked?: boolean; checked?: number; from_instruction?: number; not_run?: number;
    review: { required: boolean; state: string; reviewed_by?: Person | null; reviewed_at?: string | null; comment?: string | null; can_review: boolean; endpoint: string };
  } | null;
  recommendation?: { summary?: string; reasoning?: string[]; confidence_label?: string; source?: string } | null;
  decision_request?: DecisionRequestDto | null;
  journey?: JourneyDto | null;
  actions?: CaseAction[];
  blocked_actions?: Array<{ label: string; reason: string }>;
}

export interface ActionResult { ok?: boolean; case_id?: string; status?: string; variant?: string; message?: string; result?: string; checked_at?: string; replayed?: boolean }

const enc = encodeURIComponent;
export const getCasePage = (id: string) => v2Get<CasePage>(`/cases/${enc(id)}/page`);
export const getEvidenceSource = (id: string, evidenceId: string) =>
  v2Get<{ id: string; check?: string; source?: string; authority?: string; checked_at?: string; raw?: Record<string, unknown>; note?: string }>(`/cases/${enc(id)}/evidence/${enc(evidenceId)}`);

export interface AiView { case_id: string; payload: Record<string, unknown>; guard: { passed: boolean; rule: string }; connectors: { key: string; name: string; mode: string }[] }
/** Exactly what an AI model would be sent for this case (tokens, an amount band and derived facts only). */
export const getAiView = (id: string) => v2Get<AiView>(`/cases/${enc(id)}/ai-view`);

/** Generic POST to /cases/{id}/<path>. Used for every case action. */
export const postCaseAction = (id: string, path: string, body: Record<string, unknown> = {}) =>
  v2Post<ActionResult>(`/cases/${enc(id)}/${path}`, body);

export const submitCase = (id: string, handover_note: string, attachment_id?: string) =>
  postCaseAction(id, "submit", { handover_note, attachment_id: attachment_id || null });

/** Files a maker attaches to a handover note. The file is sent as base64 JSON; the server checks size, type and content. */
export interface AttachmentMeta { id: string; name: string; size: number; sha256: string }
export const ATTACH_MAX_BYTES = 5 * 1024 * 1024;
export const ATTACH_ACCEPT = ".pdf,.png,.jpg,.jpeg,.txt,.csv,.docx,.xlsx";
const toBase64 = (f: File) => new Promise<string>((res, rej) => {
  const r = new FileReader();
  r.onload = () => res(String(r.result).split(",")[1] ?? "");
  r.onerror = () => rej(new Error("The file could not be read."));
  r.readAsDataURL(f);
});
export const uploadAttachment = async (caseId: string, file: File) =>
  v2Post<AttachmentMeta>(`/cases/${enc(caseId)}/attachments`, { name: file.name, content_base64: await toBase64(file) });
export const removeAttachment = (caseId: string, id: string) =>
  apiFetch<{ ok: boolean }>(`/v2/cases/${enc(caseId)}/attachments/${encodeURIComponent(id)}`, { method: "DELETE" });
export const openAttachment = (caseId: string, id: string, name: string) =>
  apiDownload(`/v2/cases/${enc(caseId)}/attachments/${encodeURIComponent(id)}/download`, name);
export const approveCase = (id: string, reviewed: boolean, comment?: string) =>
  postCaseAction(id, "approve", { reviewed, comment: comment || null });
export const returnCase = (id: string, reason_code: string, comment: string) => postCaseAction(id, "return", { reason_code, comment });
export const rejectCase = (id: string, reason_code: string, comment: string) => postCaseAction(id, "reject", { reason_code, comment });
export const requestInformation = (id: string, body: { to: string; method: string; message: string; draft?: boolean; reply_due?: string | null; escalate_at?: string | null }) =>
  postCaseAction(id, "request-information", body);
export const escalateCase = (id: string, to: string, reason: string) => postCaseAction(id, "escalate", { to, reason });
export const disambiguateCase = (id: string, candidate_id: string, rationale: string) => postCaseAction(id, "disambiguate", { candidate_id, rationale });

/** Action keys use snake_case in the contract ("check_status"); URLs use kebab-case ("check-status"). */
export const actionPath = (a: CaseAction): string => {
  const ep = a.endpoint;
  if (ep) { const m = ep.match(/\/cases\/[^/]+\/(.+)$/); if (m) return m[1]; }
  return a.key.replace(/_/g, "-");
};
