import React, { useState } from "react";
import { Plug, CheckCircle2, AlertTriangle, Database, FileText, Info, ChevronRight } from "lucide-react";
import { Tile, Banner, StatusPill, DataTable, Loading, ErrorState, Modal, useToast } from "../components/v2";
import { useV2 } from "../services/v2/client";
import { getIntegrations, getModeChangeRequests, requestModeChange, approveModeChange, rejectModeChange, getHandoffs, type Integration, type ModeChangeRequest } from "../services/v2/admin";
import { useQueryParam } from "../lib/router";
import { useSession } from "../shell/session";
import { hhmm } from "./compliance/fmt";
import { RolesPanel, PoliciesPanel, ExceptionTypesPanel } from "./admin/Panels";

/** Admin > Integrations (+ Roles and permissions, Policies, Exception types). Design: 14_admin_integrations.png.
 *  Sub-section is held in ?sub= so this file works without router changes. */
const SUBS = [{ id: "integrations", label: "Integrations" }, { id: "roles", label: "Roles and permissions" }, { id: "policies", label: "Policies" }, { id: "exceptions", label: "Exception types" }];

export const AdminIntegrations: React.FC = () => {
  const [sub, setSub] = useQueryParam("sub", "integrations");
  return (
    <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-5 items-start">
      <nav aria-label="Admin sections" className="bg-surface-card rounded-card border border-surface-line shadow-card p-2 grid gap-0.5">
        {SUBS.map((s) => (
          <button key={s.id} type="button" onClick={() => setSub(s.id)} aria-current={sub === s.id ? "page" : undefined}
            className={`text-left px-3 py-2 rounded-lg text-sm ${sub === s.id ? "bg-pex-primary-soft text-pex-primary-dark font-medium" : "text-pex-ink hover:bg-slate-50"}`}>{s.label}</button>
        ))}
      </nav>
      <div className="min-w-0">
        {sub === "roles" ? <RolesPanel /> : sub === "policies" ? <PoliciesPanel /> : sub === "exceptions" ? <ExceptionTypesPanel /> : <Integrations />}
      </div>
    </div>
  );
};

const MODE_LABEL: Record<string, string> = { SHADOW: "Shadow", ASSISTED: "Assisted", LIVE: "Live" };
const MODE_TONE: Record<string, "grey" | "blue" | "green"> = { SHADOW: "grey", ASSISTED: "blue", LIVE: "green" };
const reqBy = (r: ModeChangeRequest) => (typeof r.requested_by === "string" ? r.requested_by : r.requested_by?.name ?? r.requested_by?.user_id ?? "");
const reqById = (r: ModeChangeRequest) => (typeof r.requested_by === "string" ? r.requested_by : r.requested_by?.user_id ?? "");

const Integrations: React.FC = () => {
  const { epoch, persona } = useSession();
  const toast = useToast();
  const d = useV2(getIntegrations, [epoch]);
  const reqs = useV2(getModeChangeRequests, [epoch]);
  const [selId, setSelId] = useState("");
  const [toMode, setToMode] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [showHandoffs, setShowHandoffs] = useState(false);

  if (d.loading && !d.data) return <Loading />;
  if (d.error || !d.data) return <ErrorState unavailable={d.unavailable} message={d.error ?? undefined} onRetry={d.reload} />;
  const data = d.data;
  const items = data.items ?? [];
  const sel = items.find((i) => i.id === selId);
  const t = data.tiles ?? {};
  const h = data.handoffs_24h ?? {};
  const modes = data.modes ?? [{ mode: "SHADOW", text: "PeX reads and recommends. Nothing is sent to the bank." }, { mode: "ASSISTED", text: "PeX prepares handoff requests. Bank staff or systems act on them." }, { mode: "LIVE", text: "PeX data is used directly in production flows under bank policy." }];
  const pending = (reqs.data ?? []).filter((r) => (r.state || "").includes("PENDING"));

  const submit = async () => {
    if (!sel || !toMode) return;
    setBusy(true); setErr(null);
    try { await requestModeChange({ integration_id: sel.id, to_mode: toMode, reason }); toast.push("Mode change requested. A second administrator must approve it.", "green"); setToMode(""); setReason(""); reqs.reload(); d.reload(); }
    catch (e: any) { setErr(e?.message || "Request failed"); }
    finally { setBusy(false); }
  };
  const decide = async (r: ModeChangeRequest, approve: boolean) => {
    try { await (approve ? approveModeChange(r.id) : rejectModeChange(r.id)); toast.push(approve ? "Mode change approved and applied." : "Mode change rejected.", approve ? "green" : "grey"); reqs.reload(); d.reload(); }
    catch (e: any) { toast.push(e?.message || "Could not complete", "red"); }
  };

  return (
    <>
      <div className="mb-4"><h2 className="text-2xl font-semibold text-pex-ink tracking-tight">Integrations</h2><p className="text-sm text-pex-muted mt-1">Connections to bank systems. The bank retains control of execution.</p></div>
      <Banner tone="amber" title="Simulated">{data.banner ?? "All integrations are simulated in this build. No real bank system is contacted."}</Banner>
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 my-4">
        <Tile label="Connected" value={<span className="inline-flex items-center gap-2"><Plug className="w-5 h-5 text-pex-muted" aria-hidden />{t.connected ?? items.length}</span>} />
        <Tile tone="green" label="Healthy" value={<span className="inline-flex items-center gap-2"><CheckCircle2 className="w-5 h-5 text-pex-ok" aria-hidden />{t.healthy ?? items.filter((i) => i.health === "healthy").length}</span>} />
        <Tile tone="amber" label="Degraded" value={<span className="inline-flex items-center gap-2"><AlertTriangle className="w-5 h-5 text-pex-wait" aria-hidden />{t.degraded ?? items.filter((i) => i.health === "degraded").length}</span>} />
        <Tile label="Live write-back enabled" value={<span className="inline-flex items-center gap-2"><Database className="w-5 h-5 text-pex-muted" aria-hidden />{t.live_writeback_enabled?.count ?? 0} of {t.live_writeback_enabled?.of ?? items.length}</span>} />
      </div>

      <div className="grid grid-cols-1 2xl:grid-cols-[1fr_320px] gap-4 items-start">
        <div className="bg-surface-card rounded-card border border-surface-line shadow-card p-2 min-w-0">
          <DataTable<Integration> caption="Integrations (all simulated)" rows={items} rowKey={(r) => r.id} selectedKey={selId} onRowClick={(r) => setSelId(r.id)}
            columns={[
              { key: "n", header: "System", render: (r) => <span className="font-medium text-pex-ink">{r.name}<span className="block text-[11px] font-normal text-pex-muted">Simulated</span></span> },
              { key: "t", header: "Type", render: (r) => r.purpose ?? r.type ?? "—" },
              { key: "dir", header: "Direction", render: (r) => r.direction ?? "—" },
              { key: "m", header: "Mode", render: (r) => <span className="inline-flex flex-col gap-1"><StatusPill tone={MODE_TONE[r.mode ?? ""] ?? "grey"} dot={false}>{MODE_LABEL[r.mode ?? ""] ?? r.mode ?? "—"}</StatusPill>{r.pending_mode_change && <span className="text-[11px] text-pex-wait">Change pending → {MODE_LABEL[r.pending_mode_change.to_mode ?? ""] ?? r.pending_mode_change.to_mode}</span>}</span> },
              { key: "h", header: "Health", render: (r) => r.health === "degraded" ? <span className="text-pex-wait inline-flex flex-col"><span className="inline-flex items-center gap-1 font-medium"><AlertTriangle className="w-4 h-4" aria-hidden />Degraded</span>{r.health_note && <span className="text-xs">{r.health_note}</span>}</span> : <span className="text-pex-ok inline-flex items-center gap-1 font-medium"><CheckCircle2 className="w-4 h-4" aria-hidden />Healthy</span> },
              { key: "l", header: "Last event", render: (r) => hhmm(r.last_event) || "—" },
              { key: "q", header: "Queue", align: "right", render: (r) => r.queue ?? 0 },
              { key: "a", header: "Action", render: (r) => <button type="button" onClick={(e) => { e.stopPropagation(); setSelId(r.id); }} className="text-pex-primary hover:underline">{r.action?.label === "View issue" || r.action?.kind === "issue" ? "View issue" : "Configure"}</button> },
            ]} />
        </div>

        <aside className="bg-surface-card rounded-card border border-surface-line shadow-card p-4 grid gap-3" aria-label="What each mode means">
          <h3 className="text-base font-semibold text-pex-ink">What each mode means</h3>
          {modes.map((m) => <div key={m.mode} className="flex gap-3 items-start text-sm"><span className="w-20 shrink-0"><StatusPill tone={MODE_TONE[m.mode] ?? "grey"} dot={false}>{MODE_LABEL[m.mode] ?? m.mode}</StatusPill></span><span className="text-pex-ink/80">{m.text}</span></div>)}
          <div className="rounded-lg bg-slate-50 px-3 py-2 text-sm flex gap-2"><Info className="w-4 h-4 mt-0.5 shrink-0 text-pex-muted" aria-hidden />{data.never_executes ?? "PeX never executes payments. Execution is always performed and confirmed by the bank system."}</div>
          <div className="border-t border-surface-line pt-3 grid gap-2">
            <div className="text-sm font-medium text-pex-ink">Change mode{sel ? <span className="font-normal text-pex-muted"> · {sel.name}</span> : null}</div>
            <div className="flex gap-2">
              <select aria-label="Select mode" value={toMode} onChange={(e) => setToMode(e.target.value)} disabled={!sel} className="flex-1 py-2 px-2 text-sm rounded-lg border border-surface-line bg-white disabled:bg-slate-50">
                <option value="">Select mode</option>
                {Object.keys(MODE_LABEL).filter((m) => m !== sel?.mode).map((m) => <option key={m} value={m}>{MODE_LABEL[m]}</option>)}
              </select>
              <button type="button" onClick={submit} disabled={!sel || !toMode || !reason.trim() || busy} className="px-3 py-2 text-sm font-medium rounded-lg bg-pex-primary text-white disabled:opacity-50 disabled:cursor-not-allowed">Request</button>
            </div>
            <input aria-label="Reason for mode change" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason (required)" disabled={!sel} className="py-2 px-2.5 text-sm rounded-lg border border-surface-line bg-white disabled:bg-slate-50" />
            <p className="text-xs text-pex-muted">{sel ? "Changing mode requires approval from a second administrator." : "Select a system in the table first. Changing mode requires approval from a second administrator."}</p>
            {err && <Banner tone="red" title="Request failed">{err}</Banner>}
          </div>
        </aside>
      </div>

      {pending.length > 0 && (
        <section className="mt-4 bg-surface-card rounded-card border border-surface-line shadow-card p-4" aria-labelledby="mc-h">
          <h3 id="mc-h" className="text-base font-semibold text-pex-ink mb-2">Mode changes awaiting a second administrator</h3>
          <ul className="grid gap-2">{pending.map((r) => {
            const self = !!persona && reqById(r) === persona.user_id;
            return (
              <li key={r.id} className="flex items-center gap-3 flex-wrap text-sm rounded-lg bg-slate-50 px-3 py-2">
                <span className="pex-mono text-xs">{r.id}</span>
                <span>{items.find((i) => i.id === r.integration_id)?.name ?? r.integration_id}: {MODE_LABEL[r.from_mode ?? ""] ?? r.from_mode ?? "current"} → <b>{MODE_LABEL[r.to_mode ?? ""] ?? r.to_mode}</b></span>
                <span className="text-pex-muted">requested by {reqBy(r) || "—"}{r.reason ? ` · ${r.reason}` : ""}</span>
                <span className="ml-auto flex items-center gap-2">
                  {self && <span className="text-xs text-pex-muted">You requested this. A different administrator must approve.</span>}
                  <button type="button" disabled={self} title={self ? "A different administrator must approve" : undefined} onClick={() => decide(r, true)} className="px-3 py-1.5 text-sm rounded-lg bg-pex-primary text-white disabled:opacity-50 disabled:cursor-not-allowed">Approve</button>
                  <button type="button" onClick={() => decide(r, false)} className="px-3 py-1.5 text-sm rounded-lg border border-surface-line bg-white hover:bg-slate-50">Reject</button>
                </span>
              </li>
            );
          })}</ul>
        </section>
      )}

      <section className="mt-4 bg-surface-card rounded-card border border-surface-line shadow-card p-4" aria-labelledby="ho-h">
        <h3 id="ho-h" className="text-base font-semibold text-pex-ink mb-3">Handoff requests, last 24 hours</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-stretch">
          <Tile label="Sent" value={<span className="inline-flex items-center gap-2"><FileText className="w-5 h-5 text-pex-muted" aria-hidden />{h.sent ?? 0}</span>} />
          <Tile tone="green" label="Acknowledged by bank (simulated)" value={h.acknowledged ?? 0} />
          <Tile tone="amber" label="Awaiting acknowledgement" value={h.awaiting ?? 0} />
        </div>
        <div className="mt-2 flex items-center justify-between text-xs text-pex-muted"><span>{h.source ?? "Computed from real handoffs. The bank is simulated."}</span>
          <button type="button" onClick={() => setShowHandoffs(true)} className="text-sm text-pex-primary font-medium inline-flex items-center gap-1 hover:underline">View handoffs<ChevronRight className="w-4 h-4" aria-hidden /></button></div>
      </section>
      <HandoffsModal open={showHandoffs} onClose={() => setShowHandoffs(false)} />
    </>
  );
};

const HandoffsModal: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => {
  const r = useV2(() => (open ? getHandoffs(24) : Promise.resolve(null)), [open]);
  const rows: any[] = Array.isArray(r.data) ? r.data : r.data?.items ?? [];
  const cols = rows.length ? Object.keys(rows[0]).filter((k) => ["string", "number", "boolean"].includes(typeof rows[0][k])).slice(0, 7) : [];
  return (
    <Modal open={open} onClose={onClose} title="Handoff requests, last 24 hours (simulated)" width="xl">
      {r.loading ? <Loading /> : r.error ? <ErrorState unavailable={r.unavailable} message={r.error} onRetry={r.reload} /> : !rows.length ? <div className="text-sm text-pex-muted py-4">No handoffs in the last 24 hours.</div> : (
        <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="text-left text-xs text-pex-muted border-b border-surface-line">{cols.map((c) => <th key={c} className="py-2 px-2 font-medium">{c.replace(/_/g, " ")}</th>)}</tr></thead>
          <tbody>{rows.map((x, i) => <tr key={i} className="border-b border-surface-line last:border-0">{cols.map((c) => <td key={c} className="py-2 px-2">{String(x[c])}</td>)}</tr>)}</tbody></table></div>
      )}
    </Modal>
  );
};
