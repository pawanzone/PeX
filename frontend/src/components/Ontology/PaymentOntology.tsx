import React, { useState, useEffect } from "react";
import { fetchOntologyPipeline, fetchOntologyEntities } from "../../services/api";
import { GitFork, Layers, Database, ArrowRight, Shield } from "lucide-react";

export const PaymentOntology: React.FC = () => {
  const [pipeline, setPipeline] = useState<any[]>([]);
  const [entities, setEntities] = useState<any[]>([]);

  useEffect(() => {
    fetchOntologyPipeline().then(setPipeline);
    fetchOntologyEntities().then(setEntities);
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Payment Ontology &amp; Architecture Pipeline</h1>
        <p className="text-xs text-slate-500 mt-1">Bank-agnostic canonical entities, ISO 20022 schemas, and zero-trust stage transitions</p>
      </div>

      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 tracking-tight">6-Stage Governed Architecture Pipeline</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          {pipeline.map((p) => (
            <div key={p.stage_id} className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2 relative">
              <div className="w-6 h-6 rounded bg-sky-600 text-white font-mono text-xs font-bold flex items-center justify-center">
                {p.stage_id}
              </div>
              <h4 className="text-xs font-bold text-slate-900">{p.name}</h4>
              <p className="text-[11px] text-slate-500 leading-snug">{p.description}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 tracking-tight">7 Core Canonical Domain Entities</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 text-slate-500 uppercase font-mono text-[10px] border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">Canonical Entity</th>
                <th className="px-4 py-3">Standard Alignment</th>
                <th className="px-4 py-3">Schema Attributes &amp; Lineage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {entities.map((e, idx) => (
                <tr key={idx} className="hover:bg-slate-50/60">
                  <td className="px-4 py-3 font-mono font-bold text-sky-700">{e.entity}</td>
                  <td className="px-4 py-3 font-medium text-slate-900">{e.standard}</td>
                  <td className="px-4 py-3 font-mono text-slate-600">{e.fields}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
