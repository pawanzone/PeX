import React, { useState, useEffect } from "react";
import { fetchGovernanceControls, verifyAuditChain } from "../../services/api";
import { ShieldCheck, Lock, Hash, CheckCircle2, RefreshCw, AlertOctagon } from "lucide-react";

export const ControlsGovernance: React.FC = () => {
  const [govData, setGovData] = useState<any>(null);
  const [verifyResult, setVerifyResult] = useState<any>(null);
  const [verifying, setVerifying] = useState(false);

  const loadData = async () => {
    try {
      const data = await fetchGovernanceControls();
      setGovData(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleVerifyChain = async () => {
    setVerifying(true);
    try {
      const res = await verifyAuditChain();
      setVerifyResult(res);
      await loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Institutional Controls &amp; Governance</h1>
        <p className="text-xs text-slate-500 mt-1">Active guardrails, zero-trust boundaries, AI safety postures, and cryptographic proof of integrity</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm lg:col-span-2 space-y-4">
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Active Operational Guardrails</h3>
          <div className="divide-y divide-slate-100">
            {govData?.controls?.map((c: any, i: number) => (
              <div key={i} className="py-3.5 flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <strong className="text-xs text-slate-900 font-semibold">{c.name}</strong>
                  <p className="text-xs text-slate-500">{c.description}</p>
                </div>
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono shrink-0 border ${
                  c.status === "ENFORCED" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-amber-50 text-amber-700 border-amber-200"
                }`}>
                  {c.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 tracking-tight flex items-center space-x-2">
              <Hash className="w-4 h-4 text-sky-600" />
              <span>SHA-256 Provenance Proof</span>
            </h3>
            <p className="text-xs text-slate-500">
              PeX enforces continuous hash chaining across all 20 lifecycle stages. Any unauthorized ledger tampering breaks the chain head.
            </p>

            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 font-mono text-[10px] text-slate-700 break-all space-y-1">
              <span className="text-slate-400 block font-sans text-[10px] font-bold">LATEST PROVENANCE HEAD:</span>
              <div>{govData?.continuous_audit?.latest_head_hash || "00000000000000000000000000000000"}</div>
            </div>

            {verifyResult && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 font-semibold flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Chain Verified Intact! ({verifyResult.total_events_checked} events recomputed)</span>
              </div>
            )}

            <button
              onClick={handleVerifyChain}
              disabled={verifying}
              className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${verifying ? "animate-spin" : ""}`} />
              <span>Recompute Cryptographic Hash Chain</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
