import React from "react";
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
