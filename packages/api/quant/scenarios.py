"""Historical scenario stress testing and scenario return tables."""

from typing import Literal
import numpy as np
import pandas as pd

__all__ = ["run_stress_test", "generate_scenario_return_table"]

_SCENARIO_WINDOWS: dict[str, tuple[str, str]] = {
    "gfc_2008":           ("2008-09-01", "2009-03-31"),
    "covid_2020":         ("2020-02-19", "2020-03-23"),
    "rate_shock_2022":    ("2022-01-03", "2022-10-13"),
    "dot_com_2000":       ("2000-03-24", "2002-10-09"),
    "taper_tantrum_2013": ("2013-05-22", "2013-09-05"),
}


def _portfolio_equity_curve(
    prices: pd.DataFrame,
    weights: dict[str, float],
) -> pd.Series:
    tickers = list(weights.keys())
    w = np.array([weights[t] for t in tickers])
    rets = prices[tickers].pct_change().dropna()
    port_rets = rets.values @ w
    return pd.Series(np.cumprod(1 + port_rets), index=rets.index)


def run_stress_test(
    prices: pd.DataFrame,
    weights: dict[str, float],
    scenarios: list[str] | None = None,
) -> dict:
    """Reprice a portfolio under named historical stress scenarios.

    Args:
        prices: Adjusted close prices — should span the desired scenario periods.
        weights: Portfolio weights dict.
        scenarios: List of scenario names to evaluate. None = all available.
                   Valid values: gfc_2008, covid_2020, rate_shock_2022,
                   dot_com_2000, taper_tantrum_2013.

    Returns:
        dict with per-scenario results: portfolio_return, max_drawdown,
        worst_day_return, recovery_days.
    """
    if scenarios is None:
        scenarios = list(_SCENARIO_WINDOWS.keys())

    tickers = list(weights.keys())
    w = np.array([weights[t] for t in tickers])
    rets_full = prices[tickers].pct_change().dropna()

    unknown_scenarios = [name for name in scenarios if name not in _SCENARIO_WINDOWS]

    results = []
    for name in scenarios:
        if name not in _SCENARIO_WINDOWS:
            continue
        start_str, end_str = _SCENARIO_WINDOWS[name]
        start = pd.Timestamp(start_str)
        end = pd.Timestamp(end_str)

        window_rets = rets_full.loc[start:end]
        if len(window_rets) < 2:
            results.append({
                "scenario": name,
                "start": start_str,
                "end": end_str,
                "available": False,
                "note": "Price data does not cover this scenario window.",
            })
            continue

        port_rets = window_rets.values @ w
        equity = np.cumprod(1 + port_rets)
        cum_max = np.maximum.accumulate(equity)
        dd = (equity - cum_max) / cum_max

        portfolio_return = float(equity[-1] - 1)
        max_drawdown = float(dd.min())
        worst_day = float(port_rets.min())

        # Recovery: days after scenario end where equity >= pre-scenario level
        recovery_days = None
        post_window = rets_full.loc[end:]
        if len(post_window) > 0:
            pre_level = 1.0  # normalized to 1.0 at scenario start
            final_level = float(equity[-1])
            if final_level < pre_level:
                post_rets = post_window.values @ w
                running = final_level
                for i, r in enumerate(post_rets):
                    running *= (1 + r)
                    if running >= pre_level:
                        recovery_days = i + 1
                        break

        results.append({
            "scenario": name,
            "start": start_str,
            "end": end_str,
            "available": True,
            "portfolio_return": round(portfolio_return, 6),
            "max_drawdown": round(max_drawdown, 6),
            "worst_day_return": round(worst_day, 6),
            "recovery_days": recovery_days,
            "trading_days_in_window": len(window_rets),
        })

    return {
        "results": results,
        "scenarios_evaluated": len(results),
        "unknown_scenarios": unknown_scenarios,  # empty list if all known
    }


def generate_scenario_return_table(
    prices: pd.DataFrame,
    portfolio_configs: list[dict],
    scenarios: list[str] | None = None,
) -> dict:
    """Generate a matrix of portfolio returns across multiple scenarios.

    Args:
        prices: Adjusted close prices covering scenario windows.
        portfolio_configs: List of {"name": str, "weights": dict[str, float]}.
        scenarios: Subset of scenarios to evaluate. None = all.

    Returns:
        dict with scenarios list, portfolios list, and returns_matrix (scenarios x portfolios).
    """
    if scenarios is None:
        scenarios = list(_SCENARIO_WINDOWS.keys())

    unknown = [s for s in scenarios if s not in _SCENARIO_WINDOWS]

    portfolio_names = [c["name"] for c in portfolio_configs]
    matrix: list[list[float | None]] = []

    for scenario_name in scenarios:
        row: list[float | None] = []
        for config in portfolio_configs:
            result = run_stress_test(prices, config["weights"], scenarios=[scenario_name])
            r = result["results"]
            if r and r[0].get("available"):
                row.append(round(r[0]["portfolio_return"], 4))
            else:
                row.append(None)
        matrix.append(row)

    return {
        "scenarios": scenarios,
        "portfolios": portfolio_names,
        "returns_matrix": matrix,
        "unknown_scenarios": unknown,
    }
