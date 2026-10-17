import React from "react";
import { StatusBadge } from "../common/StatusBadge";
import { NotMeasured, MeasuredValue } from "../common/NotMeasured";
import { EmptyState } from "../common/States";
import { isTerminal } from "../../lib/statusMeta";
import { AnalyticsSummary, PeXCase } from "../../types";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  TrendingUp,
  ArrowRight,
  ShieldCheck,
  Zap,
} from "lucide-react";

interface Props {
  analytics: AnalyticsSummary | null;
  velocity: Array<{ day: string; opened: number; resolved: number }>;
  cases: PeXCase[];
  onNavigateTab: (tab: any) => void;
  onSelectCase: (caseId: string) => void;
}

export const CommandCenter: React.FC<Props> = ({
  analytics,
  velocity,
  cases,
  onNavigateTab,
  onSelectCase,
}) => {
  const atRiskCases = cases.filter((c) => !isTerminal(c.status)).slice(0, 5);
  const q = analytics?.queue_distribution ?? {};
  const qMax = Math.max(1, q.Repair || 0, q.Compliance || 0, q.Investigation || 0);
  const pct = (n?: number) => `${Math.round(((n || 0) / qMax) * 100)}%`;

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Command Center</h1>
          <p className="text-xs text-slate-500 mt-1">Global operational intelligence, exception telemetry & SLA breach risk</p>
        </div>
        <div className="flex items-center space-x-3 text-xs">
          <div className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg shadow-sm">
            <span className="text-slate-400 font-mono">TENANT:</span> <span className="font-semibold text-slate-800">DEMO TENANT</span>
          </div>
          <div className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg shadow-sm">
            <span className="text-slate-400 font-mono">CYCLE DATE:</span> <span className="font-semibold text-slate-800">{analytics?.processing_date || "n/a"}</span>
          </div>
        </div>
      </div>

      {/* KPI Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase font-mono">OPEN CASES</span>
            <span className="p-1.5 bg-sky-50 text-sky-600 rounded-md"><TrendingUp className="w-4 h-4" /></span>
          </div>
          <div className="mt-3 text-3xl font-bold text-slate-900">{analytics?.open_cases || 0}</div>
          <div className="mt-1 text-[11px] text-slate-400">Live tenant-scoped exceptions</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-red-200/80 shadow-sm relative overflow-hidden bg-gradient-to-br from-white to-red-50/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-red-600 uppercase font-mono">AT-RISK VALUE</span>
            <span className="p-1.5 bg-red-50 text-red-600 rounded-md"><AlertTriangle className="w-4 h-4" /></span>
          </div>
          <div className="mt-3 text-3xl font-bold text-red-600">
            {(analytics?.at_risk_value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="mt-1 text-[11px] text-red-500/80">Open value, all currencies, not converted</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase font-mono">RESOLUTION RATE</span>
            <span className="p-1.5 bg-emerald-50 text-emerald-600 rounded-md"><CheckCircle2 className="w-4 h-4" /></span>
          </div>
          <div className="mt-3 text-3xl font-bold text-emerald-600">
            <MeasuredValue measured={analytics?.measured} value={`${analytics?.resolution_rate || 0}%`} />
          </div>
          {analytics?.measured && (
            <div className="mt-2 w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${analytics?.resolution_rate || 0}%` }}></div>
            </div>
          )}
        </div>

        <div className="bg-white p-5 rounded-xl border border-amber-200/80 shadow-sm relative overflow-hidden bg-gradient-to-br from-white to-amber-50/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-amber-600 uppercase font-mono">DUE &lt; 1HR</span>
            <span className="p-1.5 bg-amber-50 text-amber-600 rounded-md"><Clock className="w-4 h-4" /></span>
          </div>
          <div className="mt-3 text-3xl font-bold text-amber-600">{analytics?.due_under_1hr || 0}</div>
          <div className="mt-1 text-[11px] text-amber-600/80">SLA breaches pending mitigation</div>
        </div>
      </div>

      {/* Main Grid: Queue Distribution & Velocity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5">
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Queue Distribution</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs font-medium mb-1.5">
                <span className="text-slate-700">Repair Queue</span>
                <span className="font-mono font-bold text-sky-600">{analytics?.queue_distribution?.Repair || 0}</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div className="bg-sky-500 h-2 rounded-full" style={{ width: pct(q.Repair) }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium mb-1.5">
                <span className="text-slate-700">Compliance &amp; Sanctions</span>
                <span className="font-mono font-bold text-amber-600">{analytics?.queue_distribution?.Compliance || 0}</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div className="bg-amber-500 h-2 rounded-full" style={{ width: pct(q.Compliance) }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium mb-1.5">
                <span className="text-slate-700">Investigation &amp; Duplicates</span>
                <span className="font-mono font-bold text-purple-600">{analytics?.queue_distribution?.Investigation || 0}</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div className="bg-purple-500 h-2 rounded-full" style={{ width: pct(q.Investigation) }}></div>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100">
            <button
              onClick={() => onNavigateTab("worklist")}
              className="w-full py-2 px-4 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 flex items-center justify-center space-x-2 transition-all"
            >
              <span>View Full Exception Worklist</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 tracking-tight">SLA Resolution Velocity (24h)</h3>
            {!analytics?.measured && <span title="Demo data, not computed from bank outcomes" className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 cursor-help">DEMO DATA</span>}
            <div className="flex items-center space-x-4 text-xs">
              <span className="flex items-center space-x-1.5 text-sky-600 font-medium">
                <span className="w-2.5 h-2.5 rounded-sm bg-sky-500"></span>
                <span>Opened</span>
              </span>
              <span className="flex items-center space-x-1.5 text-emerald-600 font-medium">
                <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500"></span>
                <span>Resolved</span>
              </span>
            </div>
          </div>

          <div className="h-44 flex items-end justify-between gap-3 pt-6 px-2 border-b border-slate-100">
            {velocity.map((v, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-2 h-full justify-end">
                <div className="w-full flex items-end justify-center gap-1.5 h-32">
                  <div
                    className="w-4 bg-sky-500/90 rounded-t transition-all hover:bg-sky-600"
                    style={{ height: `${Math.max(v.opened * 18, 6)}px` }}
                    title={`Opened: ${v.opened}`}
                  ></div>
                  <div
                    className="w-4 bg-emerald-500/90 rounded-t transition-all hover:bg-emerald-600"
                    style={{ height: `${Math.max(v.resolved * 18, 4)}px` }}
                    title={`Resolved: ${v.resolved}`}
                  ></div>
                </div>
                <span className="text-[11px] font-mono text-slate-500">{v.day}</span>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
            <span>Peak throughput: <NotMeasured /></span>
            <span>Auto-repair SLA target: <NotMeasured /></span>
          </div>
        </div>
      </div>

      {/* Priority Action Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 tracking-tight">Active SLA Breach Mitigation Queue</h3>
            <p className="text-xs text-slate-500">Highest value and time-sensitive payment exceptions</p>
          </div>
          <button
            onClick={() => onNavigateTab("approvals")}
            className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center space-x-1"
          >
            <span>Open Approvals Desk</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 text-slate-500 uppercase font-mono text-[10px] border-b border-slate-200">
              <tr>
                <th className="px-5 py-3">Case Ref</th>
                <th className="px-4 py-3">Counterparty</th>
                <th className="px-4 py-3">Exception Reason</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Model confidence</th>
                <th className="px-5 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {atRiskCases.map((c) => (
                <tr key={c.case_id} className="hover:bg-slate-50/60 transition-colors">
                  <td className="px-5 py-3.5 font-mono font-semibold text-sky-700">{c.case_id}</td>
                  <td className="px-4 py-3.5 font-medium text-slate-900">{c.creditor_party?.party_name}</td>
                  <td className="px-4 py-3.5 text-slate-600 max-w-xs truncate" title={c.reason}>{c.reason}</td>
                  <td className="px-4 py-3.5 font-mono font-semibold text-slate-900">
                    {c.currency} {c.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-4 py-3.5">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-3.5 font-mono text-slate-700 font-semibold">
                    {c.ai_confidence ? `${(c.ai_confidence * 100).toFixed(0)}%` : "n/a"}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <button
                      onClick={() => {
                        onSelectCase(c.case_id);
                        onNavigateTab("approvals");
                      }}
                      className="px-2.5 py-1 bg-sky-50 text-sky-700 hover:bg-sky-100 rounded-md font-semibold text-xs transition-colors"
                    >
                      Review &rarr;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {atRiskCases.length === 0 && <EmptyState title="No open cases" hint="Generate a demo batch to populate the queues." />}
        </div>
      </div>
    </div>
  );
};
