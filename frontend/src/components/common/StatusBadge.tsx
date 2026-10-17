import React from "react";
import { statusMeta, TONE_CLASSES } from "../../lib/statusMeta";

export const StatusBadge: React.FC<{ status: unknown; short?: boolean; className?: string }> = ({ status, short, className = "" }) => {
  const m = statusMeta(status);
  const t = TONE_CLASSES[m.tone];
  return (
    <span
      title={m.description}
      className={`inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-md border text-[10px] font-semibold ${t.chip} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${t.dot}`} />
      <span>{short ? m.short : m.label}</span>
    </span>
  );
};
