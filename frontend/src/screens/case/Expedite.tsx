import React, { useState } from "react";
import { ArrowUp, Check, Clock, Zap } from "lucide-react";
import { StatusPill, useToast, cn } from "../../components/v2";
import { useV2 } from "../../services/v2/client";
import { getCaseExpedite, pingCase } from "../../services/v2/expedite";
import { errText } from "./parts";

/** Three-step ladder under the decision zone: ping the holder, escalate to the supervisor, then the head of operations. */
export const ExpediteLadder: React.FC<{ caseId: string; onSent?: () => void }> = ({ caseId, onSent }) => {
  const r = useV2(() => getCaseExpedite(caseId), [caseId]);
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("Cutoff approaching. Please prioritise.");
  const [busy, setBusy] = useState(false);
  const s = r.data;
  if (!s || (!s.can_ping && !s.levels.some((l) => l.sent))) return null;
  const next = s.levels[s.next_level - 1];
  const send = async () => {
    setBusy(true);
    try { const res = await pingCase(caseId, note, s.next_level); toast.push(res?.message ?? "Sent", "green"); setOpen(false); r.reload(); onSent?.(); }
    catch (e) { toast.push(errText(e), "red"); } finally { setBusy(false); }
  };
  return (
    <section aria-label="Expedite" className="bg-surface-card rounded-card border border-surface-line shadow-card p-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <h2 className="text-sm font-semibold text-pex-ink inline-flex items-center gap-1.5"><Zap className="w-4 h-4 text-pex-wait" aria-hidden />Expedite</h2>
        <ol className="flex flex-wrap items-center gap-2 text-xs flex-1">
          {s.levels.map((l) => (
            <li key={l.level} className={cn("inline-flex items-center gap-1.5 px-2 py-1 rounded-md border", l.sent ? "border-pex-wait/40 bg-amber-50" : "border-surface-line text-pex-muted")}>
              <span className="font-semibold">{l.level}</span><span>{l.title}</span>
              {l.sent && (l.status === "ACKNOWLEDGED" ? <Check className="w-3.5 h-3.5 text-pex-ok" aria-label="acknowledged" /> : <Clock className="w-3.5 h-3.5 text-pex-wait" aria-label="waiting" />)}
              {l.auto && <StatusPill tone="grey" dot={false}>auto</StatusPill>}
            </li>
          ))}
        </ol>
        {s.can_ping
          ? <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="px-3 py-1.5 text-sm font-medium rounded-lg bg-white border border-surface-line text-pex-primary hover:bg-slate-50 inline-flex items-center gap-1.5"><ArrowUp className="w-4 h-4" aria-hidden />{s.next_level === 1 ? "Ping" : "Escalate to"} {next.title.split(",")[0].replace(/ \(.*\)/, "")}</button>
          : <span className="text-xs text-pex-muted">{s.reason}</span>}
      </div>
      {open && (
        <div className="mt-3 grid gap-2">
          <label htmlFor="exp-note" className="text-xs text-pex-muted">Message to {next.title}</label>
          <textarea id="exp-note" value={note} onChange={(e) => setNote(e.target.value)} rows={2} className="py-2 px-2.5 text-sm rounded-lg border border-surface-line w-full" />
          <div className="flex gap-2"><button type="button" disabled={busy} onClick={send} className="px-3 py-1.5 text-sm font-medium rounded-lg bg-pex-primary text-white disabled:opacity-50">Send</button><button type="button" onClick={() => setOpen(false)} className="px-3 py-1.5 text-sm rounded-lg border border-surface-line bg-white">Cancel</button></div>
        </div>
      )}
    </section>
  );
};
