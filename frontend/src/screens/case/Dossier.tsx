import React, { useEffect, useRef, useState } from "react";
import { X, ChevronLeft, ChevronRight, Database, Search, FileCheck2, Scale, Timer, CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";
import { Loading, ErrorState, StatusPill, cn } from "../../components/v2";
import { useV2 } from "../../services/v2/client";
import { getDossier, type DossierStep } from "../../services/v2/dossier";
import { fmtDateTime } from "./parts";

const ICON: Record<number, React.ElementType> = { 1: Database, 2: Search, 3: FileCheck2, 4: Scale, 5: Timer };
const VERDICT: Record<string, { tone: "green" | "amber" | "red" | "grey"; icon: React.ElementType }> = {
  pass: { tone: "green", icon: CheckCircle2 }, review: { tone: "amber", icon: AlertTriangle }, fail: { tone: "red", icon: XCircle }, info: { tone: "grey", icon: Info } };

const Step: React.FC<{ s: DossierStep; children: React.ReactNode }> = ({ s, children }) => {
  const Icon = ICON[s.n] ?? Info;
  return (
    <li className="rounded-lg border border-surface-line bg-white p-3">
      <h3 className="text-sm font-semibold text-pex-ink flex items-center gap-2 mb-2">
        <span className="w-6 h-6 rounded-full bg-pex-primary-soft text-pex-primary-dark text-xs flex items-center justify-center" aria-hidden>{s.n}</span>
        <Icon className="w-4 h-4 text-pex-muted" aria-hidden />{s.title}
      </h3>
      <div className="text-sm text-pex-ink grid gap-1.5">{children}</div>
    </li>
  );
};
const KV: React.FC<{ k: string; children: React.ReactNode; mono?: boolean }> = ({ k, children, mono }) => (
  <div className="flex gap-3"><span className="w-28 shrink-0 text-xs text-pex-muted pt-0.5">{k}</span><span className={cn("min-w-0 break-words", mono && "pex-mono text-xs")}>{children}</span></div>
);

/** Right-hand drawer. All five steps stay in view; Previous / Next move between the case's evidence checks. */
export const Dossier: React.FC<{ caseId: string; evidenceId: string; onClose: () => void; onOpen: (id: string) => void }> = ({ caseId, evidenceId, onClose, onOpen }) => {
  const r = useV2(() => getDossier(caseId, evidenceId), [caseId, evidenceId]);
  const ref = useRef<HTMLDivElement>(null);
  const [prevFocus] = useState<Element | null>(() => document.activeElement);
  useEffect(() => { ref.current?.focus(); return () => { (prevFocus as HTMLElement | null)?.focus?.(); }; }, [prevFocus]);
  const d = r.data;
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") onClose();
    if (e.key === "ArrowLeft" && d?.prev_id && !(e.target as HTMLElement).closest("input,textarea")) onOpen(d.prev_id);
    if (e.key === "ArrowRight" && d?.next_id && !(e.target as HTMLElement).closest("input,textarea")) onOpen(d.next_id);
  };
  const s = (n: number) => d?.steps.find((x) => x.n === n);
  const s1 = s(1), s2 = s(2), s3 = s(3), s4 = s(4), s5 = s(5);
  const V = VERDICT[s4?.verdict ?? "info"] ?? VERDICT.info;
  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="presentation">
      <div className="absolute inset-0 bg-slate-900/40" onClick={onClose} aria-hidden />
      <div ref={ref} tabIndex={-1} role="dialog" aria-modal="true" aria-label="Evidence dossier" onKeyDown={onKey} className="relative w-full max-w-xl h-full bg-surface overflow-y-auto shadow-2xl outline-none">
        <header className="sticky top-0 z-10 bg-white border-b border-surface-line px-5 py-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-xs text-pex-muted">Evidence dossier{d ? ` · check ${d.position} of ${d.total}` : ""}</div>
            <h2 className="text-lg font-semibold text-pex-ink truncate">{d?.check ?? "Loading…"}</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Close dossier" className="p-1.5 rounded-lg hover:bg-slate-100"><X className="w-5 h-5" aria-hidden /></button>
        </header>
        <div className="p-5">
          {r.loading && !d ? <Loading /> : r.error || !d ? <ErrorState message={r.error ?? "Not found"} unavailable={r.unavailable} onRetry={r.reload} /> : (
            <>
              <nav aria-label="Checks in this case" className="flex flex-wrap gap-1.5 mb-4">
                {d.summary.map((x) => (
                  <button key={x.id} type="button" onClick={() => onOpen(x.id)} aria-current={x.id === d.evidence_id ? "step" : undefined}
                    className={cn("px-2 py-1 rounded-md text-xs border", x.id === d.evidence_id ? "bg-pex-primary text-white border-pex-primary" : "bg-white text-pex-muted border-surface-line hover:bg-slate-50")}>{x.check}</button>
                ))}
              </nav>
              <ol className="grid gap-3">
                {s1 && <Step s={s1}>
                  <KV k="System">{s1.system_name} <span className="text-xs text-pex-muted">({s1.system})</span></KV>
                  <KV k="Source">{s1.source}</KV>
                  <KV k="Authority">{s1.authority}</KV>
                  <KV k="Connection"><StatusPill tone={s1.mode === "real" ? "green" : "amber"}>{s1.mode === "real" ? "Live" : s1.mode === "zone" ? "Inside evidence zone" : "Simulated"}</StatusPill></KV>
                  <p className="text-xs text-pex-muted">{s1.note}</p>
                </Step>}
                {s2 && <Step s={s2}>
                  <KV k="Asked">{s2.asked}</KV>
                  <KV k="Exact query" mono>{s2.call}</KV>
                  <p className="text-xs text-pex-muted">{s2.note}</p>
                </Step>}
                {s3 && <Step s={s3}>
                  <KV k="Result">{s3.result}</KV>
                  <KV k="Status"><StatusPill tone={["pass", "agree"].includes(s3.status) ? "green" : ["fail", "differs"].includes(s3.status) ? "red" : s3.status === "missing" ? "amber" : "grey"}>{s3.status_label}</StatusPill></KV>
                  {!!s3.fields?.length && <KV k="Values">{s3.fields.map((f: any) => <span key={f.token} className="inline-block mr-2"><span className="text-xs text-pex-muted">{f.label}: </span><span className="pex-mono text-xs">{f.token}</span> <span className="text-[10px] px-1 rounded bg-slate-100 text-slate-600" title={f.class_name}>{f.class}</span></span>)}</KV>}
                  {!!Object.keys(s3.facts ?? {}).length && <KV k="Facts" mono>{Object.entries(s3.facts).map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`).join(" · ")}</KV>}
                </Step>}
                {s4 && <Step s={s4}>
                  <KV k="Rule"><span className="pex-mono text-xs">{s4.rule_id}</span></KV>
                  <p className="text-pex-muted">{s4.rule}</p>
                  <KV k="Verdict"><StatusPill tone={V.tone}>{s4.verdict_label}</StatusPill></KV>
                </Step>}
                {s5 && <Step s={s5}>
                  <KV k="Checked at">{fmtDateTime(s5.checked_at)}</KV>
                  <KV k="Latency">{s5.latency_ms} ms{s5.latency_simulated ? " (simulated)" : ""}</KV>
                  <KV k="Trace" mono>{s5.trace_hash}</KV>
                  <p className="text-xs text-pex-muted">{s5.trace_note}</p>
                </Step>}
              </ol>
              <div className="flex justify-between mt-4">
                <button type="button" disabled={!d.prev_id} onClick={() => d.prev_id && onOpen(d.prev_id)} className="px-3 py-1.5 rounded-lg border border-surface-line bg-white text-sm inline-flex items-center gap-1.5 disabled:opacity-40"><ChevronLeft className="w-4 h-4" aria-hidden />Previous check</button>
                <button type="button" disabled={!d.next_id} onClick={() => d.next_id && onOpen(d.next_id)} className="px-3 py-1.5 rounded-lg border border-surface-line bg-white text-sm inline-flex items-center gap-1.5 disabled:opacity-40">Next check<ChevronRight className="w-4 h-4" aria-hidden /></button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
