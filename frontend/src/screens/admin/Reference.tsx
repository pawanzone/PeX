import React, { useMemo, useState } from "react";
import { Database, Layers, Link2, X } from "lucide-react";
import { Banner, ErrorState, Loading, StatusPill, cn } from "../../components/v2";
import { useV2 } from "../../services/v2/client";
import { getDataModel, getOntology, getSop, getSops, type SopRow } from "../../services/v2/reference";

const Card: React.FC<{ title: string; right?: React.ReactNode; children: React.ReactNode; className?: string }> = ({ title, right, children, className }) => (
  <section className={cn("bg-surface-card rounded-card border border-surface-line shadow-card p-4", className)}>
    <div className="flex items-center justify-between mb-3"><h2 className="text-base font-semibold text-pex-ink">{title}</h2>{right}</div>{children}
  </section>
);
const Wait: React.FC<{ r: { loading: boolean; error: string | null; unavailable: boolean; data: unknown; reload: () => void } }> = ({ r }) =>
  r.loading && !r.data ? <Loading /> : <ErrorState message={r.error ?? undefined} unavailable={r.unavailable} onRetry={r.reload} />;

/** Payment ontology: read only. */
export const OntologyView: React.FC = () => {
  const r = useV2(getOntology, []);
  const d = r.data;
  if (!d) return <Wait r={r} />;
  return (
    <div className="grid gap-4">
      <Banner tone="grey" title="Read only">{d.note}</Banner>
      <Card title="Six-stage governed pipeline">
        <ol className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
          {d.pipeline.map((p) => (
            <li key={p.stage_id} className="rounded-lg border border-surface-line bg-slate-50 p-3">
              <span className="w-6 h-6 rounded bg-pex-primary text-white text-xs font-semibold inline-flex items-center justify-center">{p.stage_id}</span>
              <h3 className="text-sm font-semibold mt-2">{p.name}</h3><p className="text-xs text-pex-muted mt-1">{p.description}</p>
            </li>))}
        </ol>
      </Card>
      <Card title="Canonical entities">
        <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="text-xs text-pex-muted text-left"><tr><th className="py-1.5 pr-3 font-medium">Entity</th><th className="pr-3 font-medium">Standard</th><th className="pr-3 font-medium">What it holds</th><th className="font-medium">Key fields</th></tr></thead>
          <tbody>{d.entities.map((e) => <tr key={e.name} className="border-t border-surface-line align-top"><td className="py-2 pr-3 font-semibold pex-mono text-pex-primary">{e.name}</td><td className="pr-3">{e.standard}</td><td className="pr-3 text-pex-muted">{e.description}</td><td className="pex-mono text-xs text-pex-muted">{e.key_fields.join(", ")}</td></tr>)}</tbody></table></div>
      </Card>
      <Card title="Which evidence domains each exception type reads">
        <div className="overflow-x-auto"><table className="w-full text-sm"><tbody>{d.domains.map((x) => <tr key={x.exception_type} className="border-t border-surface-line first:border-0"><td className="py-1.5 pr-3">{x.exception_type}</td><td className="text-pex-muted">{x.domain_str}</td></tr>)}</tbody></table></div>
      </Card>
    </div>
  );
};

/** Canonical database and semantic layer: read from the live models. */
export const DataModelView: React.FC = () => {
  const r = useV2(getDataModel, []);
  const [q, setQ] = useState("");
  const d = r.data;
  const tables = useMemo(() => (d?.tables ?? []).filter((t) => !q || t.name.includes(q.toLowerCase()) || t.columns.some((c) => c.name.includes(q.toLowerCase()))), [d, q]);
  if (!d) return <Wait r={r} />;
  return (
    <div className="grid gap-4">
      <Banner tone="grey" title="Read only">{d.note}</Banner>
      <Card title="Semantic layer: canonical field to ISO 20022 element" right={<StatusPill tone="grey">{d.semantic_layer.length} mappings</StatusPill>}>
        <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="text-xs text-pex-muted text-left"><tr><th className="py-1.5 pr-3 font-medium">Canonical field</th><th className="pr-3 font-medium">ISO 20022 element</th><th className="font-medium">Meaning</th></tr></thead>
          <tbody>{d.semantic_layer.map((m) => <tr key={m.canonical} className="border-t border-surface-line align-top"><td className="py-1.5 pr-3 pex-mono text-xs text-pex-primary">{m.canonical}</td><td className="pr-3 pex-mono text-xs">{m.iso20022}</td><td className="text-pex-muted">{m.description}</td></tr>)}</tbody></table></div>
      </Card>
      <Card title="Canonical models">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {d.canonical.map((m) => (
            <details key={m.name} className="rounded-lg border border-surface-line p-3"><summary className="cursor-pointer font-semibold pex-mono text-sm text-pex-primary">{m.name} <span className="text-xs font-normal text-pex-muted">· {m.fields.length} fields</span></summary>
              <ul className="mt-2 grid gap-0.5 text-xs">{m.fields.map((f) => <li key={f.name} className="flex justify-between gap-3"><span className="pex-mono">{f.name}{f.required ? "" : "?"}</span><span className="text-pex-muted truncate">{f.type}</span></li>)}</ul></details>))}
        </div>
      </Card>
      <Card title="Database tables" right={<div><label className="sr-only" htmlFor="dm-q">Filter tables or columns</label><input id="dm-q" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter tables or columns" className="py-1.5 px-2.5 text-sm rounded-lg border border-surface-line" /></div>}>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {tables.map((t) => (
            <details key={t.name} className="rounded-lg border border-surface-line p-3">
              <summary className="cursor-pointer text-sm"><Database className="w-4 h-4 inline mr-1.5 text-pex-muted" aria-hidden /><span className="pex-mono font-semibold">{t.name}</span><span className="text-xs text-pex-muted ml-2">{t.columns.length} columns{t.rows >= 0 ? ` · ${t.rows} rows` : ""}</span></summary>
              {t.description && <p className="text-xs text-pex-muted mt-1.5">{t.description}</p>}
              <ul className="mt-2 grid gap-0.5 text-xs">{t.columns.map((c) => <li key={c.name} className="flex justify-between gap-3"><span className="pex-mono">{c.primary_key ? "🔑 " : ""}{c.name}{c.references && <span className="text-pex-primary"> → {c.references}</span>}</span><span className="text-pex-muted">{c.type}</span></li>)}</ul>
            </details>))}
        </div>
      </Card>
      <Card title="Relations" right={<span className="text-xs text-pex-muted inline-flex items-center gap-1"><Link2 className="w-3.5 h-3.5" aria-hidden />{d.relations.length}</span>}>
        {d.relations.length ? <ul className="grid gap-1 text-xs pex-mono">{d.relations.map((x) => <li key={x.from}>{x.from} → {x.to}</li>)}</ul> : <p className="text-sm text-pex-muted">The tables are linked by case id and user id (logical keys), not database foreign keys.</p>}
      </Card>
    </div>
  );
};

const SopDrawer: React.FC<{ code: string; onClose: () => void }> = ({ code, onClose }) => {
  const r = useV2(() => getSop(code), [code]);
  const d = r.data;
  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="presentation" onKeyDown={(e) => e.key === "Escape" && onClose()}>
      <div className="absolute inset-0 bg-slate-900/40" onClick={onClose} aria-hidden />
      <aside role="dialog" aria-modal="true" aria-label="SOP detail" className="relative w-full max-w-2xl h-full bg-surface overflow-y-auto shadow-2xl p-5">
        <div className="flex items-start justify-between gap-3 mb-3"><div><div className="text-xs text-pex-muted">{code} · {d?.version}</div><h2 className="text-lg font-semibold">{d?.name}</h2></div><button type="button" onClick={onClose} aria-label="Close" className="p-1.5 rounded-lg hover:bg-slate-100"><X className="w-5 h-5" aria-hidden /></button></div>
        {!d ? <Wait r={r} /> : <>
          <p className="text-sm text-pex-muted mb-3">{d.standards}</p>
          <Banner tone="amber" title={d.status}>{d.note}</Banner>
          <h3 className="text-sm font-semibold mt-4 mb-2">Evidence the decision needs</h3>
          <table className="w-full text-sm"><thead className="text-xs text-pex-muted text-left"><tr><th className="py-1.5 pr-2 font-medium">Item</th><th className="pr-2 font-medium">Weight</th><th className="pr-2 font-medium">Pillar</th><th className="font-medium">System of record</th></tr></thead>
            <tbody>{d.items.map((i) => <tr key={i.name} className="border-t border-surface-line align-top"><td className="py-1.5 pr-2">{i.name}{i.gate && <span className="ml-1.5"><StatusPill tone="amber" dot={false}>gate</StatusPill></span>}</td><td className="pr-2 pex-mono">{i.weight}</td><td className="pr-2 text-pex-muted">{i.pillar} {i.pillar_name}</td><td className="text-pex-muted">{i.system_name}</td></tr>)}</tbody></table>
        </>}
      </aside>
    </div>
  );
};

/** SOP list: one row per exception profile. Seeded from the framework until the bank supplies its own. */
export const SopsView: React.FC = () => {
  const r = useV2(getSops, []);
  const [fam, setFam] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const d = r.data;
  if (!d) return <Wait r={r} />;
  const fams = Array.from(new Set(d.items.map((x) => x.family)));
  const rows: SopRow[] = d.items.filter((x) => !fam || x.family === fam);
  return (
    <div className="grid gap-4">
      <Banner tone="grey" title="Framework defaults">{d.note}</Banner>
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filter by family">
        <button type="button" onClick={() => setFam("")} aria-pressed={!fam} className={cn("px-2.5 py-1 rounded-md text-xs border", !fam ? "bg-pex-primary text-white border-pex-primary" : "bg-white border-surface-line text-pex-muted")}>All {d.total}</button>
        {fams.map((f) => <button key={f} type="button" onClick={() => setFam(f)} aria-pressed={fam === f} className={cn("px-2.5 py-1 rounded-md text-xs border", fam === f ? "bg-pex-primary text-white border-pex-primary" : "bg-white border-surface-line text-pex-muted")}>{f}</button>)}
      </div>
      <Card title="Standard operating procedures" right={<span className="text-xs text-pex-muted inline-flex items-center gap-1"><Layers className="w-3.5 h-3.5" aria-hidden />{rows.length}</span>}>
        <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="text-xs text-pex-muted text-left"><tr><th className="py-1.5 pr-3 font-medium">Code</th><th className="pr-3 font-medium">Exception type</th><th className="pr-3 font-medium">Standards basis</th><th className="pr-3 font-medium">Evidence</th><th className="pr-3 font-medium">Version</th><th className="font-medium">Owner</th></tr></thead>
          <tbody>{rows.map((s) => (
            <tr key={s.code} className="border-t border-surface-line hover:bg-slate-50 cursor-pointer" onClick={() => setOpen(s.code)}>
              <td className="py-2 pr-3"><button type="button" className="pex-mono text-pex-primary hover:underline" onClick={(e) => { e.stopPropagation(); setOpen(s.code); }}>{s.code}</button></td><td className="pr-3">{s.name}</td><td className="pr-3 text-xs text-pex-muted max-w-md truncate" title={s.standards}>{s.standards}</td>
              <td className="pr-3 pex-mono">{s.evidence_items}{s.gate_items ? <span className="text-xs text-pex-muted"> ({s.gate_items} gate)</span> : null}</td><td className="pr-3">{s.version}</td><td className="text-pex-muted">{s.owner}</td></tr>))}</tbody></table></div>
      </Card>
      {open && <SopDrawer code={open} onClose={() => setOpen(null)} />}
    </div>
  );
};
