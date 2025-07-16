import { useCallback, useEffect, useMemo, useState } from "react";
import { listPortfolios, getPortfolioPerformance } from "@/api/client";
import type { Portfolio, PortfolioPerformance, PerformanceCurvePoint } from "@/api/client";

export type Period = "1m" | "3m" | "6m" | "1y" | "all";

const PERIOD_DAYS: Record<Period, number | null> = {
  "1m": 30,
  "3m": 90,
  "6m": 180,
  "1y": 365,
  "all": null,
};

export function usePortfolioPerformance(token: string | undefined) {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<Period>("1m");

  // Load portfolio list on mount
  useEffect(() => {
    if (!token) return;
    listPortfolios(token)
      .then((list) => {
        setPortfolios(list);
        if (list.length > 0) setSelectedId(list[0].id);
      })
      .catch((e) => setError(e.message));
  }, [token]);

  // Fetch performance when selected portfolio changes
  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    getPortfolioPerformance(token, selectedId)
      .then(setPerformance)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, selectedId]);

  const slicedCurve = useMemo((): PerformanceCurvePoint[] => {
    if (!performance) return [];
    const days = PERIOD_DAYS[period];
    if (days === null) return performance.curve;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString().slice(0, 10);
    return performance.curve.filter((p) => p.date >= cutoffStr);
  }, [performance, period]);

  const selectPortfolio = useCallback((id: string) => {
    setSelectedId(id);
  }, []);

  return {
    portfolios,
    selectedId,
    selectPortfolio,
    performance,
    slicedCurve,
    loading,
    error,
    period,
    setPeriod,
  };
}
