import React, { useEffect, useRef, useState } from "react";
import { Info, Search, Phone, FileText, Users, Lock, Hourglass, CheckCircle2, XCircle, RefreshCw, ChevronRight, Paperclip, Send, Save } from "lucide-react";
import { Banner, StatusPill, KeyValueList, Avatar, cn } from "../../components/v2";
import { Section, ValueBoxes, EvidenceGrid, fmtTime, fmtDateTime, HighlightedValue } from "./parts";
import type { Run } from "./forms";
import type { CasePage, ConflictDto, NeededDto, RequestInfoDto, StatusUnknownDto } from "../../services/v2/case";
import { requestInformation, postCaseAction, disambiguateCase } from "../../services/v2/case";

const field = "py-2 px-2.5 text-sm rounded-lg border border-surface-line bg-white text-pex-ink w-full";
const primaryBtn = "px-4 py-2 text-sm font-medium rounded-lg bg-pex-primary text-white hover:bg-pex-primary-dark disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2";
const plainBtn = "px-4 py-2 text-sm font-medium rounded-lg bg-white border border-surface-line text-pex-primary hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2";

// ------------------------------------------------------------ shared blocks
export const DecisionBrief: React.FC<{ brief: NonNullable<CasePage["decision_brief"]> }> = ({ brief }) => {
  const cols: Array<[string, string | undefined]> = [["What happened", brief.what_happened], ["Proposed change", brief.proposed_change], ["Evidence", brief.evidence], ["Controls", brief.controls], ["Next", brief.next]];
  return (
    <Section title="Decision brief">
      <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {cols.map(([k, v]) => <div key={k} className="lg:border-l lg:first:border-l-0 lg:pl-4 lg:first:pl-0 border-surface-line"><dt className="text-xs text-pex-muted">{k}</dt><dd className="text-sm font-medium text-pex-ink mt-1">{v || "—"}</dd></div>)}
      </dl>
    </Section>
  );
};

export const ChangeBlock: React.FC<{ page: CasePage; mode: "decision" | "approval" }> = ({ page, mode }) => {
  const c = page.change_summary;
  if (!c) return null;
  const sod = page.sod;
  return (
    <>
      <Section title={mode === "approval" ? "Change summary" : "Proposed change"} hint={mode === "decision" ? c.what_changes : undefined}>
        {mode === "approval" && c.what_changes && <div className="mb-3 text-sm"><span className="text-pex-muted mr-3">What changes</span><span className="font-medium">{c.what_changes}</span></div>}
        <ValueBoxes original={c.original} proposed={c.proposed} compact={mode === "approval"} />
        {mode === "decision" && c.source && <p className="text-sm text-pex-muted mt-3"><span className="font-medium text-pex-ink">Source:</span> {c.source}</p>}
        {mode === "approval" && (
          <dl className="mt-4 grid gap-y-2 text-sm">
            {([["Source", c.source], ["Risk", c.risk], ["Policy basis", c.policy_basis], ["If you approve", c.if_you_approve]] as Array<[string, string | undefined]>).filter(([, v]) => v).map(([k, v]) => (
              <div key={k} className="grid grid-cols-[8rem_1fr] gap-3"><dt className="text-pex-muted">{k}</dt><dd className="text-pex-ink">{v}</dd></div>
            ))}
          </dl>
        )}
      </Section>
      {sod && sod.status && sod.status !== "n/a" && (
        <Banner tone={sod.status === "passed" ? "green" : "red"} title={sod.status === "passed" ? "Separation of duties passed" : "Separation of duties failed"}>{sod.text}</Banner>
      )}
    </>
  );
};

export const HandoverNote: React.FC<{ h: NonNullable<CasePage["handover"]> }> = ({ h }) => (
  <Section title="Maker's handover note">
    <div className="flex gap-4 items-start flex-wrap">
      <div className="flex items-center gap-3 min-w-[12rem]"><Avatar bare name={h.by?.name} /><div><div className="text-sm font-semibold">{h.by?.name}</div><div className="text-xs text-pex-muted">{h.by?.role ?? "Maker"}</div></div></div>
      <div className="flex-1 min-w-[14rem] sm:border-l sm:pl-4 border-surface-line">
        <p className="text-sm text-pex-ink">{h.note}</p>
        {h.attachment?.name && <span className="mt-2 inline-flex items-center gap-1.5 text-sm px-2.5 py-1 rounded-lg border border-surface-line bg-slate-50"><Paperclip className="w-3.5 h-3.5" aria-hidden />{h.attachment.name}</span>}
      </div>
      <div className="text-xs text-pex-muted text-right">{fmtTime(h.at)}<br />Today</div>
    </div>
  </Section>
);

export const RecommendationBlock: React.FC<{ page: CasePage }> = ({ page }) => {
  const rec = page.recommendation;
  if (!rec) return null;
  return (
    <Section title="PeX recommendation and reasoning" right={rec.confidence_label ? <span className="text-xs text-pex-muted">{rec.confidence_label}</span> : undefined}>
      <div className="text-sm grid gap-2">
        {rec.summary && <p>{rec.summary}</p>}
        {!!rec.reasoning?.length && <ul className="list-disc pl-5 text-pex-muted">{rec.reasoning.map((r, i) => <li key={i}>{r}</li>)}</ul>}
        <p className="text-xs text-pex-muted">Advisory only. Controls decide, humans authorise, the bank executes.</p>
      </div>
    </Section>
  );
};

export const EvidenceBlock: React.FC<{ page: CasePage; bare?: boolean }> = ({ page, bare }) => {
  const rows = page.evidence_table ?? [];
  const sum = page.evidence_summary;
  const pill = sum?.label ? <StatusPill tone={sum.status === "conflict" ? "red" : sum.status === "missing" ? "amber" : "green"}>{sum.label}</StatusPill> : undefined;
  if (bare) return <div>{pill && <div className="mb-2">{pill}</div>}<EvidenceGrid caseId={page.case_id} rows={rows} /></div>;
  return (
    <Section title="Evidence" right={pill}>
      <EvidenceGrid caseId={page.case_id} rows={rows} />
    </Section>
  );
};

// ------------------------------------------------------------ missing information (design 05)
const NEED_TONE: Record<string, { tone: "amber" | "grey" | "green"; label: string }> = { missing: { tone: "amber", label: "Missing" }, not_required: { tone: "grey", label: "Not required" }, found: { tone: "green", label: "Found" } };

export const NeededBlock: React.FC<{ needed: NeededDto }> = ({ needed }) => (
  <Section title="What is needed">
    <div className="overflow-x-auto rounded-lg border border-surface-line">
      <table className="w-full text-sm">
        <caption className="sr-only">Information needed to proceed</caption>
        <thead><tr className="text-left text-xs text-pex-muted bg-slate-50 border-b border-surface-line">{["Item", "Why it is needed", "Where it can come from", "Status"].map((h) => <th key={h} scope="col" className="py-2 px-3 font-medium">{h}</th>)}</tr></thead>
        <tbody>
          {(needed.rows ?? []).map((r, i) => {
            const t = NEED_TONE[r.status ?? "missing"] ?? NEED_TONE.missing;
            return (
              <tr key={i} className="border-b border-surface-line last:border-0">
                <td className="py-2.5 px-3">{r.item}</td><td className="py-2.5 px-3">{r.why ?? r.why_needed ?? r.note ?? ""}</td><td className="py-2.5 px-3">{r.source ?? r.where ?? ""}</td>
                <td className="py-2.5 px-3"><StatusPill tone={t.tone}>{t.label}</StatusPill></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
    {!!needed.searched?.length && (
      <div className="grid gap-2 sm:grid-cols-2 mt-3">
        {needed.searched.map((s, i) => <div key={i} className="flex items-center gap-2 rounded-lg bg-slate-50 border border-surface-line px-3 py-2 text-sm"><Search className="w-4 h-4 text-slate-500 shrink-0" aria-hidden />Searched: {s.source} · {s.result}</div>)}
      </div>
    )}
  </Section>
);

export type SendHandle = { send: () => void };
export const RequestInfoForm: React.FC<{ caseId: string; info?: RequestInfoDto | null; run: Run; handle?: React.MutableRefObject<SendHandle | null>; onDone?: () => void; embedded?: boolean }> = ({ caseId, info, run, handle, onDone, embedded }) => {
  const [to, setTo] = useState(info?.to?.party ?? "");
  const [method, setMethod] = useState(info?.method ?? info?.methods?.[0] ?? "Email");
  const [message, setMessage] = useState(info?.message ?? "");
  const [busy, setBusy] = useState(false);
  const seeded = useRef(false);
  useEffect(() => {
    if (seeded.current || !info) return;
    seeded.current = true;
    setTo(info.to?.party ?? ""); setMethod(info.method ?? info.methods?.[0] ?? "Email"); setMessage(info.message ?? "");
  }, [info]);
  const valid = to.trim() !== "" && message.trim() !== "";
  const send = async (draft: boolean) => {
    if (!valid) return;
    setBusy(true);
    const r = await run(() => requestInformation(caseId, { to: to.trim(), method, message: message.trim(), draft, reply_due: info?.reply_due ?? null, escalate_at: info?.escalate_at ?? null }), draft ? "Draft saved" : "Request sent (simulated)");
    setBusy(false);
    if (r && !draft) onDone?.();
  };
  const sendRef = useRef(send); sendRef.current = send;
  useEffect(() => { if (handle) handle.current = { send: () => void sendRef.current(false) }; return () => { if (handle) handle.current = null; }; }, [handle]);
  const methods = info?.methods?.length ? info.methods : ["Email", "Phone", "Portal"];
  const state = info?.state;
  const form = (
    <div className="grid gap-3">
      {state === "sent" && <Banner tone="amber" title="Request sent">Waiting for a reply{info?.sent_at ? ` · sent ${fmtTime(info.sent_at)}` : ""}.</Banner>}
      {state === "overdue" && <Banner tone="red" title="Reply overdue">Escalate or follow up.</Banner>}
      <label className="grid gap-1 sm:grid-cols-[6rem_1fr] sm:items-center text-sm text-pex-muted">To
        <input value={to} onChange={(e) => setTo(e.target.value)} className={field} aria-describedby="ri-contact" />
      </label>
      {info?.to?.contact && <p id="ri-contact" className="text-xs text-pex-muted sm:pl-[6.5rem]">{info.to.role ? `${info.to.role}: ` : ""}{info.to.contact}</p>}
      <label className="grid gap-1 sm:grid-cols-[6rem_1fr] sm:items-center text-sm text-pex-muted">Method
        <select value={method} onChange={(e) => setMethod(e.target.value)} className={field}>{methods.map((m) => <option key={m}>{m}</option>)}</select>
      </label>
      <label className="grid gap-1 sm:grid-cols-[6rem_1fr] text-sm text-pex-muted">Message
        <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} className={field} />
      </label>
      <div className="sm:pl-[6.5rem] flex gap-2 flex-wrap">
        <button className={primaryBtn} disabled={!valid || busy} onClick={() => void send(false)}><Send className="w-4 h-4" aria-hidden />Send request</button>
        <button className={plainBtn} disabled={!valid || busy} onClick={() => void send(true)}><Save className="w-4 h-4" aria-hidden />Save draft</button>
      </div>
      {(info?.reply_due || info?.escalate_at) && <p className="text-sm text-pex-muted sm:pl-[6.5rem] flex items-center gap-1.5"><Hourglass className="w-4 h-4" aria-hidden />Reply due by {fmtTime(info.reply_due)} · If not received, escalate at {fmtTime(info.escalate_at)}</p>}
      {info?.draft_saved_at && <p className="text-xs text-pex-muted sm:pl-[6.5rem]">Draft saved {fmtTime(info.draft_saved_at)}</p>}
    </div>
  );
  return embedded ? form : <Section title="Request information">{form}</Section>;
};

export const ReassessBlock: React.FC<{ caseId: string; run: Run; enabled: boolean; reason?: string | null }> = ({ caseId, run, enabled, reason }) => {
  const [busy, setBusy] = useState(false);
  return (
    <Section title="Reassess case" hint="PeX will re-run evidence and validation when information is received."
      right={<div className="text-right"><button className={plainBtn} disabled={!enabled || busy} onClick={async () => { setBusy(true); await run(() => postCaseAction(caseId, "reassess", { note: null }), "Reassessed"); setBusy(false); }}><RefreshCw className="w-4 h-4" aria-hidden />Reassess case</button>
        {!enabled && reason && <div className="text-xs text-pex-muted mt-1">{reason}</div>}</div>}>
      <span className="sr-only">Reassess</span>
    </Section>
  );
};

// ------------------------------------------------------------ conflict (design 06)
const STEP_META: Record<string, { icon: React.ElementType; title: string; detail?: string }> = {
  start_verification: { icon: Phone, title: "Verify with beneficiary by call-back", detail: "Use the number on the client master record" },
  request_information: { icon: FileText, title: "Request corrected invoice or instruction" },
  escalate: { icon: Users, title: "Escalate to Senior Analyst" },
  prepare_repair: { icon: Lock, title: "Prepare repair", detail: "Available after the conflict is resolved" },
};

export const ConflictBlock: React.FC<{ c: ConflictDto; caseId: string; onAction: (key: string) => void; run: Run; canWork: boolean }> = ({ c, caseId, onAction, run, canWork }) => {
  const sources = c.sources ?? [];
  const ref = sources.find((s) => s.relation === "agrees")?.value;
  const [pick, setPick] = useState("");
  const [why, setWhy] = useState("");
  const cands = c.disambiguation?.candidates ?? [];
  return (
    <>
      <Section title={c.field ?? "Conflicting field"}>
        <div className="grid gap-3 md:grid-cols-3">
          {sources.map((s, i) => {
            const differs = s.relation === "differs";
            return (
              <div key={i} className={cn("rounded-xl border p-3", differs ? "border-red-200 bg-red-50" : "border-green-200 bg-green-50")}>
                <div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold">{s.name}</span><StatusPill tone={differs ? "red" : "green"}>{s.tag ?? (differs ? "Differs" : "Agree")}</StatusPill></div>
                <div className="pex-mono text-base mt-2 break-all"><HighlightedValue value={s.value} other={differs ? ref : undefined} tone="red" /></div>
                <dl className="mt-3 pt-2 border-t border-current/10 grid grid-cols-2 gap-2 text-xs"><div><dt className="text-pex-muted">Authority</dt><dd className="text-sm text-pex-ink">{s.authority}</dd></div><div><dt className="text-pex-muted">Time</dt><dd className="text-sm text-pex-ink">{fmtTime(s.checked_at ?? s.received_at ?? s.changed_at)}</dd></div></dl>
              </div>
            );
          })}
        </div>
        {c.note && <p className="mt-3 text-sm text-pex-muted flex items-center gap-2 rounded-lg bg-slate-50 border border-surface-line px-3 py-2"><Info className="w-4 h-4 shrink-0" aria-hidden />{c.note}</p>}
      </Section>
      {!!c.why_blocked?.length && (
        <Section title="Why STP is blocked" className="border-red-200 bg-red-50/60">
          <ol className="grid gap-2">{c.why_blocked.map((w, i) => <li key={i} className="flex items-center gap-3 text-sm"><span className="w-6 h-6 rounded-full bg-pex-block text-white text-xs font-semibold flex items-center justify-center shrink-0">{i + 1}</span>{w}</li>)}</ol>
        </Section>
      )}
      <Section title="Next steps">
        <ul className="divide-y divide-surface-line">
          {(c.next_steps ?? []).map((st) => {
            const m = STEP_META[st.key] ?? { icon: ChevronRight, title: st.label };
            const Icon = m.icon;
            const disabled = st.enabled === false || !canWork;
            return (
              <li key={st.key} className="py-3 flex items-center gap-3">
                <Icon className="w-5 h-5 text-slate-500 shrink-0" aria-hidden />
                <div className="flex-1 min-w-0"><div className={cn("text-sm font-semibold", disabled && "text-slate-500")}>{m.title}</div><div className="text-xs text-pex-muted">{st.detail ?? (disabled ? st.disabled_reason : undefined) ?? m.detail}</div></div>
                <button className={plainBtn} disabled={disabled} title={disabled ? st.disabled_reason ?? undefined : undefined} onClick={() => onAction(st.key)}>{disabled && <Lock className="w-3.5 h-3.5" aria-hidden />}{st.label}</button>
              </li>
            );
          })}
        </ul>
      </Section>
      {cands.length > 0 && canWork && (
        <Section title="Disambiguation" hint="Choose the hypothesis you have verified and record why.">
          <div className="grid gap-2" role="radiogroup" aria-label="Candidates">
            {cands.map((k) => (
              <label key={k.id} className={cn("flex gap-3 items-start rounded-lg border p-3 cursor-pointer", pick === k.id ? "border-pex-primary bg-pex-primary-soft/40" : "border-surface-line")}>
                <input type="radio" name="cand" checked={pick === k.id} onChange={() => setPick(k.id)} className="mt-1" />
                <span className="text-sm"><span className="font-medium">{k.title ?? k.id}</span>{k.value && <span className="pex-mono ml-2">{k.value}</span>}
                  <span className="block text-xs text-pex-muted">{k.source}{typeof k.confidence === "number" ? ` · confidence ${Math.round(k.confidence * 100)}% (advisory)` : ""}</span></span>
              </label>
            ))}
          </div>
          <label className="grid gap-1 text-xs text-pex-muted mt-3">Rationale (required)<textarea value={why} onChange={(e) => setWhy(e.target.value)} rows={2} className={field} /></label>
          <button className={cn(primaryBtn, "mt-3")} disabled={!pick || !why.trim()} onClick={() => void run(() => disambiguateCase(caseId, pick, why.trim()), "Disambiguation recorded")}>Record disambiguation</button>
        </Section>
      )}
    </>
  );
};

// ------------------------------------------------------------ status unknown (design 07)
const NEXT_ICON: Record<string, React.ElementType> = { "not sent": Hourglass, "accepted by network": CheckCircle2, rejected: XCircle, "delivered but misapplied": RefreshCw };

export const StatusUnknownBlock: React.FC<{ s: StatusUnknownDto; blocked: NonNullable<CasePage["blocked_actions"]>; onAction: (key: string) => void; canWork: boolean; busy: boolean }> = ({ s, blocked, onAction, canWork, busy }) => (
  <>
    <Section title="What we know">
      <div className="overflow-x-auto rounded-lg border border-surface-line">
        <table className="w-full text-sm"><caption className="sr-only">Status by source</caption>
          <thead><tr className="text-left text-xs text-pex-muted bg-slate-50 border-b border-surface-line">{["Source", "Result", "Time"].map((h) => <th key={h} scope="col" className="py-2 px-3 font-medium">{h}</th>)}</tr></thead>
          <tbody>{(s.known ?? []).map((k, i) => <tr key={i} className="border-b border-surface-line last:border-0"><td className="py-2.5 px-3">{k.system}</td><td className="py-2.5 px-3">{k.says}</td><td className="py-2.5 px-3 pex-mono">{fmtTime(k.as_of) || "—"}</td></tr>)}</tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center gap-4 flex-wrap">
        <button className={primaryBtn} disabled={!canWork || busy} onClick={() => onAction("check_status")}><RefreshCw className={cn("w-4 h-4", busy && "animate-spin")} aria-hidden />Check status now</button>
        <button className="text-sm text-pex-primary hover:underline disabled:opacity-50" disabled={!canWork || busy} onClick={() => onAction("request_bank_status")}>Request status from bank operations</button>
        {s.last_check && <span className="text-xs text-pex-muted">Last check {fmtTime(s.last_check.at)}: {s.last_check.result}</span>}
      </div>
      <p className="text-xs text-pex-muted mt-2">Status checks are simulated and never resend the payment.</p>
    </Section>
    <Section title="What happens next" hint="The correct path depends on the confirmed status.">
      <ul className="divide-y divide-surface-line rounded-lg border border-surface-line">
        {(s.next ?? []).map((n, i) => { const Icon = NEXT_ICON[(n.outcome ?? "").toLowerCase()] ?? ChevronRight; return (
          <li key={i} className="flex items-center gap-3 px-3 py-2.5 text-sm"><Icon className="w-4 h-4 text-slate-500 shrink-0" aria-hidden /><span className="font-semibold w-52 shrink-0">{n.outcome}</span><span className="text-pex-muted flex-1">{n.what_happens}</span><ChevronRight className="w-4 h-4 text-pex-primary" aria-hidden /></li>); })}
      </ul>
    </Section>
    <Section title="Blocked actions">
      {(blocked.length ? blocked : [{ label: "Resend payment", reason: "Blocked until status is confirmed." }]).map((b, i) => (
        <div key={i} className="flex items-center gap-3 flex-wrap"><button disabled aria-disabled className="px-4 py-2 text-sm rounded-lg bg-slate-100 text-slate-500 inline-flex items-center gap-2 cursor-not-allowed"><Lock className="w-4 h-4" aria-hidden />{b.label}</button><span className="text-sm text-pex-muted">{b.reason}</span></div>
      ))}
    </Section>
  </>
);

// ------------------------------------------------------------ handoff / executed
export const BankBlock: React.FC<{ page: CasePage }> = ({ page }) => {
  if (page.variant === "HANDED_TO_BANK" && page.handoff) {
    const h = page.handoff;
    return <Section title="Bank handoff" hint="Handed to the bank (simulated). PeX has not seen a bank confirmation yet.">
      <KeyValueList cols={3} items={[{ label: "Handoff ID", value: h.handoff_id ?? "", mono: true }, { label: "Sent", value: fmtDateTime(h.sent_at) }, { label: "Mode", value: h.mode ?? "" }, { label: "Bank communication", value: h.bank_comm ?? "SIMULATED" }, { label: "Awaiting", value: h.awaiting ?? "Bank confirmation" }]} />
    </Section>;
  }
  if (page.variant === "EXECUTED" && page.bank) {
    const b = page.bank;
    return <Section title="Bank confirmation" hint="Confirmed by the bank's signed signal. PeX did not execute this payment.">
      <KeyValueList cols={3} items={[{ label: "Bank reference", value: b.reference ?? "", mono: true }, { label: "Confirmed", value: fmtDateTime(b.confirmed_at) }, { label: "Clearing system", value: b.clearing_system ?? "" }]} />
    </Section>;
  }
  return null;
};

