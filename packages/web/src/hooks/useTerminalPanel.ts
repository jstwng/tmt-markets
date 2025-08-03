import { useCallback, useEffect, useRef, useState } from "react";
import { getTerminalPanel } from "@/api/client";
import type { TerminalPanelResponse } from "@/api/client";

type Panel = "macro" | "indices" | "movers" | "heatmap" | "calendar";

export function useTerminalPanel(panel: Panel, intervalMs: number) {
  const [data, setData] = useState<TerminalPanelResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchPanel = useCallback(async () => {
    try {
      const ttl = Math.floor(intervalMs / 1000);
      const result = await getTerminalPanel(panel, ttl);
      setData(result);
      setLastUpdated(new Date());
      if (result.error) {
        setError(result.error_message ?? "Failed to load panel data");
      } else {
        setError(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setLoading(false);
    }
  }, [panel, intervalMs]);

  useEffect(() => {
    setLoading(true);
    fetchPanel();

    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(fetchPanel, intervalMs);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchPanel]);

  return { data, loading, error, lastUpdated, refetch: fetchPanel };
}
