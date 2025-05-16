"""Market data fetching via yfinance and OpenBB."""

from typing import Literal

import pandas as pd
import yfinance as yf

__all__ = ["fetch_prices"]


class DataFetchError(Exception):
    """Raised when price data cannot be fetched."""


def fetch_prices(
    tickers: list[str],
    start_date: str,
    end_date: str,
    source: Literal["yfinance", "openbb"] = "yfinance",
) -> pd.DataFrame:
    """Fetch adjusted close prices for the given tickers.

    Args:
        tickers: List of ticker symbols (e.g., ["AAPL", "MSFT"]).
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        source: Data source to use.

    Returns:
        DataFrame with DatetimeIndex, columns as tickers, values as adjusted close prices.

    Raises:
        DataFetchError: If data cannot be fetched or is empty.
    """
    if source == "yfinance":
        return _fetch_yfinance(tickers, start_date, end_date)
    elif source == "openbb":
        return _fetch_openbb(tickers, start_date, end_date)
    else:
        raise ValueError(f"Unknown source: {source}")


def _fetch_yfinance(tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
    data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True)
    if data.empty:
        raise DataFetchError(f"No data returned for {tickers} from yfinance")

    # yfinance returns MultiIndex columns: (Price, Ticker)
    prices = data["Close"]

    # Drop the Ticker level if it's a MultiIndex (single or multi-ticker)
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(name=tickers[0])
    elif hasattr(prices.columns, 'droplevel'):
        # Flatten MultiIndex columns to just ticker names
        prices.columns = prices.columns.droplevel(0) if prices.columns.nlevels > 1 else prices.columns

    prices = prices.dropna()
    if prices.empty:
        raise DataFetchError(f"All data was NaN for {tickers}")

    return prices


def _fetch_openbb(tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
    try:
        from openbb import obb

        frames = []
        for ticker in tickers:
            result = obb.equity.price.historical(
                symbol=ticker,
                start_date=start_date,
                end_date=end_date,
                provider="yfinance",
            )
            df = result.to_dataframe()
            if "close" in df.columns:
                frames.append(df[["close"]].rename(columns={"close": ticker}))

        if not frames:
            raise DataFetchError(f"No data returned for {tickers} from OpenBB")

        prices = pd.concat(frames, axis=1).dropna()
        if prices.empty:
            raise DataFetchError(f"All data was NaN for {tickers} from OpenBB")

        return prices

    except ImportError:
        raise DataFetchError(
            "OpenBB is not installed. Install with: pip install openbb"
        )
