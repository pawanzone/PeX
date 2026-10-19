import React, { useCallback, useEffect, useRef, useState } from "react";
import { Play, MessageSquare, ArrowUp, Phone, RefreshCw, Mail, Send, Check, Lock } from "lucide-react";
import { ActionBar, Banner, Breadcrumbs, CaseHeader, CaseJourney, ErrorState, Loading, Modal, useToast } from "../../components/v2";
import type { ActionDef } from "../../components/v2";
import { navigate, routes } from "../../lib/router";
import { useSession } from "../../shell/session";
import { areaAllowed } from "../../shell/nav";
import { useV2 } from "../../services/v2";
import { getCasePage, postCaseAction, actionPath } from "../../services/v2/case";
import type { ActionResult, CaseAction, CasePage as CasePageDto } from "../../services/v2/case";
import { BannerFromApi, chipTone, errText, journeyVariant, mapJourney } from "./parts";
import { BankBlock, ChangeBlock, ConflictBlock, DecisionBrief, EvidenceBlock, HandoverNote, NeededBlock, ReassessBlock, RequestInfoForm, StatusUnknownBlock } from "./blocks";
import type { SendHandle } from "./blocks";
import { DecisionPanel, EscalateModal, SubmitModal } from "./forms";
import { ConfidenceBlock } from "./confidence";

const ICONS: Record<string, React.ElementType> = {
  submit: Play, request_information: MessageSquare, send_request: Send, escalate: ArrowUp, start_verification: Phone, check_status: RefreshCw,
  reassess: RefreshCw, request_bank_status: Mail, approve: Check, prepare_repair: Lock,
};
const DECISION_KEYS = ["approve", "return", "reject"];

/** One case page for every variant. `context` only changes the breadcrumb root. */
export const CasePage: React.FC<{ id: string; context?: "worklist" | "approvals"; onChanged?: () => void }> = ({ id, context = "worklist", onChanged }) => {
  const r = useV2(() => getCasePage(id), [id]);
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [modal, setModal] = useState<null | "submit" | "escalate" | "reqinfo">(null);
  const sendHandle = useRef<SendHandle | null>(null);
  const page = r.data;
  const { persona } = useSession();
  // Roles that cannot open Compliance (e.g. makers) stay on this page: banner + journey, repair actions disabled by the server.
  const toCompliance = areaAllowed("compliance", persona?.role);

  const run = useCallback(async (fn: () => Promise<ActionResult>, doneText?: string): Promise<ActionResult | undefined> => {
    setBusy(true); setErr(null);
    try {
      const res = await fn();
      toast.push(res?.message ?? (res?.result ? `Result: ${String(res.result).replace(/_/g, " ").toLowerCase()}` : doneText ?? "Done"), "green");
      r.reload(); onChanged?.();
      return res ?? ({} as ActionResult);
    } catch (e) {
      const m = errText(e); setErr(m); toast.push(m, "red");
      return undefined;
    } finally { setBusy(false); }
  }, [toast, r, onChanged]);

  // Compliance holds are worked in the Compliance area (no repair actions are offered here).
  useEffect(() => { if (page?.variant === "COMPLIANCE_HOLD" && toCompliance) navigate(routes.complianceCase(id)); }, [page?.variant, id, toCompliance]);

  const actions = page?.actions ?? [];
  const find = (k: string) => actions.find((a) => a.key === k);
  const canWork = !!find("check_status") || actions.some((a) => a.enabled !== false && ["submit", "request_information", "reassess", "start_verification", "escalate"].includes(a.key));

  const doAction = (key: string) => {
    const a = find(key);
    if (a?.enabled === false) return;
    switch (key) {
      case "submit": setModal("submit"); return;
      case "escalate": setModal("escalate"); return;
      case "request_information": case "send_request":
        if (page?.variant === "MISSING_INFO" && sendHandle.current) sendHandle.current.send(); else setModal("reqinfo");
        return;
      case "approve": case "return": case "reject":
        document.getElementById("decision-panel")?.scrollIntoView({ behavior: "smooth", block: "center" }); return;
      default:
        void run(() => postCaseAction(id, a ? actionPath(a) : key.replace(/_/g, "-"), key === "reassess" || key === "start_verification" || key === "request_bank_status" ? { note: null } : {}), a?.label);
    }
  };

  const crumbs = [{ label: context === "approvals" ? "Approvals" : "Worklist", href: context === "approvals" ? routes.approvals() : routes.worklist() }, { label: id }];

  if (r.loading && !page) return <><Breadcrumbs items={crumbs} /><Loading label="Loading case…" /></>;
  if (r.error || !page) return <><Breadcrumbs items={crumbs} /><ErrorState message={r.error ?? "Case not found"} unavailable={r.unavailable} onRetry={r.reload} /></>;
  if (page.variant === "COMPLIANCE_HOLD" && toCompliance) return <><Breadcrumbs items={crumbs} /><Loading label="Opening in Compliance…" /></>;

  const v = page.variant;
  const h = page.header ?? {};
  const j = mapJourney(page);
  const amt = h.amount;
  const hasDecisionPanel = v === "APPROVAL" && (!!page.decision_form || actions.some((a) => DECISION_KEYS.includes(a.key)));

  const bar: ActionDef[] = actions
    .filter((a: CaseAction) => !(hasDecisionPanel && DECISION_KEYS.includes(a.key)))
    .map((a) => ({
      id: a.key, label: a.label, kind: a.kind ?? "secondary", icon: ICONS[a.key],
      disabled: a.enabled === false || busy, disabledReason: a.enabled === false ? a.disabled_reason ?? "Not available" : undefined,
      onClick: () => doAction(a.key),
    }));

  const ev = <EvidenceBlock page={page} />;
  const conf = page.confidence && page.confidence.applies ? <ConfidenceBlock page={page} run={run} /> : null;
  const showChange = !!page.change_summary;

  return (
    <div>
      <div className="mb-3"><Breadcrumbs items={crumbs} /></div>
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_22rem] items-start">
        <div className="grid gap-4 min-w-0">
          <CaseHeader id={page.case_id} chips={(h.chips ?? []).map((c) => ({ label: c.label, tone: chipTone(c.tone) }))}
            amount={amt?.amount !== undefined ? amt.amount.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : amt?.display}
            currency={amt?.amount !== undefined ? amt.currency : undefined}
            cutoff={h.cutoff?.at} cutoffLabel={h.cutoff?.hhmm ? `Cutoff ${h.cutoff.hhmm} UTC` : "Cutoff"}
            meta={[
              ...(h.uetr ? [{ label: "UETR", value: <span className="pex-mono text-xs break-all">{h.uetr}</span> }] : []),
              ...(h.rail?.label ? [{ label: "Rail", value: h.rail.label }] : []),
              ...(h.creditor ? [{ label: "Creditor", value: h.creditor }] : []),
              ...(h.assignee?.name ? [{ label: "Assigned to", value: h.assignee.name }] : []),
            ]} />
          {err && <Banner tone="red" title="That did not go through">{err}</Banner>}
          <BannerFromApi banner={page.banner} />

          {(v === "DECISION" || v === "GENERIC") && page.decision_brief && <DecisionBrief brief={page.decision_brief} />}
          {v === "DECISION" && <>{showChange && <ChangeBlock page={page} mode="decision" />}{page.handover && <HandoverNote h={page.handover} />}{ev}{conf}</>}
          {v === "APPROVAL" && <>
            {showChange && <ChangeBlock page={page} mode="approval" />}
            {page.handover && <HandoverNote h={page.handover} />}
            {ev}
            {conf}
            {hasDecisionPanel && <div id="decision-panel"><DecisionPanel page={page} form={page.decision_form} actions={actions} run={run} /></div>}
          </>}
          {v === "MISSING_INFO" && <>
            {page.needed && <NeededBlock needed={page.needed} />}
            <RequestInfoForm caseId={id} info={page.request_information} run={run} handle={sendHandle} />
            <ReassessBlock caseId={id} run={run} enabled={find("reassess")?.enabled !== false && !!find("reassess")} reason={find("reassess")?.disabled_reason ?? "Available once information is received."} />
          </>}
          {v === "CONFLICT" && <>
            {page.conflict && <ConflictBlock c={page.conflict} caseId={id} onAction={doAction} run={run} canWork={canWork} />}
            {!!page.evidence_table?.length && ev}
          </>}
          {v === "STATUS_UNKNOWN" && page.status_unknown && <StatusUnknownBlock s={page.status_unknown} blocked={page.blocked_actions ?? []} onAction={doAction} canWork={!!find("check_status") && find("check_status")?.enabled !== false} busy={busy} />}
          {(v === "HANDED_TO_BANK" || v === "EXECUTED") && <>
            <BankBlock page={page} />
            {showChange && <ChangeBlock page={page} mode="approval" />}
            {page.handover && <HandoverNote h={page.handover} />}
            {ev}
            {conf}
          </>}
          {v === "GENERIC" && <>{showChange && <ChangeBlock page={page} mode="decision" />}{ev}</>}
        </div>
        <div className="lg:sticky lg:top-4">
          <CaseJourney steps={j.steps} variant={journeyVariant(v)} tone={j.tone} nextAction={j.next}
            auditCount={page.journey?.audit_events} onViewAudit={() => navigate(routes.audit({ case_id: id }))} />
        </div>
      </div>

      {bar.length > 0 && <ActionBar actions={bar} />}

      {modal === "submit" && <SubmitModal caseId={id} run={run} onClose={() => setModal(null)} />}
      {modal === "escalate" && <EscalateModal caseId={id} run={run} onClose={() => setModal(null)} />}
      {modal === "reqinfo" && (
        <Modal open title="Request information" onClose={() => setModal(null)} width="lg">
          <RequestInfoForm embedded caseId={id} info={page.request_information ?? { to: { party: h.creditor }, message: `Please confirm the missing details for payment ${id}.` }} run={run} onDone={() => setModal(null)} />
        </Modal>
      )}
    </div>
  );
};
