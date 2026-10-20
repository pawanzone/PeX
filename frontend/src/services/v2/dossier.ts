import { v2Get } from "./client";

export interface DossierStep {
  n: number; title: string;
  [k: string]: any;
}
export interface Dossier {
  case_id: string; evidence_id: string; check: string; kind: string; position: number; total: number;
  prev_id: string | null; next_id: string | null; steps: DossierStep[];
  summary: Array<{ id: string; check?: string; status?: string }>;
}
export const getDossier = (caseId: string, evidenceId: string) =>
  v2Get<Dossier>(`/cases/${encodeURIComponent(caseId)}/evidence/${encodeURIComponent(evidenceId)}/dossier`);

export interface TimelineEvent { id: string; time?: string; event?: string; actor?: string; actor_id?: string; role?: string; outcome?: string; detail?: string }
export const getTimeline = (caseId: string) =>
  v2Get<{ case_id: string; total: number; items: TimelineEvent[] }>(`/cases/${encodeURIComponent(caseId)}/timeline`);
