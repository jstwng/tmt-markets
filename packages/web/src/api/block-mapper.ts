import type {
  AttributionData,
  BacktestData,
  BenchmarkData,
  BlackLittermanData,
  ChartBlock,
  ConstrainedPortfolioData,
  CorrelationMatrixData,
  CovarianceData,
  DrawdownSeriesData,
  ExpectedReturnsData,
  FactorExposureData,
  FrontierData,
  FrontierWithAssetsData,
  LiquidityData,
  MessageBlock,
  MetricsBlock,
  MonteCarloData,
  PortfolioData,
  PricesData,
  RankedAssetsData,
  RebalancingData,
  RiskDecompData,
  RollingMetricsData,
  ScenarioTableData,
  StressTestData,
  TableBlock,
  TailRiskData,
  TearsheetData,
  VaRData,
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
    case "compute_var_cvar":
      return mapVaR(result as VaRData);
    case "compute_tail_risk_metrics":
      return mapTailRisk(result as TailRiskData);
    case "decompose_risk":
      return mapRiskDecomp(result as RiskDecompData);
    case "compute_drawdown_series":
      return mapDrawdownSeries(result as DrawdownSeriesData);
    case "compare_to_benchmark":
      return mapBenchmark(result as BenchmarkData);
    case "compute_portfolio_attribution":
      return mapAttribution(result as AttributionData);
    case "plot_correlation_matrix":
      return mapCorrelationMatrix(result as CorrelationMatrixData);
    case "compute_factor_exposure":
      return mapFactorExposure(result as FactorExposureData);
    case "estimate_expected_returns":
      return mapExpectedReturns(result as ExpectedReturnsData);
    case "run_stress_test":
      return mapStressTest(result as StressTestData);
    case "generate_scenario_return_table":
      return mapScenarioTable(result as ScenarioTableData);
    case "compute_rolling_metrics":
      return mapRollingMetrics(result as RollingMetricsData);
    case "run_rebalancing_analysis":
      return mapRebalancing(result as RebalancingData);
    case "optimize_with_constraints":
      return mapConstrainedPortfolio(result as ConstrainedPortfolioData);
    case "rank_assets_by_metric":
      return mapRankedAssets(result as RankedAssetsData);
    case "compute_liquidity_score":
      return mapLiquidity(result as LiquidityData);
    case "apply_black_litterman":
      return mapBlackLitterman(result as BlackLittermanData);
    case "run_monte_carlo":
      return mapMonteCarlo(result as MonteCarloData);
    case "plot_efficient_frontier_with_assets":
      return mapFrontierWithAssets(result as FrontierWithAssetsData);
    case "generate_tearsheet":
      return mapTearsheet(result as TearsheetData);
    default: {
      // Smart fallback: plain object → table, otherwise raw JSON
      const r = result as Record<string, unknown>;
      if (result !== null && typeof result === "object" && !Array.isArray(result)) {
        const entries = Object.entries(r).filter(
          ([, v]) => typeof v === "number" || typeof v === "string"
        );
        if (entries.length > 0) {
          const table: TableBlock = {
            type: "table",
            headers: ["Field", "Value"],
            rows: entries.map(([k, v]) => [k, String(v)]),
          };
          return [table];
        }
      }
      return [
        {
          type: "text",
          text: "```json\n" + JSON.stringify(result, null, 2) + "\n```",
        },
      ];
    }
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

function mapCorrelationMatrix(data: CorrelationMatrixData): MessageBlock[] {
  // Reuse CovarianceHeatmap — it only needs matrix + tickers
  const chart: ChartBlock = {
    type: "chart",
    chartType: "covariance_heatmap",
    data: { matrix: data.matrix, tickers: data.tickers, method: "correlation" },
  };
  return [chart];
}

function mapVaR(data: VaRData): MessageBlock[] {
  const metrics: MetricsBlock = {
    type: "metrics",
    items: [
      { label: "VaR (95%)", value: pct(data.var_95) },
      { label: "VaR (99%)", value: pct(data.var_99) },
      { label: "CVaR (95%)", value: pct(data.cvar_95) },
      { label: "CVaR (99%)", value: pct(data.cvar_99) },
    ],
  };
  return [metrics];
}

function mapTailRisk(data: TailRiskData): MessageBlock[] {
  const table: TableBlock = {
    type: "table",
    headers: ["Metric", "Value"],
    rows: [
      ["Skewness", data.skewness.toFixed(3)],
      ["Kurtosis", data.kurtosis.toFixed(3)],
      ["VaR (95%)", pct(data.var_95)],
      ["CVaR (95%)", pct(data.cvar_95)],
      ["Max Drawdown", pct(data.max_drawdown)],
    ],
  };
  return [table];
}

function mapRiskDecomp(data: RiskDecompData): MessageBlock[] {
  const metrics: MetricsBlock = {
    type: "metrics",
    items: [{ label: "Total Volatility", value: pct(data.total_volatility) }],
  };
  const tickers = Object.keys(data.percent_contribution);
  const table: TableBlock = {
    type: "table",
    headers: ["Ticker", "% Risk Contribution"],
    rows: tickers
      .sort((a, b) => data.percent_contribution[b] - data.percent_contribution[a])
      .map((t) => [t, pct(data.percent_contribution[t])]),
  };
  return [metrics, table];
}

function mapDrawdownSeries(data: DrawdownSeriesData): MessageBlock[] {
  const metrics: MetricsBlock = {
    type: "metrics",
    items: [
      { label: "Max Drawdown", value: pct(data.max_drawdown) },
      {
        label: "Current Drawdown",
        value: data.current_drawdown != null ? pct(data.current_drawdown) : "N/A",
      },
    ],
  };
  // Render as equity_curve chart using drawdown values
  const chart: ChartBlock = {
    type: "chart",
    chartType: "equity_curve",
    data: data.dates.map((d, i) => ({ date: d, value: data.drawdown[i] })),
  };
  return [metrics, chart];
}

function mapBenchmark(data: BenchmarkData): MessageBlock[] {
  const table: TableBlock = {
    type: "table",
    headers: ["Metric", "Value"],
    rows: [
      ["Portfolio Return", pct(data.portfolio_return)],
      ["Benchmark Return", pct(data.benchmark_return)],
      ["Alpha", pct(data.alpha)],
      ["Beta", data.beta.toFixed(3)],
      ["Correlation", data.correlation.toFixed(3)],
      ["Tracking Error", pct(data.tracking_error)],
      ["Information Ratio", data.information_ratio.toFixed(3)],
    ],
  };
  return [table];
}

function mapAttribution(data: AttributionData): MessageBlock[] {
  const metrics: MetricsBlock = {
    type: "metrics",
    items: [
      { label: "Total Active Return", value: pct(data.total_active_return) },
    ],
  };
  const tickers = Object.keys(data.allocation_effect);
  const table: TableBlock = {
    type: "table",
    headers: ["Ticker", "Allocation", "Selection", "Interaction"],
    rows: tickers.map((t) => [
      t,
      pct(data.allocation_effect[t]),
      pct(data.selection_effect[t]),
      pct(data.interaction_effect[t]),
    ]),
  };
  return [metrics, table];
}

function mapFactorExposure(data: FactorExposureData): MessageBlock[] {
  const metrics: MetricsBlock = {
    type: "metrics",
    items: [
      { label: "R²", value: data.r_squared.toFixed(3) },
      { label: "Residual Return", value: pct(data.residual_return) },
    ],
  };
  const table: TableBlock = {
    type: "table",
    headers: ["Factor", "Exposure"],
    rows: Object.entries(data.exposures).map(([f, v]) => [f, v.toFixed(3)]),
  };
  return [metrics, table];
}

function mapExpectedReturns(data: ExpectedReturnsData): MessageBlock[] {
  const table: TableBlock = {
    type: "table",
    headers: ["Ticker", "Expected Return"],
    rows: Object.entries(data.expected_returns)
      .sort(([, a], [, b]) => b - a)
      .map(([t, v]) => [t, pct(v)]),
  };
  return [table];
}

function mapStressTest(data: StressTestData): MessageBlock[] {
  const table: TableBlock = {
    type: "table",
    headers: data.scenarios[0]?.benchmark_return !== undefined
      ? ["Scenario", "Portfolio", "Benchmark"]
      : ["Scenario", "Portfolio Return"],
    rows: data.scenarios.map((s) =>
      s.benchmark_return !== undefined
        ? [s.name, pct(s.portfolio_return), pct(s.benchmark_return)]
        : [s.name, pct(s.portfolio_return)]
    ),
  };
  return [table];
}

function mapScenarioTable(data: ScenarioTableData): MessageBlock[] {
  const table: TableBlock = {
    type: "table",
    headers: ["Ticker", ...data.scenarios],
    rows: data.tickers.map((t) => [
      t,
      ...data.scenarios.map((s) => pct(data.returns[t]?.[s] ?? 0)),
    ]),
  };
  return [table];
}

function mapRollingMetrics(data: RollingMetricsData): MessageBlock[] {
  const chart: ChartBlock = {
    type: "chart",
    chartType: "rolling",
    data,
  };
  return [chart];
}

function mapRebalancing(data: RebalancingData): MessageBlock[] {
  const metrics: MetricsBlock = {
    type: "metrics",
    items: [
      { label: "Total Return", value: pct(data.total_return) },
      { label: "Avg Turnover", value: pct(data.avg_turnover) },
      { label: "Rebalances", value: String(data.rebalance_count) },
    ],
  };
  const chart: ChartBlock = {
    type: "chart",
    chartType: "equity_curve",
    data: data.dates.map((d, i) => ({ date: d, value: data.equity_curve[i] })),
  };
  return [metrics, chart];
}

function mapConstrainedPortfolio(data: ConstrainedPortfolioData): MessageBlock[] {
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

function mapRankedAssets(data: RankedAssetsData): MessageBlock[] {
  const table: TableBlock = {
    type: "table",
    headers: ["Rank", "Ticker", data.metric],
    rows: data.rankings.map((r) => [r.rank, r.ticker, r.value.toFixed(4)]),
  };
  return [table];
}

function mapLiquidity(data: LiquidityData): MessageBlock[] {
  const tickers = Object.keys(data.scores);
  const table: TableBlock = {
    type: "table",
    headers: ["Ticker", "Liquidity Score", "Avg Volume"],
    rows: tickers
      .sort((a, b) => data.scores[b] - data.scores[a])
      .map((t) => [t, data.scores[t].toFixed(2), Math.round(data.avg_volume[t]).toLocaleString()]),
  };
  return [table];
}

function mapBlackLitterman(data: BlackLittermanData): MessageBlock[] {
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

function mapMonteCarlo(data: MonteCarloData): MessageBlock[] {
  const metrics: MetricsBlock = {
    type: "metrics",
    items: [
      { label: "Simulations", value: data.n_simulations.toLocaleString() },
      {
        label: "Median Final",
        value: "$" + Math.round(data.p50[data.p50.length - 1]).toLocaleString(),
      },
      {
        label: "5th Pct Final",
        value: "$" + Math.round(data.p5[data.p5.length - 1]).toLocaleString(),
      },
    ],
  };
  // Render as equity curve using median path
  const chart: ChartBlock = {
    type: "chart",
    chartType: "equity_curve",
    data: data.dates.map((d, i) => ({ date: d, value: data.p50[i] })),
  };
  return [metrics, chart];
}

function mapFrontierWithAssets(data: FrontierWithAssetsData): MessageBlock[] {
  const best = data.frontier[data.max_sharpe_idx];
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
  // Reuse EfficientFrontier component — pass data in expected FrontierData shape
  const frontierData: FrontierData = {
    points: data.frontier.map((p) => ({ ...p, weights: {} })),
    max_sharpe_idx: data.max_sharpe_idx,
  };
  const chart: ChartBlock = {
    type: "chart",
    chartType: "efficient_frontier",
    data: frontierData,
  };
  return [metrics, chart];
}

function mapTearsheet(data: TearsheetData): MessageBlock[] {
  const table: TableBlock = {
    type: "table",
    headers: ["Metric", "Value"],
    rows: [
      ["Total Return", pct(data.total_return)],
      ["CAGR", pct(data.cagr)],
      ["Sharpe Ratio", data.sharpe.toFixed(3)],
      ["Max Drawdown", pct(data.max_drawdown)],
      ["Volatility", pct(data.volatility)],
      ["VaR (95%)", pct(data.var_95)],
      ["CVaR (95%)", pct(data.cvar_95)],
      ["Current Drawdown", data.current_drawdown != null ? pct(data.current_drawdown) : "N/A"],
    ],
  };
  const equityChart: ChartBlock = {
    type: "chart",
    chartType: "equity_curve",
    data: data.equity_curve,
  };
  const rollingChart: ChartBlock = {
    type: "chart",
    chartType: "rolling",
    data: data.rolling_metrics,
  };
  return [table, equityChart, rollingChart];
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function pct(value: number): string {
  const sign = value >= 0 ? "" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}
