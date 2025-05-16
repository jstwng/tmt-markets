"""Covariance matrix estimation methods."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf, ShrunkCovariance

__all__ = ["estimate_covariance", "CovarianceResult"]


class InsufficientDataError(Exception):
    """Raised when there is not enough data for covariance estimation."""


@dataclass
class CovarianceResult:
    """Result of covariance estimation.

    Attributes:
        matrix: The covariance matrix as a 2D numpy array.
        tickers: List of ticker symbols corresponding to rows/columns.
        method: The estimation method used.
    """
    matrix: np.ndarray
    tickers: list[str]
    method: str


def estimate_covariance(
    prices: pd.DataFrame,
    method: Literal["sample", "ledoit_wolf", "shrunk"] = "ledoit_wolf",
) -> CovarianceResult:
    """Estimate the covariance matrix of asset returns.

    Args:
        prices: DataFrame with columns as tickers, index as dates,
                values as adjusted close prices.
        method: Estimation method.
            - "sample": Standard sample covariance.
            - "ledoit_wolf": Ledoit-Wolf shrinkage (recommended for small samples).
            - "shrunk": Basic shrinkage estimator.

    Returns:
        CovarianceResult with the estimated covariance matrix.

    Raises:
        InsufficientDataError: If fewer than 2 observations.
    """
    returns = prices.pct_change().dropna()

    if len(returns) < 2:
        raise InsufficientDataError(
            f"Need at least 2 return observations, got {len(returns)}"
        )

    tickers = list(prices.columns)

    if method == "sample":
        cov_matrix = returns.cov().values
    elif method == "ledoit_wolf":
        lw = LedoitWolf().fit(returns.values)
        cov_matrix = lw.covariance_
    elif method == "shrunk":
        sc = ShrunkCovariance().fit(returns.values)
        cov_matrix = sc.covariance_
    else:
        raise ValueError(f"Unknown method: {method}")

    # Annualize (252 trading days)
    cov_matrix = cov_matrix * 252

    return CovarianceResult(
        matrix=cov_matrix,
        tickers=tickers,
        method=method,
    )
