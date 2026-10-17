import React, { useState, useEffect } from "react";
import { PeXCase, UserPersona, DecisionRecommendation, SystemInfo, CasePage } from "../../types";
import {
  fetchCaseDetail,
  fetchCasesPage,
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
import { StatusBadge } from "../common/StatusBadge";
import { Pagination } from "../common/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../common/States";
import { CaseJourney } from "../common/CaseJourney";
import { SimText } from "../common/SimulatedChip";
import { statusMeta, slaTone, TONE_CLASSES, isBankConfirmed, isHandedToBank } from "../../lib/statusMeta";

interface Props {
  selectedCaseId: string | null;
  onSelectCase: (caseId: string) => void;
  currentPersona: UserPersona | null;
  onRefreshCases: () => void;
  systemInfo?: SystemInfo | null;
}

const PAGE_SIZE = 25;
const APPROVABLE = ["PENDING_APPROVAL", "AWAITING_SECOND_APPROVAL"];

/** Returns a human reason why this persona cannot act on the case, or null if they can. */
function approvalBlockReason(c: PeXCase, p: UserPersona | null): string | null {
  const status = String(c.status);
  if (!p) return "Sign in as a persona to act on this case";
  if (!APPROVABLE.includes(status)) return `No approval is pending (state: ${statusMeta(status).label})`;
  if (c.maker_id && c.maker_id === p.user_id) return "You created this case (maker-checker)";
  const prior = (c.approval_history ?? []).some((a) => a.approver_id === p.user_id && /APPROVE/i.test(a.action));
  if (prior) return "You already approved this case; a different approver must give the second approval";
  if (p.max_approval_amount && c.amount > p.max_approval_amount) return `Amount exceeds your approval limit of ${c.currency} ${p.max_approval_amount.toLocaleString()}`;
  return null;
}

export const ApprovalsWorkspace: React.FC<Props> = ({
  selectedCaseId,
  onSelectCase,
  currentPersona,
  onRefreshCases,
  systemInfo,
}) => {
  const [page, setPage] = useState<CasePage | null>(null);
  const [listOffset, setListOffset] = useState(0);
  const [listFilter, setListFilter] = useState<"pending" | "all">("pending");
  const [listError, setListError] = useState<string | null>(null);
  const [listLoading, setListLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [activeCase, setActiveCase] = useState<PeXCase | null>(null);
  const [recommendation, setRecommendation] = useState<DecisionRecommendation | null>(null);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [comments, setComments] = useState("");

  const currentId = selectedCaseId || page?.items[0]?.case_id;

  const loadList = async () => {
    setListLoading(true);
    try {
      const r = await fetchCasesPage({
        limit: PAGE_SIZE,
        offset: listOffset,
        status: listFilter === "pending" ? "PENDING_APPROVAL" : undefined,
        sort: "sla_due_at",
        order: "asc",
      });
      setPage(r);
      setListError(null);
    } catch (e: any) {
      setListError(e?.message || "Could not load the queue");
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    loadList();
  }, [listOffset, listFilter, tick]);

  const refreshAll = () => {
    setTick((t) => t + 1);
    onRefreshCases();
  };

  useEffect(() => {
    if (currentId) {
      loadCase(currentId);
    }
  }, [currentId]);

  const loadCase = async (caseId: string) => {
    setLoading(true);
    setActionMessage(null);
    setActionError(null);
    setLoadError(null);
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
      setLoadError(err?.message || "Could not load this case");
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
        refreshAll();
        loadCase(activeCase.case_id);
      } else {
        setActionError(typeof res.detail === "string" ? res.detail : res.message || "Approval failed.");
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
        const ref = res.delivery_receipt?.bank_ack_reference || res.bank_ack_reference;
        setActionMessage(
          systemInfo?.operation_mode === "SHADOW"
            ? "Shadow mode: dispatch suppressed. Nothing was sent to the bank."
            : `Handed to bank${ref ? ` (ref ${ref})` : ""}. Awaiting bank confirmation; the case is not settled until the bank confirms.`
        );
        refreshAll();
        loadCase(activeCase.case_id);
      } else {
        setActionError(typeof res.detail === "string" ? res.detail : res.message || "Dispatch failed.");
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
            <p className="text-[11px] text-slate-400">{page ? `${page.total.toLocaleString()} ${listFilter === "pending" ? "awaiting approval" : "cases"}` : "Loading..."}</p>
          </div>
          <button
            onClick={refreshAll}
            className="p-1.5 hover:bg-slate-100 rounded-md text-slate-500 transition-colors"
            title="Refresh queue"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${listLoading ? "animate-spin" : ""}`} />
          </button>
        </div>
        <div className="flex border-b border-slate-100 text-[11px] font-semibold">
          {(["pending", "all"] as const).map((f) => (
            <button
              key={f}
              onClick={() => { setListFilter(f); setListOffset(0); }}
              className={`flex-1 py-2 ${listFilter === f ? "text-sky-700 border-b-2 border-sky-600 bg-sky-50/50" : "text-slate-500 hover:bg-slate-50"}`}
            >
              {f === "pending" ? "Needs approval" : "All cases"}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
          {listError ? (
            <ErrorState message={listError} onRetry={loadList} />
          ) : !page ? (
            <LoadingState />
          ) : page.items.length === 0 ? (
            <EmptyState title="Nothing to approve" hint="No cases are waiting for approval right now." />
          ) : (
            page.items.map((c) => {
              const isSelected = (activeCase?.case_id || currentId) === c.case_id;
              const sla = slaTone(c.sla_due_at);
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
                    <StatusBadge status={c.status} short />
                  </div>
                  <div className="text-xs font-medium text-slate-700 mt-1 truncate">{c.creditor_party?.party_name}</div>
                  <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2">
                    <span className="font-mono font-semibold text-slate-800">
                      {c.currency} {c.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                    <span className={`text-[10px] font-mono ${TONE_CLASSES[sla.tone].text}`}>{sla.label}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
        {page && page.total > PAGE_SIZE && (
          <div className="border-t border-slate-100">
            <Pagination total={page.total} limit={PAGE_SIZE} offset={listOffset} onChange={setListOffset} compact />
          </div>
        )}
      </div>

      {/* Right Detail Pane */}
      <div className="flex-1 bg-slate-50 overflow-y-auto p-8 space-y-6">
        {loading ? (
          <div className="h-full flex items-center justify-center space-x-2 text-slate-500 text-xs font-medium">
            <RefreshCw className="w-5 h-5 animate-spin text-sky-600" />
            <span>Loading case and recommendation...</span>
          </div>
        ) : loadError ? (
          <ErrorState message={loadError} onRetry={() => currentId && loadCase(currentId)} />
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
                  <div className="text-[11px] text-slate-500 flex items-center justify-end space-x-2">
                    <StatusBadge status={activeCase.status} />
                    <strong className={`font-mono ${TONE_CLASSES[slaTone(activeCase.sla_due_at).tone].text}`}>{slaTone(activeCase.sla_due_at).label}</strong>
                  </div>
                </div>
              </div>

              {/* Error banner */}
              <div className="p-3.5 bg-amber-50/80 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start space-x-2.5">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <strong className="font-semibold">Exception detected:</strong> <SimText text={activeCase.reason} />
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
                      <p className="text-[11px] text-sky-200">Advisory only. Deterministic controls validate; a human decides.</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 bg-sky-800/80 px-3 py-1.5 rounded-xl border border-sky-700">
                    <span className="text-xs text-sky-200">Model confidence:</span>
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
                              <span className="text-[10px] font-bold text-red-700 uppercase font-mono block mb-1">ORIGINAL VALUE</span>
                              <div className="font-mono text-xs font-bold text-red-900">{diff.original_value_masked}</div>
                              <span className="text-[10px] text-red-600 block mt-1">Field: {diff.field_path}</span>
                            </div>

                            <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-lg relative">
                              <span className="text-[10px] font-bold text-emerald-700 uppercase font-mono block mb-1 flex items-center justify-between">
                                <span>PROPOSED REPAIR (PENDING APPROVAL)</span>
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
                <label className="block text-xs font-semibold text-slate-700 mb-1">DECISION NOTES (AUDIT TRAIL)</label>
                <input
                  type="text"
                  placeholder="Reason for your decision (recorded in the audit trail)"
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-medium"
                />
              </div>

              <ActionBar
                c={activeCase}
                persona={currentPersona}
                mode={systemInfo?.operation_mode}
                busy={actionLoading}
                onApproval={handleApprovalAction}
                onDispatch={handleExecuteDispatch}
              />
            </div>

            <CaseJourney c={activeCase} />
          </div>
        ) : (
          <EmptyState title="No case selected" hint="Select an exception case from the queue to review it." />
        )}
      </div>
    </div>
  );
};


const ActionBar: React.FC<{
  c: PeXCase;
  persona: UserPersona | null;
  mode?: string;
  busy: boolean;
  onApproval: (a: string) => void;
  onDispatch: () => void;
}> = ({ c, persona, mode, busy, onApproval, onDispatch }) => {
  const status = String(c.status);
  const blocked = approvalBlockReason(c, persona);
  const Reason: React.FC<{ text: string }> = ({ text }) => (
    <div className="w-full text-[11px] text-slate-500 flex items-center space-x-1.5">
      <Lock className="w-3 h-3" />
      <span>{text}</span>
    </div>
  );

  if (status === "APPROVED") {
    const shadow = mode === "SHADOW";
    return (
      <div className="space-y-2">
        <button
          onClick={onDispatch}
          disabled={busy || shadow}
          title={shadow ? "Mode is SHADOW: dispatch suppressed" : undefined}
          className="w-full py-3 bg-sky-700 hover:bg-sky-800 disabled:bg-slate-200 disabled:text-slate-500 text-white rounded-xl font-bold text-xs flex items-center justify-center space-x-2 transition-all"
        >
          {busy ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          <span>Hand to bank adapter</span>
        </button>
        {shadow ? <Reason text="Mode is SHADOW: dispatch suppressed" /> : <Reason text="The bank executes and confirms. PeX does not settle payments." />}
      </div>
    );
  }
  if (isHandedToBank(status)) {
    return (
      <div className="w-full py-3 px-4 bg-blue-50 border border-blue-200 text-blue-800 rounded-xl text-xs text-center">
        <strong>Handed to bank, awaiting confirmation.</strong>
        {c.bank_ack_reference && <span className="font-mono ml-2">ref {c.bank_ack_reference}</span>}
        <div className="text-[11px] text-blue-700 mt-0.5">Do not resend. Only a bank confirmation moves this case forward.</div>
      </div>
    );
  }
  if (isBankConfirmed(status)) {
    return (
      <div className="w-full py-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl font-bold text-xs text-center flex items-center justify-center space-x-2">
        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
        <span>{statusMeta(status).label}</span>
        {c.bank_ack_reference && <span className="font-mono font-normal">ref {c.bank_ack_reference}</span>}
      </div>
    );
  }
  const terminalOther = ["REJECTED", "FAILED", "STATUS_UNKNOWN", "SHADOW_RECORDED", "ESCALATED", "RETURNED_FOR_REWORK"].includes(status);
  if (terminalOther && blocked) {
    return <Reason text={`${statusMeta(status).label}. ${statusMeta(status).description}`} />;
  }
  const dis = busy || !!blocked;
  const base = "px-4 py-2.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed";
  return (
    <div className="w-full space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <button onClick={() => onApproval("APPROVE")} disabled={dis} title={blocked ?? undefined}
            className={`${base} px-5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold flex items-center space-x-1.5`}>
            <CheckCircle2 className="w-4 h-4" />
            <span>Approve</span>
          </button>
          <button onClick={() => onApproval("MODIFY")} disabled={dis} title={blocked ?? undefined}
            className={`${base} bg-slate-100 hover:bg-slate-200 text-slate-700`}>Modify values</button>
          <button onClick={() => onApproval("REJECT")} disabled={dis} title={blocked ?? undefined}
            className={`${base} bg-red-50 hover:bg-red-100 text-red-700`}>Reject</button>
        </div>
        <button onClick={() => onApproval("ESCALATE")} disabled={dis} title={blocked ?? undefined}
          className={`${base} bg-purple-50 hover:bg-purple-100 text-purple-700`}>Escalate to Tier 2</button>
      </div>
      {blocked && <Reason text={blocked} />}
    </div>
  );
};
