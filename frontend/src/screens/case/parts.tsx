import { Dossier } from "./Dossier";
import React, { useState } from "react";
import { Hourglass, AlertOctagon, CheckCircle2, User, Copy, Check, ArrowRight, X as XIcon } from "lucide-react";
import { Banner, Modal, StatusPill, NextActionCard, KeyValueList, Loading, ErrorState, cn } from "../../components/v2";
import type { JourneyStep } from "../../components/v2";
import type { StatusTone } from "../../lib/statusMeta";
import { useV2 } from "../../services/v2";
import { getEvidenceSource } from "../../services/v2/case";
import type { ApiTone, CasePage, EvidenceItem, JourneyDto, JourneyStepDto, Variant } from "../../services/v2/case";

/** API tone -> design-system tone. */
export const toneOf = (t?: string): StatusTone =>
  t === "success" ? "green" : t === "warn" ? "amber" : t === "danger" ? "red" : t === "info" ? "blue" : "grey";
export const chipTone = (t?: ApiTone | string): StatusTone => toneOf(t);

/** Times are shown in UTC (the contract sends UTC). */
export const fmtTime = (iso?: string | null): string => {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toISOString().slice(11, 16);
};
export const fmtDateTime = (iso?: string | null): string => {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : `${d.toISOString().slice(0, 10)} ${d.toISOString().slice(11, 16)} UTC`;
};
export const nameOf = (p: unknown): string =>
  typeof p === "string" ? p : p && typeof p === "object" && "name" in (p as any) ? String((p as any).name ?? "") : "";

/** Section card used by every case block. */
export const Section: React.FC<{ title: string; hint?: React.ReactNode; right?: React.ReactNode; children: React.ReactNode; className?: string; id?: string }> = ({ title, hint, right, children, className, id }) => (
  <section id={id} className={cn("bg-surface-card rounded-card border border-surface-line shadow-card p-5", className)}>
    <div className="flex items-start justify-between gap-3 mb-3">
      <div><h2 className="text-base font-semibold text-pex-ink">{title}</h2>{hint && <p className="text-sm text-pex-muted mt-0.5">{hint}</p>}</div>
      {right}
    </div>
    {children}
  </section>
);

// ------------------------------------------------------------ value highlighting
/** Changed span of `value` compared with `other` (common prefix/suffix removed). Highlight indices from the
 *  API are not trusted for display because their base (spaced vs compact string) is not defined in the contract. */
export function diffSpan(value: string, other: string): [string, string, string] {
  if (!value || value === other) return [value, "", ""];
  let p = 0;
  const max = Math.min(value.length, other.length);
  while (p < max && value[p] === other[p]) p++;
  let s = 0;
  while (s < max - p && value[value.length - 1 - s] === other[other.length - 1 - s]) s++;
  return [value.slice(0, p), value.slice(p, value.length - s), s ? value.slice(value.length - s) : ""];
}

export const HighlightedValue: React.FC<{ value?: string; other?: string; tone: "red" | "green" }> = ({ value, other, tone }) => {
  if (!value) return <span className="pex-mono text-slate-400">(empty)</span>;
  const [a, b, c] = diffSpan(value, other ?? "");
  return (
    <span className="pex-mono">
      {a}{b && <mark className={cn("rounded px-1 font-semibold", tone === "red" ? "bg-red-100 text-pex-block" : "bg-green-100 text-pex-ok")}>{b}</mark>}{c}
    </span>
  );
};

export const CopyButton: React.FC<{ text?: string; label: string }> = ({ text, label }) => {
  const [done, setDone] = useState(false);
  if (!text) return null;
  return (
    <button type="button" aria-label={label} title={label} onClick={() => { try { void navigator.clipboard?.writeText(text); setDone(true); window.setTimeout(() => setDone(false), 1500); } catch { /* clipboard unavailable */ } }}
      className="p-1 rounded text-slate-500 hover:bg-white/70">{done ? <Check className="w-4 h-4" aria-hidden /> : <Copy className="w-4 h-4" aria-hidden />}</button>
  );
};

/** Original (red) vs proposed (green) value boxes. Status text always accompanies the colour. */
export const ValueBoxes: React.FC<{ original?: { value?: string; status?: string }; proposed?: { value?: string; status?: string }; compact?: boolean }> = ({ original, proposed, compact }) => (
  <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-stretch">
    <div className="rounded-2xl bg-pex-block-soft p-4">
      <div className="flex items-center justify-between text-xs text-pex-block font-medium">
        <span className="flex items-center gap-1.5"><XIcon className="w-4 h-4" aria-hidden />Original ({(original?.status ?? "failed validation").toLowerCase()})</span>
        <CopyButton text={original?.value} label="Copy original value" />
      </div>
      <div className={cn("mt-2 break-all pex-mono text-pex-ink", compact ? "text-base" : "text-2xl")}><HighlightedValue value={original?.value} other={proposed?.value} tone="red" /></div>
    </div>
    <div className="hidden md:flex items-center justify-center text-slate-400" aria-hidden><ArrowRight className="w-5 h-5" /></div>
    <div className="rounded-2xl bg-pex-ok-soft p-4">
      <div className="flex items-center justify-between text-xs text-pex-ok font-medium">
        <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4" aria-hidden />Proposed ({(proposed?.status ?? "passes validation").toLowerCase()})</span>
        <CopyButton text={proposed?.value} label="Copy proposed value" />
      </div>
      <div className={cn("mt-2 break-all pex-mono text-pex-ink", compact ? "text-base" : "text-2xl")}><HighlightedValue value={proposed?.value} other={original?.value} tone="green" /></div>
    </div>
  </div>
);

// ------------------------------------------------------------ journey
const NEXT_ICON: Record<string, React.ElementType> = { warn: Hourglass, danger: AlertOctagon, success: CheckCircle2, info: User };

export function journeyVariant(v: Variant): "awaiting_approval" | "handed_to_bank" | "executed" | undefined {
  return v === "APPROVAL" ? "awaiting_approval" : v === "HANDED_TO_BANK" ? "handed_to_bank" : v === "EXECUTED" ? "executed" : undefined;
}

export function mapJourney(page: CasePage): { steps: JourneyStep[]; next: React.ReactNode; tone: StatusTone } {
  const j: JourneyDto = page.journey ?? {};
  const steps: JourneyStep[] = (j.steps ?? []).map((s: JourneyStepDto) => {
    const rawActor = s.actor;
    const actorName = typeof rawActor === "string" ? rawActor : rawActor?.name;
    const role = (typeof rawActor === "object" && rawActor?.role) || s.role || undefined;
    const system = !actorName || actorName === "PeX" || role === "System";
    const actor = actorName ? { name: actorName, role: system ? undefined : role ?? undefined, initials: typeof rawActor === "object" ? rawActor?.initials : undefined, system } : undefined;
    let state = s.state ?? "pending";
    let note = s.note ?? undefined;
    if (page.variant === "HANDED_TO_BANK" && s.key === "executed" && state === "pending") { state = "current"; note = note ?? "Awaiting bank confirmation"; }
    if (page.variant === "EXECUTED" && s.key === "executed" && state === "done") {
      note = note ?? `Executed by bank (confirmed)${page.bank?.reference ? ` · Bank ref ${page.bank.reference}` : ""}`;
    }
    return { id: s.key, label: s.label, state, actor, at: fmtTime(s.at) || undefined, note };
  });
  const na = j.next_action;
  const tone = toneOf(na?.tone);
  const next = na ? <NextActionCard tone={tone} title={na.title ?? "Next action"} detail={na.text} owner={na.owner} icon={NEXT_ICON[na.tone ?? "info"] ?? User} /> : null;
  return { steps, next, tone };
}

// ------------------------------------------------------------ evidence
const EV_STATUS_TONE: Record<string, StatusTone> = { pass: "green", agree: "green", fail: "red", differs: "red", missing: "amber", info: "grey" };

export const EvidenceGrid: React.FC<{ caseId: string; rows: EvidenceItem[] }> = ({ caseId, rows }) => {
  const [open, setOpen] = useState<string | null>(null);
  if (!rows.length) return <p className="text-sm text-pex-muted">No evidence recorded yet.</p>;
  return (
    <>
      <div className="overflow-x-auto rounded-lg border border-surface-line">
        <table className="w-full text-sm">
          <caption className="sr-only">Evidence checks</caption>
          <thead><tr className="text-left text-xs text-pex-muted bg-slate-50 border-b border-surface-line">
            {["Check", "Result", "Source", "Authority", "Checked", "Status", ""].map((h, i) => <th key={i} scope="col" className="py-2 px-3 font-medium">{h || <span className="sr-only">Dossier</span>}</th>)}
          </tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-surface-line last:border-0">
                <td className="py-2.5 px-3">{r.check}</td><td className="py-2.5 px-3">{r.result}</td><td className="py-2.5 px-3">{r.source}</td>
                <td className="py-2.5 px-3">{r.authority}</td><td className="py-2.5 px-3 pex-mono">{fmtTime(r.checked_at)}</td>
                <td className="py-2.5 px-3"><StatusPill tone={EV_STATUS_TONE[r.status ?? "info"] ?? "grey"}>{r.status_label ?? r.status ?? "Info"}</StatusPill></td>
                <td className="py-2.5 px-3">{r.can_view_source !== false && <button className="text-pex-primary hover:underline text-sm" onClick={() => setOpen(r.id)}>Open dossier</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {open && <Dossier caseId={caseId} evidenceId={open} onClose={() => setOpen(null)} onOpen={setOpen} />}
    </>
  );
};

export const BannerFromApi: React.FC<{ banner?: CasePage["banner"] }> = ({ banner }) =>
  banner && (banner.title || banner.text) ? <Banner tone={toneOf(banner.tone)} title={banner.title}>{banner.text}</Banner> : null;

/** Friendly message for action errors (backend sends {detail}). */
export const errText = (e: unknown): string => (e as any)?.message || "Action failed";
