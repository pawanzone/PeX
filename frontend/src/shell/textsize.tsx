import React, { useEffect, useState } from "react";
import { cn } from "../components/v2";

export type TextSize = "normal" | "large" | "xlarge";
const PX: Record<TextSize, number> = { normal: 16, large: 18, xlarge: 20 };
const KEY = (uid?: string) => `pex.v2.textsize.${uid || "anon"}`;
export const loadTextSize = (uid?: string): TextSize => { try { const v = window.localStorage.getItem(KEY(uid)); if (v === "large" || v === "xlarge" || v === "normal") return v; } catch { /* ignore */ } return "normal"; };
export const applyTextSize = (s: TextSize) => { document.documentElement.style.fontSize = PX[s] + "px"; document.documentElement.dataset.textsize = s; };

/** Three steps (A, A+, A++), remembered per user. Everything is sized in rem, so the whole screen scales. */
export const TextSizeControl: React.FC<{ userId?: string }> = ({ userId }) => {
  const [size, setSize] = useState<TextSize>(() => loadTextSize(userId));
  useEffect(() => { const s = loadTextSize(userId); setSize(s); applyTextSize(s); }, [userId]);
  const pick = (s: TextSize) => { setSize(s); applyTextSize(s); try { window.localStorage.setItem(KEY(userId), s); } catch { /* ignore */ } };
  const opts: Array<[TextSize, string, string]> = [["normal", "A", "Normal text size"], ["large", "A+", "Larger text"], ["xlarge", "A++", "Largest text"]];
  return (
    <div role="group" aria-label="Text size" className="inline-flex rounded-lg border border-surface-line overflow-hidden">
      {opts.map(([k, label, title]) => (
        <button key={k} type="button" aria-pressed={size === k} aria-label={title} title={title} onClick={() => pick(k)}
          className={cn("px-2 py-1 text-xs font-semibold", size === k ? "bg-pex-primary text-white" : "bg-white text-pex-muted hover:bg-slate-50")}>{label}</button>
      ))}
    </div>
  );
};
