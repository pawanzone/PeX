import React, { useEffect, useMemo, useState } from "react";
import { Check, X, AlertTriangle, Minus, Download, FileText, ExternalLink } from "lucide-react";
import { PageHeader, Tabs, FilterBar, FilterSelect, DataTable, StatusPill, Banner, Loading, ErrorState, KeyValueList, useToast } from "../components/v2";
import { useV2 } from "../services/v2/client";
import { getAuditEvents, getAuditEvent, getControlReports, getAuditCases, downloadAuditExport, downloadCaseReport, type AuditEventRow, type AuditFilters, type CaseReportRow } from "../services/v2/audit";
import { navigate, routes, useRoute } from "../lib/router";
import { useSession } from "../shell/session";
import { hhmm, hhmmss } from "./compliance/fmt";

/** Audit: events, case reports, control reports. Read-only for the Audit and Risk role. Design: 13_audit_events.png. */
const OUTCOME: Record<string, { tone: "green" | "red" | "amber" | "grey"; icon: React.ElementType }> = {
  approved: { tone: "green", icon: Check }, passed: { tone: "green", icon: Check },
  blocked: { tone: "red", icon: X }, held: { tone: "amber", icon: AlertTriangle },
  submitted: { tone: "grey", icon: Minus }, unknown: { tone: "grey", icon: Minus },
};
const asOpts = (l: Array<string | { value: string; label?: string }> | undefined, all: string) =>
  [{ value: "", label: all }, ...(l ?? []).map((x) => (typeof x === "string" ? { value: x, label: x } : { value: x.value, label: x.label ?? x.value }))];

const todayRange = (key: string): { date_from?: string; date_to?: string } => {
  const now = new Date(); const d0 = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  if (key === "today") return { date_from: iso(d0), date_to: iso(d0) };
  if (key === "7d") return { date_from: iso(new Date(d0.getTime() - 6 * 864e5)), date_to: iso(d0) };
  if (key === "30d") return { date_from: iso(new Date(d0.getTime() - 29 * 864e5)), date_to: iso(d0) };
  return {};
};

export const Audit: React.FC = () => {
  const route = useRoute();
  const [tab, setTab] = useState<"events" | "cases" | "controls">("events");
  return (
    <>
      <PageHeader title="Audit" subtitle="Every decision and control result, with who did it and when." />
      <Tabs tabs={[{ id: "events", label: "Events" }, { id: "cases", label: "Case reports" }, { id: "controls", label: "Control reports" }]} value={tab} onChange={(t) => setTab(t as any)} label="Audit sections" />
      <div className="mt-3">
        {tab === "events" && <Events initialCase={route.query.case || route.query.case_id || ""} />}
        {tab === "cases" && <CaseReports />}
        {tab === "controls" && <Controls />}
      </div>
    </>
  );
};

const Events: React.FC<{ initialCase: string }> = ({ initialCase }) => {
  const { epoch, persona } = useSession();
  const toast = useToast();
  const [range, setRange] = useState("today");
  const [f, setF] = useState({ event_type: "", actor: "", role: "", exception_type: "", rail: "", q: initialCase });
  const [page, setPage] = useState(1);
  const [sel, setSel] = useState<string>("");
  const filters: AuditFilters = useMemo(() => ({ ...todayRange(range), ...f, page, page_size: 25 }), [range, f, page]);
  const ev = useV2(() => getAuditEvents(filters), [JSON.stringify(filters), epoch]);
  const rows = ev.data?.items ?? [];
  useEffect(() => { if (rows.length && !rows.some((r) => r.id === sel)) setSel(rows[0].id); if (!rows.length) setSel(""); }, [rows, sel]);
  const set = (k: keyof typeof f) => (v: string) => { setF((x) => ({ ...x, [k]: v })); setPage(1); };
  const readOnly = persona?.role === ("AUDIT_RISK" as any);
  const selRow = rows.find((r) => r.id === sel);
  const total = ev.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / 25));

  return (
    <>
      {readOnly && <div className="mb-2"><Banner tone="grey" title="Read only">Your role can view and export the audit trail but cannot change anything.</Banner></div>}
      <FilterBar search={{ value: f.q, onChange: set("q"), placeholder: "Search case or reference" }}>
        <FilterSelect label="Date" value={range} onChange={(v) => { setRange(v); setPage(1); }} options={[{ value: "today", label: "Today" }, { value: "7d", label: "Last 7 days" }, { value: "30d", label: "Last 30 days" }, { value: "all", label: "All time" }]} />
        <FilterSelect label="Event type" value={f.event_type} onChange={set("event_type")} options={asOpts(ev.data?.facets?.event_types, "All")} />
        <FilterSelect label="Actor" value={f.actor} onChange={set("actor")} options={asOpts(ev.data?.facets?.actors, "All")} />
        <FilterSelect label="Role" value={f.role} onChange={set("role")} options={asOpts(ev.data?.facets?.roles, "All")} />
        <FilterSelect label="Exception type" value={f.exception_type} onChange={set("exception_type")} options={[{ value: "", label: "All" }, { value: "DQ-01", label: "Invalid IBAN" }, { value: "DQ-06", label: "Missing purpose code" }]} />
        <FilterSelect label="Rail" value={f.rail} onChange={set("rail")} options={[{ value: "", label: "All" }, { value: "SWIFT_CBPR+", label: "SWIFT CBPR+" }, { value: "SEPA_SCT", label: "SEPA SCT" }, { value: "FPS", label: "Faster Payments" }, { value: "ACH", label: "ACH" }]} />
      </FilterBar>
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4 items-start">
        <div className="bg-surface-card rounded-card border border-surface-line shadow-card p-2 min-w-0">
          {ev.loading && !ev.data ? <Loading /> : ev.error ? <ErrorState unavailable={ev.unavailable} message={ev.error} onRetry={ev.reload} /> : (
            <DataTable<AuditEventRow> caption="Audit events" rows={rows} rowKey={(r) => r.id} selectedKey={sel} onRowClick={(r) => setSel(r.id)}
              emptyTitle="No events match" emptyHint="Change the date range or filters."
              columns={[
                { key: "t", header: "Time", render: (r) => hhmm(r.time) },
                { key: "c", header: "Case", mono: true, render: (r) => r.case_id ? <a href={routes.worklist({ q: r.case_id })} onClick={(e) => { e.stopPropagation(); e.preventDefault(); navigate(routes.workCase(r.case_id!)); }} className="text-pex-primary hover:underline">{r.case_id}</a> : "—" },
                { key: "e", header: "Event", render: (r) => r.event },
                { key: "a", header: "Actor", render: (r) => r.actor },
                { key: "r", header: "Role", render: (r) => r.role },
                { key: "o", header: "Outcome", render: (r) => { const m = OUTCOME[(r.outcome || "").toLowerCase()] ?? { tone: "grey" as const, icon: Minus }; const I = m.icon; return r.outcome ? <StatusPill tone={m.tone} dot={false}><I className="w-3.5 h-3.5" aria-hidden />{r.outcome}</StatusPill> : null; } },
                { key: "d", header: "Detail", render: (r) => <span className="text-pex-muted">{r.detail}</span> },
              ]}
              footer={
                <div className="flex items-center justify-between gap-3 flex-wrap px-3 py-3 text-xs text-pex-muted">
                  <span>Showing {rows.length} of {total} events{ev.data?.integrity ? ` · chain ${ev.data.integrity.chain_valid ? "verified" : "NOT verified"}` : ""}</span>
                  <span className="inline-flex items-center gap-2">
                    {pages > 1 && <><button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-2 py-1 rounded border border-surface-line disabled:opacity-40">Previous</button><span>Page {page} of {pages}</span><button disabled={page >= pages} onClick={() => setPage(page + 1)} className="px-2 py-1 rounded border border-surface-line disabled:opacity-40">Next</button></>}
                    <button onClick={() => downloadAuditExport(filters).catch((e) => toast.push(e?.message || "Export failed", "red"))} className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-pex-primary text-pex-primary bg-white hover:bg-pex-primary-soft"><Download className="w-4 h-4" aria-hidden />Export events</button>
                    <button disabled={!selRow?.case_id} title={selRow?.case_id ? undefined : "Select an event first"} onClick={() => selRow?.case_id && downloadCaseReport(selRow.case_id).catch((e) => toast.push(e?.message || "Export failed", "red"))} className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-pex-primary text-pex-primary bg-white hover:bg-pex-primary-soft disabled:opacity-50"><FileText className="w-4 h-4" aria-hidden />Export case report</button>
                  </span>
                </div>
              } />
          )}
        </div>
        <Detail id={sel} />
      </div>
    </>
  );
};

const Detail: React.FC<{ id: string }> = ({ id }) => {
  const d = useV2(() => (id ? getAuditEvent(id) : Promise.resolve(null)), [id]);
  const e = d.data;
  return (
    <aside aria-label="Event detail" className="bg-surface-card rounded-card border border-surface-line shadow-card p-5">
      <h2 className="text-base font-semibold text-pex-ink mb-3">Event detail</h2>
      {!id ? <div className="text-sm text-pex-muted">Select an event.</div> : d.loading ? <Loading /> : d.error || !e ? <ErrorState unavailable={d.unavailable} message={d.error ?? undefined} onRetry={d.reload} /> : (
        <>
          <KeyValueList cols={1} items={[
            { label: "Event", value: e.event ?? "—" },
            { label: "Case", value: e.case_id ? <a className="text-pex-primary hover:underline pex-mono" href={routes.workCase(e.case_id)}>{e.case_id}</a> : "—" },
            { label: "Actor", value: e.actor ? `${e.actor.name ?? ""}${e.actor.role ? " · " + e.actor.role : ""}` : "—" },
            { label: "Time", value: hhmmss(e.time) || "—" },
            ...(e.before != null || e.after != null ? [{ label: "Before", value: e.before ?? "—", mono: true }, { label: "After", value: e.after ?? "—", mono: true }] : []),
            { label: "Evidence reviewed", value: e.evidence_reviewed != null ? `${e.evidence_reviewed} items` : "—" },
            { label: "Policy version", value: e.policy_version ?? "—" },
            { label: "Separation of duties", value: e.sod?.result ?? "—" },
            { label: "Reason", value: e.reason ?? "—" },
            { label: "Integrity", value: e.integrity ? (e.integrity.sealed ? `Record sealed${e.integrity.verified ? " · verified" : " · not verified"}` : "Not sealed") : "—" },
          ]} />
          {e.integrity?.hash && <div className="mt-2 text-[11px] text-pex-muted pex-mono break-all">hash {e.integrity.hash}</div>}
          {e.case_id && <a href={routes.workCase(e.case_id)} className="mt-4 pt-3 border-t border-surface-line text-sm text-pex-primary inline-flex items-center gap-1.5 w-full hover:underline"><ExternalLink className="w-4 h-4" aria-hidden />Open case journey</a>}
        </>
      )}
    </aside>
  );
};

const CaseReports: React.FC = () => {
  const { epoch } = useSession();
  const toast = useToast();
  const [q, setQ] = useState("");
  const r = useV2(() => getAuditCases(q), [q, epoch]);
  return (
    <>
      <FilterBar search={{ value: q, onChange: setQ, placeholder: "Search case" }}>{null}</FilterBar>
      <div className="bg-surface-card rounded-card border border-surface-line shadow-card p-2">
        {r.loading && !r.data ? <Loading /> : r.error ? <ErrorState unavailable={r.unavailable} message={r.error} onRetry={r.reload} /> : (
          <DataTable<CaseReportRow> caption="Case reports" rows={r.data ?? []} rowKey={(x) => x.case_id} emptyTitle="No cases"
            columns={[
              { key: "id", header: "Case", mono: true, render: (x) => x.case_id },
              { key: "ex", header: "Exception", render: (x) => x.exception ?? "—" },
              { key: "am", header: "Amount", align: "right", mono: true, render: (x) => (typeof x.amount === "object" ? x.amount?.display : x.amount) ?? "—" },
              { key: "st", header: "Status", render: (x) => x.status ?? "—" },
              { key: "n", header: "Events", align: "right", render: (x) => x.events ?? 0 },
              { key: "l", header: "Last event", render: (x) => hhmm(x.last_event) || "—" },
              { key: "a", header: "Report", render: (x) => <button onClick={() => downloadCaseReport(x.case_id).catch((e) => toast.push(e?.message || "Export failed", "red"))} className="text-pex-primary hover:underline">Download CSV</button> },
            ]} />
        )}
      </div>
    </>
  );
};

const Controls: React.FC = () => {
  const { epoch } = useSession();
  const r = useV2(getControlReports, [epoch]);
  if (r.loading && !r.data) return <Loading />;
  if (r.error) return <ErrorState unavailable={r.unavailable} message={r.error} onRetry={r.reload} />;
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      {(r.data ?? []).map((c) => (
        <div key={c.id} className="bg-surface-card rounded-card border border-surface-line shadow-card p-4">
          <div className="text-sm font-semibold text-pex-ink">{c.name}</div>
          <div className="text-xs text-pex-muted">{c.period ?? ""}</div>
          <div className="mt-3 flex items-center gap-3 text-sm">
            <StatusPill tone="green">{c.passed ?? 0} passed</StatusPill>
            <StatusPill tone={(c.failed ?? 0) > 0 ? "red" : "grey"}>{c.failed ?? 0} failed</StatusPill>
          </div>
        </div>
      ))}
      {!r.data?.length && <div className="text-sm text-pex-muted">No control reports yet.</div>}
    </div>
  );
};
