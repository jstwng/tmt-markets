import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT, PALETTE } from "../chart-defaults";
import type { RendererProps, AreaData } from "./types";

const COLORS = [PALETTE.primary, PALETTE.accent, PALETTE.secondary, PALETTE.muted];

export default function AreaRenderer({ data }: RendererProps<AreaData>) {
  const traces = data.series.map((s, i) => ({
    x: s.values.map((v) => v.date),
    y: s.values.map((v) => v.value),
    type: "scatter" as const,
    mode: "lines" as const,
    name: s.name,
    fill: "tozeroy" as const,
    stackgroup: data.stacked ? "one" : undefined,
    line: { color: COLORS[i % COLORS.length], width: 1 },
    fillcolor: COLORS[i % COLORS.length] + "33",
  }));

  return (
    <Plot
      data={traces}
      layout={{
        ...BASE_LAYOUT,
        height: CHART_HEIGHT,
        showlegend: data.series.length > 1,
        xaxis: { ...BASE_LAYOUT.xaxis, type: "date" },
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
