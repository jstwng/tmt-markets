"""Advanced portfolio analytics: Black-Litterman, Monte Carlo, liquidity, ranking, tearsheet."""

from typing import Literal
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from quant.risk import compute_var_cvar, compute_tail_risk_metrics, compute_drawdown_series
from quant.rolling import compute_rolling_metrics
from quant.attribution import compare_to_benchmark
from quant.backtest import run_backtest

__all__ = [
    "rank_assets_by_metric",
    "compute_liquidity_score",
    "apply_black_litterman",
    "run_monte_carlo",
    "generate_tearsheet",
]


def rank_assets_by_metric(
    prices: pd.DataFrame,
    metric: Literal["sharpe", "momentum", "volatility", "drawdown", "return"] = "sharpe",
    lookback_days: int = 252,
    risk_free_rate: float = 0.0,
    ascending: bool = False,
) -> dict:
    """Rank assets by a computed performance metric.

    Args:
        prices: Adjusted close prices.
        metric: Metric to rank by.
        lookback_days: Number of trailing days to compute metric over.
        risk_free_rate: Annual risk-free rate (used for Sharpe).
        ascending: Sort ascending (lowest first). Default False (highest first).

    Returns:
        dict with ranked list of {ticker, value, rank}.
    """
    prices_window = prices.tail(lookback_days)
    rets = prices_window.pct_change().dropna()
    tickers = list(prices.columns)
    results: list[dict] = []

    for t in tickers:
        r = rets[t].dropna()
        if len(r) < 5:
            continue

        if metric == "sharpe":
            ann_ret = float(r.mean()) * 252
            ann_vol = float(r.std()) * np.sqrt(252)
            value = (ann_ret - risk_free_rate) / ann_vol if ann_vol > 1e-10 else 0.0
        elif metric == "momentum":
            # Simple price momentum: total return over window
            p = prices_window[t].dropna()
            value = float(p.iloc[-1] / p.iloc[0] - 1) if len(p) >= 2 else 0.0
        elif metric == "volatility":
            value = float(r.std()) * np.sqrt(252)
        elif metric == "drawdown":
            equity = (1 + r).cumprod()
            cum_max = equity.cummax()
            value = float(((equity - cum_max) / cum_max).min())
        elif metric == "return":
            value = float(r.mean()) * 252
        else:
            raise ValueError(f"Unknown metric: {metric}")

        results.append({"ticker": t, "value": round(value, 6)})

    results.sort(key=lambda x: x["value"], reverse=not ascending)
    for i, item in enumerate(results, 1):
        item["rank"] = i

    return {
        "rankings": results,
        "metric": metric,
        "lookback_days": lookback_days,
    }


def compute_liquidity_score(
    prices: pd.DataFrame,
    weights: dict[str, float],
    portfolio_value: float = 1_000_000.0,
    volume_data: dict[str, float] | None = None,
    liquidation_days: int = 5,
) -> dict:
    """Estimate portfolio liquidity as fraction of average daily volume.

    A higher score means more liquid (position is smaller relative to ADV).
    Score = ADV / (position_size / liquidation_days).

    Args:
        prices: Adjusted close prices — used to estimate ADV if volume_data absent.
        weights: Portfolio weights dict.
        portfolio_value: Total portfolio value in dollars.
        volume_data: Optional dict of ticker -> average daily volume (shares).
                     If None, liquidity score is estimated from return volatility.
        liquidation_days: Target days to fully liquidate. Lower = more aggressive.

    Returns:
        dict with per-asset and aggregate liquidity scores.
    """
    tickers = [t for t in weights if t in prices.columns]
    scores: list[dict] = []

    for t in tickers:
        w = weights.get(t, 0.0)
        position_value = w * portfolio_value
        daily_liquidation_need = position_value / max(liquidation_days, 1)

        if volume_data and t in volume_data:
            adv_shares = volume_data[t]
            price = float(prices[t].iloc[-1])
            adv_value = adv_shares * price
            score = adv_value / daily_liquidation_need if daily_liquidation_need > 0 else float("inf")
        else:
            # Proxy: use inverse of 30-day volatility as liquidity proxy
            # (more volatile assets tend to be less liquid at scale)
            recent_vol = float(prices[t].pct_change().tail(30).std()) * np.sqrt(252)
            # Heuristic: score = 1 / vol (higher vol → lower liquidity score)
            score = (1.0 / recent_vol) if recent_vol > 1e-10 else 10.0

        scores.append({
            "ticker": t,
            "weight": round(w, 6),
            "position_value": round(position_value, 2),
            "liquidity_score": round(float(score), 4),
            "liquidity_category": (
                "high" if score >= 5.0
                else "medium" if score >= 1.0
                else "low"
            ),
        })

    aggregate = float(np.mean([s["liquidity_score"] for s in scores])) if scores else 0.0
    return {
        "assets": scores,
        "aggregate_liquidity_score": round(aggregate, 4),
        "portfolio_value": portfolio_value,
        "liquidation_days_assumption": liquidation_days,
    }


def apply_black_litterman(
    prices: pd.DataFrame,
    views: list[dict],
    market_weights: dict[str, float] | None = None,
    risk_aversion: float = 2.5,
    tau: float = 0.05,
    risk_free_rate: float = 0.0,
) -> dict:
    """Apply the Black-Litterman model to blend views with market equilibrium.

    Args:
        prices: Adjusted close prices.
        views: List of view dicts:
               {"tickers": [str, ...], "expected_return": float, "confidence": float}.
               Single-asset absolute view: {"tickers": ["AAPL"], "expected_return": 0.12, "confidence": 0.8}.
               Relative view: {"tickers": ["AAPL", "MSFT"], "expected_return": 0.02, "confidence": 0.6}
               means AAPL outperforms MSFT by 2% annualized.
        market_weights: Market cap weights. If None, equal-weight is used.
        risk_aversion: Implied risk aversion coefficient λ.
        tau: Scalar expressing uncertainty in prior (typically 0.025–0.1).
        risk_free_rate: Annual risk-free rate.

    Returns:
        dict with bl_expected_returns, bl_weights, prior_returns, views_summary.
    """
    returns = prices.pct_change().dropna()
    tickers = list(prices.columns)
    n = len(tickers)

    Sigma = returns.cov().values * 252

    # Market equilibrium weights
    if market_weights:
        w_mkt = np.array([market_weights.get(t, 1.0 / n) for t in tickers])
    else:
        w_mkt = np.ones(n) / n
    w_mkt = w_mkt / w_mkt.sum()

    # Implied equilibrium returns: π = λ * Σ * w_mkt
    pi = risk_aversion * Sigma @ w_mkt

    if not views:
        # No views — return equilibrium
        return {
            "bl_expected_returns": {t: round(float(v), 6) for t, v in zip(tickers, pi)},
            "prior_returns": {t: round(float(v), 6) for t, v in zip(tickers, pi)},
            "bl_weights": {t: round(float(w), 6) for t, w in zip(tickers, w_mkt)},
            "views_incorporated": 0,
            "note": "No views provided — returning market equilibrium.",
        }

    # Build P matrix (k x n) and q vector (k,) and Omega (k x k diagonal)
    k = len(views)
    P = np.zeros((k, n))
    q = np.zeros(k)
    omega_diag = np.zeros(k)

    for i, view in enumerate(views):
        view_tickers = view["tickers"]
        q[i] = float(view["expected_return"])
        confidence = float(view.get("confidence", 0.5))

        if len(view_tickers) == 1:
            # Absolute view
            t = view_tickers[0]
            if t in tickers:
                P[i, tickers.index(t)] = 1.0
        elif len(view_tickers) == 2:
            # Relative view: long first, short second
            t_long, t_short = view_tickers
            if t_long in tickers:
                P[i, tickers.index(t_long)] = 1.0
            if t_short in tickers:
                P[i, tickers.index(t_short)] = -1.0
        else:
            # Equal-long basket vs equal-short basket (split at midpoint)
            mid = len(view_tickers) // 2
            longs = view_tickers[:mid]
            shorts = view_tickers[mid:]
            for tl in longs:
                if tl in tickers:
                    P[i, tickers.index(tl)] = 1.0 / len(longs)
            for ts in shorts:
                if ts in tickers:
                    P[i, tickers.index(ts)] = -1.0 / len(shorts)

        # Omega: uncertainty inversely proportional to confidence
        # Ω_ii = (1 - confidence) / confidence * (P_i Σ P_i^T)
        p_i = P[i]
        variance_of_view = float(p_i @ Sigma @ p_i)
        omega_diag[i] = variance_of_view * (1.0 - confidence) / max(confidence, 1e-6)

    Omega = np.diag(omega_diag)

    # BL formula:
    # μ_BL = [(τΣ)^-1 + P'Ω^-1P]^-1 * [(τΣ)^-1 π + P'Ω^-1 q]
    tauSigma = tau * Sigma
    tauSigma_inv = np.linalg.pinv(tauSigma)
    Omega_inv = np.linalg.pinv(Omega)

    M_inv = tauSigma_inv + P.T @ Omega_inv @ P
    M = np.linalg.pinv(M_inv)
    mu_bl = M @ (tauSigma_inv @ pi + P.T @ Omega_inv @ q)

    # Optimal BL weights: w = (λΣ)^-1 μ_BL, normalized
    Sigma_inv = np.linalg.pinv(Sigma)
    w_raw = Sigma_inv @ (mu_bl - risk_free_rate)
    w_raw = np.clip(w_raw, 0, None)
    # Note: standard BL allows negative weights; we clip to 0 for practical long-only
    # portfolios. For unconstrained BL, remove the clip and use w_raw directly.
    w_bl = w_raw / w_raw.sum() if w_raw.sum() > 1e-10 else w_mkt

    views_summary = [
        {
            "tickers": v["tickers"],
            "expected_return": v["expected_return"],
            "confidence": v.get("confidence", 0.5),
        }
        for v in views
    ]

    return {
        "bl_expected_returns": {t: round(float(v), 6) for t, v in zip(tickers, mu_bl)},
        "prior_returns": {t: round(float(v), 6) for t, v in zip(tickers, pi)},
        "bl_weights": {t: round(float(w), 6) for t, w in zip(tickers, w_bl)},
        "views_incorporated": k,
        "views_summary": views_summary,
    }


def run_monte_carlo(
    prices: pd.DataFrame,
    weights: dict[str, float],
    n_simulations: int = 500,
    n_days: int = 252,
    initial_value: float = 100_000.0,
    percentiles: list[float] | None = None,
    seed: int | None = None,
) -> dict:
    """Simulate forward portfolio paths using Cholesky-decomposed GBM.

    Args:
        prices: Historical adjusted close prices (used to calibrate μ and Σ).
        weights: Portfolio weights dict.
        n_simulations: Number of Monte Carlo paths.
        n_days: Number of forward trading days to simulate.
        initial_value: Starting portfolio value.
        percentiles: Percentiles to report. Default: [5, 25, 50, 75, 95].
        seed: Random seed for reproducibility.

    Returns:
        dict with percentile fan chart data, terminal stats, and VaR/CVaR.
    """
    if percentiles is None:
        percentiles = [5, 25, 50, 75, 95]

    rng = np.random.default_rng(seed)
    tickers = [t for t in weights if t in prices.columns]
    w = np.array([weights[t] for t in tickers])
    w = w / w.sum()

    rets = prices[tickers].pct_change().dropna()
    mu_daily = rets.mean().values
    Sigma_daily = rets.cov().values

    # Cholesky decomposition for correlated returns
    try:
        L = np.linalg.cholesky(Sigma_daily + np.eye(len(tickers)) * 1e-10)
    except np.linalg.LinAlgError:
        L = np.diag(np.sqrt(np.diag(Sigma_daily)))

    # Simulate: shape (n_simulations, n_days)
    terminal_values = np.zeros(n_simulations)
    # Store percentile paths — compute all simulations then take percentiles
    all_paths = np.zeros((n_simulations, n_days))

    for sim in range(n_simulations):
        z = rng.standard_normal((n_days, len(tickers)))
        sim_rets = z @ L.T + mu_daily  # correlated daily returns
        port_rets = sim_rets @ w
        equity = initial_value * np.cumprod(1 + port_rets)
        all_paths[sim] = equity

    terminal_values = all_paths[:, -1]

    # Percentile fan chart: for each day, compute percentile across simulations
    fan_chart: dict[str, list[float]] = {}
    for p in percentiles:
        fan_chart[f"p{int(p)}"] = [
            round(float(v), 2) for v in np.percentile(all_paths, p, axis=0)
        ]

    # Terminal value stats
    terminal_mean = float(np.mean(terminal_values))
    terminal_median = float(np.median(terminal_values))
    terminal_std = float(np.std(terminal_values))

    # VaR and CVaR at 95% confidence
    confidence = 0.95
    terminal_rets = terminal_values / initial_value - 1
    var_95 = float(np.percentile(terminal_rets, (1 - confidence) * 100))
    cvar_95 = float(np.mean(terminal_rets[terminal_rets <= var_95]))

    prob_profit = float(np.mean(terminal_values > initial_value))

    return {
        "fan_chart": fan_chart,
        "n_days": n_days,
        "n_simulations": n_simulations,
        "initial_value": initial_value,
        "terminal": {
            "mean": round(terminal_mean, 2),
            "median": round(terminal_median, 2),
            "std": round(terminal_std, 2),
            "var_95": round(var_95, 6),
            "cvar_95": round(cvar_95, 6),
            "prob_profit": round(prob_profit, 4),
            "percentiles": {
                f"p{int(p)}": round(float(np.percentile(terminal_values, p)), 2)
                for p in percentiles
            },
        },
    }


def generate_tearsheet(
    prices: pd.DataFrame,
    weights: dict[str, float],
    benchmark_prices: pd.DataFrame | None = None,
    risk_free_rate: float = 0.0,
    initial_capital: float = 100_000.0,
    rolling_window: int = 63,
) -> dict:
    """Generate a comprehensive portfolio tearsheet.

    Bundles performance metrics, risk metrics, rolling analytics,
    drawdown series, and factor exposures into a single structured artifact.

    Args:
        prices: Adjusted close prices for portfolio assets.
        weights: Portfolio weights dict.
        benchmark_prices: Optional benchmark for relative metrics.
        risk_free_rate: Annual risk-free rate.
        initial_capital: Starting capital for equity curve.
        rolling_window: Window for rolling metrics (trading days).

    Returns:
        dict with sections: summary, performance, risk, rolling, drawdown.
    """
    tickers = [t for t in weights if t in prices.columns]
    w = np.array([weights[t] for t in tickers])

    # Backtest for equity curve and core metrics
    backtest = run_backtest(
        prices[tickers],
        weights={t: weights[t] for t in tickers},
        initial_capital=initial_capital,
        rebalance_freq="monthly",
    )
    m = backtest.metrics

    # Risk metrics
    var_result = compute_var_cvar(prices[tickers], {t: weights[t] for t in tickers})
    tail_result = compute_tail_risk_metrics(prices[tickers], {t: weights[t] for t in tickers},
                                            risk_free_rate=risk_free_rate)
    dd_result = compute_drawdown_series(prices[tickers], {t: weights[t] for t in tickers})

    # Rolling metrics
    rolling_result = compute_rolling_metrics(
        prices[tickers], {t: weights[t] for t in tickers},
        window=rolling_window,
        benchmark_prices=benchmark_prices,
        risk_free_rate=risk_free_rate,
    )

    dd_series = dd_result.get("drawdown", [])

    # Benchmark comparison (if provided)
    benchmark_section = None
    if benchmark_prices is not None:
        bm_result = compare_to_benchmark(
            prices[tickers], {t: weights[t] for t in tickers}, benchmark_prices,
            risk_free_rate=risk_free_rate,
        )
        benchmark_section = bm_result

    equity_records = backtest.equity_curve.to_dict(orient="records")
    equity_curve = [
        {"date": str(r["date"].date()) if hasattr(r["date"], "date") else str(r["date"]), "value": r["value"]}
        for r in equity_records
    ]

    return {
        "summary": {
            "tickers": tickers,
            "weights": {t: round(float(weights[t]), 6) for t in tickers},
            "n_assets": len(tickers),
            "initial_capital": initial_capital,
            "risk_free_rate": risk_free_rate,
        },
        "performance": {
            "total_return": round(float(m.total_return), 6),
            "cagr": round(float(m.cagr), 6),
            "sharpe": round(float(m.sharpe), 4),
            "max_drawdown": round(float(m.max_drawdown), 6),
            "volatility": round(float(m.volatility), 6),
        },
        "risk": {
            "var_95": var_result.get("var"),
            "cvar_95": var_result.get("cvar"),
            "annualized_var": var_result.get("annualized_var"),
            "sortino": tail_result.get("sortino"),
            "calmar": tail_result.get("calmar"),
            "omega": tail_result.get("omega"),
            "skewness": tail_result.get("skewness"),
            "kurtosis": tail_result.get("kurtosis"),
        },
        "drawdown": {
            "max_drawdown": dd_result.get("max_drawdown"),
            "max_drawdown_duration_days": dd_result.get("max_drawdown_duration_days"),
            "current_drawdown": dd_series[-1] if dd_series else None,
            "series": dd_series[-252:],  # last year
        },
        "rolling": {
            "window": rolling_window,
            "dates": rolling_result["dates"][-252:],
            "sharpe": rolling_result["rolling_sharpe"][-252:],
            "volatility": rolling_result["rolling_volatility"][-252:],
            "drawdown": rolling_result["rolling_drawdown"][-252:],
        },
        "equity_curve": equity_curve,
        "benchmark": benchmark_section,
    }
