import type {
  CovarianceRequest,
  CovarianceResponse,
  EfficientFrontierRequest,
  EfficientFrontierResponse,
  PortfolioOptimizeRequest,
  PortfolioOptimizeResponse,
  BacktestRequest,
  BacktestResponse,
  PricesRequest,
  PricesResponse,
} from "./types";

const API_BASE = "/api";

// ---------------------------------------------------------------------------
// Base fetch helpers
// ---------------------------------------------------------------------------

async function post<TReq, TRes>(path: string, body: TReq): Promise<TRes> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail);
  }
  return res.json();
}

async function get<TRes>(path: string): Promise<TRes> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail);
  }
  return res.json();
}

async function authedGet<TRes>(path: string, token: string): Promise<TRes> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Types for new endpoints
// ---------------------------------------------------------------------------

export interface Portfolio {
  id: string;
  name: string;
  tickers: string[];
  weights: number[];
  created_at: string;
  updated_at: string;
}

export interface PerformanceCurvePoint {
  date: string;
  value: number;
  benchmark: number;
}

export interface PositionData {
  ticker: string;
  weight: number;
  price: number;
  day_pct: number;
  total_return: number;
}

export interface PortfolioPerformance {
  curve: PerformanceCurvePoint[];
  positions: PositionData[];
  stats: {
    sharpe: number;
    max_drawdown: number;
    total_return: number;
    alpha: number;
  };
  portfolio_name: string;
}

export interface MacroPanelData {
  fields: {
    label: string;
    value: string;
    change: string | null;
    sparkline: number[];
  }[];
}

export interface IndicesPanelData {
  rows: {
    ticker: string;
    price: number;
    day_change: number;
    day_pct: number;
    sparkline: number[];
    is_sector: boolean;
  }[];
}

export interface MoversPanelData {
  gainers: { ticker: string; day_pct: number }[];
  losers: { ticker: string; day_pct: number }[];
}

export interface HeatmapPanelData {
  sectors: { ticker: string; day_pct: number }[];
}

export interface CalendarPanelData {
  events: { date: string; event: string; consensus: string | null }[];
}

export type TerminalPanelData =
  | MacroPanelData
  | IndicesPanelData
  | MoversPanelData
  | HeatmapPanelData
  | CalendarPanelData;

export interface TerminalPanelResponse {
  panel: string;
  raw_data: unknown[];
  cached_at: string | null;
  error: boolean;
  error_message?: string;
}

// ---------------------------------------------------------------------------
// Existing endpoints (unchanged)
// ---------------------------------------------------------------------------

export async function healthCheck(): Promise<{ status: string }> {
  return get("/health");
}

export async function computeCovariance(req: CovarianceRequest): Promise<CovarianceResponse> {
  return post("/covariance", req);
}

export async function optimizePortfolio(req: PortfolioOptimizeRequest): Promise<PortfolioOptimizeResponse> {
  return post("/portfolio/optimize", req);
}

export async function runBacktest(req: BacktestRequest): Promise<BacktestResponse> {
  return post("/backtest", req);
}

export async function fetchPrices(req: PricesRequest): Promise<PricesResponse> {
  return post("/data/prices", req);
}

export async function generateFrontier(req: EfficientFrontierRequest): Promise<EfficientFrontierResponse> {
  return post("/portfolio/frontier", req);
}

// ---------------------------------------------------------------------------
// New endpoints
// ---------------------------------------------------------------------------

export async function listPortfolios(token: string): Promise<Portfolio[]> {
  return authedGet("/portfolios", token);
}

export async function getPortfolioPerformance(
  token: string,
  portfolioId?: string
): Promise<PortfolioPerformance> {
  const qs = portfolioId ? `?portfolio_id=${encodeURIComponent(portfolioId)}` : "";
  return authedGet(`/portfolio/performance${qs}`, token);
}

export async function getTerminalPanel(
  panel: "macro" | "indices" | "movers" | "heatmap" | "calendar",
  ttl: number
): Promise<TerminalPanelResponse> {
  return get(`/terminal/panel/${panel}?ttl=${ttl}`);
}
