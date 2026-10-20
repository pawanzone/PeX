import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Info, Loader2, AlertOctagon, Inbox, X } from "lucide-react";
import type { StatusTone } from "../../lib/statusMeta";
import { statusMeta } from "../../lib/statusMeta";

export const cn = (...c: Array<string | false | null | undefined>) => c.filter(Boolean).join(" ");

/** Tone -> classes. Tone is never the only signal: pills/banners also carry an icon or label text. */
export const TONE: Record<StatusTone, { bg: string; text: string; ring: string; dot: string }> = {
  green: { bg: "bg-pex-ok-soft", text: "text-pex-ok", ring: "ring-pex-ok/25", dot: "bg-pex-ok" },
  amber: { bg: "bg-pex-wait-soft", text: "text-pex-wait", ring: "ring-pex-wait/25", dot: "bg-pex-wait" },
  red: { bg: "bg-pex-block-soft", text: "text-pex-block", ring: "ring-pex-block/25", dot: "bg-pex-block" },
  blue: { bg: "bg-pex-primary-soft", text: "text-pex-primary-dark", ring: "ring-pex-primary/25", dot: "bg-pex-primary" },
  grey: { bg: "bg-slate-100", text: "text-slate-600", ring: "ring-slate-300", dot: "bg-slate-400" },
  purple: { bg: "bg-purple-50", text: "text-purple-700", ring: "ring-purple-300", dot: "bg-purple-500" },
};

export const Breadcrumbs: React.FC<{ items: Array<{ label: string; href?: string }> }> = ({ items }) => (
  <nav aria-label="Breadcrumb" className="text-xs text-pex-muted flex items-center gap-1.5">
    {items.map((it, i) => (
      <React.Fragment key={i}>
        {i > 0 && <span aria-hidden>/</span>}
        {it.href && i < items.length - 1
          ? <a href={it.href} className="hover:text-pex-primary hover:underline">{it.label}</a>
          : <span aria-current={i === items.length - 1 ? "page" : undefined} className={i === items.length - 1 ? "text-pex-ink font-medium" : ""}>{it.label}</span>}
      </React.Fragment>
    ))}
  </nav>
);

export const PageHeader: React.FC<{
  title: string; subtitle?: React.ReactNode; breadcrumbs?: Array<{ label: string; href?: string }>;
  actions?: React.ReactNode;
}> = ({ title, subtitle, breadcrumbs, actions }) => (
  <header className="mb-5">
    {breadcrumbs && <div className="mb-2"><Breadcrumbs items={breadcrumbs} /></div>}
    <div className="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 className="text-2xl font-semibold text-pex-ink tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-pex-muted mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  </header>
);

export const Tile: React.FC<{
  label?: string; value?: React.ReactNode; hint?: React.ReactNode; tone?: StatusTone;
  onClick?: () => void; children?: React.ReactNode; className?: string; mono?: boolean; title?: string;
}> = ({ label, value, hint, tone, onClick, children, className, mono, title }) => {
  const body = (
    <>
      {label && <div className="text-xs font-medium text-pex-muted flex items-center gap-1.5">
        {tone && <span className={cn("w-2 h-2 rounded-full", TONE[tone].dot)} aria-hidden />}{label}</div>}
      {value !== undefined && <div className={cn("mt-1 text-2xl font-semibold text-pex-ink", mono && "pex-mono")}>{value}</div>}
      {hint && <div className="mt-1 text-xs text-pex-muted">{hint}</div>}
      {children}
    </>
  );
  const cls = cn("bg-surface-card rounded-card shadow-card border border-surface-line p-4 text-left", onClick && "hover:border-pex-primary/50 transition-colors w-full", className);
  return onClick
    ? <button type="button" onClick={onClick} title={title} className={cls}>{body}</button>
    : <div className={cls} title={title}>{body}</div>;
};

export const StatusPill: React.FC<{
  tone?: StatusTone; status?: unknown; children?: React.ReactNode; dot?: boolean; title?: string;
}> = ({ tone, status, children, dot = true, title }) => {
  const meta = status !== undefined ? statusMeta(status) : null;
  const t = tone ?? meta?.tone ?? "grey";
  return (
    <span title={title ?? meta?.description} className={cn("inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ring-1 ring-inset whitespace-nowrap", TONE[t].bg, TONE[t].text, TONE[t].ring)}>
      {dot && <span className={cn("w-1.5 h-1.5 rounded-full", TONE[t].dot)} aria-hidden />}
      {children ?? meta?.short}
    </span>
  );
};

const BANNER_ICON: Record<string, React.ElementType> = { green: CheckCircle2, amber: AlertTriangle, red: AlertOctagon, blue: Info, grey: Info, purple: Info };
export const Banner: React.FC<{ tone?: StatusTone; title?: string; children?: React.ReactNode; action?: React.ReactNode }> = ({ tone = "blue", title, children, action }) => {
  const Icon = BANNER_ICON[tone];
  return (
    <div role={tone === "red" ? "alert" : "status"} className={cn("flex items-start gap-3 rounded-card border px-4 py-3 text-sm", TONE[tone].bg, TONE[tone].text, "border-current/20")}>
      <Icon className="w-4 h-4 mt-0.5 shrink-0" aria-hidden />
      <div className="flex-1 min-w-0">{title && <div className="font-semibold">{title}</div>}{children && <div className={cn(title && "mt-0.5", "text-pex-ink/80")}>{children}</div>}</div>
      {action}
    </div>
  );
};

export interface TabDef { id: string; label: string; count?: number; tone?: StatusTone }
/** ARIA tabs: arrow keys move, Home/End jump. Counts are shown as text, not colour alone. */
export const Tabs: React.FC<{ tabs: TabDef[]; value: string; onChange: (id: string) => void; label?: string }> = ({ tabs, value, onChange, label = "Views" }) => {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const onKey = (e: React.KeyboardEvent, i: number) => {
    let n = -1;
    if (e.key === "ArrowRight") n = (i + 1) % tabs.length;
    else if (e.key === "ArrowLeft") n = (i - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") n = 0; else if (e.key === "End") n = tabs.length - 1;
    if (n >= 0) { e.preventDefault(); onChange(tabs[n].id); refs.current[n]?.focus(); }
  };
  return (
    <div role="tablist" aria-label={label} className="flex gap-1 border-b border-surface-line overflow-x-auto">
      {tabs.map((t, i) => {
        const active = t.id === value;
        return (
          <button key={t.id} ref={(el) => { refs.current[i] = el; }} role="tab" aria-selected={active} tabIndex={active ? 0 : -1}
            onClick={() => onChange(t.id)} onKeyDown={(e) => onKey(e, i)}
            className={cn("px-3.5 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 -mb-px flex items-center gap-2", active ? "border-pex-primary text-pex-primary" : "border-transparent text-pex-muted hover:text-pex-ink")}>
            {t.label}
            {t.count !== undefined && <span className={cn("min-w-[1.25rem] px-1.5 rounded-full text-xs text-center", active ? "bg-pex-primary-soft text-pex-primary-dark" : "bg-slate-100 text-slate-600")}>{t.count}</span>}
          </button>
        );
      })}
    </div>
  );
};

const SKIN = ["#f1c9a5", "#e0a97c", "#c68642", "#8d5524", "#f6d7bd"];
const HAIR = ["#2b2118", "#4a3222", "#1c1c1c", "#7a5230", "#9a9a9a"];
const BG = ["#dbeafe", "#dcfce7", "#fef3c7", "#fce7f3", "#e0e7ff", "#ccfbf1"];
const SHIRT = ["#1e3a5f", "#0f766e", "#7c3aed", "#b45309", "#334155", "#be123c"];
const hashOf = (s: string) => { let h = 7; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h; };

/** Illustrated avatar, drawn from the name so the same person always looks the same. Not a photo. */
export const Illustration: React.FC<{ seed: string; className?: string }> = ({ seed, className }) => {
  const h = hashOf(seed || "?");
  const skin = SKIN[h % SKIN.length], hair = HAIR[(h >>> 3) % HAIR.length], bg = BG[(h >>> 5) % BG.length], shirt = SHIRT[(h >>> 7) % SHIRT.length], style = (h >>> 9) % 4;
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden>
      <rect width="40" height="40" fill={bg} />
      {style === 1 && <path d="M9 24c-1-12 5-17 11-17s12 5 11 17l-3 6H12z" fill={hair} />}
      <path d="M5 40c1-8 7-11 15-11s14 3 15 11z" fill={shirt} />
      <rect x="17" y="24" width="6" height="6" rx="2" fill={skin} />
      <ellipse cx="20" cy="17.5" rx="7" ry="8" fill={skin} />
      {style === 0 && <path d="M12.5 16c0-6 3-9 7.5-9s7.5 3 7.5 9c-2-3-5-4-7.5-4s-5.500 1-7.500 4z" fill={hair} />}
      {style === 1 && <path d="M13 16c1-5 4-7 7-7s6 2 7 7c-3-2-5-3-7-3s-4 1-7 3z" fill={hair} />}
      {style === 2 && <><circle cx="20" cy="7.5" r="3.2" fill={hair} /><path d="M13 16c0-5 3-7.500 7-7.500s7 2.500 7 7.500c-2-2.500-4.500-3.500-7-3.500s-5 1-7 3.500z" fill={hair} /></>}
      {style === 3 && <path d="M13.500 14.500c1-4.500 4-6 6.500-6s5.500 1.500 6.500 6c-2-1.500-4-2-6.500-2s-4.500.5-6.500 2z" fill={hair} />}
      <circle cx="17.200" cy="18" r=".8" fill="#1f2937" /><circle cx="22.800" cy="18" r=".8" fill="#1f2937" />
      <path d="M17.500 21.500c1.500 1.200 3.500 1.200 5 0" stroke="#7c2d12" strokeWidth=".9" fill="none" strokeLinecap="round" />
    </svg>
  );
};

export const Avatar: React.FC<{ name?: string; initials?: string; role?: string; size?: "sm" | "md" | "lg"; system?: boolean; bare?: boolean }> = ({ name, initials, role, size = "md", system, bare }) => {
  const ini = initials || (name || "?").split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  const dim = size === "sm" ? "w-6 h-6" : size === "lg" ? "w-14 h-14" : "w-8 h-8";
  return (
    <span className="inline-flex items-center gap-2" title={role ? `${name} · ${role}` : name}>
      {system
        ? <span className={cn("rounded-full flex items-center justify-center font-semibold shrink-0 bg-slate-200 text-slate-700", dim, size === "sm" ? "text-[10px]" : "text-xs")}>{ini}</span>
        : <span className={cn("rounded-full overflow-hidden shrink-0 ring-1 ring-black/5", dim)}><Illustration seed={name || ini} className="w-full h-full block" /></span>}
      {!bare && (name || role) && <span className="leading-tight">{name && <span className="block text-sm text-pex-ink">{name}</span>}{role && <span className="block text-xs text-pex-muted">{role}</span>}</span>}
    </span>
  );
};

export const KeyValueList: React.FC<{ items: Array<{ label: string; value: React.ReactNode; mono?: boolean }>; cols?: 1 | 2 | 3 }> = ({ items, cols = 2 }) => (
  <dl className={cn("grid gap-x-8 gap-y-3", cols === 1 ? "grid-cols-1" : cols === 2 ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-1 sm:grid-cols-3")}>
    {items.map((it, i) => (
      <div key={i}><dt className="text-xs text-pex-muted">{it.label}</dt><dd className={cn("text-sm text-pex-ink mt-0.5", it.mono && "pex-mono")}>{it.value}</dd></div>
    ))}
  </dl>
);

/** "2h 14m left" / "overdue 5m". Ticks every 30s. */
export function formatRemaining(iso: string | undefined, now = Date.now()): { text: string; tone: StatusTone } {
  if (!iso) return { text: "no cutoff", tone: "grey" };
  const ms = new Date(iso).getTime() - now;
  if (Number.isNaN(ms)) return { text: "no cutoff", tone: "grey" };
  const abs = Math.abs(ms), h = Math.floor(abs / 3600000), m = Math.floor((abs % 3600000) / 60000);
  const span = h > 0 ? `${h}h ${m}m` : `${m}m`;
  if (ms < 0) return { text: `overdue ${span}`, tone: "red" };
  return { text: `${span} left`, tone: ms < 3600000 ? "red" : ms < 4 * 3600000 ? "amber" : "green" };
}
export const CountdownText: React.FC<{ iso?: string; className?: string }> = ({ iso, className }) => {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const t = window.setInterval(() => setNow(Date.now()), 30000); return () => window.clearInterval(t); }, []);
  const r = formatRemaining(iso, now);
  return <span className={cn("font-medium", TONE[r.tone].text, className)}>{r.text}</span>;
};

export const Loading: React.FC<{ label?: string }> = ({ label = "Loading…" }) => (
  <div role="status" className="flex items-center justify-center gap-2 py-12 text-sm text-pex-muted"><Loader2 className="w-4 h-4 animate-spin" aria-hidden />{label}</div>
);
export const Empty: React.FC<{ title: string; hint?: string; action?: React.ReactNode }> = ({ title, hint, action }) => (
  <div className="flex flex-col items-center text-center py-12 gap-1"><Inbox className="w-8 h-8 text-slate-300" aria-hidden /><div className="text-sm font-medium text-pex-ink">{title}</div>{hint && <div className="text-xs text-pex-muted max-w-sm">{hint}</div>}{action && <div className="mt-3">{action}</div>}</div>
);
export const ErrorState: React.FC<{ title?: string; message?: string; onRetry?: () => void; unavailable?: boolean }> = ({ title, message, onRetry, unavailable }) => (
  <div role="alert" className="flex flex-col items-center text-center py-12 gap-1">
    <AlertOctagon className="w-8 h-8 text-pex-block" aria-hidden />
    <div className="text-sm font-medium text-pex-ink">{title ?? (unavailable ? "Not available on this server yet" : "Could not load")}</div>
    {message && <div className="text-xs text-pex-muted max-w-md">{message}</div>}
    {onRetry && <button onClick={onRetry} className="mt-3 px-3 py-1.5 text-sm rounded-lg border border-surface-line bg-white hover:bg-slate-50">Try again</button>}
  </div>
);

// ---------------------------------------------------------------- toasts
interface ToastItem { id: number; tone: StatusTone; text: string }
const ToastCtx = createContext<{ push: (text: string, tone?: StatusTone) => void }>({ push: () => {} });
export const useToast = () => useContext(ToastCtx);
export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((text: string, tone: StatusTone = "green") => {
    const id = Date.now() + Math.random();
    setItems((l) => [...l, { id, tone, text }]);
    window.setTimeout(() => setItems((l) => l.filter((x) => x.id !== id)), 5000);
  }, []);
  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div aria-live="polite" className="fixed bottom-20 right-4 z-[60] flex flex-col gap-2">
        {items.map((t) => (
          <div key={t.id} className={cn("flex items-center gap-2 rounded-lg border px-3 py-2 text-sm shadow-lg bg-white", TONE[t.tone].text)}>
            <span className={cn("w-2 h-2 rounded-full", TONE[t.tone].dot)} aria-hidden /><span className="text-pex-ink">{t.text}</span>
            <button aria-label="Dismiss" onClick={() => setItems((l) => l.filter((x) => x.id !== t.id))}><X className="w-3.5 h-3.5 text-slate-400" /></button>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
};
