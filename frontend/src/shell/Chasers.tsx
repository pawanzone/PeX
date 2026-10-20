import React, { useCallback, useEffect, useRef, useState } from "react";
import { Bell, Zap, X } from "lucide-react";
import { Avatar, StatusPill, cn } from "../components/v2";
import { navigate, routes } from "../lib/router";
import { ackExpedite, getExpedite, type ChaserItem, type ExpediteInbox } from "../services/v2/expedite";
import { useSession } from "./session";

const LEVEL_TONE: Record<number, "amber" | "red" | "purple"> = { 1: "amber", 2: "red", 3: "purple" };

const Item: React.FC<{ it: ChaserItem; onReview: (it: ChaserItem) => void; onAck: (it: ChaserItem) => void }> = ({ it, onReview, onAck }) => (
  <li className={cn("p-3 border-b border-surface-line last:border-0", it.status === "UNREAD" ? "bg-amber-50/40" : "")}>
    <div className="flex items-start gap-2.5">
      <Avatar bare size="md" name={it.sender.name} system={it.auto} initials={it.auto ? "SW" : undefined} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-pex-ink truncate">{it.sender.name}</span>
          <StatusPill tone={LEVEL_TONE[it.level] ?? "amber"} dot={false}>Level {it.level}{it.auto ? " · auto" : ""}</StatusPill>
        </div>
        <div className="text-xs text-pex-muted">{it.level_title} · {it.age_minutes < 1 ? "just now" : `${it.age_minutes} min ago`}</div>
        <p className="text-sm text-pex-ink mt-1">{it.note}</p>
        <div className="text-xs text-pex-muted mt-1"><span className="pex-mono text-pex-primary">{it.case_id}</span> · {it.exception?.label} · {it.amount?.display}{it.cutoff?.time_left ? <> · <strong className={it.cutoff.band === "passed" || it.cutoff.band === "under_1h" ? "text-pex-block" : ""}>{it.cutoff.band === "passed" ? "cutoff passed" : `${it.cutoff.time_left} left`}</strong></> : null}</div>
        <div className="flex gap-2 mt-2">
          <button type="button" onClick={() => onReview(it)} className="px-3 py-1 text-xs font-medium rounded-lg bg-pex-primary text-white hover:bg-pex-primary-dark">Review now</button>
          {it.status === "UNREAD" ? <button type="button" onClick={() => onAck(it)} className="px-3 py-1 text-xs font-medium rounded-lg border border-surface-line bg-white hover:bg-slate-50">Acknowledge</button>
            : <span className="text-xs text-pex-ok self-center">Acknowledged{it.ack_by?.name ? ` by ${it.ack_by.name}` : ""}</span>}
        </div>
      </div>
    </div>
  </li>
);

/** Bell in the top bar. Shows chasers sent to me ("SLA Expedite Chasers") and the ones I sent. */
export const ChasersBell: React.FC = () => {
  const { persona, epoch } = useSession();
  const [data, setData] = useState<ExpediteInbox | null>(null);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const load = useCallback(async () => { try { setData(await getExpedite()); } catch { /* panel simply stays empty */ } }, []);
  useEffect(() => { if (!persona) return; void load(); const t = window.setInterval(load, 30000); return () => window.clearInterval(t); }, [persona, epoch, load]);
  useEffect(() => {
    if (!open) return;
    const off = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", off); document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", off); document.removeEventListener("keydown", esc); };
  }, [open]);
  const ack = async (it: ChaserItem) => { try { await ackExpedite(it.id); } finally { await load(); } };
  const review = async (it: ChaserItem) => { if (it.status === "UNREAD") { try { await ackExpedite(it.id); } catch { /* still open the case */ } } setOpen(false); navigate(routes.workCase(it.case_id)); void load(); };
  const unread = data?.unread ?? 0;
  return (
    <div ref={ref} className="relative">
      <button type="button" aria-haspopup="dialog" aria-expanded={open} onClick={() => { setOpen((o) => !o); void load(); }}
        aria-label={unread ? `Expedite requests: ${unread} unread` : "Expedite requests"} className="relative p-2 rounded-lg hover:bg-slate-100">
        <Bell className="w-5 h-5 text-pex-ink" aria-hidden />
        {unread > 0 && <span className="absolute -top-0.5 -right-0.5 min-w-[1.1rem] h-[1.1rem] px-1 rounded-full bg-pex-block text-white text-[10px] font-semibold flex items-center justify-center">{unread}</span>}
      </button>
      {open && (
        <div role="dialog" aria-label="SLA Expedite Chasers" className="absolute right-0 mt-1 w-[26rem] max-h-[75vh] overflow-y-auto bg-white border border-surface-line rounded-lg shadow-xl z-40">
          <div className="sticky top-0 bg-white px-3 py-2.5 border-b border-surface-line flex items-center justify-between">
            <h2 className="text-sm font-semibold text-pex-ink inline-flex items-center gap-2"><Zap className="w-4 h-4 text-pex-wait" aria-hidden />SLA Expedite Chasers</h2>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close" className="p-1 rounded hover:bg-slate-100"><X className="w-4 h-4" aria-hidden /></button>
          </div>
          {data?.items.length ? <ul>{data.items.map((it) => <Item key={it.id} it={it} onReview={review} onAck={ack} />)}</ul>
            : <p className="p-4 text-sm text-pex-muted">Nobody is chasing you. Requests to expedite a case appear here.</p>}
          {!!data?.sent.length && (
            <div className="border-t border-surface-line">
              <div className="px-3 pt-2 text-[11px] uppercase tracking-wide text-pex-muted">Sent by you</div>
              <ul>{data.sent.slice(0, 5).map((it) => (
                <li key={it.id} className="px-3 py-2 text-xs text-pex-muted flex items-center justify-between gap-2">
                  <span><span className="pex-mono text-pex-primary">{it.case_id}</span> · level {it.level} to {it.level_title}</span>
                  <StatusPill tone={it.status === "ACKNOWLEDGED" ? "green" : "amber"}>{it.status === "ACKNOWLEDGED" ? "Acknowledged" : "Waiting"}</StatusPill>
                </li>))}</ul>
            </div>
          )}
          <p className="px-3 py-2 text-[11px] text-pex-muted border-t border-surface-line">An unanswered request climbs one level after {data?.policy.auto_escalate_minutes ?? 15} minutes.</p>
        </div>
      )}
    </div>
  );
};
