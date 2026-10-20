import React, { useEffect, useState } from "react";
import { RefreshCw, AlertTriangle, Clock, Users, Landmark, ShieldAlert } from "lucide-react";
import { PageHeader, Loading, ErrorState, Tile, StatusPill, cn } from "../components/v2";
import { Card } from "./home/shared";
import { useV2 } from "../services/v2/client";
import { fetchDashboard, type DashCase, type DashTone } from "../services/v2/dashboard";
import { useSession } from "../shell/session";
import { routes } from "../lib/router";

const TONE: Record<DashTone, "grey" | "blue" | "amber" | "red" | "green"> = { neutral: "grey", info: "blue", warn: "amber", danger: "red", success: "green" };
const BAND_COLOR: Record<string, string> = { passed: "bg-pex-block", under_1h: "bg-pex-wait", "1_to_3h": "bg-pex-primary", over_3h: "bg-slate-400", none: "bg-slate-200" };
const money = (a?: number, c?: string) => (a === undefined ? "—" : `${new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 }).format(a)} ${c ?? ""}`.trim());
const hhmm = (iso?: string) => (iso ? new Date(iso).toISOString().slice(11, 16) : "");

const Bar: React.FC<{ value: number; max: number; className?: string }> = ({ value, max, className }) => (
  <div className="h-2 rounded-full bg-slate-100 overflow-hidden" aria-hidden>
    <div className={cn("h-full rounded-full", className ?? "bg-pex-primary")} style={{ width: `${max ? Math.max(value ? 4 : 0, (value / max) * 100) : 0}%` }} />
  </div>
);

const CaseRow: React.FC<{ c: DashCase; detail: "cutoff" | "reason" }> = ({ c, detail }) => (
  <li className="py-2.5 border-b border-surface-line last:border-0">
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <a className="pex-mono text-sm text-pex-primary hover:underline" href={routes.workCase(c.case_id)}>{c.case_id}</a>
        <span className="text-sm text-pex-ink ml-2">{c.exception}</span>
        <div className="text-xs text-pex-muted mt-0.5">{c.stage} · with <strong className="text-pex-ink font-medium">{c.with.name}</strong> · {money(c.amount, c.currency)}</div>
        {detail === "reason" && c.reason && <div className="text-xs text-pex-wait mt-0.5">{c.reason}</div>}
      </div>
      {detail === "cutoff" && c.cutoff && (
        <StatusPill tone={c.cutoff.band === "passed" ? "red" : "amber"} title={c.cutoff.hhmm ? `Cutoff ${c.cutoff.hhmm} UTC` : undefined}>
          {c.cutoff.band === "passed" ? "Breached" : `${c.cutoff.time_left} left`}
        </StatusPill>
      )}
      {detail === "reason" && c.waiting && <StatusPill tone="red">{c.waiting}</StatusPill>}
    </div>
  </li>
);

/** Bank-wide dashboard: the same picture for every role, plus a small panel for the signed-in role. */
export const Dashboard: React.FC = () => {
  const { epoch, persona } = useSession();
  const [limit, setLimit] = useState(10);
  const r = useV2(() => fetchDashboard(limit), [epoch, limit]);
  useEffect(() => { const t = window.setInterval(() => r.reload(), 60000); return () => window.clearInterval(t); }, [r.reload]);
  if (r.loading && !r.data) return <Loading label="Loading the bank-wide picture…" />;
  if (r.error || !r.data) return <ErrorState unavailable={r.unavailable} message={r.error ?? undefined} onRetry={r.reload} />;
  const d = r.data;
  const slaTotal = d.sla.bands.reduce((s, b) => s + b.count, 0);
  const maxStage = Math.max(1, ...d.stages.map((s) => s.count));
  const maxAge = Math.max(1, ...d.ageing.map((s) => s.count));
  const att = d.attention;
  return (
    <>
      <PageHeader title="Dashboard" subtitle={<>{d.scope.label} · updated {hhmm(d.now)} UTC · {d.scope.note}</>}
        actions={<button type="button" onClick={r.reload} className="px-3 py-1.5 text-sm rounded-lg bg-white border border-surface-line text-pex-primary inline-flex items-center gap-2"><RefreshCw className="w-4 h-4" aria-hidden />Refresh</button>} />

      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3 mb-5">
        {d.headline.map((h) => <Tile key={h.key} label={h.label} value={h.value} hint={h.hint} tone={TONE[h.tone]} />)}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mb-4">
        <Card title="May breach SLA" right={<span className="text-xs text-pex-muted inline-flex items-center gap-1"><Clock className="w-3.5 h-3.5" aria-hidden />cutoff time left</span>} className="xl:col-span-1">
          <div className="flex h-3 rounded-full overflow-hidden bg-slate-100 mb-2" role="img" aria-label={d.sla.bands.map((b) => `${b.label}: ${b.count}`).join(", ")}>
            {d.sla.bands.filter((b) => b.count).map((b) => <div key={b.band} className={BAND_COLOR[b.band]} style={{ width: `${(b.count / Math.max(1, slaTotal)) * 100}%` }} />)}
          </div>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs mb-3">
            {d.sla.bands.map((b) => <li key={b.band} className="inline-flex items-center gap-1.5"><span className={cn("w-2.5 h-2.5 rounded-sm", BAND_COLOR[b.band])} aria-hidden />{b.label} <strong>{b.count}</strong></li>)}
          </ul>
          {d.at_risk.length ? <ul>{d.at_risk.map((c) => <CaseRow key={c.case_id} c={c} detail="cutoff" />)}</ul>
            : <p className="text-sm text-pex-muted">No case is past or within an hour of its cutoff.</p>}
        </Card>

        <Card title="Stuck: where and with whom" right={<StatusPill tone={d.stuck_total ? "red" : "green"}>{d.stuck_total} stuck</StatusPill>} className="xl:col-span-1">
          {d.stuck.length ? <ul>{d.stuck.map((c) => <CaseRow key={c.case_id} c={c} detail="reason" />)}</ul> : <p className="text-sm text-pex-muted">Nothing is waiting longer than its normal time.</p>}
          {d.stuck_total > d.stuck.length && <button type="button" className="mt-2 text-sm text-pex-primary hover:underline" onClick={() => setLimit(100)}>Show more ({d.stuck_total - d.stuck.length})</button>}
        </Card>

        <div className="grid gap-4 content-start">
          <Card title={d.role_extras.title} right={persona ? <span className="text-xs text-pex-muted">{persona.title}</span> : undefined}>
            <dl className="grid gap-2">
              {d.role_extras.items.map((i) => <div key={i.label} className="flex items-baseline justify-between gap-3"><dt className="text-sm text-pex-muted">{i.label}</dt><dd className="text-lg font-semibold pex-mono">{i.value}</dd></div>)}
            </dl>
            {d.role_extras.link && <a className="inline-block mt-3 text-sm text-pex-primary hover:underline" href={"#" + d.role_extras.link}>Open</a>}
          </Card>
          <Card title="Needs attention">
            <ul className="grid gap-1.5 text-sm">
              {[["Evidence conflicts", att.evidence_conflicts, ShieldAlert], ["Evidence missing", att.evidence_missing, AlertTriangle], ["Independent evidence reviews pending", att.independent_review_pending, ShieldAlert],
                ["Expedite pings active", att.expedite_pings_active, Clock], ["Unassigned with makers", att.unassigned, Users]].map(([label, n, Icon]: any) => (
                <li key={label} className="flex items-center justify-between"><span className="inline-flex items-center gap-2 text-pex-muted"><Icon className="w-4 h-4" aria-hidden />{label}</span><strong className="pex-mono">{n}</strong></li>))}
            </ul>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Card title="Where cases are" right={<span className="text-xs text-pex-muted">oldest in stage</span>}>
          <ul className="grid gap-3">
            {d.stages.map((s) => (
              <li key={s.key} title={s.hint}>
                <div className="flex items-baseline justify-between text-sm"><span>{s.label}</span><span><strong className="pex-mono">{s.count}</strong><span className="text-xs text-pex-muted ml-2">{s.count ? s.oldest : ""}</span></span></div>
                <Bar value={s.count} max={maxStage} className={s.key === "status_unknown" || s.key === "evidence_conflict" ? "bg-pex-wait" : s.key === "compliance_hold" ? "bg-purple-500" : "bg-pex-primary"} />
              </li>))}
          </ul>
        </Card>

        <Card title="Ageing of open work">
          <ul className="grid gap-3">
            {d.ageing.map((a) => <li key={a.band}><div className="flex justify-between text-sm"><span>{a.label}</span><strong className="pex-mono">{a.count}</strong></div><Bar value={a.count} max={maxAge} className={a.band === "over_24h" ? "bg-pex-block" : "bg-slate-500"} /></li>)}
          </ul>
          <h3 className="text-sm font-semibold mt-5 mb-2 inline-flex items-center gap-2"><Landmark className="w-4 h-4" aria-hidden />By rail</h3>
          <table className="w-full text-sm"><thead className="text-xs text-pex-muted text-left"><tr><th className="font-medium pb-1">Rail</th><th className="font-medium pb-1">Open</th><th className="font-medium pb-1">At risk</th><th className="font-medium pb-1">Next cutoff</th></tr></thead>
            <tbody>{d.rails.map((x) => <tr key={x.rail} className="border-t border-surface-line"><td className="py-1.5">{x.rail}</td><td className="pex-mono">{x.open}</td><td className={cn("pex-mono", x.at_risk ? "text-pex-block font-semibold" : "")}>{x.at_risk}</td><td className="text-xs text-pex-muted">{x.next_cutoff?.time_left ?? "—"}</td></tr>)}</tbody></table>
        </Card>

        <Card title="Who holds the work">
          <table className="w-full text-sm"><thead className="text-xs text-pex-muted text-left"><tr><th className="font-medium pb-1">Person or group</th><th className="font-medium pb-1">Open</th><th className="font-medium pb-1">At risk</th></tr></thead>
            <tbody>{d.workload.map((w) => <tr key={(w.user_id ?? w.name)} className="border-t border-surface-line"><td className="py-1.5">{w.name}<span className="text-xs text-pex-muted ml-2">{w.role}</span></td><td className="pex-mono">{w.open}</td><td className={cn("pex-mono", w.at_risk ? "text-pex-block font-semibold" : "")}>{w.at_risk}</td></tr>)}</tbody></table>
          <h3 className="text-sm font-semibold mt-5 mb-2">Outcomes today</h3>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-pex-muted">Executed by bank</dt><dd className="pex-mono text-right">{d.outcomes_today.executed_by_bank}</dd>
            <dt className="text-pex-muted">Awaiting bank confirmation</dt><dd className="pex-mono text-right">{d.outcomes_today.awaiting_bank_confirmation}</dd>
            <dt className="text-pex-muted">Rejected or failed</dt><dd className="pex-mono text-right">{d.outcomes_today.rejected_or_failed}</dd>
          </dl>
          <p className="text-xs text-pex-muted mt-2">{d.outcomes_today.note}</p>
        </Card>
      </div>
    </>
  );
};
