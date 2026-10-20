import React, { useState } from "react";
import { ShieldCheck, Eye, EyeOff } from "lucide-react";
import { Modal } from "../../components/v2";
import type { Run } from "./forms";
import type { CasePage } from "../../services/v2/case";
import { postCaseAction } from "../../services/v2/case";

const field = "py-2 px-2.5 text-sm rounded-lg border border-surface-line bg-white text-pex-ink w-full";
const primaryBtn = "px-4 py-2 text-sm font-medium rounded-lg bg-pex-primary text-white hover:bg-pex-primary-dark disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2";
const plainBtn = "px-3 py-1.5 text-sm font-medium rounded-lg bg-white border border-surface-line text-pex-primary hover:bg-slate-50 inline-flex items-center gap-2";
const hhmm = (iso?: string | null) => (iso ? new Date(iso).toISOString().slice(11, 16) : "");

/** Personal data (names, IBANs, accounts) is shown as tokens. Authorised roles can reveal real values for a short, logged window. */
export const PiiBar: React.FC<{ page: CasePage; run: Run }> = ({ page, run }) => {
  const p = page.pii;
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  if (!p || !p.masking) return null;
  const revealed = !p.protected;
  return (
    <>
      <div className={"rounded-lg border px-3 py-2 text-sm flex items-center gap-3 flex-wrap " + (revealed ? "border-amber-300 bg-amber-50" : "border-surface-line bg-slate-50")} role="status">
        {revealed ? <Eye className="w-4 h-4 text-amber-700" aria-hidden /> : <ShieldCheck className="w-4 h-4 text-emerald-700" aria-hidden />}
        <span className="flex-1 min-w-[16rem]">
          {revealed
            ? <>Real values are showing until <strong>{hhmm(p.revealed_until)} UTC</strong>. Your access is logged.</>
            : <>Personal data is protected. Names, IBANs and accounts show as tokens (TOK-…).</>}
        </span>
        {revealed
          ? <button type="button" className={plainBtn} onClick={() => void run(() => postCaseAction(page.case_id, "pii/hide", {}), "Hidden")}><EyeOff className="w-4 h-4" aria-hidden />Hide now</button>
          : p.can_reveal
            ? <button type="button" className={plainBtn} onClick={() => setOpen(true)}><Eye className="w-4 h-4" aria-hidden />Reveal real values</button>
            : <span className="text-xs text-pex-muted">Your role cannot reveal personal data.</span>}
      </div>
      {open && (
        <Modal open title="Reveal personal data" onClose={() => setOpen(false)} width="lg">
          <div className="grid gap-3">
            <p className="text-sm text-pex-muted">Real names, IBANs and account numbers will show for {p.reveal_minutes} minutes on this case, for you only. Who, when and why is recorded in the audit trail.</p>
            <label className="text-sm font-medium" htmlFor="pii-reason">Why do you need to see them?</label>
            <textarea id="pii-reason" rows={3} className={field} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="For example: confirming the beneficiary against invoice INV-2291." />
            <div className="flex justify-end gap-2">
              <button type="button" className={plainBtn} onClick={() => setOpen(false)}>Cancel</button>
              <button type="button" className={primaryBtn} disabled={reason.trim().length < (p.min_reason_length ?? 10)}
                onClick={async () => { const r = await run(() => postCaseAction(page.case_id, "pii/reveal", { reason }), "Revealed"); if (r) { setOpen(false); setReason(""); } }}>Reveal</button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
};
