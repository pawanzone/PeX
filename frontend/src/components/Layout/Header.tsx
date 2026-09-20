import React from "react";
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
