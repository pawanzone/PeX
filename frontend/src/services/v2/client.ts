/** v2 API client. Thin typed layer over services/http.ts (token handling, ApiError, 401/403 listeners).
 *  All v2 endpoints live under /api/v2/*. Endpoint-specific wrappers are added per docs/ui_v2_api_contract.md. */
import { apiFetch, ApiError } from "../http";
import { useCallback, useEffect, useRef, useState } from "react";

export { ApiError };
const P = "/v2";

export type Query = Record<string, string | number | boolean | undefined | null>;
const qs = (q?: Query) => {
  if (!q) return "";
  const p = new URLSearchParams();
  Object.entries(q).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") p.set(k, String(v)); });
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const v2Get = <T,>(path: string, query?: Query) => apiFetch<T>(`${P}${path}${qs(query)}`);
export const v2Post = <T,>(path: string, json?: unknown) => apiFetch<T>(`${P}${path}`, { method: "POST", json: json ?? {} });
export const v2Put = <T,>(path: string, json?: unknown) => apiFetch<T>(`${P}${path}`, { method: "PUT", json: json ?? {} });

export interface Resource<T> { data: T | null; loading: boolean; error: string | null; unavailable: boolean; reload: () => void }

/** Fetch-on-mount/deps hook. Ignores stale responses. `unavailable` is true on 404/501 (endpoint not built). */
export function useV2<T>(loader: () => Promise<T>, deps: unknown[] = []): Resource<T> {
  const [state, setState] = useState<{ data: T | null; loading: boolean; error: string | null; unavailable: boolean }>({ data: null, loading: true, error: null, unavailable: false });
  const seq = useRef(0);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  useEffect(() => {
    const id = ++seq.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    loader().then(
      (data) => { if (id === seq.current) setState({ data, loading: false, error: null, unavailable: false }); },
      (e: any) => { if (id === seq.current) setState({ data: null, loading: false, error: e?.message || "Request failed", unavailable: !!e?.unavailable }); }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { ...state, reload };
}

/** Run a mutation; returns [run, {busy, error}]. */
export function useAction<A extends unknown[], R>(fn: (...a: A) => Promise<R>) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(async (...a: A): Promise<R | undefined> => {
    setBusy(true); setError(null);
    try { return await fn(...a); }
    catch (e: any) { setError(e?.message || "Action failed"); return undefined; }
    finally { setBusy(false); }
  }, [fn]);
  return [run, { busy, error }] as const;
}
