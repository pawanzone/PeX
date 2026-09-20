import React, { useState } from "react";
import {
  Workflow,
  Layers,
  FileText,
  Maximize2,
  ExternalLink,
  Download,
  Database,
  ShieldCheck,
  Cpu,
  Boxes,
  CheckCircle2,
  RefreshCw,
  Eye,
  FileImage
} from "lucide-react";

export const ArchitectureWorkflows: React.FC = () => {
  const [activeView, setActiveView] = useState<
    "epc_diagram" | "exec_slide" | "pillars" | "icon_studio" | "playbook" | "executive_1pager"
  >("epc_diagram");
  const [iframeKey, setIframeKey] = useState<number>(0);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  const reloadIframe = () => setIframeKey((prev) => prev + 1);

  const views = [
    {
      id: "epc_diagram",
      title: "EPC Workflow Diagram",
      subtitle: "Bank-to-PeX Numbered 9-Step Process Chain",
      icon: Workflow,
      badge: "APPROVED",
      badgeColor: "bg-emerald-50 text-emerald-700 border-emerald-200",
      url: "/PeX_EPC_Workflow_Diagram.html",
      downloadJpg: "/pex_workflow_diagram_epc.jpg",
    },
    {
      id: "exec_slide",
      title: "16:9 Executive Slide",
      subtitle: "Event-Driven Processing Slide for PPT",
      icon: FileImage,
      badge: "PPT READY",
      badgeColor: "bg-indigo-50 text-indigo-700 border-indigo-200",
      url: "/PeX_Event_Driven_Architecture_Slide.html",
      downloadJpg: "/pex_agentic_workflow_slide.jpg",
    },
    {
      id: "pillars",
      title: "8 Enterprise Pillars",
      subtitle: "Production Target Architecture & AWS Roadmap",
      icon: Layers,
      badge: "1 OF 8 IN PROGRESS",
      badgeColor: "bg-amber-50 text-amber-700 border-amber-200",
    },
    {
      id: "icon_studio",
      title: "Executive Icon Studio",
      subtitle: "189 Vector Enterprise Icons & Palettes",
      icon: Cpu,
      badge: "25 CATEGORIES",
      badgeColor: "bg-sky-50 text-sky-700 border-sky-200",
      url: "/pex_executive_icons_customizer.html",
    },
    {
      id: "playbook",
      title: "41 Exception Playbooks",
      subtitle: "Taxonomy across 5 BIAN Market Domains",
      icon: Boxes,
      badge: "COMPLETE",
      badgeColor: "bg-purple-50 text-purple-700 border-purple-200",
      url: "/PeX_Playbook_1Pager.html",
      downloadJpg: "/pex_playbook_1pager_1789401912830.jpg",
    },
    {
      id: "executive_1pager",
      title: "Executive 1-Pager",
      subtitle: "Executive Summary & Business Value Moats",
      icon: FileText,
      badge: "v2.0",
      badgeColor: "bg-slate-100 text-slate-700 border-slate-200",
      url: "/PeX_Executive_1Pager.html",
      downloadJpg: "/pex_exec_1pager_v2_1789401594230.jpg",
    },
  ];

  const currentViewObj = views.find((v) => v.id === activeView);

  const pillarsList = [
    {
      number: "1",
      title: "Persistent Relational Database Layer",
      status: "CURRENT FOCUS",
      statusColor: "bg-amber-100 text-amber-800 border-amber-300 animate-pulse",
      localTech: "SQLite 3 (pex_enterprise.db) + SQLAlchemy 2.0 ORM",
      awsTarget: "AWS Aurora PostgreSQL / Amazon RDS Multi-AZ Cluster",
      description: "Complete relational persistence across Cases, Token Vault, Recommendations, Maker-Checker Approvals, Settlements, and Immutable Audit Chains.",
      icon: Database,
      details: [
        "Configured via plug-and-play DATABASE_URL env variable",
        "Connection pooling & auto-reconnect (pool_size=20, max_overflow=10)",
        "Zero-loss migration from local development to cloud production"
      ]
    },
    {
      number: "2",
      title: "Isolated Tokenization Vault & PII Boundary",
      status: "ONLINE",
      statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
      localTech: "SHA-256 HMAC Vault with TOK-* surrogate generation",
      awsTarget: "AWS KMS / Secrets Manager + Dedicated RDS Microservice",
      description: "Strict zero-trust boundary ensuring AI inference engines never see raw PII, account numbers, or party identities.",
      icon: ShieldCheck,
      details: [
        "Bidirectional deterministic surrogate mapping",
        "Display masking & PCI/GDPR compliance",
        "Token isolation between banks and internal reasoning context"
      ]
    },
    {
      number: "3",
      title: "Multi-Provider Model Gateway",
      status: "ONLINE",
      statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
      localTech: "Deterministic Mock Reasoner + Gemini 1.5 Pro + OpenAI GPT-4o",
      awsTarget: "Amazon Bedrock (Claude 3.5 Sonnet / Llama 3) + AWS Lambda",
      description: "Pluggable LLM reasoning engine with strict JSON schema adherence and zero financial hallucination guardrails.",
      icon: Cpu,
      details: [
        "Deterministic fallback modes for offline / sandbox execution",
        "Confidence scoring & multi-hypothesis elimination ranking",
        "Consequence simulation with clearing cutoff calculations"
      ]
    },
    {
      number: "4",
      title: "Retrieval-Augmented Evidence & ICD Adapters",
      status: "ONLINE",
      statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
      localTech: "In-memory Staging Service + BIAN SOP Playbooks (41 profiles)",
      awsTarget: "Amazon OpenSearch Vector DB + Amazon S3 Evidence Lake",
      description: "Automated queries against Federal Reserve cutoffs, SWIFT SSI directories, core banking ledgers, and KYC databases.",
      icon: Boxes,
      details: [
        "90-day transaction history & temporal clustering",
        "Confirmation of Payee (CoP) fuzzy matching & MOD-97 checksums",
        "Domain-specific grounding across all 5 BIAN exception domains"
      ]
    },
    {
      number: "5",
      title: "Maker-Checker & Dual Authorization Engine",
      status: "ONLINE",
      statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
      localTech: "RBAC Engine + $250k High-Value Threshold Gate",
      awsTarget: "AWS IAM + Cognito / Corporate SSO (Okta/SAML)",
      description: "Strict Segregation of Duties (SoD). Tier-1 Operations Approvers + Tier-2 Risk Approvers for large value wires.",
      icon: ShieldCheck,
      details: [
        "Prevent same-actor Maker & Checker collisions",
        "Mandatory dual-approval chain for transactions >= $250k",
        "Audit-stamped return to Maker for rework workflows"
      ]
    },
    {
      number: "6",
      title: "Governed Action Dispatch & Idempotency",
      status: "ONLINE",
      statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
      localTech: "Idempotent Action Executor + Delivery Receipt Generator",
      awsTarget: "Amazon SQS FIFO + Amazon EventBridge + Bank API Gateways",
      description: "Zero autonomous execution. Only dispatches approved repairs and returns once formal human authorization is recorded.",
      icon: Workflow,
      details: [
        "Strict idempotency keys preventing double-dispatch",
        "Outbound ISO 20022 pacs.008 / pacs.004 generation",
        "External settlement delivery receipt reconciliation"
      ]
    },
    {
      number: "7",
      title: "Cryptographic SHA-256 Audit Hash Chain",
      status: "ONLINE",
      statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
      localTech: "Linear Hash Chaining (prev_hash -> current_hash)",
      awsTarget: "Amazon QLDB / Immutable S3 Object Lock + Ledger",
      description: "Tamper-evident cryptographic provenance logging across all 20 lifecycle stages from ingestion to final settlement.",
      icon: Layers,
      details: [
        "Deterministic SHA-256 block calculation per event",
        "On-demand cryptographic verification endpoint (/verify-chain)",
        "Regulatory compliance export for internal and external auditors"
      ]
    },
    {
      number: "8",
      title: "Operations Control Plane & Telemetry",
      status: "ONLINE",
      statusColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
      localTech: "FastAPI Telemetry Endpoints + React Real-Time Dashboard",
      awsTarget: "Amazon CloudWatch + OpenTelemetry + Grafana Dashboard",
      description: "Live SLA tracking, queue distribution, at-risk capital metrics, and operations velocity analytics.",
      icon: ShieldCheck,
      details: [
        "Dynamic 1h / 4h / 24h clearing cutoff urgency tracking",
        "Queue health monitoring (Repair, Compliance, Treasury, Investigation)",
        "Real-time SLA resolution velocity graphs"
      ]
    },
  ];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="bg-slate-900 text-white rounded-xl p-6 shadow-md border border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-sky-500/20 text-sky-400 border border-sky-500/30">
                <Workflow className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-white flex items-center space-x-2">
                  <span>Architecture & Workflows Studio</span>
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono font-medium">
                    DEV & REVIEW MODE
                  </span>
                </h1>
                <p className="text-xs text-slate-400">
                  Interactive Event-Driven Architecture, Bank-to-PeX EPC Process Chains, 8 Enterprise Pillars & PPT Assets
                </p>
              </div>
            </div>
          </div>

          {/* Quick Action Controls */}
          <div className="flex items-center space-x-2.5">
            {currentViewObj?.downloadJpg && (
              <a
                href={currentViewObj.downloadJpg}
                download
                className="flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition shadow-sm"
              >
                <Download className="w-3.5 h-3.5 text-sky-400" />
                <span>Download JPG for PPT</span>
              </a>
            )}
            {currentViewObj?.url && (
              <a
                href={currentViewObj.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium shadow-sm transition"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Open in Full Tab</span>
              </a>
            )}
            {currentViewObj?.url && (
              <button
                onClick={reloadIframe}
                title="Reload diagram"
                className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* View Switcher Tabs */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 mt-6 pt-5 border-t border-slate-800">
          {views.map((v) => {
            const Icon = v.icon;
            const isActive = activeView === v.id;
            return (
              <button
                key={v.id}
                onClick={() => setActiveView(v.id as any)}
                className={`flex flex-col items-start p-3 rounded-lg text-left transition border ${
                  isActive
                    ? "bg-slate-800 border-sky-500 text-white shadow-sm ring-1 ring-sky-500"
                    : "bg-slate-900/60 border-slate-800 text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                }`}
              >
                <div className="flex items-center justify-between w-full mb-1.5">
                  <Icon className={`w-4 h-4 ${isActive ? "text-sky-400" : "text-slate-500"}`} />
                  <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-semibold border ${v.badgeColor}`}>
                    {v.badge}
                  </span>
                </div>
                <div className="text-xs font-bold leading-snug">{v.title}</div>
                <div className="text-[10px] text-slate-500 line-clamp-1 mt-0.5">{v.subtitle}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Content Area */}
      {activeView === "pillars" ? (
        /* 8 Enterprise Pillars Blueprint View */
        <div className="space-y-6">
          <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900">
                  PeX Enterprise Architecture: 8 Foundational Pillars
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Institutional design roadmap from local execution to enterprise AWS Cloud deployment.
                </p>
              </div>
              <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded bg-sky-50 text-sky-700 border border-sky-200">
                8 OF 8 PILLARS DEFINED
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              {pillarsList.map((p) => {
                const Icon = p.icon;
                return (
                  <div
                    key={p.number}
                    className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white transition hover:shadow-sm space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-lg bg-slate-900 text-white font-bold font-mono text-sm flex items-center justify-center shrink-0">
                          {p.number}
                        </div>
                        <div>
                          <h3 className="text-sm font-bold text-slate-900">{p.title}</h3>
                          <span className={`inline-block text-[10px] font-bold font-mono px-2 py-0.5 rounded border mt-1 ${p.statusColor}`}>
                            {p.status}
                          </span>
                        </div>
                      </div>
                      <Icon className="w-5 h-5 text-slate-400" />
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed">{p.description}</p>

                    <div className="space-y-2 pt-2 border-t border-slate-200/80 text-[11px]">
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
                      {p.details.map((d, dIdx) => (
                        <li key={dIdx} className="flex items-center space-x-1.5">
                          <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />
                          <span>{d}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        /* Interactive Embedded Viewer (EPC Diagram, Slide, Icon Studio, Playbook, 1-Pager) */
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          {/* Viewer Toolbar */}
          <div className="px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs text-slate-600">
            <div className="flex items-center space-x-2">
              <span className="font-bold text-slate-800">{currentViewObj?.title}</span>
              <span className="text-slate-300">•</span>
              <span className="text-slate-500">{currentViewObj?.subtitle}</span>
            </div>
            <div className="flex items-center space-x-3 text-[11px]">
              <span className="flex items-center space-x-1 text-slate-500">
                <Eye className="w-3.5 h-3.5 text-slate-400" />
                <span>Interactive Live View</span>
              </span>
              <button
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="flex items-center space-x-1 text-sky-600 hover:text-sky-700 font-medium"
              >
                <Maximize2 className="w-3.5 h-3.5" />
                <span>{isFullscreen ? "Standard Height" : "Expand View"}</span>
              </button>
            </div>
          </div>

          {/* Embedded Iframe */}
          <div
            className={`w-full transition-all duration-300 relative bg-slate-900 ${
              isFullscreen ? "h-[900px]" : "h-[700px]"
            }`}
          >
            {currentViewObj?.url ? (
              <iframe
                key={iframeKey}
                src={currentViewObj.url}
                title={currentViewObj.title}
                className="w-full h-full border-0"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-slate-400 text-sm">
                No embedded preview available
              </div>
            )}
          </div>
        </div>
      )}

      {/* Numbered Steps Mapping Summary Card */}
      <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm space-y-3">
        <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
          <span>Numbered Event-Driven Process Chain Mapping (Bank on Left &rarr; PeX on Right)</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-9 gap-2 pt-1 text-center">
          {[
            { num: "1", label: "Exception Ingested", sub: "Bank &rarr; PeX API" },
            { num: "2", label: "PII Tokenized", sub: "TOK-* Surrogates" },
            { num: "3", label: "Evidence Gathered", sub: "Fed/SWIFT Lookups" },
            { num: "4", label: "Context Assembled", sub: "BIAN Playbooks" },
            { num: "5", label: "AI Grounded", sub: "Multi-Hypothesis" },
            { num: "6", label: "Maker Review", sub: "Analyst Workbench" },
            { num: "7", label: "Approver Sign-Off", sub: "Dual-Auth Gate" },
            { num: "8", label: "Governed Dispatch", sub: "Idempotent Wire" },
            { num: "9", label: "Audit Sealed", sub: "SHA-256 Merkle" },
          ].map((s) => (
            <div key={s.num} className="p-2.5 rounded-lg border border-slate-200 bg-slate-50 flex flex-col items-center justify-center">
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
  );
};
