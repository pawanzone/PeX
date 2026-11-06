import React from "react";
import { PageHeader, StatusPill, cn } from "../components/v2";
import { useV2 } from "../services/v2/client";
import { getDirector, type DirBucket } from "../services/v2/director";
import { Card, Stat, Wait } from "./admin/Reference";

const th = "py-1.5 pr-3 font-medium whitespace-nowrap";
const FIXED: Record<string, string> = { pass_within_zero_touch: "bg-emerald-600", pass_needs_approval: "bg-emerald-400", no_proposal: "bg-slate-400" };
const BLOCKED = ["bg-amber-500", "bg-orange-500", "bg-rose-500", "bg-sky-600", "bg-violet-500", "bg-yellow-600"];
const segClass = (key: string, blockedIndex: number) => FIXED[key] ?? BLOCKED[blockedIndex % BLOCKED.length];
const pct = (n: number, d: number) => (d ? `${Math.round((100 * n) / d)}%` : "0%");
const rate = (x: number | null) => (x === null ? "n/a" : `${(x * 100).toFixed(1)}%`);
const fmtVal = (v: number | string) => (typeof v === "number" ? v.toLocaleString("en-US") : String(v).replace(/_/g, " ").toLowerCase().replace(/^./, (c) => c.toUpperCase()));
const who = (p: unknown) => (p && typeof p === "object" ? ((p as { name?: string }).name ?? "") : String(p ?? ""));

const Progress: React.FC<{ label: string; n: number; total: number }> = ({ label, n, total }) => (
  <div className="text-sm">
    <div className="flex justify-between"><span>{label}</span><span className="font-medium">{n} of {total}</span></div>
    <div className="h-2 rounded-full bg-slate-100 mt-1" role="img" aria-label={`${label}: ${n} of ${total}`}><div className="h-2 rounded-full bg-emerald-600" style={{ width: pct(n, total) }} /></div>
  </div>
);

/** Operations director view: how much of the queue passes the rules, what stops the rest, what is in force, how far validation and proof have got. */
export const Director: React.FC = () => {
  const r = useV2(getDirector, []);
  const d = r.data;
  if (!d) return <Wait r={r} />;
  const a = d.automation, c = d.control, p = d.proof;
  const passing = a.buckets.filter((b) => b.key.startsWith("pass_")).reduce((s, b) => s + b.count, 0);
  return (
    <div className="grid grid-cols-1 gap-4 min-w-0">
      <PageHeader title="Operations view" subtitle={<>What an operations director asks first · updated {d.as_of.slice(11, 16)} UTC</>} />
      <section aria-label="What this tells you" className="rounded-card border border-surface-line bg-surface-card p-4 shadow-card">
        <h2 className="text-base font-semibold mb-2">What this tells you</h2>
        <ul className="grid gap-1.5 text-sm">{d.headline.map((h) => <li key={h} className="flex gap-2"><span aria-hidden className="text-pex-primary">●</span><span>{h}</span></li>)}</ul>
        <p className="text-xs text-pex-muted mt-3">{d.data_note}</p>
      </section>

      <Card title="How much of the queue passes the rules" right={<StatusPill tone="blue" dot={false}>{a.release_mode.label}</StatusPill>}>
        <div className="grid gap-2 grid-cols-2 sm:grid-cols-4 mb-3">
          <Stat label="Open exceptions" value={a.open} />
          <Stat label="Pass all 8 rules" value={passing} hint={`${pct(passing, a.open)} of open`} />
          <Stat label="Stopped by a rule" value={a.blocked_total} hint={`${pct(a.blocked_total, a.open)} of open`} />
          <Stat label="Zero-touch limit" value={a.zero_touch_limit.toLocaleString("en-US")} hint="payment currency" />
        </div>
        <div className="flex h-4 rounded-full overflow-hidden bg-slate-100" role="img" aria-label="Open exceptions by outcome of the 8 rules">
          {a.buckets.filter((b) => b.count > 0).map((b) => <div key={b.key} className={cn(segClass(b.key, a.buckets.filter((x) => x.key.startsWith("blocked_")).findIndex((x) => x.key === b.key)))} style={{ width: pct(b.count, a.open) }} title={`${b.label}: ${b.count}`} />)}
        </div>
        <ul className="mt-3 grid gap-2">{a.buckets.map((b: DirBucket) => (
          <li key={b.key} className="flex gap-3 items-start text-sm">
            <span aria-hidden className={cn("mt-1 w-3 h-3 rounded-sm shrink-0", segClass(b.key, a.buckets.filter((x) => x.key.startsWith("blocked_")).findIndex((x) => x.key === b.key)))} />
            <div className="min-w-0 flex-1"><div className="flex justify-between gap-3"><span className="font-medium">{b.label}{b.rule && <span className="pex-mono text-xs text-pex-muted ml-2">{b.rule}</span>}</span><span className="font-semibold">{b.count}</span></div><div className="text-xs text-pex-muted">{b.meaning}</div></div>
          </li>))}</ul>
        <p className="text-xs text-pex-muted mt-3">{a.release_mode.note}</p>
      </Card>

      <Card title="By exception family">
        <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Open exceptions by family and rule outcome</caption>
          <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Family</th><th className={th}>Open</th><th className={th}>Pass the rules</th><th className={th}>Stopped by a rule</th><th className="font-medium">No fix proposed</th></tr></thead>
          <tbody>{a.by_family.map((f) => <tr key={f.family} className="border-t border-surface-line"><td className="py-1.5 pr-3">{f.name} <span className="pex-mono text-xs text-pex-muted">{f.family}</span></td><td className="pr-3">{f.open}</td><td className="pr-3">{f.pass_rules}</td><td className="pr-3">{f.blocked}</td><td>{f.no_proposal}</td></tr>)}</tbody></table></div>
      </Card>

      <Card title="Control: what is in force" right={<StatusPill tone={c.operation_mode === "SHADOW" ? "blue" : "amber"} dot={false}>{c.operation_mode.charAt(0) + c.operation_mode.slice(1).toLowerCase()} mode</StatusPill>}>
        <p className="text-sm text-pex-muted mb-3">{c.operation_mode_meaning}</p>
        <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Bank-set rules in force</caption>
          <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Rule</th><th className={th}>In force</th><th className={th}>Default</th><th className="font-medium">State</th></tr></thead>
          <tbody>{c.rules.map((x) => <tr key={x.key} className="border-t border-surface-line"><td className="py-1.5 pr-3">{x.label}</td><td className="pr-3 font-medium">{fmtVal(x.value)}</td><td className="pr-3 text-pex-muted">{fmtVal(x.default)}</td><td>{x.pending ? <StatusPill tone="amber" dot={false}>Change waiting for approval</StatusPill> : x.changed ? <StatusPill tone="blue" dot={false}>Changed by the bank</StatusPill> : <span className="text-xs text-pex-muted">Default</span>}</td></tr>)}</tbody></table></div>
        <h3 className="font-medium text-sm mt-4 mb-1">Recent approved changes</h3>
        {!c.recent_changes.length ? <p className="text-sm text-pex-muted">No rule has been changed from its default.</p> : (
          <ul className="grid gap-1.5 text-sm">{c.recent_changes.map((x, i) => <li key={i} className="border-t border-surface-line pt-1.5"><b>{x.label}</b>: {fmtVal(x.prev_value ?? "")} to {fmtVal(x.value)}. <span className="text-pex-muted">Proposed by {who(x.proposed_by)}, approved by {who(x.decided_by)}{x.decided_at ? ` on ${x.decided_at.slice(0, 10)}` : ""}. Reason: {x.reason}</span></li>)}</ul>
        )}
        <p className="text-xs text-pex-muted mt-3">{c.never_straight_through} of {c.profiles_total} exception types can never be straight-through, whatever any setting says. The 8 rules themselves cannot be changed here.</p>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Validation by the bank's experts">
          <div className="grid gap-3"><Progress label="Exception types signed off" n={c.sme_review.profiles_signed_off} total={c.sme_review.profiles_total} /><Progress label="Controls signed off" n={c.sme_review.controls_signed_off} total={c.sme_review.controls_total} /></div>
          <p className="text-xs text-pex-muted mt-3">{c.sme_review.open_comments} open comment(s).</p>
        </Card>
        <Card title="Proof: shadow comparison">
          {!p.loaded ? <p className="text-sm text-pex-muted">No analyst results loaded yet. Load what your analysts actually did, and PeX shows how many cases it would have released correctly, and how many wrongly.</p> : (
            <div className="grid gap-2 grid-cols-2">
              <Stat label="Cases compared" value={p.compared} />
              <Stat label="Would have released" value={p.would_release} />
              <Stat label="Released correctly" value={p.released_correctly} hint={`safe-release rate ${rate(p.safe_release_rate)}`} />
              <Stat label="Released wrongly" value={p.released_wrongly} hint="bring to zero before any live release" />
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
