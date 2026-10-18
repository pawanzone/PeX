import React, { useEffect, useMemo, useState } from "react";
import { ExternalLink, Lock, User, CheckCircle2, AlertOctagon, AlertTriangle, ChevronLeft, ChevronRight } from "lucide-react";
import { PageHeader, Tabs, FilterBar, FilterSelect, SavedViewsMenu, DataTable, Loading, ErrorState, StatusPill, Banner, useToast, cn, formatRemaining } from "../components/v2";
import { navigate, routes, useQueryParam } from "../lib/router";
import { useV2 } from "../services/v2/client";
import { assignCase, fetchPreview, fetchViews, fetchWorklist, saveView, type WorkRow, type WorkTab } from "../services/v2/worklist";
import { useSession } from "../shell/session";
import { CutoffChip } from "./home/shared";

/** Worklist. Design: 03_worklist.png */
const TABS: Array<{ id: WorkTab; label: string }> = [
  { id: "ready", label: "Ready to work" }, { id: "returned", label: "Returned to me" }, { id: "waiting", label: "Waiting for info" },
  { id: "pending", label: "Pending approval" }, { id: "done", label: "Done today" },
];
const ALL = { value: "", label: "All" };
const EvidencePill: React.FC<{ row: WorkRow }> = ({ row }) => {
  const s = row.evidence?.status;
  if (s === "compliance") return <span className="inline-flex items-center gap-1.5 text-xs text-slate-600"><Lock className="w-3.5 h-3.5" aria-hidden />With Compliance</span>;
  if (!s) return <span className="text-slate-400">—</span>;
  const tone = s === "complete" ? "green" : s === "conflict" ? "red" : "amber";
  const Icon = s === "complete" ? CheckCircle2 : s === "conflict" ? AlertOctagon : AlertTriangle;
  return <StatusPill tone={tone} dot={false}><Icon className="w-3.5 h-3.5" aria-hidden />{row.evidence?.label ?? s}</StatusPill>;
};

/** Highlights the characters that differ between original and proposed (common prefix/suffix kept plain). */
const Hl: React.FC<{ v?: string; other?: string; tone: "red" | "green" }> = ({ v, other, tone }) => {
  const s = v || "(empty)";
  if (!v || other === undefined) return <span className="pex-mono text-sm">{s}</span>;
  let i = 0; while (i < v.length && i < other.length && v[i] === other[i]) i++;
  let j = 0; while (j < v.length - i && j < other.length - i && v[v.length - 1 - j] === other[other.length - 1 - j]) j++;
  const mid = v.slice(i, v.length - j);
  if (!mid) return <span className="pex-mono text-sm">{s}</span>;
  return <span className="pex-mono text-sm">{v.slice(0, i)}<span className={cn("px-0.5 rounded font-semibold", tone === "red" ? "bg-red-200 text-red-800" : "bg-green-200 text-green-800")}>{mid}</span>{v.slice(v.length - j)}</span>;
};

export const Worklist: React.FC = () => {
  const { epoch, persona } = useSession();
  const toast = useToast();
  const [tabQ, setTabQ] = useQueryParam("tab", "ready");
  const tab = (TABS.some((t) => t.id === tabQ) ? tabQ : "ready") as WorkTab;
  const [scopeQ] = useQueryParam("scope", "");
  const [qParam] = useQueryParam("q", "");
  const [f, setF] = useState({ exception_type: "", rail: "", currency: "", cutoff_band: "", evidence: "" });
  const [q, setQ] = useState(qParam);
  const [page, setPage] = useState(1);
  const [sel, setSel] = useState<string | undefined>();
  const [activeView, setActiveView] = useState<string | undefined>();
  const pageSize = 25;
  useEffect(() => setQ(qParam), [qParam]);
  useEffect(() => { setPage(1); setSel(undefined); }, [tab, f, q, scopeQ, epoch]);

  const list = useV2(() => fetchWorklist({ tab, page, page_size: pageSize, ...f, q: q || undefined, sort: "cutoff", dir: "asc", scope: scopeQ || undefined }), [tab, page, f, q, scopeQ, epoch]);
  const views = useV2(fetchViews, [epoch]);
  const items = list.data?.items ?? [];
  const selected = useMemo(() => items.find((i) => i.case_id === sel) ?? items[0], [items, sel]);
  const prev = useV2(() => selected ? fetchPreview(selected.case_id) : Promise.resolve(null), [selected?.case_id]);
  const counts = list.data?.counts;
  const fac = list.data?.facets;
  const total = list.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / pageSize));

  const opts = (xs?: Array<{ value: string; label: string }>) => [ALL, ...(xs ?? [])];
  const onSelectView = (id: string) => {
    const v = views.data?.find((x) => x.id === id); if (!v) return;
    setActiveView(id);
    const fl = v.filters ?? {};
    setF({ exception_type: fl.exception_type ?? "", rail: fl.rail ?? "", currency: fl.currency ?? "", cutoff_band: fl.cutoff_band ?? "", evidence: fl.evidence ?? "" });
    if (fl.q !== undefined) setQ(fl.q);
    if (fl.tab) setTabQ(fl.tab);
  };
  const onSaveView = async () => {
    const name = window.prompt("Name for this view");
    if (!name) return;
    try { await saveView(name, { tab, ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)), ...(q ? { q } : {}) } as Record<string, string>, "cutoff"); toast.push("View saved"); views.reload(); }
    catch (e: any) { toast.push(e?.message || "Could not save view", "red"); }
  };
  const assign = async (id: string) => {
    try { const r = await assignCase(id, "me"); toast.push(`${id} assigned to ${r.assignee?.name ?? "you"}`); list.reload(); }
    catch (e: any) { toast.push(e?.message || "Could not assign", "red"); }
  };

  const canAssign = !!selected && (!selected.assignee || selected.assignee.user_id !== persona?.user_id) && tab !== "done";
  return (
    <>
      <PageHeader title="Worklist" />
      <Tabs label="Worklist tabs" value={tab} onChange={(id) => setTabQ(id)} tabs={TABS.map((t) => ({ id: t.id, label: t.label, count: counts?.[t.id] }))} />
      <FilterBar search={{ value: q, onChange: setQ, placeholder: "Search case, party or reference" }}
        right={<SavedViewsMenu views={(views.data ?? []).map((v) => ({ id: v.id, label: v.name }))} activeId={activeView} onSelect={onSelectView} onSave={onSaveView} />}>
        <FilterSelect label="Exception type" value={f.exception_type} onChange={(v) => setF({ ...f, exception_type: v })} options={opts(fac?.exception_types)} />
        <FilterSelect label="Rail" value={f.rail} onChange={(v) => setF({ ...f, rail: v })} options={opts(fac?.rails)} />
        <FilterSelect label="Currency" value={f.currency} onChange={(v) => setF({ ...f, currency: v })} options={[ALL, ...(fac?.currencies ?? []).map((c) => ({ value: c, label: c }))]} />
        <FilterSelect label="Cutoff" value={f.cutoff_band} onChange={(v) => setF({ ...f, cutoff_band: v })} options={[ALL, { value: "under_1h", label: "Under 1 hour" }, { value: "1_to_3h", label: "1 to 3 hours" }, { value: "over_3h", label: "Over 3 hours" }]} />
        <FilterSelect label="Evidence" value={f.evidence} onChange={(v) => setF({ ...f, evidence: v })} options={[ALL, { value: "complete", label: "Complete" }, { value: "conflict", label: "Conflict" }, { value: "missing", label: "Missing" }, { value: "compliance", label: "With Compliance" }]} />
      </FilterBar>
      {scopeQ === "all" && <div className="mb-3"><Banner tone="blue">Showing all cases (supervisor scope).</Banner></div>}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_22rem] gap-4 items-start">
        <div className="bg-surface-card rounded-card border border-surface-line shadow-card">
          <DataTable<WorkRow> caption={`Worklist: ${TABS.find((t) => t.id === tab)?.label}`} loading={list.loading} error={list.error} onRetry={list.reload}
            rows={items} rowKey={(r) => r.case_id} selectedKey={selected?.case_id} onRowClick={(r) => setSel(r.case_id)}
            emptyTitle="No cases in this view" emptyHint="Change the tab or clear filters."
            columns={[
              { key: "co", header: "Cutoff ↑", render: (r) => <CutoffChip cutoff={r.cutoff} />, width: "6rem" },
              { key: "id", header: "Case", render: (r) => <span className="font-medium">{r.case_id}</span> },
              { key: "ex", header: "Exception", render: (r) => r.exception?.label ?? "—" },
              { key: "am", header: "Amount", mono: true, render: (r) => r.amount?.display ?? "—" },
              { key: "ra", header: "Rail", render: (r) => <span className="text-pex-muted">{r.rail?.label ?? "—"}</span> },
              { key: "cp", header: "Counterparty", render: (r) => r.counterparty ?? "—" },
              { key: "na", header: "Next action", render: (r) => r.next_action?.text ? <button className="text-left text-pex-primary hover:underline" onClick={(e) => { e.stopPropagation(); navigate(routes.workCase(r.case_id)); }}>{r.next_action.text}</button> : "—" },
              { key: "ev", header: "Evidence", render: (r) => <EvidencePill row={r} /> },
            ]}
            footer={!list.loading && !list.error && total > 0 ? (
              <div className="flex items-center justify-between px-3 py-2 text-xs text-pex-muted border-t border-surface-line">
                <span>Showing {(page - 1) * pageSize + 1}–{Math.min(total, page * pageSize)} of {total}</span>
                <span className="flex items-center gap-1">
                  <button aria-label="Previous page" disabled={page <= 1} onClick={() => setPage(page - 1)} className="p-1 rounded border border-surface-line disabled:opacity-40"><ChevronLeft className="w-4 h-4" /></button>
                  <span>Page {page} of {pages}</span>
                  <button aria-label="Next page" disabled={page >= pages} onClick={() => setPage(page + 1)} className="p-1 rounded border border-surface-line disabled:opacity-40"><ChevronRight className="w-4 h-4" /></button>
                </span>
              </div>) : null} />
        </div>

        <aside aria-label="Case preview" className="bg-surface-card rounded-card border border-surface-line shadow-card p-4 xl:sticky xl:top-4">
          {!selected ? <p className="text-sm text-pex-muted">Select a case to preview it.</p> : prev.loading ? <Loading /> : prev.error ? <ErrorState message={prev.error} onRetry={prev.reload} /> : (() => {
            const p = prev.data;
            return (
              <>
                <h2 className="text-xl font-semibold">{selected.case_id}</h2>
                <p className="text-sm text-pex-muted">{selected.exception?.label} · <span className="pex-mono">{selected.amount?.display}</span></p>
                <dl className="mt-4 divide-y divide-surface-line text-sm">
                  <div className="py-2.5 grid grid-cols-[7rem_1fr] gap-3"><dt className="text-pex-muted">Why flagged</dt><dd>{p?.why_flagged ?? "—"}</dd></div>
                  {p?.change && (
                    <div className="py-2.5 grid grid-cols-[7rem_1fr] gap-3"><dt className="text-pex-muted">Proposed change</dt>
                      <dd><div className="font-medium mb-1.5">{p.change.field}</div>
                        <div className="rounded-lg border border-red-200 bg-red-50 p-2 mb-2"><div className="text-xs text-red-700 mb-0.5">Original (failed validation)</div><Hl v={p.change.original} other={p.change.proposed} tone="red" /></div>
                        <div className="rounded-lg border border-green-200 bg-green-50 p-2"><div className="text-xs text-green-700 mb-0.5">Proposed (passes validation)</div><Hl v={p.change.proposed} other={p.change.original} tone="green" /></div>
                      </dd></div>)}
                  <div className="py-2.5 grid grid-cols-[7rem_1fr] gap-3"><dt className="text-pex-muted">Evidence</dt><dd>{p?.evidence_summary ?? selected.evidence?.label ?? "—"}</dd></div>
                  <div className="py-2.5 grid grid-cols-[7rem_1fr] gap-3"><dt className="text-pex-muted">Controls</dt><dd>{(p?.controls ?? []).length ? p!.controls!.map((c, i) => <div key={i}>{c.label} <span className="text-xs text-pex-muted">({c.state})</span></div>) : "—"}</dd></div>
                  <div className="py-2.5 grid grid-cols-[7rem_1fr] gap-3"><dt className="text-pex-muted">Next action</dt><dd>{p?.next_action?.text ?? selected.next_action?.text ?? "—"}{(p?.next_action?.owner ?? selected.assignee?.name) ? ` · ${p?.next_action?.owner ?? selected.assignee?.name}` : ""}</dd></div>
                </dl>
                <a href={routes.workCase(selected.case_id)} className="mt-4 flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-pex-primary text-white font-medium hover:bg-pex-primary-dark focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-pex-primary"><ExternalLink className="w-4 h-4" aria-hidden />Open case</a>
                <button disabled={!canAssign} onClick={() => assign(selected.case_id)} title={canAssign ? undefined : "Already assigned to you, or not assignable in this tab"} className="mt-2 flex items-center justify-center gap-2 w-full py-2.5 rounded-lg border border-surface-line bg-white font-medium text-pex-primary hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"><User className="w-4 h-4" aria-hidden />Assign to me</button>
              </>
            );
          })()}
        </aside>
      </div>
    </>
  );
};
