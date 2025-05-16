"""Portfolio optimization using mean-variance framework."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy.optimize import minimize

__all__ = ["optimize_portfolio", "PortfolioResult"]


@dataclass
class PortfolioResult:
    """Result of portfolio optimization.

    Attributes:
        weights: Dict mapping ticker to optimal weight.
        expected_return: Annualized expected portfolio return.
        expected_volatility: Annualized expected portfolio volatility.
        sharpe: Estimated Sharpe ratio (assuming risk-free rate = 0).
    """
    weights: dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe: float


def optimize_portfolio(
    prices: pd.DataFrame,
    objective: Literal["min_variance", "max_sharpe", "risk_parity"] = "max_sharpe",
    max_weight: float | None = None,
    risk_free_rate: float = 0.0,
) -> PortfolioResult:
    """Optimize portfolio weights given historical prices.

    Args:
        prices: DataFrame with columns as tickers, values as adjusted close prices.
        objective: Optimization objective.
        max_weight: Maximum weight per asset (e.g., 0.4 for 40%). None = no constraint.
        risk_free_rate: Annual risk-free rate for Sharpe calculation.

    Returns:
        PortfolioResult with optimal weights and expected metrics.
    """
    returns = prices.pct_change().dropna()
    tickers = list(prices.columns)
    n = len(tickers)

    mu = returns.mean().values * 252  # annualized
    cov = returns.cov().values * 252  # annualized

    # Constraints: weights sum to 1, all >= 0
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    upper = max_weight if max_weight else 1.0
    bounds = [(0.0, upper)] * n
    w0 = np.ones(n) / n

    if objective == "min_variance":
        result = minimize(
            lambda w: w @ cov @ w,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
    elif objective == "max_sharpe":
        def neg_sharpe(w: np.ndarray) -> float:
            ret = w @ mu
            vol = np.sqrt(w @ cov @ w)
            return -(ret - risk_free_rate) / vol if vol > 1e-10 else 0.0

        result = minimize(
            neg_sharpe,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
    elif objective == "risk_parity":
        def risk_parity_obj(w: np.ndarray) -> float:
            port_vol = np.sqrt(w @ cov @ w)
            marginal_contrib = cov @ w
            risk_contrib = w * marginal_contrib / port_vol
            target = port_vol / n
            return np.sum((risk_contrib - target) ** 2)

        result = minimize(
            risk_parity_obj,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
    else:
        raise ValueError(f"Unknown objective: {objective}")

    w_opt = result.x
    port_return = float(w_opt @ mu)
    port_vol = float(np.sqrt(w_opt @ cov @ w_opt))
    sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 1e-10 else 0.0

    return PortfolioResult(
        weights={t: round(float(w), 6) for t, w in zip(tickers, w_opt)},
        expected_return=round(port_return, 6),
        expected_volatility=round(port_vol, 6),
        sharpe=round(sharpe, 4),
    )
