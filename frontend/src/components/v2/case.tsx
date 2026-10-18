import React from "react";
import { Check, Circle, Minus, ArrowRight, Lock, Clock, AlertTriangle } from "lucide-react";
import type { StatusTone } from "../../lib/statusMeta";
import { cn, StatusPill, CountdownText, Avatar, TONE } from "./primitives";

export const CaseHeader: React.FC<{
  id: string; chips?: Array<{ label: string; tone?: StatusTone }>; title?: string;
  amount?: string; currency?: string; cutoff?: string; cutoffLabel?: string; meta?: Array<{ label: string; value: React.ReactNode }>;
}> = ({ id, chips, title, amount, currency, cutoff, cutoffLabel = "Cutoff", meta }) => (
  <div className="bg-surface-card rounded-card border border-surface-line shadow-card p-5">
    <div className="flex items-start justify-between gap-4 flex-wrap">
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="pex-mono text-lg font-semibold text-pex-ink">{id}</span>
          {chips?.map((c, i) => <StatusPill key={i} tone={c.tone ?? "grey"}>{c.label}</StatusPill>)}
        </div>
        {title && <p className="text-sm text-pex-muted mt-1">{title}</p>}
      </div>
      <div className="text-right">
        {amount && <div className="pex-mono text-2xl font-semibold text-pex-ink">{amount}{currency && <span className="text-sm text-pex-muted ml-1.5">{currency}</span>}</div>}
        {cutoff && <div className="text-xs text-pex-muted mt-0.5 flex items-center justify-end gap-1"><Clock className="w-3 h-3" aria-hidden />{cutoffLabel}: <CountdownText iso={cutoff} /></div>}
      </div>
    </div>
    {meta && meta.length > 0 && <dl className="mt-4 pt-4 border-t border-surface-line grid grid-cols-2 sm:grid-cols-4 gap-4">
      {meta.map((m, i) => <div key={i}><dt className="text-xs text-pex-muted">{m.label}</dt><dd className="text-sm text-pex-ink mt-0.5">{m.value}</dd></div>)}
    </dl>}
  </div>
);

export const NextActionCard: React.FC<{ tone?: StatusTone; title: string; detail?: React.ReactNode; owner?: string; icon?: React.ElementType }> = ({ tone = "blue", title, detail, owner, icon: Icon = ArrowRight }) => (
  <div className={cn("rounded-card border p-4", TONE[tone].bg, "border-current/20", TONE[tone].text)}>
    <div className="text-[11px] uppercase tracking-wide font-semibold opacity-80">Next action</div>
    <div className="mt-1 flex items-start gap-2"><Icon className="w-4 h-4 mt-0.5 shrink-0" aria-hidden /><div><div className="text-sm font-semibold">{title}</div>{detail && <div className="text-xs text-pex-ink/75 mt-0.5">{detail}</div>}</div></div>
    {owner && <div className="text-xs mt-2 text-pex-ink/70">Owner: <span className="font-medium">{owner}</span></div>}
  </div>
);

export type JourneyState = "done" | "current" | "pending" | "not_required" | "blocked";
export interface JourneyStep { id: string; label: string; state: JourneyState; actor?: { name: string; role?: string; initials?: string; system?: boolean }; at?: string; note?: string }
/** Canonical step order from the design. Backends may omit steps; "not_required" is shown struck-through. */
export const JOURNEY_STEP_LABELS = ["Detected", "Evidence gathered", "Recommendation made", "Validated", "Maker review", "Approval level 1", "Approval level 2", "Handed to bank", "Executed by bank"];
export type JourneyVariant = "awaiting_approval" | "handed_to_bank" | "executed";
export const VARIANT_TONE: Record<JourneyVariant, StatusTone> = { awaiting_approval: "blue", handed_to_bank: "amber", executed: "green" };

const STATE_LABEL: Record<JourneyState, string> = { done: "Done", current: "In progress", pending: "Pending", not_required: "Not required", blocked: "Blocked" };

export const CaseJourney: React.FC<{
  steps: JourneyStep[]; variant?: JourneyVariant; tone?: StatusTone; nextAction?: React.ReactNode;
  auditCount?: number; onViewAudit?: () => void; title?: string;
}> = ({ steps, variant, tone, nextAction, auditCount, onViewAudit, title = "Case journey" }) => {
  const t = tone ?? (variant ? VARIANT_TONE[variant] : "blue");
  return (
    <aside aria-label={title} className="bg-surface-card rounded-card border border-surface-line shadow-card p-4">
      <h2 className="text-sm font-semibold text-pex-ink mb-3">{title}</h2>
      {nextAction && <div className="mb-4">{nextAction}</div>}
      <ol className="relative">
        {steps.map((s, i) => {
          const last = i === steps.length - 1;
          const dim = s.state === "pending" || s.state === "not_required";
          return (
            <li key={s.id} className="relative flex gap-3 pb-4 last:pb-0" aria-current={s.state === "current" ? "step" : undefined}>
              {!last && <span aria-hidden className={cn("absolute left-[11px] top-6 bottom-0 w-px", s.state === "done" ? TONE.green.dot : "bg-slate-200")} />}
              <span className={cn("relative z-10 w-6 h-6 rounded-full flex items-center justify-center shrink-0 ring-2 ring-white",
                s.state === "done" && "bg-pex-ok text-white", s.state === "current" && cn(TONE[t].dot, "text-white"),
                s.state === "blocked" && "bg-pex-block text-white", s.state === "pending" && "bg-slate-100 text-slate-400 border border-slate-300", s.state === "not_required" && "bg-slate-50 text-slate-300 border border-dashed border-slate-300")}>
                {s.state === "done" ? <Check className="w-3.5 h-3.5" aria-hidden /> : s.state === "blocked" ? <AlertTriangle className="w-3 h-3" aria-hidden /> : s.state === "not_required" ? <Minus className="w-3 h-3" aria-hidden /> : s.state === "current" ? <Circle className="w-2.5 h-2.5 fill-current" aria-hidden /> : <Lock className="w-3 h-3" aria-hidden />}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className={cn("text-sm", dim ? "text-slate-400" : "text-pex-ink font-medium", s.state === "not_required" && "line-through")}>{s.label}<span className="sr-only"> — {STATE_LABEL[s.state]}</span></span>
                  {s.at && <time className="text-xs text-pex-muted shrink-0">{s.at}</time>}
                </div>
                {s.actor && <div className="mt-1 flex items-center gap-1.5"><Avatar size="sm" name={s.actor.name} initials={s.actor.initials} system={s.actor.system} />{s.actor.role && <span className="text-[11px] px-1.5 py-px rounded bg-slate-100 text-slate-600">{s.actor.role}</span>}</div>}
                {s.note && <div className="text-xs text-pex-muted mt-1">{s.note}</div>}
                {s.state === "not_required" && !s.note && <div className="text-xs text-slate-400 mt-0.5">Not required for this case</div>}
              </div>
            </li>
          );
        })}
      </ol>
      {(auditCount !== undefined || onViewAudit) && (
        <div className="mt-4 pt-3 border-t border-surface-line flex items-center justify-between text-xs">
          <span className="text-pex-muted">{auditCount ?? 0} audit events</span>
          {onViewAudit && <button onClick={onViewAudit} className="text-pex-primary font-medium hover:underline">View full audit</button>}
        </div>
      )}
    </aside>
  );
};

export interface ActionDef { id: string; label: string; onClick: () => void; kind?: "primary" | "secondary" | "danger"; disabled?: boolean; disabledReason?: string; icon?: React.ElementType }
/** Sticky bottom bar. Disabled actions must carry a reason (shown as text, not just a tooltip). */
export const ActionBar: React.FC<{ actions: ActionDef[]; summary?: React.ReactNode; lockedNote?: React.ReactNode }> = ({ actions, summary, lockedNote }) => {
  const blocked = actions.filter((a) => a.disabled && a.disabledReason);
  return (
    <div className="sticky bottom-0 z-20 -mx-6 mt-6 bg-white/95 backdrop-blur border-t border-surface-line px-6 py-3">
      <div className="flex items-center gap-3 flex-wrap">
        {summary && <div className="text-sm text-pex-muted mr-auto">{summary}</div>}
        {!summary && <span className="mr-auto" />}
        {actions.map((a) => {
          const Icon = a.icon;
          return (
            <button key={a.id} type="button" onClick={a.onClick} disabled={a.disabled} title={a.disabled ? a.disabledReason : undefined}
              className={cn("px-4 py-2 text-sm font-medium rounded-lg inline-flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed",
                (a.kind ?? "secondary") === "primary" && "bg-pex-primary text-white hover:bg-pex-primary-dark",
                (a.kind ?? "secondary") === "secondary" && "bg-white border border-surface-line text-pex-ink hover:bg-slate-50",
                a.kind === "danger" && "bg-white border border-pex-block/40 text-pex-block hover:bg-pex-block-soft")}>
              {Icon && <Icon className="w-4 h-4" aria-hidden />}{a.label}
            </button>
          );
        })}
      </div>
      {(blocked.length > 0 || lockedNote) && <div className="mt-2 text-xs text-pex-muted flex items-center gap-1.5"><Lock className="w-3 h-3" aria-hidden />{lockedNote ?? blocked.map((b) => `${b.label}: ${b.disabledReason}`).join(" · ")}</div>}
    </div>
  );
};
