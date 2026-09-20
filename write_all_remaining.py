import os

comp_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\src\components"
src_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\src"

# 1. Governance/ControlsGovernance.tsx
with open(os.path.join(comp_dir, "Governance", "ControlsGovernance.tsx"), "w", encoding="utf-8") as f:
    f.write('''import React, { useState, useEffect } from "react";
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
''')

# 2. Ontology/PaymentOntology.tsx
with open(os.path.join(comp_dir, "Ontology", "PaymentOntology.tsx"), "w", encoding="utf-8") as f:
    f.write('''import React, { useState, useEffect } from "react";
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
''')

# 3. Copilot/AiCopilot.tsx
with open(os.path.join(comp_dir, "Copilot", "AiCopilot.tsx"), "w", encoding="utf-8") as f:
    f.write('''import React, { useState, useEffect } from "react";
import { fetchSops, sendCopilotChat } from "../../services/api";
import { BotMessageSquare, Send, BookOpen, ShieldCheck, RefreshCw } from "lucide-react";

export const AiCopilot: React.FC = () => {
  const [sops, setSops] = useState<any[]>([]);
  const [messages, setMessages] = useState<Array<{ sender: "user" | "bot"; text: string }>>([
    {
      sender: "bot",
      text: "Hello! I am your PeX Governed AI Copilot. You can ask me about beneficiary IBAN repair rules (SOP-114), high-value dual authorization thresholds (SOP-207), or pacs.004 return processing.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSops().then(setSops);
  }, []);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input;
    setInput("");
    setMessages((prev) => [...prev, { sender: "user", text: userText }]);
    setLoading(true);

    try {
      const res = await sendCopilotChat(userText);
      setMessages((prev) => [...prev, { sender: "bot", text: res.reply }]);
    } catch (err) {
      setMessages((prev) => [...prev, { sender: "bot", text: "Error connecting to AI Copilot service." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">AI Repair Copilot &amp; SOP Knowledge Base</h1>
        <p className="text-xs text-slate-500 mt-1">Grounded in institutional standard operating procedures with token cost tracking &amp; zero-trust redaction</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SOP Cards */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">INSTITUTIONAL SOPS</h3>
          {sops.map((s) => (
            <div key={s.sop_id} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-sky-700">{s.sop_id}</span>
                <span className="text-[10px] font-mono text-slate-400">{s.category}</span>
              </div>
              <h4 className="text-xs font-semibold text-slate-900">{s.title}</h4>
              <p className="text-[11px] text-slate-500 leading-snug">{s.summary}</p>
            </div>
          ))}
        </div>

        {/* Chat Window */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col h-[560px] lg:col-span-2 overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div className="flex items-center space-x-2">
              <BotMessageSquare className="w-4 h-4 text-sky-600" />
              <span className="text-xs font-bold text-slate-800">PeX Governed Assistant</span>
            </div>
            <span className="text-[10px] font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded">
              PII SHIELD: ACTIVE
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-lg p-3.5 rounded-2xl text-xs leading-relaxed ${
                  m.sender === "user" ? "bg-sky-600 text-white rounded-br-none" : "bg-slate-100 text-slate-800 rounded-bl-none"
                }`}>
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center space-x-2 text-xs text-slate-400">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Thinking...</span>
              </div>
            )}
          </div>

          <form onSubmit={handleSend} className="p-3 border-t border-slate-100 flex items-center gap-2 bg-white">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask Copilot about IBAN repair, dual auth rules, or SOP guidelines..."
              className="flex-1 px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            />
            <button
              type="submit"
              disabled={loading}
              className="p-2 bg-sky-600 hover:bg-sky-700 text-white rounded-xl transition-all"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
''')

# 4. App.tsx
with open(os.path.join(src_dir, "App.tsx"), "w", encoding="utf-8") as f:
    f.write('''import React, { useState, useEffect } from "react";
import { UserPersona, PeXCase, AnalyticsSummary } from "./types";
import {
  fetchPersonas,
  loginPersona,
  fetchAnalyticsSummary,
  fetchVelocity,
  fetchCases,
} from "./services/api";
import { Sidebar, NavTab } from "./components/Layout/Sidebar";
import { Header } from "./components/Layout/Header";
import { LoginModal } from "./components/Auth/LoginModal";
import { CommandCenter } from "./components/Dashboard/CommandCenter";
import { PaymentIntake } from "./components/Intake/PaymentIntake";
import { ExceptionWorklist } from "./components/Worklist/ExceptionWorklist";
import { ApprovalsWorkspace } from "./components/Approvals/ApprovalsWorkspace";
import { InvestigationsHub } from "./components/Investigations/InvestigationsHub";
import { OperationsAnalytics } from "./components/Analytics/OperationsAnalytics";
import { SwiftIsoCenter } from "./components/SwiftIso/SwiftIsoCenter";
import { ControlsGovernance } from "./components/Governance/ControlsGovernance";
import { PaymentOntology } from "./components/Ontology/PaymentOntology";
import { AiCopilot } from "./components/Copilot/AiCopilot";

export const App: React.FC = () => {
  const [personas, setPersonas] = useState<UserPersona[]>([]);
  const [currentPersona, setCurrentPersona] = useState<UserPersona | null>(null);
  const [isPersonaModalOpen, setIsPersonaModalOpen] = useState(false);

  const [currentTab, setCurrentTab] = useState<NavTab>("command_center");
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [velocity, setVelocity] = useState<Array<{ day: string; opened: number; resolved: number }>>([]);
  const [cases, setCases] = useState<PeXCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const loadInitialData = async () => {
    try {
      const pList = await fetchPersonas();
      setPersonas(pList);
      
      // Default to Daniel Osei (Operations Approver) or Amina Okafor
      const defaultUser = pList.find((p) => p.user_id === "APR-3191") || pList[0];
      if (defaultUser && !currentPersona) {
        setCurrentPersona(defaultUser);
      }

      const aData = await fetchAnalyticsSummary();
      setAnalytics(aData);

      const vData = await fetchVelocity();
      setVelocity(vData);

      const cData = await fetchCases();
      setCases(cData);
    } catch (err) {
      console.error("Initial load error:", err);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const handleSelectPersona = async (persona: UserPersona) => {
    try {
      await loginPersona(persona.user_id);
      setCurrentPersona(persona);
      setIsPersonaModalOpen(false);
    } catch (err) {
      console.error("Persona switch error:", err);
    }
  };

  const refreshCases = async () => {
    try {
      const cData = await fetchCases();
      setCases(cData);
      const aData = await fetchAnalyticsSummary();
      setAnalytics(aData);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      <Sidebar
        currentTab={currentTab}
        onTabChange={(tab) => setCurrentTab(tab)}
        pendingApprovalsCount={cases.filter((c) => c.status === "PENDING_APPROVAL" || c.status === "AWAITING_SECOND_APPROVAL").length}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header
          currentPersona={currentPersona}
          onOpenPersonaModal={() => setIsPersonaModalOpen(true)}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
        />

        <main className="flex-1 overflow-y-auto">
          {currentTab === "command_center" && (
            <CommandCenter
              analytics={analytics}
              velocity={velocity}
              cases={cases}
              onNavigateTab={(tab) => setCurrentTab(tab)}
              onSelectCase={(id) => {
                setSelectedCaseId(id);
                setCurrentTab("approvals");
              }}
            />
          )}

          {currentTab === "intake" && (
            <PaymentIntake
              onSuccess={(caseId) => {
                setSelectedCaseId(caseId);
                refreshCases();
                setCurrentTab("approvals");
              }}
            />
          )}

          {currentTab === "worklist" && (
            <ExceptionWorklist
              cases={cases}
              onSelectCase={(id) => setSelectedCaseId(id)}
              onNavigateApprovals={() => setCurrentTab("approvals")}
            />
          )}

          {currentTab === "approvals" && (
            <ApprovalsWorkspace
              cases={cases}
              selectedCaseId={selectedCaseId}
              onSelectCase={(id) => setSelectedCaseId(id)}
              currentPersona={currentPersona}
              onRefreshCases={refreshCases}
            />
          )}

          {currentTab === "investigations" && <InvestigationsHub />}
          {currentTab === "analytics" && <OperationsAnalytics analytics={analytics} />}
          {currentTab === "swift_iso" && <SwiftIsoCenter />}
          {currentTab === "governance" && <ControlsGovernance />}
          {currentTab === "ontology" && <PaymentOntology />}
          {currentTab === "copilot" && <AiCopilot />}
        </main>
      </div>

      {isPersonaModalOpen && (
        <LoginModal
          personas={personas}
          currentPersona={currentPersona}
          onSelectPersona={handleSelectPersona}
          onClose={() => setIsPersonaModalOpen(false)}
        />
      )}
    </div>
  );
};
''')

# 5. main.tsx
with open(os.path.join(src_dir, "main.tsx"), "w", encoding="utf-8") as f:
    f.write('''import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
''')

print("Wrote ControlsGovernance, PaymentOntology, AiCopilot, App.tsx, and main.tsx")
