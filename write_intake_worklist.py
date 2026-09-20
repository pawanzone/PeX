import os

comp_dir = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\src\components"

# 1. Intake/PaymentIntake.tsx
with open(os.path.join(comp_dir, "Intake", "PaymentIntake.tsx"), "w", encoding="utf-8") as f:
    f.write('''import React, { useState } from "react";
import { initiatePayment } from "../../services/api";
import { PlusCircle, CheckCircle2, Shield, ArrowRight, Zap, RefreshCw } from "lucide-react";

interface Props {
  onSuccess: (caseId: string) => void;
}

export const PaymentIntake: React.FC<Props> = ({ onSuccess }) => {
  const [clientRef, setClientRef] = useState("CLIENT-REF-2026-001");
  const [rail, setRail] = useState("SWIFT / CBPR+");
  const [profile, setProfile] = useState("INVALID_IBAN");
  const [debtorName, setDebtorName] = useState("Acme Global Holdings");
  const [creditorName, setCreditorName] = useState("Nordhavn Components A/S");
  const [amount, setAmount] = useState(250000);
  const [currency, setCurrency] = useState("USD");
  const [country, setCountry] = useState("DK");
  const [reason, setReason] = useState("Beneficiary account identifier failed validation against the receiving bank profile.");
  const [correctedIban, setCorrectedIban] = useState("GB82 WEST 1234 5698 7654 32");
  
  const [loading, setLoading] = useState(false);
  const [submittedCaseId, setSubmittedCaseId] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await initiatePayment({
        client_reference: clientRef,
        payment_rail: rail,
        exception_profile: profile,
        debtor_name: debtorName,
        creditor_name: creditorName,
        amount: Number(amount),
        currency,
        beneficiary_country: country,
        exception_reason: reason,
        corrected_beneficiary_iban: correctedIban,
      });
      if (res.success) {
        setSubmittedCaseId(res.case_id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Payment Intake &amp; Origination Simulator</h1>
        <p className="text-xs text-slate-500 mt-1">Submit synthetic payment exceptions through the canonical PeX intake contract</p>
      </div>

      {submittedCaseId ? (
        <div className="bg-white p-8 rounded-2xl border border-emerald-200 shadow-sm text-center space-y-4 max-w-xl mx-auto">
          <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-7 h-7" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">Payment Accepted Into PeX Lifecycle</h2>
          <p className="text-xs text-slate-600">
            Case <span className="font-mono font-bold text-sky-700">{submittedCaseId}</span> has passed intake schema validation, PII tokenization, and initial AI evidence planning.
          </p>
          <div className="pt-2 flex justify-center space-x-3">
            <button
              onClick={() => onSuccess(submittedCaseId)}
              className="px-5 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all"
            >
              <span>View Case in Approvals</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => setSubmittedCaseId(null)}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-all"
            >
              Submit Another
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <form onSubmit={handleSubmit} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm lg:col-span-2 space-y-5">
            <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3">Payment Instruction Envelope</h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">CLIENT PAYMENT REFERENCE</label>
                <input
                  type="text"
                  value={clientRef}
                  onChange={(e) => setClientRef(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg font-mono"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">PAYMENT RAIL</label>
                <select
                  value={rail}
                  onChange={(e) => setRail(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg"
                >
                  <option value="SWIFT / CBPR+">SWIFT / CBPR+</option>
                  <option value="ISO 20022 pacs.008">ISO 20022 pacs.008</option>
                  <option value="Fedwire MQ">Fedwire MQ</option>
                  <option value="SEPA Credit Transfer">SEPA Credit Transfer</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">EXCEPTION PROFILE</label>
                <select
                  value={profile}
                  onChange={(e) => setProfile(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg font-semibold text-sky-700"
                >
                  <option value="INVALID_IBAN">Invalid IBAN</option>
                  <option value="INVALID_BIC">Invalid BIC / Routing</option>
                  <option value="DUPLICATE_PAYMENT">Duplicate Payment Suspected</option>
                  <option value="SANCTIONS_SUSPECTED">Sanctions Screening Match</option>
                  <option value="KYC_EXPIRED">KYC Periodic Review Expired</option>
                  <option value="RETURNED_PAYMENT">Returned Payment (pacs.004)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">DEBTOR / ORIGINATING PARTY</label>
                <input
                  type="text"
                  value={debtorName}
                  onChange={(e) => setDebtorName(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">BENEFICIARY / RECEIVING PARTY</label>
                <input
                  type="text"
                  value={creditorName}
                  onChange={(e) => setCreditorName(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">AMOUNT</label>
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(Number(e.target.value))}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg font-mono font-bold"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">CURRENCY</label>
                  <input
                    type="text"
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg font-mono uppercase"
                    required
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">EXCEPTION REASON / ERROR NARRATIVE</label>
              <textarea
                rows={2}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg"
              />
            </div>

            <div className="bg-sky-50/70 border border-sky-200 rounded-xl p-4 space-y-2">
              <span className="text-[11px] font-bold text-sky-800 uppercase font-mono">PROFILE EVIDENCE GATE</span>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">CORRECTED BENEFICIARY IBAN (LOCAL VALIDATION)</label>
                <input
                  type="text"
                  value={correctedIban}
                  onChange={(e) => setCorrectedIban(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-white border border-sky-300 rounded-lg font-mono font-semibold text-slate-800"
                />
                <p className="text-[10px] text-slate-500 mt-1">Validated locally using ISO 7064 MOD-97 check; only tokenized value is persisted to AI reasoning context.</p>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between">
              <span className="text-xs text-slate-500 flex items-center space-x-1.5">
                <Shield className="w-4 h-4 text-emerald-500" />
                <span>No payment-changing action occurs at intake.</span>
              </span>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2.5 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-bold flex items-center space-x-2 transition-all shadow-sm"
              >
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                <span>Accept into PeX &rarr;</span>
              </button>
            </div>
          </form>

          {/* Stepper Cards */}
          <div className="space-y-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
              <div className="flex items-center space-x-2 text-sky-600 font-bold text-xs font-mono">
                <span className="w-5 h-5 rounded-full bg-sky-100 flex items-center justify-center text-sky-700">1</span>
                <span>VALIDATE</span>
              </div>
              <p className="text-xs text-slate-600">Schema, mandatory fields, and duplicate payment reference checks are computed instantly at the ingestion gateway.</p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
              <div className="flex items-center space-x-2 text-sky-600 font-bold text-xs font-mono">
                <span className="w-5 h-5 rounded-full bg-sky-100 flex items-center justify-center text-sky-700">2</span>
                <span>CLASSIFY</span>
              </div>
              <p className="text-xs text-slate-600">Exception profile, triage queue, SLA due timestamp, and dynamic evidence collection plan are assigned.</p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
              <div className="flex items-center space-x-2 text-sky-600 font-bold text-xs font-mono">
                <span className="w-5 h-5 rounded-full bg-sky-100 flex items-center justify-center text-sky-700">3</span>
                <span>GOVERN</span>
              </div>
              <p className="text-xs text-slate-600">Case enters tokenized investigation before any human repair authorization. External rails remain locked.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
''')

# 2. Worklist/ExceptionWorklist.tsx
with open(os.path.join(comp_dir, "Worklist", "ExceptionWorklist.tsx"), "w", encoding="utf-8") as f:
    f.write('''import React, { useState } from "react";
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
''')
print("Wrote PaymentIntake.tsx and ExceptionWorklist.tsx")
