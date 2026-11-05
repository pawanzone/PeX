import React, { useMemo, useState } from "react";
import { Database, Layers, Link2, X } from "lucide-react";
import { Banner, ErrorState, Loading, StatusPill, cn } from "../../components/v2";
import { useV2 } from "../../services/v2/client";
import { getDataModel, getOntology, getSop, getSops, type DataModel, type SopRow } from "../../services/v2/reference";

export const Card: React.FC<{ title: string; right?: React.ReactNode; children: React.ReactNode; className?: string }> = ({ title, right, children, className }) => (
  <section className={cn("min-w-0 bg-surface-card rounded-card border border-surface-line shadow-card p-4", className)}>
    <div className="flex items-center justify-between mb-3"><h2 className="text-base font-semibold text-pex-ink">{title}</h2>{right}</div>{children}
  </section>
);
export const Wait: React.FC<{ r: { loading: boolean; error: string | null; unavailable: boolean; data: unknown; reload: () => void } }> = ({ r }) =>
  r.loading && !r.data ? <Loading /> : <ErrorState message={r.error ?? undefined} unavailable={r.unavailable} onRetry={r.reload} />;

/** Payment ontology: read only. */
export const OntologyView: React.FC = () => {
  const r = useV2(getOntology, []);
  const d = r.data;
  if (!d) return <Wait r={r} />;
  return (
    <div className="grid grid-cols-1 gap-4 min-w-0">
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
        <p className="text-sm text-pex-muted mb-3">Each key field shows where the canonical data model holds it, or the canonical fields it is worked out from. The paths are checked against the code, so this page cannot name a field the model does not have.</p>
        <div className="grid gap-3 lg:grid-cols-2">
          {d.entities.map((e) => (
            <div key={e.name} className="rounded-lg border border-surface-line p-3 min-w-0">
              <div className="flex flex-wrap items-baseline justify-between gap-2"><span className="font-semibold pex-mono text-pex-primary">{e.name}</span><span className="text-xs text-pex-muted">{e.standard}</span></div>
              <p className="text-xs text-pex-muted mt-1">{e.description}</p>
              {e.source_note && <p className="text-xs mt-1 text-pex-muted"><b>Source:</b> {e.source_note}</p>}
              {e.logical_entity && <p className="text-xs mt-1 text-pex-muted"><b>Canonical entity:</b> {e.logical_entity}</p>}
              <div className="overflow-x-auto mt-2"><table className="w-full text-xs"><caption className="sr-only">{e.name} key fields and their canonical home</caption>
                <thead className="text-pex-muted text-left"><tr><th className="py-1 pr-2 font-medium">Field</th><th className="pr-2 font-medium">Held as</th><th className="font-medium">Canonical field</th></tr></thead>
                <tbody>{(e.fields ?? e.key_fields.map((k) => ({ name: k, kind: "unmapped" as const, home: null, derived_from: [], in_code: false }))).map((f) => (
                  <tr key={f.name} className="border-t border-surface-line align-top">
                    <td className="py-1 pr-2 pex-mono">{f.name}</td>
                    <td className="pr-2 whitespace-nowrap"><StatusPill tone={f.kind === "canonical" ? "green" : f.kind === "derived" ? "blue" : "grey"} dot={false}>{f.kind === "canonical" ? "stored" : f.kind === "derived" ? "derived" : "not mapped"}</StatusPill></td>
                    <td className="pex-mono text-pex-muted break-words">{f.home ?? (f.derived_from.length ? f.derived_from.join(", ") : "—")}</td></tr>))}</tbody></table></div>
            </div>))}
        </div>
      </Card>
      <Card title="Which evidence domains each exception type reads">
        <div className="overflow-x-auto"><table className="w-full text-sm"><tbody>{d.domains.map((x) => <tr key={x.exception_type} className="border-t border-surface-line first:border-0"><td className="py-1.5 pr-3">{x.exception_type}</td><td className="text-pex-muted">{x.domain_str}</td></tr>)}</tbody></table></div>
      </Card>
    </div>
  );
};

const CLASS_TONE: Record<string, "red" | "amber" | "blue" | "grey"> = { C1: "red", C2: "amber", C3: "red", C4: "blue", C5: "grey" };
export const Stat: React.FC<{ label: string; value: React.ReactNode; hint?: string }> = ({ label, value, hint }) => (
  <div className="rounded-xl bg-slate-50 px-3 py-2"><div className="text-xl font-semibold text-pex-ink">{value}</div><div className="text-xs text-pex-muted">{label}</div>{hint && <div className="text-[11px] text-pex-muted mt-0.5">{hint}</div>}</div>
);

/** Semantic layer: generated from the real models and profile packs (meaning is curated; coverage is computed and tested). */
const SemanticLayer: React.FC<{ d: DataModel }> = ({ d: raw }) => {
  // Tolerate an older backend that only returns the first-generation semantic layer (restart the backend to get the full one).
  const d: DataModel = { ...raw, evidence_catalogue: raw.evidence_catalogue ?? [], element_catalogue: raw.element_catalogue ?? [],
    semantic_layer: (raw.semantic_layer ?? []).map((m) => ({ ...m, mt: m.mt ?? "", validation: m.validation ?? "", data_class: m.data_class ?? "C5", pex_internal: !!m.pex_internal })),
    semantic_summary: raw.semantic_summary ?? { canonical_fields_total: raw.semantic_layer?.length ?? 0, canonical_fields_mapped: raw.semantic_layer?.length ?? 0, iso_mapped_fields: raw.semantic_layer?.length ?? 0, evidence_types: 0, profiles: 0, element_gaps: 0, iso_messages: [], categories: {}, data_classes: {} } };
  const stale = !raw.semantic_summary;
  const [tab, setTab] = useState<"fields" | "evidence" | "elements">("fields");
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const s = d.semantic_summary;
  const has = (...v: Array<string | undefined>) => !q || v.some((x) => (x ?? "").toLowerCase().includes(q.toLowerCase()));
  const fields = d.semantic_layer.filter((m) => has(m.canonical, m.iso20022, m.mt, m.description));
  const ev = d.evidence_catalogue.filter((e) => (!cat || e.category === cat) && has(e.type, e.label, e.source_system, e.proves, e.used_by.map((u) => u.code).join(" ")));
  const el = d.element_catalogue.filter((e) => has(e.element, e.message, e.mt, e.why, e.used_by.join(" ")));
  const tabs: Array<["fields" | "evidence" | "elements", string, number]> = [["fields", "Canonical fields", d.semantic_layer.length], ["evidence", "Evidence sources", d.evidence_catalogue.length], ["elements", "Message elements", d.element_catalogue.length]];
  const th = "py-1.5 pr-3 font-medium whitespace-nowrap";
  return (
    <Card title="Semantic layer" right={<div><label className="sr-only" htmlFor="sl-q">Filter the semantic layer</label><input id="sl-q" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter, for example IBAN, DQ-02, sanctions" className="py-1.5 px-2.5 text-sm rounded-lg border border-surface-line w-80" /></div>}>
      {stale && <div className="mb-3"><Banner tone="amber" title="Backend needs a restart">This page is newer than the running backend, so only the basic field list is shown. Stop and start the backend to see the full semantic layer.</Banner></div>}
      <p className="text-sm text-pex-muted mb-3">What each piece of payment data means: its ISO 20022 element and SWIFT MT equivalent, how it is validated, how sensitive it is, and which of the {s.profiles} exception profiles rely on it. Generated from the live models and profile packs, so it cannot drift; a test fails if any evidence a profile asks for is missing here.</p>
      <div className="grid gap-2 grid-cols-2 md:grid-cols-4 xl:grid-cols-6 mb-4">
        <Stat label="Canonical fields mapped" value={`${s.canonical_fields_mapped} of ${s.canonical_fields_total}`} hint={`${s.iso_mapped_fields} to ISO elements`} />
        <Stat label="Evidence sources" value={s.evidence_types} hint={`${Object.keys(s.categories).length} categories`} />
        <Stat label="Exception profiles" value={s.profiles} />
        <Stat label="ISO message types" value={s.iso_messages.length} hint={s.iso_messages.join(", ")} />
        <Stat label="Message elements carried" value={`${s.elements_covered ?? d.element_catalogue.filter((e) => e.in_canonical_model).length} of ${s.elements_total ?? d.element_catalogue.length}`} hint={`${s.element_gaps} still to add`} />
        <Stat label="Data classes" value={Object.keys(s.data_classes).length} hint="C1 personal to C5 operational" />
      </div>
      <div role="tablist" aria-label="Semantic layer views" className="flex flex-wrap gap-1 mb-3">
        {tabs.map(([id, label, n]) => (
          <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)} className={cn("px-3 py-1.5 text-sm rounded-full", tab === id ? "bg-pex-primary-soft text-pex-primary font-medium" : "text-slate-600 hover:bg-slate-100")}>{label} <span className="text-xs text-pex-muted">{n}</span></button>))}
      </div>
      {tab === "fields" && (
        <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Canonical fields</caption>
          <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Canonical field</th><th className={th}>ISO 20022 element</th><th className={th}>SWIFT MT</th><th className={th}>Validation</th><th className={th}>Class</th><th className="font-medium">Meaning</th></tr></thead>
          <tbody>{fields.map((m) => <tr key={m.canonical} className="border-t border-surface-line align-top">
            <td className="py-1.5 pr-3 pex-mono text-xs text-pex-primary">{m.canonical}</td><td className="pr-3 pex-mono text-xs">{m.iso20022}</td><td className="pr-3 text-xs">{m.mt}</td>
            <td className="pr-3 text-xs">{m.validation}</td><td className="pr-3"><StatusPill tone={CLASS_TONE[m.data_class]} dot={false}>{m.data_class}</StatusPill></td><td className="text-pex-muted">{m.description}</td></tr>)}</tbody></table>
          {!fields.length && <p className="text-sm text-pex-muted py-3">Nothing matches the filter.</p>}</div>)}
      {tab === "evidence" && (
        <>
          <div className="flex flex-wrap gap-1 mb-3" role="group" aria-label="Evidence category">
            <button aria-pressed={!cat} onClick={() => setCat("")} className={cn("px-2.5 py-1 text-xs rounded-full border", !cat ? "bg-pex-primary-soft border-pex-primary text-pex-primary" : "border-surface-line text-slate-600")}>All {d.evidence_catalogue.length}</button>
            {Object.entries(s.categories).map(([c, n]) => <button key={c} aria-pressed={cat === c} onClick={() => setCat(cat === c ? "" : c)} className={cn("px-2.5 py-1 text-xs rounded-full border", cat === c ? "bg-pex-primary-soft border-pex-primary text-pex-primary" : "border-surface-line text-slate-600")}>{c} {n}</button>)}
          </div>
          <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Evidence sources</caption>
            <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Evidence</th><th className={th}>Category</th><th className={th}>Comes from</th><th className="pr-3 font-medium">What it proves</th><th className={th}>ISO</th><th className={th}>Class</th><th className="font-medium">Used by (trust tier)</th></tr></thead>
            <tbody>{ev.map((e) => <tr key={e.type} className="border-t border-surface-line align-top">
              <td className="py-1.5 pr-3 pex-mono text-xs text-pex-primary">{e.type}</td><td className="pr-3 text-xs whitespace-nowrap">{e.category}</td><td className="pr-3 text-xs">{e.source_system}</td><td className="pr-3">{e.proves}</td>
              <td className="pr-3 text-xs whitespace-nowrap">{e.iso_messages}</td><td className="pr-3"><StatusPill tone={CLASS_TONE[e.data_class]} dot={false}>{e.data_class}</StatusPill></td>
              <td className="text-xs">{e.used_by.map((u) => <span key={u.code} title={`${u.name} · trust tier ${u.tier} (1 = core record, 4 = advisory)`} className="inline-block mr-1.5 pex-mono">{u.code}<span className="text-pex-muted"> T{u.tier}</span></span>)}</td></tr>)}</tbody></table>
            {!ev.length && <p className="text-sm text-pex-muted py-3">Nothing matches the filter.</p>}</div>
        </>)}
      {tab === "elements" && (
        <>
          <p className="text-sm text-pex-muted mb-2">Message elements that profiles read from the payload, and where the canonical model now carries each one. Elements marked "Not yet carried" are listed openly so gaps are visible, not hidden.</p>
          <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Message elements and where the canonical model carries them</caption>
            <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Element</th><th className={th}>Message</th><th className={th}>SWIFT MT</th><th className={th}>Carried in</th><th className={th}>Class</th><th className="pr-3 font-medium">Why PeX needs it</th><th className="font-medium">Profiles</th></tr></thead>
            <tbody>{el.map((e) => <tr key={e.element + e.message} className="border-t border-surface-line align-top">
              <td className="py-1.5 pr-3 pex-mono text-xs text-pex-primary">{e.element}</td><td className="pr-3 text-xs whitespace-nowrap">{e.message}</td><td className="pr-3 text-xs">{e.mt}</td>
              <td className="pr-3 text-xs whitespace-nowrap">{e.canonical_home ? <span className="pex-mono">{e.canonical_home}</span> : <StatusPill tone="amber" dot={false}>Not yet carried</StatusPill>}</td>
              <td className="pr-3"><StatusPill tone={CLASS_TONE[e.data_class]} dot={false}>{e.data_class}</StatusPill></td><td className="pr-3">{e.why}</td><td className="text-xs pex-mono">{e.used_by.join(" ")}</td></tr>)}</tbody></table>
            {!el.length && <p className="text-sm text-pex-muted py-3">Nothing matches the filter.</p>}</div>
        </>)}
    </Card>
  );
};


const STATUS_TONE: Record<string, "green" | "amber" | "grey"> = { "in code": "green", "database only": "amber", planned: "grey" };

/** The logical canonical model: business entities by domain. Status is computed from the code, so it cannot overstate what exists. */
const LogicalModelCard: React.FC<{ lm?: DataModel["logical_model"] }> = ({ lm }) => {
  if (!lm) return null;
  const s = lm.summary;
  return (
    <Card title="Canonical data model" right={<span className="text-xs text-pex-muted">{s.entities} entities · {s.in_code} in code · {s.database_only} database only · {s.planned} planned</span>}>
      <p className="text-sm text-pex-muted mb-3">The business entities PeX reasons about, grouped by domain. Each is marked <b>in code</b> (a real model in the code; ISO 20022 messages and bank events fill it, except mandate and screening alert, which wait for a bank feed), <b>database only</b> (held in a table, no canonical model yet) or <b>planned</b>. The status is read from the code, so it cannot claim more than exists.</p>
      <div className="grid gap-4">
        {lm.domains.map((dom) => (
          <div key={dom}>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-pex-muted mb-2">{dom}</h3>
            <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {lm.entities.filter((e) => e.domain === dom).map((e) => (
                <div key={e.name} className="rounded-lg border border-surface-line p-3 min-w-0">
                  <div className="flex items-center justify-between gap-2"><span className="font-semibold text-sm text-pex-ink">{e.name}</span><StatusPill tone={STATUS_TONE[e.status]} dot={false}>{e.status}</StatusPill></div>
                  <p className="text-xs text-pex-muted mt-1">{e.description}</p>
                  <div className="text-xs mt-2 flex flex-wrap gap-x-3 gap-y-0.5 text-pex-muted">
                    <span className="pex-mono">{e.iso_anchor}</span>
                    {e.canonical_class && <span className="pex-mono text-pex-primary">{e.canonical_class} · {e.fields} fields</span>}
                    {e.db_table && <span className="pex-mono">table {e.db_table}</span>}
                  </div>
                  {e.links.length > 0 && <div className="text-xs mt-1.5 text-pex-muted">{e.links.map((l) => `${l.label} → ${l.to}`).join(" · ")}</div>}
                </div>))}
            </div>
          </div>))}
      </div>
    </Card>
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
      <LogicalModelCard lm={d.logical_model} />
      <SemanticLayer d={d} />
      <Card title="Canonical model classes (fields)">
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
