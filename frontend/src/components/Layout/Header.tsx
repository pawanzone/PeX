import React from "react";
import { UserPersona, SystemInfo, OperationMode } from "../../types";
import { Search, UserCheck, ShieldAlert, Wifi } from "lucide-react";

interface Props {
  currentPersona: UserPersona | null;
  onOpenPersonaModal: () => void;
  searchQuery: string;
  onSearchChange: (val: string) => void;
  systemInfo?: SystemInfo | null;
  onSearchSubmit?: () => void;
}

const MODE_META: Record<OperationMode, { cls: string; tip: string }> = {
  SHADOW: { cls: "bg-slate-100 border-slate-300 text-slate-700", tip: "SHADOW: PeX analyses and records recommendations only. Dispatch to the bank is suppressed." },
  ASSISTED: { cls: "bg-sky-50 border-sky-200 text-sky-700", tip: "ASSISTED: AI recommends, controls validate, humans approve. Approved actions are handed to the bank adapter." },
  LIVE: { cls: "bg-emerald-50 border-emerald-200 text-emerald-700", tip: "LIVE: approved actions are handed to the real bank. The bank executes and confirms." },
};

export const Header: React.FC<Props> = ({
  currentPersona,
  onOpenPersonaModal,
  searchQuery,
  onSearchChange,
  systemInfo,
  onSearchSubmit,
}) => {
  const mode = systemInfo?.operation_mode;
  const bank = systemInfo?.bank_comm ?? "";
  const bankSimulated = !systemInfo || /simul/i.test(bank) || systemInfo.demo;
  const llm = systemInfo?.llm;
  return (
    <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 sticky top-0 z-30">
      <div className="flex items-center space-x-4 flex-1 max-w-xl">
        <div className="relative w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search case, UETR or party, then press Enter"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") onSearchSubmit?.(); }}
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all placeholder:text-slate-400 text-slate-800"
          />
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {mode && (
          <span title={MODE_META[mode].tip} className={`hidden sm:inline-flex px-2 py-1 border rounded-md text-[11px] font-semibold cursor-help ${MODE_META[mode].cls}`}>
            Mode: {mode}
          </span>
        )}
        <span
          title={bankSimulated ? "Bank communication is simulated. No real bank traffic is generated." : `Bank communication: ${bank}`}
          className={`hidden sm:inline-flex items-center space-x-1.5 px-2 py-1 border rounded-md text-[11px] font-medium cursor-help ${bankSimulated ? "bg-amber-50 border-amber-200 text-amber-700" : "bg-emerald-50 border-emerald-200 text-emerald-700"}`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${bankSimulated ? "bg-amber-500" : "bg-emerald-500"}`}></span>
          <span>Bank communication: {bankSimulated ? "SIMULATED" : bank.toUpperCase()}</span>
        </span>
        <span
          title={llm?.enabled ? `Local model ${llm.model ?? ""}. Advisory only: it cannot change values or STP eligibility.` : "No language model active. Deterministic rules only."}
          className="hidden md:inline-flex items-center space-x-1.5 px-2 py-1 border border-slate-200 bg-slate-50 rounded-md text-[11px] font-medium text-slate-600 cursor-help"
        >
          <span className={`w-1.5 h-1.5 rounded-full ${llm?.enabled ? (llm.reachable === false ? "bg-red-500" : "bg-emerald-500") : "bg-slate-300"}`}></span>
          <span>{llm?.enabled ? `LLM: ${llm.model ?? "local"}${llm.reachable === false ? " (offline)" : ""}` : "LLM: off"}</span>
        </span>

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
