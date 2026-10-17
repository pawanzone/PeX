import React from "react";

export const SimulatedChip: React.FC<{ className?: string }> = ({ className = "" }) => (
  <span
    title="Simulated. No real bank traffic is generated."
    className={`inline-flex items-center px-1.5 py-0.5 rounded border border-amber-300 bg-amber-50 text-amber-700 text-[9px] font-bold font-mono tracking-wide ${className}`}
  >
    SIMULATED
  </span>
);

/** Renders backend text; any "[SIMULATED]" marker becomes a chip instead of raw text. */
export const SimText: React.FC<{ text?: string | null; className?: string }> = ({ text, className }) => {
  if (!text) return null;
  const parts = text.split(/\[SIMULATED\]/gi);
  if (parts.length === 1) return <span className={className}>{text}</span>;
  return (
    <span className={className}>
      {parts.map((p, i) => (
        <React.Fragment key={i}>
          {p}
          {i < parts.length - 1 && <SimulatedChip className="mx-1" />}
        </React.Fragment>
      ))}
    </span>
  );
};
