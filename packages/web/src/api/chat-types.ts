// Chat message and block types for the AI agent interface

// ---------------------------------------------------------------------------
// Message blocks — discriminated union rendered inline in chat
// ---------------------------------------------------------------------------

export interface TextBlock {
  type: "text";
  text: string;
}

export interface ChartBlock {
  type: "chart";
  chartType: "price" | "weight_bar" | "equity_curve" | "covariance_heatmap" | "efficient_frontier";
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

export type MessageBlock =
  | TextBlock
  | ChartBlock
  | TableBlock
  | MetricsBlock
  | ToolCallBlock
  | ErrorBlock;

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
  data: { name: string; result: unknown };
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
