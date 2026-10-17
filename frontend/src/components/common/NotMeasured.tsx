import React from "react";

export const NOT_MEASURED_TIP = "Demo data, not computed from bank outcomes";

export const NotMeasured: React.FC<{ className?: string }> = ({ className = "" }) => (
  <span title={NOT_MEASURED_TIP} className={`text-slate-400 font-semibold cursor-help ${className}`}>
    Not measured
  </span>
);

/** Shows value only when the backend flags it as measured; otherwise "Not measured". */
export function MeasuredValue({ measured, value, className }: { measured?: boolean; value: React.ReactNode; className?: string }) {
  return measured ? <span className={className}>{value}</span> : <NotMeasured className={className} />;
}
