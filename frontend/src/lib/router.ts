/** Dependency-free hash router. Routes: #/home, #/worklist, #/worklist/case/<id>, #/approvals,
 *  #/compliance, #/compliance/case/<id>, #/batches, #/batches/<id>, #/audit, #/admin/<section>. */
import { useEffect, useState, useCallback } from "react";

export type Area = "dashboard" | "home" | "worklist" | "approvals" | "compliance" | "batches" | "audit" | "admin" | "policy" | "network" | "director";
export const AREAS: Area[] = ["dashboard", "home", "worklist", "approvals", "compliance", "batches", "audit", "admin", "policy", "network", "director"];

export interface Route {
  area: Area;
  /** case id or batch id */
  id?: string;
  /** admin section, e.g. integrations | reference | components */
  section?: string;
  /** sub-kind, "case" for case routes */
  kind?: "case";
  query: Record<string, string>;
  raw: string;
}

export function parseHash(hash: string): Route {
  const raw = (hash || "").replace(/^#/, "") || "/dashboard";
  const [pathPart, qs = ""] = raw.split("?");
  const parts = pathPart.split("/").filter(Boolean).map(decodeURIComponent);
  const query: Record<string, string> = {};
  new URLSearchParams(qs).forEach((v, k) => { query[k] = v; });
  const first = (parts[0] as Area) || "dashboard";
  const area: Area = AREAS.includes(first) ? first : "dashboard";
  const r: Route = { area, query, raw };
  if ((area === "worklist" || area === "compliance") && parts[1] === "case" && parts[2]) { r.kind = "case"; r.id = parts[2]; }
  else if ((area === "batches" || area === "network") && parts[1]) r.id = parts[1];
  else if (area === "admin") r.section = parts[1] || "integrations";
  if (area === "admin" && parts[1] === "reference" && parts[2]) r.id = parts[2];
  return r;
}

const q = (query?: Record<string, string>) => {
  const s = query ? new URLSearchParams(query).toString() : "";
  return s ? `?${s}` : "";
};
const e = encodeURIComponent;

export const routes = {
  dashboard: () => "#/dashboard",
  home: () => "#/home",
  worklist: (query?: Record<string, string>) => `#/worklist${q(query)}`,
  workCase: (id: string) => `#/worklist/case/${e(id)}`,
  approvals: (query?: Record<string, string>) => `#/approvals${q(query)}`,
  compliance: () => "#/compliance",
  complianceCase: (id: string) => `#/compliance/case/${e(id)}`,
  batches: () => "#/batches",
  batch: (id: string) => `#/batches/${e(id)}`,
  audit: (query?: Record<string, string>) => `#/audit${q(query)}`,
  policy: () => "#/policy",
  network: (id?: string) => `#/network${id ? "/" + e(id) : ""}`,
  admin: (section = "integrations") => `#/admin/${e(section)}`,
  adminReference: (screen?: string) => `#/admin/reference${screen ? "/" + e(screen) : ""}`,
};

export function navigate(hash: string): void { window.location.hash = hash; }

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash));
  useEffect(() => {
    const on = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

/** Update only the query string of the current route (filters, tabs) without adding history entries. */
export function useQueryParam(key: string, fallback = ""): [string, (v: string) => void] {
  const route = useRoute();
  const value = route.query[key] ?? fallback;
  const set = useCallback((v: string) => {
    const base = window.location.hash.replace(/^#/, "").split("?")[0] || "/dashboard";
    const params = new URLSearchParams(window.location.hash.split("?")[1] || "");
    if (v && v !== fallback) params.set(key, v); else params.delete(key);
    const s = params.toString();
    window.history.replaceState(null, "", `#${base}${s ? "?" + s : ""}`);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  }, [key, fallback]);
  return [value, set];
}
