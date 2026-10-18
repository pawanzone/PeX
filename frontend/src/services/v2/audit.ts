/** Audit endpoints (contract section 9). */
import { v2Get, type Query } from "./client";
import { apiDownload } from "../http";

export interface AuditEventRow {
  id: string; time?: string; case_id?: string; event?: string; event_type?: string;
  actor?: string; actor_id?: string; role?: string; outcome?: string; detail?: string;
}
export interface AuditEventsResponse {
  total: number; items: AuditEventRow[];
  facets?: { event_types?: Array<string | { value: string; label?: string }>; roles?: Array<string | { value: string; label?: string }>; actors?: Array<string | { value: string; label?: string }> };
  integrity?: { chain_valid?: boolean; events?: number };
}
export interface AuditEventDetail {
  id: string; event?: string; case_id?: string;
  actor?: { user_id?: string; name?: string; role?: string };
  time?: string; before?: string | null; after?: string | null; evidence_reviewed?: number;
  policy_version?: string; sod?: { result?: string; text?: string }; reason?: string;
  integrity?: { sealed?: boolean; verified?: boolean; hash?: string; prev_hash?: string };
  tags?: string[];
}
export interface AuditFilters { date_from?: string; date_to?: string; event_type?: string; actor?: string; role?: string; exception_type?: string; rail?: string; q?: string; case_id?: string; page?: number; page_size?: number }
export interface ControlReport { id: string; name: string; passed?: number; failed?: number; period?: string }
export interface CaseReportRow { case_id: string; exception?: string; amount?: any; status?: string; events?: number; last_event?: string }

export const getAuditEvents = (f: AuditFilters) => v2Get<AuditEventsResponse>("/audit/events", f as Query);
export const getAuditEvent = (id: string) => v2Get<AuditEventDetail>(`/audit/events/${encodeURIComponent(id)}`);
export const getControlReports = async (): Promise<ControlReport[]> => {
  const r: any = await v2Get("/audit/control-reports");
  return Array.isArray(r) ? r : r?.items ?? [];
};
export const getAuditCases = async (q: string, page = 1): Promise<CaseReportRow[]> => {
  const r: any = await v2Get("/audit/cases", { q, page });
  return Array.isArray(r) ? r : r?.items ?? [];
};
const qstr = (f: Query) => { const p = new URLSearchParams(); Object.entries(f).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") p.set(k, String(v)); }); return p.toString(); };
export const downloadAuditExport = (f: AuditFilters) => { const { page: _p, page_size: _s, ...rest } = f; return apiDownload(`/v2/audit/export?${qstr({ ...(rest as Query), format: "csv" })}`, "pex-audit-events.csv"); };
export const downloadCaseReport = (caseId: string, format: "csv" | "json" = "csv") =>
  apiDownload(`/v2/audit/cases/${encodeURIComponent(caseId)}/report?format=${format}`, `pex-case-report-${caseId}.${format}`);
