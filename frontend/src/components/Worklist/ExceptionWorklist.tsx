import React, { useState } from "react";
import { PeXCase } from "../../types";
import { Search, Filter, ArrowRight, ShieldAlert, CheckCircle2 } from "lucide-react";

interface Props {
  cases: PeXCase[];
  onSelectCase: (caseId: string) => void;
  onNavigateApprovals: () => void;
}

export const ExceptionWorklist: React.FC<Props> = ({
  cases,
  onSelectCase,
  onNavigateApprovals,
}) => {
  const [queueFilter, setQueueFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [profileFilter, setProfileFilter] = useState("All");
  const [search, setSearch] = useState("");

  const filteredCases = cases.filter((c) => {
    if (queueFilter !== "All" && c.queue !== queueFilter) return false;
    if (statusFilter !== "All" && c.status !== statusFilter) return false;
    if (profileFilter !== "All" && c.profile !== profileFilter) return false;
    if (search) {
      const s = search.toLowerCase();
      const match =
        c.case_id.toLowerCase().includes(s) ||
        c.uetr.toLowerCase().includes(s) ||
        c.creditor_party?.party_name?.toLowerCase().includes(s) ||
        c.debtor_party?.party_name?.toLowerCase().includes(s);
      if (!match) return false;
    }
    return true;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Exception Worklist</h1>
          <p className="text-xs text-slate-500 mt-1">Unified exception operations queue — server-filtered and tenant-scoped</p>
        </div>
        <div className="text-xs font-mono font-semibold text-slate-500 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm">
          {filteredCases.length} OF {cases.length} CASES
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search reference or party..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg font-medium text-slate-700"
        >
          <option value="All">All Statuses</option>
          <option value="PENDING_APPROVAL">Pending Approval</option>
          <option value="AWAITING_SECOND_APPROVAL">Awaiting Second Approval</option>
          <option value="INVESTIGATING">Investigating</option>
          <option value="SETTLED">Settled</option>
          <option value="ESCALATED">Escalated</option>
          <option value="REJECTED">Rejected</option>
        </select>

        <select
          value={queueFilter}
          onChange={(e) => setQueueFilter(e.target.value)}
          className="px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg font-medium text-slate-700"
        >
          <option value="All">All Queues</option>
          <option value="Repair">Repair</option>
          <option value="Compliance">Compliance</option>
          <option value="Investigation">Investigation</option>
          <option value="Treasury">Treasury</option>
        </select>

        <select
          value={profileFilter}
          onChange={(e) => setProfileFilter(e.target.value)}
          className="px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg font-medium text-slate-700"
        >
          <option value="All">All Types</option>
          <option value="INVALID_IBAN">Invalid IBAN</option>
          <option value="INVALID_BIC">Invalid BIC</option>
          <option value="DUPLICATE_PAYMENT">Duplicate Payment</option>
          <option value="SANCTIONS_SUSPECTED">Sanctions Match</option>
          <option value="KYC_EXPIRED">KYC Expired</option>
          <option value="RETURNED_PAYMENT">Returned Payment</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 text-slate-500 uppercase font-mono text-[10px] border-b border-slate-200">
              <tr>
                <th className="px-5 py-3">Reference</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Queue</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Counterparty</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-5 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {filteredCases.map((c) => (
                <tr key={c.case_id} className="hover:bg-slate-50/60 transition-colors">
                  <td className="px-5 py-3.5 font-mono font-semibold text-sky-700">{c.case_id}</td>
                  <td className="px-4 py-3.5 font-medium text-slate-800">{c.profile}</td>
                  <td className="px-4 py-3.5">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-slate-100 text-slate-700">
                      {c.queue}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-mono font-semibold text-slate-900">
                    {c.currency} {c.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-4 py-3.5 font-medium text-slate-800">{c.creditor_party?.party_name}</td>
                  <td className="px-4 py-3.5">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold font-mono border ${
                      c.status === "SETTLED" ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                      c.status === "ESCALATED" ? "bg-purple-50 text-purple-700 border-purple-200" :
                      c.status === "AWAITING_SECOND_APPROVAL" ? "bg-indigo-50 text-indigo-700 border-indigo-200" :
                      "bg-amber-50 text-amber-700 border-amber-200"
                    }`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                      c.priority === "CRITICAL" ? "bg-red-100 text-red-700" :
                      c.priority === "HIGH" ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-600"
                    }`}>
                      {c.priority}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <button
                      onClick={() => {
                        onSelectCase(c.case_id);
                        onNavigateApprovals();
                      }}
                      className="px-2.5 py-1 bg-sky-50 text-sky-700 hover:bg-sky-100 rounded-md font-semibold text-xs transition-colors"
                    >
                      Investigate &rarr;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
