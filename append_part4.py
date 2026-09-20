import os

dist_path = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\dist\index.html"

part4 = """
          {tab === "investigations" && (
            <div className="p-8 max-w-7xl mx-auto space-y-6">
              <div>
                <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Investigations & Operational Audit Hub</h1>
                <p className="text-xs text-slate-500 mt-1">Real-time immutable event stream with continuous SHA-256 provenance hashes</p>
              </div>

              <div className="bg-white rounded-2xl border shadow-sm divide-y">
                {auditEvents.map(ev => (
                  <div key={ev.event_index} className="p-5 hover:bg-slate-50 space-y-1.5">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center space-x-2">
                        <span className="w-6 h-6 rounded bg-slate-900 text-white font-mono text-[11px] font-bold flex items-center justify-center">#{ev.event_index}</span>
                        <span className="font-mono text-xs font-bold text-sky-700">{ev.case_id}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-100 text-slate-700">{ev.stage_name}</span>
                        <strong className="text-xs text-slate-800">{ev.action_name}</strong>
                      </div>
                      <span className="text-[11px] font-mono text-slate-400">{new Date(ev.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <p className="text-xs text-slate-600 pl-8">{ev.details}</p>
                    <div className="pl-8 flex gap-2 text-[10px] font-mono text-slate-400">
                      <span>Actor: {ev.actor_id} ({ev.actor_role})</span>
                      <span>• SHA-256: {ev.current_hash.slice(0, 24)}...</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === "analytics" && (
            <div className="p-8 max-w-7xl mx-auto space-y-6">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Operations Analytics & KPIs</h1>
              <div className="grid grid-cols-3 gap-5">
                <div className="bg-white p-5 rounded-xl border shadow-sm">
                  <span className="text-xs font-semibold text-slate-500 uppercase font-mono">TOTAL EXCEPTION VOLUME</span>
                  <div className="text-3xl font-bold text-slate-900 mt-2">{analytics?.total_cases || 18}</div>
                  <p className="text-[11px] text-emerald-600 mt-1">94.2% straight-through repair eligible</p>
                </div>
                <div className="bg-white p-5 rounded-xl border shadow-sm">
                  <span className="text-xs font-semibold text-slate-500 uppercase font-mono">SETTLED CONFIRMED</span>
                  <div className="text-3xl font-bold text-emerald-600 mt-2">$1,482,000.00</div>
                  <p className="text-[11px] text-slate-400 mt-1">Zero fails on simulated ledger</p>
                </div>
                <div className="bg-white p-5 rounded-xl border shadow-sm">
                  <span className="text-xs font-semibold text-slate-500 uppercase font-mono">AVG HUMAN TIME IN LOOP</span>
                  <div className="text-3xl font-bold text-sky-600 mt-2">42s</div>
                  <p className="text-[11px] text-slate-400 mt-1">Down from 18 mins manual query</p>
                </div>
              </div>
            </div>
          )}

          {tab === "swift_iso" && (
            <div className="p-8 max-w-7xl mx-auto space-y-6">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">SWIFT & ISO 20022 Integration Adapters</h1>
              <div className="grid grid-cols-3 gap-5">
                {adapters.map(a => (
                  <div key={a.adapter_id} className="bg-white p-5 rounded-2xl border shadow-sm space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="font-mono text-[10px] text-slate-400 uppercase">{a.protocol}</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-emerald-50 text-emerald-700 border border-emerald-200">{a.status}</span>
                    </div>
                    <h3 className="text-sm font-bold text-slate-900">{a.name}</h3>
                    <p className="text-xs text-slate-500">{a.description}</p>
                    <div className="text-xs font-mono text-slate-500 pt-2 border-t">Latency: <strong>{a.latency_ms}ms</strong></div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === "governance" && (
            <div className="p-8 max-w-7xl mx-auto space-y-6">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Controls & Governance Posture</h1>
              <div className="bg-white p-6 rounded-2xl border shadow-sm space-y-4">
                <h3 className="text-sm font-bold text-slate-900">Active Operational Guardrails</h3>
                <div className="divide-y">
                  {govData?.controls?.map((c, i) => (
                    <div key={i} className="py-3 flex justify-between items-center text-xs">
                      <div>
                        <strong className="block text-slate-900">{c.name}</strong>
                        <span className="text-slate-500">{c.description}</span>
                      </div>
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-emerald-50 text-emerald-700 border border-emerald-200">{c.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {tab === "ontology" && (
            <div className="p-8 max-w-7xl mx-auto space-y-6">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Payment Ontology & Architecture Pipeline</h1>
              <div className="bg-white p-6 rounded-2xl border shadow-sm space-y-4">
                <h3 className="text-sm font-bold text-slate-900">6-Stage Architecture Pipeline</h3>
                <div className="grid grid-cols-6 gap-3">
                  {pipeline.map(p => (
                    <div key={p.stage_id} className="p-4 bg-slate-50 border rounded-xl space-y-1">
                      <div className="w-6 h-6 rounded bg-sky-600 text-white font-mono text-xs font-bold flex items-center justify-center">{p.stage_id}</div>
                      <h4 className="text-xs font-bold text-slate-900">{p.name}</h4>
                      <p className="text-[11px] text-slate-500">{p.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {tab === "copilot" && (
            <div className="p-8 max-w-7xl mx-auto space-y-6">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">AI Repair Copilot & SOP Knowledge Base</h1>
              <div className="grid grid-cols-3 gap-6">
                <div className="space-y-3">
                  <span className="text-xs font-bold text-slate-500 font-mono">INSTITUTIONAL SOPS</span>
                  {sops.map(s => (
                    <div key={s.sop_id} className="bg-white p-4 rounded-xl border shadow-sm space-y-1">
                      <div className="flex justify-between font-mono text-xs text-sky-700 font-bold">
                        <span>{s.sop_id}</span>
                        <span className="text-[10px] text-slate-400">{s.category}</span>
                      </div>
                      <h4 className="text-xs font-semibold text-slate-900">{s.title}</h4>
                      <p className="text-[11px] text-slate-500">{s.summary}</p>
                    </div>
                  ))}
                </div>

                <div className="bg-white rounded-2xl border shadow-sm col-span-2 flex flex-col h-[520px] overflow-hidden">
                  <div className="p-4 border-b bg-slate-50/50 flex justify-between items-center text-xs font-bold text-slate-800">
                    <span>PeX Governed Assistant</span>
                    <span className="text-[10px] font-mono bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded border border-emerald-200">PII SHIELD ACTIVE</span>
                  </div>
                  <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {chatMessages.map((m, i) => (
                      <div key={i} className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}>
                        <div className={`max-w-lg p-3.5 rounded-2xl text-xs ${m.sender === "user" ? "bg-sky-600 text-white" : "bg-slate-100 text-slate-800"}`}>
                          {m.text}
                        </div>
                      </div>
                    ))}
                  </div>
                  <form onSubmit={handleChatSend} className="p-3 border-t flex gap-2">
                    <input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)} placeholder="Ask Copilot about IBAN repair or SOP guidelines..." className="flex-1 px-3 py-2 text-xs bg-slate-50 border rounded-xl" />
                    <button type="submit" className="px-4 py-2 bg-sky-600 text-white rounded-xl text-xs font-bold">Send</button>
                  </form>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Persona Switcher Modal */}
      {isPersonaModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden">
            <div className="bg-slate-900 px-6 py-5 text-white flex justify-between items-center">
              <div>
                <h2 className="text-lg font-semibold">Institutional Persona Switcher</h2>
                <p className="text-xs text-slate-400">Select an authenticated banking role to test RBAC rules</p>
              </div>
              <button onClick={() => setIsPersonaModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <div className="p-6 grid grid-cols-2 gap-3.5">
              {personas.map(p => (
                <div
                  key={p.user_id}
                  onClick={() => { setCurrentPersona(p); setIsPersonaModalOpen(false); }}
                  className={`p-4 rounded-xl border cursor-pointer hover:bg-slate-50 ${currentPersona?.user_id === p.user_id ? "border-sky-500 bg-sky-50" : "border-slate-200"}`}
                >
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-slate-900">{p.name}</h4>
                    {currentPersona?.user_id === p.user_id && <span className="text-xs text-sky-600 font-bold">Active</span>}
                  </div>
                  <p className="text-xs text-slate-500 font-medium">{p.title}</p>
                  <div className="mt-2 flex justify-between text-[11px] text-slate-400 border-t pt-1.5 font-mono">
                    <span>{p.user_id}</span>
                    <span>{p.max_approval_amount > 0 ? `Limit: $${(p.max_approval_amount / 1000).toFixed(0)}k` : "Maker Only"}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
</script>
</body>
</html>
"""

with open(dist_path, "a", encoding="utf-8") as f:
    f.write(part4)

print("Finished writing complete frontend/dist/index.html")
