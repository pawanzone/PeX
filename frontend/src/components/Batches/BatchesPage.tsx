import React, { useCallback, useEffect, useRef, useState } from "react";
import { BatchRecord } from "../../types";
import { fetchBatches, uploadBatch, generateBatch, downloadBatchResults, ApiError } from "../../services/api";
import { UploadCloud, Sparkles, Download, RefreshCw, Loader2 } from "lucide-react";
import { EmptyState, ErrorState, LoadingState } from "../common/States";
import { TONE_CLASSES, StatusTone } from "../../lib/statusMeta";
import { SimulatedChip } from "../common/SimulatedChip";

const RAILS = [
  { id: "SEPA_SCT", label: "SEPA SCT" },
  { id: "SEPA_INST", label: "SEPA Instant" },
  { id: "T2", label: "T2" },
  { id: "SWIFT", label: "SWIFT" },
];

const BATCH_TONE: Record<string, StatusTone> = {
  QUEUED: "grey",
  PROCESSING: "blue",
  COMPLETED: "green",
  FAILED: "red",
};

/** Accept slightly different field names so a backend tweak does not blank the page. */
function normalize(b: any): BatchRecord {
  return {
    ...b,
    batch_id: b.batch_id ?? b.id,
    status: String(b.status ?? "QUEUED").toUpperCase(),
    total: b.total ?? b.total_records ?? 0,
    processed: b.processed ?? b.processed_records ?? 0,
    failed: b.failed ?? b.failed_records ?? 0,
    duplicates: b.duplicates ?? b.duplicate_records ?? 0,
  };
}

export const BatchesPage: React.FC<{ onOpenWorklist: () => void; onChanged?: () => void }> = ({ onOpenWorklist, onChanged }) => {
  const [batches, setBatches] = useState<BatchRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [count, setCount] = useState(500);
  const [rails, setRails] = useState<string[]>(["SEPA_SCT", "SEPA_INST", "T2"]);
  const fileRef = useRef<HTMLInputElement>(null);
  const wasProcessing = useRef(false);

  const load = useCallback(async () => {
    try {
      const r = (await fetchBatches()).map(normalize);
      setBatches(r);
      setError(null);
      const active = r.some((b) => b.status === "PROCESSING" || b.status === "QUEUED");
      if (wasProcessing.current && !active) onChanged?.();
      wasProcessing.current = active;
    } catch (e: any) {
      setError(e instanceof ApiError && e.unavailable ? "The batch service is not available on this backend build." : e?.message || "Could not load batches");
    }
  }, [onChanged]);

  useEffect(() => {
    load();
  }, [load]);

  const hasActive = !!batches?.some((b) => b.status === "PROCESSING" || b.status === "QUEUED");
  useEffect(() => {
    if (!hasActive) return;
    const t = window.setInterval(load, 2000);
    return () => window.clearInterval(t);
  }, [hasActive, load]);

  const handleFiles = async (files: FileList | File[] | null) => {
    const f = files && (files as any)[0];
    if (!f) return;
    if (!/\.(json|jsonl|ndjson)$/i.test(f.name)) {
      setNotice({ kind: "err", text: "Only .json, .jsonl or .ndjson files are accepted." });
      return;
    }
    setBusy(true);
    setNotice(null);
    try {
      const r = await uploadBatch(f);
      setNotice({ kind: "ok", text: `Uploaded ${f.name}. Batch ${r.batch_id} is ${String(r.status).toLowerCase()}.` });
      await load();
    } catch (e: any) {
      setNotice({ kind: "err", text: e?.message || "Upload failed" });
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleGenerate = async () => {
    setBusy(true);
    setNotice(null);
    try {
      const r = await generateBatch(count, rails);
      setNotice({ kind: "ok", text: `Demo batch ${r.batch_id} created with ${count.toLocaleString()} synthetic payments.` });
      await load();
    } catch (e: any) {
      setNotice({ kind: "err", text: e?.message || "Could not generate a demo batch" });
    } finally {
      setBusy(false);
    }
  };

  const toggleRail = (id: string) => setRails((r) => (r.includes(id) ? r.filter((x) => x !== id) : [...r, id]));

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Batches</h1>
          <p className="text-xs text-slate-500 mt-1">Upload payment-exception files as JSON or JSONL, or generate synthetic demo data. Results are downloadable as JSONL.</p>
        </div>
        <SimulatedChip className="mt-1" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
          onClick={() => fileRef.current?.click()}
          className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors ${dragging ? "border-sky-500 bg-sky-50" : "border-slate-300 bg-white hover:bg-slate-50"}`}
        >
          <input ref={fileRef} type="file" accept=".json,.jsonl,.ndjson" className="hidden" onChange={(e) => handleFiles(e.target.files)} />
          <UploadCloud className="w-8 h-8 text-slate-400 mx-auto mb-2" />
          <div className="text-sm font-semibold text-slate-700">Drop a JSON or JSONL file here</div>
          <div className="text-xs text-slate-500 mt-1">or click to choose a file</div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3">
          <div className="flex items-center space-x-2 text-sm font-semibold text-slate-800">
            <Sparkles className="w-4 h-4 text-sky-600" />
            <span>Generate demo batch</span>
          </div>
          <label className="block text-xs text-slate-600">
            Payments
            <input
              type="number"
              min={1}
              max={100000}
              value={count}
              onChange={(e) => setCount(Math.max(1, Math.min(100000, Number(e.target.value) || 1)))}
              className="mt-1 w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            {RAILS.map((r) => (
              <button
                key={r.id}
                onClick={() => toggleRail(r.id)}
                className={`px-2.5 py-1 rounded-full text-[11px] font-semibold border ${rails.includes(r.id) ? "bg-sky-600 text-white border-sky-600" : "bg-white text-slate-600 border-slate-300"}`}
              >
                {r.label}
              </button>
            ))}
          </div>
          <button
            onClick={handleGenerate}
            disabled={busy || rails.length === 0}
            title={rails.length === 0 ? "Select at least one rail" : undefined}
            className="w-full py-2 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white rounded-lg text-xs font-bold flex items-center justify-center space-x-2"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            <span>Generate</span>
          </button>
        </div>
      </div>

      {notice && (
        <div className={`p-3 rounded-lg text-xs font-medium border ${notice.kind === "ok" ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-800"}`}>
          {notice.text}
        </div>
      )}

      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-slate-800">Recent batches</h2>
        <button onClick={load} className="p-1.5 rounded-md border border-slate-200 bg-white hover:bg-slate-100 text-slate-500" title="Refresh">
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {error ? (
        <div className="bg-white rounded-xl border border-slate-200"><ErrorState message={error} onRetry={load} /></div>
      ) : !batches ? (
        <LoadingState label="Loading batches..." />
      ) : batches.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200">
          <EmptyState title="No batches yet" hint="Upload a file or generate a demo batch to see results here." />
        </div>
      ) : (
        <div className="space-y-3">
          {batches.map((b) => {
            const tone = BATCH_TONE[b.status] ?? "grey";
            const t = TONE_CLASSES[tone];
            const pct = b.total > 0 ? Math.min(100, Math.round((b.processed / b.total) * 100)) : 0;
            const s = b.summary ?? {};
            const cards: Array<[string, React.ReactNode]> = [
              ["Total", b.total.toLocaleString()],
              ["Processed", b.processed.toLocaleString()],
              ["Failed", b.failed.toLocaleString()],
              ["Duplicates", b.duplicates.toLocaleString()],
              ["STP eligible", s.stp_eligible !== undefined ? s.stp_eligible.toLocaleString() : "n/a"],
              ["Speed", b.records_per_sec ? `${Math.round(b.records_per_sec).toLocaleString()}/s` : "n/a"],
            ];
            return (
              <div key={b.batch_id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-slate-900">{b.batch_id}</span>
                    {b.filename && <span className="text-[11px] text-slate-500">{b.filename}</span>}
                    <span className={`inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-md border text-[10px] font-semibold ${t.chip}`}>
                      {b.status === "PROCESSING" ? <Loader2 className="w-3 h-3 animate-spin" /> : <span className={`w-1.5 h-1.5 rounded-full ${t.dot}`} />}
                      <span>{b.status}</span>
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button onClick={onOpenWorklist} className="px-2.5 py-1 text-[11px] font-semibold rounded-md bg-sky-50 text-sky-700 hover:bg-sky-100">Open worklist</button>
                    <button
                      onClick={() => downloadBatchResults(b.batch_id).catch((e) => setNotice({ kind: "err", text: e?.message || "Download failed" }))}
                      disabled={b.status !== "COMPLETED"}
                      title={b.status !== "COMPLETED" ? "Results are available when the batch has completed" : undefined}
                      className="px-2.5 py-1 text-[11px] font-semibold rounded-md border border-slate-300 text-slate-700 hover:bg-slate-100 disabled:opacity-40 flex items-center space-x-1"
                    >
                      <Download className="w-3 h-3" />
                      <span>Results</span>
                    </button>
                  </div>
                </div>
                {(b.status === "PROCESSING" || b.status === "QUEUED") && (
                  <div>
                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-sky-500 transition-all" style={{ width: `${pct}%` }} />
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1 font-mono">{pct}%</div>
                  </div>
                )}
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                  {cards.map(([k, v]) => (
                    <div key={k} className="bg-slate-50 rounded-lg px-3 py-2 border border-slate-100">
                      <div className="text-[10px] uppercase text-slate-400 font-mono">{k}</div>
                      <div className="text-sm font-bold text-slate-800 font-mono">{v}</div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
