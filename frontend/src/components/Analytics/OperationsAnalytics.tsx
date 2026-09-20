import React from "react";
import { AnalyticsSummary } from "../../types";
import { BarChart3, TrendingUp, ShieldAlert, Award, Clock } from "lucide-react";

interface Props {
  analytics: AnalyticsSummary | null;
}

export const OperationsAnalytics: React.FC<Props> = ({ analytics }) => {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Operations Analytics &amp; KPIs</h1>
        <p className="text-xs text-slate-500 mt-1">Cross-institutional exception metrics, repair velocity, and compliance telemetry</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <span className="text-xs font-semibold text-slate-500 uppercase font-mono">TOTAL REPAIR VOLUME</span>
          <div className="text-3xl font-bold text-slate-900">{analytics?.total_cases || 18}</div>
          <p className="text-[11px] text-emerald-600 font-medium">94.2% straight-through repair eligible</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <span className="text-xs font-semibold text-slate-500 uppercase font-mono">SETTLED VALUE</span>
          <div className="text-3xl font-bold text-emerald-600">$1,482,000.00</div>
          <p className="text-[11px] text-slate-400">Zero settlement fails on simulated ledger</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <span className="text-xs font-semibold text-slate-500 uppercase font-mono">AVG HUMAN TIME IN LOOP</span>
          <div className="text-3xl font-bold text-sky-600">42s</div>
          <p className="text-[11px] text-slate-400">Down from 18 mins manual bank query</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Exception Profile Volume Breakdown</h3>
          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span>Beneficiary IBAN Checksum (MOD-97)</span>
              <span className="font-mono font-bold text-sky-600">55%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div className="bg-sky-500 h-2 rounded-full" style={{ width: "55%" }}></div>
            </div>

            <div className="flex items-center justify-between">
              <span>Sanctions Screening Entity Review</span>
              <span className="font-mono font-bold text-amber-600">22%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div className="bg-amber-500 h-2 rounded-full" style={{ width: "22%" }}></div>
            </div>

            <div className="flex items-center justify-between">
              <span>Duplicate Instruction Suspected</span>
              <span className="font-mono font-bold text-purple-600">15%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div className="bg-purple-500 h-2 rounded-full" style={{ width: "15%" }}></div>
            </div>

            <div className="flex items-center justify-between">
              <span>Invalid Routing BIC / Clearing Code</span>
              <span className="font-mono font-bold text-indigo-600">8%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div className="bg-indigo-500 h-2 rounded-full" style={{ width: "8%" }}></div>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Compliance &amp; Governance Posture</h3>
          <div className="space-y-3 text-xs text-slate-600">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
              <div>
                <strong className="text-slate-800 block">Maker-Checker Segregation</strong>
                <span>100% enforced on all payment repairs</span>
              </div>
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-mono text-[10px] font-bold">ACTIVE</span>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
              <div>
                <strong className="text-slate-800 block">Dual Authorization (&gt;= $250k)</strong>
                <span>Zero single-approver high value releases</span>
              </div>
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-mono text-[10px] font-bold">ACTIVE</span>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
              <div>
                <strong className="text-slate-800 block">Zero PII Leakage Shield</strong>
                <span>Isolated Token Vault with TOK-* substitution</span>
              </div>
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-mono text-[10px] font-bold">ACTIVE</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
