import React, { useRef, useState } from "react";
import { Check, X, Undo2, Paperclip } from "lucide-react";
import { Banner, ConfirmCheckbox, Modal, ReasonCommentFields, Section, cn } from "./reexports";
import type { ActionResult, CaseAction, DecisionForm, CasePage } from "../../services/v2/case";
import { returnCase, rejectCase, approveCase, submitCase, escalateCase, uploadAttachment, removeAttachment, ATTACH_ACCEPT, ATTACH_MAX_BYTES, type AttachmentMeta } from "../../services/v2/case";

export type Run = (fn: () => Promise<ActionResult>, doneText?: string) => Promise<ActionResult | undefined>;

const field = "py-2 px-2.5 text-sm rounded-lg border border-surface-line bg-white text-pex-ink w-full";
const primaryBtn = "px-4 py-2 text-sm font-medium rounded-lg bg-pex-primary text-white hover:bg-pex-primary-dark disabled:opacity-50 disabled:cursor-not-allowed";
const plainBtn = "px-4 py-2 text-sm font-medium rounded-lg bg-white border border-surface-line text-pex-ink hover:bg-slate-50";

// ------------------------------------------------------------ maker submit (handover note required)
export const SubmitModal: React.FC<{ caseId: string; run: Run; onClose: () => void }> = ({ caseId, run, onClose }) => {
  const [note, setNote] = useState("");
  const [file, setFile] = useState<AttachmentMeta | null>(null);
  const [upBusy, setUpBusy] = useState(false);
  const [upErr, setUpErr] = useState<string | null>(null);
  const pick = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const ok = note.trim().length > 0;
  const choose = async (f: File | undefined) => {
    if (!f) return;
    setUpErr(null);
    if (f.size > ATTACH_MAX_BYTES) { setUpErr("This file is larger than 5 MB."); return; }
    setUpBusy(true);
    try { setFile(await uploadAttachment(caseId, f)); } catch (e) { setUpErr(e instanceof Error ? e.message : "The file could not be uploaded."); }
    setUpBusy(false);
    if (pick.current) pick.current.value = "";
  };
  const drop = async () => { if (!file) return; const id = file.id; setFile(null); try { await removeAttachment(caseId, id); } catch { /* a leftover file is harmless: it is not tied to anything */ } };
  return (
    <Modal open title="Submit for approval" onClose={onClose} width="md"
      footer={<>
        <button className={plainBtn} onClick={onClose}>Cancel</button>
        <button className={primaryBtn} disabled={!ok || busy || upBusy} onClick={async () => { setBusy(true); const r = await run(() => submitCase(caseId, note.trim(), file?.id), "Submitted for approval"); setBusy(false); if (r) onClose(); }}>Submit for approval</button>
      </>}>
      <div className="grid gap-4">
        <p className="text-sm text-pex-muted">The approver sees this note with the evidence. A different person must approve: you cannot approve your own repair.</p>
        <label className="grid gap-1 text-xs text-pex-muted">Handover note (required)
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={4} className={field} placeholder="What did you verify, and with whom?" />
        </label>
        <div className="grid gap-1 text-xs text-pex-muted">
          <span className="flex items-center gap-1"><Paperclip className="w-3 h-3" aria-hidden />Attachment (optional)</span>
          <input ref={pick} id="submit-attachment" type="file" accept={ATTACH_ACCEPT} className="sr-only" onChange={(e) => void choose(e.target.files?.[0])} />
          {file ? (
            <div className="flex items-center gap-2 rounded-lg border border-surface-line bg-slate-50 px-2.5 py-2 text-sm text-pex-ink">
              <Paperclip className="w-4 h-4 shrink-0" aria-hidden /><span className="truncate">{file.name}</span>
              <span className="text-xs text-pex-muted shrink-0">{file.size < 1024 * 1024 ? Math.max(1, Math.round(file.size / 1024)) + " KB" : (file.size / 1024 / 1024).toFixed(1) + " MB"} · fingerprint {file.sha256.slice(0, 8)}</span>
              <button type="button" className="ml-auto text-pex-primary text-xs font-medium" onClick={() => void drop()}>Remove</button>
            </div>
          ) : (
            <button type="button" className={plainBtn + " justify-self-start inline-flex items-center gap-2"} disabled={upBusy} onClick={() => pick.current?.click()}>
              <Paperclip className="w-4 h-4" aria-hidden />{upBusy ? "Uploading…" : "Choose a file"}
            </button>
          )}
          <span>PDF, image, text, CSV, Word or Excel. Up to 5 MB. The approver can open it; each open is recorded.</span>
          {upErr && <span role="alert" className="text-pex-block">{upErr}</span>}
        </div>
        {!ok && <p className="text-xs text-pex-wait">A handover note is required before you can submit.</p>}
      </div>
    </Modal>
  );
};

// ------------------------------------------------------------ escalate
export const EscalateModal: React.FC<{ caseId: string; run: Run; onClose: () => void }> = ({ caseId, run, onClose }) => {
  const [to, setTo] = useState("SENIOR_ANALYST");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <Modal open title="Escalate case" onClose={onClose} width="md"
      footer={<>
        <button className={plainBtn} onClick={onClose}>Cancel</button>
        <button className={primaryBtn} disabled={!reason.trim() || busy} onClick={async () => { setBusy(true); const r = await run(() => escalateCase(caseId, to, reason.trim()), "Escalated"); setBusy(false); if (r) onClose(); }}>Escalate</button>
      </>}>
      <div className="grid gap-4">
        <label className="grid gap-1 text-xs text-pex-muted">Escalate to
          <select value={to} onChange={(e) => setTo(e.target.value)} className={field}>
            <option value="SENIOR_ANALYST">Senior analyst</option><option value="SUPERVISOR">Supervisor</option><option value="APPROVER">Approver</option>
          </select>
        </label>
        <label className="grid gap-1 text-xs text-pex-muted">Reason (required)
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} className={field} />
        </label>
      </div>
    </Modal>
  );
};

// ------------------------------------------------------------ checker decision panel (design 08)
const DEFAULT_RETURN = [{ code: "EVIDENCE_INSUFFICIENT", label: "Evidence insufficient" }, { code: "NEEDS_CLARIFICATION", label: "Needs clarification" }];
const DEFAULT_REJECT = [{ code: "NOT_JUSTIFIED", label: "Repair not justified" }, { code: "RISK_TOO_HIGH", label: "Risk too high" }];

export const DecisionPanel: React.FC<{
  page: CasePage; form: DecisionForm | null | undefined; actions: CaseAction[]; run: Run; onDone?: () => void;
}> = ({ page, form, actions, run, onDone }) => {
  const id = page.case_id;
  const [reviewed, setReviewed] = useState(false);
  const [aComment, setAComment] = useState("");
  const [rtReason, setRtReason] = useState(""); const [rtComment, setRtComment] = useState("");
  const [rjReason, setRjReason] = useState(""); const [rjComment, setRjComment] = useState("");
  const [busy, setBusy] = useState(false);
  const act = (k: string) => actions.find((a) => a.key === k);
  const approve = act("approve"), ret = act("return"), rej = act("reject");
  const approveBlocked = approve ? approve.enabled === false : false;
  const needAck = form?.requires_review_ack !== false;
  const returnReasons = (form?.return_reason_codes?.length ? form.return_reason_codes : DEFAULT_RETURN).map((r) => ({ value: r.code, label: r.label }));
  const rejectReasons = (form?.reject_reason_codes?.length ? form.reject_reason_codes : DEFAULT_REJECT).map((r) => ({ value: r.code, label: r.label }));
  const go = async (fn: () => Promise<ActionResult>, text: string) => { setBusy(true); const r = await run(fn, text); setBusy(false); if (r) onDone?.(); };
  const canApprove = !busy && !approveBlocked && (!needAck || reviewed);
  const ackOk = !needAck || reviewed;
  const canReturn = !busy && ackOk && ret?.enabled !== false && !!rtReason && !!rtComment.trim();
  const canReject = !busy && ackOk && rej?.enabled !== false && !!rjReason && !!rjComment.trim();
  return (
    <Section title="Your decision" hint={form?.dual_auth ? "Dual authorisation: a second, different approver is also required." : undefined}>
      <ConfirmCheckbox id="reviewed-ack" checked={reviewed} onChange={setReviewed}>I have reviewed the change summary and evidence</ConfirmCheckbox>
      <div className="grid gap-5 mt-4 lg:grid-cols-[1fr_1fr_1fr]">
        <div className="grid gap-2 content-start">
          <button className={cn("px-4 py-2.5 text-sm font-semibold rounded-lg inline-flex items-center justify-center gap-2 bg-pex-ok text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed")}
            disabled={!canApprove} onClick={() => go(() => approveCase(id, true, aComment.trim()), "Approved for bank handoff")}>
            <Check className="w-4 h-4" aria-hidden />Approve for bank handoff
          </button>
          <label className="grid gap-1 text-xs text-pex-muted">Comment (optional)
            <textarea value={aComment} onChange={(e) => setAComment(e.target.value)} rows={2} className={field} />
          </label>
          <p className="text-xs text-pex-muted">{form?.footnote ?? "Next: handed to bank system. Not yet executed."}</p>
          {approveBlocked && <p className="text-xs text-pex-block">{approve?.disabled_reason ?? "You cannot approve this case."}</p>}
          {!approveBlocked && needAck && !reviewed && <p className="text-xs text-pex-wait">Tick the review box to enable approval.</p>}
        </div>
        <div className="grid gap-2 content-start">
          <button className="px-4 py-2.5 text-sm font-semibold rounded-lg inline-flex items-center justify-center gap-2 bg-white border border-pex-wait/60 text-pex-wait hover:bg-pex-wait-soft disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={!canReturn} onClick={() => go(() => returnCase(id, true, rtReason, rtComment.trim()), "Returned to maker")}>
            <Undo2 className="w-4 h-4" aria-hidden />Return to Maker
          </button>
          <ReasonCommentFields reasons={returnReasons} reason={rtReason} onReason={setRtReason} comment={rtComment} onComment={setRtComment} required reasonLabel="Reason code (required)" commentLabel="Comment (required)" />
          {ret?.enabled === false && <p className="text-xs text-pex-block">{ret.disabled_reason}</p>}
          {ret?.enabled !== false && !ackOk && <p className="text-xs text-pex-wait">Tick the review box to enable this.</p>}
        </div>
        <div className="grid gap-2 content-start">
          <button className="px-4 py-2.5 text-sm font-semibold rounded-lg inline-flex items-center justify-center gap-2 bg-white border border-pex-block/50 text-pex-block hover:bg-pex-block-soft disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={!canReject} onClick={() => go(() => rejectCase(id, true, rjReason, rjComment.trim()), "Rejected")}>
            <X className="w-4 h-4" aria-hidden />Reject
          </button>
          <ReasonCommentFields reasons={rejectReasons} reason={rjReason} onReason={setRjReason} comment={rjComment} onComment={setRjComment} required reasonLabel="Reason code (required)" commentLabel="Comment (required)" />
          {rej?.enabled === false && <p className="text-xs text-pex-block">{rej.disabled_reason}</p>}
          {rej?.enabled !== false && !ackOk && <p className="text-xs text-pex-wait">Tick the review box to enable this.</p>}
        </div>
      </div>
    </Section>
  );
};
