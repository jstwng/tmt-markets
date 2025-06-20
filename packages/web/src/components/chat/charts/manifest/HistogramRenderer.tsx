import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT, PALETTE } from "../chart-defaults";
import type { RendererProps, HistogramData, Annotation } from "./types";

export default function HistogramRenderer({ data, annotations }: RendererProps<HistogramData>) {
  const bins = data.series?.[0]?.bins ?? data.bins;

  const trace = {
    x: bins.map((b) => (b.range[0] + b.range[1]) / 2),
    y: bins.map((b) => b.count),
    type: "bar" as const,
    marker: { color: PALETTE.primary + "cc" },
    width: bins.length > 0 ? bins[0].range[1] - bins[0].range[0] : undefined,
  };

  const shapes = (annotations ?? [])
    .filter((a: Annotation) => a.type === "line")
    .map((a: Annotation) => ({
      type: "line" as const,
      x0: a.value,
      x1: a.value,
      y0: 0,
      y1: 1,
      yref: "paper" as const,
      line: { color: a.color ?? "#ef4444", width: 2, dash: "dash" as const },
    }));

  return (
    <Plot
      data={[trace]}
      layout={{
        ...BASE_LAYOUT,
        height: CHART_HEIGHT,
        shapes,
        bargap: 0.02,
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
