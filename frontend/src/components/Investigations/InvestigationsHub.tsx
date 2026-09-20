import React, { useState, useEffect } from "react";
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
