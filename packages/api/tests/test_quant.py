"""Basic tests for quant library functions."""

import numpy as np
import pandas as pd
import pytest

from quant.covariance import estimate_covariance, InsufficientDataError
from quant.portfolio import optimize_portfolio
from quant.backtest import run_backtest
from quant.frontier import generate_efficient_frontier


def _make_prices(n_days: int = 252, n_assets: int = 3, seed: int = 42) -> pd.DataFrame:
    """Generate random price data for testing."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2023-01-01", periods=n_days)
    returns = rng.normal(0.0005, 0.02, (n_days, n_assets))
    prices = 100 * np.cumprod(1 + returns, axis=0)
    tickers = [f"ASSET{i}" for i in range(n_assets)]
    return pd.DataFrame(prices, index=dates, columns=tickers)


class TestCovariance:
    def test_sample_covariance(self):
        prices = _make_prices()
        result = estimate_covariance(prices, method="sample")
        assert result.matrix.shape == (3, 3)
        assert len(result.tickers) == 3
        assert result.method == "sample"

    def test_ledoit_wolf(self):
        prices = _make_prices()
        result = estimate_covariance(prices, method="ledoit_wolf")
        assert result.matrix.shape == (3, 3)
        # Diagonal should be positive (variances)
        assert all(result.matrix[i, i] > 0 for i in range(3))

    def test_insufficient_data(self):
        prices = _make_prices(n_days=2)
        with pytest.raises(InsufficientDataError):
            estimate_covariance(prices)


class TestPortfolio:
    def test_max_sharpe(self):
        prices = _make_prices()
        result = optimize_portfolio(prices, objective="max_sharpe")
        assert len(result.weights) == 3
        assert abs(sum(result.weights.values()) - 1.0) < 1e-4
        assert all(w >= -1e-6 for w in result.weights.values())

    def test_min_variance(self):
        prices = _make_prices()
        result = optimize_portfolio(prices, objective="min_variance")
        assert result.expected_volatility > 0

    def test_max_weight_constraint(self):
        prices = _make_prices()
        result = optimize_portfolio(prices, objective="max_sharpe", max_weight=0.5)
        assert all(w <= 0.5 + 1e-4 for w in result.weights.values())


class TestBacktest:
    def test_basic_backtest(self):
        prices = _make_prices()
        weights = {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}
        result = run_backtest(prices, weights, initial_capital=100_000)
        assert len(result.equity_curve) > 0
        assert result.metrics.volatility > 0
        assert result.metrics.max_drawdown <= 0

    def test_daily_rebalance(self):
        prices = _make_prices()
        weights = {"ASSET0": 0.5, "ASSET1": 0.5}
        result = run_backtest(prices[["ASSET0", "ASSET1"]], weights, rebalance_freq="daily")
        assert len(result.equity_curve) > 0


class TestEfficientFrontier:
    def test_generates_points(self):
        prices = _make_prices()
        result = generate_efficient_frontier(prices, n_points=20)
        assert len(result.points) > 0
        assert 0 <= result.max_sharpe_idx < len(result.points)

    def test_weights_sum_to_one(self):
        prices = _make_prices()
        result = generate_efficient_frontier(prices, n_points=20)
        for point in result.points:
            assert abs(sum(point.weights.values()) - 1.0) < 1e-3

    def test_max_sharpe_is_maximal(self):
        prices = _make_prices()
        result = generate_efficient_frontier(prices, n_points=20)
        max_sharpe = result.points[result.max_sharpe_idx].sharpe
        for point in result.points:
            assert point.sharpe <= max_sharpe + 1e-4

    def test_max_weight_constraint(self):
        prices = _make_prices()
        result = generate_efficient_frontier(prices, n_points=10, max_weight=0.5)
        for point in result.points:
            for w in point.weights.values():
                assert w <= 0.5 + 1e-4

    def test_volatility_increases_along_frontier(self):
        prices = _make_prices()
        result = generate_efficient_frontier(prices, n_points=20)
        vols = [p.volatility for p in result.points]
        # Frontier from min-variance: first half should be mostly non-decreasing
        assert vols[0] <= vols[-1] + 1e-4
