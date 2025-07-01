"""Tests for the 8 extended quant modules."""

import numpy as np
import pandas as pd
import pytest

from quant.risk import (
    compute_var_cvar,
    compute_tail_risk_metrics,
    decompose_risk,
    compute_drawdown_series,
)
from quant.attribution import compare_to_benchmark, compute_portfolio_attribution
from quant.plots import plot_correlation_matrix, plot_efficient_frontier_with_assets
from quant.factors import estimate_expected_returns
from quant.scenarios import run_stress_test, generate_scenario_return_table
from quant.rolling import compute_rolling_metrics, run_rebalancing_analysis
from quant.constraints import optimize_with_constraints
from quant.analytics import (
    rank_assets_by_metric,
    compute_liquidity_score,
    apply_black_litterman,
    run_monte_carlo,
    generate_tearsheet,
)


def _make_prices(n_days: int = 252, n_assets: int = 3, seed: int = 42) -> pd.DataFrame:
    """Same helper as test_quant.py — synthetic prices, no network."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2023-01-01", periods=n_days)
    returns = rng.normal(0.0005, 0.02, (n_days, n_assets))
    prices = 100 * np.cumprod(1 + returns, axis=0)
    tickers = [f"ASSET{i}" for i in range(n_assets)]
    return pd.DataFrame(prices, index=dates, columns=tickers)


# ---------------------------------------------------------------------------
# risk.py
# ---------------------------------------------------------------------------

class TestVaRCVaR:
    def _weights(self):
        return {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}

    def test_historical_var_cvar_signs(self):
        prices = _make_prices()
        result = compute_var_cvar(prices, self._weights(), method="historical")
        assert result["var"] >= 0
        assert result["cvar"] >= result["var"]
        assert not np.isnan(result["cvar"])

    def test_parametric_var_cvar_signs(self):
        prices = _make_prices()
        result = compute_var_cvar(prices, self._weights(), method="parametric")
        assert result["var"] >= 0
        assert result["cvar"] >= result["var"]
        assert not np.isnan(result["cvar"])

    def test_monte_carlo_var_cvar_signs(self):
        prices = _make_prices()
        result = compute_var_cvar(prices, self._weights(), method="monte_carlo")
        assert result["var"] >= 0
        assert result["cvar"] >= result["var"]
        assert not np.isnan(result["cvar"])

    def test_cvar_not_nan_at_low_confidence(self):
        prices = _make_prices()
        result = compute_var_cvar(prices, self._weights(), confidence_level=0.5, method="historical")
        assert not np.isnan(result["cvar"])

    def test_annualized_var_approx(self):
        prices = _make_prices()
        result = compute_var_cvar(prices, self._weights(), method="historical")
        expected_ann = result["var"] * np.sqrt(252)
        assert abs(result["annualized_var"] - expected_ann) < 1e-4


class TestTailRiskMetrics:
    def _weights(self):
        return {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}

    def test_all_keys_present(self):
        prices = _make_prices()
        result = compute_tail_risk_metrics(prices, self._weights())
        for key in ("sortino", "calmar", "omega", "skewness", "kurtosis"):
            assert key in result

    def test_omega_positive(self):
        prices = _make_prices()
        result = compute_tail_risk_metrics(prices, self._weights())
        assert result["omega"] > 0

    def test_deterministic(self):
        prices = _make_prices()
        r1 = compute_tail_risk_metrics(prices, self._weights())
        r2 = compute_tail_risk_metrics(prices, self._weights())
        assert r1["sortino"] == r2["sortino"]
        assert r1["omega"] == r2["omega"]


class TestDecomposeRisk:
    def _weights(self):
        return {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}

    def test_percent_contributions_sum_to_one(self):
        prices = _make_prices()
        result = decompose_risk(prices, self._weights())
        total = sum(result["percent_contribution"].values())
        assert abs(total - 1.0) < 1e-4

    def test_all_tickers_present(self):
        prices = _make_prices()
        result = decompose_risk(prices, self._weights())
        for key in ("ASSET0", "ASSET1", "ASSET2"):
            assert key in result["component_risk"]
            assert key in result["percent_contribution"]

    def test_portfolio_volatility_positive(self):
        prices = _make_prices()
        result = decompose_risk(prices, self._weights())
        assert result["total_volatility"] > 0


class TestDrawdownSeries:
    def _weights(self):
        return {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}

    def test_max_drawdown_non_positive(self):
        prices = _make_prices()
        result = compute_drawdown_series(prices, self._weights())
        assert result["max_drawdown"] <= 0

    def test_lengths_match(self):
        prices = _make_prices()
        result = compute_drawdown_series(prices, self._weights())
        assert len(result["dates"]) == len(result["drawdown"])

    def test_avg_drawdown_non_positive(self):
        prices = _make_prices()
        result = compute_drawdown_series(prices, self._weights())
        assert result["avg_drawdown"] <= 0

    def test_max_drawdown_duration_non_negative(self):
        prices = _make_prices()
        result = compute_drawdown_series(prices, self._weights())
        assert result["max_drawdown_duration_days"] >= 0


# ---------------------------------------------------------------------------
# attribution.py
# ---------------------------------------------------------------------------

def _make_benchmark(prices: pd.DataFrame, source_col: str = "ASSET0") -> pd.DataFrame:
    """Return a benchmark DataFrame with a non-overlapping column name."""
    bm = prices[[source_col]].copy()
    bm.columns = ["BENCH"]
    return bm


class TestCompareToBenchmark:
    def _weights(self):
        return {"ASSET0": 1 / 3, "ASSET1": 1 / 3, "ASSET2": 1 / 3}

    def test_all_keys_present(self):
        prices = _make_prices()
        bm = _make_benchmark(prices)
        result = compare_to_benchmark(prices, self._weights(), benchmark_prices=bm)
        for key in ("excess_return", "tracking_error", "information_ratio", "beta", "alpha"):
            assert key in result

    def test_tracking_error_non_negative(self):
        prices = _make_prices()
        bm = _make_benchmark(prices)
        result = compare_to_benchmark(prices, self._weights(), benchmark_prices=bm)
        assert result["tracking_error"] >= 0

    def test_identical_portfolio_and_benchmark(self):
        """When portfolio and benchmark are the same series, excess_return ~ 0 and beta ~ 1."""
        prices = _make_prices()
        # Single-asset portfolio; benchmark is the same series under a different column name
        single_prices = prices[["ASSET0"]]
        single_weights = {"ASSET0": 1.0}
        bm = prices[["ASSET0"]].rename(columns={"ASSET0": "BENCH"})
        result = compare_to_benchmark(single_prices, single_weights, benchmark_prices=bm)
        assert abs(result["excess_return"]) < 1e-4
        assert abs(result["beta"] - 1.0) < 1e-3


class TestPortfolioAttribution:
    def test_all_tickers_in_assets(self):
        prices = _make_prices()
        port_w = {"ASSET0": 0.5, "ASSET1": 0.3, "ASSET2": 0.2}
        bm_w = {"ASSET0": 1 / 3, "ASSET1": 1 / 3, "ASSET2": 1 / 3}
        result = compute_portfolio_attribution(prices, port_w, bm_w)
        for t in ("ASSET0", "ASSET1", "ASSET2"):
            assert t in result["assets"]

    def test_effect_sum_approx_active_return(self):
        """Sum of per-asset (allocation + selection + interaction) ~ total_active_return."""
        prices = _make_prices()
        port_w = {"ASSET0": 0.5, "ASSET1": 0.3, "ASSET2": 0.2}
        bm_w = {"ASSET0": 1 / 3, "ASSET1": 1 / 3, "ASSET2": 1 / 3}
        result = compute_portfolio_attribution(prices, port_w, bm_w)
        total_effects = sum(
            result["allocation_effect"][t]
            + result["selection_effect"][t]
            + result["interaction_effect"][t]
            for t in result["assets"]
        )
        assert abs(total_effects - result["total_active_return"]) < 1e-4

    def test_returns_are_finite(self):
        prices = _make_prices()
        port_w = {"ASSET0": 0.5, "ASSET1": 0.3, "ASSET2": 0.2}
        bm_w = {"ASSET0": 1 / 3, "ASSET1": 1 / 3, "ASSET2": 1 / 3}
        result = compute_portfolio_attribution(prices, port_w, bm_w)
        assert np.isfinite(result["portfolio_return"])
        assert np.isfinite(result["benchmark_return"])


# ---------------------------------------------------------------------------
# plots.py
# ---------------------------------------------------------------------------

class TestPlotCorrelationMatrix:
    def test_matrix_is_n_by_n(self):
        prices = _make_prices()
        result = plot_correlation_matrix(prices)
        n = len(prices.columns)
        assert len(result["matrix"]) == n
        assert all(len(row) == n for row in result["matrix"])

    def test_diagonal_approx_one(self):
        prices = _make_prices()
        result = plot_correlation_matrix(prices)
        for i, row in enumerate(result["matrix"]):
            assert abs(row[i] - 1.0) < 1e-3

    def test_cluster_false_preserves_order(self):
        prices = _make_prices()
        result = plot_correlation_matrix(prices, cluster=False)
        assert result["tickers"] == list(prices.columns)


class TestPlotFrontierWithAssets:
    def test_one_asset_entry_per_ticker(self):
        prices = _make_prices()
        result = plot_efficient_frontier_with_assets(prices)
        assert len(result["assets"]) == len(prices.columns)

    def test_asset_volatility_positive(self):
        prices = _make_prices()
        result = plot_efficient_frontier_with_assets(prices)
        for asset in result["assets"]:
            assert asset["volatility"] > 0
            assert "expected_return" in asset

    def test_frontier_non_empty(self):
        prices = _make_prices()
        result = plot_efficient_frontier_with_assets(prices)
        assert len(result["frontier"]) > 0


# ---------------------------------------------------------------------------
# factors.py
# ---------------------------------------------------------------------------

class TestEstimateExpectedReturns:
    def test_historical_all_tickers_finite(self):
        prices = _make_prices()
        result = estimate_expected_returns(prices, method="historical")
        for t in prices.columns:
            assert t in result["expected_returns"]
            assert np.isfinite(result["expected_returns"][t])

    def test_capm_all_tickers(self):
        prices = _make_prices()
        result = estimate_expected_returns(prices, method="capm")
        assert set(result["expected_returns"].keys()) == set(prices.columns)

    def test_shrinkage_pulled_toward_grand_mean(self):
        prices = _make_prices()
        hist_result = estimate_expected_returns(prices, method="historical")
        shrink_result = estimate_expected_returns(prices, method="shrinkage")

        hist_vals = hist_result["expected_returns"]
        shrink_vals = shrink_result["expected_returns"]
        grand_mean = np.mean(list(hist_vals.values()))

        for t in prices.columns:
            hist_val = hist_vals[t]
            shrink_val = shrink_vals[t]
            # After shrinkage the value must be no further from grand_mean than hist_val
            assert abs(shrink_val - grand_mean) <= abs(hist_val - grand_mean) + 1e-6


# ---------------------------------------------------------------------------
# scenarios.py
# ---------------------------------------------------------------------------

class TestRunStressTest:
    def test_unavailable_when_prices_dont_cover_window(self):
        """Synthetic 2023 prices won't cover any scenario window — all unavailable."""
        prices = _make_prices()
        weights = {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}
        result = run_stress_test(prices, weights, scenarios=["gfc_2008"])
        assert len(result["results"]) == 1
        assert result["results"][0]["available"] is False

    def test_no_crash_when_prices_dont_cover_window(self):
        prices = _make_prices()
        weights = {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}
        # Should not raise even when none of the scenarios are covered
        result = run_stress_test(prices, weights)
        assert isinstance(result, dict)

    def test_unknown_scenarios_empty_when_all_valid(self):
        prices = _make_prices()
        weights = {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}
        result = run_stress_test(prices, weights, scenarios=["gfc_2008", "covid_2020"])
        assert result["unknown_scenarios"] == []

    def test_unknown_scenarios_captured(self):
        prices = _make_prices()
        weights = {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}
        result = run_stress_test(prices, weights, scenarios=["gfc_2008", "not_a_scenario"])
        assert "not_a_scenario" in result["unknown_scenarios"]

    def test_scenarios_evaluated_count(self):
        prices = _make_prices()
        weights = {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}
        result = run_stress_test(prices, weights, scenarios=["gfc_2008", "covid_2020"])
        # Both will be unavailable but both should be listed in results
        assert result["scenarios_evaluated"] == 2


# ---------------------------------------------------------------------------
# rolling.py
# ---------------------------------------------------------------------------

class TestComputeRollingMetrics:
    def _weights(self):
        return {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}

    def test_lengths_match(self):
        prices = _make_prices()
        result = compute_rolling_metrics(prices, self._weights(), window=21)
        n = len(result["dates"])
        assert n == len(result["rolling_sharpe"])
        assert n == len(result["rolling_volatility"])
        assert n == len(result["rolling_drawdown"])

    def test_first_window_minus_one_values_are_zero(self):
        prices = _make_prices()
        window = 21
        result = compute_rolling_metrics(prices, self._weights(), window=window)
        # Before the window fills, rolling std is NaN -> filled with 0
        for v in result["rolling_sharpe"][: window - 1]:
            assert v == 0.0
        for v in result["rolling_volatility"][: window - 1]:
            assert v == 0.0

    def test_no_benchmark_gives_none_beta_corr(self):
        prices = _make_prices()
        result = compute_rolling_metrics(prices, self._weights())
        assert result["rolling_beta"] is None
        assert result["rolling_correlation"] is None

    def test_with_benchmark_gives_lists(self):
        prices = _make_prices()
        bm = prices[["ASSET0"]].copy()
        result = compute_rolling_metrics(prices, self._weights(), benchmark_prices=bm, window=21)
        assert result["rolling_beta"] is not None
        assert result["rolling_correlation"] is not None


class TestRunRebalancingAnalysis:
    def _weights(self):
        return {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}

    def test_results_contain_requested_frequencies(self):
        prices = _make_prices(n_days=126)
        result = run_rebalancing_analysis(
            prices, self._weights(), frequencies=["weekly", "monthly"]
        )
        freqs = [r["frequency"] for r in result["results"]]
        assert "weekly" in freqs
        assert "monthly" in freqs

    def test_cost_adjusted_cagr_le_cagr(self):
        prices = _make_prices(n_days=126)
        result = run_rebalancing_analysis(
            prices, self._weights(), frequencies=["weekly", "monthly"]
        )
        for r in result["results"]:
            assert r["cost_adjusted_cagr"] <= r["cagr"] + 1e-9

    def test_n_rebalances_non_negative(self):
        prices = _make_prices(n_days=126)
        result = run_rebalancing_analysis(
            prices, self._weights(), frequencies=["monthly", "threshold"]
        )
        for r in result["results"]:
            assert r["n_rebalances"] >= 0


# ---------------------------------------------------------------------------
# constraints.py
# ---------------------------------------------------------------------------

class TestOptimizeWithConstraints:
    def _prices(self):
        return _make_prices()

    def test_weights_sum_to_one(self):
        result = optimize_with_constraints(self._prices(), objective="min_variance")
        assert abs(sum(result["weights"].values()) - 1.0) < 1e-4

    def test_weights_within_default_bounds(self):
        result = optimize_with_constraints(self._prices(), min_weight=0.0, max_weight=1.0)
        for w in result["weights"].values():
            assert -1e-5 <= w <= 1.0 + 1e-5

    def test_max_weight_constraint_respected(self):
        result = optimize_with_constraints(self._prices(), max_weight=0.5)
        for w in result["weights"].values():
            assert w <= 0.5 + 1e-4

    def test_sector_cap_respected(self):
        prices = _make_prices(n_assets=4)
        # ASSET0 and ASSET1 are in "tech", capped at 0.5
        sector_map = {"ASSET0": "tech", "ASSET1": "tech", "ASSET2": "other", "ASSET3": "other"}
        sector_caps = {"tech": 0.5}
        result = optimize_with_constraints(
            prices,
            objective="min_variance",
            sector_map=sector_map,
            sector_caps=sector_caps,
        )
        tech_total = result["weights"]["ASSET0"] + result["weights"]["ASSET1"]
        assert tech_total <= 0.5 + 1e-4


# ---------------------------------------------------------------------------
# analytics.py
# ---------------------------------------------------------------------------

class TestRankAssets:
    def test_one_entry_per_ticker(self):
        prices = _make_prices()
        result = rank_assets_by_metric(prices, metric="sharpe")
        assert len(result["rankings"]) == len(prices.columns)

    def test_rank_values_no_gaps(self):
        prices = _make_prices()
        result = rank_assets_by_metric(prices, metric="return")
        ranks = sorted(r["rank"] for r in result["rankings"])
        n = len(ranks)
        assert ranks == list(range(1, n + 1))

    def test_ascending_volatility_first_entry_lowest(self):
        prices = _make_prices()
        result = rank_assets_by_metric(prices, metric="volatility", ascending=True)
        first_val = result["rankings"][0]["value"]
        for entry in result["rankings"]:
            assert first_val <= entry["value"] + 1e-9


class TestComputeLiquidityScore:
    def _weights(self):
        return {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}

    def test_all_tickers_present(self):
        prices = _make_prices()
        result = compute_liquidity_score(prices, self._weights())
        asset_tickers = {a["ticker"] for a in result["assets"]}
        assert "ASSET0" in asset_tickers
        assert "ASSET1" in asset_tickers
        assert "ASSET2" in asset_tickers

    def test_aggregate_score_positive(self):
        prices = _make_prices()
        result = compute_liquidity_score(prices, self._weights())
        assert result["aggregate_liquidity_score"] > 0

    def test_liquidity_category_valid(self):
        prices = _make_prices()
        result = compute_liquidity_score(prices, self._weights())
        valid_categories = {"high", "medium", "low"}
        for asset in result["assets"]:
            assert asset["liquidity_category"] in valid_categories


class TestApplyBlackLitterman:
    def _prices(self):
        return _make_prices()

    def test_bl_weights_sum_to_one(self):
        prices = self._prices()
        views = [{"tickers": ["ASSET0"], "expected_return": 0.12, "confidence": 0.8}]
        result = apply_black_litterman(prices, views=views)
        assert abs(sum(result["bl_weights"].values()) - 1.0) < 1e-4

    def test_no_views_bl_equals_prior(self):
        prices = self._prices()
        result = apply_black_litterman(prices, views=[])
        for t in prices.columns:
            assert abs(result["bl_expected_returns"][t] - result["prior_returns"][t]) < 1e-6

    def test_view_raises_asset_return(self):
        prices = self._prices()
        prior_result = apply_black_litterman(prices, views=[])
        prior_return_a0 = prior_result["prior_returns"]["ASSET0"]

        # Apply a high positive view on ASSET0
        views = [{"tickers": ["ASSET0"], "expected_return": prior_return_a0 + 0.20, "confidence": 0.9}]
        result = apply_black_litterman(prices, views=views)
        assert result["bl_expected_returns"]["ASSET0"] > prior_return_a0


class TestRunMonteCarlo:
    def _weights(self):
        return {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}

    def test_fan_chart_keys_present(self):
        prices = _make_prices()
        result = run_monte_carlo(prices, self._weights(), n_simulations=100, seed=0)
        for key in ("p5", "p25", "p50", "p75", "p95"):
            assert key in result["fan_chart"]

    def test_fan_chart_series_length(self):
        prices = _make_prices()
        n_days = 63
        result = run_monte_carlo(prices, self._weights(), n_simulations=100, n_days=n_days, seed=0)
        for key in result["fan_chart"]:
            assert len(result["fan_chart"][key]) == n_days

    def test_prob_profit_in_range(self):
        prices = _make_prices()
        result = run_monte_carlo(prices, self._weights(), n_simulations=200, seed=7)
        assert 0.0 <= result["terminal"]["prob_profit"] <= 1.0

    def test_no_nan_in_percentile_series(self):
        prices = _make_prices()
        result = run_monte_carlo(prices, self._weights(), n_simulations=100, seed=1)
        for key, series in result["fan_chart"].items():
            assert not any(np.isnan(v) for v in series), f"NaN found in {key}"


class TestGenerateTearsheet:
    def _weights(self):
        return {"ASSET0": 0.4, "ASSET1": 0.3, "ASSET2": 0.3}

    def test_top_level_sections_present(self):
        prices = _make_prices()
        result = generate_tearsheet(prices, self._weights())
        for section in ("summary", "performance", "risk", "rolling", "drawdown", "benchmark"):
            assert section in result

    def test_performance_max_drawdown_non_positive(self):
        prices = _make_prices()
        result = generate_tearsheet(prices, self._weights())
        assert result["performance"]["max_drawdown"] <= 0

    def test_current_drawdown_not_none(self):
        prices = _make_prices()
        result = generate_tearsheet(prices, self._weights())
        assert result["drawdown"]["current_drawdown"] is not None

    def test_benchmark_none_without_benchmark_prices(self):
        prices = _make_prices()
        result = generate_tearsheet(prices, self._weights())
        assert result["benchmark"] is None

    def test_benchmark_populated_with_benchmark_prices(self):
        prices = _make_prices()
        bm = _make_benchmark(prices)
        result = generate_tearsheet(prices, self._weights(), benchmark_prices=bm)
        assert result["benchmark"] is not None
