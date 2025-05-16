"""Efficient frontier generation via mean-variance optimization."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy.optimize import minimize

__all__ = ["generate_efficient_frontier", "FrontierResult", "FrontierPoint"]


@dataclass
class FrontierPoint:
    """A single point on the efficient frontier.

    Attributes:
        volatility: Annualized portfolio volatility.
        expected_return: Annualized expected portfolio return.
        weights: Dict mapping ticker to weight.
        sharpe: Sharpe ratio (rf=0).
    """
    volatility: float
    expected_return: float
    weights: dict[str, float]
    sharpe: float


@dataclass
class FrontierResult:
    """Result of efficient frontier generation.

    Attributes:
        points: List of frontier points from min-variance to max-return.
        max_sharpe_idx: Index of the maximum Sharpe ratio point.
    """
    points: list[FrontierPoint]
    max_sharpe_idx: int


def generate_efficient_frontier(
    prices: pd.DataFrame,
    n_points: int = 50,
    max_weight: float | None = None,
    risk_free_rate: float = 0.0,
) -> FrontierResult:
    """Generate the efficient frontier by sweeping target returns.

    Args:
        prices: DataFrame with columns as tickers, values as adjusted close prices.
        n_points: Number of frontier points to compute.
        max_weight: Maximum weight per asset. None = no constraint.
        risk_free_rate: Annual risk-free rate for Sharpe calculation.

    Returns:
        FrontierResult with frontier points and max-Sharpe index.
    """
    returns = prices.pct_change().dropna()
    tickers = list(prices.columns)
    n = len(tickers)

    mu = returns.mean().values * 252  # annualized
    cov = returns.cov().values * 252  # annualized

    upper = max_weight if max_weight else 1.0
    bounds = [(0.0, upper)] * n
    w0 = np.ones(n) / n

    # Find min-variance and max-return anchors
    def portfolio_stats(w: np.ndarray) -> tuple[float, float]:
        ret = float(w @ mu)
        vol = float(np.sqrt(w @ cov @ w))
        return ret, vol

    # Min-variance portfolio
    min_var_result = minimize(
        lambda w: w @ cov @ w,
        w0,
        method="SLSQP",
        bounds=bounds,
        constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}],
    )
    min_ret, _ = portfolio_stats(min_var_result.x)

    # Max-return portfolio (maximize expected return = minimize negative)
    max_ret_result = minimize(
        lambda w: -(w @ mu),
        w0,
        method="SLSQP",
        bounds=bounds,
        constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}],
    )
    max_ret, _ = portfolio_stats(max_ret_result.x)

    # Sweep target returns from min to max
    target_returns = np.linspace(min_ret, max_ret, n_points)
    points: list[FrontierPoint] = []

    for target_ret in target_returns:
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w, t=target_ret: w @ mu - t},
        ]
        result = minimize(
            lambda w: w @ cov @ w,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if not result.success:
            # Fallback: skip infeasible points
            continue

        w_opt = result.x
        ret, vol = portfolio_stats(w_opt)
        sharpe = (ret - risk_free_rate) / vol if vol > 1e-10 else 0.0

        points.append(FrontierPoint(
            volatility=round(vol, 6),
            expected_return=round(ret, 6),
            weights={t: round(float(w), 6) for t, w in zip(tickers, w_opt)},
            sharpe=round(sharpe, 4),
        ))

    if not points:
        raise ValueError("Could not generate any valid frontier points")

    # Find max-Sharpe index
    max_sharpe_idx = int(np.argmax([p.sharpe for p in points]))

    return FrontierResult(points=points, max_sharpe_idx=max_sharpe_idx)
