import type { StatusTone } from "../../lib/statusMeta";
import type { JourneyStep } from "../../components/v2";
import type { JourneyV2 } from "../../services/v2/compliance";

/** HH:MM (UTC, as the contract provides timestamps in UTC). */
export const hhmm = (iso?: string | null): string => {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
};
export const hhmmss = (iso?: string | null): string => {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return `${hhmm(iso)}:${String(d.getUTCSeconds()).padStart(2, "0")}`;
};
const TONES: Record<string, StatusTone> = { info: "blue", blue: "blue", warn: "amber", amber: "amber", success: "green", green: "green", danger: "red", red: "red", neutral: "grey", grey: "grey", lock: "grey" };
export const tone = (t?: string, fallback: StatusTone = "grey"): StatusTone => (t && TONES[t]) || fallback;

export const mapJourney = (j?: JourneyV2): JourneyStep[] =>
  (j?.steps ?? []).map((s) => ({
    id: s.key, label: s.label, state: s.state, at: hhmm(s.at) || undefined, note: s.note ?? undefined,
    actor: s.actor ? { name: s.actor, role: s.role, system: s.role === "System" || s.actor === "PeX" } : undefined,
  }));
