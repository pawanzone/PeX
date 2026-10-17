import React from "react";
import { PeXCase } from "../../types";
import { statusMeta, TONE_CLASSES, StatusTone } from "../../lib/statusMeta";
import { Bot, User, ShieldCheck, Landmark, Cog, Clock } from "lucide-react";

type Step = NonNullable<PeXCase["audit_timeline"]>[number];

function roleIcon(role: string) {
  const r = (role || "").toUpperCase();
  if (r.includes("AI") || r.includes("AGENT") || r.includes("MODEL")) return Bot;
  if (r.includes("BANK") || r.includes("RAIL")) return Landmark;
  if (r.includes("SYSTEM") || r.includes("CONTROL") || r.includes("POLICY")) return ShieldCheck;
  if (r.includes("WORKER") || r.includes("PIPELINE")) return Cog;
  return User;
}

function stepTone(step: Step, isLast: boolean): StatusTone {
  const t = `${step.action_title} ${step.summary}`.toUpperCase();
  if (/REJECT|BLOCK|FAIL|DENIED|VIOLAT/.test(t)) return "red";
  if (/AWAIT|WAIT|PENDING|HANDED|DISPATCH|UNKNOWN/.test(t)) return isLast ? "blue" : "amber";
  if (/APPROV|PASS|VALID|CONFIRM|SETTLED|EXECUTED|RESOLVED/.test(t)) return "green";
  return isLast ? "blue" : "grey";
}

export const BANK_BANNER = "PeX never executes or settles payments. The bank does.";

export const CaseJourney: React.FC<{ c: PeXCase }> = ({ c }) => {
  const steps = [...(c.audit_timeline ?? [])].sort((a, b) => a.step_index - b.step_index);
  const meta = statusMeta(c.status);
  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-900">Case journey</h3>
        <span className="text-[11px] text-slate-500">Current state: <strong className="text-slate-800">{meta.label}</strong></span>
      </div>
      <div className="px-5 py-2 bg-slate-50 border-b border-slate-100 text-[11px] text-slate-600 flex items-center space-x-1.5">
        <Landmark className="w-3.5 h-3.5 text-slate-400" />
        <span>{BANK_BANNER}</span>
      </div>
      {steps.length === 0 ? (
        <div className="p-6 text-xs text-slate-400 flex items-center space-x-2">
          <Clock className="w-4 h-4" />
          <span>No journey events recorded for this case yet.</span>
        </div>
      ) : (
        <ol className="p-5 space-y-0">
          {steps.map((s, i) => {
            const last = i === steps.length - 1;
            const tone = stepTone(s, last);
            const t = TONE_CLASSES[tone];
            const Icon = roleIcon(s.actor_role);
            return (
              <li key={s.step_index} className="relative pl-10 pb-5 last:pb-0">
                {!last && <span className="absolute left-[13px] top-7 bottom-0 w-px bg-slate-200" />}
                <span className={`absolute left-0 top-0 w-7 h-7 rounded-full border flex items-center justify-center ${t.chip}`}>
                  <Icon className="w-3.5 h-3.5" />
                </span>
                <div className="flex items-baseline justify-between gap-3">
                  <div className="text-xs font-semibold text-slate-800">{s.action_title}</div>
                  <div className="text-[10px] font-mono text-slate-400 shrink-0">{s.timestamp ? new Date(s.timestamp).toLocaleString() : ""}</div>
                </div>
                <div className="text-[11px] text-slate-500">{s.actor_name} <span className="font-mono text-slate-400">({s.actor_role})</span></div>
                {s.summary && <div className="text-[11px] text-slate-600 mt-0.5">{s.summary}</div>}
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
};
