"""Rolling analytics and rebalancing frequency comparison."""

import numpy as np
import pandas as pd

from quant.backtest import run_backtest

__all__ = ["compute_rolling_metrics", "run_rebalancing_analysis"]


def compute_rolling_metrics(
    prices: pd.DataFrame,
    weights: dict[str, float],
    window: int = 63,
    benchmark_prices: pd.DataFrame | None = None,
    risk_free_rate: float = 0.0,
) -> dict:
    """Compute rolling Sharpe, volatility, beta, correlation, and drawdown.

    Args:
        prices: Adjusted close prices for portfolio assets.
        weights: Portfolio weights dict.
        window: Rolling window in trading days.
        benchmark_prices: Optional benchmark price DataFrame for beta/correlation.
        risk_free_rate: Annual risk-free rate.

    Returns:
        dict with dates and rolling series for each metric.
    """
    tickers = list(weights.keys())
    w = np.array([weights[t] for t in tickers])
    rets = prices[tickers].pct_change().dropna()
    port_rets = pd.Series(rets.values @ w, index=rets.index)

    daily_rf = risk_free_rate / 252

    # Rolling Sharpe
    roll_mean = port_rets.rolling(window).mean() - daily_rf
    roll_std = port_rets.rolling(window).std()
    rolling_sharpe = (roll_mean / roll_std * np.sqrt(252)).fillna(0)

    # Rolling volatility (annualized)
    rolling_vol = (roll_std * np.sqrt(252)).fillna(0)

    # Rolling drawdown
    equity = (1 + port_rets).cumprod()
    roll_max = equity.rolling(window, min_periods=1).max()
    rolling_dd = ((equity - roll_max) / roll_max).fillna(0)

    # Rolling beta and correlation vs benchmark
    rolling_beta = None
    rolling_corr = None
    if benchmark_prices is not None:
        bm_col = benchmark_prices.columns[0]
        bm_rets = benchmark_prices[bm_col].pct_change().reindex(port_rets.index).dropna()
        aligned_port = port_rets.reindex(bm_rets.index)

        roll_cov = aligned_port.rolling(window).cov(bm_rets)
        roll_bm_var = bm_rets.rolling(window).var()
        rolling_beta_series = (roll_cov / roll_bm_var.replace(0, np.nan)).fillna(0)

        roll_corr_series = aligned_port.rolling(window).corr(bm_rets).fillna(0)

        rolling_beta = [round(float(v), 4) for v in rolling_beta_series.values]
        rolling_corr = [round(float(v), 4) for v in roll_corr_series.values]

    return {
        "dates": [str(d.date()) for d in port_rets.index],
        "rolling_sharpe": [round(float(v), 4) for v in rolling_sharpe.values],
        "rolling_volatility": [round(float(v), 6) for v in rolling_vol.values],
        "rolling_drawdown": [round(float(v), 6) for v in rolling_dd.values],
        "rolling_beta": rolling_beta,
        "rolling_correlation": rolling_corr,
        "window": window,
    }


def run_rebalancing_analysis(
    prices: pd.DataFrame,
    weights: dict[str, float],
    frequencies: list[str] | None = None,
    transaction_cost_bps: float = 10.0,
    threshold: float = 0.05,
    initial_capital: float = 100_000.0,
) -> dict:
    """Compare portfolio performance across different rebalancing frequencies.

    Args:
        prices: Adjusted close prices.
        weights: Target portfolio weights.
        frequencies: Subset of ["daily","weekly","monthly","quarterly","threshold"].
                     None = all five.
        transaction_cost_bps: Round-trip transaction cost in basis points per rebalance.
        threshold: Drift threshold for threshold-based rebalancing.
        initial_capital: Starting capital.

    Note: Transaction costs are estimated as a post-hoc CAGR deduction, not applied
          to the equity curve directly.

    Returns:
        dict with performance comparison across frequencies.
    """
    if frequencies is None:
        frequencies = ["daily", "weekly", "monthly", "quarterly", "threshold"]

    results = []
    tickers = list(weights.keys())
    w_target = np.array([weights[t] for t in tickers])
    prices_subset = prices[tickers].dropna()
    rets = prices_subset.pct_change().dropna()

    for freq in frequencies:
        if freq in ("daily", "weekly", "monthly"):
            backtest_result = run_backtest(
                prices_subset,
                weights,
                initial_capital=initial_capital,
                rebalance_freq=freq,
            )
            m = backtest_result.metrics

            # Estimate number of rebalances
            n_days = len(rets)
            n_rebalances = {
                "daily": n_days,
                "weekly": n_days // 5,
                "monthly": n_days // 21,
            }[freq]

        elif freq == "quarterly":
            # Simulate quarterly rebalancing manually
            equity_val = initial_capital
            current_w = w_target.copy()
            equity_series = []
            quarter = None
            n_rebalances = 0

            for i, (date, ret) in enumerate(rets.iterrows()):
                daily_ret = ret.values
                weighted_ret = float(np.dot(current_w, daily_ret))
                equity_val *= (1 + weighted_ret)
                current_w = current_w * (1 + daily_ret)
                if current_w.sum() > 0:
                    current_w /= current_w.sum()

                q = (date.month - 1) // 3
                if quarter is None:
                    quarter = q
                elif q != quarter:
                    current_w = w_target.copy()
                    n_rebalances += 1
                    quarter = q

                equity_series.append(equity_val)

            eq = pd.Series(equity_series)
            dr = eq.pct_change().dropna()
            n_years = len(dr) / 252
            total_ret = (eq.iloc[-1] / initial_capital) - 1
            cagr = (eq.iloc[-1] / initial_capital) ** (1 / n_years) - 1 if n_years > 0 else 0
            vol = float(dr.std() * np.sqrt(252))
            sharpe = float(dr.mean() / dr.std() * np.sqrt(252)) if dr.std() > 0 else 0
            cum_max = eq.cummax()
            max_dd = float(((eq - cum_max) / cum_max).min())
            m = type("M", (), {"cagr": cagr, "sharpe": sharpe, "max_drawdown": max_dd, "volatility": vol})()

        elif freq == "threshold":
            # Threshold-based: rebalance when any weight drifts > threshold
            equity_val = initial_capital
            current_w = w_target.copy()
            equity_series = []
            n_rebalances = 0

            for i, (date, ret) in enumerate(rets.iterrows()):
                daily_ret = ret.values
                weighted_ret = float(np.dot(current_w, daily_ret))
                equity_val *= (1 + weighted_ret)
                current_w = current_w * (1 + daily_ret)
                if current_w.sum() > 0:
                    current_w /= current_w.sum()

                max_drift = float(np.max(np.abs(current_w - w_target)))
                if max_drift > threshold:
                    current_w = w_target.copy()
                    n_rebalances += 1

                equity_series.append(equity_val)

            eq = pd.Series(equity_series)
            dr = eq.pct_change().dropna()
            n_years = len(dr) / 252
            cagr = (eq.iloc[-1] / initial_capital) ** (1 / n_years) - 1 if n_years > 0 else 0
            vol = float(dr.std() * np.sqrt(252))
            sharpe = float(dr.mean() / dr.std() * np.sqrt(252)) if dr.std() > 0 else 0
            cum_max = eq.cummax()
            max_dd = float(((eq - cum_max) / cum_max).min())
            m = type("M", (), {"cagr": cagr, "sharpe": sharpe, "max_drawdown": max_dd, "volatility": vol})()
        else:
            continue

        # Cost adjustment is a post-hoc approximation: estimated cost fraction is
        # subtracted from CAGR rather than applied per-trade to the equity curve.
        # This slightly overstates performance when turnover is concentrated early.
        cost_fraction = n_rebalances * transaction_cost_bps / 10_000 * 0.5
        cost_adj_cagr = getattr(m, "cagr", 0) - cost_fraction

        results.append({
            "frequency": freq,
            "cagr": round(float(getattr(m, "cagr", 0)), 6),
            "cost_adjusted_cagr": round(float(cost_adj_cagr), 6),
            "sharpe": round(float(getattr(m, "sharpe", 0)), 4),
            "max_drawdown": round(float(getattr(m, "max_drawdown", 0)), 6),
            "volatility": round(float(getattr(m, "volatility", 0)), 6),
            "n_rebalances": n_rebalances,
            "estimated_cost_bps": round(cost_fraction * 10_000, 2),
        })

    return {"results": results, "transaction_cost_bps": transaction_cost_bps}
