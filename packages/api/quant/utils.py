"""Shared utility functions for quant computations."""

import numpy as np
import pandas as pd

__all__ = ["annualize_return", "annualize_volatility", "max_drawdown", "rolling_sharpe"]


def annualize_return(daily_returns: pd.Series, trading_days: int = 252) -> float:
    """Annualize a series of daily returns."""
    cum_return = (1 + daily_returns).prod()
    n_years = len(daily_returns) / trading_days
    return float(cum_return ** (1 / n_years) - 1) if n_years > 0 else 0.0


def annualize_volatility(daily_returns: pd.Series, trading_days: int = 252) -> float:
    """Annualize daily return volatility."""
    return float(daily_returns.std() * np.sqrt(trading_days))


def max_drawdown(equity_curve: pd.Series) -> float:
    """Compute maximum drawdown from an equity curve."""
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax
    return float(drawdown.min())


def rolling_sharpe(
    daily_returns: pd.Series,
    window: int = 63,
    trading_days: int = 252,
) -> pd.Series:
    """Compute rolling Sharpe ratio."""
    rolling_mean = daily_returns.rolling(window).mean()
    rolling_std = daily_returns.rolling(window).std()
    return rolling_mean / rolling_std * np.sqrt(trading_days)
