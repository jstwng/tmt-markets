import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT, PALETTE } from "./chart-defaults";

interface WeightBarProps {
  data: Record<string, number>;
}

export default function WeightBar({ data }: WeightBarProps) {
  // Sort descending by weight
  const sorted = Object.entries(data).sort(([, a], [, b]) => b - a);
  const tickers = sorted.map(([t]) => t);
  const weights = sorted.map(([, w]) => w);
  const pctLabels = weights.map((w) => `${(w * 100).toFixed(1)}%`);

  const dynamicHeight = Math.max(180, tickers.length * 36 + 40);

  return (
    <Plot
      data={[
        {
          x: weights,
          y: tickers,
          type: "bar",
          orientation: "h",
          text: pctLabels,
          textposition: "outside",
          marker: { color: PALETTE.primary },
          hovertemplate: "%{y}: %{text}<extra></extra>",
        },
      ]}
      layout={{
        ...BASE_LAYOUT,
        height: Math.min(dynamicHeight, CHART_HEIGHT),
        margin: { l: 64, r: 56, t: 12, b: 32 },
        xaxis: {
          ...BASE_LAYOUT.xaxis,
          tickformat: ".0%",
          range: [0, Math.max(...weights) * 1.25],
          showline: false,
          showticklabels: false,
        },
        yaxis: {
          ...BASE_LAYOUT.yaxis,
          autorange: "reversed",
          tickfont: { size: 12 },
        },
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
