"""Extended portfolio optimization with explicit constraints."""

from typing import Literal
import numpy as np
import pandas as pd
from scipy.optimize import minimize

__all__ = ["optimize_with_constraints"]


def optimize_with_constraints(
    prices: pd.DataFrame,
    objective: Literal["min_variance", "max_sharpe", "risk_parity"] = "max_sharpe",
    min_weight: float = 0.0,
    max_weight: float = 1.0,
    sector_map: dict[str, str] | None = None,
    sector_caps: dict[str, float] | None = None,
    current_weights: dict[str, float] | None = None,
    max_turnover: float | None = None,
    risk_free_rate: float = 0.0,
) -> dict:
    """Optimize portfolio weights with extended constraints.

    Supports per-asset weight bounds, sector caps, and turnover limits
    in addition to the standard mean-variance objectives.

    Args:
        prices: Adjusted close prices.
        objective: Optimization objective.
        min_weight: Minimum weight per asset.
        max_weight: Maximum weight per asset.
        sector_map: Optional dict mapping ticker -> sector string.
        sector_caps: Optional dict mapping sector -> maximum total weight.
        current_weights: Current portfolio weights (needed for turnover constraint).
        max_turnover: Maximum total weight change allowed (sum of |w_new - w_old|).
        risk_free_rate: Annual risk-free rate for Sharpe calculation.

    Returns:
        dict with weights, expected_return, expected_volatility, sharpe, turnover.
    """
    returns = prices.pct_change().dropna()
    tickers = list(prices.columns)
    n = len(tickers)

    mu = returns.mean().values * 252
    cov = returns.cov().values * 252

    bounds = [(min_weight, max_weight)] * n
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    # Sector cap constraints
    if sector_map and sector_caps:
        for sector, cap in sector_caps.items():
            sector_tickers = [t for t in tickers if sector_map.get(t) == sector]
            if not sector_tickers:
                continue
            idx = [tickers.index(t) for t in sector_tickers]
            constraints.append({
                "type": "ineq",
                "fun": lambda w, idx=idx, cap=cap: cap - sum(w[i] for i in idx),
            })

    # Turnover constraint
    w_current = None
    if current_weights and max_turnover is not None:
        w_current = np.array([current_weights.get(t, 0.0) for t in tickers])
        constraints.append({
            "type": "ineq",
            "fun": lambda w, wc=w_current, mt=max_turnover: mt - np.sum(np.abs(w - wc)),
        })

    w0 = np.ones(n) / n
    if w_current is not None:
        w0 = w_current.copy()

    if objective == "min_variance":
        result = minimize(
            lambda w: w @ cov @ w,
            w0, method="SLSQP", bounds=bounds, constraints=constraints,
        )
    elif objective == "max_sharpe":
        def neg_sharpe(w: np.ndarray) -> float:
            ret = w @ mu
            vol = np.sqrt(w @ cov @ w)
            return -(ret - risk_free_rate) / vol if vol > 1e-10 else 0.0
        result = minimize(
            neg_sharpe, w0, method="SLSQP", bounds=bounds, constraints=constraints,
        )
    elif objective == "risk_parity":
        def risk_parity_obj(w: np.ndarray) -> float:
            port_vol = np.sqrt(w @ cov @ w)
            marginal = cov @ w
            risk_contrib = w * marginal / port_vol if port_vol > 1e-10 else np.zeros(n)
            target = port_vol / n
            return float(np.sum((risk_contrib - target) ** 2))
        result = minimize(
            risk_parity_obj, w0, method="SLSQP", bounds=bounds, constraints=constraints,
        )
    else:
        raise ValueError(f"Unknown objective: {objective}")

    w_opt = result.x
    port_return = float(w_opt @ mu)
    port_vol = float(np.sqrt(w_opt @ cov @ w_opt))
    sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 1e-10 else 0.0

    turnover = None
    if w_current is not None:
        turnover = round(float(np.sum(np.abs(w_opt - w_current))), 4)

    return {
        "weights": {t: round(float(w), 6) for t, w in zip(tickers, w_opt)},
        "expected_return": round(port_return, 6),
        "expected_volatility": round(port_vol, 6),
        "sharpe": round(sharpe, 4),
        "turnover": turnover,
        "objective": objective,
        "converged": bool(result.success),
    }
