import React, { useEffect, useRef, useState } from "react";
import { ArrowRight, Bookmark, ChevronDown, Search, ShieldCheck, ShieldAlert, ShieldQuestion } from "lucide-react";
import { cn, StatusPill, Empty, Loading, ErrorState } from "./primitives";

export const FilterBar: React.FC<{ children: React.ReactNode; search?: { value: string; onChange: (v: string) => void; placeholder?: string }; right?: React.ReactNode }> = ({ children, search, right }) => (
  <div className="flex items-center gap-2 flex-wrap py-3">
    {search && (
      <label className="relative">
        <span className="sr-only">Search</span>
        <Search className="w-4 h-4 absolute left-2.5 top-2.5 text-slate-400" aria-hidden />
        <input value={search.value} onChange={(e) => search.onChange(e.target.value)} placeholder={search.placeholder ?? "Search"} className="pl-8 pr-3 py-2 text-sm rounded-lg border border-surface-line bg-white w-64" />
      </label>
    )}
    {children}
    {right && <div className="ml-auto flex items-center gap-2">{right}</div>}
  </div>
);

export const FilterSelect: React.FC<{ label: string; value: string; onChange: (v: string) => void; options: Array<{ value: string; label: string }> }> = ({ label, value, onChange, options }) => (
  <label className="inline-flex items-center gap-1.5 text-xs text-pex-muted">
    {label}
    <select value={value} onChange={(e) => onChange(e.target.value)} className="py-2 pl-2 pr-7 text-sm rounded-lg border border-surface-line bg-white text-pex-ink">
      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </label>
);

export interface SavedView { id: string; label: string }
/** Menu button (aria-haspopup) with arrow-key navigation and Escape to close. */
export const SavedViewsMenu: React.FC<{ views: SavedView[]; activeId?: string; onSelect: (id: string) => void; onSave?: () => void }> = ({ views, activeId, onSelect, onSave }) => {
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const off = (e: MouseEvent) => { if (!wrap.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", off);
    return () => document.removeEventListener("mousedown", off);
  }, [open]);
  const items = () => Array.from(wrap.current?.querySelectorAll<HTMLElement>("[role=menuitem]") ?? []);
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") { setOpen(false); return; }
    const its = items(); const i = its.indexOf(document.activeElement as HTMLElement);
    if (e.key === "ArrowDown") { e.preventDefault(); its[(i + 1) % its.length]?.focus(); }
    if (e.key === "ArrowUp") { e.preventDefault(); its[(i - 1 + its.length) % its.length]?.focus(); }
  };
  return (
    <div ref={wrap} className="relative" onKeyDown={onKey}>
      <button type="button" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-surface-line bg-white hover:bg-slate-50">
        <Bookmark className="w-4 h-4" aria-hidden />Saved views<ChevronDown className="w-3.5 h-3.5" aria-hidden />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 mt-1 w-56 bg-white border border-surface-line rounded-lg shadow-lg z-30 py-1">
          {views.map((v) => (
            <button key={v.id} role="menuitem" onClick={() => { onSelect(v.id); setOpen(false); }} className={cn("w-full text-left px-3 py-2 text-sm hover:bg-slate-50", v.id === activeId && "font-semibold text-pex-primary")}>{v.label}{v.id === activeId && <span className="sr-only"> (current)</span>}</button>
          ))}
          {onSave && <button role="menuitem" onClick={() => { onSave(); setOpen(false); }} className="w-full text-left px-3 py-2 text-sm border-t border-surface-line text-pex-primary hover:bg-slate-50">Save current filters…</button>}
        </div>
      )}
    </div>
  );
};

export interface Column<T> { key: string; header: string; render: (row: T) => React.ReactNode; mono?: boolean; align?: "left" | "right"; width?: string; nowrap?: boolean }
export function DataTable<T>({ columns, rows, rowKey, onRowClick, selectedKey, selectable, selected, onToggle, loading, error, onRetry, emptyTitle = "Nothing here", emptyHint, caption, footer, density = "comfortable", stripe }: {
  density?: "comfortable" | "compact"; stripe?: (r: T) => "block" | "wait" | "ok" | null;
  columns: Column<T>[]; rows: T[]; rowKey: (r: T) => string; onRowClick?: (r: T) => void; selectedKey?: string;
  selectable?: boolean; selected?: Set<string>; onToggle?: (key: string) => void;
  loading?: boolean; error?: string | null; onRetry?: () => void; emptyTitle?: string; emptyHint?: string; caption?: string; footer?: React.ReactNode;
}) {
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (!rows.length) return <Empty title={emptyTitle} hint={emptyHint} />;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead><tr className="text-left text-xs text-pex-muted border-b border-surface-line">
          {selectable && <th className="w-8 py-2 px-2"><span className="sr-only">Select</span></th>}
          {columns.map((c) => <th key={c.key} scope="col" style={{ width: c.width }} className={cn("py-2.5 px-2.5 font-medium whitespace-nowrap", c.align === "right" && "text-right")}>{c.header}</th>)}
        </tr></thead>
        <tbody>
          {rows.map((r) => {
            const k = rowKey(r);
            return (
              <tr key={k} onClick={onRowClick ? () => onRowClick(r) : undefined} aria-selected={selectedKey === k || undefined}
                tabIndex={onRowClick ? 0 : undefined} onKeyDown={onRowClick ? (e) => { if (e.key === "Enter") onRowClick(r); } : undefined}
                className={cn("border-b border-surface-line last:border-0", onRowClick && "cursor-pointer hover:bg-slate-50", selectedKey === k && "bg-pex-primary-soft/60")}>
                {selectable && <td className={cn("px-2", density === "compact" ? "py-1" : "py-2.5")} onClick={(e) => e.stopPropagation()}><input type="checkbox" aria-label={`Select ${k}`} checked={!!selected?.has(k)} onChange={() => onToggle?.(k)} /></td>}
                {columns.map((c, ci) => { const st = ci === 0 && !selectable ? stripe?.(r) : null; return <td key={c.key} style={st ? { boxShadow: `inset 3px 0 0 rgb(var(--c-${st}))` } : undefined} className={cn("px-2.5 align-middle", density === "compact" ? "py-1.5" : "py-2.5", c.mono && "pex-mono", c.nowrap && "whitespace-nowrap", c.align === "right" && "text-right")}>{c.render(r)}</td>; })}
              </tr>
            );
          })}
        </tbody>
      </table>
      {footer}
    </div>
  );
}

export interface EvidenceRow { source: string; finding: React.ReactNode; confidence?: "high" | "medium" | "low" | string; status?: "match" | "mismatch" | "missing" | "info"; ref?: string }
const EV_TONE = { match: "green", mismatch: "red", missing: "amber", info: "grey" } as const;
const EV_LABEL = { match: "Matches", mismatch: "Conflicts", missing: "Missing", info: "Info" } as const;
export const EvidenceTable: React.FC<{ rows: EvidenceRow[] }> = ({ rows }) => (
  <DataTable caption="Evidence" rows={rows} rowKey={(r) => r.source + (r.ref ?? "")} emptyTitle="No evidence recorded"
    columns={[
      { key: "s", header: "Source", render: (r) => <span className="font-medium">{r.source}</span> },
      { key: "f", header: "Finding", render: (r) => r.finding },
      { key: "c", header: "Confidence", render: (r) => r.confidence ? <span className="capitalize">{r.confidence}</span> : <span className="text-slate-400">—</span> },
      { key: "st", header: "Result", render: (r) => r.status ? <StatusPill tone={EV_TONE[r.status]}>{EV_LABEL[r.status]}</StatusPill> : null },
    ]} />
);

/** Before -> after change for one field. Both values shown as text; arrow is decorative. */
export const FieldDiff: React.FC<{ rows: Array<{ field: string; before?: string; after?: string; note?: string }> }> = ({ rows }) => (
  <div className="divide-y divide-surface-line">
    {rows.map((r, i) => (
      <div key={i} className="py-2.5 grid grid-cols-[10rem_1fr] gap-4 items-start">
        <div className="text-xs text-pex-muted pt-0.5">{r.field}</div>
        <div>
          <div className="flex items-center gap-2 flex-wrap pex-mono text-sm">
            <span className="line-through text-pex-block/80 bg-pex-block-soft px-1.5 rounded"><span className="sr-only">Before: </span>{r.before || "(empty)"}</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-400" aria-hidden />
            <span className="text-pex-ok bg-pex-ok-soft px-1.5 rounded"><span className="sr-only">After: </span>{r.after || "(empty)"}</span>
          </div>
          {r.note && <div className="text-xs text-pex-muted mt-1">{r.note}</div>}
        </div>
      </div>
    ))}
  </div>
);

export const SourceCard: React.FC<{ title: string; status?: "match" | "mismatch" | "missing" | "info"; lines: Array<{ label: string; value: React.ReactNode; mono?: boolean }>; footer?: React.ReactNode }> = ({ title, status = "info", lines, footer }) => {
  const Icon = status === "match" ? ShieldCheck : status === "mismatch" ? ShieldAlert : ShieldQuestion;
  return (
    <section className="bg-surface-card rounded-card border border-surface-line shadow-card p-4">
      <div className="flex items-center justify-between gap-2 mb-3">
        <h3 className="text-sm font-semibold flex items-center gap-2"><Icon className="w-4 h-4 text-slate-500" aria-hidden />{title}</h3>
        <StatusPill tone={EV_TONE[status]}>{EV_LABEL[status]}</StatusPill>
      </div>
      <dl className="space-y-1.5">{lines.map((l, i) => <div key={i} className="flex justify-between gap-3 text-sm"><dt className="text-pex-muted">{l.label}</dt><dd className={cn("text-right text-pex-ink", l.mono && "pex-mono")}>{l.value}</dd></div>)}</dl>
      {footer && <div className="mt-3 pt-3 border-t border-surface-line text-xs text-pex-muted">{footer}</div>}
    </section>
  );
};

export const ConfirmCheckbox: React.FC<{ checked: boolean; onChange: (v: boolean) => void; children: React.ReactNode; id?: string }> = ({ checked, onChange, children, id = "confirm-reviewed" }) => (
  <label htmlFor={id} className="flex items-start gap-2.5 text-sm text-pex-ink cursor-pointer">
    <input id={id} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="mt-0.5 w-4 h-4" />
    <span>{children}</span>
  </label>
);

export const ReasonCommentFields: React.FC<{
  reasons: Array<{ value: string; label: string }>; reason: string; onReason: (v: string) => void;
  comment: string; onComment: (v: string) => void; required?: boolean; reasonLabel?: string; commentLabel?: string;
}> = ({ reasons, reason, onReason, comment, onComment, required, reasonLabel = "Reason", commentLabel = "Comment" }) => (
  <div className="grid gap-3">
    <label className="grid gap-1 text-xs text-pex-muted">{reasonLabel}{required && <span className="sr-only"> (required)</span>}
      <select value={reason} onChange={(e) => onReason(e.target.value)} required={required} className="py-2 px-2.5 text-sm rounded-lg border border-surface-line bg-white text-pex-ink">
        <option value="">Select a reason…</option>
        {reasons.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
      </select>
    </label>
    <label className="grid gap-1 text-xs text-pex-muted">{commentLabel}
      <textarea value={comment} onChange={(e) => onComment(e.target.value)} rows={3} className="py-2 px-2.5 text-sm rounded-lg border border-surface-line bg-white text-pex-ink" />
    </label>
  </div>
);
