import os

path = r"C:\Users\pawan\.gemini\antigravity\scratch\pex_platform\frontend\src\components\Approvals\ApprovalsWorkspace.tsx"
with open(path, "w", encoding="utf-8") as f:
    f.write('''import React, { useState, useEffect } from "react";
import { PeXCase, UserPersona, DecisionRecommendation } from "../../types";
import {
  fetchCaseDetail,
  runInvestigation,
  submitApproval,
  executeAction,
} from "../../services/api";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Zap,
  Sparkles,
  Lock,
  RefreshCw,
  FileCheck2,
  Scale,
  Send,
} from "lucide-react";

interface Props {
  cases: PeXCase[];
  selectedCaseId: string | null;
  onSelectCase: (caseId: string) => void;
  currentPersona: UserPersona | null;
  onRefreshCases: () => void;
}

export const ApprovalsWorkspace: React.FC<Props> = ({
  cases,
  selectedCaseId,
  onSelectCase,
  currentPersona,
  onRefreshCases,
}) => {
  const [activeCase, setActiveCase] = useState<PeXCase | null>(null);
  const [recommendation, setRecommendation] = useState<DecisionRecommendation | null>(null);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [comments, setComments] = useState("Validated against beneficiary standing instructions and MOD-97 check digits.");

  const currentId = selectedCaseId || cases[0]?.case_id;

  useEffect(() => {
    if (currentId) {
      loadCase(currentId);
    }
  }, [currentId]);

  const loadCase = async (caseId: string) => {
    setLoading(true);
    setActionMessage(null);
    setActionError(null);
    try {
      const data = await fetchCaseDetail(caseId);
      setActiveCase(data.case);
      setRecommendation(data.recommendation);
      setApprovals(data.approvals);
      
      // If no recommendation yet, automatically trigger investigation
      if (!data.recommendation) {
        const inv = await runInvestigation(caseId);
        setRecommendation(inv.recommendation);
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprovalAction = async (actionType: string) => {
    if (!activeCase) return;
    setActionLoading(true);
    setActionMessage(null);
    setActionError(null);
    try {
      const token = currentPersona ? currentPersona.user_id : undefined;
      const res = await submitApproval(activeCase.case_id, actionType, comments, token);
      if (res.success) {
        setActionMessage(res.message);
        onRefreshCases();
        loadCase(activeCase.case_id);
      } else {
        setActionError(res.detail || res.message || "Approval failed.");
      }
    } catch (err: any) {
      setActionError(err.message || "Server error during approval submission.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleExecuteDispatch = async () => {
    if (!activeCase) return;
    setActionLoading(true);
    setActionMessage(null);
    setActionError(null);
    try {
      const res = await executeAction(activeCase.case_id);
      if (res.success) {
        setActionMessage(`Dispatched & Settled! Delivery Receipt: ${res.delivery_receipt?.bank_ack_reference}`);
        onRefreshCases();
        loadCase(activeCase.case_id);
      } else {
        setActionError(res.detail || res.message || "Dispatch execution failed.");
      }
    } catch (err: any) {
      setActionError(err.message || "Server error during action execution.");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="h-[calc(100vh-3.5rem)] flex overflow-hidden">
      {/* Left Master List */}
      <div className="w-80 border-r border-slate-200 bg-white flex flex-col shrink-0">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">APPROVALS QUEUE</h2>
            <p className="text-[11px] text-slate-400">{cases.length} exceptions under governance</p>
          </div>
          <button
            onClick={() => onRefreshCases()}
            className="p-1.5 hover:bg-slate-100 rounded-md text-slate-500 transition-colors"
            title="Refresh queue"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
          {cases.map((c) => {
            const isSelected = (activeCase?.case_id || currentId) === c.case_id;
            return (
              <div
                key={c.case_id}
                onClick={() => {
                  onSelectCase(c.case_id);
                  loadCase(c.case_id);
                }}
                className={`p-3.5 cursor-pointer transition-all ${
                  isSelected ? "bg-sky-50/80 border-l-4 border-sky-600" : "hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-slate-900">{c.case_id}</span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                    c.status === "SETTLED" ? "bg-emerald-100 text-emerald-700" :
                    c.status === "APPROVED" ? "bg-blue-100 text-blue-700" :
                    c.status === "AWAITING_SECOND_APPROVAL" ? "bg-purple-100 text-purple-700" : "bg-amber-100 text-amber-700"
                  }`}>
                    {c.status}
                  </span>
                </div>
                <div className="text-xs font-medium text-slate-700 mt-1 truncate">{c.creditor_party?.party_name}</div>
                <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2">
                  <span className="font-mono font-semibold text-slate-800">
                    {c.currency} {c.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">{c.queue}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Right Detail Pane */}
      <div className="flex-1 bg-slate-50 overflow-y-auto p-8 space-y-6">
        {loading ? (
          <div className="h-full flex items-center justify-center space-x-2 text-slate-500 text-xs font-medium">
            <RefreshCw className="w-5 h-5 animate-spin text-sky-600" />
            <span>Assembling Tokenized Context &amp; Running AI Reasoner...</span>
          </div>
        ) : activeCase ? (
          <div className="max-w-5xl mx-auto space-y-6">
            {/* Header Card */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2.5">
                    <h1 className="text-xl font-bold text-slate-900 font-mono tracking-tight">{activeCase.case_id}</h1>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-sky-50 text-sky-700 border border-sky-200">
                      {activeCase.profile}
                    </span>
                    {activeCase.dual_auth_required && (
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-purple-50 text-purple-700 border border-purple-200 flex items-center space-x-1">
                        <Scale className="w-3 h-3" />
                        <span>Dual Authorization Required</span>
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500">
                    UETR: <span className="font-mono text-slate-700">{activeCase.uetr}</span> | Rail: <span className="font-semibold text-slate-700">{activeCase.payment_rail}</span>
                  </p>
                </div>

                <div className="text-right">
                  <div className="text-2xl font-bold font-mono text-slate-900">
                    {activeCase.currency} {activeCase.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    SLA Due in: <strong className="text-amber-600 font-mono">1h 45m</strong>
                  </div>
                </div>
              </div>

              {/* Error banner */}
              <div className="p-3.5 bg-amber-50/80 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start space-x-2.5">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <strong className="font-semibold">Exception Detected:</strong> {activeCase.reason}
                </div>
              </div>
            </div>

            {/* AI Recommendation & Field Diff */}
            {recommendation && (
              <div className="bg-white rounded-2xl border border-sky-200 shadow-sm overflow-hidden space-y-0">
                <div className="bg-sky-900 text-white px-6 py-4 flex items-center justify-between">
                  <div className="flex items-center space-x-2.5">
                    <Sparkles className="w-5 h-5 text-sky-400" />
                    <div>
                      <h3 className="text-sm font-bold tracking-tight">Governed AI Recommendation: {recommendation.action_type}</h3>
                      <p className="text-[11px] text-sky-200">Grounded in ISO 20022 canonical rules &amp; beneficiary master directory</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 bg-sky-800/80 px-3 py-1.5 rounded-xl border border-sky-700">
                    <span className="text-xs text-sky-200">AI Confidence:</span>
                    <span className="text-sm font-bold font-mono text-emerald-400">
                      {(recommendation.confidence_score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                <div className="p-6 space-y-6">
                  {/* Rationale */}
                  <div className="space-y-1.5">
                    <h4 className="text-xs font-bold text-slate-700 uppercase font-mono tracking-wider">AI Reasoning &amp; Investigation Rationale</h4>
                    <p className="text-xs text-slate-700 bg-slate-50 p-3.5 rounded-xl border border-slate-200 leading-relaxed">
                      {recommendation.rationale}
                    </p>
                  </div>

                  {/* Field Diff if changes proposed */}
                  {recommendation.proposed_changes.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-slate-700 uppercase font-mono tracking-wider">Proposed Value Field Diff (Maker Review)</h4>
                      <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-200">
                        {recommendation.proposed_changes.map((diff, idx) => (
                          <div key={idx} className="p-4 bg-white grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
                            <div className="p-3 bg-red-50/70 border border-red-200 rounded-lg">
                              <span className="text-[10px] font-bold text-red-700 uppercase font-mono block mb-1">ORIGINAL VALUE (CORRUPTED)</span>
                              <div className="font-mono text-xs font-bold text-red-900">{diff.original_value_masked}</div>
                              <span className="text-[10px] text-red-600 block mt-1">Field: {diff.field_path}</span>
                            </div>

                            <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-lg relative">
                              <span className="text-[10px] font-bold text-emerald-700 uppercase font-mono block mb-1 flex items-center justify-between">
                                <span>PROPOSED REPAIR (CORRECTED)</span>
                                <span className="text-[10px] bg-emerald-200 text-emerald-800 px-1.5 py-0.5 rounded font-mono">MOD-97 PASS</span>
                              </span>
                              <div className="font-mono text-xs font-bold text-emerald-900">{diff.proposed_value_masked}</div>
                              <span className="text-[10px] text-emerald-700 block mt-1">{diff.justification}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Corroborating Evidence Citations */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-slate-700 uppercase font-mono tracking-wider">Corroborating Evidence Citations</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {recommendation.corroborating_evidence.map((ev, i) => (
                        <div key={i} className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
                          <div className="flex items-center space-x-1.5 text-sky-700 font-semibold text-[11px]">
                            <FileCheck2 className="w-3.5 h-3.5" />
                            <span>{ev.evidence_type}</span>
                          </div>
                          <p className="text-slate-600 text-[11px]">{ev.citation}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Zero-Trust Privacy Tag Banner */}
            <div className="bg-slate-100 border border-slate-200 rounded-xl p-3.5 flex items-center justify-between text-xs text-slate-600">
              <div className="flex items-center space-x-2">
                <Lock className="w-4 h-4 text-slate-500" />
                <span>
                  <strong>PII Isolation Boundary:</strong> Debtor Token <code className="text-sky-700">{activeCase.debtor_party?.token_ref || "TOK-PARTY-..."}</code> | Creditor Token <code className="text-sky-700">{activeCase.creditor_party?.token_ref || "TOK-PARTY-..."}</code>
                </span>
              </div>
              <span className="font-mono text-[10px] bg-slate-200 px-2 py-0.5 rounded text-slate-700">VAULT ISOLATED</span>
            </div>

            {/* Action Feedback Messages */}
            {actionMessage && (
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 font-semibold flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{actionMessage}</span>
              </div>
            )}
            {actionError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 font-semibold flex items-center space-x-2">
                <XCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            {/* Role-Gated Action Bar */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-sm font-bold text-slate-900">Institutional Governance &amp; Decision Bar</h3>
                <div className="text-xs text-slate-500">
                  Acting Persona: <strong className="text-slate-800">{currentPersona?.name}</strong> ({currentPersona?.role})
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">DECISION JUSTIFICATION / AUDIT NOTES</label>
                <input
                  type="text"
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-medium"
                />
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                {activeCase.status === "APPROVED" ? (
                  <button
                    onClick={handleExecuteDispatch}
                    disabled={actionLoading}
                    className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs flex items-center justify-center space-x-2 transition-all shadow-md shadow-emerald-600/20"
                  >
                    {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    <span>Execute Governed Dispatch &amp; Settle Against Banking Rails &rarr;</span>
                  </button>
                ) : activeCase.status === "SETTLED" ? (
                  <div className="w-full py-3 bg-slate-100 border border-slate-200 text-slate-600 rounded-xl font-bold text-xs text-center flex items-center justify-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Case Fully Settled &amp; Reconciled in External Ledger</span>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleApprovalAction("APPROVE")}
                        disabled={actionLoading}
                        className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold flex items-center space-x-1.5 transition-all shadow-sm"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Approve Repair</span>
                      </button>

                      <button
                        onClick={() => handleApprovalAction("MODIFY")}
                        disabled={actionLoading}
                        className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-all"
                      >
                        Modify Values
                      </button>

                      <button
                        onClick={() => handleApprovalAction("REJECT")}
                        disabled={actionLoading}
                        className="px-4 py-2.5 bg-red-50 hover:bg-red-100 text-red-700 rounded-lg text-xs font-semibold transition-all"
                      >
                        Reject
                      </button>
                    </div>

                    <button
                      onClick={() => handleApprovalAction("ESCALATE")}
                      disabled={actionLoading}
                      className="px-4 py-2.5 bg-purple-50 hover:bg-purple-100 text-purple-700 rounded-lg text-xs font-semibold transition-all"
                    >
                      Escalate to Tier 2
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center text-xs text-slate-400 py-12">Select an exception case from the queue to investigate.</div>
        )}
      </div>
    </div>
  );
};
''')
print("Wrote ApprovalsWorkspace.tsx")
