import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT, PALETTE } from "../chart-defaults";
import type { RendererProps, BarData } from "./types";

const COLORS = [PALETTE.primary, PALETTE.accent, PALETTE.secondary, PALETTE.muted];

export default function BarRenderer({ data }: RendererProps<BarData>) {
  const traces = data.series.map((s, i) => ({
    x: data.categories,
    y: s.values,
    type: "bar" as const,
    name: s.name,
    marker: { color: COLORS[i % COLORS.length] },
  }));

  return (
    <Plot
      data={traces}
      layout={{
        ...BASE_LAYOUT,
        height: CHART_HEIGHT,
        barmode: data.series.length > 1 ? "group" : undefined,
        showlegend: data.series.length > 1,
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
