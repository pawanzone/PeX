"""Script to inject Dynamic Rule & Policy Studio + ICD Registry into build_guided_frontend.py and compile."""
import re
from pathlib import Path

source_path = Path(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\build_guided_frontend.py")
content = source_path.read_text(encoding="utf-8")

# 1. State hooks to inject
state_hooks = """
      // =========================================================================
      // DYNAMIC GOVERNED RULE & POLICY STUDIO + ICD REGISTRY STATE (RELEASE v1.4)
      // =========================================================================
      const [rulesList, setRulesList] = useState([]);
      const [icdList, setIcdList] = useState([]);
      const [rulesSubTab, setRulesSubTab] = useState("builder"); // "builder", "registry", "icd"
      const [rulePrompt, setRulePrompt] = useState("Anything more than $250,000 will go to 2-level approvals");
      const [ruleCategory, setRuleCategory] = useState("APPROVAL_GATING");
      const [ruleDomain, setRuleDomain] = useState("ALL");
      const [synthesizedAst, setSynthesizedAst] = useState(null);
      const [synthesizing, setSynthesizing] = useState(false);
      const [simulating, setSimulating] = useState(false);
      const [simulationResult, setSimulationResult] = useState(null);
      const [ruleMakerNotes, setRuleMakerNotes] = useState("");
      const [rulesFilterStatus, setRulesFilterStatus] = useState("ALL");
      const [ruleInspectModalRule, setRuleInspectModalRule] = useState(null);
      
      // Checker Decision Modal for Policy Rules
      const [ruleCheckerModalOpen, setRuleCheckerModalOpen] = useState(false);
      const [selectedRuleForChecker, setSelectedRuleForChecker] = useState(null);
      const [ruleCheckerAction, setRuleCheckerAction] = useState("APPROVE"); // "APPROVE", "REJECT"
      const [ruleCheckerComments, setRuleCheckerComments] = useState("");

      // Onboard New ICD Bank Adapter Modal
      const [newIcdModalOpen, setNewIcdModalOpen] = useState(false);
      const [newIcdForm, setNewIcdForm] = useState({
        name: "BNP Paribas Paris SEPA Instant Node",
        institution_name: "BNP Paribas SA Paris",
        bic: "BNPAFRPP",
        rail: "TARGET2",
        adapter_type: "DIRECTORY_LOOKUP",
        endpoint_url: "https://api.clearing.bnpparibas.internal/sepa/dir",
        latency_ms: 16,
        maker_notes: "Request to integrate new SEPA instant clearing node for Euro correspondent flows."
      });
"""

# Insert state hooks after notificationMenuRef
target_state_anchor = "const notificationMenuRef = useRef(null);"
if target_state_anchor in content:
    content = content.replace(target_state_anchor, target_state_anchor + "\n" + state_hooks, 1)
    print("Injected state hooks.")

# 2. Handlers to inject
handlers = """
      // =========================================================================
      // RULE & POLICY STUDIO API HANDLERS (RELEASE v1.4)
      // =========================================================================
      const loadRulesAndIcd = async () => {
        try {
          const rRes = await fetch(`${API_BASE}/rules`).then(r => r.json());
          setRulesList(rRes || []);
          const iRes = await fetch(`${API_BASE}/rules/icd-configs/list`).then(r => r.json());
          setIcdList(iRes || []);
        } catch (e) {
          console.error("Error loading rules or ICDs:", e);
        }
      };

      const handleSynthesizeRule = async () => {
        if (!rulePrompt.trim()) return;
        setSynthesizing(true);
        setActionMsg(null);
        setActionErr(null);
        try {
          const res = await fetch(`${API_BASE}/rules/synthesize`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: rulePrompt.trim(), category: ruleCategory, domain: ruleDomain })
          });
          if (!res.ok) throw new Error(await res.text());
          const data = await res.json();
          setSynthesizedAst(data);
          setActionMsg(`✨ Policy successfully translated to JSON AST: ${data.name}`);
        } catch (e) {
          setActionErr(e.message || "Synthesis failed");
        } finally {
          setSynthesizing(false);
        }
      };

      const handleSimulateRule = async () => {
        if (!synthesizedAst) return;
        setSimulating(true);
        setActionMsg(null);
        setActionErr(null);
        try {
          const res = await fetch(`${API_BASE}/rules/simulate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              domain: synthesizedAst.domain,
              conditions: synthesizedAst.conditions,
              actions: synthesizedAst.actions
            })
          });
          if (!res.ok) throw new Error(await res.text());
          const data = await res.json();
          setSimulationResult(data);
          setActionMsg(`📊 Live simulation complete: Affects ${data.matched_cases_count} of ${data.total_cases_evaluated} cases ($${data.total_dollar_volume_affected.toLocaleString()})`);
        } catch (e) {
          setActionErr(e.message || "Simulation failed");
        } finally {
          setSimulating(false);
        }
      };

      const handleSubmitRuleForApproval = async () => {
        if (!synthesizedAst) return;
        setActionMsg(null);
        setActionErr(null);
        try {
          const res = await fetch(`${API_BASE}/rules/submit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name: synthesizedAst.name,
              natural_language_prompt: rulePrompt,
              category: synthesizedAst.category,
              domain: synthesizedAst.domain,
              conditions: synthesizedAst.conditions,
              actions: synthesizedAst.actions,
              maker_id: currentPersona.user_id,
              maker_name: currentPersona.name,
              maker_notes: ruleMakerNotes || `Submitted by ${currentPersona.name} via Policy Studio.`
            })
          });
          if (!res.ok) throw new Error(await res.text());
          const saved = await res.json();
          setActionMsg(`📤 Rule ${saved.rule_id} submitted for Checker approval!`);
          setRuleMakerNotes("");
          loadRulesAndIcd();
          setRulesSubTab("registry");
        } catch (e) {
          setActionErr(e.message || "Submission failed");
        }
      };

      const handleConfirmRuleCheckerDecision = async () => {
        if (!selectedRuleForChecker) return;
        setActionMsg(null);
        setActionErr(null);
        const isApprove = ruleCheckerAction === "APPROVE";
        const endpoint = `${API_BASE}/rules/${selectedRuleForChecker.rule_id}/${isApprove ? "approve" : "reject"}`;
        try {
          const res = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              checker_id: currentPersona.user_id,
              checker_name: currentPersona.name,
              comments: ruleCheckerComments || (isApprove ? "Approved for live enforcement" : "Rejected by Checker")
            })
          });
          if (!res.ok) {
            const errJson = await res.json().catch(() => ({ detail: "Request failed" }));
            throw new Error(errJson.detail || "Checker action failed");
          }
          const updated = await res.json();
          setActionMsg(isApprove ? `✓ Rule ${updated.rule_id} approved and active in production with zero downtime!` : `✕ Rule ${updated.rule_id} returned to Maker with comments.`);
          setRuleCheckerModalOpen(false);
          setSelectedRuleForChecker(null);
          setRuleCheckerComments("");
          loadRulesAndIcd();
        } catch (e) {
          setActionErr(e.message || "Checker decision error");
        }
      };

      const handleToggleRuleStatus = async (ruleId) => {
        try {
          const res = await fetch(`${API_BASE}/rules/${ruleId}/toggle-status`, { method: "POST" });
          if (!res.ok) throw new Error("Toggle failed");
          loadRulesAndIcd();
        } catch (e) {
          setActionErr(e.message || "Toggle failed");
        }
      };

      const handleSubmitNewIcd = async () => {
        setActionMsg(null);
        setActionErr(null);
        try {
          const res = await fetch(`${API_BASE}/rules/icd-configs/submit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name: newIcdForm.name,
              institution_name: newIcdForm.institution_name,
              bic: newIcdForm.bic,
              rail: newIcdForm.rail,
              adapter_type: newIcdForm.adapter_type,
              endpoint_url: newIcdForm.endpoint_url,
              latency_ms: parseInt(newIcdForm.latency_ms) || 12,
              config_payload: { rail: newIcdForm.rail },
              maker_id: currentPersona.user_id,
              maker_name: currentPersona.name,
              maker_notes: newIcdForm.maker_notes
            })
          });
          if (!res.ok) throw new Error(await res.text());
          const saved = await res.json();
          setActionMsg(`📤 ICD Adapter ${saved.icd_id} (${saved.name}) submitted for Checker approval!`);
          setNewIcdModalOpen(false);
          loadRulesAndIcd();
        } catch (e) {
          setActionErr(e.message || "ICD submission failed");
        }
      };

      const handleApproveIcd = async (icdId) => {
        setActionMsg(null);
        setActionErr(null);
        try {
          const res = await fetch(`${API_BASE}/rules/icd-configs/${icdId}/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              checker_id: currentPersona.user_id,
              checker_name: currentPersona.name,
              comments: "ICD bank adapter integration verified and activated."
            })
          });
          if (!res.ok) {
            const errJson = await res.json().catch(() => ({ detail: "Request failed" }));
            throw new Error(errJson.detail || "Approval failed");
          }
          const updated = await res.json();
          setActionMsg(`✓ ICD Adapter ${updated.icd_id} (${updated.name}) approved and active!`);
          loadRulesAndIcd();
        } catch (e) {
          setActionErr(e.message || "ICD approval failed");
        }
      };
"""

target_handlers_anchor = "fetch(`${API_BASE}/copilot/skills/active`).then(r => r.json()).then(setActiveSkillsData);"
if target_handlers_anchor in content:
    content = content.replace(target_handlers_anchor, target_handlers_anchor + "\n          loadRulesAndIcd();" + "\n" + handlers, 1)
    print("Injected handlers.")

# 3. Sidebar link for Rule Studio
sidebar_link = """
                <button onClick={() => setTab("rules_studio")} className={`w-full flex items-center justify-between px-3 py-2 rounded-lg font-semibold transition-all ${tab === "rules_studio" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  <div className="flex items-center space-x-2">
                    <span>⚡</span>
                    <span>Rule & Policy Studio</span>
                  </div>
                  <span className="text-[9px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded font-mono border border-amber-500/30">BRMS</span>
                </button>
"""

target_sidebar_anchor = '<span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">CONFIGURE & GOVERN</span>'
if target_sidebar_anchor in content:
    content = content.replace(target_sidebar_anchor, target_sidebar_anchor + "\n" + sidebar_link, 1)
    print("Injected sidebar link.")

# 4. View component for tab === "rules_studio"
rules_studio_view = """
              {/* TAB: DYNAMIC GOVERNED RULE & POLICY STUDIO + ICD REGISTRY (RELEASE v1.4) */}
              {tab === "rules_studio" && (
                <div className="p-8 max-w-[1440px] mx-auto space-y-6">
                  {/* Studio Hero Banner */}
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-6 rounded-2xl text-white border border-slate-800 shadow-xl">
                    <div className="space-y-1.5">
                      <div className="flex items-center space-x-2">
                        <span className="text-[10px] font-bold uppercase tracking-widest font-mono bg-amber-500/20 text-amber-300 border border-amber-400/30 px-2.5 py-0.5 rounded">
                          DYNAMIC NO-CODE BRMS • RELEASE v1.4
                        </span>
                        <span className="text-[10px] font-mono text-emerald-400 flex items-center space-x-1">
                          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                          <span>LIVE DB EXECUTION</span>
                        </span>
                      </div>
                      <h1 className="text-2xl font-bold tracking-tight text-white flex items-center space-x-2">
                        <span>⚡</span>
                        <span>Dynamic Governed Rule & Policy Studio + ICD Registry</span>
                      </h1>
                      <p className="text-xs text-slate-300 max-w-3xl leading-relaxed">
                        Define and refine payment exception governance rules in plain English. The platform compiles natural language statements into executable JSON condition/action ASTs, simulates portfolio impact against live database cases, and enforces full Maker-Checker segregation of duties — <strong>with zero Python code changes and zero server restarts</strong>.
                      </p>
                    </div>

                    <div className="flex items-center space-x-2 shrink-0">
                      <div className="text-right font-mono text-xs">
                        <div className="text-slate-400 text-[10px]">ACTIVE POLICIES</div>
                        <div className="text-emerald-400 font-bold text-base">{rulesList.filter(r => r.status === "ACTIVE").length} RUNNING</div>
                      </div>
                      <div className="border-l border-slate-700 pl-3 text-right font-mono text-xs">
                        <div className="text-slate-400 text-[10px]">ICD NODES</div>
                        <div className="text-sky-400 font-bold text-base">{icdList.length} CONNECTED</div>
                      </div>
                    </div>
                  </div>

                  {/* Studio Navigation Sub-Tabs */}
                  <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                    <div className="flex items-center space-x-2">
                      {[
                        { id: "builder", label: "✨ Natural Language Rule Builder & Sandbox", count: "Compiler" },
                        { id: "registry", label: "📜 Governed Policy Rules Registry", count: `${rulesList.length} Rules` },
                        { id: "icd", label: "🏦 ICD & External Bank Node Integrations", count: `${icdList.length} Nodes` }
                      ].map(t => (
                        <button
                          key={t.id}
                          onClick={() => setRulesSubTab(t.id)}
                          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center space-x-2 ${
                            rulesSubTab === t.id
                              ? "bg-slate-900 text-white shadow-sm"
                              : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
                          }`}
                        >
                          <span>{t.label}</span>
                          <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${rulesSubTab === t.id ? "bg-slate-800 text-slate-300" : "bg-slate-100 text-slate-500"}`}>
                            {t.count}
                          </span>
                        </button>
                      ))}
                    </div>

                    <button
                      onClick={loadRulesAndIcd}
                      className="px-3 py-1.5 bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 rounded-lg text-xs font-mono font-semibold flex items-center space-x-1.5"
                    >
                      <span>🔄</span>
                      <span>Sync DB</span>
                    </button>
                  </div>

                  {/* ========================================================================= */}
                  {/* SUBTAB 1: NATURAL LANGUAGE RULE BUILDER & SANDBOX SIMULATOR */}
                  {/* ========================================================================= */}
                  {rulesSubTab === "builder" && (
                    <div className="space-y-6">
                      {/* Step 1: Plain English Rule Formulation */}
                      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                          <div>
                            <span className="text-[10px] font-bold uppercase font-mono text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                              STEP 1: NATURAL LANGUAGE POLICY PROMPT
                            </span>
                            <h3 className="text-base font-bold text-slate-900 mt-1">
                              Define Governance Policy Statement
                            </h3>
                            <p className="text-xs text-slate-500">
                              Type plain-English governance rules for authorization gating, micro-repair fast-lanes, desk routing, or SLA escalation.
                            </p>
                          </div>
                          <span className="text-xs font-mono text-slate-500">Maker: <strong>{currentPersona.name} ({currentPersona.role})</strong></span>
                        </div>

                        {/* Quick-Fill Template Chips */}
                        <div className="space-y-1.5">
                          <span className="text-[11px] font-semibold text-slate-600 font-mono">Quick Template Presets:</span>
                          <div className="flex flex-wrap gap-2">
                            {[
                              { label: "📌 Dual-Auth > $250k", text: "Anything more than $250,000 will go to 2-level approvals", cat: "APPROVAL_GATING", dom: "ALL" },
                              { label: "📌 Fast-Lane Micro Repair (<$25k)", text: "Auto-qualify micro repairs under $25,000 with >95% confidence for 1-click fast-lane", cat: "STP_FAST_LANE", dom: "FORMAT_SYNTAX" },
                              { label: "📌 EUR High-Value Treasury (€1M+)", text: "Route EUR wires over €1M to Treasury Desk", cat: "ROUTING", dom: "CLIENT_TREASURY" },
                              { label: "📌 OFAC Sanctions Quarantine", text: "Transactions involving country CU, IR, SY, KP must route to Compliance Desk", cat: "ROUTING", dom: "SANCTIONS_AML" },
                              { label: "📌 High Severity Urgency", text: "High severity exceptions escalate priority to CRITICAL", cat: "SLA_URGENCY", dom: "ALL" }
                            ].map((chip, idx) => (
                              <button
                                key={idx}
                                onClick={() => {
                                  setRulePrompt(chip.text);
                                  setRuleCategory(chip.cat);
                                  setRuleDomain(chip.dom);
                                }}
                                className="px-2.5 py-1 bg-slate-50 hover:bg-sky-50 hover:text-sky-700 hover:border-sky-300 border border-slate-200 text-slate-700 rounded-lg text-xs font-medium transition"
                              >
                                {chip.label}
                              </button>
                            ))}
                          </div>
                        </div>

                        {/* Prompt Input & Parameter Selectors */}
                        <div className="space-y-3">
                          <textarea
                            value={rulePrompt}
                            onChange={(e) => setRulePrompt(e.target.value)}
                            rows="2"
                            placeholder='e.g. "Anything more than $250,000 will go to 2-level approvals"'
                            className="w-full p-3.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-mono text-slate-900 focus:ring-2 focus:ring-sky-500 focus:outline-none"
                          />

                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <div>
                              <label className="block text-[10px] font-bold text-slate-600 mb-1 font-mono uppercase">GOVERNANCE CATEGORY</label>
                              <select
                                value={ruleCategory}
                                onChange={(e) => setRuleCategory(e.target.value)}
                                className="w-full p-2 bg-slate-50 border border-slate-300 rounded-lg text-xs font-medium text-slate-800"
                              >
                                <option value="APPROVAL_GATING">Approval Gating (Dual-Auth / Tier-2)</option>
                                <option value="STP_FAST_LANE">STP Fast-Lane (1-Click Auto Repair)</option>
                                <option value="ROUTING">Queue Routing & Desk Allocation</option>
                                <option value="SLA_URGENCY">SLA Priority & Urgency Escalation</option>
                              </select>
                            </div>

                            <div>
                              <label className="block text-[10px] font-bold text-slate-600 mb-1 font-mono uppercase">DOMAIN SCOPE</label>
                              <select
                                value={ruleDomain}
                                onChange={(e) => setRuleDomain(e.target.value)}
                                className="w-full p-2 bg-slate-50 border border-slate-300 rounded-lg text-xs font-medium text-slate-800"
                              >
                                <option value="ALL">ALL (Global Enterprise Scope)</option>
                                <option value="FORMAT_SYNTAX">Format & Syntax (Data Quality)</option>
                                <option value="ACCOUNT_DIRECTORY">Account & Directory</option>
                                <option value="SANCTIONS_AML">Sanctions & AML Compliance</option>
                                <option value="SETTLEMENT_RETURNS">Settlement & Returns</option>
                                <option value="CLIENT_TREASURY">Client & Treasury</option>
                                <option value="PROCESSING">Processing & Deduplication</option>
                              </select>
                            </div>

                            <div className="flex items-end">
                              <button
                                onClick={handleSynthesizeRule}
                                disabled={synthesizing || !rulePrompt.trim()}
                                className="w-full py-2.5 bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white font-bold rounded-lg text-xs shadow-md transition flex items-center justify-center space-x-1.5"
                              >
                                <span>{synthesizing ? "⏳ Translating..." : "✨ Translate to JSON AST"}</span>
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Step 2: Synthesized AST Viewer & Live Simulation */}
                      {synthesizedAst && (
                        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5 animate-in fade-in">
                          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                            <div className="space-y-0.5">
                              <span className="text-[10px] font-bold uppercase font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                                STEP 2: EXECUTABLE JSON ABSTRACT SYNTAX TREE (AST)
                              </span>
                              <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                                <span>{synthesizedAst.name}</span>
                                <span className="text-xs font-mono text-slate-400">({synthesizedAst.rule_id})</span>
                              </h3>
                            </div>
                            <div className="flex items-center space-x-2">
                              <span className="px-2.5 py-1 rounded bg-slate-100 font-mono text-[10px] text-slate-700 font-bold">
                                Category: {synthesizedAst.category}
                              </span>
                              <span className="px-2.5 py-1 rounded bg-slate-100 font-mono text-[10px] text-slate-700 font-bold">
                                Domain: {synthesizedAst.domain}
                              </span>
                            </div>
                          </div>

                          {/* Semantic Explanation Callout */}
                          <div className="p-3 bg-emerald-50/80 border border-emerald-200 rounded-xl text-xs space-y-1">
                            <span className="font-bold text-emerald-900 font-mono text-[10px] uppercase block">SEMANTIC REASONING INTERPRETATION:</span>
                            <p className="text-emerald-950 font-medium">{synthesizedAst.explanation}</p>
                          </div>

                          {/* Side-by-Side Condition AST & Action AST Panels */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                              <div className="flex justify-between items-center text-[10px] font-bold font-mono text-slate-500 uppercase">
                                <span>1. Condition Clauses (Evaluation AST)</span>
                                <span className="text-sky-600">Logic: {synthesizedAst.conditions?.logic || "AND"}</span>
                              </div>
                              <pre className="p-3.5 bg-slate-900 text-sky-300 rounded-xl font-mono text-[11px] overflow-x-auto border border-slate-800">
                                {JSON.stringify(synthesizedAst.conditions, null, 2)}
                              </pre>
                            </div>

                            <div className="space-y-1.5">
                              <div className="flex justify-between items-center text-[10px] font-bold font-mono text-slate-500 uppercase">
                                <span>2. Governance Actions (Runtime Overrides)</span>
                                <span className="text-emerald-500 font-bold">Dynamic Dispatch</span>
                              </div>
                              <pre className="p-3.5 bg-slate-900 text-emerald-300 rounded-xl font-mono text-[11px] overflow-x-auto border border-slate-800">
                                {JSON.stringify(synthesizedAst.actions, null, 2)}
                              </pre>
                            </div>
                          </div>

                          {/* Sandbox Simulator Trigger */}
                          <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div>
                              <h4 className="text-xs font-bold text-slate-800">Pre-Deployment Impact Sandbox</h4>
                              <p className="text-[11px] text-slate-500">Simulate this policy rule against all 90 live enterprise database cases before Maker submission.</p>
                            </div>
                            <button
                              onClick={handleSimulateRule}
                              disabled={simulating}
                              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-md transition flex items-center space-x-1.5 shrink-0"
                            >
                              <span>{simulating ? "⏳ Simulating..." : "📊 Run Impact Sandbox Simulation"}</span>
                            </button>
                          </div>

                          {/* Simulation Results Display */}
                          {simulationResult && (
                            <div className="p-5 bg-slate-50 border border-indigo-200 rounded-2xl space-y-4 animate-in fade-in">
                              <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
                                <span className="text-xs font-bold text-indigo-900 font-mono uppercase flex items-center space-x-1.5">
                                  <span>📈</span>
                                  <span>SIMULATION IMPACT METRICS (LIVE DATABASE PORTFOLIO)</span>
                                </span>
                                <span className="text-[10px] font-mono text-slate-500">
                                  Evaluated on {simulationResult.total_cases_evaluated} Live Cases
                                </span>
                              </div>

                              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                <div className="p-3 bg-white rounded-xl border border-slate-200">
                                  <span className="text-[10px] text-slate-400 font-mono block">MATCHED CASES</span>
                                  <strong className="text-lg font-bold text-indigo-900 font-mono">
                                    {simulationResult.matched_cases_count} <span className="text-xs font-normal text-slate-500">({simulationResult.match_percentage}%)</span>
                                  </strong>
                                </div>
                                <div className="p-3 bg-white rounded-xl border border-slate-200">
                                  <span className="text-[10px] text-slate-400 font-mono block">TOTAL EXPOSURE AFFECTED</span>
                                  <strong className="text-lg font-bold text-emerald-800 font-mono">
                                    ${simulationResult.total_dollar_volume_affected.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                  </strong>
                                </div>
                                <div className="p-3 bg-white rounded-xl border border-slate-200">
                                  <span className="text-[10px] text-slate-400 font-mono block">TOP DOMAIN</span>
                                  <strong className="text-sm font-bold text-slate-800 font-mono truncate block">
                                    {Object.keys(simulationResult.matched_by_domain || {})[0] || "ALL"}
                                  </strong>
                                </div>
                                <div className="p-3 bg-white rounded-xl border border-slate-200">
                                  <span className="text-[10px] text-slate-400 font-mono block">GOVERNANCE ACTION</span>
                                  <strong className="text-xs font-bold text-sky-700 font-mono block truncate">
                                    {synthesizedAst.category === "APPROVAL_GATING" ? "Dual-Auth Mandated" : synthesizedAst.category === "STP_FAST_LANE" ? "Fast-Lane Qualified" : "Desk Route"}
                                  </strong>
                                </div>
                              </div>

                              {/* Sample Matched Cases Grid */}
                              {simulationResult.sample_matched_cases && simulationResult.sample_matched_cases.length > 0 && (
                                <div className="space-y-1.5">
                                  <span className="text-[10px] font-bold text-slate-600 font-mono uppercase">Sample Matching Live Cases (Top 5):</span>
                                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                                    {simulationResult.sample_matched_cases.map((c, i) => (
                                      <div key={i} className="p-2.5 bg-white rounded-lg border border-slate-200 text-xs font-mono space-y-1">
                                        <div className="flex justify-between items-center">
                                          <strong className="text-sky-700">{c.case_id}</strong>
                                          <span className="text-emerald-700 font-bold">${c.amount?.toLocaleString()}</span>
                                        </div>
                                        <div className="text-[10px] text-slate-500 truncate">{c.domain} • {c.profile}</div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Step 3: Maker Submission Card */}
                          <div className="p-5 bg-sky-50/70 border border-sky-200 rounded-2xl space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-bold uppercase font-mono text-sky-900">
                                STEP 3: SUBMIT POLICY FOR CHECKER AUTHORIZATION (MAKER-CHECKER WORKFLOW)
                              </span>
                              <span className="text-[10px] font-mono text-sky-700">Segregation of Duties Active</span>
                            </div>

                            <textarea
                              value={ruleMakerNotes}
                              onChange={(e) => setRuleMakerNotes(e.target.value)}
                              rows="2"
                              placeholder="Maker justification notes for Risk/Approvals Officer (e.g. Mandated by Q3 Risk Committee audit)..."
                              className="w-full p-3 bg-white border border-sky-300 rounded-xl text-xs font-sans text-slate-900 focus:ring-2 focus:ring-sky-500 focus:outline-none"
                            />

                            <div className="flex justify-end">
                              <button
                                onClick={handleSubmitRuleForApproval}
                                className="px-6 py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-xl shadow-md transition flex items-center space-x-2"
                              >
                                <span>📤</span>
                                <span>Submit Policy Rule to Checker &rarr;</span>
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* ========================================================================= */}
                  {/* SUBTAB 2: GOVERNED POLICY RULES REGISTRY */}
                  {/* ========================================================================= */}
                  {rulesSubTab === "registry" && (
                    <div className="space-y-4">
                      {/* Filter Chips */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          {[
                            { id: "ALL", label: `All Rules (${rulesList.length})` },
                            { id: "ACTIVE", label: `Active (${rulesList.filter(r => r.status === "ACTIVE").length})` },
                            { id: "PENDING_APPROVAL", label: `Pending Checker (${rulesList.filter(r => r.status === "PENDING_APPROVAL").length})` },
                            { id: "RETIRED", label: `Retired (${rulesList.filter(r => r.status === "RETIRED").length})` }
                          ].map(f => (
                            <button
                              key={f.id}
                              onClick={() => setRulesFilterStatus(f.id)}
                              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition font-mono ${
                                rulesFilterStatus === f.id
                                  ? "bg-slate-900 text-white"
                                  : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
                              }`}
                            >
                              {f.label}
                            </button>
                          ))}
                        </div>

                        <button
                          onClick={() => setRulesSubTab("builder")}
                          className="px-3.5 py-1.5 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-bold shadow-sm flex items-center space-x-1"
                        >
                          <span>+</span>
                          <span>Draft New Rule</span>
                        </button>
                      </div>

                      {/* Rules Cards List */}
                      <div className="space-y-3">
                        {rulesList
                          .filter(r => rulesFilterStatus === "ALL" || r.status === rulesFilterStatus)
                          .map((rule) => {
                            const isPending = rule.status === "PENDING_APPROVAL";
                            const isActive = rule.status === "ACTIVE";
                            const isChecker = currentPersona.role_type === "CHECKER" || currentPersona.role === "ADMIN";
                            const isMaker = currentPersona.role_type === "MAKER";

                            return (
                              <div key={rule.rule_id} className={`p-5 rounded-2xl border transition bg-white shadow-sm space-y-3 ${isPending ? "border-amber-300 ring-1 ring-amber-200" : "border-slate-200"}`}>
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                  <div className="space-y-1">
                                    <div className="flex items-center space-x-2">
                                      <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold uppercase ${
                                        isActive ? "bg-emerald-50 text-emerald-800 border border-emerald-200" : isPending ? "bg-amber-100 text-amber-900 border border-amber-300 animate-pulse" : "bg-slate-100 text-slate-600"
                                      }`}>
                                        {rule.status}
                                      </span>
                                      <span className="font-mono text-xs font-bold text-slate-900">{rule.name}</span>
                                      <span className="font-mono text-[11px] text-slate-400">({rule.rule_id})</span>
                                    </div>
                                    <p className="text-xs font-serif italic text-slate-700">
                                      "{rule.natural_language_prompt}"
                                    </p>
                                  </div>

                                  <div className="flex items-center space-x-2 shrink-0">
                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-200">
                                      v{rule.version || "1.0"}
                                    </span>
                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                                      {rule.category}
                                    </span>
                                  </div>
                                </div>

                                {rule.impact_summary && (
                                  <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-600 font-mono">
                                    <span className="text-slate-400">IMPACT METRIC:</span> {rule.impact_summary}
                                  </div>
                                )}

                                {/* Maker & Checker Governance Audit Trail */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 border-t border-slate-100 text-[11px] font-mono">
                                  <div className="text-slate-500">
                                    <span>Maker:</span> <strong className="text-slate-800">{rule.maker_name || "Priya Sharma"}</strong>
                                    {rule.created_at && <span className="text-slate-400 ml-1">({formatLocalDateTime(rule.created_at)})</span>}
                                    {rule.maker_notes && <p className="text-slate-600 italic font-sans text-[10px] mt-0.5">"{rule.maker_notes}"</p>}
                                  </div>
                                  <div className="text-slate-500">
                                    <span>Checker:</span> <strong className="text-slate-800">{rule.checker_name || "Pending Review"}</strong>
                                    {rule.approved_at && <span className="text-emerald-600 ml-1">({formatLocalDateTime(rule.approved_at)})</span>}
                                    {rule.checker_comments && <p className="text-emerald-700 italic font-sans text-[10px] mt-0.5">"{rule.checker_comments}"</p>}
                                  </div>
                                </div>

                                {/* Action Controls */}
                                <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                                  <button
                                    onClick={() => setRuleInspectModalRule(rule)}
                                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-mono font-semibold"
                                  >
                                    👁️ Inspect JSON AST
                                  </button>

                                  <div className="flex items-center space-x-2">
                                    {isPending && (
                                      isChecker ? (
                                        <div className="flex items-center space-x-2">
                                          <button
                                            onClick={() => {
                                              setSelectedRuleForChecker(rule);
                                              setRuleCheckerAction("REJECT");
                                              setRuleCheckerModalOpen(true);
                                            }}
                                            className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-lg text-xs font-bold"
                                          >
                                            ✕ Reject / Return
                                          </button>
                                          <button
                                            onClick={() => {
                                              setSelectedRuleForChecker(rule);
                                              setRuleCheckerAction("APPROVE");
                                              setRuleCheckerModalOpen(true);
                                            }}
                                            className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-sm"
                                          >
                                            ✓ Review & Approve Policy
                                          </button>
                                        </div>
                                      ) : (
                                        <span className="text-[11px] font-mono text-amber-700 bg-amber-50 px-3 py-1 rounded-lg border border-amber-200">
                                          🔒 Awaiting Checker Sign-off (SoD: Maker cannot self-approve)
                                        </span>
                                      )
                                    )}

                                    {isActive && (
                                      <button
                                        onClick={() => handleToggleRuleStatus(rule.rule_id)}
                                        className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 rounded-lg text-xs font-mono"
                                      >
                                        Retire Rule
                                      </button>
                                    )}
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                      </div>
                    </div>
                  )}

                  {/* ========================================================================= */}
                  {/* SUBTAB 3: ICD & EXTERNAL BANK NODE INTEGRATIONS */}
                  {/* ========================================================================= */}
                  {rulesSubTab === "icd" && (
                    <div className="space-y-5">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-base font-bold text-slate-900">External Clearing Network & Bank Adapters (ICD Registry)</h3>
                          <p className="text-xs text-slate-500">Governed external bank nodes connecting Fedwire, TARGET2, CHAPS, and SWIFT CBPR+ clearing rails.</p>
                        </div>
                        <button
                          onClick={() => setNewIcdModalOpen(true)}
                          className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold shadow-sm flex items-center space-x-1.5"
                        >
                          <span>+</span>
                          <span>Onboard New Bank Adapter</span>
                        </button>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {icdList.map((icd) => {
                          const isPending = icd.status === "PENDING_APPROVAL";
                          const isChecker = currentPersona.role_type === "CHECKER" || currentPersona.role === "ADMIN";

                          return (
                            <div key={icd.icd_id} className={`p-5 bg-white rounded-2xl border transition shadow-sm space-y-3 ${isPending ? "border-amber-300 ring-1 ring-amber-200" : "border-slate-200"}`}>
                              <div className="flex items-center justify-between">
                                <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold uppercase ${
                                  icd.status === "ACTIVE" ? "bg-emerald-50 text-emerald-800 border border-emerald-200" : "bg-amber-100 text-amber-900 border border-amber-300 animate-pulse"
                                }`}>
                                  {icd.status}
                                </span>
                                <span className="font-mono text-xs font-bold text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                                  {icd.rail}
                                </span>
                              </div>

                              <div>
                                <h4 className="text-sm font-bold text-slate-900">{icd.name}</h4>
                                <p className="text-xs text-slate-500">{icd.institution_name}</p>
                              </div>

                              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5 text-xs font-mono text-[11px]">
                                <div className="flex justify-between"><span>BIC NODE:</span><strong className="text-slate-900">{icd.bic}</strong></div>
                                <div className="flex justify-between"><span>ADAPTER TYPE:</span><strong className="text-indigo-700">{icd.adapter_type}</strong></div>
                                <div className="flex justify-between"><span>LATENCY:</span><strong className="text-emerald-600">{icd.latency_ms}ms</strong></div>
                                <div className="truncate text-slate-400 text-[10px] pt-1 border-t border-slate-200">
                                  URL: {icd.endpoint_url}
                                </div>
                              </div>

                              {isPending && (
                                isChecker ? (
                                  <button
                                    onClick={() => handleApproveIcd(icd.icd_id)}
                                    className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs shadow-sm transition"
                                  >
                                    ✓ Approve & Connect Bank Node
                                  </button>
                                ) : (
                                  <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg text-center font-mono text-[10px] text-amber-800 font-bold">
                                    🔒 Pending Checker Sign-off
                                  </div>
                                )
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* MODAL: INSPECT RULE JSON AST */}
                  {ruleInspectModalRule && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
                      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden animate-in fade-in">
                        <div className="bg-slate-900 px-6 py-4 text-white flex justify-between items-center">
                          <div>
                            <h3 className="text-sm font-bold font-mono text-amber-400">{ruleInspectModalRule.rule_id}</h3>
                            <p className="text-xs text-slate-300">{ruleInspectModalRule.name}</p>
                          </div>
                          <button onClick={() => setRuleInspectModalRule(null)} className="text-slate-400 hover:text-white">✕</button>
                        </div>
                        <div className="p-6 space-y-4 text-xs">
                          <div>
                            <span className="text-[10px] font-bold font-mono text-slate-500 uppercase block mb-1">NATURAL LANGUAGE PROMPT</span>
                            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl italic font-serif text-slate-800">
                              "{ruleInspectModalRule.natural_language_prompt}"
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <span className="text-[10px] font-bold font-mono text-slate-500 uppercase block mb-1">CONDITION AST</span>
                              <pre className="p-3 bg-slate-900 text-sky-300 rounded-xl font-mono text-[11px] overflow-x-auto max-h-48">
                                {JSON.stringify(ruleInspectModalRule.conditions, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <span className="text-[10px] font-bold font-mono text-slate-500 uppercase block mb-1">ACTION AST</span>
                              <pre className="p-3 bg-slate-900 text-emerald-300 rounded-xl font-mono text-[11px] overflow-x-auto max-h-48">
                                {JSON.stringify(ruleInspectModalRule.actions, null, 2)}
                              </pre>
                            </div>
                          </div>
                          <div className="flex justify-end pt-2">
                            <button
                              onClick={() => setRuleInspectModalRule(null)}
                              className="px-5 py-2 bg-slate-900 text-white rounded-xl font-bold text-xs hover:bg-slate-800"
                            >
                              Close
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* MODAL: CHECKER DECISION MODAL */}
                  {ruleCheckerModalOpen && selectedRuleForChecker && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
                      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in">
                        <div className="bg-slate-900 px-6 py-4 text-white flex justify-between items-center">
                          <div>
                            <h3 className="text-sm font-bold">
                              {ruleCheckerAction === "APPROVE" ? "✓ Authorize & Activate Policy Rule" : "✕ Reject / Return Policy Rule"}
                            </h3>
                            <p className="text-[11px] text-slate-400">Checker: {currentPersona.name} ({currentPersona.role})</p>
                          </div>
                          <button onClick={() => setRuleCheckerModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
                        </div>
                        <div className="p-6 space-y-4 text-xs">
                          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                            <div className="font-bold text-slate-900">{selectedRuleForChecker.name} ({selectedRuleForChecker.rule_id})</div>
                            <p className="text-slate-600 italic">"{selectedRuleForChecker.natural_language_prompt}"</p>
                            <div className="text-[10px] text-slate-500 pt-1 font-mono">
                              Maker: {selectedRuleForChecker.maker_name} • Notes: "{selectedRuleForChecker.maker_notes}"
                            </div>
                          </div>

                          <div>
                            <label className="block text-xs font-bold text-slate-700 mb-1.5 uppercase font-mono">
                              CHECKER SIGN-OFF COMMENTS / AUDIT JUSTIFICATION
                            </label>
                            <textarea
                              value={ruleCheckerComments}
                              onChange={(e) => setRuleCheckerComments(e.target.value)}
                              rows="3"
                              placeholder="Mandatory justification recorded into immutable audit trail..."
                              className="w-full p-3 bg-slate-50 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-sky-500 focus:outline-none"
                              required
                            />
                          </div>

                          <div className="flex justify-end space-x-2 pt-2">
                            <button
                              onClick={() => setRuleCheckerModalOpen(false)}
                              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-semibold"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={handleConfirmRuleCheckerDecision}
                              className={`px-5 py-2 text-white rounded-xl font-bold shadow-md ${
                                ruleCheckerAction === "APPROVE" ? "bg-emerald-600 hover:bg-emerald-700" : "bg-rose-600 hover:bg-rose-700"
                              }`}
                            >
                              {ruleCheckerAction === "APPROVE" ? "Authorize & Activate in DB &rarr;" : "Confirm Rejection & Return"}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* MODAL: ONBOARD NEW ICD BANK ADAPTER */}
                  {newIcdModalOpen && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
                      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in">
                        <div className="bg-slate-900 px-6 py-4 text-white flex justify-between items-center">
                          <div>
                            <h3 className="text-sm font-bold">Onboard New External Bank / Clearing Node</h3>
                            <p className="text-[11px] text-slate-400">Maker: {currentPersona.name} ({currentPersona.title})</p>
                          </div>
                          <button onClick={() => setNewIcdModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
                        </div>
                        <div className="p-6 space-y-3 text-xs">
                          <div>
                            <label className="block text-[10px] font-bold text-slate-600 mb-1 font-mono uppercase">NODE / INTEGRATION NAME</label>
                            <input
                              type="text"
                              value={newIcdForm.name}
                              onChange={(e) => setNewIcdForm({ ...newIcdForm, name: e.target.value })}
                              className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-semibold"
                            />
                          </div>

                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="block text-[10px] font-bold text-slate-600 mb-1 font-mono uppercase">INSTITUTION</label>
                              <input
                                type="text"
                                value={newIcdForm.institution_name}
                                onChange={(e) => setNewIcdForm({ ...newIcdForm, institution_name: e.target.value })}
                                className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] font-bold text-slate-600 mb-1 font-mono uppercase">SWIFT BIC CODE</label>
                              <input
                                type="text"
                                value={newIcdForm.bic}
                                onChange={(e) => setNewIcdForm({ ...newIcdForm, bic: e.target.value })}
                                className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-mono uppercase"
                              />
                            </div>
                          </div>

                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="block text-[10px] font-bold text-slate-600 mb-1 font-mono uppercase">PAYMENT RAIL</label>
                              <select
                                value={newIcdForm.rail}
                                onChange={(e) => setNewIcdForm({ ...newIcdForm, rail: e.target.value })}
                                className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-semibold"
                              >
                                <option value="FEDWIRE">FEDWIRE (USD RTGS)</option>
                                <option value="TARGET2">TARGET2 (EUR RTGS)</option>
                                <option value="CHAPS">CHAPS (GBP RTGS)</option>
                                <option value="SWIFT_CBPR+">SWIFT CBPR+ (Cross-Border)</option>
                              </select>
                            </div>
                            <div>
                              <label className="block text-[10px] font-bold text-slate-600 mb-1 font-mono uppercase">ADAPTER TYPE</label>
                              <select
                                value={newIcdForm.adapter_type}
                                onChange={(e) => setNewIcdForm({ ...newIcdForm, adapter_type: e.target.value })}
                                className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-semibold"
                              >
                                <option value="DIRECTORY_LOOKUP">DIRECTORY_LOOKUP</option>
                                <option value="NOSTRO_ALM">NOSTRO_ALM</option>
                                <option value="SANCTIONS_GATEWAY">SANCTIONS_GATEWAY</option>
                                <option value="CORE_LEDGER">CORE_LEDGER</option>
                              </select>
                            </div>
                          </div>

                          <div>
                            <label className="block text-[10px] font-bold text-slate-600 mb-1 font-mono uppercase">ENDPOINT URL</label>
                            <input
                              type="text"
                              value={newIcdForm.endpoint_url}
                              onChange={(e) => setNewIcdForm({ ...newIcdForm, endpoint_url: e.target.value })}
                              className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-mono"
                            />
                          </div>

                          <div>
                            <label className="block text-[10px] font-bold text-slate-600 mb-1 font-mono uppercase">MAKER JUSTIFICATION NOTES</label>
                            <textarea
                              value={newIcdForm.maker_notes}
                              onChange={(e) => setNewIcdForm({ ...newIcdForm, maker_notes: e.target.value })}
                              rows="2"
                              className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs"
                            />
                          </div>

                          <div className="flex justify-end space-x-2 pt-2">
                            <button
                              onClick={() => setNewIcdModalOpen(false)}
                              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-semibold"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={handleSubmitNewIcd}
                              className="px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold shadow-md"
                            >
                              Submit Bank Node to Checker &rarr;
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
"""

target_view_anchor = '{/* TAB 8: RESPONSIBLE AI TRUST CENTER & GOVERNANCE */}'
if target_view_anchor in content:
    content = content.replace(target_view_anchor, rules_studio_view + "\n              " + target_view_anchor, 1)
    print("Injected rules_studio view component.")

# Write updated build_guided_frontend.py
source_path.write_text(content, encoding="utf-8")
print("Saved updated build_guided_frontend.py!")
