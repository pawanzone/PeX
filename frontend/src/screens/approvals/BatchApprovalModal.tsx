import React, { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle2, Send, ArrowRight } from "lucide-react";
import { Banner, DataTable, ErrorState, Loading, Modal, StatusPill, Tile } from "../../components/v2";
import type { Column } from "../../components/v2";
import { useV2 } from "../../services/v2";
import { approveStp, getStpReview } from "../../services/v2/approvals";
import type { StpApproveResult, StpItem } from "../../services/v2/approvals";
import { HighlightedValue, chipTone, errText } from "../case/parts";

const num = (n: number) => n.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const humanize = (f?: string) => { const s = (f ?? "field").split(".").pop()!.replace(/_/g, " "); return s.charAt(0).toUpperCase() + s.slice(1); };
const amountOf = (i: StpItem) => i.amount?.amount ?? 0;

const FieldChange: React.FC<{ c?: StpItem["change"] }> = ({ c }) => {
  if (!c) return <span className="text-slate-400">—</span>;
  const long = (c.original ?? "").length > 12 || (c.proposed ?? "").length > 12;
  return (
    <div className="text-xs">
      <div className="text-pex-muted mb-1">{humanize(c.field)}:</div>
      {long ? (
        <div className="grid gap-0.5 text-[13px]"><div><HighlightedValue value={c.original} other={c.proposed} tone="red" /></div><div className="flex items-center gap-1"><ArrowRight className="w-3 h-3 text-slate-400" aria-hidden /><HighlightedValue value={c.proposed} other={c.original} tone="green" /></div></div>
      ) : (
        <div className="flex items-center gap-2 text-[13px] flex-wrap"><HighlightedValue value={c.original} other={c.proposed} tone="red" /><ArrowRight className="w-3 h-3 text-slate-400" aria-hidden /><HighlightedValue value={c.proposed} other={c.original} tone="green" /></div>
      )}
      {c.source && <div className="text-pex-muted mt-1">Source: {c.source}</div>}
    </div>
  );
};

const Content: React.FC<{ onClose: () => void; onDone: () => void }> = ({ onClose, onDone }) => {
  const r = useV2(getStpReview, []);
  const items = r.data?.eligible ?? [];
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [showWhy, setShowWhy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<StpApproveResult | null>(null);
  useEffect(() => { if (r.data) setSel(new Set((r.data.eligible ?? []).map((i) => i.case_id))); }, [r.data]);

  const chosen = useMemo(() => items.filter((i) => sel.has(i.case_id)), [items, sel]);
  const total = chosen.reduce((s, i) => s + amountOf(i), 0);
  const currencies = new Set(chosen.map((i) => i.amount?.currency).filter(Boolean));
  const largest = chosen.reduce<StpItem | null>((m, i) => (!m || amountOf(i) > amountOf(m) ? i : m), null);
  const ne = r.data?.not_eligible;
  const mode = r.data?.release_mode;
  const bulk = mode ? mode.bulk_release : true;
  const toggle = (k: string) => setSel((s) => { const n = new Set(s); if (n.has(k)) n.delete(k); else n.add(k); return n; });

  const submit = async () => {
    setBusy(true); setErr(null);
    try { setResult(await approveStp(chosen.map((i) => i.case_id))); onDone(); }
    catch (e) { setErr(errText(e)); }
    finally { setBusy(false); }
  };

  const cols: Column<StpItem>[] = [
    { key: "c", header: "Case", mono: true, render: (i) => i.case_id },
    { key: "e", header: "Exception", render: (i) => i.exception?.label ?? "" },
    { key: "a", header: "Amount and rail", render: (i) => <div><span className="pex-mono font-medium">{i.amount?.display ?? ""}</span><div className="text-xs text-pex-muted">{i.rail?.label}</div></div> },
    { key: "f", header: "Field change", render: (i) => <FieldChange c={i.change} /> },
    { key: "w", header: "Why eligible", render: (i) => <div className="flex flex-wrap gap-1.5">{i.auto_release_eligible && mode?.value === "AUTO_RELEASE" && <StatusPill tone="blue">Auto-release eligible</StatusPill>}{(i.chips ?? []).map((c, k) => <StatusPill key={k} tone={chipTone(c.tone)}><CheckCircle2 className="w-3 h-3" aria-hidden />{c.label}</StatusPill>)}</div> },
  ];

  const sim = result?.mode === "SHADOW";
  const footer = result ? <button className="px-4 py-2 text-sm font-medium rounded-lg bg-pex-primary text-white" onClick={onClose}>Done</button> : (
    <div className="flex items-center gap-4 w-full">
      <p className="text-xs text-pex-muted mr-auto">{r.data?.footnote ?? "Handoff requests will be sent to the bank payment system. Execution is confirmed by the bank."}</p>
      <button className="px-4 py-2 text-sm font-medium rounded-lg bg-white border border-surface-line text-pex-primary" onClick={onClose}>Cancel</button>
      <button disabled={busy || chosen.length === 0 || !bulk} onClick={submit} className="px-4 py-2 text-sm font-semibold rounded-lg bg-pex-primary text-white hover:bg-pex-primary-dark disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"><Send className="w-4 h-4" aria-hidden />Approve {chosen.length} for bank handoff</button>
    </div>
  );

  return (
    <Modal open title="Review low-risk repairs for batch approval" onClose={onClose} width="xl" footer={footer}>
      <p className="text-sm text-pex-muted -mt-2 mb-4">Eligibility is set by bank policy and passed validations. Approving prepares a bank handoff. PeX does not execute payments.</p>
      {r.loading ? <Loading /> : r.error ? <ErrorState message={r.error} unavailable={r.unavailable} onRetry={r.reload} /> : result ? (
        <div className="grid gap-3">
          <Banner tone={sim ? "grey" : "green"} title={sim ? "Recorded, nothing sent (shadow mode)" : "Handoff requests sent (simulated)"}>{result.message ?? `${result.handed_to_bank ?? 0} of ${result.requested ?? 0} handed to the bank. Awaiting bank confirmation.`}</Banner>
          {!!result.skipped?.length && <Banner tone="amber" title={`${result.skipped.length} skipped`}><ul className="list-disc pl-5">{result.skipped.map((s) => <li key={s.case_id}><span className="pex-mono">{s.case_id}</span>: {s.reason}</li>)}</ul></Banner>}
        </div>
      ) : (
        <div className="grid gap-4">
          {mode && <Banner tone={bulk ? "blue" : "amber"} title={mode.value === "REVIEW_EACH" ? "Review each: bulk release is off" : mode.value === "AUTO_RELEASE" ? "Release mode: auto-release" : "Release mode: approve all"}>{mode.note}</Banner>}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Tile label={bulk ? "Selected" : "Eligible"} value={bulk ? `${chosen.length} of ${items.length}` : String(items.length)} />
            <Tile label="Total value" value={num(bulk ? total : items.reduce((a, i) => a + amountOf(i), 0))} hint={currencies.size > 1 ? "(mixed currencies)" : [...currencies][0] as string} mono />
            <Tile label="Largest item" value={largest ? num(amountOf(largest)) : "—"} hint={largest ? `${largest.case_id} · ${largest.amount?.currency ?? ""}` : undefined} mono />
            <Tile label="Policy rule"><div className="mt-1 text-sm text-pex-ink">{r.data?.policy?.text ?? "—"}</div></Tile>
          </div>
          {bulk && <div className="flex items-center gap-4 rounded-lg border border-surface-line px-3 py-2 text-sm">
            <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={items.length > 0 && sel.size === items.length} onChange={(e) => setSel(e.target.checked ? new Set(items.map((i) => i.case_id)) : new Set())} />Select all</label>
            <button className="text-pex-primary hover:underline" onClick={() => setSel(new Set())}>Clear</button>
            <span className="ml-auto text-pex-muted">{sel.size} of {items.length} selected</span>
          </div>}
          <div className="max-h-[22rem] overflow-y-auto rounded-lg border border-surface-line">
            <DataTable columns={cols} rows={items} rowKey={(i) => i.case_id} selectable={bulk} selected={sel} onToggle={toggle} emptyTitle="No low-risk repairs are eligible right now" caption="Eligible low-risk repairs" />
          </div>
          {!!ne?.total && (
            <div className="rounded-card border border-red-200 bg-red-50">
              <button className="w-full flex items-center gap-3 flex-wrap px-4 py-3 text-left" aria-expanded={showWhy} onClick={() => setShowWhy((s) => !s)}>
                {showWhy ? <ChevronDown className="w-4 h-4 text-pex-block" aria-hidden /> : <ChevronRight className="w-4 h-4 text-pex-block" aria-hidden />}
                <span className="font-semibold text-pex-block">{ne.total} item{ne.total === 1 ? "" : "s"} not eligible</span>
                {(ne.groups ?? []).map((g, i) => <span key={i} className="text-xs rounded-full bg-white border border-red-200 px-2.5 py-1 text-pex-ink">{g.reason}{g.rule ? <span className="pex-mono text-pex-muted"> · {g.rule}</span> : null} <b className="ml-1">{g.count}</b></span>)}
                <span className="ml-auto text-sm text-pex-primary">{showWhy ? "Hide" : "View why"}</span>
              </button>
              {showWhy && <div className="px-4 pb-3 grid gap-2">{(ne.groups ?? []).flatMap((g) => (g.cases ?? []).map((c) => <div key={c.case_id} className="text-sm flex gap-3 flex-wrap"><span className="pex-mono">{c.case_id}</span><span className="font-medium">{g.reason}{g.rule ? ` (${g.rule})` : ""}</span><span className="text-pex-muted">{c.detail}</span></div>))}</div>}
            </div>
          )}
          {err && <Banner tone="red" title="Batch approval failed">{err}</Banner>}
        </div>
      )}
    </Modal>
  );
};

export const BatchApprovalModal: React.FC<{ open: boolean; onClose: () => void; onDone: () => void }> = ({ open, onClose, onDone }) => (open ? <Content onClose={onClose} onDone={onDone} /> : null);
