/**
 * Central HTTP client. Every request goes through apiFetch so the bearer token is attached in
 * exactly one place and failures are reported consistently.
 */
const API_BASE = "/api";
const TOKEN_KEY = "pex.token";

let memoryToken: string | null = null;

export function getToken(): string | null {
  if (memoryToken) return memoryToken;
  try {
    memoryToken = window.localStorage.getItem(TOKEN_KEY);
  } catch {
    /* storage may be unavailable; fall back to memory only */
  }
  return memoryToken;
}

export function setToken(token: string | null): void {
  memoryToken = token;
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
  get unavailable(): boolean {
    return this.status === 404 || this.status === 501 || this.status === 0;
  }
}

type Listener = (status: number) => void;
const authListeners = new Set<Listener>();
/** Subscribe to 401/403 responses (e.g. to show a "sign in again" prompt). */
export function onAuthProblem(fn: Listener): () => void {
  authListeners.add(fn);
  return () => authListeners.delete(fn);
}

export interface FetchOptions extends Omit<RequestInit, "body"> {
  json?: unknown;
  body?: BodyInit | null;
  query?: Record<string, string | number | boolean | undefined | null>;
  /** Return parsed body even for non-2xx (used by endpoints that report failure in the body). */
  tolerant?: boolean;
}

export function buildQuery(query?: FetchOptions["query"]): string {
  if (!query) return "";
  const q = new URLSearchParams();
  Object.entries(query).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "" || v === "All") return;
    q.set(k, String(v));
  });
  const s = q.toString();
  return s ? `?${s}` : "";
}

export async function apiFetch<T = any>(path: string, opts: FetchOptions = {}): Promise<T> {
  const { json, query, tolerant, headers, ...rest } = opts;
  const h = new Headers(headers);
  const token = getToken();
  if (token && !h.has("Authorization")) h.set("Authorization", `Bearer ${token}`);
  let body = rest.body;
  if (json !== undefined) {
    h.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}${buildQuery(query)}`, { ...rest, headers: h, body });
  } catch (e: any) {
    throw new ApiError(0, e?.message || "Network error: backend unreachable");
  }
  const contentType = res.headers.get("content-type") || "";
  let data: any = null;
  if (contentType.includes("application/json")) {
    try { data = await res.json(); } catch { data = null; }
  } else {
    try { data = await res.text(); } catch { data = null; }
  }
  if (!res.ok && !tolerant) {
    if (res.status === 401 || res.status === 403) authListeners.forEach((fn) => fn(res.status));
    const detail = data && typeof data === "object" ? (data.detail ?? data.message ?? data) : data;
    const msg = typeof detail === "string" ? detail : `Request failed (${res.status})`;
    throw new ApiError(res.status, msg, detail);
  }
  return data as T;
}

export async function apiDownload(path: string, filename: string): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!res.ok) throw new ApiError(res.status, `Download failed (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
