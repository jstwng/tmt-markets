import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { usePortfolioPerformance } from "@/hooks/usePortfolioPerformance";
import EquityCurve from "@/components/dashboard/EquityCurve";
import PositionsTable from "@/components/dashboard/PositionsTable";
import HoldingsPie from "@/components/dashboard/HoldingsPie";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

function usd(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

function pct(n: number) {
  return `${n >= 0 ? "+" : ""}${(n * 100).toFixed(2)}%`;
}

const TOTAL_VALUE_KEY = (id: string) => `portfolio_total_value_${id}`;

export default function Dashboard() {
  const { session } = useAuth();
  const token = session?.access_token;

  const {
    portfolios,
    selectedId,
    selectPortfolio,
    performance,
    slicedCurve,
    loading,
    error,
    period,
    setPeriod,
  } = usePortfolioPerformance(token);

  const [totalValue, setTotalValue] = useState<number>(100_000);
  const [valueInput, setValueInput] = useState<string>("$100,000");

  // Load persisted total value when portfolio changes
  useEffect(() => {
    if (!selectedId) return;
    const stored = localStorage.getItem(TOTAL_VALUE_KEY(selectedId));
    const val = stored ? parseFloat(stored) : 100_000;
    setTotalValue(val);
    setValueInput(
      new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(val)
    );
  }, [selectedId]);

  function handleValueBlur() {
    const cleaned = valueInput.replace(/[^0-9.]/g, "");
    const val = parseFloat(cleaned) || 100_000;
    setTotalValue(val);
    if (selectedId) localStorage.setItem(TOTAL_VALUE_KEY(selectedId), String(val));
    setValueInput(
      new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(val)
    );
  }

  const todayChange = performance
    ? performance.positions.reduce((acc, p) => acc + p.day_pct * p.weight, 0)
    : 0;
  const todayChangeDollar = todayChange * totalValue;
  const lastUpdated = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="py-6 space-y-4 max-w-4xl">
      {/* Selector bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground uppercase tracking-wide">Portfolio</span>
          <Select value={selectedId} onValueChange={selectPortfolio} disabled={portfolios.length === 0}>
            <SelectTrigger className="w-48 h-8 text-sm">
              <SelectValue placeholder={loading ? "Loading..." : "No portfolios"} />
            </SelectTrigger>
            <SelectContent>
              {portfolios.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Total Value</span>
          <input
            className="w-28 text-right text-sm font-semibold border border-border rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-foreground"
            value={valueInput}
            onChange={(e) => setValueInput(e.target.value)}
            onBlur={handleValueBlur}
            onKeyDown={(e) => e.key === "Enter" && handleValueBlur()}
          />
        </div>
      </div>

      {error && (
        <div className="text-sm text-red-600 border border-red-200 bg-red-50 rounded px-3 py-2">
          {error}
        </div>
      )}

      {/* Big portfolio value */}
      <div className="text-center py-2">
        <div className="text-4xl font-bold tracking-tight">{usd(totalValue)}</div>
        <div
          className={cn(
            "text-sm mt-1 font-medium",
            todayChange >= 0 ? "text-green-600" : "text-red-600"
          )}
        >
          {todayChange >= 0 ? "+" : ""}
          {usd(todayChangeDollar)} ({pct(todayChange)}) Today
        </div>
      </div>

      {/* Equity curve */}
      <EquityCurve
        curve={slicedCurve}
        period={period}
        onPeriodChange={setPeriod}
        loading={loading}
      />

      {/* Pie + stats */}
      <div className="grid grid-cols-2 gap-4">
        <HoldingsPie positions={performance?.positions ?? []} loading={loading} />
        <div className="grid grid-cols-2 gap-3">
          {[
            {
              label: "Total Return",
              value: performance ? pct(performance.stats.total_return) : "—",
              positive: (performance?.stats.total_return ?? 0) >= 0,
            },
            {
              label: "vs SPY",
              value: performance ? pct(performance.stats.alpha) : "—",
              positive: (performance?.stats.alpha ?? 0) >= 0,
            },
            {
              label: "Sharpe Ratio",
              value: performance ? performance.stats.sharpe.toFixed(2) : "—",
              positive: null,
            },
            {
              label: "Max Drawdown",
              value: performance ? pct(performance.stats.max_drawdown) : "—",
              positive: false,
            },
          ].map((stat) => (
            <div key={stat.label} className="border border-border rounded-lg p-3">
              <div className="text-xs text-muted-foreground">{stat.label}</div>
              <div
                className={cn(
                  "text-lg font-bold mt-1",
                  stat.positive === null
                    ? ""
                    : stat.positive
                    ? "text-green-600"
                    : "text-red-600"
                )}
              >
                {loading ? <div className="h-5 w-16 bg-muted/40 rounded animate-pulse" /> : stat.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Positions table */}
      <PositionsTable
        positions={performance?.positions ?? []}
        totalValue={totalValue}
        loading={loading}
      />

      <div className="text-xs text-muted-foreground text-right">
        Prices via yfinance · Last updated {lastUpdated}
      </div>
    </div>
  );
}
