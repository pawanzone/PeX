import os

dist_path = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\dist\index.html"

part2 = """
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 h-screen sticky top-0 select-none">
        <div className="h-14 flex items-center px-6 border-b border-slate-800 space-x-3">
          <div className="w-7 h-7 rounded-lg bg-sky-500 flex items-center justify-center text-white font-bold font-mono text-sm shadow-md">
            P
          </div>
          <h1 className="text-sm font-bold text-white tracking-wider flex items-center space-x-1.5">
            <span>PeX Platform</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-400 font-mono">v1.0</span>
          </h1>
        </div>

        <div className="flex-1 overflow-y-auto py-4 px-3 space-y-5 text-xs">
          <div className="space-y-1">
            <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">OVERVIEW</span>
            <button onClick={() => setTab("command_center")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "command_center" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
              Command Center
            </button>
          </div>

          <div className="space-y-1">
            <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">EXCEPTION OPERATIONS</span>
            <button onClick={() => setTab("intake")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "intake" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
              Payment Intake
            </button>
            <button onClick={() => setTab("worklist")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "worklist" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
              Exception Worklist
            </button>
            <button onClick={() => setTab("approvals")} className={`w-full flex items-center justify-between px-3 py-2 rounded-lg font-semibold transition-all ${tab === "approvals" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
              <span>Role Approvals</span>
              <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-sky-500/20 text-sky-400 font-mono">
                {cases.filter(c => c.status === "PENDING_APPROVAL" || c.status === "AWAITING_SECOND_APPROVAL").length}
              </span>
            </button>
            <button onClick={() => setTab("investigations")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "investigations" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
              Investigations Hub
            </button>
          </div>

          <div className="space-y-1">
            <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">INTELLIGENCE & CONNECTIVITY</span>
            <button onClick={() => setTab("analytics")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "analytics" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
              Operations Analytics
            </button>
            <button onClick={() => setTab("swift_iso")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "swift_iso" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
              SWIFT & ISO Center
            </button>
            <button onClick={() => setTab("ontology")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "ontology" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
              Payment Ontology
            </button>
            <button onClick={() => setTab("copilot")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "copilot" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
              AI Repair Copilot
            </button>
          </div>

          <div className="space-y-1">
            <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">CONFIGURE & GOVERN</span>
            <button onClick={() => setTab("governance")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "governance" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
              Controls & Governance
            </button>
          </div>
        </div>

        <div className="p-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
          <span>ISO 20022 / CBPR+</span>
          <span className="text-emerald-400 font-mono flex items-center space-x-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>ONLINE</span>
          </span>
        </div>
      </aside>

      {/* Main Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 sticky top-0 z-30">
          <div className="text-xs font-semibold text-slate-600">
            Institutional Banking Platform • <span className="text-slate-400 font-normal">Deterministic Mock Mode</span>
          </div>

          <div className="flex items-center space-x-4">
            <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 bg-amber-50 border border-amber-200 rounded-md text-[11px] font-medium text-amber-700">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
              <span>DEMO • NO BANK TRAFFIC</span>
            </div>

            {currentPersona && (
              <button
                onClick={() => setIsPersonaModalOpen(true)}
                className="flex items-center space-x-2.5 pl-2 pr-3 py-1 rounded-lg border border-slate-200 hover:border-slate-300 bg-slate-50 hover:bg-slate-100 transition-all text-left"
              >
                <div className="w-7 h-7 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-bold font-mono">
                  {currentPersona.avatar_initials}
                </div>
                <div className="hidden md:block">
                  <div className="text-xs font-semibold text-slate-800 leading-tight">
                    {currentPersona.name} <span className="text-[10px] text-slate-400 font-mono">({currentPersona.user_id})</span>
                  </div>
                  <div className="text-[10px] text-slate-500 font-medium">{currentPersona.title}</div>
                </div>
              </button>
            )}
          </div>
        </header>

        {/* Dynamic Main Body Content */}
        <main className="flex-1 overflow-y-auto">
          {tab === "command_center" && (
            <div className="p-8 space-y-8 max-w-7xl mx-auto">
              <div className="flex justify-between items-center">
                <div>
                  <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Command Center</h1>
                  <p className="text-xs text-slate-500 mt-1">Global operational intelligence, exception telemetry & SLA breach risk</p>
                </div>
                <div className="text-xs font-mono bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm">
                  CYCLE DATE: <strong className="text-slate-800">{analytics?.processing_date || "2026-08-24"}</strong>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                  <span className="text-xs font-semibold text-slate-500 uppercase font-mono">OPEN CASES</span>
                  <div className="mt-3 text-3xl font-bold text-slate-900">{analytics?.open_cases || 0}</div>
                  <div className="mt-1 text-[11px] text-slate-400">Live tenant-scoped exceptions</div>
                </div>

                <div className="bg-white p-5 rounded-xl border border-red-200 shadow-sm bg-gradient-to-br from-white to-red-50/20">
                  <span className="text-xs font-semibold text-red-600 uppercase font-mono">AT-RISK VALUE</span>
                  <div className="mt-3 text-3xl font-bold text-red-600">
                    ${(analytics?.at_risk_value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div className="mt-1 text-[11px] text-red-500/80">Pending human review</div>
                </div>

                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                  <span className="text-xs font-semibold text-slate-500 uppercase font-mono">RESOLUTION RATE</span>
                  <div className="mt-3 text-3xl font-bold text-emerald-600">{analytics?.resolution_rate || 0}%</div>
                  <div className="mt-2 w-full bg-slate-100 rounded-full h-1.5">
                    <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${analytics?.resolution_rate || 0}%` }}></div>
                  </div>
                </div>

                <div className="bg-white p-5 rounded-xl border border-amber-200 shadow-sm bg-gradient-to-br from-white to-amber-50/20">
                  <span className="text-xs font-semibold text-amber-600 uppercase font-mono">DUE &lt; 1HR</span>
                  <div className="mt-3 text-3xl font-bold text-amber-600">{analytics?.due_under_1hr || 0}</div>
                  <div className="mt-1 text-[11px] text-amber-600/80">SLA breaches pending mitigation</div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
                  <h3 className="text-sm font-bold text-slate-900">Queue Distribution</h3>
                  <div className="space-y-3 text-xs">
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>Repair Queue</span>
                        <span className="font-mono font-bold text-sky-600">{analytics?.queue_distribution?.Repair || 0}</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2">
                        <div className="bg-sky-500 h-2 rounded-full" style={{ width: "65%" }}></div>
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>Compliance & Sanctions</span>
                        <span className="font-mono font-bold text-amber-600">{analytics?.queue_distribution?.Compliance || 0}</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2">
                        <div className="bg-amber-500 h-2 rounded-full" style={{ width: "30%" }}></div>
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>Investigation & Duplicates</span>
                        <span className="font-mono font-bold text-purple-600">{analytics?.queue_distribution?.Investigation || 0}</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2">
                        <div className="bg-purple-500 h-2 rounded-full" style={{ width: "25%" }}></div>
                      </div>
                    </div>
                  </div>
                  <button onClick={() => setTab("worklist")} className="w-full py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 transition-all">
                    View Full Exception Worklist &rarr;
                  </button>
                </div>

                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm lg:col-span-2 space-y-4">
                  <h3 className="text-sm font-bold text-slate-900">SLA Resolution Velocity (24h)</h3>
                  <div className="h-40 flex items-end justify-between gap-3 pt-4 border-b border-slate-100 px-2">
                    {velocity.map((v, i) => (
                      <div key={i} className="flex-1 flex flex-col items-center gap-2 h-full justify-end">
                        <div className="w-full flex items-end justify-center gap-1.5 h-28">
                          <div className="w-4 bg-sky-500 rounded-t" style={{ height: `${Math.max(v.opened * 16, 6)}px` }}></div>
                          <div className="w-4 bg-emerald-500 rounded-t" style={{ height: `${Math.max(v.resolved * 16, 4)}px` }}></div>
                        </div>
                        <span className="text-[11px] font-mono text-slate-500">{v.day}</span>
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-between text-xs text-slate-500">
                    <span>Peak throughput: <strong>12 items / hr</strong></span>
                    <span>Auto-Repair Target: <strong className="text-emerald-600">&lt; 15 mins</strong></span>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="p-5 border-b border-slate-100 flex justify-between items-center">
                  <h3 className="text-sm font-bold text-slate-900">Active High-Priority Exceptions</h3>
                  <button onClick={() => setTab("approvals")} className="text-xs font-semibold text-sky-600 hover:text-sky-700">
                    Open Approvals Desk &rarr;
                  </button>
                </div>
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase font-mono text-[10px] border-b border-slate-200">
                    <tr>
                      <th className="px-5 py-3">Case ID</th>
                      <th className="px-4 py-3">Counterparty</th>
                      <th className="px-4 py-3">Exception Reason</th>
                      <th className="px-4 py-3">Amount</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-5 py-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {cases.slice(0, 5).map(c => (
                      <tr key={c.case_id} className="hover:bg-slate-50/60">
                        <td className="px-5 py-3.5 font-mono font-semibold text-sky-700">{c.case_id}</td>
                        <td className="px-4 py-3.5 font-medium text-slate-900">{c.creditor_party?.party_name}</td>
                        <td className="px-4 py-3.5 text-slate-600 truncate max-w-xs">{c.reason}</td>
                        <td className="px-4 py-3.5 font-mono font-bold text-slate-900">{c.currency} {c.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                        <td className="px-4 py-3.5">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-amber-50 text-amber-700 border border-amber-200">
                            {c.status}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <button onClick={() => { setSelectedCaseId(c.case_id); loadCaseDetail(c.case_id); setTab("approvals"); }} className="px-2.5 py-1 bg-sky-50 text-sky-700 hover:bg-sky-100 rounded-md font-semibold text-xs">
                            Review &rarr;
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
"""

with open(dist_path, "a", encoding="utf-8") as f:
    f.write(part2)

print("Appended part 2.")
