/** Case page + case action wrappers. Coded to docs/ui_v2_api_contract.md sections 5-6.
 *  Every field is optional: the backend may omit blocks that do not apply to a variant. */
import { v2Get, v2Post } from "./client";

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
  handover?: { note?: string; by?: Person; at?: string; attachment?: { name?: string } | null } | null;
  evidence_table?: EvidenceItem[];
  evidence_summary?: { agree?: number; total?: number; label?: string; status?: string } | null;
  needed?: NeededDto | null; conflict?: ConflictDto | null; status_unknown?: StatusUnknownDto | null; compliance?: unknown;
  request_information?: RequestInfoDto | null; decision_form?: DecisionForm | null;
  handoff?: { handoff_id?: string; sent_at?: string; mode?: string; bank_comm?: string; awaiting?: string } | null;
  bank?: { reference?: string; confirmed_at?: string; clearing_system?: string } | null;
  recommendation?: { summary?: string; reasoning?: string[]; confidence_label?: string; source?: string } | null;
  journey?: JourneyDto | null;
  actions?: CaseAction[];
  blocked_actions?: Array<{ label: string; reason: string }>;
}

export interface ActionResult { ok?: boolean; case_id?: string; status?: string; variant?: string; message?: string; result?: string; checked_at?: string; replayed?: boolean }

const enc = encodeURIComponent;
export const getCasePage = (id: string) => v2Get<CasePage>(`/cases/${enc(id)}/page`);
export const getEvidenceSource = (id: string, evidenceId: string) =>
  v2Get<{ id: string; check?: string; source?: string; authority?: string; checked_at?: string; raw?: Record<string, unknown>; note?: string }>(`/cases/${enc(id)}/evidence/${enc(evidenceId)}`);

/** Generic POST to /cases/{id}/<path>. Used for every case action. */
export const postCaseAction = (id: string, path: string, body: Record<string, unknown> = {}) =>
  v2Post<ActionResult>(`/cases/${enc(id)}/${path}`, body);

export const submitCase = (id: string, handover_note: string, attachment_name?: string) =>
  postCaseAction(id, "submit", { handover_note, attachment_name: attachment_name || null });
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
