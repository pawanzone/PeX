import React, { useState } from "react";
import { Avatar, Empty, ErrorState, Loading, Tabs } from "../../components/v2";
import { useV2 } from "../../services/v2/client";
import { getTimeline } from "../../services/v2/dossier";
import type { CasePage } from "../../services/v2/case";
import { EvidenceBlock, HandoverNote, RecommendationBlock } from "./blocks";
import { AiSeen } from "./pii";
import { fmtDateTime } from "./parts";

const Timeline: React.FC<{ caseId: string }> = ({ caseId }) => {
  const r = useV2(() => getTimeline(caseId), [caseId]);
  if (r.loading && !r.data) return <Loading />;
  if (r.error || !r.data) return <ErrorState message={r.error ?? undefined} unavailable={r.unavailable} onRetry={r.reload} />;
  if (!r.data.items.length) return <Empty title="No events recorded yet" />;
  return (
    <ol className="grid gap-0" aria-label="Case audit trail">
      {r.data.items.map((e) => (
        <li key={e.id} className="flex gap-3 py-2.5 border-b border-surface-line last:border-0">
          <Avatar bare size="md" name={e.actor} role={e.role} system={/system/i.test(e.role || "")} initials={/system/i.test(e.role || "") ? "PX" : undefined} />
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline justify-between gap-3"><span className="text-sm font-medium text-pex-ink">{e.event}</span><span className="text-xs text-pex-muted whitespace-nowrap">{fmtDateTime(e.time)}</span></div>
            <div className="text-xs text-pex-muted">{e.actor} · {e.role}</div>
            {e.detail && <div className="text-sm text-pex-ink mt-0.5">{e.detail}</div>}
          </div>
        </li>
      ))}
    </ol>
  );
};

/** Tabs under the decision zone, so the decision and what it rests on are in view without scrolling the whole page. */
export const CaseTabs: React.FC<{ page: CasePage; confidence?: React.ReactNode }> = ({ page, confidence }) => {
  const evCount = page.evidence_table?.length ?? 0;
  const hasAi = !!page.recommendation || !!confidence;
  const tabs = [
    ...(evCount ? [{ id: "evidence", label: "Evidence", count: evCount }] : []),
    ...(page.handover ? [{ id: "handover", label: "Maker handover note" }] : []),
    ...(hasAi ? [{ id: "ai", label: "AI view and reasoning" }] : []),
    { id: "audit", label: "Audit trail", count: page.journey?.audit_events },
  ];
  const [tab, setTab] = useState(tabs[0].id);
  const cur = tabs.some((t) => t.id === tab) ? tab : tabs[0].id;
  return (
    <section className="bg-surface-card rounded-card border border-surface-line shadow-card" aria-label="Case detail">
      <div className="px-3 pt-1"><Tabs tabs={tabs} value={cur} onChange={setTab} label="Case detail" /></div>
      <div role="tabpanel" className="p-4">
        {cur === "evidence" && <EvidenceBlock page={page} bare />}
        {cur === "handover" && page.handover && <HandoverNote h={page.handover} />}
        {cur === "ai" && <div className="grid gap-4"><RecommendationBlock page={page} />{confidence}<AiSeen page={page} /></div>}
        {cur === "audit" && <Timeline caseId={page.case_id} />}
      </div>
    </section>
  );
};
