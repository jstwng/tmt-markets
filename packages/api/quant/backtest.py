"""Simple vectorized portfolio backtester."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

__all__ = ["run_backtest", "BacktestResult", "BacktestMetrics"]


@dataclass
class BacktestMetrics:
    """Summary performance metrics.

    Attributes:
        total_return: Cumulative return over the period.
        cagr: Compound annual growth rate.
        sharpe: Annualized Sharpe ratio (assuming rf=0).
        max_drawdown: Maximum peak-to-trough drawdown.
        volatility: Annualized volatility.
    """
    total_return: float
    cagr: float
    sharpe: float
    max_drawdown: float
    volatility: float


@dataclass
class BacktestResult:
    """Result of a backtest run.

    Attributes:
        equity_curve: DataFrame with 'date' and 'value' columns.
        metrics: Summary performance metrics.
    """
    equity_curve: pd.DataFrame
    metrics: BacktestMetrics


def run_backtest(
    prices: pd.DataFrame,
    weights: dict[str, float],
    initial_capital: float = 100_000.0,
    rebalance_freq: Literal["daily", "weekly", "monthly"] = "monthly",
) -> BacktestResult:
    """Run a simple backtest with periodic rebalancing.

    Args:
        prices: DataFrame with columns as tickers, values as adjusted close prices.
        weights: Target portfolio weights (must sum to ~1.0).
        initial_capital: Starting capital.
        rebalance_freq: How often to rebalance.

    Returns:
        BacktestResult with equity curve and performance metrics.
    """
    tickers = list(weights.keys())
    w = np.array([weights[t] for t in tickers])
    price_data = prices[tickers].dropna()
    returns = price_data.pct_change().dropna()

    # Determine rebalance dates
    if rebalance_freq == "daily":
        rebalance_mask = pd.Series(True, index=returns.index)
    elif rebalance_freq == "weekly":
        rebalance_mask = returns.index.to_series().dt.dayofweek == 0
    elif rebalance_freq == "monthly":
        month = returns.index.to_series().dt.month
        rebalance_mask = month != month.shift(1)
    else:
        raise ValueError(f"Unknown rebalance_freq: {rebalance_freq}")

    # Simulate
    portfolio_value = initial_capital
    values = []

    current_weights = w.copy()
    for i, (date, ret) in enumerate(returns.iterrows()):
        daily_ret = ret.values
        # Apply returns to current weights
        current_weights = current_weights * (1 + daily_ret)
        portfolio_value = portfolio_value * (current_weights.sum() / (current_weights.sum() / (1 + daily_ret @ (current_weights / current_weights.sum())) if current_weights.sum() > 0 else 1))

        # Simpler approach: weighted return
        weighted_return = np.sum(w * daily_ret) if rebalance_mask.iloc[i] else np.sum(current_weights / current_weights.sum() * daily_ret)

        if rebalance_mask.iloc[i]:
            current_weights = w.copy()

        values.append({"date": date, "value": portfolio_value})

    # Rebuild using simple weighted returns approach
    values = []
    portfolio_value = initial_capital
    current_w = w.copy()

    for i, (date, ret) in enumerate(returns.iterrows()):
        daily_ret = ret.values
        weighted_ret = float(np.dot(current_w, daily_ret))
        portfolio_value *= (1 + weighted_ret)

        # Drift weights
        current_w = current_w * (1 + daily_ret)
        current_w = current_w / current_w.sum()

        # Rebalance
        if rebalance_mask.iloc[i]:
            current_w = w.copy()

        values.append({"date": str(date.date()), "value": round(portfolio_value, 2)})

    equity_curve = pd.DataFrame(values)

    # Compute metrics
    equity_series = equity_curve["value"]
    total_return = (equity_series.iloc[-1] / equity_series.iloc[0]) - 1
    n_days = len(equity_series)
    n_years = n_days / 252
    cagr = (equity_series.iloc[-1] / initial_capital) ** (1 / n_years) - 1 if n_years > 0 else 0.0

    daily_returns = equity_series.pct_change().dropna()
    volatility = float(daily_returns.std() * np.sqrt(252))
    sharpe = float(daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0.0

    # Max drawdown
    cummax = equity_series.cummax()
    drawdown = (equity_series - cummax) / cummax
    max_drawdown = float(drawdown.min())

    metrics = BacktestMetrics(
        total_return=round(float(total_return), 6),
        cagr=round(float(cagr), 6),
        sharpe=round(sharpe, 4),
        max_drawdown=round(max_drawdown, 6),
        volatility=round(volatility, 6),
    )

    return BacktestResult(equity_curve=equity_curve, metrics=metrics)
