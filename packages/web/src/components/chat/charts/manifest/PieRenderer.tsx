import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT } from "../chart-defaults";
import type { RendererProps, PieData } from "./types";

export default function PieRenderer({ data }: RendererProps<PieData>) {
  const trace = {
    labels: data.slices.map((s) => s.label),
    values: data.slices.map((s) => s.value),
    type: "pie" as const,
    hole: 0.4,
    textinfo: "label+percent",
    textposition: "outside",
    marker: {
      colors: ["#111111", "#555555", "#999999", "#2563eb", "#bbbbbb", "#333333"],
    },
  };

  return (
    <Plot
      data={[trace as any]}
      layout={{
        ...BASE_LAYOUT,
        height: CHART_HEIGHT,
        margin: { l: 20, r: 20, t: 20, b: 20 },
        showlegend: false,
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
