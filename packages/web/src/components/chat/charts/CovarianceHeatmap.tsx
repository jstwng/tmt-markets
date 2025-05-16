import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT } from "./chart-defaults";
import type { CovarianceData } from "@/api/chat-types";

interface CovarianceHeatmapProps {
  data: CovarianceData;
}

export default function CovarianceHeatmap({ data }: CovarianceHeatmapProps) {
  const absMax = Math.max(...data.matrix.flat().map(Math.abs));

  // Annotations: show value in each cell
  const annotations = data.tickers.flatMap((rowTicker, i) =>
    data.tickers.map((colTicker, j) => ({
      x: colTicker,
      y: rowTicker,
      text: data.matrix[i][j].toFixed(4),
      showarrow: false,
      font: { size: 10, color: "#111111" },
    }))
  );

  const n = data.tickers.length;
  const size = Math.min(CHART_HEIGHT, Math.max(200, n * 52));

  return (
    <Plot
      data={[
        {
          z: data.matrix,
          x: data.tickers,
          y: data.tickers,
          type: "heatmap",
          colorscale: [
            [0, "#2563eb"],
            [0.5, "#ffffff"],
            [1, "#111111"],
          ],
          reversescale: false,
          zmin: -absMax,
          zmax: absMax,
          showscale: false,
          hovertemplate: "%{y} / %{x}: %{z:.4f}<extra></extra>",
        },
      ]}
      layout={{
        ...BASE_LAYOUT,
        height: size,
        width: size + 20,
        margin: { l: 64, r: 16, t: 16, b: 64 },
        annotations,
        xaxis: { ...BASE_LAYOUT.xaxis, side: "bottom", showline: false },
        yaxis: { ...BASE_LAYOUT.yaxis, autorange: "reversed", showline: false },
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
