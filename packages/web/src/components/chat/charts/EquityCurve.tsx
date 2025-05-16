import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT, PALETTE } from "./chart-defaults";

interface EquityCurvePoint {
  date: string;
  value: number;
}

interface EquityCurveProps {
  data: EquityCurvePoint[];
}

export default function EquityCurve({ data }: EquityCurveProps) {
  const dates = data.map((p) => p.date);
  const values = data.map((p) => p.value);
  const initialValue = values[0] ?? 0;
  const finalValue = values[values.length - 1] ?? 0;
  const isPositive = finalValue >= initialValue;

  return (
    <Plot
      data={[
        {
          x: dates,
          y: values,
          type: "scatter",
          mode: "lines",
          name: "Portfolio",
          fill: "tozeroy",
          fillcolor: isPositive ? "rgba(17,17,17,0.05)" : "rgba(85,85,85,0.05)",
          line: { color: PALETTE.primary, width: 1.5 },
          hovertemplate: "%{x|%b %d, %Y}<br>$%{y:,.0f}<extra></extra>",
        },
      ]}
      layout={{
        ...BASE_LAYOUT,
        height: CHART_HEIGHT,
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
