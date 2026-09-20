import os

comp_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\src\components"

# 1. Auth/LoginModal.tsx
with open(os.path.join(comp_dir, "Auth", "LoginModal.tsx"), "w", encoding="utf-8") as f:
    f.write('''import React from "react";
import { UserPersona } from "../../types";
import { ShieldCheck, UserCheck, Lock } from "lucide-react";

interface Props {
  personas: UserPersona[];
  currentPersona: UserPersona | null;
  onSelectPersona: (persona: UserPersona) => void;
  onClose?: () => void;
}

export const LoginModal: React.FC<Props> = ({
  personas,
  currentPersona,
  onSelectPersona,
  onClose,
}) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
        <div className="bg-slate-900 px-6 py-5 text-white flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-sky-500/20 border border-sky-400/30 flex items-center justify-center text-sky-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-semibold tracking-tight">Institutional Access & Persona Switcher</h2>
              <p className="text-xs text-slate-400">Select an authenticated banking role to test RBAC & Maker-Checker rules</p>
            </div>
          </div>
          {onClose && (
            <button onClick={onClose} className="text-slate-400 hover:text-white text-sm font-medium">✕</button>
          )}
        </div>

        <div className="p-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {personas.map((p) => {
              const isSelected = currentPersona?.user_id === p.user_id;
              return (
                <div
                  key={p.user_id}
                  onClick={() => onSelectPersona(p)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all duration-150 relative ${
                    isSelected
                      ? "border-sky-500 bg-sky-50/70 ring-2 ring-sky-500/20 shadow-sm"
                      : "border-slate-200 hover:border-slate-300 hover:bg-slate-50/80"
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold font-mono shrink-0 ${
                      p.role === "OPERATOR" ? "bg-blue-100 text-blue-700" :
                      p.role === "OPERATIONS_APPROVER" ? "bg-emerald-100 text-emerald-700" :
                      p.role === "COMPLIANCE_APPROVER" ? "bg-amber-100 text-amber-700" :
                      p.role === "RISK_APPROVER" ? "bg-purple-100 text-purple-700" : "bg-slate-100 text-slate-700"
                    }`}>
                      {p.avatar_initials}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-semibold text-slate-900 truncate">{p.name}</h4>
                        {isSelected && <span className="text-xs text-sky-600 font-bold">Active</span>}
                      </div>
                      <p className="text-xs text-slate-500 font-medium">{p.title}</p>
                      <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-100 pt-1.5">
                        <span className="font-mono">{p.user_id}</span>
                        <span>{p.max_approval_amount > 0 ? `Limit: $${(p.max_approval_amount / 1000).toFixed(0)}k` : "Maker Only"}</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-6 bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex items-center justify-between text-xs text-slate-600">
            <div className="flex items-center space-x-2">
              <Lock className="w-4 h-4 text-slate-400" />
              <span>Zero-trust session token active. Sensitive data boundary enforced.</span>
            </div>
            <span className="font-mono text-slate-400 text-[10px]">PEX_AUTH_GATEWAY: ONLINE</span>
          </div>
        </div>
      </div>
    </div>
  );
};
''')

# 2. Layout/Header.tsx
with open(os.path.join(comp_dir, "Layout", "Header.tsx"), "w", encoding="utf-8") as f:
    f.write('''import React from "react";
import { UserPersona } from "../../types";
import { Search, UserCheck, ShieldAlert, Wifi } from "lucide-react";

interface Props {
  currentPersona: UserPersona | null;
  onOpenPersonaModal: () => void;
  searchQuery: string;
  onSearchChange: (val: string) => void;
}

export const Header: React.FC<Props> = ({
  currentPersona,
  onOpenPersonaModal,
  searchQuery,
  onSearchChange,
}) => {
  return (
    <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 sticky top-0 z-30">
      <div className="flex items-center space-x-4 flex-1 max-w-xl">
        <div className="relative w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search case, UETR, TRN, party, or ISO message..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all placeholder:text-slate-400 text-slate-800"
          />
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 bg-amber-50 border border-amber-200 rounded-md text-[11px] font-medium text-amber-700">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
          <span>DEMO • NO BANK TRAFFIC</span>
        </div>

        {currentPersona && (
          <button
            onClick={onOpenPersonaModal}
            className="flex items-center space-x-2.5 pl-2 pr-3 py-1 rounded-lg border border-slate-200 hover:border-slate-300 bg-slate-50 hover:bg-slate-100 transition-all text-left"
          >
            <div className="w-7 h-7 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-bold font-mono">
              {currentPersona.avatar_initials}
            </div>
            <div className="hidden md:block">
              <div className="text-xs font-semibold text-slate-800 leading-tight flex items-center space-x-1">
                <span>{currentPersona.name}</span>
                <span className="text-[10px] text-slate-400 font-mono font-normal">({currentPersona.user_id})</span>
              </div>
              <div className="text-[10px] text-slate-500 font-medium leading-tight">{currentPersona.title}</div>
            </div>
          </button>
        )}
      </div>
    </header>
  );
};
''')

# 3. Layout/Sidebar.tsx
with open(os.path.join(comp_dir, "Layout", "Sidebar.tsx"), "w", encoding="utf-8") as f:
    f.write('''import React from "react";
import {
  LayoutDashboard,
  PlusCircle,
  ListOrdered,
  CheckCircle2,
  Activity,
  BarChart3,
  Network,
  ShieldAlert,
  GitFork,
  BotMessageSquare,
} from "lucide-react";

export type NavTab =
  | "command_center"
  | "intake"
  | "worklist"
  | "approvals"
  | "investigations"
  | "analytics"
  | "swift_iso"
  | "governance"
  | "ontology"
  | "copilot";

interface Props {
  currentTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  pendingApprovalsCount?: number;
}

export const Sidebar: React.FC<Props> = ({
  currentTab,
  onTabChange,
  pendingApprovalsCount = 0,
}) => {
  const navSections = [
    {
      title: "OVERVIEW",
      items: [
        { id: "command_center" as NavTab, label: "Command Center", icon: LayoutDashboard },
      ],
    },
    {
      title: "EXCEPTION OPERATIONS",
      items: [
        { id: "intake" as NavTab, label: "Payment Intake", icon: PlusCircle },
        { id: "worklist" as NavTab, label: "Exception Worklist", icon: ListOrdered },
        { id: "approvals" as NavTab, label: "Role Approvals", icon: CheckCircle2, badge: pendingApprovalsCount },
        { id: "investigations" as NavTab, label: "Investigations Hub", icon: Activity },
      ],
    },
    {
      title: "INTELLIGENCE & CONNECTIVITY",
      items: [
        { id: "analytics" as NavTab, label: "Operations Analytics", icon: BarChart3 },
        { id: "swift_iso" as NavTab, label: "SWIFT & ISO Center", icon: Network },
        { id: "ontology" as NavTab, label: "Payment Ontology", icon: GitFork },
        { id: "copilot" as NavTab, label: "AI Repair Copilot", icon: BotMessageSquare },
      ],
    },
    {
      title: "CONFIGURE & GOVERN",
      items: [
        { id: "governance" as NavTab, label: "Controls & Governance", icon: ShieldAlert },
      ],
    },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 h-screen sticky top-0 select-none">
      <div className="h-14 flex items-center px-6 border-b border-slate-800 space-x-3">
        <div className="w-7 h-7 rounded-lg bg-sky-500 flex items-center justify-center text-white font-bold font-mono text-sm shadow-md shadow-sky-500/20">
          P
        </div>
        <div>
          <h1 className="text-sm font-bold text-white tracking-wider flex items-center space-x-1.5">
            <span>PeX Platform</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-400 font-mono font-medium">v1.0</span>
          </h1>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-6">
        {navSections.map((section, idx) => (
          <div key={idx} className="space-y-1">
            <h3 className="px-3 text-[10px] font-bold text-slate-400 tracking-wider uppercase font-mono">
              {section.title}
            </h3>
            <div className="space-y-0.5 pt-1">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = currentTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onTabChange(item.id)}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                      isActive
                        ? "bg-sky-600 text-white shadow-sm font-semibold"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                    }`}
                  >
                    <div className="flex items-center space-x-2.5">
                      <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-400"}`} />
                      <span>{item.label}</span>
                    </div>
                    {item.badge !== undefined && item.badge > 0 && (
                      <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold font-mono ${
                        isActive ? "bg-white text-sky-600" : "bg-sky-500/20 text-sky-400"
                      }`}>
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
        <span>ISO 20022 / CBPR+</span>
        <span className="text-emerald-400 font-mono flex items-center space-x-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>ONLINE</span>
        </span>
      </div>
    </aside>
  );
};
''')

print("Wrote LoginModal, Header, and Sidebar.")
