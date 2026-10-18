import React, { useState } from "react";
import { Check, Ban, Users, Lock, ExternalLink, Paperclip, AlertTriangle, Minus } from "lucide-react";
import { Banner, Breadcrumbs, CaseHeader, CaseJourney, NextActionCard, Loading, ErrorState, ReasonCommentFields, ConfirmCheckbox, StatusPill, useToast, cn } from "../../components/v2";
import { useV2 } from "../../services/v2/client";
import { getCasePage, postComplianceDecision, type ComplianceDecisionKey, type PartyRow } from "../../services/v2/compliance";
import { navigate, routes } from "../../lib/router";
import { useSession } from "../../shell/session";
import { hhmm, mapJourney, tone } from "./fmt";

const RESULT: Record<string, { tone: "amber" | "grey" | "green" | "red"; icon: React.ElementType; label: string }> = {
  similar: { tone: "amber", icon: AlertTriangle, label: "Similar" },
  same: { tone: "grey", icon: Minus, label: "Same" },
  differs: { tone: "green", icon: Check, label: "Differs" },
  not_comparable: { tone: "grey", icon: Minus, label: "Not comparable" },
};
const DEFAULT_DECISIONS = [
  { key: "release", label: "Clear hold · false match (returns to approval)" },
  { key: "confirm_block", label: "Confirm match · block payment", needs_second_reviewer: true },
  { key: "escalate", label: "Escalate to Senior Compliance" },
];
const DEC_STYLE: Record<string, { cls: string; icon: React.ElementType }> = {
  release: { cls: "border-pex-ok text-pex-ok hover:bg-pex-ok-soft", icon: Check },
  confirm_block: { cls: "border-pex-block text-pex-block hover:bg-pex-block-soft", icon: Ban },
  escalate: { cls: "border-pex-primary text-pex-primary hover:bg-pex-primary-soft", icon: Users },
};

export const ComplianceCase: React.FC<{ id: string }> = ({ id }) => {
  const { epoch } = useSession();
  const toast = useToast();
  const page = useV2(() => getCasePage(id), [id, epoch]);
  const [pick, setPick] = useState<ComplianceDecisionKey | null>(null);
  const [reason, setReason] = useState("");
  const [comment, setComment] = useState("");
  const [ack, setAck] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [notes, setNotes] = useState("");

  const crumbs = [{ label: "Compliance", href: routes.compliance() }, { label: id }];
  if (page.loading && !page.data) return <><Breadcrumbs items={crumbs} /><Loading /></>;
  if (page.error || !page.data) return <><Breadcrumbs items={crumbs} /><ErrorState unavailable={page.unavailable} message={page.error ?? undefined} onRetry={page.reload} /></>;

  const p = page.data;
  const c = p.compliance;
  const h = p.header ?? {};
  const isCompliance = p.variant === "COMPLIANCE_HOLD" && !!c;
  const viewerCanDecide = p.viewer_mode === "compliance";
  const decisions = c?.decisions?.length ? c.decisions : DEFAULT_DECISIONS;
  const reasons = (c?.reason_codes ?? []).map((r) => ({ value: r.code, label: r.label }));
  const second = c?.second_review;
  const lockedReason = !viewerCanDecide ? "Only a Compliance Officer can record a decision." : undefined;
  const ja = p.journey?.next_action;

  const submit = async () => {
    if (!pick) return;
    setBusy(true); setErr(null);
    try {
      const r = await postComplianceDecision(id, { decision: pick, reason_code: reason, comment: [comment, notes && `Investigation notes: ${notes}`].filter(Boolean).join("\n") });
      toast.push(r?.message || "Decision recorded.", "green");
      setPick(null); setReason(""); setComment(""); setAck(false); setNotes("");
      page.reload();
    } catch (e: any) { setErr(e?.message || "Could not record the decision."); }
    finally { setBusy(false); }
  };

  return (
    <>
      <div className="mb-3"><Breadcrumbs items={crumbs} /></div>
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-5 items-start">
        <div className="grid gap-4 min-w-0">
          <CaseHeader id={p.case_id} chips={h.chips?.map((x) => ({ label: x.label, tone: tone(x.tone) }))} title={h.creditor ? `Party: ${h.creditor}` : h.title}
            amount={h.amount?.display} cutoff={h.cutoff?.at} />
          <Banner tone={p.banner ? tone(p.banner.tone, "grey") : "grey"} title={p.banner?.title}>
            <span className="inline-flex items-center gap-2"><Lock className="w-4 h-4" aria-hidden />{p.banner?.text ?? "Repair actions are unavailable while the hold is open. Do not contact the customer about this alert."}</span>
          </Banner>
          {!isCompliance && <Banner tone="amber" title="This case has no compliance hold in this view">It is shown as variant {p.variant}. Open it from the Worklist for the normal case page.</Banner>}

          {c?.alert && (
            <section className="bg-surface-card rounded-card border border-surface-line shadow-card p-5" aria-labelledby="alert-h">
              <h2 id="alert-h" className="text-base font-semibold text-pex-ink mb-3">Screening alert</h2>
              <div className="flex justify-between gap-4 flex-wrap">
                <dl className="grid grid-cols-[140px_1fr] gap-y-1.5 text-sm">
                  <dt className="text-pex-muted">Alert reference</dt><dd className="pex-mono">{c.alert.reference ?? "—"}</dd>
                  <dt className="text-pex-muted">Screening system</dt><dd>{c.alert.source ?? "—"}</dd>
                  <dt className="text-pex-muted">List</dt><dd>{c.alert.list ?? "—"}</dd>
                  <dt className="text-pex-muted">Match type</dt><dd>{c.alert.match_type ?? "—"}</dd>
                  <dt className="text-pex-muted">Raised</dt><dd>{hhmm(c.alert.raised_at) || "—"}</dd>
                </dl>
                <div className="text-sm">
                  {c.alert.open_url
                    ? <a href={c.alert.open_url} target="_blank" rel="noreferrer" className="text-pex-primary inline-flex items-center gap-1.5 hover:underline"><ExternalLink className="w-4 h-4" aria-hidden />Open in screening system</a>
                    : <span className="text-pex-muted inline-flex items-center gap-1.5"><ExternalLink className="w-4 h-4" aria-hidden />Open in screening system (not linked)</span>}
                  {c.alert.note && <div className="text-xs text-pex-muted mt-1 max-w-[260px]">{c.alert.note}</div>}
                </div>
              </div>
            </section>
          )}

          {c && (
            <section className="bg-surface-card rounded-card border border-surface-line shadow-card p-5" aria-labelledby="cmp-h">
              <h2 id="cmp-h" className="text-base font-semibold text-pex-ink mb-3">Payment party vs listed entity</h2>
              {!c.party_comparison?.length ? <div className="text-sm text-pex-muted">No comparison data was returned.</div> : (
                <div className="overflow-x-auto border border-surface-line rounded-lg">
                  <table className="w-full text-sm">
                    <caption className="sr-only">Attribute comparison between the payment party and the listed entity</caption>
                    <thead className="bg-slate-50 text-xs text-pex-muted text-left"><tr>{["Attribute", "Payment", "Listed entity", "Result"].map((x) => <th key={x} scope="col" className="py-2 px-3 font-medium">{x}</th>)}</tr></thead>
                    <tbody>{c.party_comparison.map((r: PartyRow, i) => {
                      const m = RESULT[r.result ?? ""] ?? { tone: "grey" as const, icon: Minus, label: r.label ?? r.result ?? "—" };
                      const Icon = m.icon;
                      return (
                        <tr key={i} className="border-t border-surface-line">
                          <td className="py-2.5 px-3">{r.attribute}</td><td className="py-2.5 px-3">{r.payment_party ?? "—"}</td><td className="py-2.5 px-3">{r.listed_entity ?? "—"}</td>
                          <td className="py-2.5 px-3"><StatusPill tone={m.tone} dot={false}><Icon className="w-3.5 h-3.5" aria-hidden />{r.label ?? m.label}</StatusPill></td>
                        </tr>
                      );
                    })}</tbody>
                  </table>
                </div>
              )}
              {!!c.notes?.length && (
                <ul className="mt-3 grid gap-1.5 text-sm">{c.notes.map((n, i) => <li key={i} className="rounded-lg bg-slate-50 px-3 py-2"><span className="text-xs text-pex-muted">{n.by} · {hhmm(n.at)}</span><div>{n.text}</div></li>)}</ul>
              )}
              <label className="block mt-4 text-sm text-pex-muted">Investigation notes
                <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} placeholder="Add findings" disabled={!viewerCanDecide} className="mt-1 w-full py-2 px-2.5 text-sm rounded-lg border border-surface-line bg-white text-pex-ink disabled:bg-slate-50" />
              </label>
              <div className="mt-2 text-sm flex items-center gap-4 flex-wrap">
                <span className="text-pex-muted inline-flex items-center gap-1.5" title="Attachments are not uploaded in this demo"><Paperclip className="w-4 h-4" aria-hidden />Attach document (not available in demo)</span>
                {c.attachments?.map((a) => <span key={a.name} className="pex-mono text-xs">{a.name}</span>)}
              </div>
            </section>
          )}

          {c && (
            <section className="bg-surface-card rounded-card border border-surface-line shadow-card p-5" aria-labelledby="dec-h">
              <h2 id="dec-h" className="text-base font-semibold text-pex-ink mb-3">Compliance decision</h2>
              {second?.state === "pending" && <div className="mb-3"><Banner tone="amber" title="Second review pending">First review recorded{second.first_reviewer ? ` by ${second.first_reviewer}` : ""}. A different reviewer must confirm before the payment is blocked.</Banner></div>}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {decisions.map((d) => {
                  const st = DEC_STYLE[d.key] ?? DEC_STYLE.escalate; const Icon = st.icon;
                  return (
                    <button key={d.key} type="button" disabled={!!lockedReason} title={lockedReason} onClick={() => { setPick(d.key as ComplianceDecisionKey); setErr(null); }}
                      aria-pressed={pick === d.key}
                      className={cn("flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border bg-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed", st.cls, pick === d.key && "ring-2 ring-offset-1 ring-pex-primary")}>
                      <Icon className="w-4 h-4" aria-hidden />{d.label}
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-pex-muted mt-2">{lockedReason ?? "A reason code and comment are required. Confirming a match requires a second reviewer."}</p>
              {pick && viewerCanDecide && (
                <div className="mt-4 border-t border-surface-line pt-4 grid gap-3 max-w-xl">
                  <div className="text-sm font-medium">{decisions.find((d) => d.key === pick)?.label}</div>
                  <ReasonCommentFields reasons={reasons} reason={reason} onReason={setReason} comment={comment} onComment={setComment} required reasonLabel="Reason code" commentLabel="Comment (required)" />
                  <ConfirmCheckbox id="cmp-ack" checked={ack} onChange={setAck}>I have reviewed the alert and the party comparison.</ConfirmCheckbox>
                  {err && <Banner tone="red" title="Decision not recorded">{err}</Banner>}
                  <div className="flex gap-2">
                    <button type="button" disabled={busy || !reason || !comment.trim() || !ack} onClick={submit}
                      className="px-4 py-2 text-sm font-medium rounded-lg bg-pex-primary text-white hover:bg-pex-primary-dark disabled:opacity-50 disabled:cursor-not-allowed">{busy ? "Recording…" : "Record decision"}</button>
                    <button type="button" onClick={() => setPick(null)} className="px-4 py-2 text-sm rounded-lg border border-surface-line bg-white hover:bg-slate-50">Cancel</button>
                  </div>
                  {(!reason || !comment.trim() || !ack) && <p className="text-xs text-pex-muted">Choose a reason, add a comment and tick the box to continue.</p>}
                </div>
              )}
              <p className="text-xs text-pex-muted mt-4 pt-3 border-t border-surface-line">{c.footer ?? "The decision is recorded in PeX and passed to the bank. The bank screening system remains the system of record."}</p>
            </section>
          )}
          {!!p.blocked_actions?.length && <ul className="text-xs text-pex-muted grid gap-1">{p.blocked_actions.map((b, i) => <li key={i} className="flex items-center gap-1.5"><Lock className="w-3 h-3" aria-hidden />{b.label}: {b.reason}</li>)}</ul>}
        </div>

        <CaseJourney steps={mapJourney(p.journey)} tone={tone(ja?.tone, "blue")}
          nextAction={ja ? <NextActionCard tone={tone(ja.tone, "blue")} title={ja.title ?? "Next action"} detail={ja.text} owner={ja.owner} /> : undefined}
          auditCount={p.journey?.audit_events} onViewAudit={() => navigate(routes.audit({ case: id }))} />
      </div>
    </>
  );
};
