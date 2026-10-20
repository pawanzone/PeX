import React, { useState } from "react";
import { ArrowDownLeft, ArrowUpRight, Check, ClipboardPaste, Copy, FileText, ShieldCheck, Undo2 } from "lucide-react";
import { Avatar, Banner, ErrorState, Loading, PageHeader, StatusPill, Tabs, useToast, cn } from "../components/v2";
import { navigate } from "../lib/router";
import { useV2 } from "../services/v2/client";
import {
  authoriseMessage, closeNetworkCase, draftReply, getNetworkCase, getNetworkCases, raiseOutbound, receiveMessage, receiveSample, recordBankReturn, simulateReply,
  type NetDetail, type NetKind, type NetList, type NetRow, type NetStatus,
} from "../services/v2/network";
import { useSession } from "../shell/session";
import { fmtDateTime } from "./case/parts";

const TONE: Record<NetStatus, "blue" | "amber" | "green" | "grey"> = { NEW: "blue", DRAFTED: "amber", PART_APPROVED: "amber", SENT: "grey", REPLY_RECEIVED: "blue", AWAITING_BANK_RETURN: "amber", CLOSED: "grey" };
const money = (a: number | null, c?: string | null) => (a == null ? "" : `${new Intl.NumberFormat("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(a)} ${c ?? ""}`.trim());
const short = (u: string) => (u.length > 22 ? `${u.slice(0, 8)}…${u.slice(-6)}` : u);
const inputCls = "py-2 px-2.5 text-sm rounded-lg border border-surface-line bg-white w-full";
const btnPrimary = "px-3 py-1.5 text-sm font-medium rounded-lg bg-pex-primary text-white disabled:opacity-50 inline-flex items-center gap-1.5";
const btnGhost = "px-3 py-1.5 text-sm rounded-lg border border-surface-line bg-white hover:bg-slate-50 disabled:opacity-50 inline-flex items-center gap-1.5";

const Card: React.FC<{ title?: string; right?: React.ReactNode; children: React.ReactNode; className?: string }> = ({ title, right, children, className }) => (
  <section className={cn("bg-surface-card rounded-card border border-surface-line shadow-card p-4", className)}>
    {title && <div className="flex items-center justify-between mb-3"><h2 className="text-base font-semibold text-pex-ink">{title}</h2>{right}</div>}{children}
  </section>
);
const Field: React.FC<{ id: string; label: string; children: React.ReactNode }> = ({ id, label, children }) => (
  <div className="grid gap-1"><label htmlFor={id} className="text-xs font-medium text-pex-muted">{label}</label>{children}</div>
);
const Due: React.FC<{ r: Pick<NetRow, "due_at" | "overdue" | "status" | "direction"> }> = ({ r }) => {
  if (!r.due_at) return <span className="text-pex-muted">-</span>;
  const waiting = ["NEW", "DRAFTED", "PART_APPROVED"].includes(r.status) || (r.direction === "OUTBOUND" && r.status === "SENT");
  if (!waiting) return <span className="text-pex-muted">{fmtDateTime(r.due_at)}</span>;
  const hrs = Math.round((new Date(r.due_at).getTime() - Date.now()) / 3.6e6);
  return <span className={cn(r.overdue ? "text-red-700 font-medium" : "text-pex-ink")}>{r.overdue ? `${Math.abs(hrs)}h overdue` : hrs < 1 ? "due within the hour" : `due in ${hrs}h`}</span>;
};
const Kind: React.FC<{ r: Pick<NetRow, "kind" | "direction"> }> = ({ r }) => (
  <span className="inline-flex items-center gap-1.5">
    {r.direction === "INBOUND" ? <ArrowDownLeft className="w-4 h-4 text-pex-primary" aria-label="Inbound" /> : <ArrowUpRight className="w-4 h-4 text-pex-muted" aria-label="Outbound" />}
    {r.kind === "INVESTIGATION" ? "Investigation" : "Recall"}
  </span>
);

/* ---------- list ---------- */
const Composer: React.FC<{ list: NetList; onDone: (id: string) => void }> = ({ list, onDone }) => {
  const toast = useToast();
  const [mode, setMode] = useState("raise");
  const [kind, setKind] = useState<NetKind>("INVESTIGATION");
  const [caseId, setCaseId] = useState("");
  const [bic, setBic] = useState("");
  const [reason, setReason] = useState("");
  const [why, setWhy] = useState("");
  const [xml, setXml] = useState("");
  const [err, setErr] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const reasons = kind === "INVESTIGATION" ? list.codes.investigation_reasons : list.codes.recall_reasons;
  const run = async (fn: () => Promise<NetDetail>, ok: string) => {
    setBusy(true); setErr([]);
    try { const d = await fn(); toast.push(ok, "green"); onDone(d.id); } catch (e: any) { setErr(e?.problems?.length ? e.problems : [e?.message || "Failed"]); } finally { setBusy(false); }
  };
  return (
    <Card title="Start or receive" right={<Tabs tabs={[{ id: "raise", label: "Raise a case" }, { id: "paste", label: "Paste an incoming message" }, { id: "demo", label: "Demo samples" }]} value={mode} onChange={setMode} label="Network case actions" />}>
      {mode === "raise" && (
        <div className="grid gap-3 md:grid-cols-3">
          <Field id="nk" label="What"><select id="nk" className={inputCls} value={kind} onChange={(e) => { setKind(e.target.value as NetKind); setReason(""); }}><option value="INVESTIGATION">Investigation (camt.110)</option><option value="RECALL">Recall / cancellation (camt.056)</option></select></Field>
          <Field id="nc" label="Payment case id"><input id="nc" className={inputCls} placeholder="PEX-INV-0001" value={caseId} onChange={(e) => setCaseId(e.target.value.trim())} /></Field>
          <Field id="nb" label="Other bank's BIC"><input id="nb" className={inputCls} placeholder="CNTPDEFF" value={bic} onChange={(e) => setBic(e.target.value.toUpperCase().trim())} /></Field>
          <Field id="nr" label="Reason"><select id="nr" className={inputCls} value={reason} onChange={(e) => setReason(e.target.value)}><option value="">Choose…</option>{Object.entries(reasons).map(([k, v]) => <option key={k} value={k}>{k} · {v}</option>)}</select></Field>
          <div className="md:col-span-2"><Field id="nw" label="Explain in a sentence"><input id="nw" className={inputCls} value={why} onChange={(e) => setWhy(e.target.value)} /></Field></div>
          <div className="md:col-span-3 flex flex-wrap items-center gap-3">
            <button type="button" disabled={busy || !caseId || !bic || !reason || why.trim().length < 3} onClick={() => run(() => raiseOutbound({ kind, case_id: caseId, reason_code: reason, narrative: why, counterparty_bic: bic }), kind === "INVESTIGATION" ? "Investigation sent" : "Recall drafted: it needs an approver before it leaves PeX")} className={btnPrimary}>{kind === "INVESTIGATION" ? "Send investigation" : "Draft recall"}</button>
            <span className="text-xs text-pex-muted">{kind === "INVESTIGATION" ? "An information request goes out at once." : "A cancellation request needs a different approver before it is sent."}</span>
          </div>
        </div>
      )}
      {mode === "paste" && (
        <div className="grid gap-3">
          <Field id="nx" label="camt.110 or camt.056 XML received from another bank (a reply to something we sent also works)"><textarea id="nx" rows={6} className={cn(inputCls, "pex-mono text-xs")} value={xml} onChange={(e) => setXml(e.target.value)} /></Field>
          <div><button type="button" disabled={busy || !xml.trim()} onClick={() => run(() => receiveMessage(xml), "Message received")} className={btnPrimary}><ClipboardPaste className="w-4 h-4" aria-hidden />Receive message</button></div>
        </div>
      )}
      {mode === "demo" && (
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" disabled={busy} onClick={() => run(() => receiveSample("INVESTIGATION"), "Sample investigation received")} className={btnGhost}>Receive a sample investigation</button>
          <button type="button" disabled={busy} onClick={() => run(() => receiveSample("RECALL"), "Sample recall received")} className={btnGhost}>Receive a sample recall</button>
          <span className="text-xs text-pex-muted">Builds a real XML message from an existing payment and receives it as if it came from the network. Demo only.</span>
        </div>
      )}
      {!!err.length && <ul role="alert" className="mt-3 text-sm text-red-700 grid gap-0.5">{err.map((x, i) => <li key={i}>{x}</li>)}</ul>}
    </Card>
  );
};

const Tile: React.FC<{ label: string; value: number; tone?: "red" | "amber" }> = ({ label, value, tone }) => (
  <div className="rounded-card border border-surface-line bg-surface-card p-3 shadow-card"><div className={cn("text-2xl font-semibold pex-mono", tone === "red" && value ? "text-red-700" : tone === "amber" && value ? "text-amber-700" : "text-pex-ink")}>{value}</div><div className="text-xs text-pex-muted mt-0.5">{label}</div></div>
);

const NetworkList: React.FC = () => {
  const { epoch, persona } = useSession();
  const [kind, setKind] = useState("");
  const [dir, setDir] = useState("");
  const r = useV2(() => getNetworkCases(kind || undefined, dir || undefined), [epoch, kind, dir]);
  const canWork = ["OPERATOR", "SUPERVISOR"].includes(persona?.role ?? "");
  if (r.loading && !r.data) return <Loading label="Loading network cases…" />;
  if (r.error || !r.data) return <ErrorState unavailable={r.unavailable} message={r.error ?? undefined} onRetry={r.reload} />;
  const d = r.data;
  const chip = (cur: string, set: (v: string) => void, v: string, label: string) => (
    <button type="button" aria-pressed={cur === v} onClick={() => set(v)} className={cn("px-2.5 py-1 rounded-md text-xs border", cur === v ? "bg-pex-primary text-white border-pex-primary" : "bg-white border-surface-line text-pex-muted")}>{label}</button>
  );
  return (
    <>
      <PageHeader title="Network cases" subtitle="Investigations (camt.110 / camt.111) and recalls (camt.056 / camt.029) with other banks, tied to the payment by UETR." />
      <Banner tone="blue" title="Controls"><span className="inline-flex items-center gap-1.5"><ShieldCheck className="w-4 h-4" aria-hidden />{d.rule} We answer within {d.response_hours} hours (set in Policy Studio). Our BIC in this demo: {d.own_bic}.</span></Banner>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">
        <Tile label="Open" value={d.counts.open} /><Tile label="Overdue" value={d.counts.overdue} tone="red" /><Tile label="Waiting for the bank to return funds" value={d.counts.awaiting_bank} tone="amber" />
        <Tile label="Inbound" value={d.counts.inbound} /><Tile label="Outbound" value={d.counts.outbound} />
      </div>
      {canWork && <div className="mt-4"><Composer list={d} onDone={(id) => navigate(`#/network/${encodeURIComponent(id)}`)} /></div>}
      <div className="flex flex-wrap items-center gap-2 mt-4" role="group" aria-label="Filters">
        {chip(kind, setKind, "", "All types")}{chip(kind, setKind, "INVESTIGATION", "Investigations")}{chip(kind, setKind, "RECALL", "Recalls")}
        <span className="w-px h-5 bg-surface-line mx-1" aria-hidden />
        {chip(dir, setDir, "", "Both ways")}{chip(dir, setDir, "INBOUND", "Inbound")}{chip(dir, setDir, "OUTBOUND", "Outbound")}
      </div>
      <Card className="mt-3 p-0 overflow-x-auto">
        {d.items.length === 0 ? <p className="p-6 text-sm text-pex-muted">No network cases yet. {canWork ? "Raise one, paste a message, or use a demo sample above." : ""}</p> : (
          <table className="w-full text-sm"><thead className="text-xs text-pex-muted text-left"><tr><th className="py-2 px-3 font-medium">Case</th><th className="px-3 font-medium">Type</th><th className="px-3 font-medium">UETR</th><th className="px-3 font-medium">Bank</th><th className="px-3 font-medium text-right">Amount</th><th className="px-3 font-medium">Status</th><th className="px-3 font-medium">Due</th><th className="px-3 font-medium">Payment case</th></tr></thead>
            <tbody>{d.items.map((x) => (
              <tr key={x.id} className="border-t border-surface-line hover:bg-slate-50 cursor-pointer" onClick={() => navigate(`#/network/${encodeURIComponent(x.id)}`)}>
                <td className="py-2 px-3"><a href={`#/network/${encodeURIComponent(x.id)}`} className="pex-mono text-pex-primary hover:underline" onClick={(e) => e.stopPropagation()}>{x.id}</a></td>
                <td className="px-3"><Kind r={x} /><div className="text-xs text-pex-muted">{x.reason_label}</div></td><td className="px-3 pex-mono text-xs" title={x.uetr}>{short(x.uetr)}</td><td className="px-3 pex-mono text-xs">{x.counterparty_bic}</td>
                <td className="px-3 text-right pex-mono">{money(x.amount, x.currency)}</td><td className="px-3"><StatusPill tone={TONE[x.status]}>{x.status_label}</StatusPill></td><td className="px-3"><Due r={x} /></td>
                <td className="px-3 pex-mono text-xs">{x.linked_case_id ?? <span className="text-amber-700">none</span>}</td>
              </tr>))}</tbody></table>)}
      </Card>
    </>
  );
};

/* ---------- detail ---------- */
const Xml: React.FC<{ xml: string }> = ({ xml }) => {
  const toast = useToast();
  return (
    <div className="relative">
      <button type="button" aria-label="Copy XML" onClick={() => { try { navigator.clipboard.writeText(xml); toast.push("XML copied", "green"); } catch { /* clipboard blocked */ } }} className="absolute top-2 right-2 p-1.5 rounded-md bg-white border border-surface-line hover:bg-slate-50"><Copy className="w-4 h-4" aria-hidden /></button>
      <pre className="text-xs pex-mono bg-slate-50 border border-surface-line rounded-lg p-3 overflow-auto max-h-80 whitespace-pre-wrap break-all">{xml}</pre>
    </div>
  );
};
const FieldTable: React.FC<{ f: Record<string, any> }> = ({ f }) => {
  const rows: Array<[string, any]> = [["Message", f.msg_type], ["Message id", f.message_id], ["Their case id", f.case_id], ["From", f.sender_bic], ["To", f.receiver_bic], ["UETR", f.uetr], ["End-to-end id", f.end_to_end_id],
    ["Amount", f.amount != null ? money(f.amount, f.currency) : ""], ["Settlement date", f.settlement_date], ["Reason", f.reason_code], ["Status", f.status_code], ["Note", f.narrative]];
  return <dl className="grid grid-cols-[10rem_1fr] gap-x-3 gap-y-1.5 text-sm">{rows.filter(([, v]) => v).map(([k, v]) => <React.Fragment key={k}><dt className="text-pex-muted">{k}</dt><dd className="pex-mono text-xs break-all self-center">{String(v)}</dd></React.Fragment>)}</dl>;
};

const Decision: React.FC<{ d: NetDetail; onChange: (d: NetDetail) => void }> = ({ d, onChange }) => {
  const toast = useToast();
  const a = d.actions;
  const [outcome, setOutcome] = useState(d.response?.outcome ?? "");
  const [reason, setReason] = useState(d.response?.reason_code ?? "");
  const [text, setText] = useState(d.response?.text ?? "");
  const [note, setNote] = useState("");
  const [ref, setRef] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const run = async (fn: () => Promise<NetDetail>, ok: string) => { setBusy(true); setErr(null); try { const n = await fn(); toast.push(ok, "green"); setNote(""); onChange(n); } catch (e: any) { setErr(e?.message || "Failed"); } finally { setBusy(false); } };
  const recall = d.kind === "RECALL";
  const next: Record<NetStatus, string> = {
    NEW: "Draft a reply. A different approver then authorises it before anything is sent.",
    DRAFTED: "The draft is waiting for an approver who did not write it.",
    PART_APPROVED: `One approval is in; a second, different approver is needed (amount is at or above ${new Intl.NumberFormat("en-GB").format(d.dual_amount)}).`,
    SENT: d.direction === "OUTBOUND" ? "Sent. Waiting for the other bank's reply." : "Reply sent. Close the case when you are done.",
    REPLY_RECEIVED: "The other bank has replied. Read it and close the case.",
    AWAITING_BANK_RETURN: "Accepted. The bank system must return the funds; PeX does not move money. Record the bank's confirmation when it arrives.",
    CLOSED: "Closed.",
  };
  return (
    <Card title="Decision" className="grid gap-4 content-start">
      <p className="text-sm text-pex-muted">{next[d.status]}</p>
      {a.can_draft && (
        <div className="grid gap-3">
          <Field id="do" label={recall ? "Decision" : "Outcome"}>
            <select id="do" className={inputCls} value={outcome} onChange={(e) => { setOutcome(e.target.value); setReason(""); }}><option value="">Choose…</option>{Object.entries(d.codes.outcomes).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          </Field>
          {recall && outcome && (
            <Field id="dr" label={outcome === "RJCR" ? "Reason for rejecting (required)" : "Reason (optional)"}>
              <select id="dr" className={inputCls} value={reason} onChange={(e) => setReason(e.target.value)}><option value="">{outcome === "RJCR" ? "Choose…" : "None"}</option>{Object.entries(outcome === "RJCR" ? d.codes.reject_reasons : d.codes.accept_reasons).map(([k, v]) => <option key={k} value={k}>{k} · {v}</option>)}</select>
            </Field>
          )}
          <Field id="dt" label={recall ? "Note to the other bank (optional)" : "What we found"}><textarea id="dt" rows={3} className={inputCls} value={text} onChange={(e) => setText(e.target.value)} /></Field>
          <div><button type="button" disabled={busy || !outcome || (recall && outcome === "RJCR" && !reason) || (!recall && text.trim().length < 3)} onClick={() => run(() => draftReply(d.id, { outcome, reason_code: reason || null, text }), "Draft saved")} className={btnPrimary}><FileText className="w-4 h-4" aria-hidden />{d.status === "DRAFTED" ? "Update draft" : "Save draft"}</button></div>
        </div>
      )}
      {(d.status === "DRAFTED" || d.status === "PART_APPROVED") && (
        <div className="grid gap-2 rounded-lg border border-amber-200 bg-amber-50/50 p-3">
          <div className="text-sm font-medium">Authorisation: {d.approvals.length} of {d.approvals_needed}</div>
          {d.approvals.map((x) => <div key={x.user_id} className="flex items-center gap-2 text-sm"><Avatar bare size="sm" name={x.name} /><span>{x.name}</span><span className="text-xs text-pex-muted">{fmtDateTime(x.at)}</span></div>)}
          {a.can_authorise ? (
            <>
              <Field id="an" label="Note (optional)"><input id="an" className={inputCls} value={note} onChange={(e) => setNote(e.target.value)} /></Field>
              <div><button type="button" disabled={busy} onClick={() => run(() => authoriseMessage(d.id, note), "Authorised")} className={btnPrimary}><Check className="w-4 h-4" aria-hidden />{d.approvals.length + 1 >= d.approvals_needed ? "Authorise and send" : "Give first approval"}</button></div>
            </>
          ) : <p className="text-xs text-pex-muted">Only an approver who did not draft this, and has not already approved it, can authorise.</p>}
        </div>
      )}
      {a.can_simulate_reply && (
        <div className="grid gap-2 rounded-lg border border-surface-line p-3">
          <div className="text-sm font-medium">Demo: the other bank replies</div>
          <div className="flex flex-wrap gap-2">{(recall ? [["CNCL", "Accepts"], ["RJCR", "Rejects"]] : [["ANSW", "Answers"], ["WIPG", "Working on it"], ["RJCT", "Cannot investigate"]]).map(([k, l]) => <button key={k} type="button" disabled={busy} onClick={() => run(() => simulateReply(d.id, k), "Reply received")} className={btnGhost}>{l}</button>)}</div>
        </div>
      )}
      {a.can_record_return && (
        <div className="grid gap-2 rounded-lg border border-surface-line p-3">
          <Field id="rr" label="Bank's reference for the return (for example its pacs.004 id)"><input id="rr" className={inputCls} value={ref} onChange={(e) => setRef(e.target.value)} /></Field>
          <div><button type="button" disabled={busy || ref.trim().length < 3} onClick={() => run(() => recordBankReturn(d.id, ref), "Bank confirmation recorded")} className={btnPrimary}><Undo2 className="w-4 h-4" aria-hidden />Record bank confirmation</button></div>
        </div>
      )}
      {a.can_close && <div><button type="button" disabled={busy} onClick={() => run(() => closeNetworkCase(d.id, note), "Case closed")} className={btnGhost}>Close case</button></div>}
      {err && <p role="alert" className="text-sm text-red-700">{err}</p>}
    </Card>
  );
};

const NetworkDetail: React.FC<{ id: string }> = ({ id }) => {
  const { epoch } = useSession();
  const r = useV2(() => getNetworkCase(id), [id, epoch]);
  const [tab, setTab] = useState("request");
  const [local, setLocal] = useState<NetDetail | null>(null);
  const d = local && local.id === id ? local : r.data;
  if (r.loading && !d) return <Loading label="Loading case…" />;
  if ((r.error && !d) || !d) return <ErrorState unavailable={r.unavailable} message={r.error ?? undefined} onRetry={r.reload} />;
  const tabs = [{ id: "request", label: d.request.title }, ...(d.response ? [{ id: "reply", label: d.response.title }] : []), { id: "timeline", label: `Timeline (${d.timeline.length})` }];
  const msg = tab === "reply" && d.response ? d.response : d.request;
  return (
    <>
      <a href="#/network" className="text-sm text-pex-primary hover:underline">← Network cases</a>
      <PageHeader title={`${d.id} · ${d.kind === "INVESTIGATION" ? "Investigation" : "Recall"} ${d.direction === "INBOUND" ? "from" : "to"} ${d.counterparty_bic}`} subtitle={`${money(d.amount, d.currency)} · ${d.reason_label}`} />
      <div className="flex flex-wrap items-center gap-3 mb-3 text-sm">
        <StatusPill tone={TONE[d.status]}>{d.status_label}</StatusPill><Kind r={d} /><span>·</span><Due r={d} />
        {d.linked_case ? <a href={`#${d.linked_case.link}`} className="pex-mono text-pex-primary hover:underline">Payment case {d.linked_case.case_id}</a> : <span className="text-amber-700">No matching payment case</span>}
      </div>
      {d.warnings.map((w) => <div key={w} className="mb-2"><Banner tone="amber" title="Check this">{w}</Banner></div>)}
      {!d.uetr_standard && <div className="mb-2"><Banner tone="grey" title="UETR format">This UETR is not a standard UUID. That is normal in the demo data; a real network UETR is a UUID.</Banner></div>}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <Card>
          <Tabs tabs={tabs} value={tab} onChange={setTab} label="Case sections" />
          <div className="mt-4">
            {tab === "timeline" ? (
              <ol className="grid gap-3">{d.timeline.map((t, i) => <li key={i} className="grid grid-cols-[9rem_1fr] gap-3 text-sm"><span className="text-xs text-pex-muted">{fmtDateTime(t.at)}</span><span><span className="font-medium">{t.actor}</span> · {t.text}</span></li>)}</ol>
            ) : msg.fields ? (
              <div className="grid gap-4"><FieldTable f={msg.fields} />{msg.xml && <details open><summary className="cursor-pointer text-sm text-pex-muted mb-2">Message XML (simplified ISO 20022 structure, not validated against the official schema)</summary><Xml xml={msg.xml} /></details>}</div>
            ) : <p className="text-sm text-pex-muted">{msg.title} drafted: {msg.outcome_label}. {msg.text}</p>}
          </div>
        </Card>
        <div className="grid gap-4 content-start">
          <Decision key={d.id + d.status + d.approvals.length} d={d} onChange={setLocal} />
          {d.handoff && <Card title="Hand-off to the bank system"><p className="text-sm">{d.handoff.state === "RETURN_CONFIRMED" ? `Bank confirmed the return (${d.handoff.reference}).` : d.handoff.note}</p></Card>}
          <Banner tone="grey" title="PeX does not move money">{d.kind === "RECALL" ? "Accepting a recall only asks the bank system to return the funds." : "An investigation only exchanges information."} {d.money_moved ? "" : "Nothing has been moved by PeX."}</Banner>
        </div>
      </div>
    </>
  );
};

export const Network: React.FC<{ id?: string }> = ({ id }) => (id ? <NetworkDetail id={id} /> : <NetworkList />);
