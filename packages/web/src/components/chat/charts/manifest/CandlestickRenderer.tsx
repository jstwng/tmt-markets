import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT } from "../chart-defaults";
import type { RendererProps, CandlestickData } from "./types";

export default function CandlestickRenderer({ data }: RendererProps<CandlestickData>) {
  const trace = {
    x: data.candles.map((c) => c.date),
    open: data.candles.map((c) => c.open),
    high: data.candles.map((c) => c.high),
    low: data.candles.map((c) => c.low),
    close: data.candles.map((c) => c.close),
    type: "candlestick" as const,
    increasing: { line: { color: "#111111" } },
    decreasing: { line: { color: "#999999" } },
  };

  return (
    <Plot
      data={[trace as any]}
      layout={{
        ...BASE_LAYOUT,
        height: CHART_HEIGHT,
        xaxis: { ...BASE_LAYOUT.xaxis, type: "date", rangeslider: { visible: false } },
        yaxis: { ...BASE_LAYOUT.yaxis, tickprefix: "$", tickformat: ",.2f" },
      }}
      config={BASE_CONFIG}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
