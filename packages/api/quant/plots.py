"""Visualization data generators: correlation matrix and efficient frontier with assets."""

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform

from quant.frontier import generate_efficient_frontier

__all__ = ["plot_correlation_matrix", "plot_efficient_frontier_with_assets"]


def plot_correlation_matrix(
    prices: pd.DataFrame,
    cluster: bool = True,
) -> dict:
    """Compute pairwise correlation matrix, optionally reordered by hierarchical clustering.

    Args:
        prices: Adjusted close prices DataFrame.
        cluster: If True, reorder tickers via ward linkage for visual clustering.

    Returns:
        dict with tickers (reordered), matrix (reordered), and cluster_order indices.
    """
    returns = prices.pct_change().dropna()
    corr = returns.corr().values
    tickers = list(prices.columns)

    if cluster and len(tickers) > 1:
        # Convert correlation to distance matrix: d = sqrt(0.5 * (1 - C))
        distance = np.sqrt(np.clip(0.5 * (1 - corr), 0, None))
        np.fill_diagonal(distance, 0.0)
        condensed = squareform(distance)
        lnk = linkage(condensed, method="ward")
        order = leaves_list(lnk).tolist()
    else:
        order = list(range(len(tickers)))

    reordered_tickers = [tickers[i] for i in order]
    reordered_corr = corr[np.ix_(order, order)]

    return {
        "tickers": reordered_tickers,
        "matrix": [[round(float(v), 4) for v in row] for row in reordered_corr],
        "cluster_order": order,
        "original_tickers": tickers,
    }


def plot_efficient_frontier_with_assets(
    prices: pd.DataFrame,
    n_points: int = 50,
    max_weight: float | None = None,
    risk_free_rate: float = 0.0,
) -> dict:
    """Generate efficient frontier data plus individual asset risk/return coordinates.

    Args:
        prices: Adjusted close prices DataFrame.
        n_points: Number of frontier points.
        max_weight: Max weight per asset on the frontier.
        risk_free_rate: Annual risk-free rate for Sharpe calculation.

    Returns:
        dict with frontier points, individual asset scatter coords, and max_sharpe_idx.
    """
    returns = prices.pct_change().dropna()
    mu = returns.mean().values * 252
    vol = returns.std().values * np.sqrt(252)
    tickers = list(prices.columns)

    frontier_result = generate_efficient_frontier(
        prices,
        n_points=n_points,
        max_weight=max_weight,
        risk_free_rate=risk_free_rate,
    )

    assets = [
        {
            "ticker": t,
            "volatility": round(float(v), 6),
            "expected_return": round(float(r), 6),
            "sharpe": round((float(r) - risk_free_rate) / float(v), 4) if float(v) > 1e-10 else 0.0,
        }
        for t, r, v in zip(tickers, mu, vol)
    ]

    return {
        "frontier": [
            {
                "volatility": p.volatility,
                "expected_return": p.expected_return,
                "sharpe": p.sharpe,
            }
            for p in frontier_result.points
        ],
        "assets": assets,
        "max_sharpe_idx": frontier_result.max_sharpe_idx,
    }
