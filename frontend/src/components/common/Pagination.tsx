import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface Props {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
  compact?: boolean;
}

export const Pagination: React.FC<Props> = ({ total, limit, offset, onChange, compact }) => {
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.max(1, Math.ceil(total / limit));
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(total, offset + limit);
  const btn = "p-1 rounded border border-slate-200 text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:hover:bg-transparent";
  return (
    <div className="flex items-center justify-between text-[11px] text-slate-500 px-3 py-2">
      <span>{compact ? `${from}-${to} / ${total.toLocaleString()}` : `Showing ${from.toLocaleString()}-${to.toLocaleString()} of ${total.toLocaleString()}`}</span>
      <div className="flex items-center space-x-2">
        <button className={btn} disabled={page <= 1} onClick={() => onChange(Math.max(0, offset - limit))} aria-label="Previous page">
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="font-mono">{page} / {pages}</span>
        <button className={btn} disabled={page >= pages} onClick={() => onChange(offset + limit)} aria-label="Next page">
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
