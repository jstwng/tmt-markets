// --- Covariance ---

export interface CovarianceRequest {
  tickers: string[];
  start_date: string;
  end_date: string;
  method: "sample" | "ledoit_wolf" | "shrunk";
}

export interface CovarianceResponse {
  matrix: number[][];
  tickers: string[];
  method: string;
}

// --- Portfolio ---

export interface PortfolioOptimizeRequest {
  tickers: string[];
  start_date: string;
  end_date: string;
  objective: "min_variance" | "max_sharpe" | "risk_parity";
  max_weight?: number | null;
}

export interface PortfolioOptimizeResponse {
  weights: Record<string, number>;
  expected_return: number;
  expected_volatility: number;
  sharpe: number;
}

// --- Backtest ---

export interface BacktestRequest {
  tickers: string[];
  weights: Record<string, number>;
  start_date: string;
  end_date: string;
  initial_capital: number;
  rebalance_freq: "daily" | "weekly" | "monthly";
}

export interface EquityCurvePoint {
  date: string;
  value: number;
}

export interface BacktestMetrics {
  total_return: number;
  cagr: number;
  sharpe: number;
  max_drawdown: number;
  volatility: number;
}

export interface BacktestResponse {
  equity_curve: EquityCurvePoint[];
  metrics: BacktestMetrics;
}

// --- Data ---

export interface PricesRequest {
  tickers: string[];
  start_date: string;
  end_date: string;
  source: "yfinance" | "openbb";
}

export interface PricesResponse {
  dates: string[];
  tickers: string[];
  prices: Record<string, number[]>;
}
