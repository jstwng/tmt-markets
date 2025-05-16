import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT, PALETTE } from "./chart-defaults";
import type { FrontierData } from "@/api/chat-types";

interface EfficientFrontierProps {
  data: FrontierData;
}

export default function EfficientFrontier({ data }: EfficientFrontierProps) {
  const vols = data.points.map((p) => p.volatility * 100);
  const rets = data.points.map((p) => p.expected_return * 100);
  const sharpes = data.points.map((p) => p.sharpe);

  const maxSharpePoint = data.points[data.max_sharpe_idx];

  return (
    <Plot
      data={[
        // Frontier curve
        {
          x: vols,
          y: rets,
          type: "scatter",
          mode: "lines",
          line: { color: PALETTE.muted, width: 1.5 },
          name: "Frontier",
          hovertemplate:
            "Vol: %{x:.2f}%<br>Return: %{y:.2f}%<br>Sharpe: %{customdata:.3f}<extra></extra>",
          customdata: sharpes,
        },
        // Max-Sharpe point
        ...(maxSharpePoint
          ? [
              {
                x: [maxSharpePoint.volatility * 100],
                y: [maxSharpePoint.expected_return * 100],
                type: "scatter" as const,
                mode: "markers+text" as const,
                marker: { color: PALETTE.primary, size: 8, symbol: "circle" },
                text: [`Sharpe ${maxSharpePoint.sharpe.toFixed(2)}`],
                textposition: "top center" as const,
                textfont: { size: 11 },
                name: "Max Sharpe",
                hovertemplate:
                  "Max Sharpe<br>Vol: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>",
              },
            ]
          : []),
      ]}
      layout={{
        ...BASE_LAYOUT,
        height: CHART_HEIGHT,
        xaxis: {
          ...BASE_LAYOUT.xaxis,
          title: { text: "Annualized Volatility (%)", font: { size: 11 } },
          ticksuffix: "%",
        },
        yaxis: {
          ...BASE_LAYOUT.yaxis,
          title: { text: "Annualized Return (%)", font: { size: 11 } },
          ticksuffix: "%",
        },
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
