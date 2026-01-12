import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG } from "@/components/chat/charts/chart-defaults";
import type { PerformanceCurvePoint } from "@/api/client";
import type { Period } from "@/hooks/usePortfolioPerformance";
import { cn } from "@/lib/utils";

const PERIODS: Period[] = ["1m", "3m", "6m", "1y", "all"];

interface EquityCurveProps {
  curve: PerformanceCurvePoint[];
  period: Period;
  onPeriodChange: (p: Period) => void;
  loading?: boolean;
}

export default function EquityCurve({ curve, period, onPeriodChange, loading }: EquityCurveProps) {
  if (loading) {
    return (
      <div className="border border-border rounded-lg p-4">
        <div className="h-[200px] bg-muted/30 rounded animate-pulse" />
        <div className="flex justify-center gap-2 mt-3">
          {PERIODS.map((p) => (
            <div key={p} className="h-6 w-8 bg-muted/30 rounded-full animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const portfolioTrace = {
    x: curve.map((p) => p.date),
    y: curve.map((p) => p.value),
    type: "scatter" as const,
    mode: "lines" as const,
    name: "Portfolio",
    line: { color: "#111111", width: 2 },
    fill: "tozeroy" as const,
    fillcolor: "rgba(17,17,17,0.05)",
    hovertemplate: "%{x}<br>%{y:.1f}<extra>Portfolio</extra>",
  };

  const benchmarkTrace = {
    x: curve.map((p) => p.date),
    y: curve.map((p) => p.benchmark),
    type: "scatter" as const,
    mode: "lines" as const,
    name: "SPY",
    line: { color: "#cccccc", width: 1.5, dash: "dash" as const },
    hovertemplate: "%{x}<br>%{y:.1f}<extra>SPY</extra>",
  };

  return (
    <div className="border border-border rounded-lg p-4">
      <Plot
        data={[portfolioTrace, benchmarkTrace]}
        layout={{
          ...BASE_LAYOUT,
          height: 200,
          margin: { l: 48, r: 16, t: 32, b: 64 },
          showlegend: true,
          legend: { x: 0.5, y: -0.3, xanchor: "center" as const, yanchor: "top" as const, orientation: "h" as const, font: { size: 11 } },
          yaxis: {
            ...BASE_LAYOUT.yaxis,
            tickformat: ".0f",
            hoverformat: ".1f",
          },
          xaxis: {
            ...BASE_LAYOUT.xaxis,
            type: "date" as const,
          },
        }}
        config={BASE_CONFIG}
        style={{ width: "100%" }}
        useResizeHandler
      />
      <div className="flex justify-center gap-1 mt-2">
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => onPeriodChange(p)}
            className={cn(
              "text-xs px-3 py-1 rounded-full transition-colors",
              period === p
                ? "bg-foreground text-background"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {p.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );
}
