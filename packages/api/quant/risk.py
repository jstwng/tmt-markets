"""Portfolio risk analytics: VaR/CVaR, tail metrics, risk decomposition, drawdown."""

from typing import Literal
import numpy as np
import pandas as pd
import scipy.stats as stats
from sklearn.decomposition import PCA

from quant.covariance import estimate_covariance

__all__ = [
    "compute_var_cvar",
    "compute_tail_risk_metrics",
    "decompose_risk",
    "compute_drawdown_series",
]


def _portfolio_returns(prices: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    tickers = list(weights.keys())
    w = np.array([weights[t] for t in tickers])
    returns = prices[tickers].pct_change().dropna()
    return returns.values @ w


def compute_var_cvar(
    prices: pd.DataFrame,
    weights: dict[str, float],
    confidence_level: float = 0.95,
    method: Literal["historical", "parametric", "monte_carlo"] = "historical",
    n_simulations: int = 10_000,
) -> dict:
    """Compute Value-at-Risk and Conditional VaR (Expected Shortfall).

    Args:
        prices: Adjusted close prices DataFrame.
        weights: Portfolio weights dict (ticker -> float, sum ~1).
        confidence_level: Confidence level, e.g. 0.95 or 0.99.
        method: Estimation method.
        n_simulations: Number of MC paths (only for 'monte_carlo').

    Returns:
        dict with var, cvar, confidence_level, method.
    """
    tickers = list(weights.keys())
    w = np.array([weights[t] for t in tickers])
    rets = prices[tickers].pct_change().dropna()
    port_rets = rets.values @ w

    alpha = 1.0 - confidence_level

    if method == "historical":
        var = -float(np.quantile(port_rets, alpha))
        tail = port_rets[port_rets <= -var]
        cvar = -float(tail.mean()) if len(tail) > 0 else var

    elif method == "parametric":
        mu = float(port_rets.mean())
        sigma = float(port_rets.std())
        z = stats.norm.ppf(alpha)
        var = -(mu + z * sigma)
        cvar = -(mu - sigma * stats.norm.pdf(z) / alpha)

    elif method == "monte_carlo":
        mu_vec = rets.mean().values
        cov_mat = rets.cov().values
        rng = np.random.default_rng(42)
        sim_rets = rng.multivariate_normal(mu_vec, cov_mat, n_simulations)
        sim_port = sim_rets @ w
        var = -float(np.quantile(sim_port, alpha))
        tail = sim_port[sim_port <= -var]
        cvar = -float(tail.mean()) if len(tail) > 0 else var
    else:
        raise ValueError(f"Unknown method: {method}")

    return {
        "var": round(var, 6),
        "cvar": round(cvar, 6),
        "confidence_level": confidence_level,
        "method": method,
        "annualized_var": round(var * np.sqrt(252), 6),
    }


def compute_tail_risk_metrics(
    prices: pd.DataFrame,
    weights: dict[str, float],
    risk_free_rate: float = 0.0,
    mar: float = 0.0,
) -> dict:
    """Compute higher-moment and downside risk metrics.

    Returns skewness, kurtosis, Sortino, Calmar, and Omega ratios.
    """
    port_rets = _portfolio_returns(prices, weights)
    daily_rf = risk_free_rate / 252
    excess = port_rets - daily_rf

    # Annualized stats
    ann_ret = float(np.mean(port_rets)) * 252
    ann_vol = float(np.std(port_rets)) * np.sqrt(252)

    skew = float(stats.skew(port_rets))
    kurt = float(stats.kurtosis(port_rets))  # excess kurtosis

    # Sortino: downside deviation relative to MAR
    daily_mar = mar / 252
    downside = port_rets[port_rets < daily_mar] - daily_mar
    downside_dev = float(np.sqrt(np.mean(downside ** 2))) * np.sqrt(252) if len(downside) > 0 else 1e-10
    sortino = (ann_ret - mar) / downside_dev if downside_dev > 1e-10 else 0.0

    # Calmar: annualized return / max drawdown
    equity = pd.Series(np.cumprod(1 + port_rets))
    cum_max = equity.cummax()
    drawdown = (equity - cum_max) / cum_max
    max_dd = float(drawdown.min())
    calmar = ann_ret / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

    # Omega: ratio of gains above threshold to losses below
    threshold = daily_mar
    gains = float(np.sum(np.maximum(port_rets - threshold, 0)))
    losses = float(np.sum(np.maximum(threshold - port_rets, 0)))
    omega = gains / losses if losses > 1e-10 else float("inf")

    return {
        "skewness": round(skew, 4),
        "kurtosis": round(kurt, 4),
        "sortino": round(sortino, 4),
        "calmar": round(calmar, 4),
        "omega": round(min(omega, 999.0), 4),
        "annualized_return": round(ann_ret, 6),
        "annualized_volatility": round(ann_vol, 6),
    }


def decompose_risk(
    prices: pd.DataFrame,
    weights: dict[str, float],
    n_factors: int = 3,
) -> dict:
    """Decompose portfolio variance into asset-level marginal contributions and PCA factors.

    Args:
        prices: Adjusted close prices.
        weights: Portfolio weights.
        n_factors: Number of PCA factors to extract.

    Returns:
        dict with marginal_contributions, percent_contributions, and PCA factor info.
    """
    tickers = list(weights.keys())
    w = np.array([weights[t] for t in tickers])
    cov_result = estimate_covariance(prices[tickers])
    cov = cov_result.matrix  # annualized

    # Marginal risk contributions
    port_vol = float(np.sqrt(w @ cov @ w))
    if port_vol < 1e-10:
        marginal = np.zeros(len(w))
    else:
        marginal = (cov @ w) / port_vol  # marginal contribution to vol

    risk_contrib = w * marginal  # absolute contribution
    pct_contrib = risk_contrib / port_vol if port_vol > 1e-10 else np.zeros(len(w))

    # PCA on covariance matrix
    n_factors = min(n_factors, len(tickers))
    pca = PCA(n_components=n_factors)
    returns = prices[tickers].pct_change().dropna()
    pca.fit(returns.values)

    return {
        "marginal_contributions": {t: round(float(v), 6) for t, v in zip(tickers, risk_contrib)},
        "percent_contributions": {t: round(float(v), 4) for t, v in zip(tickers, pct_contrib)},
        "portfolio_volatility": round(port_vol, 6),
        "factor_variance_explained": [round(float(v), 4) for v in pca.explained_variance_ratio_],
        "factor_loadings": pca.components_.tolist(),
    }


def compute_drawdown_series(
    prices: pd.DataFrame,
    weights: dict[str, float],
) -> dict:
    """Compute full drawdown time series and summary statistics.

    Returns dates, drawdown values, max drawdown, average drawdown,
    drawdown duration, and recovery duration.
    """
    tickers = list(weights.keys())
    w = np.array([weights[t] for t in tickers])
    price_data = prices[tickers].dropna()
    returns = price_data.pct_change().dropna()
    port_rets = returns.values @ w

    equity = pd.Series(np.cumprod(1 + port_rets), index=returns.index)
    cum_max = equity.cummax()
    dd = (equity - cum_max) / cum_max

    max_dd = float(dd.min())
    max_dd_date = str(dd.idxmin().date()) if not dd.empty else ""
    avg_dd = float(dd[dd < 0].mean()) if (dd < 0).any() else 0.0

    # Drawdown duration: consecutive days below 0
    in_dd = (dd < -1e-6).astype(int)
    duration = 0
    max_duration = 0
    for v in in_dd.values:
        if v:
            duration += 1
            max_duration = max(max_duration, duration)
        else:
            duration = 0

    # Recovery: days from max drawdown trough to recovery
    trough_idx = int(dd.argmin())
    recovery_days = None
    peak_val = float(cum_max.iloc[trough_idx])
    for i in range(trough_idx, len(equity)):
        if equity.iloc[i] >= peak_val:
            recovery_days = i - trough_idx
            break

    return {
        "dates": [str(d.date()) for d in dd.index],
        "drawdown": [round(float(v), 6) for v in dd.values],
        "max_drawdown": round(max_dd, 6),
        "max_drawdown_date": max_dd_date,
        "avg_drawdown": round(avg_dd, 6),
        "max_drawdown_duration_days": max_duration,
        "recovery_duration_days": recovery_days,
    }
