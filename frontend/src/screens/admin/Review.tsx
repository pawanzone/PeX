import React, { useRef, useState } from "react";
import { Download, Upload } from "lucide-react";
import { Banner, StatusPill, cn } from "../../components/v2";
import { useV2 } from "../../services/v2/client";
import { useSession } from "../../shell/session";
import {
  addReviewComment, addressReviewComment, downloadReviewWorkbook, getReviewDetail, getReviewItems, getReviewSummary, importReviewWorkbook, setReviewStatus,
  type ReviewCounts, type ReviewImportResult, type ReviewKind, type ReviewStatus,
} from "../../services/v2/review";
import { pretty } from "./Library";
import { Card, Stat, Wait } from "./Reference";

const th = "py-1.5 pr-3 font-medium whitespace-nowrap";
const TONE: Record<ReviewStatus, "grey" | "blue" | "amber" | "green" | "red"> = { NOT_REVIEWED: "grey", IN_REVIEW: "blue", CHANGES_REQUESTED: "amber", SIGNED_OFF: "green", CHANGED_SINCE_SIGNOFF: "red" };
const LABEL: Record<ReviewStatus, string> = { NOT_REVIEWED: "Not reviewed", IN_REVIEW: "In review", CHANGES_REQUESTED: "Changes requested", SIGNED_OFF: "Signed off", CHANGED_SINCE_SIGNOFF: "Changed since sign-off" };
const SETTABLE: ReviewStatus[] = ["IN_REVIEW", "CHANGES_REQUESTED", "SIGNED_OFF"];
const canReview = (role?: string) => role === "ADMIN" || role === "POLICY_OWNER";

export const ReviewPill: React.FC<{ status: ReviewStatus }> = ({ status }) => <StatusPill tone={TONE[status]} dot={false}>{LABEL[status]}</StatusPill>;

/** Review of one profile or control: status, who and when, comments. Shown in the profile drawer and in the review list. */
export const ReviewPanel: React.FC<{ kind: ReviewKind; id: string; onChange?: () => void }> = ({ kind, id, onChange }) => {
  const { persona } = useSession();
  const editable = canReview(persona?.role as string | undefined);
  const [tick, setTick] = useState(0);
  const r = useV2(() => getReviewDetail(kind, id), [kind, id, tick]);
  const [text, setText] = useState("");
  const [part, setPart] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const d = r.data;
  if (!d) return <Wait r={r} />;
  const done = () => { setTick((t) => t + 1); onChange?.(); };
  const run = async (f: () => Promise<unknown>) => { setErr(null); try { await f(); done(); } catch (e: any) { setErr(e?.message || "That did not work"); } };
  return (
    <section aria-label="SME review" className="grid gap-3">
      <div>
        <h3 className="font-semibold">SME review</h3>
        <p className="text-pex-muted text-sm">The bank's experts confirm this against their own process. A sign-off applies to the content version below; a later change reopens it.</p>
      </div>
      <div className="flex items-center gap-2 flex-wrap text-sm">
        <ReviewPill status={d.status} />
        <span className="text-pex-muted">Version <span className="pex-mono">{d.version}</span>{d.reviewed_at ? ` · ${d.reviewer_name || d.reviewer} · ${d.reviewed_at.slice(0, 10)}` : ""}</span>
        {d.status === "CHANGED_SINCE_SIGNOFF" && <span className="text-red-700 text-xs">Signed off on version <span className="pex-mono">{d.signed_off_on_version}</span>; the content has changed since.</span>}
      </div>
      {editable && (
        <div className="flex gap-2 flex-wrap" role="group" aria-label="Set review status">
          {SETTABLE.map((s) => <button key={s} type="button" onClick={() => run(() => setReviewStatus(kind, id, s))} className={cn("px-3 py-1.5 text-sm rounded-lg border", d.stored_status === s ? "bg-pex-primary text-white border-pex-primary" : "bg-white border-surface-line")}>{LABEL[s]}</button>)}
        </div>
      )}
      {err && <p role="alert" className="text-sm text-red-700">{err}</p>}
      <div>
        <h4 className="font-medium text-sm mb-1">Comments ({d.comments.filter((c) => c.status === "OPEN").length} open)</h4>
        {!d.comments.length ? <p className="text-sm text-pex-muted">No comments yet.</p> : (
          <ul className="grid gap-2">{d.comments.map((c) => (
            <li key={c.id} className="rounded-lg border border-surface-line p-2.5 text-sm">
              <div className="flex items-center gap-2 flex-wrap"><StatusPill tone={c.status === "OPEN" ? "amber" : "green"} dot={false}>{c.status === "OPEN" ? "Open" : "Addressed"}</StatusPill>{c.part && <span className="pex-mono text-xs">{c.part}</span>}<span className="text-xs text-pex-muted">{c.author_name || c.author} · {c.created_at.slice(0, 10)}</span></div>
              <p className="mt-1">{c.text}</p>
              {c.status === "ADDRESSED" && <p className="text-xs text-pex-muted mt-1">Addressed by {c.addressed_by}{c.addressed_note ? `: ${c.addressed_note}` : ""}</p>}
              {editable && c.status === "OPEN" && <button type="button" className="text-xs underline mt-1" onClick={() => run(() => addressReviewComment(c.id))}>Mark addressed</button>}
            </li>))}</ul>
        )}
      </div>
      {editable && (
        <form className="grid gap-2" onSubmit={(e) => { e.preventDefault(); if (text.trim()) run(async () => { await addReviewComment(kind, id, text.trim(), part.trim() || undefined); setText(""); setPart(""); }); }}>
          <label className="text-sm grid gap-1"><span className="text-pex-muted">Comment</span><textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} maxLength={2000} className="rounded-lg border border-surface-line bg-white px-2 py-1.5" /></label>
          <label className="text-sm grid gap-1 sm:max-w-sm"><span className="text-pex-muted">About which part? (optional, for example evidence: CORE_DDA_ACCOUNT)</span><input value={part} onChange={(e) => setPart(e.target.value)} maxLength={160} className="rounded-lg border border-surface-line bg-white px-2 py-1.5" /></label>
          <div><button type="submit" disabled={!text.trim()} className="px-3 py-1.5 text-sm rounded-lg border border-surface-line bg-white disabled:opacity-50">Add comment</button></div>
        </form>
      )}
    </section>
  );
};

const Counts: React.FC<{ title: string; c: ReviewCounts }> = ({ title, c }) => (
  <Card title={title}>
    <div className="grid gap-2 grid-cols-2 sm:grid-cols-5">
      <Stat label="Signed off" value={`${c.SIGNED_OFF} of ${c.total}`} hint={`${c.percent_signed_off}%`} />
      <Stat label="In review" value={c.IN_REVIEW} />
      <Stat label="Changes requested" value={c.CHANGES_REQUESTED} />
      <Stat label="Changed since sign-off" value={c.CHANGED_SINCE_SIGNOFF} />
      <Stat label="Not reviewed" value={c.NOT_REVIEWED} />
    </div>
  </Card>
);

/** Where the bank's SME validation stands, with the Excel round trip. */
export const ReviewView: React.FC = () => {
  const { persona } = useSession();
  const isAdmin = persona?.role === ("ADMIN" as any);
  const [kind, setKind] = useState<ReviewKind>("profile");
  const [tick, setTick] = useState(0);
  const [open, setOpen] = useState<string | null>(null);
  const s = useV2(getReviewSummary, [tick]);
  const l = useV2(() => getReviewItems(kind), [kind, tick]);
  const [res, setRes] = useState<ReviewImportResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  if (!s.data) return <Wait r={s} />;
  const send = async (f?: File) => {
    if (!f) return;
    setErr(null); setRes(null);
    try { setRes(await importReviewWorkbook(f)); setTick((t) => t + 1); } catch (e: any) { setErr(e?.message || "Import failed"); } finally { if (input.current) input.current.value = ""; }
  };
  const bump = () => setTick((t) => t + 1);
  return (
    <div className="grid grid-cols-1 gap-4 min-w-0">
      <Banner tone="blue" title="SME review">Each profile and control is validated by the bank's own experts: set a status, leave comments, or work offline in Excel and send the workbook back. Review changes no rule, profile or case.</Banner>
      <div className="grid gap-4 md:grid-cols-2"><Counts title="Profiles" c={s.data.profiles} /><Counts title="Controls" c={s.data.controls} /></div>
      <Card title="Excel round trip" right={<span className="text-xs text-pex-muted">{s.data.open_comments} open comment(s)</span>}>
        <div className="flex items-center gap-3 flex-wrap">
          <button type="button" onClick={() => downloadReviewWorkbook()} className="px-3 py-1.5 text-sm rounded-lg border border-surface-line bg-white inline-flex items-center gap-1.5"><Download className="w-4 h-4" aria-hidden />Download review workbook</button>
          {isAdmin && <>
            <input ref={input} type="file" accept=".xlsx" className="sr-only" id="review-file" onChange={(e) => send(e.target.files?.[0])} />
            <label htmlFor="review-file" className="px-3 py-1.5 text-sm rounded-lg border border-surface-line bg-white inline-flex items-center gap-1.5 cursor-pointer"><Upload className="w-4 h-4" aria-hidden />Import completed workbook</label>
          </>}
          <span className="text-xs text-pex-muted">Fill in Status and Reviewer comment, leave Version as it is.</span>
        </div>
        {err && <p role="alert" className="text-sm text-red-700 mt-2">{err}</p>}
        {res && <div className="mt-2 text-sm" role="status">Applied {res.applied} row(s){res.rejected.length ? `; ${res.rejected.length} not used:` : "."}
          {!!res.rejected.length && <ul className="list-disc pl-5 text-pex-muted">{res.rejected.slice(0, 20).map((x, i) => <li key={i}>{x.sheet} row {x.row} ({x.id || "no id"}): {x.reason}</li>)}</ul>}</div>}
      </Card>
      <Card title="Items" right={<div className="flex gap-1.5" role="group" aria-label="Kind">{(["profile", "control"] as ReviewKind[]).map((k) => <button key={k} type="button" aria-pressed={kind === k} onClick={() => { setKind(k); setOpen(null); }} className={cn("px-2.5 py-1 rounded-md text-xs border", kind === k ? "bg-pex-primary text-white border-pex-primary" : "bg-white border-surface-line")}>{k === "profile" ? "Profiles" : "Controls"}</button>)}</div>}>
        {!l.data ? <Wait r={l} /> : (
          <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Review status of each {kind}</caption>
            <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>{kind === "profile" ? "Code" : "ID"}</th><th className={th}>Name</th><th className={th}>Status</th><th className={th}>Open comments</th><th className="font-medium">Reviewed</th></tr></thead>
            <tbody>{l.data.items.map((x) => (
              <React.Fragment key={x.id}>
                <tr className="border-t border-surface-line align-top">
                  <td className="py-1.5 pr-3"><button type="button" aria-expanded={open === x.id} onClick={() => setOpen(open === x.id ? null : x.id)} className="pex-mono text-xs text-pex-primary underline">{x.id}</button></td>
                  <td className="pr-3">{pretty(x.name)}</td>
                  <td className="pr-3"><ReviewPill status={x.status} /></td>
                  <td className="pr-3">{x.open_comments || <span className="text-pex-muted">0</span>}</td>
                  <td className="text-xs text-pex-muted">{x.reviewed_at ? `${x.reviewer_name || x.reviewer} · ${x.reviewed_at.slice(0, 10)}` : ""}</td>
                </tr>
                {open === x.id && <tr><td colSpan={5} className="py-3 border-t border-surface-line"><ReviewPanel kind={kind} id={x.id} onChange={bump} /></td></tr>}
              </React.Fragment>))}</tbody></table></div>
        )}
      </Card>
    </div>
  );
};
