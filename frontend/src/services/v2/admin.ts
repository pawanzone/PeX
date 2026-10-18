/** Admin endpoints (contract section 10). */
import { v2Get, v2Post } from "./client";

export interface Integration {
  id: string; name: string; purpose?: string; type?: string; direction?: string; mode?: "SHADOW" | "ASSISTED" | "LIVE" | string;
  health?: "healthy" | "degraded" | string; health_note?: string | null; last_event?: string; queue?: number; simulated?: boolean;
  pending_mode_change?: { id?: string; to_mode?: string; requested_by?: string } | null;
  action?: { label?: string; kind?: string };
}
export interface IntegrationsResponse {
  simulated?: boolean; banner?: string;
  tiles?: { connected?: number; healthy?: number; degraded?: number; live_writeback_enabled?: { count?: number; of?: number } };
  items: Integration[];
  modes?: Array<{ mode: string; text: string }>;
  never_executes?: string;
  handoffs_24h?: { sent?: number; acknowledged?: number; awaiting?: number; source?: string };
}
export interface ModeChangeRequest { id: string; integration_id?: string; from_mode?: string; to_mode?: string; reason?: string; state?: string; requested_by?: any; requested_at?: string; approved_by?: any }
export interface RolesResponse {
  roles: Array<{ role: string; label?: string; permissions?: string[]; approval_limit?: number; users?: Array<{ user_id: string; name: string }> }>;
  authority_matrix?: Array<{ role: string; limit?: number | string; can?: string[] }>;
}
export interface PoliciesResponse {
  thresholds: Array<{ key: string; label?: string; value?: string | number; currency?: string; editable?: boolean }>;
  rules?: any[];
}
export interface ExceptionTypesResponse {
  total: number;
  items: Array<{ code: string; label?: string; domain?: string; queue?: string; stp_permissible?: boolean; stp_note?: string | null; open_cases?: number }>;
}

export const getIntegrations = () => v2Get<IntegrationsResponse>("/admin/integrations");
export const getHandoffs = (hours = 24) => v2Get<any>("/admin/handoffs", { hours });
export const getModeChangeRequests = async (): Promise<ModeChangeRequest[]> => {
  const r: any = await v2Get("/admin/mode-change-requests");
  return Array.isArray(r) ? r : r?.items ?? [];
};
export const requestModeChange = (b: { integration_id: string; to_mode: string; reason: string }) => v2Post<ModeChangeRequest>("/admin/mode-change-request", b);
export const approveModeChange = (id: string) => v2Post<any>(`/admin/mode-change-request/${encodeURIComponent(id)}/approve`, {});
export const rejectModeChange = (id: string) => v2Post<any>(`/admin/mode-change-request/${encodeURIComponent(id)}/reject`, {});
export const getRoles = () => v2Get<RolesResponse>("/admin/roles");
export const getPolicies = () => v2Get<PoliciesResponse>("/admin/policies");
export const getExceptionTypes = () => v2Get<ExceptionTypesResponse>("/admin/exception-types");
