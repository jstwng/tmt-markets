"""
Verify that every tool wrapper in api/agent/tools.py:
  1. Calls the underlying quant function with correct parameters (no crash)
  2. Returns a dict with the keys the frontend block-mapper expects

All tests use synthetic price data — no network required.
_prices() is monkey-patched to return a synthetic DataFrame.
"""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------

def _make_prices(n_days: int = 500, n_assets: int = 3, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2000-01-01", periods=n_days)
    returns = rng.normal(0.0005, 0.015, (n_days, n_assets))
    prices = 100 * np.cumprod(1 + returns, axis=0)
    tickers = ["AAPL", "MSFT", "GOOGL"]
    return pd.DataFrame(prices, index=dates, columns=tickers)


PRICES = _make_prices()
TICKERS = list(PRICES.columns)
WEIGHTS = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}
BASE_ARGS = {
    "tickers": TICKERS,
    "start_date": "2000-01-01",
    "end_date": "2002-01-01",
    "weights": WEIGHTS,
}


# Long-term prices for scenario tools
LONG_PRICES = _make_prices(n_days=6000, n_assets=3, seed=99)  # ~24 years


def _patch_prices(return_value=None):
    """Return a context manager that patches _prices in tools.py."""
    val = return_value if return_value is not None else PRICES
    return patch("api.agent.tools._prices", return_value=val)


def _patch_fetch_prices(return_value=None):
    """Patch fetch_prices used directly in wrappers (benchmark tools)."""
    val = return_value if return_value is not None else PRICES
    return patch("api.agent.tools.fetch_prices", return_value=val)


# ---------------------------------------------------------------------------
# Import the private wrappers
# ---------------------------------------------------------------------------
from api.agent.tools import (
    _run_fetch_prices,
    _run_estimate_covariance,
    _run_optimize_portfolio,
    _run_backtest,
    _run_generate_frontier,
    _run_compute_var_cvar,
    _run_compute_tail_risk_metrics,
    _run_decompose_risk,
    _run_compute_drawdown_series,
    _run_compare_to_benchmark,
    _run_portfolio_attribution,
    _run_plot_correlation_matrix,
    _run_plot_frontier_with_assets,
    _run_compute_factor_exposure,
    _run_estimate_expected_returns,
    _run_stress_test,
    _run_scenario_return_table,
    _run_compute_rolling_metrics,
    _run_rebalancing_analysis,
    _run_optimize_with_constraints,
    _run_rank_assets_by_metric,
    _run_compute_liquidity_score,
    _run_apply_black_litterman,
    _run_monte_carlo,
    _run_generate_tearsheet,
)


# ---------------------------------------------------------------------------
# fetch_prices
# ---------------------------------------------------------------------------

class TestFetchPrices:
    def test_returns_expected_keys(self):
        with _patch_prices():
            result = _run_fetch_prices(BASE_ARGS)
        assert "dates" in result
        assert "tickers" in result
        assert "prices" in result
        assert isinstance(result["tickers"], list)
        assert len(result["prices"]) == len(result["tickers"])


# ---------------------------------------------------------------------------
# estimate_covariance
# ---------------------------------------------------------------------------

class TestEstimateCovariance:
    def test_returns_matrix_and_tickers(self):
        with _patch_prices():
            result = _run_estimate_covariance(BASE_ARGS)
        assert "matrix" in result
        assert "tickers" in result
        n = len(result["tickers"])
        assert len(result["matrix"]) == n
        assert len(result["matrix"][0]) == n


# ---------------------------------------------------------------------------
# optimize_portfolio
# ---------------------------------------------------------------------------

class TestOptimizePortfolio:
    def test_weights_sum_to_one(self):
        with _patch_prices():
            result = _run_optimize_portfolio(BASE_ARGS)
        assert "weights" in result
        assert abs(sum(result["weights"].values()) - 1.0) < 1e-3

    def test_returns_sharpe_and_stats(self):
        with _patch_prices():
            result = _run_optimize_portfolio(BASE_ARGS)
        assert "expected_return" in result
        assert "expected_volatility" in result
        assert "sharpe" in result


# ---------------------------------------------------------------------------
# run_backtest
# ---------------------------------------------------------------------------

class TestRunBacktest:
    def test_returns_equity_curve_and_metrics(self):
        args = {**BASE_ARGS, "weights": WEIGHTS}
        with _patch_prices():
            result = _run_backtest(args)
        assert "equity_curve" in result
        assert "metrics" in result
        assert len(result["equity_curve"]) > 0
        assert "total_return" in result["metrics"]


# ---------------------------------------------------------------------------
# generate_efficient_frontier
# ---------------------------------------------------------------------------

class TestGenerateEfficientFrontier:
    def test_returns_points_and_max_sharpe_idx(self):
        with _patch_prices():
            result = _run_generate_frontier(BASE_ARGS)
        assert "points" in result
        assert "max_sharpe_idx" in result
        assert len(result["points"]) > 0
        pt = result["points"][0]
        assert "volatility" in pt and "expected_return" in pt and "sharpe" in pt


# ---------------------------------------------------------------------------
# compute_var_cvar — must return 95 AND 99 confidence levels
# ---------------------------------------------------------------------------

class TestComputeVarCvar:
    def test_returns_four_values(self):
        with _patch_prices():
            result = _run_compute_var_cvar(BASE_ARGS)
        for key in ("var_95", "cvar_95", "var_99", "cvar_99"):
            assert key in result, f"Missing {key}"
        assert "method" in result

    def test_99_var_ge_95_var(self):
        with _patch_prices():
            result = _run_compute_var_cvar(BASE_ARGS)
        assert result["var_99"] >= result["var_95"] - 1e-6


# ---------------------------------------------------------------------------
# compute_tail_risk_metrics — must include var_95, cvar_95, max_drawdown
# ---------------------------------------------------------------------------

class TestComputeTailRiskMetrics:
    def test_returns_frontend_expected_keys(self):
        with _patch_prices():
            result = _run_compute_tail_risk_metrics(BASE_ARGS)
        for key in ("skewness", "kurtosis", "var_95", "cvar_95", "max_drawdown"):
            assert key in result, f"Missing {key}"

    def test_max_drawdown_is_non_positive(self):
        with _patch_prices():
            result = _run_compute_tail_risk_metrics(BASE_ARGS)
        assert result["max_drawdown"] <= 0


# ---------------------------------------------------------------------------
# decompose_risk — must return marginal_risk, component_risk, etc.
# ---------------------------------------------------------------------------

class TestDecomposeRisk:
    def test_returns_frontend_expected_keys(self):
        with _patch_prices():
            result = _run_decompose_risk(BASE_ARGS)
        for key in ("marginal_risk", "component_risk", "percent_contribution", "total_volatility"):
            assert key in result, f"Missing {key}"

    def test_percent_contribution_sums_to_one(self):
        with _patch_prices():
            result = _run_decompose_risk(BASE_ARGS)
        total = sum(result["percent_contribution"].values())
        assert abs(total - 1.0) < 1e-3

    def test_total_volatility_positive(self):
        with _patch_prices():
            result = _run_decompose_risk(BASE_ARGS)
        assert result["total_volatility"] > 0


# ---------------------------------------------------------------------------
# compute_drawdown_series — must include dates, drawdown, max_drawdown, current_drawdown
# ---------------------------------------------------------------------------

class TestComputeDrawdownSeries:
    def test_returns_frontend_expected_keys(self):
        with _patch_prices():
            result = _run_compute_drawdown_series(BASE_ARGS)
        for key in ("dates", "drawdown", "max_drawdown", "current_drawdown"):
            assert key in result, f"Missing {key}"

    def test_drawdown_non_positive(self):
        with _patch_prices():
            result = _run_compute_drawdown_series(BASE_ARGS)
        assert all(v <= 1e-9 for v in result["drawdown"])

    def test_current_drawdown_matches_last_value(self):
        with _patch_prices():
            result = _run_compute_drawdown_series(BASE_ARGS)
        assert abs(result["current_drawdown"] - result["drawdown"][-1]) < 1e-9


# ---------------------------------------------------------------------------
# compare_to_benchmark
# ---------------------------------------------------------------------------

class TestCompareToBenchmark:
    def test_returns_benchmark_keys(self):
        # Build a 4-column prices DataFrame: 3 portfolio tickers + SPY as benchmark
        rng = np.random.default_rng(7)
        dates = pd.bdate_range("2000-01-01", periods=500)
        raw = 100 * np.cumprod(1 + rng.normal(0.0005, 0.015, (500, 4)), axis=0)
        bm_prices = pd.DataFrame(raw, index=dates, columns=["AAPL", "MSFT", "GOOGL", "SPY"])
        args = {**BASE_ARGS, "benchmark_ticker": "SPY"}
        with _patch_fetch_prices(bm_prices):
            result = _run_compare_to_benchmark(args)
        for key in ("portfolio_return", "benchmark_return", "alpha", "beta", "correlation",
                    "tracking_error", "information_ratio"):
            assert key in result, f"Missing {key}"


# ---------------------------------------------------------------------------
# compute_portfolio_attribution
# ---------------------------------------------------------------------------

class TestComputePortfolioAttribution:
    def test_returns_attribution_keys(self):
        args = {**BASE_ARGS, "benchmark_ticker": "MSFT"}
        with _patch_fetch_prices(PRICES):
            result = _run_portfolio_attribution(args)
        for key in ("allocation_effect", "selection_effect", "interaction_effect", "total_active_return"):
            assert key in result, f"Missing {key}"


# ---------------------------------------------------------------------------
# plot_correlation_matrix
# ---------------------------------------------------------------------------

class TestPlotCorrelationMatrix:
    def test_returns_tickers_and_matrix(self):
        with _patch_prices():
            result = _run_plot_correlation_matrix(BASE_ARGS)
        assert "tickers" in result
        assert "matrix" in result
        n = len(result["tickers"])
        assert len(result["matrix"]) == n

    def test_diagonal_is_one(self):
        with _patch_prices():
            result = _run_plot_correlation_matrix(BASE_ARGS)
        for i in range(len(result["tickers"])):
            assert abs(result["matrix"][i][i] - 1.0) < 1e-3


# ---------------------------------------------------------------------------
# plot_efficient_frontier_with_assets
# ---------------------------------------------------------------------------

class TestPlotEfficientFrontierWithAssets:
    def test_returns_frontier_and_assets(self):
        with _patch_prices():
            result = _run_plot_frontier_with_assets(BASE_ARGS)
        assert "frontier" in result
        assert "assets" in result
        assert "max_sharpe_idx" in result
        assert len(result["frontier"]) > 0
        asset = result["assets"][0]
        assert "ticker" in asset and "volatility" in asset and "expected_return" in asset


# ---------------------------------------------------------------------------
# compute_factor_exposure — must return exposures, r_squared, residual_return
# ---------------------------------------------------------------------------

class TestComputeFactorExposure:
    def test_returns_frontend_expected_keys(self):
        with _patch_prices():
            result = _run_compute_factor_exposure(BASE_ARGS)
        for key in ("exposures", "r_squared", "residual_return", "tickers"):
            assert key in result, f"Missing {key}"


# ---------------------------------------------------------------------------
# estimate_expected_returns
# ---------------------------------------------------------------------------

class TestEstimateExpectedReturns:
    def test_returns_expected_returns_dict(self):
        with _patch_prices():
            result = _run_estimate_expected_returns(BASE_ARGS)
        assert "expected_returns" in result
        assert all(t in result["expected_returns"] for t in TICKERS)


# ---------------------------------------------------------------------------
# run_stress_test — must return {scenarios: [{name, portfolio_return}]}
# ---------------------------------------------------------------------------

class TestRunStressTest:
    def test_returns_scenarios_list(self):
        args = {"tickers": TICKERS, "weights": WEIGHTS}
        with patch("api.agent.tools.fetch_prices", return_value=LONG_PRICES), \
             patch("api.agent.tools.run_stress_test") as mock_st:
            mock_st.return_value = {
                "results": [
                    {"scenario": "gfc_2008", "available": True, "portfolio_return": -0.45},
                    {"scenario": "covid_2020", "available": True, "portfolio_return": -0.33},
                ],
                "scenarios_evaluated": 2,
                "unknown_scenarios": [],
            }
            result = _run_stress_test(args)
        assert "scenarios" in result
        assert isinstance(result["scenarios"], list)
        for s in result["scenarios"]:
            assert "name" in s and "portfolio_return" in s


# ---------------------------------------------------------------------------
# generate_scenario_return_table — must return {tickers, scenarios, returns}
# ---------------------------------------------------------------------------

class TestGenerateScenarioReturnTable:
    def test_returns_frontend_expected_keys(self):
        args = {"tickers": TICKERS}
        with patch("api.agent.tools.fetch_prices", return_value=LONG_PRICES), \
             patch("api.agent.tools.generate_scenario_return_table") as mock_gst:
            mock_gst.return_value = {
                "scenarios": ["gfc_2008", "covid_2020"],
                "portfolios": TICKERS,
                "returns_matrix": [[-0.4, -0.35, -0.5], [-0.3, -0.25, -0.4]],
                "unknown_scenarios": [],
            }
            result = _run_scenario_return_table(args)
        assert "tickers" in result
        assert "scenarios" in result
        assert "returns" in result
        # returns should be nested: {ticker: {scenario: value}}
        for ticker in result["tickers"]:
            assert ticker in result["returns"]
            for scenario in result["scenarios"]:
                assert scenario in result["returns"][ticker]


# ---------------------------------------------------------------------------
# compute_rolling_metrics
# ---------------------------------------------------------------------------

class TestComputeRollingMetrics:
    def test_returns_rolling_keys(self):
        with _patch_prices():
            result = _run_compute_rolling_metrics(BASE_ARGS)
        for key in ("dates", "rolling_sharpe", "rolling_volatility", "rolling_drawdown"):
            assert key in result, f"Missing {key}"
        assert len(result["dates"]) == len(result["rolling_sharpe"])


# ---------------------------------------------------------------------------
# run_rebalancing_analysis — must return equity curve format
# ---------------------------------------------------------------------------

class TestRunRebalancingAnalysis:
    def test_returns_equity_curve_format(self):
        with _patch_prices():
            result = _run_rebalancing_analysis(BASE_ARGS)
        for key in ("dates", "equity_curve", "total_return", "rebalance_count"):
            assert key in result, f"Missing {key}"
        assert len(result["dates"]) == len(result["equity_curve"])
        assert len(result["equity_curve"]) > 0


# ---------------------------------------------------------------------------
# optimize_with_constraints
# ---------------------------------------------------------------------------

class TestOptimizeWithConstraints:
    def test_returns_weights_and_stats(self):
        with _patch_prices():
            result = _run_optimize_with_constraints(BASE_ARGS)
        for key in ("weights", "expected_return", "expected_volatility", "sharpe"):
            assert key in result, f"Missing {key}"
        assert abs(sum(result["weights"].values()) - 1.0) < 1e-3


# ---------------------------------------------------------------------------
# rank_assets_by_metric
# ---------------------------------------------------------------------------

class TestRankAssetsByMetric:
    def test_returns_rankings_with_rank_field(self):
        with _patch_prices():
            result = _run_rank_assets_by_metric(BASE_ARGS)
        assert "rankings" in result
        assert "metric" in result
        for item in result["rankings"]:
            assert "ticker" in item and "value" in item and "rank" in item


# ---------------------------------------------------------------------------
# compute_liquidity_score — must return {scores, avg_volume, bid_ask_spread_est}
# ---------------------------------------------------------------------------

class TestComputeLiquidityScore:
    def test_returns_frontend_expected_keys(self):
        with _patch_prices():
            result = _run_compute_liquidity_score(BASE_ARGS)
        for key in ("scores", "avg_volume", "bid_ask_spread_est"):
            assert key in result, f"Missing {key}"
        assert all(t in result["scores"] for t in TICKERS)


# ---------------------------------------------------------------------------
# apply_black_litterman — must return {weights, posterior_returns, expected_return, etc.}
# ---------------------------------------------------------------------------

class TestApplyBlackLitterman:
    def test_returns_frontend_expected_keys(self):
        args = {
            **BASE_ARGS,
            "views": ["AAPL > MSFT by 0.02"],
            "view_confidences": ["0.8"],
        }
        with _patch_prices():
            result = _run_apply_black_litterman(args)
        for key in ("weights", "posterior_returns", "expected_return", "expected_volatility", "sharpe"):
            assert key in result, f"Missing {key}"

    def test_no_views_returns_equilibrium(self):
        args = {**BASE_ARGS, "views": []}
        with _patch_prices():
            result = _run_apply_black_litterman(args)
        assert "weights" in result
        assert abs(sum(result["weights"].values()) - 1.0) < 1e-3


# ---------------------------------------------------------------------------
# run_monte_carlo — must return {dates, p5, p25, p50, p75, p95, ...}
# ---------------------------------------------------------------------------

class TestRunMonteCarlo:
    def test_returns_frontend_expected_keys(self):
        args = {**BASE_ARGS, "horizon_days": 63, "n_simulations": 100}
        with _patch_prices():
            result = _run_monte_carlo(args)
        for key in ("dates", "p5", "p25", "p50", "p75", "p95", "initial_value", "n_simulations"):
            assert key in result, f"Missing {key}"

    def test_dates_length_matches_horizon(self):
        args = {**BASE_ARGS, "horizon_days": 63, "n_simulations": 50}
        with _patch_prices():
            result = _run_monte_carlo(args)
        assert len(result["dates"]) == 63
        assert len(result["p50"]) == 63

    def test_p95_ge_p5(self):
        args = {**BASE_ARGS, "horizon_days": 63, "n_simulations": 100}
        with _patch_prices():
            result = _run_monte_carlo(args)
        assert all(h >= l - 1e-6 for h, l in zip(result["p95"], result["p5"]))


# ---------------------------------------------------------------------------
# generate_tearsheet — must return flat structure with equity_curve + rolling_metrics
# ---------------------------------------------------------------------------

class TestGenerateTearsheet:
    def test_returns_frontend_expected_keys(self):
        with _patch_prices():
            result = _run_generate_tearsheet(BASE_ARGS)
        for key in ("total_return", "cagr", "sharpe", "max_drawdown", "volatility",
                    "var_95", "cvar_95", "current_drawdown", "equity_curve", "rolling_metrics"):
            assert key in result, f"Missing {key}"

    def test_equity_curve_has_date_and_value(self):
        with _patch_prices():
            result = _run_generate_tearsheet(BASE_ARGS)
        assert len(result["equity_curve"]) > 0
        assert "date" in result["equity_curve"][0]
        assert "value" in result["equity_curve"][0]

    def test_rolling_metrics_has_expected_keys(self):
        with _patch_prices():
            result = _run_generate_tearsheet(BASE_ARGS)
        rm = result["rolling_metrics"]
        for key in ("dates", "rolling_sharpe", "rolling_volatility", "rolling_drawdown"):
            assert key in rm, f"Missing rolling_metrics.{key}"
