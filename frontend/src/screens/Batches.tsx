import React, { useRef, useState } from "react";
import { Upload, FlaskConical, ChevronRight } from "lucide-react";
import { PageHeader, DataTable, StatusPill, Banner, useToast, Loading, ErrorState } from "../components/v2";
import { navigate, routes } from "../lib/router";
import { useV2 } from "../services/v2/client";
import { fetchBatchList, generateDemoBatch, uploadBatchFile, type BatchSummary } from "../services/v2/batches";
import { useSession } from "../shell/session";
import { hhmm } from "./home/shared";

const tone = (s?: string) => { const x = (s || "").toLowerCase(); return x.includes("fail") ? "red" : x.includes("partial") || x.includes("process") && !x.includes("processed") ? "amber" : x === "processed" || x.includes("complete") ? "green" : "grey"; };

/** Batches list + batch JSON upload. Upload goes through the same pipeline as /api/batch/upload. */
export const Batches: React.FC = () => {
  const { epoch } = useSession();
  const toast = useToast();
  const file = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ tone: "green" | "red" | "blue"; text: string } | null>(null);
  const list = useV2(() => fetchBatchList(1, 50), [epoch]);

  const onFile = async (f?: File | null) => {
    if (!f) return;
    setBusy(true); setMsg(null);
    try {
      const r = await uploadBatchFile(f);
      toast.push(`Batch ${r.batch_id} received`);
      setMsg({ tone: "blue", text: `Batch ${r.batch_id} accepted and queued. It is processed in the background; refresh to see counts.` });
      list.reload();
      window.setTimeout(list.reload, 3000); window.setTimeout(list.reload, 8000);
    } catch (e: any) { setMsg({ tone: "red", text: e?.message || "Upload failed" }); }
    finally { setBusy(false); if (file.current) file.current.value = ""; }
  };
  const onGenerate = async () => {
    setBusy(true); setMsg(null);
    try { const r = await generateDemoBatch(50, ["GB", "US", "EU"]); setMsg({ tone: "blue", text: `Synthetic demo batch ${r.batch_id} generated and queued (synthetic data, simulated bank).` }); list.reload(); window.setTimeout(list.reload, 4000); }
    catch (e: any) { setMsg({ tone: "red", text: e?.message || "Could not generate a batch" }); }
    finally { setBusy(false); }
  };

  return (
    <>
      <PageHeader title="Batches" subtitle="Exception files received, checked and turned into cases"
        actions={<>
          <input ref={file} type="file" accept=".json,.jsonl,.gz,application/json" className="sr-only" aria-label="Choose batch file" onChange={(e) => onFile(e.target.files?.[0])} />
          <button disabled={busy} onClick={onGenerate} className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-surface-line bg-white hover:bg-slate-50 disabled:opacity-50"><FlaskConical className="w-4 h-4" aria-hidden />Generate demo batch</button>
          <button disabled={busy} onClick={() => file.current?.click()} className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-pex-primary text-white hover:bg-pex-primary-dark disabled:opacity-50"><Upload className="w-4 h-4" aria-hidden />Upload batch file</button>
        </>} />
      {msg && <div className="mb-4"><Banner tone={msg.tone}>{msg.text}</Banner></div>}
      <div className="bg-surface-card rounded-card border border-surface-line shadow-card">
        {list.loading ? <Loading /> : list.error ? <ErrorState unavailable={list.unavailable} message={list.error} onRetry={list.reload} /> : (
          <DataTable<BatchSummary> caption="Batches" rows={list.data ?? []} rowKey={(r) => r.batch_id} onRowClick={(r) => navigate(routes.batch(r.batch_id))}
            emptyTitle="No batches yet" emptyHint="Upload a JSON, JSONL or .gz file, or generate a synthetic demo batch."
            columns={[
              { key: "f", header: "File", render: (r) => <span className="font-medium pex-mono">{r.filename ?? r.batch_id}</span> },
              { key: "rc", header: "Received", render: (r) => hhmm(r.received_at) },
              { key: "s", header: "Source", render: (r) => r.source ?? "—" },
              { key: "st", header: "Status", render: (r) => <StatusPill tone={tone(r.status_label ?? r.status) as any}>{r.status_label ?? r.status ?? "—"}</StatusPill> },
              { key: "n", header: "Records", render: (r) => r.records ?? "—" },
              { key: "a", header: "Accepted", render: (r) => r.accepted ?? "—" },
              { key: "d", header: "Duplicate", render: (r) => r.duplicate ?? "—" },
              { key: "rj", header: "Rejected", render: (r) => <span className={r.rejected ? "text-pex-block font-semibold" : ""}>{r.rejected ?? "—"}</span> },
              { key: "nr", header: "Needs review", render: (r) => <span className={r.needs_review ? "text-pex-wait font-semibold" : ""}>{r.needs_review ?? "—"}</span> },
              { key: "go", header: "", render: () => <ChevronRight className="w-4 h-4 text-slate-400" aria-hidden /> },
            ]} />
        )}
      </div>
    </>
  );
};
