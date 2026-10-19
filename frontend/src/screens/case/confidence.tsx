import React, { useState } from "react";
import { ShieldCheck, ShieldAlert } from "lucide-react";
import { Banner, StatusPill, cn } from "../../components/v2";
import { Section } from "./parts";
import type { Run } from "./forms";
import type { CasePage } from "../../services/v2/case";
import { postCaseAction } from "../../services/v2/case";

const field = "py-2 px-2.5 text-sm rounded-lg border border-surface-line bg-white text-pex-ink w-full";
const primaryBtn = "px-4 py-2 text-sm font-medium rounded-lg bg-pex-primary text-white hover:bg-pex-primary-dark disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2";
const SRC: Record<string, string> = { B: "Bank event", A: "Bank system (API)", X: "External" };
const STATE: Record<string, { tone: "green" | "amber" | "red" | "grey"; label: string }> = {
  PRESENT: { tone: "green", label: "Present" }, MISSING: { tone: "amber", label: "Missing" }, STALE: { tone: "amber", label: "Stale" }, CONFLICT: { tone: "red", label: "Conflict" },
};

/** Decision confidence and evidence coverage for the case (rules-based; used by the 85% approval gate). */
export const ConfidenceBlock: React.FC<{ page: CasePage; run: Run }> = ({ page, run }) => {
  const c = page.confidence;
  const [comment, setComment] = useState("");
  const [open, setOpen] = useState(false);
  if (!c) return null;
  const low = c.extra_approval;
  const rv = c.review;
  const pct = Math.max(0, Math.min(100, c.confidence_pct));
  return (
    <Section id="confidence" title="Decision confidence"
      hint={`${c.profile.replace(/_/g, " ").toLowerCase()} · ${c.family_name} · threshold ${c.threshold}%`}
      right={<StatusPill tone={low ? "amber" : "green"}>{c.label}</StatusPill>}>
      <div className="grid gap-4 sm:grid-cols-[11rem_1fr] items-start">
        <div>
          <div className={cn("text-4xl font-semibold tabular-nums", low ? "text-amber-700" : "text-emerald-700")}>{Math.round(c.confidence_pct)}%</div>
          <div className="text-xs text-pex-muted mt-1">Evidence coverage {Math.round(c.coverage_pct)}%</div>
          <div className="relative h-2 rounded-full bg-slate-100 mt-3" role="img" aria-label={`Confidence ${Math.round(pct)} percent, threshold ${c.threshold} percent`}>
            <div className={cn("h-2 rounded-full", low ? "bg-amber-500" : "bg-emerald-600")} style={{ width: `${pct}%` }} />
            <div className="absolute -top-1 h-4 w-0.5 bg-pex-ink" style={{ left: `${c.threshold}%` }} title={`Threshold ${c.threshold}%`} />
          </div>
          <div className="text-[11px] text-pex-muted mt-1">| marks {c.threshold}%</div>
        </div>
        <div className="grid gap-1.5">
          {Object.entries(c.pillars).map(([k, p]) => (
            <div key={k} className="grid grid-cols-[1fr_3rem_9rem] gap-2 items-center text-sm">
              <span>{p.name}<span className="text-xs text-pex-muted"> · weight {p.weight}</span></span>
              <span className="tabular-nums text-right">{p.score_pct}%</span>
              <span className="h-1.5 rounded-full bg-slate-100"><span className={cn("block h-1.5 rounded-full", p.score_pct >= 100 ? "bg-emerald-600" : p.score_pct > 0 ? "bg-amber-500" : "bg-red-500")} style={{ width: `${p.score_pct}%` }} /></span>
            </div>
          ))}
          {c.penalty_pct > 0 && <div className="text-sm text-red-700">Ambiguity penalty −{c.penalty_pct}%</div>}
        </div>
      </div>

      {low && (
        <div className="mt-4">
          <Banner tone="amber" title="Extra approval required">
            {c.reasons.join(". ")}. A second person reviews the evidence first; a different approver then authorises the handoff.
          </Banner>
        </div>
      )}

      {rv?.state === "pending" && (
        <div className="mt-3 rounded-lg border border-surface-line p-3 grid gap-2">
          <div className="text-sm font-semibold flex items-center gap-2"><ShieldAlert className="w-4 h-4 text-amber-600" aria-hidden />Evidence review pending</div>
          {rv.can_review ? (
            <>
              <label className="text-sm" htmlFor="cr-comment">What did you check? (required)</label>
              <textarea id="cr-comment" rows={2} className={field} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="For example: directory record and invoice checked, name matches." />
              <div><button type="button" className={primaryBtn} disabled={!comment.trim()}
                onClick={() => void run(() => postCaseAction(page.case_id, "confidence-review", { decision: "confirm", comment }), "Evidence review recorded")}>Confirm evidence review</button>
                <span className="text-xs text-pex-muted ml-3">This does not approve the payment. To send it back, use Return to Maker below.</span></div>
            </>
          ) : <p className="text-sm text-pex-muted">Waiting for an approver (not the maker) to review the evidence.</p>}
        </div>
      )}
      {rv?.state === "confirmed" && (
        <div className="mt-3 text-sm flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-emerald-700" aria-hidden />
          Evidence reviewed by {rv.reviewed_by?.name ?? "a reviewer"}. “{rv.comment}” A different approver must authorise.</div>
      )}

      <button type="button" className="mt-3 text-sm text-pex-primary underline" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? "Hide" : "Show"} evidence used ({c.items.length})</button>
      {open && (
        <div className="mt-2 overflow-x-auto rounded-lg border border-surface-line">
          <table className="w-full text-sm">
            <caption className="sr-only">Evidence items, source and weight</caption>
            <thead><tr className="text-left text-xs text-pex-muted bg-slate-50 border-b border-surface-line">{["Evidence", "Source", "Weight", "State"].map((h) => <th key={h} scope="col" className="py-2 px-3 font-medium">{h}</th>)}</tr></thead>
            <tbody>{c.items.map((i) => {
              const s = STATE[i.state] ?? STATE.MISSING;
              return (
                <tr key={i.name} className="border-b border-surface-line last:border-0">
                  <td className="py-2 px-3">{i.name}{i.gate && <span className="ml-2 text-[11px] text-pex-muted">must have</span>}</td>
                  <td className="py-2 px-3"><span className="text-xs text-pex-muted">{SRC[i.source_class]} · </span>{i.source}</td>
                  <td className="py-2 px-3 tabular-nums">{i.weight}</td>
                  <td className="py-2 px-3"><StatusPill tone={s.tone}>{s.label}</StatusPill></td>
                </tr>);
            })}</tbody>
          </table>
          <p className="text-xs text-pex-muted p-2">Standards basis: {c.standards}</p>
        </div>
      )}
    </Section>
  );
};
