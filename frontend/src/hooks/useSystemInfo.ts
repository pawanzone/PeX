import { useEffect, useState } from "react";
import { fetchSystemInfo } from "../services/api";
import { SystemInfo } from "../types";

export function useSystemInfo(refreshMs = 30000) {
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const r = await fetchSystemInfo();
        if (alive) { setInfo(r); setError(null); }
      } catch (e: any) {
        if (alive) setError(e?.message || "unavailable");
      }
    };
    load();
    const t = window.setInterval(load, refreshMs);
    return () => { alive = false; window.clearInterval(t); };
  }, [refreshMs]);
  return { info, error };
}
