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
      <button aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-lg hover:bg-slate-100">
        <Avatar bare size="sm" name={persona?.name} initials={persona?.avatar_initials} />
        <span className="text-sm text-pex-ink max-w-[9rem] xl:max-w-[16rem] truncate">{roleLabel(persona)}</span><ChevronDown className="w-3.5 h-3.5 text-slate-400" aria-hidden />
      </button>
      {open && (
        <div role="menu" aria-label="Switch demo persona" className="absolute right-0 mt-1 w-80 max-h-[70vh] overflow-y-auto bg-white border border-surface-line rounded-lg shadow-xl z-40 py-1">
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
    <header className="h-14 bg-white border-b border-surface-line px-5 flex items-center gap-4 shrink-0">
      <form onSubmit={submit} role="search" className="relative flex-1 max-w-md">
        <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" aria-hidden />
        <label className="sr-only" htmlFor="pex-global-search">Search case, party or reference</label>
        <input id="pex-global-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search case, party or reference" className="w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-slate-100 border border-transparent focus:bg-white focus:border-surface-line" />
      </form>
      <div className="ml-auto flex items-center gap-3">
        {info?.operation_mode && <StatusPill tone={info.operation_mode === "LIVE" ? "red" : info.operation_mode === "ASSISTED" ? "amber" : "blue"} title="Operation mode">{info.operation_mode}</StatusPill>}
        {info?.bank_comm && <StatusPill tone="grey" title="Bank communication">Bank: {info.bank_comm}</StatusPill>}
        <StatusPill tone="amber" title="All data in this environment is synthetic">Demo data</StatusPill>
        <Clock />
        <TextSizeControl userId={persona?.user_id} />
        <ChasersBell />
        <PersonaMenu />
      </div>
    </header>
  );
};

const Sidebar: React.FC<{ route: Route }> = ({ route }) => {
  const { persona } = useSession();
  return (
    <nav aria-label="Main" className="w-56 bg-navy-800 text-slate-200 flex flex-col shrink-0">
      <div className="h-14 px-5 flex items-center gap-2.5 border-b border-white/10">
        <span className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center font-bold text-white">P</span>
        <div className="leading-tight"><div className="text-white font-semibold">PeX</div><div className="text-[10px] text-slate-400">Payment Exception Resolution</div></div>
      </div>
      <ul className="p-3 space-y-1">
        {NAV.filter((n) => areaAllowed(n.area, persona?.role)).map((n) => {
          const active = route.area === n.area; const Icon = n.icon;
          return (
            <li key={n.area}>
              <a href={n.href} aria-current={active ? "page" : undefined} className={cn("flex items-center gap-3 px-3 py-2 rounded-lg text-sm", active ? "bg-white/15 text-white font-medium" : "text-slate-300 hover:bg-white/10")}>
                <Icon className="w-4 h-4" aria-hidden />{n.label}
              </a>
            </li>
          );
        })}
      </ul>
      <div className="mt-auto p-4 text-[11px] text-slate-400 leading-snug border-t border-white/10">AI recommends. Controls validate. Humans authorize when required. Bank systems execute.</div>
    </nav>
  );
};

export const Shell: React.FC<{ render: (route: Route) => React.ReactNode }> = ({ render }) => {
  const route = useRoute();
  const { persona, note, ready } = useSession();
  if (!ready) return <div className="min-h-screen bg-navy-800" aria-busy="true" />;
  if (!persona) return <Login />;
  const allowed = route.kind === "case" || areaAllowed(route.area, persona?.role); // case links are readable by every role (server decides what it shows)
  return (
    <div className="flex h-screen overflow-hidden font-sans bg-surface text-pex-ink">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-white focus:p-2">Skip to content</a>
      <Sidebar route={route} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        {note && <div className="px-6 pt-3"><Banner tone="amber">{note}</Banner></div>}
        <main id="main" className="flex-1 overflow-y-auto px-6 py-5">
          {persona && !allowed
            ? <Banner tone="amber" title="Not available for your role" action={<a className="text-sm font-medium underline" href="#/home">Go home</a>}>{persona.title} ({persona.role}) cannot open this area. Switch persona from the top right to see it.</Banner>
            : render(route)}
        </main>
      </div>
    </div>
  );
};
