"""Benchmark comparison and Brinson portfolio attribution."""

import numpy as np
import pandas as pd

from quant.data import fetch_prices

__all__ = ["compare_to_benchmark", "compute_portfolio_attribution"]


def compare_to_benchmark(
    prices: pd.DataFrame,
    weights: dict[str, float],
    benchmark_prices: pd.DataFrame,
    risk_free_rate: float = 0.0,
) -> dict:
    """Compare portfolio performance against a benchmark index.

    Args:
        prices: Adjusted close prices for portfolio assets.
        weights: Portfolio weights dict.
        benchmark_prices: Single-column DataFrame for the benchmark (e.g. SPY).
        risk_free_rate: Annual risk-free rate.

    Returns:
        dict with excess_return, tracking_error, information_ratio, beta,
        alpha, correlation, up_capture, down_capture.
    """
    tickers = list(weights.keys())
    w = np.array([weights[t] for t in tickers])

    # Align dates, then compute returns together so lengths are guaranteed equal
    combined = prices[tickers].join(benchmark_prices, how="inner")
    bm_col = benchmark_prices.columns[0]
    rets = combined.pct_change().dropna()
    port_rets = rets[tickers].values @ w
    bm_rets = rets[bm_col].values
    # no min/slicing needed — same length guaranteed

    daily_rf = risk_free_rate / 252
    excess_daily = port_rets - bm_rets

    ann_factor = 252
    ann_port = float(np.mean(port_rets)) * ann_factor
    ann_bm = float(np.mean(bm_rets)) * ann_factor
    excess_return = ann_port - ann_bm

    tracking_error = float(np.std(excess_daily)) * np.sqrt(ann_factor)
    information_ratio = excess_return / tracking_error if tracking_error > 1e-10 else 0.0

    # Beta via OLS
    cov_mat = np.cov(port_rets, bm_rets)
    beta = float(cov_mat[0, 1] / cov_mat[1, 1]) if cov_mat[1, 1] > 1e-10 else 0.0
    alpha = ann_port - risk_free_rate - beta * (ann_bm - risk_free_rate)
    correlation = float(np.corrcoef(port_rets, bm_rets)[0, 1])

    # Up/down capture
    up_mask = bm_rets > 0
    down_mask = bm_rets < 0
    up_capture = (
        float(np.mean(port_rets[up_mask])) / float(np.mean(bm_rets[up_mask]))
        if up_mask.sum() > 0 and abs(np.mean(bm_rets[up_mask])) > 1e-10
        else 1.0
    )
    down_capture = (
        float(np.mean(port_rets[down_mask])) / float(np.mean(bm_rets[down_mask]))
        if down_mask.sum() > 0 and abs(np.mean(bm_rets[down_mask])) > 1e-10
        else 1.0
    )

    return {
        "excess_return": round(excess_return, 6),
        "tracking_error": round(tracking_error, 6),
        "information_ratio": round(information_ratio, 4),
        "beta": round(beta, 4),
        "alpha": round(alpha, 6),
        "correlation": round(correlation, 4),
        "up_capture": round(up_capture, 4),
        "down_capture": round(down_capture, 4),
        "portfolio_return": round(ann_port, 6),
        "benchmark_return": round(ann_bm, 6),
    }


def compute_portfolio_attribution(
    prices: pd.DataFrame,
    portfolio_weights: dict[str, float],
    benchmark_weights: dict[str, float],
) -> dict:
    """Brinson-Hood-Beebower attribution decomposition.

    Decomposes active return into allocation effect, selection effect,
    and interaction effect relative to a benchmark.

    Args:
        prices: Adjusted close prices for all assets in both portfolio and benchmark.
        portfolio_weights: Portfolio weights (may differ from benchmark).
        benchmark_weights: Benchmark weights (baseline allocation).

    Returns:
        dict with per-asset effects and total active return.
    """
    all_tickers = sorted(set(list(portfolio_weights.keys()) + list(benchmark_weights.keys())))
    rets = prices[all_tickers].pct_change().dropna()

    # Total period returns for each asset
    total_rets = {t: float((1 + rets[t]).prod() - 1) for t in all_tickers}

    # Benchmark total return
    bm_total = sum(benchmark_weights.get(t, 0.0) * total_rets[t] for t in all_tickers)

    allocation = {}
    selection = {}
    interaction = {}

    for ticker in all_tickers:
        w_p = portfolio_weights.get(ticker, 0.0)
        w_b = benchmark_weights.get(ticker, 0.0)
        r_p = total_rets[ticker]  # simplified: same return for portfolio and benchmark asset
        r_b = total_rets[ticker]

        allocation[ticker] = round((w_p - w_b) * (r_b - bm_total), 6)
        selection[ticker] = round(w_b * (r_p - r_b), 6)
        interaction[ticker] = round((w_p - w_b) * (r_p - r_b), 6)

    port_total = sum(portfolio_weights.get(t, 0.0) * total_rets[t] for t in all_tickers)
    active_return = port_total - bm_total

    return {
        "assets": all_tickers,
        "allocation_effect": allocation,
        "selection_effect": selection,
        "interaction_effect": interaction,
        "portfolio_return": round(port_total, 6),
        "benchmark_return": round(bm_total, 6),
        "total_active_return": round(active_return, 6),
    }
