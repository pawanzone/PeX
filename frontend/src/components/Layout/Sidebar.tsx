import React from "react";
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
  Workflow,
} from "lucide-react";

export type NavTab =
  | "command_center"
  | "architecture"
  | "intake"
  | "worklist"
  | "approvals"
  | "investigations"
  | "analytics"
  | "swift_iso"
  | "governance"
  | "ontology"
  | "copilot";

export interface NavItem {
  id: NavTab;
  label: string;
  icon: any;
  badge?: number;
  badgeText?: string;
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

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
  const navSections: NavSection[] = [
    {
      title: "OVERVIEW & ARCHITECTURE",
      items: [
        { id: "command_center" as NavTab, label: "Command Center", icon: LayoutDashboard },
        { id: "architecture" as NavTab, label: "Architecture & Workflows", icon: Workflow, badgeText: "DEV" },
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
                    {item.badgeText && (
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold font-mono ${
                        isActive ? "bg-white/20 text-white" : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                      }`}>
                        {item.badgeText}
                      </span>
                    )}
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
