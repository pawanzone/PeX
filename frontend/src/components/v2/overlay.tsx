import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "./primitives";

/** Accessible modal: role=dialog, Escape closes, focus moves in and returns, Tab is trapped. */
export const Modal: React.FC<{ open: boolean; title: string; onClose: () => void; children: React.ReactNode; footer?: React.ReactNode; width?: "md" | "lg" | "xl" }> = ({ open, title, onClose, children, footer, width = "lg" }) => {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    box.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { onClose(); return; }
      if (e.key !== "Tab" || !box.current) return;
      const f = Array.from(box.current.querySelectorAll<HTMLElement>("button,[href],input,select,textarea,[tabindex]:not([tabindex='-1'])")).filter((el) => !el.hasAttribute("disabled"));
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); prev?.focus(); };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div ref={box} role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} className={cn("bg-white rounded-card shadow-2xl w-full max-h-[90vh] flex flex-col outline-none", width === "md" ? "max-w-lg" : width === "lg" ? "max-w-3xl" : "max-w-5xl")}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-surface-line">
          <h2 className="text-lg font-semibold text-pex-ink">{title}</h2>
          <button aria-label="Close dialog" onClick={onClose} className="p-1 rounded hover:bg-slate-100"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-5 overflow-y-auto">{children}</div>
        {footer && <div className="px-5 py-3 border-t border-surface-line flex justify-end gap-2 bg-slate-50 rounded-b-card">{footer}</div>}
      </div>
    </div>
  );
};
