import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT, PALETTE } from "../chart-defaults";
import type { RendererProps, ScatterData } from "./types";

const COLORS = [PALETTE.primary, PALETTE.accent, PALETTE.secondary, PALETTE.muted];

export default function ScatterRenderer({ data, xAxis, yAxis, annotations }: RendererProps<ScatterData>) {
  const traces = data.series.map((s, i) => ({
    x: s.points.map((p) => p.x),
    y: s.points.map((p) => p.y),
    text: s.points.map((p) => p.label ?? ""),
    type: "scatter" as const,
    mode: "markers" as const,
    name: s.name,
    marker: { color: COLORS[i % COLORS.length], size: 6 },
    hovertemplate: "%{text}<br>x: %{x:.4f}<br>y: %{y:.4f}<extra></extra>",
  }));

  const plotAnnotations = (annotations ?? []).map((a) => ({
    x: a.type === "point" ? a.value : undefined,
    y: a.value,
    text: a.label ?? "",
    showarrow: a.type === "point",
    font: { size: 11, color: a.color ?? PALETTE.accent },
  }));

  return (
    <Plot
      data={traces}
      layout={{
        ...BASE_LAYOUT,
        height: CHART_HEIGHT,
        showlegend: data.series.length > 1,
        annotations: plotAnnotations,
        xaxis: {
          ...BASE_LAYOUT.xaxis,
          title: { text: xAxis?.label ?? "" },
          ...(xAxis?.type === "percent" ? { tickformat: ".1%" } : {}),
        },
        yaxis: {
          ...BASE_LAYOUT.yaxis,
          title: { text: yAxis?.label ?? "" },
          ...(yAxis?.type === "percent" ? { tickformat: ".1%" } : {}),
        },
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
