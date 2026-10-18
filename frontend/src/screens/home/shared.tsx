import React from "react";
import { cn, TONE } from "../../components/v2";
import type { StatusTone } from "../../lib/statusMeta";
import type { Cutoff } from "../../services/v2/home";

export const bandTone = (band?: string, secs?: number): StatusTone => {
  if (band === "passed") return "red";
  if (band === "under_1h") return "red";
  if (band === "1_to_3h") return "amber";
  if (band === "over_3h") return "grey";
  if (secs !== undefined) return secs < 3600 ? "red" : secs < 10800 ? "amber" : "grey";
  return "grey";
};

/** Cutoff chip: server-provided time_left, tone by band. Text always present. */
export const CutoffChip: React.FC<{ cutoff?: Cutoff }> = ({ cutoff }) => {
  if (!cutoff || (!cutoff.time_left && !cutoff.hhmm)) return <span className="text-slate-400">—</span>;
  const t = bandTone(cutoff.band, cutoff.seconds_left);
  const label = cutoff.band === "passed" ? "Passed" : cutoff.time_left || cutoff.hhmm;
  return (
    <span title={cutoff.hhmm ? `Cutoff ${cutoff.hhmm} UTC` : undefined}
      className={cn("inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold whitespace-nowrap", t === "grey" ? "text-slate-600" : cn(TONE[t].bg, TONE[t].text))}>
      {label}
    </span>
  );
};

export const hhmm = (iso?: string) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toISOString().slice(11, 16);
};

export const Card: React.FC<{ title?: string; right?: React.ReactNode; children: React.ReactNode; className?: string }> = ({ title, right, children, className }) => (
  <section className={cn("bg-surface-card rounded-card border border-surface-line shadow-card p-4", className)}>
    {(title || right) && <div className="flex items-center justify-between mb-3"><h2 className="text-base font-semibold text-pex-ink">{title}</h2>{right}</div>}
    {children}
  </section>
);

export const OpenButton: React.FC<{ href?: string; label?: string; onClick?: () => void }> = ({ href, label = "Open", onClick }) => (
  <a href={href} onClick={onClick} className="inline-block px-3 py-1.5 text-sm rounded-lg border border-pex-primary text-pex-primary hover:bg-pex-primary-soft focus:outline-none focus-visible:ring-2 focus-visible:ring-pex-primary">{label}</a>
);
