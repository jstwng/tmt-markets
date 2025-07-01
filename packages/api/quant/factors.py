"""Factor analysis: Fama-French exposure and forward-looking expected returns."""

from typing import Literal
import warnings

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from quant.covariance import estimate_covariance

__all__ = ["compute_factor_exposure", "estimate_expected_returns"]

# ETF proxies used when pandas_datareader is unavailable
_FF3_PROXIES = {
    "Mkt-RF": ("SPY", "BIL"),   # market minus risk-free (approx via T-bill ETF)
    "SMB": ("IWM", "SPY"),       # small minus big
    "HML": ("IVE", "IVW"),       # value minus growth
}

_FF5_EXTRA_PROXIES = {
    "RMW": ("USMV", "MTUM"),     # profitability proxy
    "CMA": ("VBR", "VUG"),       # investment proxy
}


def _fetch_ff_factors(
    start_date: str,
    end_date: str,
    model: Literal["ff3", "ff5"] = "ff3",
) -> pd.DataFrame | None:
    """Attempt to fetch Fama-French factors from Ken French data library.

    Falls back to ETF-proxy factors via yfinance if pandas_datareader is unavailable
    or the request fails.
    """
    try:
        import pandas_datareader.data as web
        dataset = (
            "F-F_Research_Data_Factors_daily"
            if model == "ff3"
            else "F-F_Research_Data_5_Factors_2x3_daily"
        )
        raw = web.DataReader(dataset, "famafrench", start=start_date, end=end_date)[0]
        # Convert from percent to decimal
        factors = raw / 100.0
        factors.index = pd.to_datetime(factors.index)
        return factors
    except Exception:
        return _build_proxy_factors(start_date, end_date, model)


def _build_proxy_factors(
    start_date: str,
    end_date: str,
    model: Literal["ff3", "ff5"],
) -> pd.DataFrame | None:
    """Build approximate FF factors from publicly available ETFs via yfinance."""
    try:
        import yfinance as yf
        proxies = list(_FF3_PROXIES.values())
        if model == "ff5":
            proxies += list(_FF5_EXTRA_PROXIES.values())

        tickers_needed = list({t for pair in proxies for t in pair})
        data = yf.download(tickers_needed, start=start_date, end=end_date, auto_adjust=True)
        closes = data["Close"]
        if isinstance(closes, pd.Series):
            closes = closes.to_frame()
        if hasattr(closes.columns, "droplevel") and closes.columns.nlevels > 1:
            closes.columns = closes.columns.droplevel(0)
        rets = closes.pct_change().dropna()

        factors: dict[str, pd.Series] = {}
        for name, (long_t, short_t) in _FF3_PROXIES.items():
            if long_t in rets.columns and short_t in rets.columns:
                factors[name] = rets[long_t] - rets[short_t]

        if model == "ff5":
            for name, (long_t, short_t) in _FF5_EXTRA_PROXIES.items():
                if long_t in rets.columns and short_t in rets.columns:
                    factors[name] = rets[long_t] - rets[short_t]

        if not factors:
            return None
        return pd.DataFrame(factors).dropna()
    except Exception:
        return None


def compute_factor_exposure(
    prices: pd.DataFrame,
    weights: dict[str, float],
    factors: Literal["ff3", "ff5"] = "ff3",
) -> dict:
    """Regress portfolio returns against Fama-French 3 or 5 factors.

    Args:
        prices: Adjusted close prices for portfolio assets.
        weights: Portfolio weights dict.
        factors: Factor model to use ('ff3' or 'ff5').

    Returns:
        dict with loadings, t-stats, p-values, R², alpha, factor_names.
    """
    tickers = list(weights.keys())
    w = np.array([weights[t] for t in tickers])
    returns = prices[tickers].pct_change().dropna()
    port_rets = pd.Series(returns.values @ w, index=returns.index, name="portfolio")

    start = str(returns.index[0].date())
    end = str(returns.index[-1].date())

    ff = _fetch_ff_factors(start, end, factors)

    if ff is None or ff.empty:
        return {
            "loadings": {},
            "t_stats": {},
            "p_values": {},
            "r_squared": None,
            "alpha": None,
            "factor_names": [],
            "error": "Factor data unavailable — check network or install pandas_datareader",
        }

    # Align
    aligned = port_rets.to_frame().join(ff, how="inner").dropna()
    if len(aligned) < 10:
        return {
            "loadings": {}, "t_stats": {}, "p_values": {},
            "r_squared": None, "alpha": None, "factor_names": [],
            "error": "Insufficient overlapping observations",
        }

    y = aligned["portfolio"].values
    factor_cols = [c for c in ff.columns if c != "RF"]
    X_raw = aligned[factor_cols].values

    # Excess returns (subtract RF if available)
    rf = aligned["RF"].values if "RF" in aligned.columns else np.zeros(len(y))
    y_excess = y - rf

    # Add intercept
    X = np.column_stack([np.ones(len(X_raw)), X_raw])
    result = np.linalg.lstsq(X, y_excess, rcond=None)
    coeffs = result[0]

    # Residuals and stats
    y_hat = X @ coeffs
    residuals = y_excess - y_hat
    n, k = X.shape
    df = n - k
    s2 = float(np.sum(residuals ** 2) / df) if df > 0 else 1.0
    XtX_inv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(XtX_inv) * s2)
    t_vals = coeffs / (se + 1e-12)
    p_vals = [2 * (1 - scipy_stats.t.cdf(abs(t), df)) for t in t_vals]

    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((y_excess - y_excess.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-10 else 0.0

    alpha = float(coeffs[0]) * 252  # annualized
    loadings = {f: round(float(c), 4) for f, c in zip(factor_cols, coeffs[1:])}
    t_stats = {f: round(float(t), 4) for f, t in zip(factor_cols, t_vals[1:])}
    p_values = {f: round(float(p), 4) for f, p in zip(factor_cols, p_vals[1:])}

    return {
        "loadings": loadings,
        "t_stats": t_stats,
        "p_values": p_values,
        "r_squared": round(r2, 4),
        "alpha": round(alpha, 6),
        "alpha_t_stat": round(float(t_vals[0]), 4),
        "factor_names": factor_cols,
        "n_observations": n,
    }


def estimate_expected_returns(
    prices: pd.DataFrame,
    method: Literal["historical", "capm", "shrinkage"] = "historical",
    risk_free_rate: float = 0.0,
    market_prices: pd.DataFrame | None = None,
) -> dict:
    """Estimate forward-looking expected returns.

    Args:
        prices: Adjusted close prices for assets.
        method: Estimation approach.
        risk_free_rate: Annual risk-free rate.
        market_prices: Single-column DataFrame for market portfolio (used for CAPM).

    Returns:
        dict with expected_returns per ticker and method used.
    """
    returns = prices.pct_change().dropna()
    tickers = list(prices.columns)

    if method == "historical":
        ann_returns = {t: round(float(returns[t].mean()) * 252, 6) for t in tickers}

    elif method == "capm":
        if market_prices is None:
            # Fallback: use equal-weight portfolio as market proxy
            mkt_rets = returns.mean(axis=1)
        else:
            mkt_col = market_prices.columns[0]
            mkt_rets = market_prices.join(prices, how="right")[mkt_col].pct_change()

        mkt_rets = mkt_rets.reindex(returns.index).dropna()
        aligned = returns.reindex(mkt_rets.index).dropna()
        mkt_rets = mkt_rets.reindex(aligned.index)

        mkt_ann = float(mkt_rets.mean()) * 252
        mkt_var = float(mkt_rets.var())
        betas = {
            t: float(np.cov(aligned[t].values, mkt_rets.values)[0, 1] / mkt_var)
            if mkt_var > 1e-10 else 1.0
            for t in tickers
        }
        ann_returns = {
            t: round(risk_free_rate + betas[t] * (mkt_ann - risk_free_rate), 6)
            for t in tickers
        }

    elif method == "shrinkage":
        # James-Stein shrinkage toward grand mean
        hist = {t: float(returns[t].mean()) * 252 for t in tickers}
        grand_mean = np.mean(list(hist.values()))
        n = len(tickers)
        T = len(returns)
        shrinkage_factor = max(0.0, 1.0 - (n - 2) / (T * np.var(list(hist.values())) + 1e-10))
        ann_returns = {
            t: round(shrinkage_factor * hist[t] + (1 - shrinkage_factor) * grand_mean, 6)
            for t in tickers
        }
    else:
        raise ValueError(f"Unknown method: {method}")

    return {"expected_returns": ann_returns, "method": method}
