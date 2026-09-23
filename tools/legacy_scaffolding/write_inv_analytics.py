import os

comp_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\src\components"

# 1. Investigations/InvestigationsHub.tsx
with open(os.path.join(comp_dir, "Investigations", "InvestigationsHub.tsx"), "w", encoding="utf-8") as f:
    f.write('''import React, { useState, useEffect } from "react";
import { AuditEvent } from "../../types";
import { fetchAuditStream } from "../../services/api";
import { Activity, ShieldCheck, Hash, Clock, RefreshCw, Key } from "lucide-react";

export const InvestigationsHub: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);

  const loadAuditStream = async () => {
    setLoading(true);
    try {
      const data = await fetchAuditStream();
      setEvents(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAuditStream();
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Investigations &amp; Operational Audit Hub</h1>
          <p className="text-xs text-slate-500 mt-1">Real-time immutable event stream with control trace tags and continuous SHA-256 provenance hashes</p>
        </div>
        <button
          onClick={loadAuditStream}
          className="px-3.5 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg text-xs font-semibold text-slate-700 flex items-center space-x-1.5 shadow-sm transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Stream</span>
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden divide-y divide-slate-100">
        {events.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400">Loading audit provenance events...</div>
        ) : (
          events.map((ev) => (
            <div key={ev.event_index} className="p-5 hover:bg-slate-50/70 transition-colors space-y-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center space-x-2.5">
                  <span className="w-6 h-6 rounded bg-slate-900 text-white font-mono text-[11px] font-bold flex items-center justify-center">
                    #{ev.event_index}
                  </span>
                  <span className="font-mono text-xs font-bold text-sky-700">{ev.case_id}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-100 text-slate-700">
                    {ev.stage_name}
                  </span>
                  <span className="font-bold text-xs text-slate-800">{ev.action_name}</span>
                </div>
                <div className="text-[11px] font-mono text-slate-400 flex items-center space-x-2">
                  <Clock className="w-3 h-3" />
                  <span>{new Date(ev.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>

              <p className="text-xs text-slate-600 pl-8">{ev.details}</p>

              <div className="pl-8 flex flex-wrap items-center gap-2 pt-1">
                <span className="text-[10px] text-slate-400 font-mono">Actor: {ev.actor_id} ({ev.actor_role})</span>
                {ev.control_tags.map((tag, i) => (
                  <span key={i} className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 text-[10px] font-mono border border-emerald-200">
                    ✓ {tag}
                  </span>
                ))}
              </div>

              <div className="pl-8 pt-1 text-[10px] font-mono text-slate-400 flex items-center space-x-2">
                <Hash className="w-3 h-3 text-slate-300" />
                <span className="truncate max-w-md">SHA-256: {ev.current_hash}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
''')

# 2. Analytics/OperationsAnalytics.tsx
with open(os.path.join(comp_dir, "Analytics", "OperationsAnalytics.tsx"), "w", encoding="utf-8") as f:
    f.write('''import React from "react";
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
''')

# 3. SwiftIso/SwiftIsoCenter.tsx
with open(os.path.join(comp_dir, "SwiftIso", "SwiftIsoCenter.tsx"), "w", encoding="utf-8") as f:
    f.write('''import React, { useState, useEffect } from "react";
import { fetchAdapters, testAdapter } from "../../services/api";
import { Network, Activity, Zap, CheckCircle2, RefreshCw } from "lucide-react";

export const SwiftIsoCenter: React.FC = () => {
  const [adapters, setAdapters] = useState<any[]>([]);
  const [testingId, setTestingId] = useState<string | null>(null);

  const loadAdapters = async () => {
    try {
      const data = await fetchAdapters();
      setAdapters(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadAdapters();
  }, []);

  const handleTest = async (adapterId: string) => {
    setTestingId(adapterId);
    try {
      await testAdapter(adapterId);
      await loadAdapters();
    } catch (err) {
      console.error(err);
    } finally {
      setTestingId(null);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">SWIFT &amp; ISO 20022 Integration Center</h1>
        <p className="text-xs text-slate-500 mt-1">Status and connectivity monitoring for clearing networks, payment hubs, and messaging rails</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {adapters.map((a) => (
          <div key={a.adapter_id} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] text-slate-400 uppercase">{a.protocol}</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {a.status}
                </span>
              </div>
              <h3 className="text-sm font-bold text-slate-900">{a.name}</h3>
              <p className="text-xs text-slate-500">{a.description}</p>
            </div>

            <div className="pt-3 border-t border-slate-100 space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-500 font-mono">
                <span>Latency: <strong className="text-slate-800">{a.latency_ms}ms</strong></span>
                <span className="text-[10px]">Tested: {a.last_tested.split(" ")[1] || "00:01:20"}</span>
              </div>

              <button
                onClick={() => handleTest(a.adapter_id)}
                disabled={testingId === a.adapter_id}
                className="w-full py-1.5 px-3 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 flex items-center justify-center space-x-1.5 transition-all"
              >
                {testingId === a.adapter_id ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5 text-sky-600" />}
                <span>Test Adapter Connectivity</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
''')
print("Wrote InvestigationsHub.tsx, OperationsAnalytics.tsx, and SwiftIsoCenter.tsx")
