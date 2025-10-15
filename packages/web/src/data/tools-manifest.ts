export const CATEGORIES = [
  "Data",
  "Portfolio",
  "Risk",
  "Backtesting",
  "Covariance & Returns",
  "Scenarios",
  "Attribution",
  "Charts & Reports",
] as const;

export type ToolCategory = (typeof CATEGORIES)[number];

export interface Tool {
  name: string;
  description: string;
  examplePrompt: string;
  category: ToolCategory;
}

export const TOOLS_MANIFEST: readonly Tool[] = [
  // Data
  {
    name: "Price History",
    description: "Fetch historical adjusted close prices for one or more tickers.",
    examplePrompt: "Fetch daily prices for AAPL, MSFT from 2022 to 2024",
    category: "Data",
  },
  {
    name: "OpenBB Query",
    description: "Query financial data via OpenBB: options, earnings, fundamentals, macro indicators.",
    examplePrompt: "Get earnings estimates and income statement for NVDA",
    category: "Data",
  },

  // Portfolio
  {
    name: "Optimize Portfolio",
    description: "Find the optimal asset weights that maximize Sharpe ratio or minimize volatility.",
    examplePrompt: "Maximize Sharpe ratio for AAPL, MSFT, GOOGL over 2 years",
    category: "Portfolio",
  },
  {
    name: "Efficient Frontier",
    description: "Generate the mean-variance efficient frontier for a set of assets.",
    examplePrompt: "Show the efficient frontier for SPY, TLT, GLD, QQQ",
    category: "Portfolio",
  },
  {
    name: "Constrained Optimization",
    description: "Optimize a portfolio subject to constraints like position limits or sector caps.",
    examplePrompt: "Optimize my portfolio with a max 30% weight in any single stock",
    category: "Portfolio",
  },
  {
    name: "Black-Litterman",
    description: "Blend market equilibrium returns with investor views using the Black-Litterman model.",
    examplePrompt: "Apply Black-Litterman with my views that AAPL will outperform TSLA",
    category: "Portfolio",
  },
  {
    name: "Load / Save Portfolio",
    description: "Persist a named portfolio to your account or reload a previously saved one.",
    examplePrompt: "Save this portfolio as 'Core Holdings'",
    category: "Portfolio",
  },

  // Risk
  {
    name: "VaR / CVaR",
    description: "Compute Value at Risk and Conditional Value at Risk at a given confidence level.",
    examplePrompt: "Compute 95% VaR for my portfolio over the last year",
    category: "Risk",
  },
  {
    name: "Tail Risk Metrics",
    description: "Calculate skewness, kurtosis, and other tail risk statistics.",
    examplePrompt: "What are the tail risk metrics for a 60/40 SPY/TLT portfolio?",
    category: "Risk",
  },
  {
    name: "Risk Decomposition",
    description: "Break down total portfolio risk into per-asset marginal contributions.",
    examplePrompt: "Decompose risk contributions for SPY, TLT, GLD",
    category: "Risk",
  },
  {
    name: "Drawdown Analysis",
    description: "Compute the drawdown series and max drawdown for a portfolio.",
    examplePrompt: "Show max drawdown for a 60/40 SPY/TLT portfolio",
    category: "Risk",
  },
  {
    name: "Liquidity Score",
    description: "Score the relative liquidity of holdings based on average traded volume.",
    examplePrompt: "Score the liquidity of my current holdings",
    category: "Risk",
  },

  // Backtesting
  {
    name: "Backtest Portfolio",
    description: "Run a historical backtest for a fixed-weight portfolio over a date range.",
    examplePrompt: "Backtest a 60/40 SPY/TLT portfolio from 2022 to 2024",
    category: "Backtesting",
  },
  {
    name: "Rebalancing Analysis",
    description: "Analyze how rebalancing frequency affects portfolio performance and drift.",
    examplePrompt: "How often should I rebalance SPY/TLT to maintain a 60/40 split?",
    category: "Backtesting",
  },

  // Covariance & Returns
  {
    name: "Covariance Matrix",
    description: "Estimate the annualized covariance matrix of asset returns.",
    examplePrompt: "What is the covariance matrix for the Mag 7 stocks in 2024?",
    category: "Covariance & Returns",
  },
  {
    name: "Factor Exposure",
    description: "Compute a portfolio's exposure to common risk factors (market, size, value, momentum).",
    examplePrompt: "Show the factor exposure for my portfolio vs the market",
    category: "Covariance & Returns",
  },
  {
    name: "Expected Returns",
    description: "Estimate forward-looking expected returns using historical or factor-based methods.",
    examplePrompt: "Estimate expected returns for AAPL, MSFT, GOOGL",
    category: "Covariance & Returns",
  },

  // Scenarios
  {
    name: "Stress Test",
    description: "Simulate portfolio performance under historical stress scenarios (e.g. 2008, COVID).",
    examplePrompt: "Stress test my portfolio under a 2008-style market crash",
    category: "Scenarios",
  },
  {
    name: "Scenario Return Table",
    description: "Generate a table of portfolio returns across multiple predefined market scenarios.",
    examplePrompt: "Generate a scenario return table for my portfolio",
    category: "Scenarios",
  },
  {
    name: "Monte Carlo Simulation",
    description: "Run Monte Carlo paths to model the range of possible future portfolio outcomes.",
    examplePrompt: "Run 1000 Monte Carlo paths for my portfolio over 5 years",
    category: "Scenarios",
  },

  // Attribution
  {
    name: "Benchmark Comparison",
    description: "Compare portfolio returns, alpha, and beta against a benchmark index.",
    examplePrompt: "Compare my portfolio returns to SPY over 2 years",
    category: "Attribution",
  },
  {
    name: "Portfolio Attribution",
    description: "Break down return attribution by asset and time period.",
    examplePrompt: "Break down my portfolio's return attribution by holding",
    category: "Attribution",
  },

  // Charts & Reports
  {
    name: "Correlation Matrix",
    description: "Plot a heatmap of pairwise correlations between assets.",
    examplePrompt: "Plot the correlation matrix for the Mag 7 stocks",
    category: "Charts & Reports",
  },
  {
    name: "Frontier with Assets",
    description: "Plot the efficient frontier with individual asset risk/return points overlaid.",
    examplePrompt: "Show the efficient frontier with individual assets plotted",
    category: "Charts & Reports",
  },
  {
    name: "Rolling Metrics",
    description: "Compute rolling Sharpe ratio, volatility, or other metrics over a sliding window.",
    examplePrompt: "Show the rolling Sharpe ratio for my portfolio over 2 years",
    category: "Charts & Reports",
  },
  {
    name: "Asset Ranking",
    description: "Rank a list of assets by a chosen metric (Sharpe, return, volatility, etc.).",
    examplePrompt: "Rank AAPL, MSFT, GOOGL by Sharpe ratio in 2023",
    category: "Charts & Reports",
  },
  {
    name: "Tearsheet",
    description: "Generate a full performance tearsheet with key metrics, charts, and attribution.",
    examplePrompt: "Generate a full tearsheet for my portfolio",
    category: "Charts & Reports",
  },
];
