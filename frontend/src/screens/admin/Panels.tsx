import React, { useState } from "react";
import { Banner, DataTable, Loading, ErrorState, StatusPill, FilterBar, FilterSelect } from "../../components/v2";
import { useV2 } from "../../services/v2/client";
import { getRoles, getPolicies, getExceptionTypes } from "../../services/v2/admin";
import { useSession } from "../../shell/session";

const Head: React.FC<{ title: string; sub?: string }> = ({ title, sub }) => (
  <div className="mb-4"><h2 className="text-2xl font-semibold text-pex-ink tracking-tight">{title}</h2>{sub && <p className="text-sm text-pex-muted mt-1">{sub}</p>}</div>
);
const Card: React.FC<{ children: React.ReactNode; title?: string }> = ({ children, title }) => (
  <section className="bg-surface-card rounded-card border border-surface-line shadow-card p-4 mb-4">{title && <h3 className="text-base font-semibold text-pex-ink mb-3">{title}</h3>}{children}</section>
);
const money = (n?: number | string) => (typeof n === "number" ? (n >= 1e6 ? `${(n / 1e6).toLocaleString()}M` : n.toLocaleString()) : n ?? "—");

export const RolesPanel: React.FC = () => {
  const { epoch } = useSession();
  const r = useV2(getRoles, [epoch]);
  if (r.loading && !r.data) return <Loading />;
  if (r.error || !r.data) return <ErrorState unavailable={r.unavailable} message={r.error ?? undefined} onRetry={r.reload} />;
  return (
    <>
      <Head title="Roles and permissions" sub="Read only. Roles come from the demo personas; the server enforces every permission." />
      <Card title="Roles">
        <DataTable rows={r.data.roles} rowKey={(x) => x.role} caption="Roles" columns={[
          { key: "r", header: "Role", render: (x) => <span className="font-medium">{x.label ?? x.role}<span className="block pex-mono text-[11px] font-normal text-pex-muted">{x.role}</span></span> },
          { key: "p", header: "Permissions", render: (x) => <span className="flex flex-wrap gap-1">{(x.permissions ?? []).map((p) => <span key={p} className="pex-mono text-[11px] px-1.5 py-0.5 rounded bg-slate-100">{p}</span>)}</span> },
          { key: "l", header: "Approval limit", align: "right", mono: true, render: (x) => (x.approval_limit ? money(x.approval_limit) : "—") },
          { key: "u", header: "People", render: (x) => (x.users ?? []).map((u) => u.name).join(", ") || "—" },
        ]} />
      </Card>
      {!!r.data.authority_matrix?.length && (
        <Card title="Authority matrix">
          <DataTable rows={r.data.authority_matrix} rowKey={(x) => x.role} caption="Authority matrix" columns={[
            { key: "r", header: "Role", render: (x) => x.role },
            { key: "l", header: "Limit", mono: true, align: "right", render: (x) => money(x.limit) },
            { key: "c", header: "Can", render: (x) => (x.can ?? []).join(", ") || "—" },
          ]} />
        </Card>
      )}
    </>
  );
};

export const PoliciesPanel: React.FC = () => {
  const { epoch } = useSession();
  const r = useV2(getPolicies, [epoch]);
  if (r.loading && !r.data) return <Loading />;
  if (r.error || !r.data) return <ErrorState unavailable={r.unavailable} message={r.error ?? undefined} onRetry={r.reload} />;
  const rules = r.data.rules ?? [];
  return (
    <>
      <Head title="Policies" sub="Thresholds that decide who must approve and what may be handed to the bank without manual repair." />
      <Card title="Thresholds">
        <DataTable rows={r.data.thresholds} rowKey={(x) => x.key} caption="Policy thresholds" columns={[
          { key: "l", header: "Policy", render: (x) => x.label ?? x.key },
          { key: "v", header: "Value", mono: true, render: (x) => (typeof x.value === "number" ? `${money(x.value)}${x.currency ? " " + x.currency : ""}` : String(x.value ?? "—")) },
          { key: "e", header: "Change", render: (x) => x.editable ? <StatusPill tone="blue">Editable</StatusPill> : <StatusPill tone="grey" dot={false}>Set by configuration</StatusPill> },
        ]} />
        <p className="text-xs text-pex-muted mt-2">The limit is set with an environment setting on the server in this build. It cannot be edited here.</p>
      </Card>
      <Card title={`Rules (${rules.length})`}>
        {!rules.length ? <div className="text-sm text-pex-muted">No rules returned. The rules studio remains under Reference screens.</div> : (
          <DataTable rows={rules.slice(0, 50)} rowKey={(x: any) => String(x.rule_id ?? x.id ?? x.name ?? JSON.stringify(x).slice(0, 40))} caption="Rules" columns={[
            { key: "i", header: "Rule", mono: true, render: (x: any) => x.rule_id ?? x.id ?? "—" },
            { key: "n", header: "Name", render: (x: any) => x.name ?? x.title ?? x.description ?? "—" },
            { key: "s", header: "Status", render: (x: any) => String(x.status ?? x.enabled ?? "—") },
          ]} />
        )}
      </Card>
    </>
  );
};

export const ExceptionTypesPanel: React.FC = () => {
  const { epoch } = useSession();
  const r = useV2(getExceptionTypes, [epoch]);
  const [domain, setDomain] = useState("");
  const [q, setQ] = useState("");
  if (r.loading && !r.data) return <Loading />;
  if (r.error || !r.data) return <ErrorState unavailable={r.unavailable} message={r.error ?? undefined} onRetry={r.reload} />;
  const domains = Array.from(new Set(r.data.items.map((i) => i.domain).filter(Boolean))) as string[];
  const rows = r.data.items.filter((i) => (!domain || i.domain === domain) && (!q || `${i.code} ${i.label}`.toLowerCase().includes(q.toLowerCase())));
  return (
    <>
      <Head title="Exception types" sub={`${r.data.total} types. STP permissible means a validated micro-repair may be approved in a batch.`} />
      <Banner tone="grey">Compliance and sanctions types are never STP permissible.</Banner>
      <FilterBar search={{ value: q, onChange: setQ, placeholder: "Search code or name" }}>
        <FilterSelect label="Domain" value={domain} onChange={setDomain} options={[{ value: "", label: "All" }, ...domains.map((d) => ({ value: d, label: d.replace(/_/g, " ").toLowerCase().replace(/^./, (c) => c.toUpperCase()) }))]} />
      </FilterBar>
      <Card>
        <DataTable rows={rows} rowKey={(x) => x.code} caption="Exception types" emptyTitle="No exception types match" columns={[
          { key: "c", header: "Code", mono: true, render: (x) => x.code },
          { key: "l", header: "Name", render: (x) => x.label ?? "—" },
          { key: "d", header: "Domain", render: (x) => (x.domain ?? "—").replace(/_/g, " ") },
          { key: "q", header: "Queue", render: (x) => x.queue ?? "—" },
          { key: "s", header: "STP", render: (x) => x.stp_permissible ? <StatusPill tone="green">Permissible</StatusPill> : <span title={x.stp_note ?? undefined}><StatusPill tone="grey" dot={false}>Not permissible</StatusPill></span> },
          { key: "o", header: "Open cases", align: "right", render: (x) => x.open_cases ?? 0 },
        ]} />
      </Card>
    </>
  );
};
