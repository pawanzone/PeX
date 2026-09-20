import React, { useState, useEffect } from "react";
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
