"""Deterministic OpenBB fetchers for each Market Overview panel.

Each async function returns a JSON-serializable list and raises on failure.
The terminal route calls these directly — no LLM code generation involved.
"""

import asyncio
from datetime import datetime, timedelta

from api.agent.openbb_client import get_obb_client

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


def _days_ahead(n: int) -> str:
    return (datetime.now() + timedelta(days=n)).strftime("%Y-%m-%d")


# Shared date helpers above are used by upcoming fetchers (fetch_equities, etc.).


# ---------------------------------------------------------------------------
# fetch_macro
# ---------------------------------------------------------------------------

_MACRO_SYMBOLS = ["FEDFUNDS", "DGS2", "DGS10", "CPIAUCSL", "VIXCLS"]


async def fetch_macro() -> list:
    """Fetch macro series from FRED. Returns long-format [{date, symbol, value}]."""
    obb = get_obb_client()

    def _call():
        return obb.economy.fred_series(
            symbol=_MACRO_SYMBOLS,
            provider="fred",
            start_date=_days_ago(90),
            end_date=_today(),
        )

    df = await asyncio.to_thread(_call)

    # FRED returns wide-format DataFrame (one column per symbol, date index).
    # reset_index() may name the column "index" or "date" depending on the index name.
    # Melt to long format expected by MacroPanel.extractSeriesLatest.
    reset = df.reset_index()
    # Normalize the date column name — it could be "index" if the index had no name
    if "index" in reset.columns and "date" not in reset.columns:
        reset = reset.rename(columns={"index": "date"})
    long = (
        reset
        .melt(id_vars="date", var_name="symbol", value_name="value")
        .dropna(subset=["value"])
    )
    long["date"] = long["date"].astype(str)
    return long.to_dict(orient="records")


# ---------------------------------------------------------------------------
# fetch_indices
# ---------------------------------------------------------------------------

_INDEX_TICKERS = [
    "SPY", "QQQ", "IWM", "DIA",
    "XLK", "XLF", "XLE", "XLV", "XLY", "XLC",
]


async def fetch_indices() -> list:
    """Fetch 10-day price history for equity index ETFs."""
    obb = get_obb_client()

    def _call():
        return obb.equity.price.historical(
            _INDEX_TICKERS,
            start_date=_days_ago(14),
            end_date=_today(),
            provider="yfinance",
        )

    df = await asyncio.to_thread(_call)
    return df.reset_index().to_dict(orient="records")


# ---------------------------------------------------------------------------
# fetch_heatmap
# ---------------------------------------------------------------------------

_HEATMAP_TICKERS = [
    "XLK", "XLC", "XLY", "XLE", "XLV", "XLF", "XLI", "XLU", "XLRE",
]


async def fetch_heatmap() -> list:
    """Fetch 3-day price history for sector ETFs."""
    obb = get_obb_client()

    def _call():
        return obb.equity.price.historical(
            _HEATMAP_TICKERS,
            start_date=_days_ago(5),
            end_date=_today(),
            provider="yfinance",
        )

    df = await asyncio.to_thread(_call)
    return df.reset_index().to_dict(orient="records")


# ---------------------------------------------------------------------------
# fetch_movers
# ---------------------------------------------------------------------------

# Top 50 S&P 500 large-caps by market cap. Update periodically.
_MOVERS_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK-B", "LLY", "JPM", "XOM",
    "V", "UNH", "AVGO", "TSLA", "PG", "MA", "JNJ", "HD", "COST", "MRK",
    "ABBV", "CVX", "WMT", "BAC", "PFE", "KO", "NFLX", "PM", "TMO", "CRM",
    "ACN", "AMD", "INTC", "ORCL", "ADBE", "QCOM", "TXN", "INTU", "IBM", "GE",
    "CAT", "DE", "MMM", "HON", "RTX", "BA", "LMT", "GS", "MS", "C",
]


async def fetch_movers() -> list:
    """Compute day % change for large-cap S&P 500 stocks using price history.

    Returns [{symbol, pct_change}] sorted descending by pct_change.
    """
    obb = get_obb_client()

    def _call():
        return obb.equity.price.historical(
            _MOVERS_TICKERS,
            start_date=_days_ago(5),
            end_date=_today(),
            provider="yfinance",
        )

    df = await asyncio.to_thread(_call)
    df = df.reset_index()

    results = []
    for symbol, grp in df.groupby("symbol"):
        grp = grp.sort_values("date")
        if len(grp) < 2:
            continue
        prev_close = grp.iloc[-2]["close"]
        last_close = grp.iloc[-1]["close"]
        if prev_close == 0:
            continue
        pct = (last_close - prev_close) / prev_close * 100
        results.append({"symbol": symbol, "pct_change": round(float(pct), 4)})

    results.sort(key=lambda x: x["pct_change"], reverse=True)
    return results
