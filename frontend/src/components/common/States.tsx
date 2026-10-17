import React from "react";
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";

export const EmptyState: React.FC<{ title: string; hint?: string; action?: React.ReactNode }> = ({ title, hint, action }) => (
  <div className="flex flex-col items-center justify-center text-center py-12 px-6 text-slate-500">
    <Inbox className="w-8 h-8 text-slate-300 mb-2" />
    <div className="text-sm font-semibold text-slate-600">{title}</div>
    {hint && <div className="text-xs mt-1 max-w-sm">{hint}</div>}
    {action && <div className="mt-3">{action}</div>}
  </div>
);

export const ErrorState: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div className="flex flex-col items-center justify-center text-center py-10 px-6">
    <AlertTriangle className="w-7 h-7 text-red-400 mb-2" />
    <div className="text-sm font-semibold text-red-700">Something went wrong</div>
    <div className="text-xs text-slate-500 mt-1 max-w-md break-words">{message}</div>
    {onRetry && (
      <button onClick={onRetry} className="mt-3 px-3 py-1 text-xs rounded-md border border-slate-300 hover:bg-slate-100 text-slate-700">
        Retry
      </button>
    )}
  </div>
);

export const LoadingState: React.FC<{ label?: string }> = ({ label = "Loading..." }) => (
  <div className="flex items-center justify-center py-10 text-xs text-slate-400">
    <Loader2 className="w-4 h-4 animate-spin mr-2" />
    {label}
  </div>
);
