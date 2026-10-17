import React, { useCallback, useEffect, useRef, useState } from "react";
import { CasePage } from "../../types";
import { fetchCasesPage } from "../../services/api";
import { Search, RefreshCw, ArrowUp, ArrowDown } from "lucide-react";
import { StatusBadge } from "../common/StatusBadge";
import { Pagination } from "../common/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../common/States";
import { STATUS_FILTER_OPTIONS, slaTone, TONE_CLASSES } from "../../lib/statusMeta";

interface Props {
  onSelectCase: (caseId: string) => void;
  onNavigateApprovals: () => void;
  initialSearch?: string;
  refreshKey?: number;
}

const PAGE_SIZE = 50;
const SORTS: Array<{ value: string; label: string }> = [
  { value: "sla_due_at", label: "SLA due" },
  { value: "created_at", label: "Created" },
  { value: "amount", label: "Amount" },
  { value: "priority", label: "Priority" },
];
const sel = "px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg font-medium text-slate-700";

export const ExceptionWorklist: React.FC<Props> = ({ onSelectCase, onNavigateApprovals, initialSearch = "", refreshKey = 0 }) => {
  const [queue, setQueue] = useState("All");
  const [status, setStatus] = useState("All");
  const [profile, setProfile] = useState("All");
  const [rail, setRail] = useState("All");
  const [currency, setCurrency] = useState("All");
  const [search, setSearch] = useState(initialSearch);
  const [debounced, setDebounced] = useState(initialSearch);
  const [sort, setSort] = useState("sla_due_at");
  const [order, setOrder] = useState<"asc" | "desc">("asc");
  const [offset, setOffset] = useState(0);

  const [data, setData] = useState<CasePage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reqId = useRef(0);

  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(search), 300);
    return () => window.clearTimeout(t);
  }, [search]);

  useEffect(() => setOffset(0), [queue, status, profile, rail, currency, debounced, sort, order]);

  const load = useCallback(async () => {
    const id = ++reqId.current;
    setLoading(true);
    try {
      const r = await fetchCasesPage({ limit: PAGE_SIZE, offset, queue, status, profile, rail, currency, q: debounced, sort, order });
      if (id !== reqId.current) return;
      setData(r);
      setError(null);
    } catch (e: any) {
      if (id !== reqId.current) return;
      setError(e?.message || "Could not load cases");
    } finally {
      if (id === reqId.current) setLoading(false);
    }
  }, [offset, queue, status, profile, rail, currency, debounced, sort, order]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const clear = () => {
    setQueue("All"); setStatus("All"); setProfile("All"); setRail("All"); setCurrency("All"); setSearch("");
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Exception Worklist</h1>
          <p className="text-xs text-slate-500 mt-1">Server-side filtering, sorting and paging. Only the current page is loaded.</p>
        </div>
        <div className="flex items-center space-x-2">
          <div className="text-xs font-mono font-semibold text-slate-500 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm">
            {data ? `${data.total.toLocaleString()} CASES` : "..."}
          </div>
          <button onClick={load} className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-500" title="Refresh">
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search case, UETR, reference or party..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20"
          />
        </div>
        <select aria-label="Status" value={status} onChange={(e) => setStatus(e.target.value)} className={sel}>
          <option value="All">All statuses</option>
          {STATUS_FILTER_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select aria-label="Queue" value={queue} onChange={(e) => setQueue(e.target.value)} className={sel}>
          <option value="All">All queues</option>
          <option value="Repair">Repair</option>
          <option value="Compliance">Compliance</option>
          <option value="Investigation">Investigation</option>
          <option value="Treasury">Treasury</option>
        </select>
        <select aria-label="Exception type" value={profile} onChange={(e) => setProfile(e.target.value)} className={sel}>
          <option value="All">All types</option>
          <option value="INVALID_IBAN">Invalid IBAN</option>
          <option value="INVALID_BIC">Invalid BIC</option>
          <option value="DUPLICATE_PAYMENT">Duplicate payment</option>
          <option value="SANCTIONS_SUSPECTED">Sanctions match</option>
          <option value="KYC_EXPIRED">KYC expired</option>
          <option value="RETURNED_PAYMENT">Returned payment</option>
        </select>
        <select aria-label="Rail" value={rail} onChange={(e) => setRail(e.target.value)} className={sel}>
          <option value="All">All rails</option>
          <option value="SEPA_SCT">SEPA SCT</option>
          <option value="SEPA_INST">SEPA Instant</option>
          <option value="T2">T2</option>
          <option value="SWIFT">SWIFT</option>
        </select>
        <select aria-label="Currency" value={currency} onChange={(e) => setCurrency(e.target.value)} className={sel}>
          <option value="All">All currencies</option>
          {["EUR", "USD", "GBP", "CHF"].map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <div className="flex items-center space-x-1">
          <select aria-label="Sort by" value={sort} onChange={(e) => setSort(e.target.value)} className={sel}>
            {SORTS.map((s) => <option key={s.value} value={s.value}>Sort: {s.label}</option>)}
          </select>
          <button onClick={() => setOrder(order === "asc" ? "desc" : "asc")} className="p-2 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600" title={order === "asc" ? "Ascending" : "Descending"}>
            {order === "asc" ? <ArrowUp className="w-3.5 h-3.5" /> : <ArrowDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {error ? (
          <ErrorState message={error} onRetry={load} />
        ) : !data ? (
          <LoadingState label="Loading cases..." />
        ) : data.items.length === 0 ? (
          <EmptyState
            title="No cases match these filters"
            hint="Try removing a filter, or generate a demo batch from the Batches page."
            action={<button onClick={clear} className="px-3 py-1 text-xs rounded-md border border-slate-300 hover:bg-slate-100 text-slate-700">Clear filters</button>}
          />
        ) : (
          <>
            <div className={`overflow-x-auto ${loading ? "opacity-60" : ""}`}>
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50/80 text-slate-500 uppercase font-mono text-[10px] border-b border-slate-200">
                  <tr>
                    <th className="px-5 py-3">Reference</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Queue</th>
                    <th className="px-4 py-3">Rail</th>
                    <th className="px-4 py-3">Amount</th>
                    <th className="px-4 py-3">Counterparty</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">SLA</th>
                    <th className="px-5 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {data.items.map((c) => {
                    const sla = slaTone(c.sla_due_at);
                    return (
                      <tr key={c.case_id} className="hover:bg-slate-50/60 transition-colors">
                        <td className="px-5 py-3.5 font-mono font-semibold text-sky-700">{c.case_id}</td>
                        <td className="px-4 py-3.5 font-medium text-slate-800">{String(c.profile).replace(/_/g, " ")}</td>
                        <td className="px-4 py-3.5">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-slate-100 text-slate-700">{c.queue}</span>
                        </td>
                        <td className="px-4 py-3.5 font-mono text-slate-600">{c.payment_rail}</td>
                        <td className="px-4 py-3.5 font-mono font-semibold text-slate-900">
                          {c.currency} {c.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-4 py-3.5 font-medium text-slate-800">{c.creditor_party?.party_name}</td>
                        <td className="px-4 py-3.5"><StatusBadge status={c.status} /></td>
                        <td className={`px-4 py-3.5 font-mono text-[11px] ${TONE_CLASSES[sla.tone].text}`}>{sla.label}</td>
                        <td className="px-5 py-3.5 text-right">
                          <button
                            onClick={() => { onSelectCase(c.case_id); onNavigateApprovals(); }}
                            className="px-2.5 py-1 bg-sky-50 text-sky-700 hover:bg-sky-100 rounded-md font-semibold text-xs transition-colors"
                          >
                            Open &rarr;
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="border-t border-slate-100">
              <Pagination total={data.total} limit={PAGE_SIZE} offset={offset} onChange={setOffset} />
            </div>
          </>
        )}
      </div>
    </div>
  );
};
