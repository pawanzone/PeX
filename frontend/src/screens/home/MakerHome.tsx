import React from "react";
import { AlertOctagon, Check, ChevronRight, ClipboardList, Clock, Users, AlertTriangle } from "lucide-react";
import { Tile, PageHeader, DataTable, cn } from "../../components/v2";
import { routes } from "../../lib/router";
import type { MakerHome as M } from "../../services/v2/home";
import { Card, CutoffChip, OpenButton, hhmm } from "./shared";

const caseHref = (id: string) => routes.workCase(id);
const Icon: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <span className={cn("w-10 h-10 rounded-full flex items-center justify-center shrink-0", className)} aria-hidden>{children}</span>
);

export const MakerHomeView: React.FC<{ d: M }> = ({ d }) => {
  const t = d.tiles ?? { ready: 0, returned: 0, waiting: 0, pending: 0, done_today: 0 };
  const act = d.act_now ?? [];
  const maxBand = Math.max(1, ...(d.ready_by_cutoff ?? []).map((b) => b.count));
  const barColor: Record<string, string> = { under_1h: "bg-red-500", "1_to_3h": "bg-amber-500", over_3h: "bg-slate-500" };
  const go = (tab: string) => { window.location.hash = routes.worklist({ tab }); };
  const tile = (key: string, label: string, value: number, icon: React.ReactNode, tone: string, tab: string) => (
    <button key={key} type="button" onClick={() => go(tab)} aria-label={`${label}: ${value}. Open worklist`}
      className={cn("flex items-center gap-3 rounded-card border p-4 text-left bg-white shadow-card hover:border-pex-primary/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-pex-primary", tone)}>
      <Icon className="bg-white/70">{icon}</Icon>
      <span className="flex-1"><span className="block text-sm font-medium">{label}</span><span className="block text-3xl font-semibold leading-tight">{value}</span></span>
      <ChevronRight className="w-4 h-4 opacity-60" aria-hidden />
    </button>
  );
  return (
    <>
      <PageHeader title={d.greeting || "Good morning"} subtitle="What needs you before cutoff" />

      {act.length > 0 && (
        <section aria-label="Act now" className="rounded-card border border-red-300 bg-red-50/60 mb-5">
          <h2 className="flex items-center gap-2 px-4 pt-3 pb-1 text-lg font-semibold text-red-700"><AlertOctagon className="w-5 h-5" aria-hidden />Act now</h2>
          <ul className="divide-y divide-red-100">
            {act.map((a) => (
              <li key={a.case_id} className="grid grid-cols-[5rem_9rem_1fr_11rem_1fr_6rem] gap-3 items-center px-4 py-2.5 bg-white/60 text-sm">
                <CutoffChip cutoff={a.cutoff} />
                <span className="font-medium">{a.case_id}</span>
                <span>{a.exception}</span>
                <span className="pex-mono">{a.amount?.display ?? ""}</span>
                <span className="text-pex-muted">{a.next_action}{a.reason ? ` · ${a.reason}` : ""}</span>
                <span className="text-right"><OpenButton href={caseHref(a.case_id)} /></span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3 mb-5">
        {tile("ready", "Ready to work", t.ready, <ClipboardList className="w-5 h-5 text-slate-600" />, "border-surface-line", "ready")}
        {tile("returned", "Returned to me", t.returned, <AlertTriangle className="w-5 h-5 text-amber-600" />, t.returned ? "border-amber-300 bg-amber-50/60 text-amber-800" : "border-surface-line", "returned")}
        {tile("waiting", "Waiting for information", t.waiting, <Clock className="w-5 h-5 text-slate-600" />, "border-surface-line", "waiting")}
        {tile("pending", "Pending approval", t.pending, <Users className="w-5 h-5 text-slate-600" />, "border-surface-line", "pending")}
        {tile("done", "Done today", t.done_today, <Check className="w-5 h-5 text-green-700" />, "border-green-200 bg-green-50/60 text-green-800", "done")}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-5">
        <Card title="Ready to work by cutoff">
          <ul className="space-y-3">
            {(d.ready_by_cutoff ?? []).map((b) => (
              <li key={b.band} className="grid grid-cols-[7rem_1fr_2rem] items-center gap-3 text-sm">
                <span>{b.label}</span>
                <span className="h-2.5 rounded-full bg-slate-100 overflow-hidden" role="img" aria-label={`${b.count} cases`}>
                  <span className={cn("block h-full rounded-full", barColor[b.band] ?? "bg-slate-500")} style={{ width: `${Math.max(4, (b.count / maxBand) * 100)}%` }} />
                </span>
                <span className="text-right font-medium">{b.count}</span>
              </li>
            ))}
          </ul>
          <a href={routes.worklist({ tab: "ready", sort: "cutoff" })} className="inline-block mt-4 text-sm text-pex-primary hover:underline">Open worklist, sorted by cutoff</a>
        </Card>

        <Card title="Waiting on others">
          <DataTable caption="Waiting on others" rows={d.waiting_on_others ?? []} rowKey={(r) => r.case_id} emptyTitle="Nothing is waiting on others"
            columns={[
              { key: "c", header: "Case", render: (r) => <a className="text-pex-primary hover:underline" href={caseHref(r.case_id)}>{r.case_id}</a> },
              { key: "w", header: "Waiting for", render: (r) => r.waiting_for },
              { key: "s", header: "Since", render: (r) => hhmm(r.since) },
              { key: "d", header: "Due", render: (r) => r.overdue ? <span className="text-pex-block font-semibold">Overdue</span> : hhmm(r.due) },
            ]} />
        </Card>
      </div>

      <Card title="Returned to me">
        <DataTable caption="Returned to me" rows={d.returned_to_me ?? []} rowKey={(r) => r.case_id} emptyTitle="Nothing returned to you"
          columns={[
            { key: "c", header: "Case", render: (r) => <a className="text-pex-primary hover:underline" href={caseHref(r.case_id)}>{r.case_id}</a> },
            { key: "b", header: "Returned by", render: (r) => `Returned by ${r.returned_by}` },
            { key: "m", header: "Comment", render: (r) => r.comment || <span className="text-slate-400">No comment</span> },
            { key: "a", header: "Action", align: "right", render: (r) => <OpenButton href={caseHref(r.case_id)} /> },
          ]} />
      </Card>
    </>
  );
};
