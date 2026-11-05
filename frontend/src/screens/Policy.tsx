import React, { useState } from "react";
import { Check, X, Undo2, History, ShieldCheck } from "lucide-react";
import { Avatar, Banner, ErrorState, Loading, PageHeader, StatusPill, useToast, cn } from "../components/v2";
import { useV2 } from "../services/v2/client";
import { decidePolicy, getPolicyParams, previewPolicy, proposePolicy, type Impact, type PolicyParam } from "../services/v2/policy";
import { useSession } from "../shell/session";
import { fmtDateTime } from "./case/parts";

const fmt = (p: PolicyParam, v: number | string) => (p.kind === "choice" ? (p.options?.find((o) => o.value === v)?.label ?? String(v)) : p.kind === "amount" ? new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 }).format(Number(v)) : String(v));
const TONE: Record<string, "green" | "amber" | "red" | "grey"> = { ACTIVE: "green", PENDING: "amber", REJECTED: "red", WITHDRAWN: "grey", SUPERSEDED: "grey" };

const ImpactBox: React.FC<{ i: Impact }> = ({ i }) => (
  <div className="rounded-lg border border-surface-line bg-slate-50 p-3 text-sm" aria-live="polite">
    <div className="font-medium text-pex-ink">{i.summary}</div>
    {!!i.cases.length && <ul className="mt-1.5 text-xs text-pex-muted grid gap-0.5">{i.cases.slice(0, 5).map((c) => <li key={c.case_id}><span className="pex-mono text-pex-primary">{c.case_id}</span> · {new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 }).format(c.amount)} {c.currency} · was {c.was}, would be {c.now}</li>)}{i.cases_affected > 5 && <li>and {i.cases_affected - 5} more</li>}</ul>}
  </div>
);

const Card: React.FC<{ p: PolicyParam; me: string; onChanged: () => void }> = ({ p, me, onChanged }) => {
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(String(p.value));
  const [reason, setReason] = useState("");
  const [impact, setImpact] = useState<Impact | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const choice = p.kind === "choice";
  const num: number | string = choice ? val : Number(val);
  const run = async (fn: () => Promise<unknown>, ok: string) => { setBusy(true); setErr(null); try { await fn(); toast.push(ok, "green"); setEditing(false); setReason(""); setImpact(null); onChanged(); } catch (e: any) { setErr(e?.message || "Failed"); } finally { setBusy(false); } };
  const check = async () => { setErr(null); try { setImpact(await previewPolicy(p.key, num)); } catch (e: any) { setImpact(null); setErr(e?.message || "Value not accepted"); } };
  const pend = p.pending;
  const mine = pend?.proposed_by?.user_id === me;
  return (
    <section aria-label={p.label} className="bg-surface-card rounded-card border border-surface-line shadow-card p-4 grid gap-3 content-start">
      <div className="flex items-start justify-between gap-3">
        <div><h3 className="text-base font-semibold text-pex-ink">{p.label}</h3><p className="text-sm text-pex-muted mt-0.5">{p.description}</p></div>
        {pend ? <StatusPill tone="amber">Change waiting</StatusPill> : p.value !== p.default ? <StatusPill tone="blue">Changed from default</StatusPill> : <StatusPill tone="grey">Default</StatusPill>}
      </div>
      <div className="flex items-baseline gap-3"><span className={choice ? "text-2xl font-semibold text-pex-ink" : "text-3xl font-semibold pex-mono text-pex-ink"}>{fmt(p, p.value)}</span>{!choice && <span className="text-sm text-pex-muted">{p.unit}</span>}{p.value !== p.default && <span className="text-xs text-pex-muted">default {fmt(p, p.default)}</span>}</div>
      <p className="text-xs text-pex-muted">Used by: {p.used_by}</p>

      {pend && (
        <div className="rounded-lg border border-pex-wait/40 bg-amber-50/50 p-3 grid gap-2">
          <div className="flex items-center gap-2 text-sm"><Avatar bare size="sm" name={pend.proposed_by?.name} /><span><strong>{pend.proposed_by?.name}</strong> proposed {fmt(p, pend.prev_value)} → <strong>{fmt(p, pend.value)}</strong></span></div>
          <p className="text-sm text-pex-ink">“{pend.reason}”</p>
          <ImpactBox i={pend.impact} />
          {err && <p role="alert" className="text-sm text-pex-block">{err}</p>}
          {mine ? (
            <div className="flex items-center gap-2"><span className="text-xs text-pex-muted">A different Policy Owner must approve.</span><button type="button" disabled={busy} onClick={() => run(() => decidePolicy(pend.id, "withdraw"), "Change withdrawn")} className="ml-auto px-3 py-1.5 text-sm rounded-lg border border-surface-line bg-white inline-flex items-center gap-1.5"><Undo2 className="w-4 h-4" aria-hidden />Withdraw</button></div>
          ) : (
            <div className="grid gap-2">
              <label className="text-xs text-pex-muted" htmlFor={`n-${p.key}`}>Note (optional)</label>
              <input id={`n-${p.key}`} value={note} onChange={(e) => setNote(e.target.value)} className="py-1.5 px-2.5 text-sm rounded-lg border border-surface-line" />
              <div className="flex gap-2"><button type="button" disabled={busy} onClick={() => run(() => decidePolicy(pend.id, "approve", note), "Approved: in force now")} className="px-3 py-1.5 text-sm font-medium rounded-lg bg-pex-primary text-white inline-flex items-center gap-1.5"><Check className="w-4 h-4" aria-hidden />Approve</button>
                <button type="button" disabled={busy} onClick={() => run(() => decidePolicy(pend.id, "reject", note), "Rejected")} className="px-3 py-1.5 text-sm rounded-lg border border-surface-line bg-white inline-flex items-center gap-1.5"><X className="w-4 h-4" aria-hidden />Reject</button></div>
            </div>
          )}
        </div>
      )}

      {!pend && !editing && <button type="button" onClick={() => { setEditing(true); setVal(String(p.value)); }} className="justify-self-start px-3 py-1.5 text-sm font-medium rounded-lg bg-white border border-surface-line text-pex-primary hover:bg-slate-50">Propose a change</button>}
      {!pend && editing && (
        <div className="grid gap-2">
          {choice ? (
            <fieldset className="grid gap-2"><legend className="text-xs text-pex-muted mb-1">New value</legend>
              {p.options?.map((o) => (
                <label key={o.value} className={cn("flex gap-2 items-start rounded-lg border p-2.5 cursor-pointer", val === o.value ? "border-pex-primary bg-blue-50/40" : "border-surface-line")}>
                  <input type="radio" name={`v-${p.key}`} className="mt-1" checked={val === o.value} onChange={() => { setVal(o.value); setImpact(null); }} />
                  <span><span className="text-sm font-medium text-pex-ink">{o.label}</span><span className="block text-xs text-pex-muted">{o.meaning}</span></span>
                </label>))}
            </fieldset>
          ) : (<>
          <label htmlFor={`v-${p.key}`} className="text-xs text-pex-muted">New value ({p.unit}, {fmt(p, p.min)} to {fmt(p, p.max)})</label>
          <input id={`v-${p.key}`} type="number" inputMode="decimal" min={p.min} max={p.max} step={p.step} value={val} onChange={(e) => { setVal(e.target.value); setImpact(null); }} className="py-2 px-2.5 text-sm rounded-lg border border-surface-line w-48 pex-mono" />
          </>)}
          <label htmlFor={`r-${p.key}`} className="text-xs text-pex-muted">Reason (recorded in the audit trail)</label>
          <textarea id={`r-${p.key}`} rows={2} value={reason} onChange={(e) => setReason(e.target.value)} className="py-2 px-2.5 text-sm rounded-lg border border-surface-line" />
          {impact && <ImpactBox i={impact} />}
          {err && <p role="alert" className="text-sm text-pex-block">{err}</p>}
          <div className="flex gap-2">
            <button type="button" onClick={check} disabled={!val} className="px-3 py-1.5 text-sm rounded-lg border border-surface-line bg-white">Check impact on recent cases</button>
            <button type="button" disabled={busy || !reason.trim() || !val || (choice && val === p.value)} onClick={() => run(() => proposePolicy(p.key, num, reason), "Sent for a second Policy Owner's approval")} className="px-3 py-1.5 text-sm font-medium rounded-lg bg-pex-primary text-white disabled:opacity-50">Submit for approval</button>
            <button type="button" onClick={() => { setEditing(false); setErr(null); setImpact(null); }} className="px-3 py-1.5 text-sm rounded-lg">Cancel</button>
          </div>
        </div>
      )}

      {!!p.history.length && (
        <details className="text-sm"><summary className="cursor-pointer text-pex-muted inline-flex items-center gap-1.5"><History className="w-4 h-4" aria-hidden />History ({p.history.length})</summary>
          <ul className="mt-2 grid gap-1.5">{p.history.map((h) => (
            <li key={h.id} className="flex flex-wrap items-center gap-x-2 text-xs text-pex-muted"><StatusPill tone={TONE[h.status]}>{h.status.toLowerCase()}</StatusPill><span>{fmt(p, h.prev_value)} → {fmt(p, h.value)}</span><span>{h.proposed_by?.name}{h.decided_by ? ` / ${h.decided_by.name}` : ""}</span><span>{fmtDateTime(h.decided_at || h.proposed_at)}</span></li>))}</ul>
        </details>
      )}
    </section>
  );
};

/** Rules & Policy Studio: Policy Owner only. Change a rule by proposal; a second Policy Owner approves before it takes effect. */
export const Policy: React.FC = () => {
  const { persona, epoch } = useSession();
  const r = useV2(getPolicyParams, [epoch]);
  if (r.loading && !r.data) return <Loading label="Loading rules…" />;
  if (r.error || !r.data) return <ErrorState unavailable={r.unavailable} message={r.error ?? undefined} onRetry={r.reload} />;
  const groups = Array.from(new Set(r.data.params.map((p) => p.group)));
  return (
    <>
      <PageHeader title="Rules and Policy Studio" subtitle="The numbers the platform decides by. Every change needs a reason and a second Policy Owner's approval, and is recorded in the audit trail." />
      <Banner tone="blue" title="Four eyes"><span className="inline-flex items-center gap-1.5"><ShieldCheck className="w-4 h-4" aria-hidden />{r.data.rule} Natural-language rules and more rule types come next.</span></Banner>
      {groups.map((g) => (
        <div key={g} className="mt-5">
          <h2 className="text-sm font-semibold text-pex-muted uppercase tracking-wide mb-2">{g}</h2>
          <div className={cn("grid gap-4 md:grid-cols-2 xl:grid-cols-3")}>{r.data!.params.filter((p) => p.group === g).map((p) => <Card key={p.key} p={p} me={persona?.user_id ?? ""} onChanged={r.reload} />)}</div>
        </div>
      ))}
    </>
  );
};
