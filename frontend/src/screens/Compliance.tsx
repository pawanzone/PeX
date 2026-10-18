import React from "react";
import { PageHeader, Banner, DataTable, StatusPill, ErrorState, Loading, CountdownText, Tile } from "../components/v2";
import { useV2 } from "../services/v2/client";
import { getComplianceQueue, type ComplianceQueueRow } from "../services/v2/compliance";
import { navigate, routes } from "../lib/router";
import { useSession } from "../shell/session";
import { hhmm } from "./compliance/fmt";
import { ComplianceCase } from "./compliance/ComplianceCase";

/** Compliance workspace. Queue + case page. Design: 10_compliance_hold.png.
 *  Compliance holds offer NO repair actions: decisions only (release / confirm match / escalate). */
export const Compliance: React.FC<{ id?: string }> = ({ id }) => (id ? <ComplianceCase id={id} /> : <Queue />);

const Queue: React.FC = () => {
  const { epoch } = useSession();
  const q = useV2(getComplianceQueue, [epoch]);
  const rows = q.data?.items ?? [];
  const holds = rows.filter((r) => (r.status || "").toUpperCase().includes("HOLD") || !r.status).length;
  return (
    <>
      <PageHeader title="Compliance" subtitle="Screening holds and potential matches. The bank screening system remains the system of record." />
      <Banner tone="grey" title="Simulated screening">Alerts come from a simulated bank screening system. No real sanctions list is contacted.</Banner>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 my-4">
        <Tile label="In queue" value={q.data?.total ?? rows.length} tone="amber" />
        <Tile label="Open holds" value={holds} tone="red" />
        <Tile label="Other status" value={Math.max(0, rows.length - holds)} tone="grey" />
      </div>
      <div className="bg-surface-card rounded-card border border-surface-line shadow-card p-2">
        {q.loading ? <Loading /> : q.error ? <ErrorState unavailable={q.unavailable} message={q.error} onRetry={q.reload} /> : (
          <DataTable<ComplianceQueueRow>
            caption="Compliance queue" rows={rows} rowKey={(r) => r.case_id}
            onRowClick={(r) => navigate(routes.complianceCase(r.case_id))}
            emptyTitle="No compliance cases" emptyHint="Nothing is waiting for a compliance decision."
            columns={[
              { key: "cut", header: "Cutoff", render: (r) => r.cutoff?.at ? <CountdownText iso={r.cutoff.at} /> : <span className="text-pex-muted">{r.cutoff?.time_left ?? "—"}</span> },
              { key: "id", header: "Case", mono: true, render: (r) => <a className="text-pex-primary hover:underline" href={routes.complianceCase(r.case_id)} onClick={(e) => e.stopPropagation()}>{r.case_id}</a> },
              { key: "ex", header: "Exception", render: (r) => r.exception?.label ?? "Screening alert" },
              { key: "amt", header: "Amount", align: "right", mono: true, render: (r) => r.amount?.display ?? "—" },
              { key: "cp", header: "Party", render: (r) => r.counterparty ?? "—" },
              { key: "ref", header: "Alert", mono: true, render: (r) => r.screening_ref ?? "—" },
              { key: "raised", header: "Raised", render: (r) => hhmm(r.raised_at) || "—" },
              { key: "st", header: "Status", render: (r) => <StatusPill tone={(r.status || "").toUpperCase().includes("ESCAL") ? "purple" : "red"}>{r.status ? r.status.replace(/_/g, " ").toLowerCase().replace(/^./, (c) => c.toUpperCase()) : "Compliance hold"}</StatusPill> },
            ]}
          />
        )}
      </div>
    </>
  );
};
