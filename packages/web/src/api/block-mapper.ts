import type {
  BacktestData,
  ChartBlock,
  CovarianceData,
  FrontierData,
  MessageBlock,
  MetricsBlock,
  PortfolioData,
  PricesData,
  TableBlock,
} from "./chat-types";
import type { ChartManifest } from "@/components/chat/charts/manifest/types";

/**
 * Convert a raw tool result from an SSE event into typed MessageBlocks
 * for rendering in the chat interface.
 *
 * Blocks are ordered: metrics summary first, then the main visualization.
 */
export function mapToolResultToBlocks(
  toolName: string,
  result: unknown
): MessageBlock[] {
  // Dynamic OpenBB query — the full SSE event data is passed as `result`
  // containing both `result` (raw data) and `chart_manifest`
  if (toolName === "openbb_query") {
    const r = result as { chart_manifest?: unknown };
    if (r.chart_manifest) {
      return [{
        type: "manifest_chart" as const,
        manifest: r.chart_manifest as ChartManifest
      }];
    }
    // Fallback if no manifest
    return [{ type: "text", text: "```json\n" + JSON.stringify(result, null, 2) + "\n```" }];
  }

  switch (toolName) {
    case "fetch_prices":
      return mapPrices(result as PricesData);
    case "estimate_covariance":
      return mapCovariance(result as CovarianceData);
    case "optimize_portfolio":
      return mapPortfolio(result as PortfolioData);
    case "run_backtest":
      return mapBacktest(result as BacktestData);
    case "generate_efficient_frontier":
      return mapFrontier(result as FrontierData);
    default:
      // Fallback: render raw JSON as a text block
      return [
        {
          type: "text",
          text: "```json\n" + JSON.stringify(result, null, 2) + "\n```",
        },
      ];
  }
}

// ---------------------------------------------------------------------------
// Per-tool mappers
// ---------------------------------------------------------------------------

function mapPrices(data: PricesData): MessageBlock[] {
  const chart: ChartBlock = {
    type: "chart",
    chartType: "price",
    data,
  };
  return [chart];
}

function mapCovariance(data: CovarianceData): MessageBlock[] {
  const chart: ChartBlock = {
    type: "chart",
    chartType: "covariance_heatmap",
    data,
  };
  return [chart];
}

function mapPortfolio(data: PortfolioData): MessageBlock[] {
  const metrics: MetricsBlock = {
    type: "metrics",
    items: [
      { label: "Expected Return", value: pct(data.expected_return) },
      { label: "Volatility", value: pct(data.expected_volatility) },
      { label: "Sharpe Ratio", value: data.sharpe.toFixed(3) },
    ],
  };

  const chart: ChartBlock = {
    type: "chart",
    chartType: "weight_bar",
    data: data.weights,
  };

  return [metrics, chart];
}

function mapBacktest(data: BacktestData): MessageBlock[] {
  const m = data.metrics;

  const table: TableBlock = {
    type: "table",
    headers: ["Metric", "Value"],
    rows: [
      ["Total Return", pct(m.total_return)],
      ["CAGR", pct(m.cagr)],
      ["Sharpe Ratio", m.sharpe.toFixed(3)],
      ["Max Drawdown", pct(m.max_drawdown)],
      ["Annualized Volatility", pct(m.volatility)],
    ],
  };

  const chart: ChartBlock = {
    type: "chart",
    chartType: "equity_curve",
    data: data.equity_curve,
  };

  return [table, chart];
}

function mapFrontier(data: FrontierData): MessageBlock[] {
  const best = data.points[data.max_sharpe_idx];

  const metrics: MetricsBlock = {
    type: "metrics",
    items: best
      ? [
          { label: "Max Sharpe", value: best.sharpe.toFixed(3) },
          { label: "Return", value: pct(best.expected_return) },
          { label: "Volatility", value: pct(best.volatility) },
        ]
      : [],
  };

  const chart: ChartBlock = {
    type: "chart",
    chartType: "efficient_frontier",
    data,
  };

  return [metrics, chart];
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function pct(value: number): string {
  const sign = value >= 0 ? "" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}
