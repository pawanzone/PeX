import React from "react";
import { AnalyticsSummary, SummaryCounts } from "../../types";
import { NotMeasured, MeasuredValue } from "../common/NotMeasured";
import { statusMeta } from "../../lib/statusMeta";

interface Props {
  analytics: AnalyticsSummary | null;
  counts?: SummaryCounts | null;
}

const BAR_COLORS = ["bg-sky-500", "bg-amber-500", "bg-purple-500", "bg-indigo-500", "bg-emerald-500", "bg-slate-400"];

const Distribution: React.FC<{ title: string; data?: Record<string, number>; labelFor?: (k: string) => string }> = ({ title, data, labelFor }) => {
  const entries = Object.entries(data ?? {}).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const total = entries.reduce((a, [, v]) => a + v, 0);
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
      <h3 className="text-sm font-bold text-slate-900 tracking-tight">{title}</h3>
      {entries.length === 0 ? (
        <p className="text-xs text-slate-400">No data yet.</p>
      ) : (
        <div className="space-y-3 text-xs">
          {entries.map(([k, v], i) => (
            <div key={k}>
              <div className="flex items-center justify-between mb-1">
                <span>{labelFor ? labelFor(k) : k.replace(/_/g, " ")}</span>
                <span className="font-mono font-bold text-slate-700">{v.toLocaleString()} <span className="text-slate-400 font-normal">({Math.round((v / total) * 100)}%)</span></span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div className={`${BAR_COLORS[i % BAR_COLORS.length]} h-2 rounded-full`} style={{ width: `${(v / total) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export const OperationsAnalytics: React.FC<Props> = ({ analytics, counts }) => {
  const total = counts?.total ?? analytics?.total_cases;
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Operations Analytics</h1>
        <p className="text-xs text-slate-500 mt-1">Counts come from the case store. Outcome metrics stay "Not measured" until real bank outcomes are connected.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <span className="text-xs font-semibold text-slate-500 uppercase font-mono">Total cases</span>
          <div className="text-3xl font-bold text-slate-900">{total !== undefined ? total.toLocaleString() : "n/a"}</div>
          <p className="text-[11px] text-slate-400">Counted from the case store</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <span className="text-xs font-semibold text-slate-500 uppercase font-mono">STP rate</span>
          <div className="text-3xl font-bold"><MeasuredValue measured={analytics?.measured} value={`${analytics?.resolution_rate ?? 0}%`} className="text-slate-900" /></div>
          <p className="text-[11px] text-slate-400">Share resolved without manual touch</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <span className="text-xs font-semibold text-slate-500 uppercase font-mono">Avg resolution time</span>
          <div className="text-3xl font-bold"><NotMeasured /></div>
          <p className="text-[11px] text-slate-400">Needs bank-confirmed outcomes</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <span className="text-xs font-semibold text-slate-500 uppercase font-mono">Estimated savings</span>
          <div className="text-3xl font-bold"><NotMeasured /></div>
          <p className="text-[11px] text-slate-400">Needs client cost baseline</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Distribution title="Cases by exception type" data={counts?.by_profile} />
        <Distribution title="Cases by state" data={counts?.by_status} labelFor={(k) => statusMeta(k).label} />
        <Distribution title="Cases by queue" data={counts?.by_queue} />
        <Distribution title="Cases by rail" data={counts?.by_rail} />
      </div>

      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
        <h3 className="text-sm font-bold text-slate-900 tracking-tight">Control design</h3>
        <p className="text-xs text-slate-500">Controls PeX is designed to apply. Enforcement evidence is in Controls &amp; Governance and the audit chain.</p>
        <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-5">
          <li>Maker-checker: the creator of a case cannot approve it.</li>
          <li>Dual authorisation above the configured amount threshold.</li>
          <li>Party data is tokenised before any language model sees a case.</li>
          <li>PeX never executes or settles payments. The bank does.</li>
        </ul>
      </div>
    </div>
  );
};
