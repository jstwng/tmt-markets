import Plot from "@/components/Plot";
import { BASE_CONFIG } from "@/components/chat/charts/chart-defaults";
import type { PositionData } from "@/api/client";

interface HoldingsPieProps {
  positions: PositionData[];
  loading?: boolean;
}

const COLORS = ["#111111", "#555555", "#999999", "#cccccc", "#333333", "#777777"];

export default function HoldingsPie({ positions, loading }: HoldingsPieProps) {
  if (loading) {
    return (
      <div className="border border-border rounded-lg p-4 flex items-center justify-center">
        <div className="h-[160px] w-[160px] rounded-full bg-muted/30 animate-pulse" />
      </div>
    );
  }

  const trace = {
    labels: positions.map((p) => p.ticker),
    values: positions.map((p) => p.weight),
    type: "pie" as const,
    hole: 0.5,
    textinfo: "label+percent" as const,
    textposition: "outside" as const,
    marker: { colors: COLORS.slice(0, positions.length) },
    hovertemplate: "%{label}<br>%{percent}<extra></extra>",
  };

  return (
    <div className="border border-border rounded-lg p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
        Holdings
      </div>
      <Plot
        data={[trace as any]}
        layout={{
          paper_bgcolor: "#ffffff",
          plot_bgcolor: "#ffffff",
          margin: { l: 20, r: 20, t: 8, b: 8 },
          height: 160,
          showlegend: false,
          autosize: true,
        }}
        config={BASE_CONFIG}
        style={{ width: "100%" }}
        useResizeHandler
      />
    </div>
  );
}
