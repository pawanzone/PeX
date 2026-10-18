import React, { useState } from "react";
import { Layers, ArrowLeft } from "lucide-react";
import { Banner, CountdownText, DataTable, PageHeader, StatusPill, Tabs } from "../components/v2";
import type { Column } from "../components/v2";
import { useQueryParam } from "../lib/router";
import { useV2 } from "../services/v2";
import { getApprovals } from "../services/v2/approvals";
import type { ApprovalRow } from "../services/v2/approvals";
import { CasePage } from "./case/CasePage";
import { BatchApprovalModal } from "./approvals/BatchApprovalModal";
import { fmtTime, nameOf } from "./case/parts";

const PAGE_SIZE = 25;

/** Checker queue + decision. Design 08 (decision) and 09 (batch approval modal). The selected case lives in `?case=`. */
export const Approvals: React.FC = () => {
  const [caseId, setCase] = useQueryParam("case");
  const [tier, setTier] = useState("all");
  const [page, setPage] = useState(1);
  const [batch, setBatch] = useState(false);
  const q = useV2(() => getApprovals(tier, page, PAGE_SIZE), [tier, page]);
  const total = q.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  if (caseId) {
    return (
      <div>
        <button className="mb-3 inline-flex items-center gap-1.5 text-sm text-pex-primary hover:underline" onClick={() => setCase("")}><ArrowLeft className="w-4 h-4" aria-hidden />Back to approvals queue</button>
        <CasePage id={caseId} context="approvals" onChanged={q.reload} />
      </div>
    );
  }

  const cols: Column<ApprovalRow>[] = [
    { key: "cut", header: "Cutoff", render: (r) => <span className="whitespace-nowrap"><CountdownText iso={r.cutoff?.at} />{r.cutoff?.hhmm && <span className="text-xs text-pex-muted ml-1.5">{r.cutoff.hhmm}</span>}</span> },
    { key: "id", header: "Case", mono: true, render: (r) => <span className="font-medium text-pex-primary">{r.case_id}</span> },
    { key: "ex", header: "Exception", render: (r) => r.exception?.label ?? "" },
    { key: "amt", header: "Amount", mono: true, align: "right", render: (r) => r.amount?.display ?? "" },
    { key: "rail", header: "Rail", render: (r) => r.rail?.label ?? "" },
    { key: "by", header: "Submitted by", render: (r) => <div>{nameOf(r.submitted_by)}<div className="text-xs text-pex-muted">{fmtTime(r.submitted_at)}</div></div> },
    { key: "wait", header: "Waiting", render: (r) => r.waiting_for ?? "" },
    { key: "can", header: "Your decision", render: (r) => r.can_approve === false ? <StatusPill tone="grey" title={r.cannot_approve_reason ?? undefined}>{r.cannot_approve_reason ?? "Cannot approve"}</StatusPill> : <StatusPill tone="blue">Awaiting your approval</StatusPill> },
  ];

  return (
    <div className="grid gap-4">
      <PageHeader title="Approvals" subtitle="Repairs waiting for a decision. Approving hands the repair to the bank system (simulated here); the bank executes and confirms."
        actions={<button className="px-4 py-2 text-sm font-medium rounded-lg bg-pex-primary text-white hover:bg-pex-primary-dark inline-flex items-center gap-2" onClick={() => setBatch(true)}><Layers className="w-4 h-4" aria-hidden />Review low-risk batch</button>} />
      <Tabs label="Approval level" value={tier} onChange={(t) => { setTier(t); setPage(1); }} tabs={[{ id: "all", label: "All" }, { id: "1", label: "Level 1" }, { id: "2", label: "Level 2 (above 250,000)" }]} />
      {q.unavailable && <Banner tone="grey" title="Approvals API not available on this server yet" />}
      <div className="bg-surface-card rounded-card border border-surface-line shadow-card p-2">
        <DataTable columns={cols} rows={q.data?.items ?? []} rowKey={(r) => r.case_id} onRowClick={(r) => setCase(r.case_id)} loading={q.loading} error={q.error} onRetry={q.reload}
          emptyTitle="Nothing is waiting for approval" emptyHint="New submissions from makers appear here." caption="Approvals queue" />
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between px-3 py-2 text-sm text-pex-muted border-t border-surface-line">
            <span>Page {page} of {pages} · {total} cases</span>
            <span className="flex gap-2"><button className="px-3 py-1 rounded border border-surface-line disabled:opacity-50" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button><button className="px-3 py-1 rounded border border-surface-line disabled:opacity-50" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button></span>
          </div>
        )}
      </div>
      <BatchApprovalModal open={batch} onClose={() => setBatch(false)} onDone={q.reload} />
    </div>
  );
};
