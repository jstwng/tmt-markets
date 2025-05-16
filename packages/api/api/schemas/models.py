from pydantic import BaseModel
from typing import Literal


# --- Covariance ---

class CovarianceRequest(BaseModel):
    tickers: list[str]
    start_date: str
    end_date: str
    method: Literal["sample", "ledoit_wolf", "shrunk"] = "ledoit_wolf"


class CovarianceResponse(BaseModel):
    matrix: list[list[float]]
    tickers: list[str]
    method: str


# --- Portfolio ---

class PortfolioOptimizeRequest(BaseModel):
    tickers: list[str]
    start_date: str
    end_date: str
    objective: Literal["min_variance", "max_sharpe", "risk_parity"] = "max_sharpe"
    max_weight: float | None = None


class PortfolioOptimizeResponse(BaseModel):
    weights: dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe: float


# --- Backtest ---

class BacktestRequest(BaseModel):
    tickers: list[str]
    weights: dict[str, float]
    start_date: str
    end_date: str
    initial_capital: float = 100_000.0
    rebalance_freq: Literal["daily", "weekly", "monthly"] = "monthly"


class EquityCurvePoint(BaseModel):
    date: str
    value: float


class BacktestMetrics(BaseModel):
    total_return: float
    cagr: float
    sharpe: float
    max_drawdown: float
    volatility: float


class BacktestResponse(BaseModel):
    equity_curve: list[EquityCurvePoint]
    metrics: BacktestMetrics


# --- Data ---

class PricesRequest(BaseModel):
    tickers: list[str]
    start_date: str
    end_date: str
    source: Literal["yfinance", "openbb"] = "yfinance"


class PricesResponse(BaseModel):
    dates: list[str]
    tickers: list[str]
    prices: dict[str, list[float]]
