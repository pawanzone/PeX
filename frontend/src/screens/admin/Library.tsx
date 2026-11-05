import React, { useMemo, useState } from "react";
import { X } from "lucide-react";
import { Banner, StatusPill, cn } from "../../components/v2";
import { useV2 } from "../../services/v2/client";
import { getControls, getLibrary, getLibraryProfile, type LibRow } from "../../services/v2/reference";
import { Card, Stat, Wait } from "./Reference";
import { ContractSection, ContractView } from "./Contract";

const STP_TONE: Record<string, "green" | "amber" | "red"> = { ALLOWED: "green", POLICY_GATED: "amber", NEVER: "red" };
const STP_LABEL: Record<string, string> = { ALLOWED: "May go straight through", POLICY_GATED: "Bank opt-in", NEVER: "Never straight through" };
const OUTCOME_LABEL: Record<string, string> = { REPAIR: "Repair", DECISION_SUPPORT: "Decision support", INVESTIGATION: "Investigation" };
const APPROVAL_LABEL: Record<string, string> = { MAKER_CHECKER: "Maker-checker", COMPLIANCE_THEN_RISK: "Compliance then risk", SINGLE: "Single approver" };
const EFFECT_TONE: Record<string, "green" | "red" | "amber" | "blue"> = { PROCEED: "green", STOP: "red", ESCALATE: "amber", HOLD: "blue" };
const th = "py-1.5 pr-3 font-medium whitespace-nowrap";
const ACR = new Set(["AML", "PEP", "KYC", "BIC", "IBAN", "FX", "STP", "SLA", "ISO", "UETR", "SSI", "ID"]);
const pretty = (s: string) => s.replace(/_/g, " ").toLowerCase().split(" ").map((w, i) => (ACR.has(w.toUpperCase()) ? w.toUpperCase() : i === 0 ? w.replace(/^./, (c) => c.toUpperCase()) : w)).join(" ");
const Chip: React.FC<{ on: boolean; onClick: () => void; children: React.ReactNode }> = ({ on, onClick, children }) => (
  <button type="button" aria-pressed={on} onClick={onClick} className={cn("px-2.5 py-1 rounded-md text-xs border", on ? "bg-pex-primary text-white border-pex-primary" : "bg-white border-surface-line text-pex-muted")}>{children}</button>);

const ProfileDrawer: React.FC<{ code: string; onClose: () => void }> = ({ code, onClose }) => {
  const r = useV2(() => getLibraryProfile(code), [code]);
  const d = r.data;
  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="presentation" onKeyDown={(e) => e.key === "Escape" && onClose()}>
      <div className="absolute inset-0 bg-slate-900/40" onClick={onClose} aria-hidden />
      <aside role="dialog" aria-modal="true" aria-label="Profile detail" className="relative w-full max-w-4xl h-full bg-surface overflow-y-auto shadow-2xl p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div><div className="text-xs text-pex-muted">{code} · version {d?.version} · {d?.family_name}</div><h2 className="text-lg font-semibold">{d ? pretty(d.name) : code}</h2></div>
          <button type="button" onClick={onClose} aria-label="Close" autoFocus className="p-1.5 rounded-lg hover:bg-slate-100"><X className="w-5 h-5" aria-hidden /></button>
        </div>
        {!d ? <Wait r={r} /> : <div className="grid gap-5 text-sm">
          <Banner tone="amber" title={d.validation_status}>Trust tiers, decision-option effects and the wording below are a first draft. The bank's payment operations and compliance SMEs should validate them against their own process.</Banner>
          <section aria-label="What it does"><h3 className="font-semibold mb-1">What it does</h3><p className="text-pex-muted">{d.outcome_meaning}</p></section>
          <section aria-label="Release and approval">
            <h3 className="font-semibold mb-2">Release and approval</h3>
            <dl className="grid gap-2 sm:grid-cols-[11rem_1fr]">
              <dt className="text-pex-muted">Straight-through</dt><dd><StatusPill tone={STP_TONE[d.stp]} dot={false}>{STP_LABEL[d.stp]}</StatusPill> <span className="text-pex-muted">{d.stp_meaning}</span></dd>
              <dt className="text-pex-muted">When a person decides</dt><dd><b>{APPROVAL_LABEL[d.approval]}.</b> <span className="text-pex-muted">{d.approval_meaning}</span></dd>
              <dt className="text-pex-muted">Authority</dt><dd><b>{pretty(d.authority_domain)}.</b> <span className="text-pex-muted">{d.authority_meaning}</span></dd>
              <dt className="text-pex-muted">Action</dt><dd className="pex-mono text-xs">{d.action}</dd>
              <dt className="text-pex-muted">Resolver</dt><dd className="pex-mono text-xs">{d.resolver ?? "None (a person decides)"}</dd>
              {d.checks.length > 0 && <><dt className="text-pex-muted">Checks</dt><dd className="pex-mono text-xs">{d.checks.join(", ")}</dd></>}
              {d.min_confidence != null && <><dt className="text-pex-muted">Minimum confidence</dt><dd>{d.min_confidence} <span className="text-pex-muted">{d.confidence_note}</span></dd></>}
            </dl>
          </section>
          <ContractSection code={code} />
          {d.decision && (
            <section aria-label="Decision options">
              <h3 className="font-semibold mb-1">Decision options</h3>
              <p className="text-pex-muted mb-2">Reviewer: <b>{pretty(d.decision.reviewer_role)}</b>. Decides <span className="pex-mono text-xs">{d.decision.target_field}</span>. PeX never picks an option.</p>
              <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Options and what each does to the case</caption>
                <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Option</th><th className={th}>Effect on the case</th><th className="font-medium">What that means</th></tr></thead>
                <tbody>{d.decision.options.map((o) => <tr key={o.option} className="border-t border-surface-line align-top"><td className="py-1.5 pr-3 pex-mono text-xs">{o.option}</td><td className="pr-3"><StatusPill tone={EFFECT_TONE[o.effect]} dot={false}>{o.effect}</StatusPill></td><td className="text-pex-muted">{o.effect_meaning}</td></tr>)}</tbody></table></div>
            </section>)}
          <section aria-label="Controls that apply">
            <h3 className="font-semibold mb-2">Controls that apply <span className="text-xs font-normal text-pex-muted">{d.controls.length}</span></h3>
            <ul className="flex flex-wrap gap-1.5">{d.controls.map((c) => <li key={c.id} className="text-xs rounded-md border border-surface-line px-2 py-1" title={c.kind}><span className="pex-mono text-pex-primary">{c.id}</span> {c.name}{c.configurable === "bank-configurable" && <span className="text-pex-muted"> · bank-configurable</span>}</li>)}</ul>
          </section>
        </div>}
      </aside>
    </div>
  );
};

const Profiles: React.FC = () => {
  const r = useV2(getLibrary, []);
  const [q, setQ] = useState(""); const [fam, setFam] = useState(""); const [out, setOut] = useState(""); const [stp, setStp] = useState(""); const [open, setOpen] = useState<string | null>(null);
  const d = r.data;
  const rows: LibRow[] = useMemo(() => (d?.profiles ?? []).filter((p) => (!fam || p.family === fam) && (!out || p.outcome === out) && (!stp || p.stp === stp) &&
    (!q || `${p.code} ${p.name} ${p.authority_domain} ${p.resolver ?? ""}`.toLowerCase().includes(q.toLowerCase()))), [d, q, fam, out, stp]);
  if (!d) return <Wait r={r} />;
  const s = d.summary;
  return (
    <div className="grid grid-cols-1 gap-4 min-w-0">
      <div className="grid gap-2 grid-cols-1 sm:grid-cols-3">
        <Stat label="Profiles" value={s.profiles} hint={Object.entries(s.by_family).map(([k, v]) => `${k} ${v}`).join(" · ")} />
        <Stat label="Repair" value={s.by_outcome.REPAIR ?? 0} hint={`of ${s.profiles}. May go straight through: ${s.by_stp.ALLOWED ?? 0} always allowed, ${s.by_stp.POLICY_GATED ?? 0} only if the bank opts in`} />
        <Stat label="Decision support and investigation" value={(s.by_outcome.DECISION_SUPPORT ?? 0) + (s.by_outcome.INVESTIGATION ?? 0)} hint={`of ${s.profiles}. Never straight through; a person always decides`} />
      </div>
      <Card title="Exception profiles" right={<div><label className="sr-only" htmlFor="lib-q">Filter profiles</label><input id="lib-q" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter, for example IBAN, CO-01, resolver" className="py-1.5 px-2.5 text-sm rounded-lg border border-surface-line w-72 max-w-full" /></div>}>
        <div className="grid gap-2 mb-3">
          <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter by family"><span className="text-xs text-pex-muted w-20">Family</span><Chip on={!fam} onClick={() => setFam("")}>All</Chip>{Object.entries(d.families).map(([k, v]) => <Chip key={k} on={fam === k} onClick={() => setFam(fam === k ? "" : k)}>{k} {v}</Chip>)}</div>
          <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter by outcome"><span className="text-xs text-pex-muted w-20">Outcome</span><Chip on={!out} onClick={() => setOut("")}>All</Chip>{Object.keys(s.by_outcome).map((k) => <Chip key={k} on={out === k} onClick={() => setOut(out === k ? "" : k)}>{OUTCOME_LABEL[k]} {s.by_outcome[k]}</Chip>)}</div>
          <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter by straight-through rule"><span className="text-xs text-pex-muted w-20">Straight-through</span><Chip on={!stp} onClick={() => setStp("")}>All</Chip>{Object.keys(s.by_stp).map((k) => <Chip key={k} on={stp === k} onClick={() => setStp(stp === k ? "" : k)}>{STP_LABEL[k]} {s.by_stp[k]}</Chip>)}</div>
        </div>
        <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">All exception profiles</caption>
          <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Code</th><th className={th}>Profile</th><th className={th}>Outcome</th><th className={th}>Straight-through</th><th className={th}>Approval</th><th className={th}>Authority</th><th className={th}>Evidence</th><th className="font-medium">Options</th></tr></thead>
          <tbody>{rows.map((p) => (
            <tr key={p.code} className="border-t border-surface-line hover:bg-slate-50 cursor-pointer" onClick={() => setOpen(p.code)}>
              <td className="py-2 pr-3"><button type="button" onClick={(e) => { e.stopPropagation(); setOpen(p.code); }} className="pex-mono text-pex-primary hover:underline">{p.code}</button></td>
              <td className="pr-3">{pretty(p.name)}<div className="text-xs text-pex-muted">{p.family_name}</div></td>
              <td className="pr-3 whitespace-nowrap">{OUTCOME_LABEL[p.outcome]}</td>
              <td className="pr-3 whitespace-nowrap"><StatusPill tone={STP_TONE[p.stp]} dot={false}>{STP_LABEL[p.stp]}</StatusPill></td>
              <td className="pr-3 text-xs">{APPROVAL_LABEL[p.approval]}</td><td className="pr-3 text-xs">{pretty(p.authority_domain)}</td>
              <td className="pr-3 pex-mono">{p.evidence_mandatory}<span className="text-xs text-pex-muted"> of {p.evidence_total}</span></td><td className="pex-mono">{p.decision_options || "—"}</td></tr>))}</tbody></table>
          {!rows.length && <p className="text-sm text-pex-muted py-3">Nothing matches the filters.</p>}</div>
      </Card>
      {open && <ProfileDrawer code={open} onClose={() => setOpen(null)} />}
    </div>
  );
};

const StpRules: React.FC = () => {
  const r = useV2(getControls, []);
  const d = r.data;
  if (!d) return <Wait r={r} />;
  const val = (v: unknown) => Array.isArray(v) ? v.join(", ") : typeof v === "boolean" ? (v ? "On" : "Off") : typeof v === "number" ? v.toLocaleString() : String(v);
  return (
    <div className="grid grid-cols-1 gap-4 min-w-0">
      <Banner tone="grey" title="One rule decides straight-through">{d.formula}. All eight must be true. One false predicate sends the case to a person. The AI's confidence score is never one of them.</Banner>
      <Card title="The eight predicates">
        <div className="grid gap-3 md:grid-cols-2">
          {d.stp_predicates.map((p) => (
            <div key={p.code} className="rounded-lg border border-surface-line p-3 min-w-0">
              <div className="flex items-center justify-between gap-2"><span><span className="pex-mono font-semibold text-pex-primary">{p.code}</span> <span className="font-semibold">{p.name}</span></span><StatusPill tone={p.configurable === "fixed" ? "grey" : "blue"} dot={false}>{p.configurable === "fixed" ? "Fixed" : "Bank-configurable"}</StatusPill></div>
              <p className="text-sm mt-1">{p.meaning}</p>
              <p className="text-xs text-pex-muted mt-1"><b>Fed by:</b> {p.fed_by}</p>
              {p.bank_settings.length > 0 && <p className="text-xs text-pex-muted mt-1"><b>Bank settings:</b> <span className="pex-mono">{p.bank_settings.join(", ")}</span></p>}
              <p className="text-xs text-pex-muted mt-1">Applies to {p.profile_count} profiles that can go straight through.</p>
            </div>))}
        </div>
      </Card>
      <Card title="Settings a bank can change">
        <p className="text-sm text-pex-muted mb-3">The framework default is what the code ships with. The value in force is what this bank's policy currently says.</p>
        <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Bank-configurable settings and framework defaults</caption>
          <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Setting</th><th className={th}>Framework default</th><th className={th}>In force</th><th className={th}>Set in</th><th className="font-medium">What it does</th></tr></thead>
          <tbody>{d.bank_settings.map((s) => <tr key={s.key} className="border-t border-surface-line align-top"><td className="py-1.5 pr-3">{s.label}<div className="pex-mono text-xs text-pex-muted">{s.key}</div></td><td className="pr-3 pex-mono">{val(s.default)}</td><td className="pr-3 pex-mono">{val(s.value)}{JSON.stringify(s.value) !== JSON.stringify(s.default) && <span className="ml-1.5 text-xs text-pex-primary">changed</span>}</td><td className="pr-3 text-xs text-pex-muted">{s.source}</td><td className="text-pex-muted">{s.note}</td></tr>)}</tbody></table></div>
      </Card>
      <Card title="Straight-through ceiling per profile">
        <ul className="grid gap-2 text-sm">{Object.entries(d.stp_rules).map(([k, v]) => <li key={k} className="flex flex-wrap items-baseline gap-2"><StatusPill tone={STP_TONE[k]} dot={false}>{STP_LABEL[k]}</StatusPill><span className="text-pex-muted">{v}</span></li>)}</ul>
      </Card>
    </div>
  );
};

const Controls: React.FC = () => {
  const r = useV2(getControls, []);
  const [kind, setKind] = useState("");
  const d = r.data;
  if (!d) return <Wait r={r} />;
  const kinds = Array.from(new Set(d.controls.map((c) => c.kind)));
  const rows = d.controls.filter((c) => !kind || c.kind === kind);
  return (
    <div className="grid grid-cols-1 gap-4 min-w-0">
      <Banner tone="grey" title="Controls">{d.note}</Banner>
      <Card title="Controls" right={<span className="text-xs text-pex-muted">{rows.length} of {d.controls.length}</span>}>
        <div className="flex flex-wrap gap-1.5 mb-3" role="group" aria-label="Filter by kind"><Chip on={!kind} onClick={() => setKind("")}>All</Chip>{kinds.map((k) => <Chip key={k} on={kind === k} onClick={() => setKind(kind === k ? "" : k)}>{k}</Chip>)}</div>
        <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Controls, what enforces them and which profiles they cover</caption>
          <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>ID</th><th className={th}>Control</th><th className={th}>Kind</th><th className="pr-3 font-medium">What it does</th><th className={th}>Can a bank change it?</th><th className="font-medium">Covers</th></tr></thead>
          <tbody>{rows.map((c) => (
            <tr key={c.id} className="border-t border-surface-line align-top">
              <td className="py-2 pr-3 pex-mono text-pex-primary">{c.id}</td><td className="pr-3 font-medium">{c.name}<div className="pex-mono text-xs text-pex-muted font-normal">{c.enforced_in}</div></td><td className="pr-3 text-xs">{c.kind}</td>
              <td className="pr-3">{c.meaning}</td><td className="pr-3"><StatusPill tone={c.configurable === "fixed" ? "grey" : "blue"} dot={false}>{c.configurable === "fixed" ? "No, fixed" : "Yes"}</StatusPill></td>
              <td className="text-xs whitespace-nowrap">{c.profile_count} profiles{c.breakdown && <div className="text-pex-muted">{Object.entries(c.breakdown).map(([k, v]) => `${pretty(k)} ${v}`).join(" · ")}</div>}</td></tr>))}</tbody></table></div>
      </Card>
    </div>
  );
};

export const LibraryView: React.FC = () => {
  const [tab, setTab] = useState<"profiles" | "stp" | "controls" | "contract">("profiles");
  const tabs: Array<["profiles" | "stp" | "controls" | "contract", string]> = [["profiles", "Profiles"], ["stp", "Straight-through rules"], ["controls", "Controls"], ["contract", "Integration contract"]];
  return (
    <div className="grid grid-cols-1 gap-4 min-w-0">
      <Banner tone="amber" title="Read only. Bank SME to validate against their process">Everything here is read from the live profile packs and a definitions file. The meanings, trust tiers and decision-option effects are a first draft. The bank's payment operations and compliance SMEs should validate them against their own process.</Banner>
      <div role="tablist" aria-label="Library views" className="flex flex-wrap gap-1">
        {tabs.map(([id, label]) => <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)} className={cn("px-3 py-1.5 text-sm rounded-full", tab === id ? "bg-pex-primary-soft text-pex-primary font-medium" : "text-slate-600 hover:bg-slate-100")}>{label}</button>)}
      </div>
      {tab === "profiles" && <Profiles />}{tab === "stp" && <StpRules />}{tab === "controls" && <Controls />}{tab === "contract" && <ContractView />}
    </div>
  );
};
