import type { ChartManifest, SeriesDef } from "./charts/manifest/types";
import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG, CHART_HEIGHT, PALETTE } from "./charts/chart-defaults";

interface Props {
  manifest: ChartManifest;
}

type Datum = string | number | null;

function col(data: Record<string, unknown>[], key: string): Datum[] {
  return data.map((row) => (row[key] as Datum) ?? null);
}

const COLOR_PALETTE = [
  PALETTE.primary,
  PALETTE.accent,
  PALETTE.secondary,
  PALETTE.muted,
  "#7c3aed",
  "#059669",
];

export default function ManifestChartBlock({ manifest }: Props) {
  const { kind, title, data, series, xKey, metrics } = manifest;

  // Metrics summary strip
  const metricsBar =
    metrics && metrics.length > 0 ? (
      <div className="flex flex-wrap gap-4 px-4 py-2 border-b border-border text-xs">
        {metrics.map((m, i) => (
          <div key={i} className="flex flex-col">
            <span className="text-muted-foreground">{m.label}</span>
            <span className="font-medium tabular-nums">{String(m.value)}</span>
          </div>
        ))}
      </div>
    ) : null;

  const xs: Datum[] = xKey
    ? col(data, xKey)
    : data.map((_, i) => i);

  // Resolve series list — always produce full SeriesDef-compatible objects
  function resolveSeriesList(): SeriesDef[] {
    if (series && series.length > 0) return series;
    return Object.keys(data[0] ?? {})
      .filter((k) => k !== xKey)
      .map((k) => ({ key: k, label: k }));
  }

  // Build Plotly traces
  let traces: Plotly.Data[] = [];

  if (kind === "line" || kind === "area") {
    const seriesList = resolveSeriesList();
    traces = seriesList.map((s, idx) => ({
      x: xs,
      y: col(data, s.key),
      type: "scatter" as const,
      mode: "lines" as const,
      name: s.label,
      line: { color: s.color ?? COLOR_PALETTE[idx % COLOR_PALETTE.length], width: 1.5 },
      ...(kind === "area"
        ? { fill: "tozeroy" as const, fillcolor: "rgba(37,99,235,0.06)" }
        : {}),
    }));
  } else if (kind === "bar") {
    const seriesList = resolveSeriesList();
    traces = seriesList.map((s, idx) => ({
      x: xs,
      y: col(data, s.key),
      type: "bar" as const,
      name: s.label,
      marker: { color: s.color ?? COLOR_PALETTE[idx % COLOR_PALETTE.length] },
    }));
  } else if (kind === "scatter") {
    const seriesList = resolveSeriesList();
    traces = seriesList.map((s, idx) => ({
      x: xs,
      y: col(data, s.key),
      type: "scatter" as const,
      mode: "markers" as const,
      name: s.label,
      marker: {
        color: s.color ?? COLOR_PALETTE[idx % COLOR_PALETTE.length],
        size: 5,
      },
    }));
  } else if (kind === "histogram") {
    const valueKey =
      manifest.valueKey ?? series?.[0]?.key ?? Object.keys(data[0] ?? {})[0];
    traces = [
      {
        x: col(data, valueKey),
        type: "histogram" as const,
        marker: { color: PALETTE.primary },
        name: valueKey,
      },
    ];
  } else if (kind === "pie") {
    const valueKey = manifest.valueKey ?? "value";
    const labelKey = manifest.labelKey ?? xKey ?? "label";
    traces = [
      {
        values: col(data, valueKey),
        labels: col(data, labelKey),
        type: "pie" as const,
      },
    ];
  } else {
    // Fallback: render numeric columns as lines
    const numericKeys = Object.keys(data[0] ?? {}).filter(
      (k) => k !== xKey && typeof data[0][k] === "number"
    );
    traces = numericKeys.slice(0, 3).map((k, idx) => ({
      x: xs,
      y: col(data, k),
      type: "scatter" as const,
      mode: "lines" as const,
      name: k,
      line: { color: COLOR_PALETTE[idx % COLOR_PALETTE.length], width: 1.5 },
    }));
  }

  const layout: Partial<Plotly.Layout> = {
    ...BASE_LAYOUT,
    height: CHART_HEIGHT,
    showlegend: traces.length > 1,
    legend: { orientation: "h", y: -0.18, font: { size: 11 } },
    xaxis: {
      ...BASE_LAYOUT.xaxis,
      title: manifest.xAxis?.label
        ? { text: manifest.xAxis.label, font: { size: 11 } }
        : undefined,
      tickformat: manifest.xAxis?.tickFormat,
    },
    yaxis: {
      ...BASE_LAYOUT.yaxis,
      title: manifest.yAxis?.label
        ? { text: manifest.yAxis.label, font: { size: 11 } }
        : undefined,
      tickformat: manifest.yAxis?.tickFormat,
    },
  };

  return (
    <div className="rounded border border-border overflow-hidden">
      {title && (
        <div className="px-4 py-2 text-xs font-medium border-b border-border bg-muted/30">
          {title}
        </div>
      )}
      {metricsBar}
      <Plot
        data={traces}
        layout={layout}
        config={BASE_CONFIG}
        style={{ width: "100%" }}
        useResizeHandler
      />
    </div>
  );
}
