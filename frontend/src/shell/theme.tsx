import React, { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "lucide-react";

export type ThemeMode = "auto" | "light" | "dark";
const KEY = "pex.v2.theme";
export const loadTheme = (): ThemeMode => { try { const v = window.localStorage.getItem(KEY); if (v === "light" || v === "dark" || v === "auto") return v; } catch { /* ignore */ } return "auto"; };
/** "auto" follows the device setting; light / dark force it. The Tailwind palette reads [data-theme] (see tailwind.config.js). */
export const applyTheme = (m: ThemeMode) => { const el = document.documentElement; if (m === "auto") el.removeAttribute("data-theme"); else el.setAttribute("data-theme", m); };
applyTheme(loadTheme());

const NEXT: Record<ThemeMode, ThemeMode> = { auto: "light", light: "dark", dark: "auto" };
const LABEL: Record<ThemeMode, string> = { auto: "Appearance: match device", light: "Appearance: light", dark: "Appearance: dark" };

export const ThemeControl: React.FC = () => {
  const [mode, setMode] = useState<ThemeMode>(() => loadTheme());
  useEffect(() => { applyTheme(mode); }, [mode]);
  const Icon = mode === "light" ? Sun : mode === "dark" ? Moon : Monitor;
  const pick = () => { const n = NEXT[mode]; setMode(n); try { window.localStorage.setItem(KEY, n); } catch { /* ignore */ } };
  return (
    <button type="button" onClick={pick} title={`${LABEL[mode]} (click to change)`} aria-label={`${LABEL[mode]}. Click to change.`}
      className="w-8 h-8 inline-flex items-center justify-center rounded-full text-slate-500 hover:bg-slate-100 hover:text-pex-ink">
      <Icon className="w-4 h-4" aria-hidden />
    </button>
  );
};
