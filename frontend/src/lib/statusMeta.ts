/**
 * Single source of truth for lifecycle status presentation and grouping.
 * Every component that renders or filters a case status MUST use this module.
 *
 * Principle: PeX never executes or settles payments. Only a bank-signed outcome can produce
 * EXECUTED_CONFIRMED / SETTLED, so those are always labelled "bank confirmed".
 */
import { LifecycleStage } from "../types";

export type StatusTone = "red" | "amber" | "green" | "blue" | "grey" | "purple";

export interface StatusMeta {
  label: string;
  short: string;
  tone: StatusTone;
  /** Work still needed from a human or PeX (shows in actionable counts). */
  actionable: boolean;
  /** No further PeX/human work expected (bank-confirmed or rejected/closed). */
  terminal: boolean;
  /** Waiting on something outside PeX (bank acknowledgement, second approver...). */
  waiting: boolean;
  description: string;
}

export const STATUS_META: Record<LifecycleStage, StatusMeta> = {
  INGESTED: { label: "Ingested", short: "Ingested", tone: "grey", actionable: true, terminal: false, waiting: false, description: "Exception received and normalised." },
  CANONICALIZED: { label: "Normalised", short: "Normalised", tone: "grey", actionable: true, terminal: false, waiting: false, description: "Mapped into the canonical payment model." },
  VALIDATED: { label: "Validated", short: "Validated", tone: "blue", actionable: true, terminal: false, waiting: false, description: "Deterministic checks passed; awaiting resolution decision." },
  INVESTIGATING: { label: "Investigating", short: "Investigating", tone: "blue", actionable: true, terminal: false, waiting: false, description: "Evidence is being gathered and assessed." },
  RECOMMENDED: { label: "Recommended", short: "Recommended", tone: "blue", actionable: true, terminal: false, waiting: false, description: "A repair is proposed and needs a human decision." },
  PENDING_APPROVAL: { label: "Pending approval", short: "Pending approval", tone: "amber", actionable: true, terminal: false, waiting: true, description: "Waiting for a checker to authorise." },
  AWAITING_SECOND_APPROVAL: { label: "Awaiting second approver", short: "2nd approval", tone: "amber", actionable: true, terminal: false, waiting: true, description: "Dual authorisation: a second, different approver is required." },
  RETURNED_FOR_REWORK: { label: "Returned to maker", short: "Rework", tone: "amber", actionable: true, terminal: false, waiting: false, description: "Checker returned the case for changes." },
  APPROVED: { label: "Approved, not yet handed to bank", short: "Approved", tone: "green", actionable: true, terminal: false, waiting: false, description: "Authorised by a checker. Ready to hand to the bank." },
  REJECTED: { label: "Rejected", short: "Rejected", tone: "red", actionable: false, terminal: true, waiting: false, description: "Repair rejected. No instruction will be sent." },
  ESCALATED: { label: "Escalated", short: "Escalated", tone: "purple", actionable: true, terminal: false, waiting: true, description: "Routed to a specialist or senior approver." },
  DISPATCHED: { label: "Handed to bank, awaiting confirmation", short: "Handed to bank", tone: "blue", actionable: false, terminal: false, waiting: true, description: "Instruction handed to the bank. PeX has not seen a bank confirmation yet." },
  HANDED_TO_BANK: { label: "Handed to bank, awaiting confirmation", short: "Handed to bank", tone: "blue", actionable: false, terminal: false, waiting: true, description: "Instruction handed to the bank. PeX has not seen a bank confirmation yet." },
  EXECUTED_CONFIRMED: { label: "Executed, bank confirmed", short: "Executed", tone: "green", actionable: false, terminal: false, waiting: false, description: "The bank confirmed it executed the instruction." },
  SETTLED: { label: "Settled, bank confirmed", short: "Settled", tone: "green", actionable: false, terminal: true, waiting: false, description: "The bank confirmed settlement. Set only by a bank signal." },
  FAILED: { label: "Failed", short: "Failed", tone: "red", actionable: true, terminal: false, waiting: false, description: "Processing or the bank reported a failure." },
  STATUS_UNKNOWN: { label: "Status unknown, do not resend", short: "Unknown, do not resend", tone: "red", actionable: true, terminal: false, waiting: true, description: "No bank confirmation arrived in time. Check with the bank before any resend." },
  SHADOW_RECORDED: { label: "Shadow, no action taken", short: "Shadow", tone: "grey", actionable: false, terminal: true, waiting: false, description: "Recommendation recorded for comparison. Nothing was sent to any bank." },
};

const FALLBACK: StatusMeta = {
  label: "Unknown status", short: "Unknown", tone: "grey", actionable: false, terminal: false, waiting: false,
  description: "Status not recognised by this version of the UI.",
};

/** Accepts "SETTLED", "LifecycleStage.SETTLED" or undefined. */
export function normalizeStatus(raw: unknown): string {
  return String(raw ?? "").replace("LifecycleStage.", "").trim().toUpperCase();
}

export function statusMeta(raw: unknown): StatusMeta {
  const key = normalizeStatus(raw) as LifecycleStage;
  const meta = STATUS_META[key];
  if (meta) return meta;
  const text = normalizeStatus(raw);
  return text ? { ...FALLBACK, label: text, short: text } : FALLBACK;
}

export const TONE_CLASSES: Record<StatusTone, { chip: string; dot: string; text: string; bg: string; border: string }> = {
  red: { chip: "bg-red-50 text-red-700 border-red-200", dot: "bg-red-500", text: "text-red-700", bg: "bg-red-50", border: "border-red-200" },
  amber: { chip: "bg-amber-50 text-amber-700 border-amber-200", dot: "bg-amber-500", text: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200" },
  green: { chip: "bg-emerald-50 text-emerald-700 border-emerald-200", dot: "bg-emerald-500", text: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200" },
  blue: { chip: "bg-sky-50 text-sky-700 border-sky-200", dot: "bg-sky-500", text: "text-sky-700", bg: "bg-sky-50", border: "border-sky-200" },
  grey: { chip: "bg-slate-100 text-slate-600 border-slate-200", dot: "bg-slate-400", text: "text-slate-600", bg: "bg-slate-100", border: "border-slate-200" },
  purple: { chip: "bg-purple-50 text-purple-700 border-purple-200", dot: "bg-purple-500", text: "text-purple-700", bg: "bg-purple-50", border: "border-purple-200" },
};

/** Filter dropdown options for the worklist. value "All" means no filter. */
export const STATUS_FILTER_OPTIONS: Array<{ value: string; label: string }> = [
  "RECOMMENDED", "PENDING_APPROVAL", "AWAITING_SECOND_APPROVAL", "RETURNED_FOR_REWORK", "APPROVED",
  "HANDED_TO_BANK", "EXECUTED_CONFIRMED", "SETTLED", "SHADOW_RECORDED", "STATUS_UNKNOWN",
  "INGESTED", "INVESTIGATING", "ESCALATED", "REJECTED", "FAILED",
].map((v) => ({ value: v === "HANDED_TO_BANK" ? "DISPATCHED" : v, label: STATUS_META[v as LifecycleStage].short }));

export function isTerminal(raw: unknown): boolean { return statusMeta(raw).terminal; }
export function isBankConfirmed(raw: unknown): boolean {
  const s = normalizeStatus(raw);
  return s === "SETTLED" || s === "EXECUTED_CONFIRMED";
}
export function isHandedToBank(raw: unknown): boolean {
  const s = normalizeStatus(raw);
  return s === "DISPATCHED" || s === "HANDED_TO_BANK";
}

/** SLA colour semantics from the design system: <1h red, 1-3h amber, >3h grey. */
export function slaTone(dueIso?: string, now: number = Date.now()): { tone: StatusTone; label: string; minutes: number | null } {
  if (!dueIso) return { tone: "grey", label: "No SLA", minutes: null };
  const due = new Date(dueIso).getTime();
  if (Number.isNaN(due)) return { tone: "grey", label: "No SLA", minutes: null };
  const minutes = Math.round((due - now) / 60000);
  if (minutes < 0) return { tone: "red", label: `Overdue ${formatDuration(-minutes)}`, minutes };
  if (minutes < 60) return { tone: "red", label: `${formatDuration(minutes)} left`, minutes };
  if (minutes <= 180) return { tone: "amber", label: `${formatDuration(minutes)} left`, minutes };
  return { tone: "grey", label: `${formatDuration(minutes)} left`, minutes };
}

export function formatDuration(totalMinutes: number): string {
  const m = Math.max(0, Math.round(totalMinutes));
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  const rem = m % 60;
  if (h >= 48) return `${Math.floor(h / 24)}d`;
  return rem ? `${h}h ${rem}m` : `${h}h`;
}
