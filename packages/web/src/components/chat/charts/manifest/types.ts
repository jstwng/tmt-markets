/** Chart Manifest — the contract between backend LLM and frontend renderers. */

export type ChartType =
  | "time_series"
  | "candlestick"
  | "heatmap"
  | "bar"
  | "table"
  | "scatter"
  | "area"
  | "histogram"
  | "waterfall"
  | "fan"
  | "pie";

export interface AxisConfig {
  label: string;
  type: "date" | "category" | "numeric" | "percent" | "currency";
}

export interface Annotation {
  type: "line" | "band" | "point";
  value: number;
  label?: string;
  color?: string;
}

export interface ChartManifest {
  chart_type: ChartType;
  title: string;
  subtitle?: string;
  data: unknown; // narrowed per chart_type in each renderer
  x_axis?: AxisConfig;
  y_axis?: AxisConfig;
  annotations?: Annotation[];
  source: {
    query: string;
    openbb_call: string;
    timestamp: string;
  };
}

// ---------------------------------------------------------------------------
// Per-chart-type data shapes
// ---------------------------------------------------------------------------

export interface TimeSeriesData {
  series: Array<{ name: string; values: Array<{ date: string; value: number }> }>;
}

export interface CandlestickData {
  candles: Array<{
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume?: number;
  }>;
}

export interface HeatmapData {
  rows: string[];
  cols: string[];
  matrix: number[][];
}

export interface BarData {
  categories: string[];
  series: Array<{ name: string; values: number[] }>;
}

export interface TableData {
  columns: Array<{
    key: string;
    label: string;
    format?: "number" | "percent" | "currency" | "date";
  }>;
  rows: Array<Record<string, unknown>>;
}

export interface ScatterData {
  series: Array<{
    name: string;
    points: Array<{ x: number; y: number; label?: string }>;
  }>;
}

export interface AreaData {
  series: Array<{ name: string; values: Array<{ date: string; value: number }> }>;
  stacked?: boolean;
}

export interface HistogramData {
  bins: Array<{ range: [number, number]; count: number }>;
  series?: Array<{ name: string; bins: Array<{ range: [number, number]; count: number }> }>;
}

export interface WaterfallData {
  items: Array<{ label: string; value: number; type: "absolute" | "delta" }>;
}

export interface FanData {
  dates: string[];
  percentiles: Array<{ p: number; values: number[] }>;
}

export interface PieData {
  slices: Array<{ label: string; value: number }>;
}

// ---------------------------------------------------------------------------
// Renderer props — shared by all renderers
// ---------------------------------------------------------------------------

export interface RendererProps<T = unknown> {
  data: T;
  xAxis?: AxisConfig;
  yAxis?: AxisConfig;
  annotations?: Annotation[];
}
