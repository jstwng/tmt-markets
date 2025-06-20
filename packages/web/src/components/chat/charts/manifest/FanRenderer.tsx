import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT, PALETTE } from "../chart-defaults";
import type { RendererProps, FanData } from "./types";

export default function FanRenderer({ data }: RendererProps<FanData>) {
  // Sort percentiles ascending
  const sorted = [...data.percentiles].sort((a, b) => a.p - b.p);
  const median = sorted.find((p) => p.p === 50);

  // Build filled bands: pair outer percentiles symmetrically
  const traces: object[] = [];
  const n = sorted.length;

  for (let i = 0; i < Math.floor(n / 2); i++) {
    const lower = sorted[i];
    const upper = sorted[n - 1 - i];
    const opacity = 0.1 + (i / n) * 0.2;

    // Upper bound (invisible line)
    traces.push({
      x: data.dates,
      y: upper.values,
      type: "scatter",
      mode: "lines",
      line: { width: 0 },
      showlegend: false,
      hoverinfo: "skip",
    });

    // Lower bound filled to upper
    traces.push({
      x: data.dates,
      y: lower.values,
      type: "scatter",
      mode: "lines",
      fill: "tonexty",
      fillcolor: `rgba(37, 99, 235, ${opacity})`,
      line: { width: 0 },
      name: `p${lower.p}–p${upper.p}`,
      showlegend: false,
    });
  }

  // Median line on top
  if (median) {
    traces.push({
      x: data.dates,
      y: median.values,
      type: "scatter",
      mode: "lines",
      line: { color: PALETTE.primary, width: 2 },
      name: "Median (p50)",
    });
  }

  return (
    <Plot
      data={traces as any[]}
      layout={{
        ...BASE_LAYOUT,
        height: CHART_HEIGHT,
        xaxis: { ...BASE_LAYOUT.xaxis, type: "date" },
        yaxis: { ...BASE_LAYOUT.yaxis, tickprefix: "$", tickformat: ",.0f" },
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
