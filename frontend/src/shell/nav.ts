import { LayoutDashboard, Home, ListChecks, ShieldCheck, Scale, Layers, ScrollText, Settings, SlidersHorizontal, type LucideIcon } from "lucide-react";
import type { Area } from "../lib/router";
import type { UserPersona } from "../types";

export interface NavDef { area: Area; label: string; icon: LucideIcon; href: string }
export const NAV: NavDef[] = [
  { area: "dashboard", label: "Dashboard", icon: LayoutDashboard, href: "#/dashboard" },
  { area: "home", label: "My work", icon: Home, href: "#/home" },
  { area: "worklist", label: "Worklist", icon: ListChecks, href: "#/worklist" },
  { area: "approvals", label: "Approvals", icon: ShieldCheck, href: "#/approvals" },
  { area: "compliance", label: "Compliance", icon: Scale, href: "#/compliance" },
  { area: "batches", label: "Batches", icon: Layers, href: "#/batches" },
  { area: "audit", label: "Audit", icon: ScrollText, href: "#/audit" },
  { area: "policy", label: "Policy Studio", icon: SlidersHorizontal, href: "#/policy" },
  { area: "admin", label: "Admin", icon: Settings, href: "#/admin/integrations" },
];

/** Role-aware visibility, mirroring the server's GET /api/v2/me nav table (backend/app/services/v2/core.py NAV).
 *  UI hiding is a convenience only; the server enforces every permission. Unknown roles see Home only. */
const ROLE_AREAS: Record<string, Area[]> = {
  OPERATOR: ["dashboard", "home", "worklist", "batches"],
  SUPERVISOR: ["dashboard", "home", "worklist", "approvals", "compliance", "batches", "audit"],
  OPERATIONS_APPROVER: ["dashboard", "home", "approvals", "worklist", "batches"],
  RISK_APPROVER: ["dashboard", "home", "approvals", "compliance", "worklist", "batches"],
  COMPLIANCE_APPROVER: ["dashboard", "home", "compliance", "audit"],
  AUDIT_RISK: ["dashboard", "home", "audit"],
  ADMIN: ["dashboard", "home", "batches", "audit", "admin"],
  POLICY_OWNER: ["dashboard", "policy", "admin", "audit"],
};
export function areaAllowed(area: Area, role?: string): boolean {
  const r = (role || "").toUpperCase();
  if (!r) return area === "home" || area === "dashboard";
  const list = ROLE_AREAS[r];
  if (!list) return area === "home" || area === "dashboard" || area === "worklist"; // legacy personas (OP-8472 etc.)
  return list.includes(area);
}
export const roleLabel = (p: UserPersona | null) => (p ? `${p.name} · ${p.title || p.role}` : "Not signed in");
