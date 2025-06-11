import type { ChartManifest, ChartType } from "./charts/manifest/types";
import SaveButton from "./charts/manifest/SaveButton";
import TimeSeriesRenderer from "./charts/manifest/TimeSeriesRenderer";
import CandlestickRenderer from "./charts/manifest/CandlestickRenderer";
import HeatmapRenderer from "./charts/manifest/HeatmapRenderer";
import BarRenderer from "./charts/manifest/BarRenderer";
import TableRenderer from "./charts/manifest/TableRenderer";
import ScatterRenderer from "./charts/manifest/ScatterRenderer";
import AreaRenderer from "./charts/manifest/AreaRenderer";
import HistogramRenderer from "./charts/manifest/HistogramRenderer";
import WaterfallRenderer from "./charts/manifest/WaterfallRenderer";
import FanRenderer from "./charts/manifest/FanRenderer";
import PieRenderer from "./charts/manifest/PieRenderer";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const RENDERERS: Record<ChartType, React.ComponentType<any>> = {
  time_series: TimeSeriesRenderer,
  candlestick: CandlestickRenderer,
  heatmap: HeatmapRenderer,
  bar: BarRenderer,
  table: TableRenderer,
  scatter: ScatterRenderer,
  area: AreaRenderer,
  histogram: HistogramRenderer,
  waterfall: WaterfallRenderer,
  fan: FanRenderer,
  pie: PieRenderer,
};

interface ManifestChartBlockProps {
  manifest: ChartManifest;
}

export default function ManifestChartBlock({ manifest }: ManifestChartBlockProps) {
  const Renderer = RENDERERS[manifest.chart_type];

  if (!Renderer) {
    return (
      <div className="text-sm text-muted-foreground p-3">
        Unknown chart type: {manifest.chart_type}
      </div>
    );
  }

  return (
    <div className="rounded border border-border overflow-hidden">
      <div className="px-4 pt-3">
        <h3 className="text-sm font-medium">{manifest.title}</h3>
        {manifest.subtitle && (
          <p className="text-xs text-muted-foreground mt-0.5">{manifest.subtitle}</p>
        )}
      </div>
      <Renderer
        data={manifest.data}
        xAxis={manifest.x_axis}
        yAxis={manifest.y_axis}
        annotations={manifest.annotations}
      />
      <div className="px-4 py-2 flex justify-end border-t border-border/50">
        <SaveButton manifest={manifest} />
      </div>
    </div>
  );
}
