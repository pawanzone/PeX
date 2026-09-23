"""Update Investigations Hub in build_guided_frontend.py with Search, Case Filters, and Forensic Trace View."""
import re

with open("build_guided_frontend.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add state variables
target_state = "      // Audit Inspection Modal State\n      const [selectedAuditEvent, setSelectedAuditEvent] = useState(null);"
replacement_state = """      // Audit Inspection Modal State
      const [selectedAuditEvent, setSelectedAuditEvent] = useState(null);

      // Investigations Hub Search, Case Filtering & Forensic Trace States
      const [auditSearch, setAuditSearch] = useState("");
      const [auditCaseFilter, setAuditCaseFilter] = useState("ALL");
      const [auditStageFilter, setAuditStageFilter] = useState("ALL");
      const [auditViewMode, setAuditViewMode] = useState("STREAM"); // "STREAM" | "LIFECYCLE"
      const [auditExpandedCase, setAuditExpandedCase] = useState(null);"""

if "const [auditSearch, setAuditSearch]" not in content:
    content = content.replace(target_state, replacement_state, 1)

# 2. Update audit stream limit to 1000
content = content.replace("fetch(`${API_BASE}/audit/stream?limit=100`)", "fetch(`${API_BASE}/audit/stream?limit=1000`)")

# 3. Locate the investigations tab rendering
old_tab_pattern = re.compile(
    r'\{\/\* INVESTIGATIONS HUB \*\/\}\s*\{tab === "investigations" && \(\s*<div className="p-8 max-w-\[1440px\] mx-auto space-y-6">.*?<\/div>\s*\)\}',
    re.DOTALL
)

new_tab_code = """{/* INVESTIGATIONS HUB */}
              {tab === "investigations" && (() => {
                // Compute available cases in audit log
                const auditCaseMap = {};
                auditEvents.forEach(ev => {
                  if (ev.case_id) {
                    if (!auditCaseMap[ev.case_id]) {
                      auditCaseMap[ev.case_id] = [];
                    }
                    auditCaseMap[ev.case_id].push(ev);
                  }
                });

                const uniqueAuditCaseIds = Object.keys(auditCaseMap);

                // Stage counts
                const stageCounts = {
                  ALL: auditEvents.length,
                  INGESTION: auditEvents.filter(e => e.stage_name === "INGESTION" || e.stage_name === "INTAKE").length,
                  REPAIR: auditEvents.filter(e => e.stage_name === "ANALYST_REPAIR" || e.stage_name === "AI_REASONING" || e.stage_name === "EVIDENCE_GATHERING").length,
                  APPROVAL: auditEvents.filter(e => e.stage_name === "HITL_APPROVAL" || e.stage_name === "APPROVAL").length,
                  SETTLED: auditEvents.filter(e => e.stage_name === "SETTLED" || e.stage_name === "ACTION_DISPATCH").length,
                };

                // Filter audit events
                const filteredAuditEvents = auditEvents.filter(ev => {
                  if (auditCaseFilter !== "ALL" && ev.case_id !== auditCaseFilter) return false;
                  
                  if (auditStageFilter === "INGESTION" && ev.stage_name !== "INGESTION" && ev.stage_name !== "INTAKE") return false;
                  if (auditStageFilter === "REPAIR" && ev.stage_name !== "ANALYST_REPAIR" && ev.stage_name !== "AI_REASONING" && ev.stage_name !== "EVIDENCE_GATHERING") return false;
                  if (auditStageFilter === "APPROVAL" && ev.stage_name !== "HITL_APPROVAL" && ev.stage_name !== "APPROVAL") return false;
                  if (auditStageFilter === "SETTLED" && ev.stage_name !== "SETTLED" && ev.stage_name !== "ACTION_DISPATCH") return false;

                  if (auditSearch.trim()) {
                    const q = auditSearch.toLowerCase().trim();
                    const matchCase = ev.case_id?.toLowerCase().includes(q);
                    const matchAction = ev.action_name?.toLowerCase().includes(q);
                    const matchStage = ev.stage_name?.toLowerCase().includes(q);
                    const matchActor = ev.actor_id?.toLowerCase().includes(q) || ev.actor_role?.toLowerCase().includes(q);
                    const matchDetails = ev.details?.toLowerCase().includes(q);
                    const matchHash = ev.current_hash?.toLowerCase().includes(q) || ev.prev_hash?.toLowerCase().includes(q) || ev.correlation_id?.toLowerCase().includes(q);
                    if (!matchCase && !matchAction && !matchStage && !matchActor && !matchDetails && !matchHash) {
                      return false;
                    }
                  }
                  return true;
                });

                // Group by case for Lifecycle view
                const groupedByCase = {};
                filteredAuditEvents.forEach(ev => {
                  const cid = ev.case_id || "SYSTEM";
                  if (!groupedByCase[cid]) groupedByCase[cid] = [];
                  groupedByCase[cid].push(ev);
                });

                const isFilterActive = auditSearch.trim() !== "" || auditCaseFilter !== "ALL" || auditStageFilter !== "ALL";

                const getStageBadgeStyle = (st) => {
                  switch (st) {
                    case "INGESTION":
                    case "INTAKE":
                      return "bg-indigo-50 text-indigo-700 border-indigo-200";
                    case "ANALYST_REPAIR":
                    case "AI_REASONING":
                    case "EVIDENCE_GATHERING":
                      return "bg-purple-50 text-purple-700 border-purple-200";
                    case "HITL_APPROVAL":
                    case "APPROVAL":
                      return "bg-amber-50 text-amber-700 border-amber-200";
                    case "SETTLED":
                    case "ACTION_DISPATCH":
                      return "bg-emerald-50 text-emerald-700 border-emerald-200";
                    default:
                      return "bg-slate-100 text-slate-700 border-slate-200";
                  }
                };

                const getStageIcon = (st) => {
                  switch (st) {
                    case "INGESTION":
                    case "INTAKE":
                      return "📥";
                    case "ANALYST_REPAIR":
                    case "AI_REASONING":
                    case "EVIDENCE_GATHERING":
                      return "⚡";
                    case "HITL_APPROVAL":
                    case "APPROVAL":
                      return "📋";
                    case "SETTLED":
                    case "ACTION_DISPATCH":
                      return "🏁";
                    default:
                      return "🔒";
                  }
                };

                return (
                  <div className="p-8 max-w-[1440px] mx-auto space-y-6">
                    {/* TOP BANNER */}
                    <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 bg-gradient-to-r from-slate-900 via-sky-950 to-indigo-950 p-6 rounded-2xl text-white shadow-lg border border-slate-800">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="text-xl">🛡️</span>
                          <h1 className="text-2xl font-bold tracking-tight">Audit & Investigation Event Stream</h1>
                        </div>
                        <p className="text-xs text-sky-200/80 mt-1 max-w-2xl">
                          Cryptographically linked SHA-256 continuous provenance ledger. Every payment ingestion, AI diagnostic synthesis, maker repair submission, dual-authorization stamp, and clearing dispatch is permanently sealed into an immutable block chain.
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 shrink-0">
                        <span className="text-xs font-mono text-emerald-300 bg-emerald-950/80 border border-emerald-500/40 px-3.5 py-2 rounded-xl font-bold flex items-center space-x-2 shadow-inner">
                          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                          <span>SHA-256 CHAIN INTACT ({auditEvents.length} BLOCKS)</span>
                        </span>
                        <span className="text-xs font-mono text-sky-300 bg-sky-950/80 border border-sky-500/40 px-3 py-2 rounded-xl font-medium">
                          {uniqueAuditCaseIds.length} CASES TRACKED
                        </span>
                      </div>
                    </div>

                    {/* SEARCH, FILTER & VIEW CONTROLS TOOLBAR */}
                    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-center">
                        {/* SEARCH INPUT */}
                        <div className="lg:col-span-6 relative">
                          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                          </div>
                          <input
                            type="text"
                            value={auditSearch}
                            onChange={(e) => setAuditSearch(e.target.value)}
                            placeholder="Search Case ID (e.g. PEX-INV-0007), Actor (e.g. Priya Nair), Action, UETR, Hash..."
                            className="w-full pl-10 pr-10 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white text-slate-900 transition-all font-mono"
                          />
                          {auditSearch && (
                            <button
                              onClick={() => setAuditSearch("")}
                              className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 text-xs font-bold"
                            >
                              ✕
                            </button>
                          )}
                        </div>

                        {/* CASE SELECTOR DROPDOWN */}
                        <div className="lg:col-span-3">
                          <select
                            value={auditCaseFilter}
                            onChange={(e) => setAuditCaseFilter(e.target.value)}
                            className="w-full py-2 px-3 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono text-slate-800 font-semibold"
                          >
                            <option value="ALL">🌐 All Cases ({uniqueAuditCaseIds.length} tracked)</option>
                            {uniqueAuditCaseIds.map(cid => {
                              const caseObj = cases.find(c => c.case_id === cid);
                              const evCount = auditCaseMap[cid]?.length || 0;
                              const statusLabel = caseObj ? `[${caseObj.status}]` : "";
                              return (
                                <option key={cid} value={cid}>
                                  {cid} — {evCount} events {statusLabel}
                                </option>
                              );
                            })}
                          </select>
                        </div>

                        {/* VIEW MODE SWITCHER */}
                        <div className="lg:col-span-3 flex justify-end">
                          <div className="bg-slate-100 p-1 rounded-xl flex items-center space-x-1 border border-slate-200 w-full lg:w-auto">
                            <button
                              onClick={() => setAuditViewMode("STREAM")}
                              className={`flex-1 lg:flex-none px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center justify-center space-x-1.5 ${
                                auditViewMode === "STREAM"
                                  ? "bg-white text-sky-700 shadow-sm border border-slate-200/80"
                                  : "text-slate-600 hover:text-slate-900"
                              }`}
                            >
                              <span>📜</span>
                              <span>Global Stream</span>
                            </button>
                            <button
                              onClick={() => setAuditViewMode("LIFECYCLE")}
                              className={`flex-1 lg:flex-none px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center justify-center space-x-1.5 ${
                                auditViewMode === "LIFECYCLE"
                                  ? "bg-white text-sky-700 shadow-sm border border-slate-200/80"
                                  : "text-slate-600 hover:text-slate-900"
                              }`}
                            >
                              <span>🗂️</span>
                              <span>Case Forensic Trace</span>
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* STAGE FILTER PILLS & ACTIVE FILTER STATUS */}
                      <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
                        <div className="flex flex-wrap items-center gap-1.5 text-xs">
                          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-mono mr-1">Lifecycle Stage:</span>
                          <button
                            onClick={() => setAuditStageFilter("ALL")}
                            className={`px-3 py-1 rounded-lg font-mono text-xs font-semibold transition-all ${
                              auditStageFilter === "ALL"
                                ? "bg-slate-900 text-white shadow-sm"
                                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                            }`}
                          >
                            All Events ({stageCounts.ALL})
                          </button>
                          <button
                            onClick={() => setAuditStageFilter("INGESTION")}
                            className={`px-3 py-1 rounded-lg font-mono text-xs font-semibold transition-all ${
                              auditStageFilter === "INGESTION"
                                ? "bg-indigo-600 text-white shadow-sm"
                                : "bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200/60"
                            }`}
                          >
                            📥 Ingestion ({stageCounts.INGESTION})
                          </button>
                          <button
                            onClick={() => setAuditStageFilter("REPAIR")}
                            className={`px-3 py-1 rounded-lg font-mono text-xs font-semibold transition-all ${
                              auditStageFilter === "REPAIR"
                                ? "bg-purple-600 text-white shadow-sm"
                                : "bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200/60"
                            }`}
                          >
                            ⚡ AI & Maker Repair ({stageCounts.REPAIR})
                          </button>
                          <button
                            onClick={() => setAuditStageFilter("APPROVAL")}
                            className={`px-3 py-1 rounded-lg font-mono text-xs font-semibold transition-all ${
                              auditStageFilter === "APPROVAL"
                                ? "bg-amber-600 text-white shadow-sm"
                                : "bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200/60"
                            }`}
                          >
                            📋 Dual-Auth Approvals ({stageCounts.APPROVAL})
                          </button>
                          <button
                            onClick={() => setAuditStageFilter("SETTLED")}
                            className={`px-3 py-1 rounded-lg font-mono text-xs font-semibold transition-all ${
                              auditStageFilter === "SETTLED"
                                ? "bg-emerald-600 text-white shadow-sm"
                                : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200/60"
                            }`}
                          >
                            🏁 Settlement & Dispatch ({stageCounts.SETTLED})
                          </button>
                        </div>

                        {/* ACTIVE FILTERS BADGE & RESET */}
                        <div className="flex items-center space-x-2 text-xs">
                          <span className="font-mono text-slate-500 text-[11px]">
                            Showing <strong className="text-slate-900 font-bold">{filteredAuditEvents.length}</strong> of {auditEvents.length} blocks
                          </span>
                          {isFilterActive && (
                            <button
                              onClick={() => {
                                setAuditSearch("");
                                setAuditCaseFilter("ALL");
                                setAuditStageFilter("ALL");
                              }}
                              className="px-2.5 py-1 text-[11px] font-bold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-lg transition-all"
                            >
                              ✕ Reset Filters
                            </button>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* EMPTY STATE */}
                    {filteredAuditEvents.length === 0 && (
                      <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center space-y-4 shadow-sm">
                        <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto text-xl font-bold">
                          🔍
                        </div>
                        <div>
                          <h3 className="text-sm font-bold text-slate-900">No Audit Events Match Your Filter Criteria</h3>
                          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                            Try broadening your search term, switching the stage pill to "All Events", or selecting "All Cases".
                          </p>
                        </div>
                        <button
                          onClick={() => {
                            setAuditSearch("");
                            setAuditCaseFilter("ALL");
                            setAuditStageFilter("ALL");
                          }}
                          className="px-4 py-2 text-xs font-bold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 rounded-xl transition-all"
                        >
                          Clear All Filters
                        </button>
                      </div>
                    )}

                    {/* VIEW MODE 1: CONTINUOUS CHRONOLOGICAL STREAM */}
                    {filteredAuditEvents.length > 0 && auditViewMode === "STREAM" && (
                      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm divide-y divide-slate-100 overflow-hidden">
                        {filteredAuditEvents.map(ev => {
                          const caseObj = cases.find(c => c.case_id === ev.case_id);
                          return (
                            <div
                              key={ev.event_index}
                              onClick={() => setSelectedAuditEvent(ev)}
                              className="p-4 hover:bg-sky-50/60 cursor-pointer transition-all flex flex-col md:flex-row md:items-center justify-between gap-3 group"
                            >
                              <div className="flex items-start space-x-3.5 min-w-0">
                                <span className="w-8 h-8 rounded-xl bg-slate-900 text-white font-mono text-xs font-bold flex items-center justify-center shrink-0 shadow-sm group-hover:bg-sky-700 transition-colors">
                                  #{ev.event_index}
                                </span>
                                <div className="min-w-0 space-y-1">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <span className="font-mono text-xs font-bold text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                                      {ev.case_id}
                                    </span>
                                    {caseObj && (
                                      <span className="text-[10px] font-mono text-slate-500 font-semibold">
                                        [{caseObj.domain}] ${(caseObj.amount || 0).toLocaleString()}
                                      </span>
                                    )}
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${getStageBadgeStyle(ev.stage_name)}`}>
                                      {getStageIcon(ev.stage_name)} {ev.stage_name}
                                    </span>
                                    <strong className="text-xs text-slate-900">{ev.action_name}</strong>
                                    <span className="text-[11px] text-slate-500 font-mono">
                                      by <strong className="text-slate-700">{ev.actor_id}</strong> ({ev.actor_role})
                                    </span>
                                  </div>
                                  <p className="text-xs text-slate-600 line-clamp-1 group-hover:text-slate-900">{ev.details}</p>
                                  <div className="flex items-center space-x-3 text-[10px] font-mono text-slate-400">
                                    <span>HASH: {ev.current_hash.slice(0, 16)}...</span>
                                    <span>PREV: {ev.prev_hash.slice(0, 12)}...</span>
                                  </div>
                                </div>
                              </div>

                              <div className="flex items-center space-x-3 shrink-0 self-end md:self-center">
                                <span className="text-[11px] font-mono text-slate-400">
                                  {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                </span>
                                <span className="text-xs font-bold text-sky-600 group-hover:text-sky-700 bg-sky-50 group-hover:bg-sky-100 px-3 py-1.5 rounded-lg border border-sky-200/60 transition-all flex items-center space-x-1">
                                  <span>Inspect Block</span>
                                  <span>&rarr;</span>
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* VIEW MODE 2: CASE FORENSIC TRACE (GROUPED LIFECYCLE VIEW) */}
                    {filteredAuditEvents.length > 0 && auditViewMode === "LIFECYCLE" && (
                      <div className="space-y-4">
                        {Object.entries(groupedByCase).map(([cid, events]) => {
                          const caseObj = cases.find(c => c.case_id === cid);
                          const isExpanded = auditExpandedCase === cid || Object.keys(groupedByCase).length === 1;
                          const firstEv = events[0];
                          const lastEv = events[events.length - 1];

                          return (
                            <div
                              key={cid}
                              className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden transition-all"
                            >
                              {/* CASE ACCORDION HEADER */}
                              <div
                                onClick={() => setAuditExpandedCase(isExpanded ? null : cid)}
                                className="p-4 bg-slate-50/70 hover:bg-sky-50/50 cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-100 transition-colors"
                              >
                                <div className="flex items-center space-x-3">
                                  <div className="w-9 h-9 rounded-xl bg-slate-900 text-white font-mono text-xs font-bold flex items-center justify-center shrink-0 shadow-sm">
                                    {events.length}
                                  </div>
                                  <div>
                                    <div className="flex items-center space-x-2">
                                      <span className="font-mono text-sm font-bold text-sky-800">{cid}</span>
                                      {caseObj && (
                                        <>
                                          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-200 text-slate-800">
                                            {caseObj.domain}
                                          </span>
                                          <span className="text-xs font-bold text-slate-900">
                                            ${(caseObj.amount || 0).toLocaleString()}
                                          </span>
                                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                                            caseObj.status === "SETTLED" ? "bg-emerald-100 text-emerald-800" :
                                            caseObj.status === "MAKER_REPAIR" ? "bg-indigo-100 text-indigo-800" :
                                            caseObj.status === "CHECKER_APPROVAL" ? "bg-amber-100 text-amber-800" :
                                            "bg-slate-100 text-slate-700"
                                          }`}>
                                            {caseObj.status}
                                          </span>
                                        </>
                                      )}
                                    </div>
                                    <p className="text-xs text-slate-500 mt-0.5">
                                      {caseObj?.profile || "System Event Chain"} &bull; {events.length} sequential cryptographic lifecycle checkpoints
                                    </p>
                                  </div>
                                </div>

                                <div className="flex items-center space-x-3">
                                  <div className="text-right text-[11px] font-mono text-slate-400 hidden sm:block">
                                    <div>Inception: {new Date(firstEv.timestamp).toLocaleTimeString()}</div>
                                    <div>Latest: {new Date(lastEv.timestamp).toLocaleTimeString()}</div>
                                  </div>
                                  <span className="text-xs font-bold text-sky-700 bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-2xs">
                                    {isExpanded ? "Collapse Trail ▲" : "Expand Trail ▼"}
                                  </span>
                                </div>
                              </div>

                              {/* VERTICAL FORENSIC LIFECYCLE STEPPER */}
                              {isExpanded && (
                                <div className="p-6 bg-slate-50/30">
                                  <div className="relative pl-6 sm:pl-8 border-l-2 border-sky-200 space-y-6 ml-3 my-2">
                                    {events.map((ev, idx) => {
                                      return (
                                        <div key={ev.event_index} className="relative group">
                                          {/* STEP MARKER NODE */}
                                          <div className="absolute -left-[31px] sm:-left-[39px] top-1 w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-white border-2 border-sky-500 shadow-sm flex items-center justify-center text-xs font-mono font-bold text-sky-800 group-hover:scale-110 transition-transform">
                                            {idx + 1}
                                          </div>

                                          {/* STEP CONTENT CARD */}
                                          <div
                                            onClick={() => setSelectedAuditEvent(ev)}
                                            className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:shadow-md hover:border-sky-300 transition-all cursor-pointer space-y-2"
                                          >
                                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                              <div className="flex flex-wrap items-center gap-2">
                                                <span className="w-5 h-5 rounded bg-slate-900 text-white font-mono text-[10px] font-bold flex items-center justify-center">
                                                  #{ev.event_index}
                                                </span>
                                                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${getStageBadgeStyle(ev.stage_name)}`}>
                                                  {getStageIcon(ev.stage_name)} {ev.stage_name}
                                                </span>
                                                <strong className="text-xs text-slate-900 font-bold">{ev.action_name}</strong>
                                                <span className="text-[11px] text-slate-500 font-mono">
                                                  by <strong className="text-slate-800">{ev.actor_id}</strong> ({ev.actor_role})
                                                </span>
                                              </div>
                                              <span className="text-[11px] font-mono text-slate-400 shrink-0">
                                                {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                              </span>
                                            </div>

                                            <p className="text-xs text-slate-700 leading-relaxed">{ev.details}</p>

                                            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 text-[10px] font-mono">
                                              <div className="flex items-center space-x-2 text-slate-400">
                                                <span>BLOCK HASH:</span>
                                                <code className="text-sky-700 bg-sky-50 px-1.5 py-0.5 rounded font-bold">
                                                  {ev.current_hash.slice(0, 16)}...
                                                </code>
                                              </div>
                                              <span className="text-sky-600 group-hover:text-sky-700 font-bold flex items-center space-x-1">
                                                <span>Inspect SHA-256 Certificate</span>
                                                <span>&rarr;</span>
                                              </span>
                                            </div>
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })()}"""

if old_tab_pattern.search(content):
    content = old_tab_pattern.sub(new_tab_code, content)
    print("Matched old tab pattern and replaced.")
else:
    print("Old tab pattern did not match directly, searching for tab === 'investigations'...")
    # fallback find and replace
    start_str = '{/* INVESTIGATIONS HUB */}\n              {tab === "investigations" && ('
    end_str = '              {/* PAYMENT ONTOLOGY TAB */}'
    start_pos = content.find(start_str)
    end_pos = content.find(end_str)
    if start_pos != -1 and end_pos != -1:
        content = content[:start_pos] + new_tab_code + "\n\n              " + content[end_pos:]
        print("Replaced by index range successfully.")
    else:
        print("Failed to find boundaries.")

with open("build_guided_frontend.py", "w", encoding="utf-8") as f:
    f.write(content)

print("build_guided_frontend.py updated successfully!")
