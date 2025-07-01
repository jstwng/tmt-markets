// Chat message and block types for the AI agent interface
import type { ChartManifest } from "@/components/chat/charts/manifest/types";

// ---------------------------------------------------------------------------
// Message blocks — discriminated union rendered inline in chat
// ---------------------------------------------------------------------------

export interface TextBlock {
  type: "text";
  text: string;
}

export interface ChartBlock {
  type: "chart";
  chartType:
    | "price"
    | "weight_bar"
    | "equity_curve"
    | "covariance_heatmap"
    | "efficient_frontier"
    | "rolling";
  data: unknown;
}

export interface TableBlock {
  type: "table";
  headers: string[];
  rows: (string | number)[][];
}

export interface MetricsBlock {
  type: "metrics";
  items: MetricItem[];
}

export interface MetricItem {
  label: string;
  value: string;
}

export interface ToolCallBlock {
  type: "tool_call";
  name: string;
  displayName: string;
  args: Record<string, unknown>;
  status: "pending" | "complete";
  durationMs?: number;
}

export interface ErrorBlock {
  type: "error";
  message: string;
}

export interface ManifestChartBlock {
  type: "manifest_chart";
  manifest: ChartManifest;
}

export type MessageBlock =
  | TextBlock
  | ChartBlock
  | TableBlock
  | MetricsBlock
  | ToolCallBlock
  | ErrorBlock
  | ManifestChartBlock;

// ---------------------------------------------------------------------------
// Chat message
// ---------------------------------------------------------------------------

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  blocks: MessageBlock[];
  timestamp: number;
}

// ---------------------------------------------------------------------------
// SSE event types from the backend
// ---------------------------------------------------------------------------

export interface SSESessionEvent {
  event: "session";
  data: { session_id: string };
}

export interface SSEThinkingEvent {
  event: "thinking";
  data: { text: string };
}

export interface SSEToolCallEvent {
  event: "tool_call";
  data: { name: string; args: Record<string, unknown> };
}

export interface SSEToolResultEvent {
  event: "tool_result";
  data: { name: string; result: unknown; chart_manifest?: ChartManifest };
}

export interface SSETextEvent {
  event: "text";
  data: { text: string };
}

export interface SSEErrorEvent {
  event: "error";
  data: { message: string };
}

export interface SSEDoneEvent {
  event: "done";
  data: Record<string, never>;
}

export type SSEEvent =
  | SSESessionEvent
  | SSEThinkingEvent
  | SSEToolCallEvent
  | SSEToolResultEvent
  | SSETextEvent
  | SSEErrorEvent
  | SSEDoneEvent;

// ---------------------------------------------------------------------------
// Tool result data shapes (for block mapper)
// ---------------------------------------------------------------------------

export interface PricesData {
  dates: string[];
  tickers: string[];
  prices: Record<string, number[]>;
}

export interface CovarianceData {
  matrix: number[][];
  tickers: string[];
  method: string;
}

export interface PortfolioData {
  weights: Record<string, number>;
  expected_return: number;
  expected_volatility: number;
  sharpe: number;
}

export interface BacktestData {
  equity_curve: { date: string; value: number }[];
  metrics: {
    total_return: number;
    cagr: number;
    sharpe: number;
    max_drawdown: number;
    volatility: number;
  };
}

export interface FrontierData {
  points: {
    volatility: number;
    expected_return: number;
    weights: Record<string, number>;
    sharpe: number;
  }[];
  max_sharpe_idx: number;
}

export interface RollingMetricsData {
  dates: string[];
  rolling_sharpe: number[];
  rolling_volatility: number[];
  rolling_drawdown: number[];
  window?: number;
}

export interface CorrelationMatrixData {
  matrix: number[][];
  tickers: string[];
}

export interface VaRData {
  var_95: number;
  var_99: number;
  cvar_95: number;
  cvar_99: number;
  method: string;
  tickers: string[];
  weights: Record<string, number>;
}

export interface TailRiskData {
  skewness: number;
  kurtosis: number;
  var_95: number;
  cvar_95: number;
  max_drawdown: number;
  tickers: string[];
}

export interface RiskDecompData {
  marginal_risk: Record<string, number>;
  component_risk: Record<string, number>;
  percent_contribution: Record<string, number>;
  total_volatility: number;
}

export interface DrawdownSeriesData {
  dates: string[];
  drawdown: number[];
  current_drawdown: number | null;
  max_drawdown: number;
}

export interface BenchmarkData {
  portfolio_return: number;
  benchmark_return: number;
  alpha: number;
  beta: number;
  correlation: number;
  tracking_error: number;
  information_ratio: number;
}

export interface AttributionData {
  allocation_effect: Record<string, number>;
  selection_effect: Record<string, number>;
  interaction_effect: Record<string, number>;
  total_active_return: number;
}

export interface FactorExposureData {
  exposures: Record<string, number>;
  r_squared: number;
  residual_return: number;
  tickers: string[];
}

export interface ExpectedReturnsData {
  expected_returns: Record<string, number>;
  method: string;
  annualized: boolean;
}

export interface StressTestData {
  scenarios: {
    name: string;
    portfolio_return: number;
    benchmark_return?: number;
  }[];
}

export interface ScenarioTableData {
  scenarios: string[];
  tickers: string[];
  returns: Record<string, Record<string, number>>;
}

export interface RebalancingData {
  dates: string[];
  equity_curve: number[];
  turnover_series: number[];
  total_return: number;
  avg_turnover: number;
  rebalance_count: number;
}

export interface ConstrainedPortfolioData {
  weights: Record<string, number>;
  expected_return: number;
  expected_volatility: number;
  sharpe: number;
  constraints_applied: string[];
}

export interface RankedAssetsData {
  rankings: { ticker: string; value: number; rank: number }[];
  metric: string;
}

export interface LiquidityData {
  scores: Record<string, number>;
  avg_volume: Record<string, number>;
  bid_ask_spread_est: Record<string, number>;
}

export interface BlackLittermanData {
  weights: Record<string, number>;
  posterior_returns: Record<string, number>;
  expected_return: number;
  expected_volatility: number;
  sharpe: number;
}

export interface MonteCarloData {
  dates: string[];
  p5: number[];
  p25: number[];
  p50: number[];
  p75: number[];
  p95: number[];
  initial_value: number;
  n_simulations: number;
}

export interface FrontierWithAssetsData {
  frontier: { volatility: number; expected_return: number; sharpe: number }[];
  assets: { ticker: string; volatility: number; expected_return: number; sharpe: number }[];
  max_sharpe_idx: number;
}

export interface TearsheetData {
  total_return: number;
  cagr: number;
  sharpe: number;
  max_drawdown: number;
  volatility: number;
  var_95: number;
  cvar_95: number;
  current_drawdown: number | null;
  equity_curve: { date: string; value: number }[];
  rolling_metrics: RollingMetricsData;
}

// ---------------------------------------------------------------------------
// SSE codegen event types (Task 5)
// ---------------------------------------------------------------------------

export interface SSECodegenEvent {
  event: "codegen";
  data: { attempt: number; code: string };
}

export interface SSECodegenRetryEvent {
  event: "codegen_retry";
  data: { attempt: number; error: string };
}
