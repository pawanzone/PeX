import sys
from pathlib import Path

guided_file = Path(r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\build_guided_frontend.py")
with open(guided_file, "r", encoding="utf-8") as f:
    code = f.read()

# 1. State hooks
if "const [archView, setArchView]" not in code:
    code = code.replace(
        'const [tab, setTab] = useState("command_center");',
        'const [tab, setTab] = useState("command_center");\n      const [archView, setArchView] = useState("epc_diagram");\n      const [archIframeKey, setArchIframeKey] = useState(0);\n      const [archFullscreen, setArchFullscreen] = useState(false);'
    )

# 2. Sidebar button under OVERVIEW
if 'setTab("architecture")' not in code:
    old_sidebar = '''              <div className="space-y-1">
                <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">OVERVIEW</span>
                <button onClick={() => setTab("command_center")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "command_center" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  Overview Dashboard
                </button>
              </div>'''

    new_sidebar = '''              <div className="space-y-1">
                <span className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">OVERVIEW</span>
                <button onClick={() => setTab("command_center")} className={`w-full flex items-center px-3 py-2 rounded-lg font-semibold transition-all ${tab === "command_center" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  Overview Dashboard
                </button>
                <button onClick={() => setTab("architecture")} className={`w-full flex items-center justify-between px-3 py-2 rounded-lg font-semibold transition-all ${tab === "architecture" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}>
                  <div className="flex items-center space-x-2">
                    <span>⚡</span>
                    <span>Architecture & Workflows</span>
                  </div>
                  <span className="text-[9px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded font-mono border border-amber-500/30">DEV</span>
                </button>
              </div>'''

    code = code.replace(old_sidebar, new_sidebar)

# 3. Tab block
arch_tab_block = '''              {/* TAB 9: ARCHITECTURE & WORKFLOWS STUDIO */}
              {tab === "architecture" && (
                <div className="p-8 max-w-[1440px] mx-auto space-y-6">
                  {/* Top Banner */}
                  <div className="bg-gradient-to-r from-slate-900 via-sky-950 to-slate-900 text-white rounded-2xl p-6 shadow-xl border border-slate-800">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="space-y-1.5">
                        <div className="flex items-center space-x-2">
                          <span className="text-[10px] font-bold uppercase tracking-widest font-mono bg-amber-500/20 text-amber-300 border border-amber-400/30 px-2.5 py-0.5 rounded">
                            SYSTEM ARCHITECTURE & WORKFLOWS STUDIO
                          </span>
                          <span className="text-[10px] font-mono text-emerald-400 flex items-center space-x-1">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                            <span>DEV / REVIEW MODE</span>
                          </span>
                        </div>
                        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center space-x-2">
                          <span>⚡</span>
                          <span>PeX Architecture & Workflows</span>
                        </h1>
                        <p className="text-xs text-slate-300 max-w-3xl leading-relaxed">
                          Interactive Event-Driven Process Chains (EPC), Bank-to-PeX numbered 9-step workflows, 8 enterprise pillars target blueprint, PPT presentation slides, and vector icon customizers.
                        </p>
                      </div>

                      {/* Top Action Buttons */}
                      <div className="flex items-center space-x-2 shrink-0">
                        {archView === "epc_diagram" && (
                          <a
                            href="/pex_workflow_diagram_epc.jpg"
                            download="PeX_Workflow_Diagram_EPC.jpg"
                            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition shadow-sm"
                          >
                            <span>📥</span>
                            <span>Download Diagram JPG</span>
                          </a>
                        )}
                        {archView === "exec_slide" && (
                          <a
                            href="/pex_agentic_workflow_slide.jpg"
                            download="PeX_Event_Driven_Slide.jpg"
                            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition shadow-sm"
                          >
                            <span>📥</span>
                            <span>Download Slide JPG</span>
                          </a>
                        )}
                        {["epc_diagram", "exec_slide", "icon_studio", "playbook", "executive_1pager"].includes(archView) && (
                          <a
                            href={
                              archView === "epc_diagram" ? "/PeX_EPC_Workflow_Diagram.html" :
                              archView === "exec_slide" ? "/PeX_Event_Driven_Architecture_Slide.html" :
                              archView === "icon_studio" ? "/pex_executive_icons_customizer.html" :
                              archView === "playbook" ? "/PeX_Playbook_1Pager.html" :
                              "/PeX_Executive_1Pager.html"
                            }
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-md transition"
                          >
                            <span>↗</span>
                            <span>Open in Full Tab</span>
                          </a>
                        )}
                        <button
                          onClick={() => setArchIframeKey(k => k + 1)}
                          title="Reload diagram"
                          className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                        >
                          🔄
                        </button>
                      </div>
                    </div>

                    {/* View Switcher Pills */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 mt-6 pt-5 border-t border-slate-800">
                      {[
                        { id: "epc_diagram", title: "EPC Workflow", sub: "Bank -> PeX 9 Steps", badge: "APPROVED", badgeColor: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30", icon: "📊" },
                        { id: "exec_slide", title: "16:9 Slide", sub: "PPT Presentation", badge: "PPT READY", badgeColor: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30", icon: "🖼️" },
                        { id: "pillars", title: "8 Pillars", sub: "AWS Roadmap", badge: "1 OF 8 IN PROGRESS", badgeColor: "bg-amber-500/20 text-amber-300 border-amber-500/30", icon: "🏛️" },
                        { id: "icon_studio", title: "Icon Studio", sub: "189 Vector Icons", badge: "25 CATEGORIES", badgeColor: "bg-sky-500/20 text-sky-300 border-sky-500/30", icon: "✨" },
                        { id: "playbook", title: "41 Playbooks", sub: "5 BIAN Domains", badge: "COMPLETE", badgeColor: "bg-purple-500/20 text-purple-300 border-purple-500/30", icon: "📚" },
                        { id: "executive_1pager", title: "Executive 1-Pager", sub: "Strategic Moats", badge: "v2.0", badgeColor: "bg-slate-700 text-slate-300 border-slate-600", icon: "📄" },
                      ].map((v) => {
                        const isActive = archView === v.id;
                        return (
                          <button
                            key={v.id}
                            onClick={() => setArchView(v.id)}
                            className={`flex flex-col items-start p-3 rounded-xl text-left transition border ${
                              isActive
                                ? "bg-slate-800 border-sky-500 text-white shadow-md ring-1 ring-sky-500"
                                : "bg-slate-900/60 border-slate-800 text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                            }`}
                          >
                            <div className="flex items-center justify-between w-full mb-1">
                              <span className="text-sm">{v.icon}</span>
                              <span className={`text-[8px] px-1.5 py-0.2 rounded font-mono font-semibold border ${v.badgeColor}`}>
                                {v.badge}
                              </span>
                            </div>
                            <div className="text-xs font-bold leading-tight text-white">{v.title}</div>
                            <div className="text-[10px] text-slate-400 truncate w-full mt-0.5">{v.sub}</div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* View 1: 8 Enterprise Pillars */}
                  {archView === "pillars" ? (
                    <div className="space-y-6">
                      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h2 className="text-base font-bold text-slate-900">
                              PeX Enterprise Architecture: 8 Foundational Pillars
                            </h2>
                            <p className="text-xs text-slate-500 mt-0.5">
                              Institutional design roadmap transitioning from local execution to enterprise AWS Cloud deployment.
                            </p>
                          </div>
                          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded bg-sky-50 text-sky-700 border border-sky-200">
                            8 OF 8 PILLARS DEFINED
                          </span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                          {[
                            {
                              num: "1",
                              title: "Persistent Relational Database Layer",
                              status: "CURRENT FOCUS (1 of 8)",
                              statusColor: "bg-amber-100 text-amber-800 border-amber-300 animate-pulse",
                              localTech: "SQLite 3 (pex_enterprise.db) + SQLAlchemy 2.0 ORM",
                              awsTarget: "AWS Aurora PostgreSQL / Amazon RDS Multi-AZ Cluster",
                              desc: "Relational persistence across Cases, Token Vault, Recommendations, Approvals, Settlements, and Immutable Audit Chains.",
                              icon: "💾",
                              bullets: [
                                "Configured via plug-and-play DATABASE_URL env variable",
                                "Connection pooling (pool_size=20, max_overflow=10, pool_pre_ping=True)",
                                "Zero-loss migration from local development to cloud production"
                              ]
                            },
                            {
                              num: "2",
                              title: "Isolated Tokenization Vault & PII Boundary",
                              status: "ONLINE",
                              statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
                              localTech: "SHA-256 HMAC Vault with TOK-* surrogate generation",
                              awsTarget: "AWS KMS / Secrets Manager + Dedicated RDS Microservice",
                              desc: "Strict zero-trust boundary ensuring AI inference engines never receive raw PII, account numbers, or party identities.",
                              icon: "🔒",
                              bullets: [
                                "Bidirectional deterministic surrogate mapping",
                                "Display masking & PCI/GDPR compliance",
                                "Token isolation between banks and internal reasoning context"
                              ]
                            },
                            {
                              num: "3",
                              title: "Multi-Provider Model Gateway",
                              status: "ONLINE",
                              statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
                              localTech: "Deterministic Mock Reasoner + Gemini 1.5 Pro + OpenAI GPT-4o",
                              awsTarget: "Amazon Bedrock (Claude 3.5 Sonnet / Llama 3) + AWS Lambda",
                              desc: "Pluggable LLM reasoning engine with strict JSON schema adherence and zero financial hallucination guardrails.",
                              icon: "🧠",
                              bullets: [
                                "Deterministic fallback modes for offline / sandbox execution",
                                "Confidence scoring & multi-hypothesis elimination ranking",
                                "Consequence simulation with clearing cutoff calculations"
                              ]
                            },
                            {
                              num: "4",
                              title: "Retrieval-Augmented Evidence & ICD Adapters",
                              status: "ONLINE",
                              statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
                              localTech: "In-memory Staging Service + BIAN SOP Playbooks (41 profiles)",
                              awsTarget: "Amazon OpenSearch Vector DB + Amazon S3 Evidence Lake",
                              desc: "Automated queries against Federal Reserve cutoffs, SWIFT SSI directories, core banking ledgers, and KYC databases.",
                              icon: "📡",
                              bullets: [
                                "90-day transaction history & temporal clustering",
                                "Confirmation of Payee (CoP) fuzzy matching & MOD-97 checksums",
                                "Domain-specific grounding across all 5 BIAN exception domains"
                              ]
                            },
                            {
                              num: "5",
                              title: "Maker-Checker & Dual Authorization Engine",
                              status: "ONLINE",
                              statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
                              localTech: "RBAC Engine + $250k High-Value Threshold Gate",
                              awsTarget: "AWS IAM + Cognito / Corporate SSO (Okta/SAML)",
                              desc: "Strict Segregation of Duties (SoD). Tier-1 Operations Approvers + Tier-2 Risk Approvers for large value wires.",
                              icon: "👥",
                              bullets: [
                                "Prevent same-actor Maker & Checker collisions",
                                "Mandatory dual-approval chain for transactions >= $250k",
                                "Audit-stamped return to Maker for rework workflows"
                              ]
                            },
                            {
                              num: "6",
                              title: "Governed Action Dispatch & Idempotency",
                              status: "ONLINE",
                              statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
                              localTech: "Idempotent Action Executor + Delivery Receipt Generator",
                              awsTarget: "Amazon SQS FIFO + Amazon EventBridge + Bank API Gateways",
                              desc: "Zero autonomous execution. Only dispatches approved repairs and returns once formal human authorization is recorded.",
                              icon: "⚙️",
                              bullets: [
                                "Strict idempotency keys preventing double-dispatch",
                                "Outbound ISO 20022 pacs.008 / pacs.004 generation",
                                "External settlement delivery receipt reconciliation"
                              ]
                            },
                            {
                              num: "7",
                              title: "Cryptographic SHA-256 Audit Hash Chain",
                              status: "ONLINE",
                              statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
                              localTech: "Linear Hash Chaining (prev_hash -> current_hash)",
                              awsTarget: "Amazon QLDB / Immutable S3 Object Lock + Ledger",
                              desc: "Tamper-evident cryptographic provenance logging across all 20 lifecycle stages from ingestion to final settlement.",
                              icon: "🔗",
                              bullets: [
                                "Deterministic SHA-256 block calculation per event",
                                "On-demand cryptographic verification endpoint (/verify-chain)",
                                "Regulatory compliance export for internal and external auditors"
                              ]
                            },
                            {
                              num: "8",
                              title: "Operations Control Plane & Telemetry",
                              status: "ONLINE",
                              statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
                              localTech: "FastAPI Telemetry Endpoints + React Real-Time Dashboard",
                              awsTarget: "Amazon CloudWatch + OpenTelemetry + Grafana Dashboard",
                              desc: "Live SLA tracking, queue distribution, at-risk capital metrics, and operations velocity analytics.",
                              icon: "📈",
                              bullets: [
                                "Dynamic 1h / 4h / 24h clearing cutoff urgency tracking",
                                "Queue health monitoring (Repair, Compliance, Treasury, Investigation)",
                                "Real-time SLA resolution velocity graphs"
                              ]
                            }
                          ].map((p) => (
                            <div key={p.num} className="p-5 rounded-2xl border border-slate-200 bg-slate-50/60 hover:bg-white transition hover:shadow-sm space-y-3">
                              <div className="flex items-start justify-between">
                                <div className="flex items-center space-x-3">
                                  <div className="w-8 h-8 rounded-xl bg-slate-900 text-white font-bold font-mono text-sm flex items-center justify-center shrink-0">
                                    {p.num}
                                  </div>
                                  <div>
                                    <h3 className="text-sm font-bold text-slate-900">{p.title}</h3>
                                    <span className={`inline-block text-[10px] font-bold font-mono px-2 py-0.5 rounded border mt-1 ${p.statusColor}`}>
                                      {p.status}
                                    </span>
                                  </div>
                                </div>
                                <span className="text-xl">{p.icon}</span>
                              </div>

                              <p className="text-xs text-slate-600 leading-relaxed">{p.desc}</p>

                              <div className="space-y-1.5 pt-2 border-t border-slate-200/80 text-[11px]">
                                <div className="flex items-center justify-between">
                                  <span className="font-semibold text-slate-500">Local Dev Engine:</span>
                                  <span className="font-mono text-slate-800 font-medium">{p.localTech}</span>
                                </div>
                                <div className="flex items-center justify-between">
                                  <span className="font-semibold text-slate-500">AWS Target Tier:</span>
                                  <span className="font-mono text-sky-700 font-medium">{p.awsTarget}</span>
                                </div>
                              </div>

                              <ul className="space-y-1 text-[11px] text-slate-500 pt-1">
                                {p.bullets.map((b, bIdx) => (
                                  <li key={bIdx} className="flex items-center space-x-1.5">
                                    <span className="text-emerald-500">✓</span>
                                    <span>{b}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* Embedded Interactive Viewer for Diagrams, Slides, Icon Studio, Playbooks */
                    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
                      <div className="px-6 py-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs text-slate-600">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-slate-900">
                            {archView === "epc_diagram" ? "Interactive EPC Workflow Diagram (Bank on Left -> PeX on Right)" :
                             archView === "exec_slide" ? "16:9 Executive Presentation Slide (Event-Driven Architecture)" :
                             archView === "icon_studio" ? "Executive Vector Icon Studio (189 Icons Across 25 Categories)" :
                             archView === "playbook" ? "41 Exception Playbooks Taxonomy Across 5 BIAN Domains" :
                             "PeX Executive 1-Pager Briefing & Strategic Moats"}
                          </span>
                        </div>
                        <div className="flex items-center space-x-3 text-[11px]">
                          <span className="text-emerald-600 font-semibold font-mono flex items-center space-x-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                            <span>LIVE PREVIEW</span>
                          </span>
                          <button
                            onClick={() => setArchFullscreen(!archFullscreen)}
                            className="text-sky-600 hover:text-sky-700 font-semibold flex items-center space-x-1"
                          >
                            <span>{archFullscreen ? "Standard Height" : "Expand Height (900px)"}</span>
                          </button>
                        </div>
                      </div>

                      <div className={`w-full transition-all duration-300 relative bg-slate-900 ${archFullscreen ? "h-[900px]" : "h-[720px]"}`}>
                        <iframe
                          key={archIframeKey}
                          src={
                            archView === "epc_diagram" ? "/PeX_EPC_Workflow_Diagram.html" :
                            archView === "exec_slide" ? "/PeX_Event_Driven_Architecture_Slide.html" :
                            archView === "icon_studio" ? "/pex_executive_icons_customizer.html" :
                            archView === "playbook" ? "/PeX_Playbook_1Pager.html" :
                            "/PeX_Executive_1Pager.html"
                          }
                          title="Architecture Viewer"
                          className="w-full h-full border-0"
                        />
                      </div>
                    </div>
                  )}

                  {/* 9 Numbered Steps Mapping Summary Card */}
                  <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-3">
                    <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                      <span>Numbered Event-Driven Process Chain Mapping (Bank on Left -> PeX on Right)</span>
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-9 gap-2 pt-1 text-center">
                      {[
                        { num: "1", label: "Exception Ingested", sub: "Bank -> PeX API" },
                        { num: "2", label: "PII Tokenized", sub: "TOK-* Surrogates" },
                        { num: "3", label: "Evidence Gathered", sub: "Fed/SWIFT Lookups" },
                        { num: "4", label: "Context Assembled", sub: "BIAN Playbooks" },
                        { num: "5", label: "AI Grounded", sub: "Multi-Hypothesis" },
                        { num: "6", label: "Maker Review", sub: "Analyst Workbench" },
                        { num: "7", label: "Approver Sign-Off", sub: "Dual-Auth Gate" },
                        { num: "8", label: "Governed Dispatch", sub: "Idempotent Wire" },
                        { num: "9", label: "Audit Sealed", sub: "SHA-256 Merkle" },
                      ].map((s) => (
                        <div key={s.num} className="p-2.5 rounded-xl border border-slate-200 bg-slate-50 flex flex-col items-center justify-center">
                          <div className="w-6 h-6 rounded-full bg-slate-900 text-white font-mono text-[11px] font-bold flex items-center justify-center mb-1">
                            {s.num}
                          </div>
                          <div className="text-[11px] font-bold text-slate-800 leading-tight">{s.label}</div>
                          <div className="text-[9px] text-slate-500 font-mono mt-0.5">{s.sub}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}\n'''

if '{tab === "architecture" && (' not in code:
    code = code.replace('            </main>', arch_tab_block + '            </main>')

with open(guided_file, "w", encoding="utf-8") as f:
    f.write(code)

print("build_guided_frontend.py successfully updated!")
