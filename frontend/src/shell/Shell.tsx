import React, { useEffect, useRef, useState } from "react";
import { ChevronDown, LogOut, Search } from "lucide-react";
import { useRoute, navigate, routes, type Route } from "../lib/router";
import { useSystemInfo } from "../hooks/useSystemInfo";
import { useSession } from "./session";
import { NAV, areaAllowed, roleLabel } from "./nav";
import { Avatar, Banner, StatusPill, cn } from "../components/v2";
import { Login } from "./Login";
import { TextSizeControl } from "./textsize";
import { ChasersBell } from "./Chasers";
import { ThemeControl } from "./theme";

const Clock: React.FC = () => {
  const [now, setNow] = useState(new Date());
  useEffect(() => { const t = window.setInterval(() => setNow(new Date()), 15000); return () => window.clearInterval(t); }, []);
  const d = now.toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short" });
  const t = now.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  return <time className="text-xs text-slate-500 whitespace-nowrap hidden md:block">{d} · {t}</time>;
};

const PersonaMenu: React.FC = () => {
  const { personas, persona, switchTo, signOut } = useSession();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const off = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", off); return () => document.removeEventListener("mousedown", off);
  }, [open]);
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") setOpen(false);
    const its = Array.from(ref.current?.querySelectorAll<HTMLElement>("[role=menuitemradio]") ?? []);
    const i = its.indexOf(document.activeElement as HTMLElement);
    if (e.key === "ArrowDown") { e.preventDefault(); its[(i + 1) % its.length]?.focus(); }
    if (e.key === "ArrowUp") { e.preventDefault(); its[(i - 1 + its.length) % its.length]?.focus(); }
  };
  return (
    <div ref={ref} className="relative" onKeyDown={onKey}>
      <button aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-full hover:bg-slate-100">
        <Avatar bare size="sm" name={persona?.name} initials={persona?.avatar_initials} />
        <span className="text-sm text-pex-ink max-w-[9rem] xl:max-w-[16rem] truncate">{roleLabel(persona)}</span><ChevronDown className="w-3.5 h-3.5 text-slate-400" aria-hidden />
      </button>
      {open && (
        <div role="menu" aria-label="Switch demo persona" className="absolute right-0 mt-1 w-80 max-h-[70vh] overflow-y-auto bg-white border border-surface-line rounded-xl shadow-xl z-40 py-1">
          <div className="px-3 py-1.5 text-[11px] uppercase tracking-wide text-pex-muted">Switch role (demo)</div>
          {personas.map((p) => (
            <button key={p.user_id} role="menuitemradio" aria-checked={p.user_id === persona?.user_id} onClick={async () => { if (await switchTo(p)) setOpen(false); }}
              className={cn("w-full text-left px-3 py-2 flex items-center gap-2.5 hover:bg-slate-50", p.user_id === persona?.user_id && "bg-pex-primary-soft/50")}>
              <Avatar bare size="sm" name={p.name} initials={p.avatar_initials} />
              <span className="leading-tight"><span className="block text-sm text-pex-ink">{p.name}</span><span className="block text-xs text-pex-muted">{p.title} · {p.role}</span></span>
            </button>
          ))}
          {!personas.length && <div className="px-3 py-2 text-sm text-pex-muted">No personas available.</div>}
          <div className="border-t border-surface-line mt-1 pt-1"><button role="menuitem" onClick={() => { setOpen(false); signOut(); }} className="w-full text-left px-3 py-2 flex items-center gap-2 text-sm text-pex-ink hover:bg-slate-50"><LogOut className="w-4 h-4" aria-hidden />Sign out</button></div>
        </div>
      )}
    </div>
  );
};

const TopBar: React.FC = () => {
  const { info } = useSystemInfo();
  const { persona } = useSession();
  const [q, setQ] = useState("");
  const submit = (e: React.FormEvent) => { e.preventDefault(); if (q.trim()) navigate(routes.worklist({ q: q.trim() })); };
  return (
    <header className="h-14 glass border-b border-surface-line px-6 flex items-center gap-4 shrink-0 sticky top-0 z-30">
      <form onSubmit={submit} role="search" className="relative flex-1 max-w-md min-w-0">
        <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" aria-hidden />
        <label className="sr-only" htmlFor="pex-global-search">Search case, party or reference</label>
        <input id="pex-global-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search case, party or reference" className="w-full pl-9 pr-3 py-2 text-sm rounded-full bg-slate-100 border border-transparent focus:bg-white focus:border-surface-line" />
      </form>
      <div className="ml-auto flex items-center gap-3">
        {info?.operation_mode && <StatusPill tone={info.operation_mode === "LIVE" ? "red" : info.operation_mode === "ASSISTED" ? "amber" : "blue"} title="Operation mode">{info.operation_mode}</StatusPill>}
        {info?.bank_comm && <StatusPill tone="grey" title="Bank communication">Bank: {info.bank_comm}</StatusPill>}
        <StatusPill tone="amber" title="All data in this environment is synthetic">Demo data</StatusPill>
        <Clock />
        <TextSizeControl userId={persona?.user_id} />
        <ThemeControl />
        <ChasersBell />
        <PersonaMenu />
      </div>
    </header>
  );
};

const Sidebar: React.FC<{ route: Route }> = ({ route }) => {
  const { persona } = useSession();
  return (
    <nav aria-label="Main" className="w-16 lg:w-60 bg-surface border-r border-surface-line text-slate-600 flex flex-col shrink-0">
      <div className="h-14 px-4 lg:px-5 flex items-center gap-3">
        <span className="w-8 h-8 rounded-[9px] bg-pex-primary flex items-center justify-center font-semibold text-white text-sm">Px</span>
        <div className="leading-tight hidden lg:block"><div className="text-pex-ink font-semibold tracking-tight">PeX</div><div className="text-[11px] text-slate-500">Payment exceptions</div></div>
      </div>
      <ul className="px-2 lg:px-3 pt-3 space-y-0.5">
        {NAV.filter((n) => areaAllowed(n.area, persona?.role)).map((n) => {
          const active = route.area === n.area; const Icon = n.icon;
          return (
            <li key={n.area}>
              <a href={n.href} title={n.label} aria-current={active ? "page" : undefined}
                className={cn("flex items-center justify-center lg:justify-start gap-3 px-3 py-2 rounded-[10px] text-sm", active ? "bg-white text-pex-ink font-medium shadow-card" : "text-slate-600 hover:bg-white/70 hover:text-pex-ink")}>
                <Icon className={cn("w-[17px] h-[17px]", active && "text-pex-primary")} strokeWidth={1.75} aria-hidden /><span className="hidden lg:inline">{n.label}</span>
              </a>
            </li>
          );
        })}
      </ul>
      <div className="hidden lg:block mt-auto m-4 p-3 rounded-xl bg-white/60 border border-surface-line text-[11px] text-slate-500 leading-snug">AI recommends. Controls validate. Humans authorize when required. Bank systems execute.</div>
    </nav>
  );
};

export const Shell: React.FC<{ render: (route: Route) => React.ReactNode }> = ({ render }) => {
  const route = useRoute();
  const { persona, note, ready } = useSession();
  if (!ready) return <div className="min-h-screen bg-surface" aria-busy="true" />;
  if (!persona) return <Login />;
  const allowed = route.kind === "case" || areaAllowed(route.area, persona?.role); // case links are readable by every role (server decides what it shows)
  return (
    <div className="flex h-screen overflow-hidden font-sans bg-surface text-pex-ink">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-white focus:p-2">Skip to content</a>
      <Sidebar route={route} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        {note && <div className="px-6 pt-3"><Banner tone="amber">{note}</Banner></div>}
        <main id="main" className="flex-1 overflow-y-auto px-8 py-6">
          {persona && !allowed
            ? <Banner tone="amber" title="Not available for your role" action={<a className="text-sm font-medium underline" href="#/home">Go home</a>}>{persona.title} ({persona.role}) cannot open this area. Switch persona from the top right to see it.</Banner>
            : render(route)}
        </main>
        {/* Bottom pane: page action bars are drawn here, outside the scrolling area, so nothing scrolls behind them. */}
        <div id="action-dock" className="shrink-0 empty:hidden" />
      </div>
    </div>
  );
};
