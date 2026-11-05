import React, { useState } from "react";
import { Copy } from "lucide-react";
import { Banner, StatusPill, cn } from "../../components/v2";
import { useV2 } from "../../services/v2/client";
import { getContract, getContractProfile, type ContractEvidence, type HowKey } from "../../services/v2/reference";
import { Card, Stat, Wait } from "./Reference";

const th = "py-1.5 pr-3 font-medium whitespace-nowrap";
const HOW_TONE: Record<HowKey, "grey" | "green" | "amber" | "blue"> = { BANK_SENDS: "grey", PEX_LOOKUP_COMPUTED: "green", PEX_LOOKUP_SIMULATED: "amber", COULD_LOOK_UP: "blue" };
const MODE_SHORT: Record<string, string> = { MODE_1_INBOUND_PAYLOAD: "In the event", MODE_2_API_CONNECTOR: "PeX looks up", MODE_3_BANK_PUSH: "Bank pushes later", MODE_4_HITL_OPERATOR: "Person enters" };
const FIELD_ARR = (xs: string[]) => xs.map((x) => <span key={x} className="pex-mono text-xs rounded-md border border-surface-line px-1.5 py-0.5">{x}</span>);

const HowPill: React.FC<{ e: ContractEvidence }> = ({ e }) => (
  <div>
    <StatusPill tone={HOW_TONE[e.how]} dot={false}>{e.how_label}</StatusPill>
    {e.lookup && <div className="text-[11px] text-pex-muted mt-1 max-w-[16rem]">{e.lookup.source}. As of: {e.lookup.as_of}. Input: <span className="pex-mono">{e.lookup.params.join(", ")}</span></div>}
  </div>
);

const copy = async (text: string) => { try { await navigator.clipboard.writeText(text); } catch { /* clipboard may be refused; the text stays selectable */ } };

/** One profile: everything a bank's event must carry, and how PeX gets each item. Shown inside the profile drawer. */
export const ContractSection: React.FC<{ code: string }> = ({ code }) => {
  const r = useV2(() => getContractProfile(code), [code]);
  const d = r.data;
  const [show, setShow] = useState(false);
  if (!d) return <Wait r={r} />;
  const json = d.sample ? JSON.stringify(d.sample.event, null, 2) : "";
  return (
    <section aria-label="Inbound event" className="grid gap-3">
      <div>
        <h3 className="font-semibold">Inbound event: what the bank sends</h3>
        <p className="text-pex-muted text-sm">{d.counts.mandatory} must-have and {d.counts.optional} optional evidence items. PeX can look up {d.counts.lookups_built} of {d.counts.total}; the bank sends {d.counts.bank_sends}.</p>
      </div>
      <div className="text-sm grid gap-1.5">
        <div><span className="text-pex-muted">Every event needs: </span><span className="inline-flex flex-wrap gap-1 align-middle">{FIELD_ARR(d.payment_fields.always_required)}</span></div>
        {!!d.payment_fields.used_in_sample.length && <div><span className="text-pex-muted">Also used for this exception type: </span><span className="inline-flex flex-wrap gap-1 align-middle">{FIELD_ARR(d.payment_fields.used_in_sample)}</span></div>}
        <p className="text-xs text-pex-muted">{d.payment_fields.note}</p>
      </div>
      <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Evidence the event carries and how PeX gets each item</caption>
        <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Evidence (key in the event)</th><th className={th}>Need</th><th className={th}>Trust tier</th><th className={th}>How PeX gets it</th><th className="font-medium">Comes from</th></tr></thead>
        <tbody>{d.evidence.map((e) => (
          <tr key={e.type} className="border-t border-surface-line align-top">
            <td className="py-1.5 pr-3"><span className="pex-mono text-xs text-pex-primary">{e.event_key}</span><div className="text-pex-muted text-xs max-w-[22rem]">{e.meaning}</div></td>
            <td className="pr-3">{e.mandatory ? <StatusPill tone="blue" dot={false}>Must have</StatusPill> : <span className="text-xs text-pex-muted">Optional</span>}</td>
            <td className="pr-3 whitespace-nowrap">T{e.tier} <span className="text-xs text-pex-muted">{e.tier_name}</span><div className="text-[11px] text-pex-muted">fresh for {e.freshness_hours}h</div></td>
            <td className="pr-3"><HowPill e={e} /></td>
            <td className="text-xs text-pex-muted">{e.source_system}</td>
          </tr>))}</tbody></table></div>
      <div>
        {d.sample ? (
          <>
            <div className="flex items-center gap-2 flex-wrap">
              <button type="button" aria-expanded={show} onClick={() => setShow((s) => !s)} className="px-3 py-1.5 text-sm rounded-lg border border-surface-line bg-white">{show ? "Hide" : "Show"} sample event</button>
              {show && <button type="button" onClick={() => copy(json)} className="px-3 py-1.5 text-sm rounded-lg border border-surface-line bg-white inline-flex items-center gap-1.5"><Copy className="w-4 h-4" aria-hidden />Copy</button>}
              <span className="text-xs text-pex-muted">Synthetic test data from <span className="pex-mono">{d.sample.file}</span>. It runs through the real pipeline in the tests.</span>
            </div>
            {show && <pre className="mt-2 text-xs pex-mono rounded-lg bg-slate-50 border border-surface-line p-3 overflow-x-auto max-h-96">{json}</pre>}
          </>
        ) : <p className="text-sm text-pex-muted">{d.sample_note}</p>}
      </div>
    </section>
  );
};

const KIND: Record<string, string> = { COMPUTED: "Computed from published rules", SIMULATED_DIRECTORY: "Simulated directory" };

/** Overview for the bank's integration team: envelope, delivery, acquisition modes, lookups and coverage. */
export const ContractView: React.FC = () => {
  const r = useV2(getContract, []);
  const d = r.data;
  if (!d) return <Wait r={r} />;
  const by = d.evidence_summary.by_how;
  const built = (by.PEX_LOOKUP_COMPUTED ?? 0) + (by.PEX_LOOKUP_SIMULATED ?? 0);
  return (
    <div className="grid grid-cols-1 gap-4 min-w-0">
      <Banner tone="blue" title="Integration contract">{d.rule}</Banner>
      <div className="grid gap-2 grid-cols-1 sm:grid-cols-4">
        <Stat label="Exception types" value={d.profiles} hint="each has its own contract" />
        <Stat label="Evidence types in total" value={d.evidence_summary.distinct_types} hint={`${d.evidence_summary.shared_by_two_or_more} are used by more than one type`} />
        <Stat label="PeX can look up" value={built} hint={`${by.PEX_LOOKUP_COMPUTED ?? 0} computed · ${by.PEX_LOOKUP_SIMULATED ?? 0} simulated`} />
        <Stat label="Sent by the bank" value={by.BANK_SENDS ?? 0} hint={`${by.COULD_LOOK_UP ?? 0} more could be looked up later`} />
      </div>
      <Card title="Every event needs">
        <p className="text-sm text-pex-muted mb-2">These fields are enough for PeX to accept an event. Missing evidence does not reject it: the case goes to a person.</p>
        <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Payment fields</caption>
          <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Payment field</th><th className={th}>Need</th><th className="font-medium">Meaning</th></tr></thead>
          <tbody>{d.envelope.payment_fields.map((f) => <tr key={f.field} className="border-t border-surface-line align-top"><td className="py-1.5 pr-3 pex-mono text-xs">{f.field}</td><td className="pr-3">{f.required ? <StatusPill tone="blue" dot={false}>Must have</StatusPill> : <span className="text-xs text-pex-muted">Optional</span>}</td><td className="text-pex-muted">{f.meaning}</td></tr>)}</tbody></table></div>
        <h4 className="font-medium mt-4 mb-1 text-sm">Where evidence goes in the event</h4>
        <ul className="text-sm grid gap-1">{d.envelope.evidence_groups.map((g) => <li key={g.field}><span className="pex-mono text-xs">{g.field}</span> <span className="text-pex-muted">{g.meaning}</span></li>)}</ul>
      </Card>
      <Card title="How evidence reaches PeX">
        <ul className="grid gap-2 sm:grid-cols-2">{d.modes.map((m) => <li key={m.mode} className="rounded-lg border border-surface-line p-2.5 text-sm"><div className="font-medium">{MODE_SHORT[m.mode]}</div><div className="text-pex-muted text-xs">{m.meaning}</div></li>)}</ul>
      </Card>
      <Card title="Sending events">
        <div className="grid gap-3 md:grid-cols-2">{([d.delivery.single, d.delivery.batch] as const).map((x) => (
          <div key={x.title} className="rounded-lg border border-surface-line p-3 text-sm grid gap-1.5 content-start">
            <div className="font-semibold">{x.title}</div>
            <div><span className="text-pex-muted">Shape: </span>{x.shape}</div>
            <ul className="list-disc pl-5 text-pex-muted">{x.channels.map((c) => <li key={c}>{c}</li>)}</ul>
            <div><span className="text-pex-muted">PeX returns: </span>{x.answer}</div>
            {"outcomes" in x && <div className="flex flex-wrap gap-1">{FIELD_ARR(x.outcomes)}</div>}
          </div>))}</div>
      </Card>
      <Card title="What PeX can look up itself">
        <p className="text-sm text-pex-muted mb-2">Computed lookups use a published rule. Simulated ones answer from a small seeded sample table, not the real directory. None is used in the live case flow yet.</p>
        <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Lookups PeX can run</caption>
          <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Lookup</th><th className={th}>Kind</th><th className={th}>Based on</th><th className={th}>As of</th><th className="font-medium">Input</th></tr></thead>
          <tbody>{d.lookups.map((l) => <tr key={l.evidence_type} className="border-t border-surface-line align-top"><td className="py-1.5 pr-3">{l.name}<div className="pex-mono text-xs text-pex-muted">{l.evidence_type}</div></td><td className="pr-3"><StatusPill tone={l.kind === "COMPUTED" ? "green" : "amber"} dot={false}>{KIND[l.kind]}</StatusPill></td><td className="pr-3 text-pex-muted">{l.source}</td><td className="pr-3 text-xs text-pex-muted">{l.as_of}</td><td className="pex-mono text-xs">{l.params.join(", ")}</td></tr>)}</tbody></table></div>
      </Card>
      <Card title="Coverage by exception type">
        <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Evidence needed and how it arrives, for each exception type</caption>
          <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Code</th><th className={th}>Exception type</th><th className={th}>Must have</th><th className={th}>Total</th><th className={th}>PeX looks up</th><th className={th}>Could look up</th><th className={th}>Bank sends</th><th className="font-medium">Sample</th></tr></thead>
          <tbody>{d.coverage.map((c) => <tr key={c.code} className="border-t border-surface-line"><td className="py-1.5 pr-3 pex-mono text-xs text-pex-primary">{c.code}</td><td className="pr-3">{c.name.replace(/_/g, " ").toLowerCase().replace(/^./, (x) => x.toUpperCase())}</td><td className="pr-3">{c.mandatory}</td><td className="pr-3">{c.total}</td><td className={cn("pr-3", c.lookups_built ? "text-emerald-700 font-medium" : "text-pex-muted")}>{c.lookups_built}</td><td className="pr-3 text-pex-muted">{c.could_look_up}</td><td className="pr-3">{c.bank_sends}</td><td className="text-xs">{c.has_sample ? "Yes" : <span className="text-pex-muted">Not yet</span>}</td></tr>)}</tbody></table></div>
      </Card>
      <p className="text-xs text-pex-muted">{d.validation_status}.</p>
    </div>
  );
};
