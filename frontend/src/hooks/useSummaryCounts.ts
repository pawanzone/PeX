import { useCallback, useEffect, useState } from "react";
import { fetchSummaryCounts } from "../services/api";
import { SummaryCounts } from "../types";

export function useSummaryCounts(refreshMs = 15000) {
  const [counts, setCounts] = useState<SummaryCounts | null>(null);
  const refresh = useCallback(async () => {
    try { setCounts(await fetchSummaryCounts()); } catch { /* keep last value */ }
  }, []);
  useEffect(() => {
    refresh();
    const t = window.setInterval(refresh, refreshMs);
    return () => window.clearInterval(t);
  }, [refresh, refreshMs]);
  return { counts, refresh };
}
