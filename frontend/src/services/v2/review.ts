import { apiFetch, apiDownload } from "../http";
import { v2Get } from "./client";

export type ReviewStatus = "NOT_REVIEWED" | "IN_REVIEW" | "CHANGES_REQUESTED" | "SIGNED_OFF" | "CHANGED_SINCE_SIGNOFF";
export type ReviewKind = "profile" | "control";
export interface ReviewCounts { total: number; percent_signed_off: number; NOT_REVIEWED: number; IN_REVIEW: number; CHANGES_REQUESTED: number; SIGNED_OFF: number; CHANGED_SINCE_SIGNOFF: number }
export interface ReviewSummary { profiles: ReviewCounts; controls: ReviewCounts; open_comments: number; labels: Record<ReviewStatus, string> }
export interface ReviewItem { kind: ReviewKind; id: string; name: string; status: ReviewStatus; status_label: string; reviewer: string | null; reviewer_name: string | null; reviewed_at: string | null; stored_status: string | null; version: string; signed_off_on_version: string | null; open_comments: number }
export interface ReviewComment { id: string; part: string | null; text: string; author: string; author_name: string | null; created_at: string; status: "OPEN" | "ADDRESSED"; addressed_by: string | null; addressed_note: string | null }
export interface ReviewDetail extends ReviewItem { comments: ReviewComment[] }
export interface ReviewImportResult { applied: number; rejected: Array<{ sheet: string; row: number; id: string; reason: string }> }

export const getReviewSummary = () => v2Get<ReviewSummary>("/review/summary");
export const getReviewItems = (kind: ReviewKind) => v2Get<{ items: ReviewItem[]; total: number }>("/review/items", { kind });
export const getReviewDetail = (kind: ReviewKind, id: string) => v2Get<ReviewDetail>(`/review/items/${kind}/${encodeURIComponent(id)}`);
export const setReviewStatus = (kind: ReviewKind, id: string, status: string, note?: string) => apiFetch<ReviewDetail>(`/v2/review/items/${kind}/${encodeURIComponent(id)}/status`, { method: "POST", json: { status, note } });
export const addReviewComment = (kind: ReviewKind, id: string, text: string, part?: string) => apiFetch<ReviewComment>(`/v2/review/items/${kind}/${encodeURIComponent(id)}/comments`, { method: "POST", json: { text, part } });
export const addressReviewComment = (cid: string, note?: string) => apiFetch<ReviewComment>(`/v2/review/comments/${cid}/address`, { method: "POST", json: { note } });
export const downloadReviewWorkbook = () => apiDownload("/v2/review/export.xlsx", "pex_review_workbook.xlsx");
export const importReviewWorkbook = (file: File) => { const f = new FormData(); f.append("file", file); return apiFetch<ReviewImportResult>("/v2/review/import", { method: "POST", body: f }); };
