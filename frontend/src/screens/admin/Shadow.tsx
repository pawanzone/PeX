import React, { useRef, useState } from "react";
import { Upload } from "lucide-react";
import { Banner, StatusPill } from "../../components/v2";
import { useV2 } from "../../services/v2/client";
import { clearShadow, getScorecard, getShadowCases, getValueModel, uploadShadowFile, type UploadResult, type ValueInputs } from "../../services/v2/shadow";
import { useSession } from "../../shell/session";
import { Card, Stat, Wait } from "./Reference";

const th = "py-1.5 pr-3 font-medium whitespace-nowrap";
const pct = (x: number | null) => (x === null ? "n/a" : `${(x * 100).toFixed(1)}%`);

const FIELDS: Array<[keyof ValueInputs, string]> = [["monthly_exceptions", "Exceptions per month"], ["minutes_per_case", "Minutes to handle a case today"], ["cost_per_hour", "Loaded cost per hour"], ["review_minutes", "Minutes to approve a prepared case"]];
const n0 = (x: number) => Math.round(x).toLocaleString("en-US");

/** Gross saving from the bank's own figures. Nothing about PeX cost is assumed. */
const ValueCard: React.FC<{ tick: number }> = ({ tick }) => {
  const [inp, setInp] = useState<ValueInputs>({ monthly_exceptions: 5000, minutes_per_case: 15, cost_per_hour: 45, review_minutes: 3 });
  const r = useV2(() => getValueModel(inp), [inp.monthly_exceptions, inp.minutes_per_case, inp.cost_per_hour, inp.review_minutes, tick]);
  const d = r.data;
  return (
    <Card title="What it is worth">
      <p className="text-sm text-pex-muted mb-3">Enter the bank's own figures. The saving is gross: no PeX cost is included.</p>
      <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {FIELDS.map(([k, label]) => (
          <label key={k} className="text-sm grid gap-1"><span className="text-pex-muted">{label}</span>
            <input type="number" inputMode="decimal" min={0} value={inp[k]} onChange={(e) => setInp({ ...inp, [k]: e.target.value === "" ? 0 : Number(e.target.value) })} className="rounded-lg border border-surface-line bg-white px-2 py-1.5 w-full" />
          </label>))}
      </div>
      {r.error && <p role="alert" className="text-sm text-red-700 mt-2">{r.error}</p>}
      {d && (
        <>
          {d.measured_minutes_per_case !== null && <p className="text-xs text-pex-muted mt-2">Analyst time in the loaded results averages {d.measured_minutes_per_case} minutes a case. <button type="button" className="underline" onClick={() => setInp({ ...inp, minutes_per_case: d.measured_minutes_per_case! })}>Use it</button></p>}
          <div className="overflow-x-auto mt-3"><table className="w-full text-sm"><caption className="sr-only">Saving by share of cases</caption>
            <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Scenario</th><th className={th}>Cases a month</th><th className={th}>Hours a month</th><th className={th}>Saved a month</th><th className="font-medium">Saved a year</th></tr></thead>
            <tbody>{d.scenarios.map((s) => (
              <tr key={s.label} className="border-t border-surface-line align-top">
                <td className="py-1.5 pr-3">{s.label}{s.kind === "measured" && <span className="ml-1.5"><StatusPill tone={s.wrong_releases ? "amber" : "green"} dot={false}>{s.wrong_releases ? "not yet safe" : "from your data"}</StatusPill></span>}{s.caveat && <div className="text-xs text-pex-muted max-w-[26rem]">{s.caveat}</div>}</td>
                <td className="pr-3">{n0(s.cases_per_month)}</td><td className="pr-3">{n0(s.hours_saved_month)}</td><td className="pr-3">{n0(s.cost_saved_month)}</td><td className="font-medium">{n0(s.cost_saved_year)}</td>
              </tr>))}</tbody></table></div>
          <ul className="list-disc pl-5 text-xs text-pex-muted mt-3 grid gap-0.5">{d.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
        </>
      )}
    </Card>
  );
};

const WrongList: React.FC<{ tick: number }> = ({ tick }) => {
  const r = useV2(() => getShadowCases("released_wrongly"), [tick]);
  if (!r.data) return <Wait r={r} />;
  if (!r.data.items.length) return <p className="text-sm text-pex-muted">None. Every case PeX would have released matches what the analyst did.</p>;
  return (
    <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Cases PeX would have released that the analyst handled differently</caption>
      <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Case</th><th className={th}>Type</th><th className={th}>PeX proposed</th><th className={th}>Analyst did</th><th className="font-medium">Why it matters</th></tr></thead>
      <tbody>{r.data.items.map((x) => (
        <tr key={x.case_id} className="border-t border-surface-line align-top">
          <td className="py-1.5 pr-3 pex-mono text-xs text-pex-primary">{x.case_id}</td><td className="pr-3">{x.profile}</td>
          <td className="pr-3 max-w-[16rem]">{x.pex_value}</td>
          <td className="pr-3 max-w-[16rem]">{x.analyst_action === "FIXED" ? x.analyst_value : <span className="text-pex-muted">{x.analyst_action.toLowerCase()} (no fix)</span>}</td>
          <td className="text-xs text-pex-muted">{x.verdict_text}</td>
        </tr>))}</tbody></table></div>
  );
};

/** Shadow scorecard: what PeX would have done, against what the bank's analyst actually did. Read only; nothing is released. */
export const ShadowView: React.FC = () => {
  const { persona } = useSession();
  const canLoad = persona?.role === ("ADMIN" as any);
  const [tick, setTick] = useState(0);
  const r = useV2(getScorecard, [tick]);
  const [res, setRes] = useState<UploadResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const d = r.data;
  if (!d) return <Wait r={r} />;
  const send = async (f: File | undefined) => {
    if (!f) return;
    setBusy(true); setErr(null); setRes(null);
    try { setRes(await uploadShadowFile(f)); setTick((t) => t + 1); } catch (e: any) { setErr(e?.message || "Upload failed"); } finally { setBusy(false); if (input.current) input.current.value = ""; }
  };
  const wrong = d.release.released_wrongly;
  const loadCard = (

        <Card title="Load analyst results" right={d.compared ? <button type="button" className="text-sm text-pex-muted underline" onClick={async () => { await clearShadow(); setRes(null); setTick((t) => t + 1); }}>Clear loaded results</button> : undefined}>
          <div className="flex items-center gap-3 flex-wrap">
            <input ref={input} type="file" accept=".csv,text/csv" className="sr-only" id="shadow-file" onChange={(e) => send(e.target.files?.[0])} />
            <label htmlFor="shadow-file" className="px-3 py-1.5 text-sm rounded-lg border border-surface-line bg-white inline-flex items-center gap-1.5 cursor-pointer"><Upload className="w-4 h-4" aria-hidden />{busy ? "Loading…" : "Choose a CSV file"}</label>
            <span className="text-xs text-pex-muted">One row per case the analyst already worked. Loading a case again replaces it.</span>
          </div>
          <div className="overflow-x-auto mt-3"><table className="w-full text-sm"><caption className="sr-only">Columns in the file</caption>
            <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Column</th><th className={th}>Need</th><th className="font-medium">Meaning</th></tr></thead>
            <tbody>{d.columns.map((c) => <tr key={c.name} className="border-t border-surface-line align-top"><td className="py-1.5 pr-3 pex-mono text-xs">{c.name}</td><td className="pr-3">{c.required ? <StatusPill tone="blue" dot={false}>Must have</StatusPill> : <span className="text-xs text-pex-muted">Optional</span>}</td><td className="text-pex-muted">{c.meaning}</td></tr>)}</tbody></table></div>
          {err && <p role="alert" className="text-sm text-red-700 mt-2">{err}</p>}
          {res && (
            <div className="mt-2 text-sm" role="status">
              Loaded {res.accepted} ({res.replaced} replaced){res.rejected.length ? `; ${res.rejected.length} rows not used:` : "."}
              {!!res.rejected.length && <ul className="list-disc pl-5 text-pex-muted">{res.rejected.slice(0, 20).map((x) => <li key={x.row}>Row {x.row}{x.case_id ? ` (${x.case_id})` : ""}: {x.reason}</li>)}</ul>}
            </div>
          )}
        </Card>
      
  );
  return (
    <div className="grid grid-cols-1 gap-4 min-w-0">
      <Banner tone="blue" title="Shadow scorecard">{d.note}</Banner>
      {canLoad && d.compared === 0 && loadCard}
      {d.compared > 0 && (
        <>
          <div className="grid gap-2 grid-cols-2 sm:grid-cols-4">
            <Stat label="Cases compared" value={d.compared} hint={d.loaded_at ? `loaded ${d.loaded_at.slice(0, 10)}` : undefined} />
            <Stat label="PeX would have released" value={d.release.would_release} hint="passed all 8 rules" />
            <Stat label="Released correctly" value={d.release.released_correctly} hint={`safe-release rate ${pct(d.rates.safe_release_rate)}`} />
            <Stat label="Released wrongly" value={wrong.count} hint={`${wrong.differ} different value · ${wrong.analyst_no_fix} analyst did not fix`} />
          </div>
          <div className="grid gap-2 grid-cols-2 sm:grid-cols-4">
            <Stat label="Sent to a person" value={d.release.sent_to_person} hint="failed a rule or no proposal" />
            <Stat label="Agree rate" value={pct(d.rates.agree_rate)} hint="same value, where both fixed" />
            <Stat label="Analyst minutes saved" value={d.time.minutes_on_released} hint={`${d.time.released_cases} correctly released cases`} />
            <Stat label="Cases with minutes" value={d.time.cases_with_minutes} hint={`${d.time.minutes_all} minutes in total`} />
          </div>
          <Card title="How the cases compare">
            <ul className="text-sm grid gap-1">{d.verdicts.map((v) => <li key={v.verdict} className="flex justify-between gap-3 border-b border-surface-line py-1"><span>{v.text}</span><span className="font-medium">{v.count}</span></li>)}</ul>
          </Card>
          <Card title="Released wrongly: review each one"><WrongList tick={tick} /></Card>
          <Card title="By exception type">
            <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="sr-only">Comparison by exception type</caption>
              <thead className="text-xs text-pex-muted text-left"><tr><th className={th}>Type</th><th className={th}>Compared</th><th className={th}>Same fix</th><th className={th}>Released correctly</th><th className={th}>Released wrongly</th><th className="font-medium">Sent to a person</th></tr></thead>
              <tbody>{d.by_profile.map((p) => <tr key={p.profile} className="border-t border-surface-line"><td className="py-1.5 pr-3 pex-mono text-xs text-pex-primary">{p.profile}</td><td className="pr-3">{p.compared}</td><td className="pr-3">{p.agree}</td><td className="pr-3">{p.released_correctly}</td><td className={p.released_wrongly ? "pr-3 text-red-700 font-medium" : "pr-3"}>{p.released_wrongly}</td><td>{p.sent_to_person}</td></tr>)}</tbody></table></div>
          </Card>
        </>
      )}
      <ValueCard tick={tick} />
      {canLoad && d.compared > 0 && loadCard}
    </div>
  );
};
