import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT, PALETTE } from "../chart-defaults";
import type { RendererProps, TimeSeriesData } from "./types";

const COLORS = [PALETTE.primary, PALETTE.secondary, PALETTE.muted, PALETTE.accent];

export default function TimeSeriesRenderer({ data, yAxis }: RendererProps<TimeSeriesData>) {
  const traces = data.series.map((s, i) => ({
    x: s.values.map((v) => v.date),
    y: s.values.map((v) => v.value),
    type: "scatter" as const,
    mode: "lines" as const,
    name: s.name,
    line: { color: COLORS[i % COLORS.length], width: 1.5 },
  }));

  const annotations = data.series.map((s, i) => {
    const last = s.values[s.values.length - 1];
    return {
      x: last?.date,
      y: last?.value,
      xref: "x" as const,
      yref: "y" as const,
      text: s.name,
      showarrow: false,
      xanchor: "left" as const,
      font: { size: 11, color: COLORS[i % COLORS.length] },
      xshift: 6,
    };
  });

  return (
    <Plot
      data={traces}
      layout={{
        ...BASE_LAYOUT,
        height: CHART_HEIGHT,
        annotations,
        margin: { ...BASE_LAYOUT.margin, r: 60 },
        xaxis: { ...BASE_LAYOUT.xaxis, type: "date" },
        yaxis: {
          ...BASE_LAYOUT.yaxis,
          ...(yAxis?.type === "currency" ? { tickprefix: "$", tickformat: ",.0f" } : {}),
          ...(yAxis?.type === "percent" ? { tickformat: ".1%" } : {}),
        },
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
