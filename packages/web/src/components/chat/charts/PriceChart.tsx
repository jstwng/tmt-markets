import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT, PALETTE } from "./chart-defaults";
import type { PricesData } from "@/api/chat-types";

interface PriceChartProps {
  data: PricesData;
}

export default function PriceChart({ data }: PriceChartProps) {
  const colors = [PALETTE.primary, PALETTE.secondary, PALETTE.muted, PALETTE.accent];

  const traces = data.tickers.map((ticker, i) => ({
    x: data.dates,
    y: data.prices[ticker],
    type: "scatter" as const,
    mode: "lines" as const,
    name: ticker,
    line: { color: colors[i % colors.length], width: 1.5 },
  }));

  // Direct end-labels instead of legend
  const annotations = data.tickers.map((ticker, i) => ({
    x: data.dates[data.dates.length - 1],
    y: data.prices[ticker][data.prices[ticker].length - 1],
    xref: "x" as const,
    yref: "y" as const,
    text: ticker,
    showarrow: false,
    xanchor: "left" as const,
    yanchor: "middle" as const,
    font: { size: 11, color: colors[i % colors.length] },
    xshift: 6,
  }));

  return (
    <Plot
      data={traces}
      layout={{
        ...BASE_LAYOUT,
        height: CHART_HEIGHT,
        annotations,
        margin: { ...BASE_LAYOUT.margin, r: 60 }, // room for end-labels
        xaxis: { ...BASE_LAYOUT.xaxis, type: "date" },
        yaxis: {
          ...BASE_LAYOUT.yaxis,
          tickprefix: "$",
          tickformat: ",.0f",
        },
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
