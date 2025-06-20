import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT } from "../chart-defaults";
import type { RendererProps, WaterfallData } from "./types";

export default function WaterfallRenderer({ data }: RendererProps<WaterfallData>) {
  const trace = {
    type: "waterfall" as const,
    x: data.items.map((item) => item.label),
    y: data.items.map((item) => item.value),
    measure: data.items.map((item) => (item.type === "absolute" ? "absolute" : "relative")),
    connector: { line: { color: "#e5e5e5", width: 1 } },
    increasing: { marker: { color: "#111111" } },
    decreasing: { marker: { color: "#999999" } },
    totals: { marker: { color: "#2563eb" } },
  };

  return (
    <Plot
      data={[trace as any]}
      layout={{
        ...BASE_LAYOUT,
        height: CHART_HEIGHT,
        waterfallgap: 0.3,
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
