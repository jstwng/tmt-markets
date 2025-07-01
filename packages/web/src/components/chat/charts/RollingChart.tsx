import Plot from "@/components/Plot";
import type { RollingMetricsData } from "@/api/chat-types";
import { BASE_LAYOUT, BASE_CONFIG } from "./chart-defaults";

interface RollingChartProps {
  data: RollingMetricsData;
}

export default function RollingChart({ data }: RollingChartProps) {
  const { dates, rolling_sharpe, rolling_volatility, rolling_drawdown } = data;

  const traces: Plotly.Data[] = [
    {
      x: dates,
      y: rolling_sharpe,
      type: "scatter",
      mode: "lines",
      name: "Sharpe",
      line: { color: "#000000", width: 1.5 },
    },
    {
      x: dates,
      y: rolling_volatility,
      type: "scatter",
      mode: "lines",
      name: "Volatility",
      line: { color: "#555555", width: 1, dash: "dot" },
    },
    {
      x: dates,
      y: rolling_drawdown,
      type: "scatter",
      mode: "lines",
      name: "Drawdown",
      line: { color: "#999999", width: 1 },
      fill: "tozeroy",
      fillcolor: "rgba(153,153,153,0.08)",
    },
  ];

  const layout: Partial<Plotly.Layout> = {
    ...BASE_LAYOUT,
    showlegend: true,
    legend: { orientation: "h", y: -0.15, font: { size: 11 } },
    xaxis: { ...BASE_LAYOUT.xaxis, tickangle: -30 },
    yaxis: { ...BASE_LAYOUT.yaxis },
    margin: { t: 16, r: 16, b: 48, l: 48 },
    height: 300,
  };

  return (
    <Plot
      data={traces}
      layout={layout}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
