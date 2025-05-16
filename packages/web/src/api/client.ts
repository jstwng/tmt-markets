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

export async function healthCheck(): Promise<{ status: string }> {
  return get("/health");
}

export async function computeCovariance(
  req: CovarianceRequest
): Promise<CovarianceResponse> {
  return post("/covariance", req);
}

export async function optimizePortfolio(
  req: PortfolioOptimizeRequest
): Promise<PortfolioOptimizeResponse> {
  return post("/portfolio/optimize", req);
}

export async function runBacktest(
  req: BacktestRequest
): Promise<BacktestResponse> {
  return post("/backtest", req);
}

export async function fetchPrices(
  req: PricesRequest
): Promise<PricesResponse> {
  return post("/data/prices", req);
}

export async function generateFrontier(
  req: EfficientFrontierRequest
): Promise<EfficientFrontierResponse> {
  return post("/portfolio/frontier", req);
}
