import React, { useState } from "react";
import { Send, CornerUpLeft, XCircle } from "lucide-react";
import * as V from "../components/v2";

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <section className="mb-8"><h2 className="text-xs uppercase tracking-wide text-pex-muted font-semibold mb-3">{title}</h2>{children}</section>
);

const inHours = (h: number) => new Date(Date.now() + h * 3600000).toISOString();

export const Gallery: React.FC = () => {
  const [tab, setTab] = useState("ready");
  const [open, setOpen] = useState(false);
  const [chk, setChk] = useState(false);
  const [reason, setReason] = useState(""); const [comment, setComment] = useState("");
  const [sel, setSel] = useState<Set<string>>(new Set(["a"]));
  const [view, setView] = useState("mine");
  const toast = V.useToast();
  const step = (id: string, label: string, state: V.JourneyState, extra: Partial<V.JourneyStep> = {}): V.JourneyStep => ({ id, label, state, ...extra });
  const mk = (variant: V.JourneyVariant): V.JourneyStep[] => {
    const L = V.JOURNEY_STEP_LABELS;
    const upto = variant === "awaiting_approval" ? 5 : variant === "handed_to_bank" ? 7 : 8;
    return L.map((label, i) => {
      if (i === 6) return step("s6", label, "not_required");
      const state: V.JourneyState = i < upto ? "done" : i === upto ? "current" : "pending";
      const s = state === "done" ? (variant === "executed" && i === 8 ? "done" : "done") : state;
      return step("s" + i, label, i === 8 && variant === "executed" ? "done" : s, i === 4 ? { actor: { name: "Elena Marsh", role: "Maker" }, at: "10:42" } : i === 3 ? { actor: { name: "PeX", role: "System", system: true }, at: "10:31" } : {});
    });
  };
  return (
    <div>
      <V.PageHeader title="Component gallery" subtitle="Every v2 component, fed with fake data. Dev reference only; no backend calls." breadcrumbs={[{ label: "Admin", href: "#/admin/integrations" }, { label: "Components" }]} />

      <Section title="Pills, tiles, banners">
        <div className="flex gap-2 flex-wrap mb-4">{(["green", "amber", "red", "blue", "grey", "purple"] as const).map((t) => <V.StatusPill key={t} tone={t}>{t}</V.StatusPill>)}<V.StatusPill status="STATUS_UNKNOWN" /><V.StatusPill status="SETTLED" /></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <V.Tile label="Ready to work" value={14} tone="blue" hint="3 near cutoff" /><V.Tile label="Amount at risk" value="€1.24M" mono tone="amber" /><V.Tile label="Blocked" value={2} tone="red" onClick={() => toast.push("Tile clicked", "blue")} /><V.Tile label="Time to cutoff"><V.CountdownText iso={inHours(1.5)} /></V.Tile>
        </div>
        <div className="grid gap-3">
          <V.Banner tone="blue" title="Info">Neutral guidance banner.</V.Banner><V.Banner tone="amber" title="Waiting">Waiting on bank confirmation.</V.Banner>
          <V.Banner tone="red" title="Blocked">STP is blocked: conflicting evidence.</V.Banner><V.Banner tone="green" title="Passed">All checks passed.</V.Banner>
        </div>
      </Section>

      <Section title="Tabs, filters, saved views">
        <V.Tabs value={tab} onChange={setTab} tabs={[{ id: "ready", label: "Ready to work", count: 12 }, { id: "returned", label: "Returned to me", count: 2 }, { id: "wait", label: "Waiting for info", count: 5 }, { id: "pend", label: "Pending approval", count: 7 }, { id: "done", label: "Done today", count: 31 }]} />
        <V.FilterBar search={{ value: "", onChange: () => {}, placeholder: "Search case, party or reference" }} right={<V.SavedViewsMenu views={[{ id: "mine", label: "My cases" }, { id: "cut", label: "Near cutoff" }]} activeId={view} onSelect={setView} onSave={() => toast.push("Saved")} />}>
          <V.FilterSelect label="Rail" value="all" onChange={() => {}} options={[{ value: "all", label: "All" }, { value: "sepa", label: "SEPA" }]} />
          <V.FilterSelect label="Priority" value="all" onChange={() => {}} options={[{ value: "all", label: "All" }]} />
        </V.FilterBar>
      </Section>

      <Section title="DataTable (selectable) and EvidenceTable">
        <div className="bg-white rounded-card border border-surface-line p-2 mb-4">
          <V.DataTable selectable selected={sel} onToggle={(k) => setSel((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n; })}
            rows={[{ id: "a", amt: "12,400.00", p: "Acme GmbH" }, { id: "b", amt: "980.50", p: "Nordic Parts AB" }]} rowKey={(r) => r.id} onRowClick={() => {}}
            columns={[{ key: "id", header: "Case", render: (r) => r.id, mono: true }, { key: "p", header: "Party", render: (r) => r.p }, { key: "amt", header: "Amount (EUR)", render: (r) => r.amt, mono: true, align: "right" }]} />
        </div>
        <div className="bg-white rounded-card border border-surface-line p-2"><V.EvidenceTable rows={[{ source: "Beneficiary directory", finding: "IBAN valid for Acme GmbH", confidence: "high", status: "match" }, { source: "Prior payments", finding: "Different account used in 2 of 9 payments", confidence: "medium", status: "mismatch" }, { source: "Invoice", finding: "Not attached", status: "missing" }]} /></div>
        <div className="mt-4 grid grid-cols-3 gap-4"><V.DataTable rows={[]} rowKey={() => ""} columns={[]} emptyTitle="Nothing here" emptyHint="Empty state" /><V.Loading /><V.ErrorState message="Example error" onRetry={() => {}} /></div>
      </Section>

      <Section title="FieldDiff, SourceCard, KeyValueList, Avatar">
        <div className="bg-white rounded-card border border-surface-line p-4 mb-4"><V.FieldDiff rows={[{ field: "Creditor IBAN", before: "DE89 3704 0044 0532 0130 00", after: "DE89 3704 0044 0532 0130 01", note: "Checksum corrected" }, { field: "Creditor name", before: "", after: "Acme GmbH" }]} /></div>
        <div className="grid md:grid-cols-3 gap-3 mb-4">
          <V.SourceCard title="Core banking" status="match" lines={[{ label: "Account", value: "DE89…0001", mono: true }, { label: "Holder", value: "Acme GmbH" }]} />
          <V.SourceCard title="Invoice" status="mismatch" lines={[{ label: "Account", value: "DE89…0002", mono: true }]} footer="Differs from core banking" />
          <V.SourceCard title="Verification of Payee" status="missing" lines={[{ label: "Result", value: "No response" }]} />
        </div>
        <V.KeyValueList items={[{ label: "Debtor", value: "Globex SA" }, { label: "Rail", value: "SEPA Credit Transfer" }, { label: "End-to-end id", value: "E2E-0001", mono: true }]} cols={3} />
        <div className="mt-4 flex gap-6"><V.Avatar name="Elena Marsh" role="Maker" /><V.Avatar name="PeX" role="System" system size="sm" /></div>
      </Section>

      <Section title="Case header, journey (variants A / B / C)">
        <V.CaseHeader id="PEX-INV-0001" chips={[{ label: "Validated", tone: "blue" }, { label: "SEPA", tone: "grey" }]} title="Invalid IBAN checksum" amount="12,400.00" currency="EUR" cutoff={inHours(2.2)} meta={[{ label: "Debtor", value: "Globex SA" }, { label: "Creditor", value: "Acme GmbH" }, { label: "Rail", value: "SEPA CT" }, { label: "Assigned", value: "Elena Marsh" }]} />
        <div className="grid md:grid-cols-3 gap-4 mt-4">
          {(["awaiting_approval", "handed_to_bank", "executed"] as const).map((v) => (
            <V.CaseJourney key={v} variant={v} steps={mk(v)} auditCount={v === "executed" ? 14 : 9} onViewAudit={() => {}}
              nextAction={<V.NextActionCard tone={V.VARIANT_TONE[v]} title={v === "awaiting_approval" ? "Approval level 1 needed" : v === "handed_to_bank" ? "Waiting for bank confirmation" : "Executed by bank · ref BNK-88123"} detail={v === "handed_to_bank" ? "Do not resend." : undefined} owner={v === "awaiting_approval" ? "Operations Approver" : "Bank"} />} />
          ))}
        </div>
      </Section>

      <Section title="Forms, modal, action bar">
        <div className="bg-white rounded-card border border-surface-line p-4 max-w-xl">
          <V.ConfirmCheckbox checked={chk} onChange={setChk}>I have reviewed the evidence and the change.</V.ConfirmCheckbox>
          <div className="mt-4"><V.ReasonCommentFields required reasons={[{ value: "evidence", label: "Evidence insufficient" }, { value: "policy", label: "Outside policy" }]} reason={reason} onReason={setReason} comment={comment} onComment={setComment} /></div>
          <button onClick={() => setOpen(true)} className="mt-4 px-3 py-2 text-sm rounded-lg border border-surface-line hover:bg-slate-50">Open modal</button>
        </div>
        <V.Modal open={open} title="Approve 12 for bank handoff" onClose={() => setOpen(false)} footer={<><button onClick={() => setOpen(false)} className="px-4 py-2 text-sm rounded-lg border border-surface-line bg-white">Cancel</button><button onClick={() => { setOpen(false); toast.push("Approved for bank handoff"); }} className="px-4 py-2 text-sm rounded-lg bg-pex-primary text-white">Approve</button></>}>
          <p className="text-sm text-pex-muted">Modal body. Escape closes; Tab is trapped; focus returns to the trigger.</p>
        </V.Modal>
        <V.ActionBar summary="Maker: Elena Marsh" actions={[{ id: "a", label: "Submit for approval", kind: "primary", icon: Send, onClick: () => toast.push("Submitted") }, { id: "b", label: "Request information", icon: CornerUpLeft, onClick: () => {} }, { id: "c", label: "Escalate", kind: "danger", icon: XCircle, onClick: () => {} }, { id: "d", label: "Prepare repair", disabled: true, disabledReason: "locked while evidence conflicts", onClick: () => {} }]} />
      </Section>
    </div>
  );
};
