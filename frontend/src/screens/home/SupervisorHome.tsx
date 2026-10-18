import React from "react";
import { AlertTriangle, Check, Clock, FileText, Info, Users } from "lucide-react";
import { PageHeader, DataTable, cn, useToast } from "../../components/v2";
import { routes } from "../../lib/router";
import type { SupervisorHome as S } from "../../services/v2/home";
import { assignCase } from "../../services/v2/worklist";
import { Card, hhmm, OpenButton } from "./shared";

const Big: React.FC<{ label: string; value: number | string; icon: React.ReactNode; cls: string; link?: { label: string; href: string } }> = ({ label, value, icon, cls, link }) => (
  <div className={cn("rounded-card border p-4 flex items-start gap-3 shadow-card", cls)}>
    <span className="w-10 h-10 rounded-full bg-white/70 flex items-center justify-center" aria-hidden>{icon}</span>
    <div><div className="text-sm font-medium">{label}</div><div className="flex items-baseline gap-3"><span className="text-3xl font-semibold">{value}</span>{link && <a href={link.href} className="text-sm underline text-pex-primary">{link.label}</a>}</div></div>
  </div>
);

export const SupervisorHomeView: React.FC<{ d: S; reload: () => void }> = ({ d, reload }) => {
  const t = d.tiles ?? { open: 0, unassigned: 0, under_1h: 0, waiting_too_long: 0, pending_approval: 0, resolved_today: 0 };
  const o = d.outcomes_today;
  const toast = useToast();
  const total = Math.max(1, o?.resolved_total ?? 0, (o?.executed_by_bank ?? 0) + (o?.handed_to_bank_awaiting ?? 0));
  const act = async (item: NonNullable<S["needs_decision"]>[number]) => {
    if (item.kind === "UNASSIGNED") { window.location.hash = routes.worklist({ tab: "ready", scope: "all" }); return; }
    if (item.case_id) window.location.hash = routes.workCase(item.case_id);
  };
  return (
    <>
      <PageHeader title={d.title || "Operations overview"} subtitle="Cutoff risk and workload, today" />
      <div className="grid grid-cols-2 xl:grid-cols-6 gap-3 mb-5">
        <Big label="Open cases" value={t.open} icon={<FileText className="w-5 h-5 text-slate-600" />} cls="bg-white border-surface-line" />
        <Big label="Unassigned" value={t.unassigned} icon={<Users className="w-5 h-5 text-amber-600" />} cls="bg-amber-50/70 border-amber-300 text-amber-800" link={{ label: "Assign", href: routes.worklist({ tab: "ready", scope: "all" }) }} />
        <Big label="Under 1h to cutoff" value={t.under_1h} icon={<Clock className="w-5 h-5 text-red-600" />} cls="bg-red-50/70 border-red-300 text-red-700" />
        <Big label="Waiting too long" value={t.waiting_too_long} icon={<AlertTriangle className="w-5 h-5 text-amber-600" />} cls="bg-amber-50/70 border-amber-300 text-amber-800" />
        <Big label="Pending approval" value={t.pending_approval} icon={<Users className="w-5 h-5 text-slate-600" />} cls="bg-white border-surface-line" />
        <Big label="Resolved today" value={t.resolved_today} icon={<Check className="w-5 h-5 text-green-700" />} cls="bg-green-50/70 border-green-300 text-green-800" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <Card title="Cutoff risk by rail">
          <DataTable caption="Cutoff risk by rail" rows={d.cutoff_risk ?? []} rowKey={(r) => r.rail}
            columns={[
              { key: "r", header: "Rail", render: (r) => r.rail },
              { key: "n", header: "Next cutoff", render: (r) => r.next_cutoff?.hhmm ?? hhmm(r.next_cutoff?.at) },
              { key: "t", header: "Time left", render: (r) => <span className={cn("font-medium", r.next_cutoff?.band === "under_1h" || r.next_cutoff?.band === "passed" ? "text-pex-block" : r.next_cutoff?.band === "1_to_3h" ? "text-pex-wait" : "")}>{r.next_cutoff?.time_left ?? "—"}</span> },
              { key: "o", header: "Open cases", render: (r) => r.open },
              { key: "a", header: "At risk", render: (r) => <span className={cn(r.at_risk > 0 && "text-pex-block font-semibold")}>{r.at_risk}</span> },
            ]} />
        </Card>

        <Card title="Today's outcomes">
          {o ? (
            <>
              <dl className="space-y-2.5 text-sm">
                <div className="flex justify-between"><dt>Executed by bank (confirmed)</dt><dd className="font-semibold">{o.executed_by_bank}</dd></div>
                <div className="flex justify-between"><dt>Handed to bank, awaiting confirmation</dt><dd className="font-semibold">{o.handed_to_bank_awaiting}</dd></div>
                <div className="flex justify-between"><dt>Resolved without manual repair, policy-approved</dt><dd className="font-semibold">{o.resolved_without_manual_repair ?? o.policy_approved ?? 0} of {o.resolved_total}</dd></div>
              </dl>
              <div className="mt-4 flex h-5 rounded-full overflow-hidden bg-slate-100 text-xs text-white font-semibold" role="img" aria-label={`${o.executed_by_bank} executed by bank, ${o.handed_to_bank_awaiting} awaiting bank confirmation`}>
                {o.executed_by_bank > 0 && <span className="bg-green-700 flex items-center justify-center" style={{ width: `${(o.executed_by_bank / total) * 100}%` }}>{o.executed_by_bank}</span>}
                {o.handed_to_bank_awaiting > 0 && <span className="bg-amber-500 flex items-center justify-center" style={{ width: `${(o.handed_to_bank_awaiting / total) * 100}%` }}>{o.handed_to_bank_awaiting}</span>}
              </div>
              <p className="mt-2 text-xs text-pex-muted">Only bank-confirmed outcomes count as executed. Bank communication is simulated in this build.{o.note ? ` ${o.note}` : ""}</p>
            </>
          ) : <p className="text-sm text-pex-muted">No outcome data yet.</p>}
        </Card>

        <Card title="Team workload">
          <DataTable caption="Team workload" rows={d.team_workload ?? []} rowKey={(r) => r.user_id}
            columns={[
              { key: "n", header: "Analyst", render: (r) => r.name },
              { key: "o", header: "Open", render: (r) => r.open },
              { key: "u", header: "Under 1h", render: (r) => <span className={cn(r.under_1h > 0 && "text-pex-block font-semibold")}>{r.under_1h}</span> },
              { key: "r", header: "Returned", render: (r) => r.returned },
              { key: "ol", header: "Oldest case", render: (r) => r.oldest ?? "—" },
              { key: "a", header: "", align: "right", render: (r) => r.can_reassign === false ? null : (
                <a className="text-pex-primary hover:underline" href={routes.worklist({ tab: "ready", scope: "all", assignee: r.user_id })}>Reassign</a>) },
            ]} />
        </Card>

        <Card title="Approver queue">
          <DataTable caption="Approver queue" rows={d.approver_queue ?? []} rowKey={(r) => r.user_id}
            columns={[
              { key: "n", header: "Approver", render: (r) => r.name },
              { key: "p", header: "Pending", render: (r) => r.pending },
              { key: "o", header: "Oldest case", render: (r) => r.oldest ?? "—" },
              { key: "a", header: "", align: "right", render: (r) => <a className="text-pex-primary hover:underline" href={routes.approvals({ approver: r.user_id })}>Open queue</a> },
            ]} />
          <p className="mt-3 pt-3 border-t border-surface-line text-xs text-pex-muted flex items-center gap-2"><Info className="w-4 h-4" aria-hidden />{d.compliance_note || "Compliance cases are managed in the Compliance workspace."}</p>
        </Card>
      </div>

      <Card title="Needs your decision">
        {(d.needs_decision ?? []).length === 0 ? <p className="text-sm text-pex-muted">Nothing needs a decision right now.</p> : (
          <ul className="divide-y divide-surface-line">
            {(d.needs_decision ?? []).map((n, i) => (
              <li key={i} className="grid grid-cols-[12rem_1fr_9rem] items-center gap-3 py-2.5 text-sm">
                <span className="font-medium">{n.case_id ?? n.kind.replace(/_/g, " ").toLowerCase()}</span>
                <span className={cn(n.kind === "STATUS_CHECK_OVERDUE" ? "text-pex-block" : "text-pex-wait", "font-medium")}>{n.title}</span>
                <span className="text-right"><button onClick={() => act(n)} className="px-3 py-1.5 text-sm rounded-lg border border-pex-primary text-pex-primary hover:bg-pex-primary-soft">{n.action?.label ?? "Open"}</button></span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
};
