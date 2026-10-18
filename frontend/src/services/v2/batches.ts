import { apiFetch, apiDownload } from "../http";
import { v2Get } from "./client";

export interface BatchSummary { batch_id: string; filename?: string; status?: string; status_label?: string; received_at?: string; source?: string; records?: number; accepted?: number; duplicate?: number; rejected?: number; needs_review?: number }
export const fetchBatchList = async (page = 1, page_size = 25) => {
  const r = await v2Get<any>("/batches", { page, page_size });
  return (Array.isArray(r) ? r : r?.items ?? []) as BatchSummary[];
};

export type Outcome = "accepted" | "duplicate" | "rejected" | "needs_review";
export type BatchTab = "all" | Outcome;
export interface BatchRecordRow { record: number; source_reference?: string; case_id?: string | null; outcome: Outcome; outcome_label?: string; detail?: string; action?: { type: string; label: string } }
export interface BatchDetailData {
  batch_id: string; filename?: string; status?: string; status_label?: string; received_at?: string; source?: string; records?: number;
  stages?: Array<{ key: string; label: string; at?: string | null; state?: string }>;
  counts?: { received: number; accepted: number; duplicate: number; rejected: number; needs_review: number };
  reconciliation?: { balanced: boolean; text: string };
  tab?: string; tab_counts?: Record<string, number>; page: number; page_size: number; total: number; items: BatchRecordRow[];
  outputs?: { bank_handoff_requests?: { sent: number; text: string }; archive?: { archived: boolean; checksum?: string; verified?: boolean; at?: string | null } };
  actions?: { download_rejected?: string; reprocess?: { enabled: boolean; reason?: string; endpoint?: string } };
}
export const fetchBatchDetail = (id: string, tab: BatchTab, page: number, page_size: number) =>
  v2Get<BatchDetailData>(`/batches/${encodeURIComponent(id)}`, { tab, page, page_size });
export const fetchRecord = (id: string, record: number) => v2Get<{ record: number; outcome: string; detail?: string; errors?: string[]; raw?: unknown; case_id?: string | null }>(`/batches/${encodeURIComponent(id)}/records/${record}`);

/** Upload a batch JSON/JSONL/gz file. Uses the v2 wrapper, falls back to the original /api/batch/upload (same pipeline). */
export async function uploadBatchFile(file: File): Promise<{ batch_id: string; status?: string }> {
  const mk = () => { const fd = new FormData(); fd.append("file", file); return fd; };
  try { return await apiFetch("/v2/batches/upload", { method: "POST", body: mk() }); }
  catch (e: any) {
    if (e?.status === 404 || e?.status === 405 || e?.status === 501) return apiFetch("/batch/upload", { method: "POST", body: mk() });
    throw e;
  }
}
/** Generate a demo batch via the existing endpoint (synthetic, labelled as such). */
export const generateDemoBatch = (count: number, rails: string[], seed = 1) =>
  apiFetch<{ batch_id: string }>("/batch/generate", { method: "POST", query: { count, seed, rails: rails.join(",") } });

export const downloadRejected = (id: string, format: "jsonl" | "csv" | "json" = "jsonl") =>
  apiDownload(`/v2/batches/${encodeURIComponent(id)}/rejected?format=${format}`, `${id}.rejected.${format}`);
export async function reprocessBatch(id: string, file: File): Promise<{ batch_id: string; parent_batch_id?: string; status?: string }> {
  const fd = new FormData(); fd.append("file", file);
  return apiFetch(`/v2/batches/${encodeURIComponent(id)}/reprocess`, { method: "POST", body: fd });
}
