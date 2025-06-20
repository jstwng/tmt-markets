import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT } from "../chart-defaults";
import type { RendererProps, HeatmapData } from "./types";

export default function HeatmapRenderer({ data }: RendererProps<HeatmapData>) {
  const absMax = Math.max(...data.matrix.flat().map(Math.abs));
  const n = data.rows.length;
  const size = Math.min(CHART_HEIGHT, Math.max(200, n * 52));

  const annotations = data.rows.flatMap((row, i) =>
    data.cols.map((col, j) => ({
      x: col,
      y: row,
      text: data.matrix[i][j].toFixed(4),
      showarrow: false,
      font: { size: 10, color: "#111111" },
    }))
  );

  return (
    <Plot
      data={[
        {
          z: data.matrix,
          x: data.cols,
          y: data.rows,
          type: "heatmap",
          colorscale: [
            [0, "#2563eb"],
            [0.5, "#ffffff"],
            [1, "#111111"],
          ],
          zmin: -absMax,
          zmax: absMax,
          showscale: false,
          hovertemplate: "%{y} / %{x}: %{z:.4f}<extra></extra>",
        } as any,
      ]}
      layout={{
        ...BASE_LAYOUT,
        height: size,
        width: size + 20,
        margin: { l: 64, r: 16, t: 16, b: 64 },
        annotations,
        xaxis: { ...BASE_LAYOUT.xaxis, showline: false },
        yaxis: { ...BASE_LAYOUT.yaxis, autorange: "reversed" as any, showline: false },
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
