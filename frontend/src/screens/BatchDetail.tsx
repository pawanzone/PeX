import React, { useEffect, useRef, useState } from "react";
import { Archive, Check, CheckCircle2, Database, Download, FileText, Layers, RefreshCw, Search, XCircle, AlertTriangle, ExternalLink, FileCode2, Loader2 } from "lucide-react";
import { PageHeader, Tabs, DataTable, StatusPill, Banner, Loading, ErrorState, useToast, cn } from "../components/v2";
import { routes, navigate } from "../lib/router";
import { useV2 } from "../services/v2/client";
import { downloadRejected, fetchBatchDetail, fetchRecord, reprocessBatch, type BatchRecordRow, type BatchTab } from "../services/v2/batches";
import { useSession } from "../shell/session";
import { hhmm } from "./home/shared";

const STAGE_ICON: Record<string, React.ElementType> = { received: FileText, schema: FileCode2, duplicates: Database, cases: FileText, archived: Archive };
const OUT_TONE = { accepted: "green", duplicate: "grey", rejected: "red", needs_review: "amber" } as const;
const OUT_ICON = { accepted: CheckCircle2, duplicate: Layers, rejected: XCircle, needs_review: AlertTriangle } as const;

/** Batch detail. Design: 11_batch_detail.png */
export const BatchDetail: React.FC<{ id?: string }> = ({ id = "" }) => {
  const { epoch } = useSession();
  const toast = useToast();
  const [tab, setTab] = useState<BatchTab>("all");
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [openRec, setOpenRec] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const pageSize = 25;
  useEffect(() => { setPage(1); }, [tab, id]);
  const r = useV2(() => fetchBatchDetail(id, tab, page, pageSize), [id, tab, page, epoch]);
  const rec = useV2(() => openRec === null ? Promise.resolve(null) : fetchRecord(id, openRec), [id, openRec]);
  const d = r.data;

  // Batches are processed in the background: poll while not finished.
  const inFlight = !!d && /queued|process/i.test(d.status ?? "") && !/processed|complete/i.test(d.status_label ?? "") && !d.counts?.received;
  useEffect(() => { if (!inFlight) return; const t = window.setInterval(r.reload, 2500); return () => window.clearInterval(t); }, [inFlight, r.reload]);

  if (r.loading && !d) return <Loading label="Loading batch…" />;
  if (r.error || !d) return <ErrorState unavailable={r.unavailable} message={r.error ?? undefined} onRetry={r.reload} />;
  const c = d.counts;
  const tc = d.tab_counts ?? {};
  const rows = (d.items ?? []).filter((x) => !q || `${x.record} ${x.source_reference ?? ""} ${x.case_id ?? ""} ${x.detail ?? ""}`.toLowerCase().includes(q.toLowerCase()));
  const total = d.total ?? rows.length;
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const rejectedN = tc.rejected ?? c?.rejected ?? 0;
  const reprocess = d.actions?.reprocess;

  const doDownload = async (format: "jsonl" | "csv" | "json" = "jsonl") => {
    try { await downloadRejected(id, format); } catch (e: any) { toast.push(e?.message || "Download failed", "red"); }
  };
  const onReprocess = async (f?: File | null) => {
    if (!f) return; setBusy(true);
    try { const x = await reprocessBatch(id, f); toast.push(`Corrected records queued as batch ${x.batch_id}`); navigate(routes.batch(x.batch_id)); }
    catch (e: any) { toast.push(e?.message || "Reprocess failed", "red"); }
    finally { setBusy(false); if (file.current) file.current.value = ""; }
  };

  const tabs = [{ id: "all", label: "All", count: tc.all ?? c?.received }, { id: "accepted", label: "Accepted", count: tc.accepted ?? c?.accepted }, { id: "duplicate", label: "Duplicate", count: tc.duplicate ?? c?.duplicate }, { id: "rejected", label: "Rejected", count: tc.rejected ?? c?.rejected }, { id: "needs_review", label: "Needs review", count: tc.needs_review ?? c?.needs_review }];
  const stat = (key: keyof NonNullable<typeof c>, label: string, cls: string, Icon: React.ElementType, ic: string) => (
    <div className={cn("rounded-card border p-4 flex items-center gap-3", cls)}>
      <span className="w-10 h-10 rounded-full bg-white/70 flex items-center justify-center" aria-hidden><Icon className={cn("w-5 h-5", ic)} /></span>
      <div><div className="text-sm font-medium">{label}</div><div className="text-3xl font-semibold leading-tight">{c ? c[key] : "—"}</div></div>
    </div>
  );

  return (
    <>
      <PageHeader breadcrumbs={[{ label: "Batches", href: routes.batches() }, { label: d.filename ?? d.batch_id }]}
        title={d.filename ?? d.batch_id}
        subtitle={<>Received {hhmm(d.received_at)} · {d.source ?? "Upload"} · {d.records ?? c?.received ?? 0} records</>}
        actions={<StatusPill tone={/partial/i.test(d.status_label ?? "") ? "amber" : /fail/i.test(d.status_label ?? "") ? "red" : /process|complete/i.test(d.status_label ?? d.status ?? "") ? "green" : "grey"}>{d.status_label ?? d.status}</StatusPill>} />
      {inFlight && <div className="mb-4"><Banner tone="blue"><span className="inline-flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" aria-hidden />Still processing. This page refreshes automatically.</span></Banner></div>}

      <ol className="grid grid-cols-5 gap-2 mb-5" aria-label="Processing stages">
        {(d.stages ?? []).map((s, i, arr) => {
          const Icon = STAGE_ICON[s.key] ?? FileText; const done = s.state ? s.state === "done" : !!s.at;
          return (
            <li key={s.key} className="relative flex flex-col items-center text-center">
              {i < arr.length - 1 && <span aria-hidden className={cn("absolute top-5 left-1/2 w-full h-0.5", done ? "bg-green-600" : "bg-slate-200")} />}
              <span className="relative z-10 w-10 h-10 rounded-full bg-white border border-surface-line flex items-center justify-center"><Icon className="w-5 h-5 text-slate-600" aria-hidden />
                {done && <span className="absolute -right-1 -top-1 w-4 h-4 rounded-full bg-green-600 flex items-center justify-center"><Check className="w-3 h-3 text-white" aria-hidden /></span>}</span>
              <span className="mt-1.5 text-sm font-medium">{s.label}<span className="sr-only">{done ? " (done)" : " (pending)"}</span></span>
              <span className="text-xs text-pex-muted">{s.at ? hhmm(s.at) : "—"}</span>
            </li>
          );
        })}
      </ol>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-3">
        {stat("received", "Received", "bg-white border-surface-line", FileText, "text-slate-600")}
        {stat("accepted", "Accepted", "bg-green-50/70 border-green-300 text-green-800", Check, "text-green-700")}
        {stat("duplicate", "Duplicate", "bg-slate-50 border-slate-300", Layers, "text-slate-600")}
        {stat("rejected", "Rejected", "bg-red-50/70 border-red-300 text-red-700", XCircle, "text-red-600")}
        {stat("needs_review", "Needs review", "bg-amber-50/70 border-amber-300 text-amber-800", AlertTriangle, "text-amber-600")}
      </div>
      {d.reconciliation && <div className="mb-5"><Banner tone={d.reconciliation.balanced ? "green" : "red"} title={d.reconciliation.balanced ? "Reconciled" : "Does not reconcile"}>{d.reconciliation.text}</Banner></div>}

      <section className="bg-surface-card rounded-card border border-surface-line shadow-card p-4 mb-5">
        <h2 className="text-lg font-semibold mb-2">Records from this file</h2>
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <Tabs label="Outcome" value={tab} onChange={(t) => setTab(t as BatchTab)} tabs={tabs} />
          <label className="relative"><span className="sr-only">Search records</span><Search className="w-4 h-4 absolute left-2.5 top-2.5 text-slate-400" aria-hidden />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search record, reference or case" className="pl-8 pr-3 py-2 text-sm rounded-lg border border-surface-line w-72" /></label>
        </div>
        <DataTable<BatchRecordRow> caption="Batch records" loading={r.loading} rows={rows} rowKey={(x) => String(x.record)} onRowClick={(x) => setOpenRec(openRec === x.record ? null : x.record)} selectedKey={openRec !== null ? String(openRec) : undefined}
          emptyTitle="No records in this outcome"
          columns={[
            { key: "n", header: "Record", render: (x) => x.record },
            { key: "s", header: "Source reference", render: (x) => x.source_reference ?? "—" },
            { key: "c", header: "Case", render: (x) => x.case_id ? <a className="text-pex-primary hover:underline" href={routes.workCase(x.case_id)} onClick={(e) => e.stopPropagation()}>{x.case_id}</a> : "—" },
            { key: "o", header: "Outcome", render: (x) => { const I = OUT_ICON[x.outcome] ?? Layers; return <StatusPill tone={OUT_TONE[x.outcome] ?? "grey"} dot={false}><I className="w-3.5 h-3.5" aria-hidden />{x.outcome_label ?? x.outcome}</StatusPill>; } },
            { key: "d", header: "Detail", render: (x) => x.detail ?? "" },
            { key: "a", header: "Action", render: (x) => {
              if (x.action?.type === "download" || x.outcome === "rejected") return <button className="inline-flex items-center gap-1.5 text-pex-primary hover:underline" onClick={(e) => { e.stopPropagation(); doDownload(); }}><Download className="w-4 h-4" aria-hidden />Download</button>;
              if (x.case_id) return <a className="inline-flex items-center gap-1.5 text-pex-primary hover:underline" href={routes.workCase(x.case_id)} onClick={(e) => e.stopPropagation()}><ExternalLink className="w-4 h-4" aria-hidden />{x.action?.label ?? (x.outcome === "needs_review" ? "Review" : "View case")}</a>;
              return null; } },
          ]}
          footer={<div className="flex items-center justify-between text-xs text-pex-muted px-3 py-2">
            <span>Showing {rows.length} of {total} records</span>
            <span className="flex items-center gap-2"><button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-2 py-1 rounded border border-surface-line disabled:opacity-40">Previous</button>Page {page} of {pages}<button disabled={page >= pages} onClick={() => setPage(page + 1)} className="px-2 py-1 rounded border border-surface-line disabled:opacity-40">Next</button></span></div>} />
        {openRec !== null && (
          <div className="mt-3 rounded-lg border border-surface-line bg-slate-50 p-3 text-sm" aria-live="polite">
            <div className="flex justify-between mb-1"><strong>Record {openRec}</strong><button className="text-xs text-pex-primary" onClick={() => setOpenRec(null)}>Close</button></div>
            {rec.loading ? <Loading /> : rec.error ? <span className="text-pex-block">{rec.error}</span> : (
              <>
                <p>{rec.data?.detail}</p>
                {(rec.data?.errors ?? []).length > 0 && <ul className="list-disc ml-5 mt-1">{rec.data!.errors!.map((e, i) => <li key={i}>{e}</li>)}</ul>}
                <details className="mt-2"><summary className="cursor-pointer text-xs text-pex-muted">Source record</summary><pre className="pex-mono text-xs overflow-x-auto mt-1">{JSON.stringify(rec.data?.raw ?? {}, null, 2)}</pre></details>
              </>
            )}
          </div>
        )}
      </section>

      <section className="bg-surface-card rounded-card border border-surface-line shadow-card p-4 flex items-center justify-between gap-6 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold mb-2">Outputs</h2>
          <ul className="space-y-1.5 text-sm">
            <li className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-green-600" aria-hidden />Bank handoff requests: {d.outputs?.bank_handoff_requests?.text ?? "0 sent"} <span className="text-xs text-pex-muted">(simulated)</span></li>
            <li className="flex items-center gap-2">{d.outputs?.archive?.archived ? <CheckCircle2 className="w-4 h-4 text-green-600" aria-hidden /> : <AlertTriangle className="w-4 h-4 text-amber-600" aria-hidden />}
              {d.outputs?.archive?.archived ? <>Source file archived · checksum {d.outputs.archive.verified ? "verified" : "not verified"} {hhmm(d.outputs.archive.at ?? undefined)}{d.outputs.archive.checksum && <span className="pex-mono text-xs text-pex-muted" title={d.outputs.archive.checksum}> {d.outputs.archive.checksum.slice(0, 16)}…</span>}</> : "Source file not archived yet"}</li>
          </ul>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className="flex gap-3">
            <button disabled={rejectedN === 0} onClick={() => doDownload()} title={rejectedN === 0 ? "No rejected records" : undefined} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-pex-primary text-pex-primary hover:bg-pex-primary-soft disabled:opacity-50 disabled:cursor-not-allowed"><Download className="w-4 h-4" aria-hidden />Download rejected records</button>
            <input ref={file} type="file" accept=".json,.jsonl,.gz" className="sr-only" aria-label="Choose corrected records file" onChange={(e) => onReprocess(e.target.files?.[0])} />
            <button disabled={busy || rejectedN === 0} onClick={() => file.current?.click()} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-surface-line bg-white hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"><RefreshCw className="w-4 h-4" aria-hidden />Reprocess corrected records</button>
          </div>
          <span className="text-xs text-pex-muted">{rejectedN === 0 ? "Nothing to reprocess" : "Upload corrected records to reprocess them as a new batch"}</span>
        </div>
      </section>
    </>
  );
};
