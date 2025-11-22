"""Unit tests for panel_fetchers — each fetcher mocks OBB and HTTP calls."""
import json
import os
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from api.agent.panel_fetchers import fetch_macro, fetch_indices, fetch_heatmap, fetch_movers, fetch_calendar


# ---------------------------------------------------------------------------
# fetch_macro
# ---------------------------------------------------------------------------

def _make_fred_df():
    """Wide-format DataFrame as returned by obb.economy.fred_series."""
    idx = pd.to_datetime(["2026-03-01", "2026-03-02", "2026-03-03"])
    return pd.DataFrame(
        {
            "FEDFUNDS": [5.33, 5.33, None],
            "DGS2": [4.60, 4.61, 4.59],
            "DGS10": [4.30, 4.31, 4.29],
            "CPIAUCSL": [None, None, None],
            "VIXCLS": [15.2, 16.1, 14.8],
        },
        index=idx,
    )


@pytest.mark.asyncio
async def test_fetch_macro_returns_long_format():
    mock_obb = MagicMock()
    mock_obb.economy.fred_series.return_value = _make_fred_df()
    with patch("api.agent.panel_fetchers.get_obb_client", return_value=mock_obb):
        result = await fetch_macro()
    assert isinstance(result, list)
    assert len(result) > 0
    first = result[0]
    assert "symbol" in first
    assert "value" in first
    assert "date" in first


@pytest.mark.asyncio
async def test_fetch_macro_drops_nan_rows():
    mock_obb = MagicMock()
    mock_obb.economy.fred_series.return_value = _make_fred_df()
    with patch("api.agent.panel_fetchers.get_obb_client", return_value=mock_obb):
        result = await fetch_macro()
    symbols = {r["symbol"] for r in result}
    assert "CPIAUCSL" not in symbols


@pytest.mark.asyncio
async def test_fetch_macro_uses_fred_provider():
    mock_obb = MagicMock()
    mock_obb.economy.fred_series.return_value = _make_fred_df()
    with patch("api.agent.panel_fetchers.get_obb_client", return_value=mock_obb):
        await fetch_macro()
    call_kwargs = mock_obb.economy.fred_series.call_args[1]
    assert call_kwargs.get("provider") == "fred"
    assert "FEDFUNDS" in call_kwargs.get("symbol", [])
    assert call_kwargs.get("start_date") is not None
    assert call_kwargs.get("end_date") is not None


# ---------------------------------------------------------------------------
# fetch_indices + fetch_heatmap
# ---------------------------------------------------------------------------

def _make_price_df(symbols: list[str], days: int = 3):
    """Minimal OHLCV DataFrame as returned by obb.equity.price.historical."""
    rows = []
    for sym in symbols:
        for i in range(days):
            rows.append({
                "date": f"2026-04-0{i+5}",
                "open": 100.0, "high": 101.0, "low": 99.0,
                "close": 100.5 + i, "volume": 1_000_000,
                "symbol": sym,
            })
    return pd.DataFrame(rows).set_index("date")


@pytest.mark.asyncio
async def test_fetch_indices_returns_list_of_records():
    mock_obb = MagicMock()
    mock_obb.equity.price.historical.return_value = _make_price_df(
        ["SPY", "QQQ", "IWM"], days=3
    )
    with patch("api.agent.panel_fetchers.get_obb_client", return_value=mock_obb):
        result = await fetch_indices()
    assert isinstance(result, list)
    assert len(result) > 0
    assert "symbol" in result[0]
    assert "close" in result[0]


@pytest.mark.asyncio
async def test_fetch_indices_requests_correct_tickers():
    mock_obb = MagicMock()
    mock_obb.equity.price.historical.return_value = _make_price_df(["SPY"])
    with patch("api.agent.panel_fetchers.get_obb_client", return_value=mock_obb):
        await fetch_indices()
    tickers = mock_obb.equity.price.historical.call_args[0][0]
    assert "SPY" in tickers
    assert "XLC" in tickers
    assert len(tickers) == 10


@pytest.mark.asyncio
async def test_fetch_heatmap_requests_sector_etfs():
    mock_obb = MagicMock()
    mock_obb.equity.price.historical.return_value = _make_price_df(["XLK"])
    with patch("api.agent.panel_fetchers.get_obb_client", return_value=mock_obb):
        await fetch_heatmap()
    tickers = mock_obb.equity.price.historical.call_args[0][0]
    assert "XLK" in tickers
    assert "XLRE" in tickers
    assert len(tickers) == 9


# ---------------------------------------------------------------------------
# fetch_movers
# ---------------------------------------------------------------------------

def _make_movers_df():
    """5-day price history for a small set of tickers."""
    rows = [
        # AAPL: went up 10%
        {"date": "2026-04-07", "close": 100.0, "open": 99.0, "high": 101.0, "low": 98.0, "volume": 1000, "symbol": "AAPL"},
        {"date": "2026-04-08", "close": 110.0, "open": 100.0, "high": 111.0, "low": 99.0, "volume": 1000, "symbol": "AAPL"},
        # MSFT: went down 10%
        {"date": "2026-04-07", "close": 200.0, "open": 201.0, "high": 202.0, "low": 198.0, "volume": 1000, "symbol": "MSFT"},
        {"date": "2026-04-08", "close": 180.0, "open": 200.0, "high": 201.0, "low": 179.0, "volume": 1000, "symbol": "MSFT"},
        # NVDA: went up 4%
        {"date": "2026-04-07", "close": 50.0, "open": 50.0, "high": 51.0, "low": 49.0, "volume": 1000, "symbol": "NVDA"},
        {"date": "2026-04-08", "close": 52.0, "open": 50.0, "high": 53.0, "low": 49.0, "volume": 1000, "symbol": "NVDA"},
    ]
    return pd.DataFrame(rows).set_index("date")


@pytest.mark.asyncio
async def test_fetch_movers_returns_pct_change():
    mock_obb = MagicMock()
    mock_obb.equity.price.historical.return_value = _make_movers_df()
    with patch("api.agent.panel_fetchers.get_obb_client", return_value=mock_obb):
        result = await fetch_movers()
    assert isinstance(result, list)
    symbols = {r["symbol"] for r in result}
    assert "AAPL" in symbols
    assert "MSFT" in symbols
    aapl = next(r for r in result if r["symbol"] == "AAPL")
    assert abs(aapl["pct_change"] - 10.0) < 0.01  # (110-100)/100 * 100 = 10%


@pytest.mark.asyncio
async def test_fetch_movers_sorted_descending():
    mock_obb = MagicMock()
    mock_obb.equity.price.historical.return_value = _make_movers_df()
    with patch("api.agent.panel_fetchers.get_obb_client", return_value=mock_obb):
        result = await fetch_movers()
    pcts = [r["pct_change"] for r in result]
    assert pcts == sorted(pcts, reverse=True)


@pytest.mark.asyncio
async def test_fetch_movers_skips_single_day_tickers():
    mock_obb = MagicMock()
    df = _make_movers_df()
    solo_row = pd.DataFrame([
        {"date": "2026-04-08", "close": 10.0, "open": 10.0, "high": 10.5, "low": 9.5, "volume": 100, "symbol": "SOLO"}
    ]).set_index("date")
    mock_obb.equity.price.historical.return_value = pd.concat([df, solo_row])
    with patch("api.agent.panel_fetchers.get_obb_client", return_value=mock_obb):
        result = await fetch_movers()
    assert all(r["symbol"] != "SOLO" for r in result)


# ---------------------------------------------------------------------------
# fetch_calendar
# ---------------------------------------------------------------------------

def _make_fred_response(dates: list[str]) -> bytes:
    return json.dumps({
        "release_dates": [{"date": d} for d in dates]
    }).encode()


@pytest.mark.asyncio
async def test_fetch_calendar_returns_sorted_events():
    future_dates = ["2026-04-15", "2026-04-10"]

    def _mock_urlopen(url, **kwargs):
        resp = MagicMock()
        resp.read.return_value = _make_fred_response(future_dates)
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("api.agent.panel_fetchers.urllib.request.urlopen", side_effect=_mock_urlopen):
        with patch.dict(os.environ, {"FRED_API_KEY": "testkey"}):
            result = await fetch_calendar()

    dates = [r["date"] for r in result if r["event"] != "FOMC Meeting"]
    assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_fetch_calendar_deduplicates():
    future_dates = ["2026-04-14"]

    def _mock_urlopen(url, **kwargs):
        resp = MagicMock()
        resp.read.return_value = _make_fred_response(future_dates)
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("api.agent.panel_fetchers.urllib.request.urlopen", side_effect=_mock_urlopen):
        with patch.dict(os.environ, {"FRED_API_KEY": "testkey"}):
            result = await fetch_calendar()

    pairs = [(r["date"], r["event"]) for r in result]
    assert len(pairs) == len(set(pairs))


@pytest.mark.asyncio
async def test_fetch_calendar_max_10_events():
    future_dates = [f"2026-04-{str(i).zfill(2)}" for i in range(9, 30)]

    def _mock_urlopen(url, **kwargs):
        resp = MagicMock()
        resp.read.return_value = _make_fred_response(future_dates)
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("api.agent.panel_fetchers.urllib.request.urlopen", side_effect=_mock_urlopen):
        with patch.dict(os.environ, {"FRED_API_KEY": "testkey"}):
            result = await fetch_calendar()

    assert len(result) <= 10
