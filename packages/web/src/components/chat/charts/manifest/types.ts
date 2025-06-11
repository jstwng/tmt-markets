// ChartManifest types — describes the chart produced by an OpenBB query
// The backend generates these and the frontend renders them dynamically.

export type ChartKind =
  | "line"
  | "bar"
  | "scatter"
  | "area"
  | "candlestick"
  | "histogram"
  | "heatmap"
  | "pie"
  | "table"
  | "metrics"
  | "combo";

export interface SeriesDef {
  key: string;
  label: string;
  color?: string;
  yAxis?: "left" | "right";
}

export interface AxisDef {
  label?: string;
  tickFormat?: string;
  domain?: [number, number];
}

export interface ChartManifest {
  kind: ChartKind;
  title?: string;
  description?: string;
  xKey?: string;
  xAxis?: AxisDef;
  yAxis?: AxisDef;
  y2Axis?: AxisDef;
  series?: SeriesDef[];
  colorKey?: string;
  valueKey?: string;
  labelKey?: string;
  /** Raw data rows */
  data: Record<string, unknown>[];
  /** Optional metrics summary items */
  metrics?: { label: string; value: string | number }[];
}
