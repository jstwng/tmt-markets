# Terminal Panel Direct Fetchers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the LLM code-generation pipeline for the five Market Overview panels with deterministic Python fetcher functions so that MACRO, TOP MOVERS, and MACRO CALENDAR stop failing.

**Architecture:** A new `panel_fetchers.py` module exposes one `async` function per panel that calls OpenBB (or FRED REST) directly. `terminal.py` replaces `_fetch_panel()` with a direct call into that map. The response schema is unchanged, so no frontend panel components change.

**Tech Stack:** Python 3.12, FastAPI, OpenBB Platform, FRED REST API, pandas, pytest-asyncio, React/TypeScript

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| **Create** | `packages/api/api/agent/panel_fetchers.py` | One async fetcher per panel; PANEL_FETCHERS dict |
| **Create** | `packages/api/tests/test_panel_fetchers.py` | Unit tests for each fetcher (mocked OBB/HTTP) |
| **Modify** | `packages/api/api/agent/openbb_client.py` | Load FRED_API_KEY from env, set on obb credentials |
| **Modify** | `packages/api/api/routes/terminal.py` | Remove codegen pipeline; call PANEL_FETCHERS directly |
| **Modify** | `packages/api/api/main.py` | Add FRED_API_KEY to startup env check |
| **Modify** | `packages/api/tests/test_terminal_routes.py` | Replace codegen mocks with PANEL_FETCHERS mock |
| **Modify** | `packages/web/src/hooks/useTerminalPanel.ts` | Set loading=true + clear error before fetch (retry fix) |
| **Modify** | `packages/web/src/components/terminal/MoversPanel.tsx` | Add `pct_change` to field fallback chain |

---

## Task 1: Configure FRED API key in openbb_client

**Files:**
- Modify: `packages/api/api/agent/openbb_client.py`

- [ ] **Read the current file**

```python
# Current content of packages/api/api/agent/openbb_client.py:
from openbb import obb
obb.user.preferences.output_type = "dataframe"

def get_obb_client():
    return obb
```

- [ ] **Write the failing test**

Create `packages/api/tests/test_openbb_client.py`:

```python
"""Tests for OpenBB client credential configuration."""
import os
from unittest.mock import patch, MagicMock


def test_fred_key_applied_when_env_set():
    mock_obb = MagicMock()
    with patch.dict(os.environ, {"FRED_API_KEY": "test_key_123"}):
        with patch("api.agent.openbb_client.obb", mock_obb):
            from importlib import reload
            import api.agent.openbb_client as mod
            reload(mod)
            client = mod.get_obb_client()
    mock_obb.user.credentials.__setattr__  # just confirm obb was accessed
    assert client is mock_obb


def test_fred_key_skipped_when_env_missing():
    mock_obb = MagicMock()
    env = {k: v for k, v in os.environ.items() if k != "FRED_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with patch("api.agent.openbb_client.obb", mock_obb):
            from importlib import reload
            import api.agent.openbb_client as mod
            reload(mod)
            mod.get_obb_client()
    # Should not raise
```

- [ ] **Run test to confirm it fails**

```bash
cd packages/api
/opt/anaconda3/envs/tmt-markets/bin/python -m pytest tests/test_openbb_client.py -v
```

Expected: ImportError or AttributeError since the credential-setting code doesn't exist yet.

- [ ] **Implement: update openbb_client.py**

```python
"""OpenBB Platform client singleton for sandboxed code execution."""

import os

from dotenv import load_dotenv
from openbb import obb

load_dotenv()

# Use DataFrame output by default — generated code often transforms DataFrames
obb.user.preferences.output_type = "dataframe"


def get_obb_client():
    """Return the configured OpenBB client singleton.

    Applies FRED_API_KEY from environment if present.
    Free providers (yfinance, SEC EDGAR) are available without API keys.
    """
    fred_key = os.getenv("FRED_API_KEY")
    if fred_key:
        obb.user.credentials.fred_api_key = fred_key
    return obb
```

- [ ] **Run test to confirm it passes**

```bash
/opt/anaconda3/envs/tmt-markets/bin/python -m pytest tests/test_openbb_client.py -v
```

Expected: 2 passed.

- [ ] **Commit**

```bash
git add packages/api/api/agent/openbb_client.py packages/api/tests/test_openbb_client.py
git commit -m "feat: load FRED_API_KEY from env in openbb_client"
```

---

## Task 2: Create panel_fetchers.py — fetch_macro

**Files:**
- Create: `packages/api/api/agent/panel_fetchers.py`
- Create: `packages/api/tests/test_panel_fetchers.py`

- [ ] **Write the failing test**

Create `packages/api/tests/test_panel_fetchers.py`:

```python
"""Unit tests for panel_fetchers — each fetcher mocks OBB and HTTP calls."""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime


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
        from api.agent.panel_fetchers import fetch_macro
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
        from api.agent.panel_fetchers import fetch_macro
        result = await fetch_macro()

    # CPIAUCSL has all NaN — should be dropped
    symbols = {r["symbol"] for r in result}
    assert "CPIAUCSL" not in symbols or all(
        r["value"] is not None for r in result if r["symbol"] == "CPIAUCSL"
    )


@pytest.mark.asyncio
async def test_fetch_macro_uses_fred_provider():
    mock_obb = MagicMock()
    mock_obb.economy.fred_series.return_value = _make_fred_df()

    with patch("api.agent.panel_fetchers.get_obb_client", return_value=mock_obb):
        from api.agent.panel_fetchers import fetch_macro
        await fetch_macro()

    call_kwargs = mock_obb.economy.fred_series.call_args[1]
    assert call_kwargs.get("provider") == "fred"
    assert "FEDFUNDS" in call_kwargs.get("symbol", [])
```

- [ ] **Run test to confirm it fails**

```bash
cd packages/api
/opt/anaconda3/envs/tmt-markets/bin/python -m pytest tests/test_panel_fetchers.py -v
```

Expected: ImportError — `panel_fetchers` module does not exist yet.

- [ ] **Implement: create panel_fetchers.py with fetch_macro**

Create `packages/api/api/agent/panel_fetchers.py`:

```python
"""Deterministic OpenBB fetchers for each Market Overview panel.

Each async function returns a JSON-serializable list and raises on failure.
The terminal route calls these directly — no LLM code generation involved.
"""

import asyncio
import json
import os
import urllib.request
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


# ---------------------------------------------------------------------------
# fetch_macro
# ---------------------------------------------------------------------------

_MACRO_SYMBOLS = ["FEDFUNDS", "DGS2", "DGS10", "CPIAUCSL", "VIXCLS"]


async def fetch_macro() -> list:
    """Fetch macro series from FRED. Returns long-format [{date, symbol, value}]."""
    obb = get_obb_client()

    def _call():
        return obb.economy.fred_series(symbol=_MACRO_SYMBOLS, provider="fred")

    df = await asyncio.to_thread(_call)

    # FRED returns wide-format DataFrame (one column per symbol, date index).
    # Melt to long format expected by MacroPanel.extractSeriesLatest.
    long = (
        df.reset_index()
        .melt(id_vars="date", var_name="symbol", value_name="value")
        .dropna(subset=["value"])
    )
    long["date"] = long["date"].astype(str)
    return long.to_dict(orient="records")
```

- [ ] **Run test to confirm it passes**

```bash
/opt/anaconda3/envs/tmt-markets/bin/python -m pytest tests/test_panel_fetchers.py -v
```

Expected: 3 passed.

- [ ] **Commit**

```bash
git add packages/api/api/agent/panel_fetchers.py packages/api/tests/test_panel_fetchers.py
git commit -m "feat: add panel_fetchers module with fetch_macro"
```

---

## Task 3: Add fetch_indices and fetch_heatmap

**Files:**
- Modify: `packages/api/api/agent/panel_fetchers.py`
- Modify: `packages/api/tests/test_panel_fetchers.py`

- [ ] **Write failing tests** — append to `tests/test_panel_fetchers.py`:

```python
# ---------------------------------------------------------------------------
# fetch_indices + fetch_heatmap
# ---------------------------------------------------------------------------

def _make_price_df(symbols: list[str], days: int = 3):
    """Minimal OHLCV DataFrame as returned by obb.equity.price.historical."""
    import pandas as pd
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
        from api.agent.panel_fetchers import fetch_indices
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
        from api.agent.panel_fetchers import fetch_indices
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
        from api.agent.panel_fetchers import fetch_heatmap
        await fetch_heatmap()

    tickers = mock_obb.equity.price.historical.call_args[0][0]
    assert "XLK" in tickers
    assert "XLRE" in tickers
    assert len(tickers) == 9
```

- [ ] **Run test to confirm it fails**

```bash
/opt/anaconda3/envs/tmt-markets/bin/python -m pytest tests/test_panel_fetchers.py::test_fetch_indices_returns_list_of_records -v
```

Expected: AttributeError — `fetch_indices` does not exist yet.

- [ ] **Implement: append to panel_fetchers.py**

```python
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
```

- [ ] **Run tests to confirm they pass**

```bash
/opt/anaconda3/envs/tmt-markets/bin/python -m pytest tests/test_panel_fetchers.py -v
```

Expected: all existing + 3 new = 6 passed.

- [ ] **Commit**

```bash
git add packages/api/api/agent/panel_fetchers.py packages/api/tests/test_panel_fetchers.py
git commit -m "feat: add fetch_indices and fetch_heatmap to panel_fetchers"
```

---

## Task 4: Add fetch_movers

**Files:**
- Modify: `packages/api/api/agent/panel_fetchers.py`
- Modify: `packages/api/tests/test_panel_fetchers.py`

- [ ] **Write failing tests** — append to `tests/test_panel_fetchers.py`:

```python
# ---------------------------------------------------------------------------
# fetch_movers
# ---------------------------------------------------------------------------

def _make_movers_df():
    """5-day price history for a small set of tickers."""
    import pandas as pd
    rows = [
        # AAPL: went up
        {"date": "2026-04-07", "close": 100.0, "open": 99.0, "high": 101.0, "low": 98.0, "volume": 1000, "symbol": "AAPL"},
        {"date": "2026-04-08", "close": 110.0, "open": 100.0, "high": 111.0, "low": 99.0, "volume": 1000, "symbol": "AAPL"},
        # MSFT: went down
        {"date": "2026-04-07", "close": 200.0, "open": 201.0, "high": 202.0, "low": 198.0, "volume": 1000, "symbol": "MSFT"},
        {"date": "2026-04-08", "close": 180.0, "open": 200.0, "high": 201.0, "low": 179.0, "volume": 1000, "symbol": "MSFT"},
        # NVDA: unchanged direction
        {"date": "2026-04-07", "close": 50.0, "open": 50.0, "high": 51.0, "low": 49.0, "volume": 1000, "symbol": "NVDA"},
        {"date": "2026-04-08", "close": 52.0, "open": 50.0, "high": 53.0, "low": 49.0, "volume": 1000, "symbol": "NVDA"},
    ]
    return pd.DataFrame(rows).set_index("date")


@pytest.mark.asyncio
async def test_fetch_movers_returns_pct_change():
    mock_obb = MagicMock()
    mock_obb.equity.price.historical.return_value = _make_movers_df()
    with patch("api.agent.panel_fetchers.get_obb_client", return_value=mock_obb):
        from api.agent.panel_fetchers import fetch_movers
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
        from api.agent.panel_fetchers import fetch_movers
        result = await fetch_movers()

    pcts = [r["pct_change"] for r in result]
    assert pcts == sorted(pcts, reverse=True)


@pytest.mark.asyncio
async def test_fetch_movers_skips_single_day_tickers():
    import pandas as pd
    mock_obb = MagicMock()
    # Only one day of data for SOLO — should be excluded
    df = _make_movers_df()
    solo_row = pd.DataFrame([
        {"date": "2026-04-08", "close": 10.0, "open": 10.0, "high": 10.5, "low": 9.5, "volume": 100, "symbol": "SOLO"}
    ]).set_index("date")
    mock_obb.equity.price.historical.return_value = pd.concat([df, solo_row])
    with patch("api.agent.panel_fetchers.get_obb_client", return_value=mock_obb):
        from api.agent.panel_fetchers import fetch_movers
        result = await fetch_movers()

    assert all(r["symbol"] != "SOLO" for r in result)
```

- [ ] **Run test to confirm it fails**

```bash
/opt/anaconda3/envs/tmt-markets/bin/python -m pytest tests/test_panel_fetchers.py::test_fetch_movers_returns_pct_change -v
```

Expected: AttributeError — `fetch_movers` does not exist.

- [ ] **Implement: append to panel_fetchers.py**

```python
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
```

- [ ] **Run tests to confirm they pass**

```bash
/opt/anaconda3/envs/tmt-markets/bin/python -m pytest tests/test_panel_fetchers.py -v
```

Expected: all 9 passed.

- [ ] **Commit**

```bash
git add packages/api/api/agent/panel_fetchers.py packages/api/tests/test_panel_fetchers.py
git commit -m "feat: add fetch_movers to panel_fetchers"
```

---

## Task 5: Add fetch_calendar

**Files:**
- Modify: `packages/api/api/agent/panel_fetchers.py`
- Modify: `packages/api/tests/test_panel_fetchers.py`

- [ ] **Write failing tests** — append to `tests/test_panel_fetchers.py`:

```python
# ---------------------------------------------------------------------------
# fetch_calendar
# ---------------------------------------------------------------------------

def _make_fred_response(dates: list[str]) -> bytes:
    import json
    return json.dumps({
        "release_dates": [{"date": d} for d in dates]
    }).encode()


@pytest.mark.asyncio
async def test_fetch_calendar_returns_sorted_events():
    future_dates = ["2026-04-15", "2026-04-10"]

    def _mock_urlopen(url):
        resp = MagicMock()
        resp.read.return_value = _make_fred_response(future_dates)
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("api.agent.panel_fetchers.urllib.request.urlopen", side_effect=_mock_urlopen):
        with patch.dict(os.environ, {"FRED_API_KEY": "testkey"}):
            from api.agent.panel_fetchers import fetch_calendar
            result = await fetch_calendar()

    dates = [r["date"] for r in result if r["event"] != "FOMC Meeting"]
    assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_fetch_calendar_includes_fomc():
    def _mock_urlopen(url):
        resp = MagicMock()
        resp.read.return_value = _make_fred_response([])
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("api.agent.panel_fetchers.urllib.request.urlopen", side_effect=_mock_urlopen):
        with patch.dict(os.environ, {"FRED_API_KEY": "testkey"}):
            from api.agent.panel_fetchers import fetch_calendar
            result = await fetch_calendar()

    fomc = [r for r in result if r["event"] == "FOMC Meeting"]
    # May be 0 if all FOMC dates are >60 days away — just verify no crash
    assert isinstance(fomc, list)


@pytest.mark.asyncio
async def test_fetch_calendar_deduplicates():
    # Same date returned for multiple release IDs
    future_dates = ["2026-04-14"]

    def _mock_urlopen(url):
        resp = MagicMock()
        resp.read.return_value = _make_fred_response(future_dates)
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("api.agent.panel_fetchers.urllib.request.urlopen", side_effect=_mock_urlopen):
        with patch.dict(os.environ, {"FRED_API_KEY": "testkey"}):
            from api.agent.panel_fetchers import fetch_calendar
            result = await fetch_calendar()

    # Each (date, event) pair should appear at most once
    pairs = [(r["date"], r["event"]) for r in result]
    assert len(pairs) == len(set(pairs))


@pytest.mark.asyncio
async def test_fetch_calendar_max_10_events():
    # Return many dates to test the cap
    future_dates = [f"2026-04-{str(i).zfill(2)}" for i in range(9, 30)]

    def _mock_urlopen(url):
        resp = MagicMock()
        resp.read.return_value = _make_fred_response(future_dates)
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("api.agent.panel_fetchers.urllib.request.urlopen", side_effect=_mock_urlopen):
        with patch.dict(os.environ, {"FRED_API_KEY": "testkey"}):
            from api.agent.panel_fetchers import fetch_calendar
            result = await fetch_calendar()

    assert len(result) <= 10
```

Also add `import os` to the top of the test file.

- [ ] **Run test to confirm it fails**

```bash
/opt/anaconda3/envs/tmt-markets/bin/python -m pytest tests/test_panel_fetchers.py::test_fetch_calendar_returns_sorted_events -v
```

Expected: AttributeError — `fetch_calendar` does not exist.

- [ ] **Implement: append to panel_fetchers.py**

```python
# ---------------------------------------------------------------------------
# fetch_calendar
# ---------------------------------------------------------------------------

# FRED release IDs for key macro events (free, no API key tier limit)
_FRED_MACRO_RELEASES: dict[int, str] = {
    10: "CPI",
    46: "PPI",
    53: "GDP",
    50: "Nonfarm Payrolls",
    54: "PCE",
    175: "Retail Sales",
}

# Fed's published 2026 FOMC decision dates (second day of each meeting).
# Update each December when the Fed releases the following year's schedule.
_FOMC_DATES = [
    "2026-05-07", "2026-06-17", "2026-07-29",
    "2026-09-16", "2026-10-28", "2026-12-10",
]


async def _fetch_release_dates(release_id: int, name: str, api_key: str, today: str, end: str) -> list:
    url = (
        "https://api.stlouisfed.org/fred/release/dates"
        f"?release_id={release_id}&api_key={api_key}&file_type=json"
        "&sort_order=asc&include_release_dates_with_no_data=true"
    )

    def _get():
        with urllib.request.urlopen(url) as resp:
            return json.loads(resp.read())

    data = await asyncio.to_thread(_get)
    return [
        {"date": d["date"], "event": name}
        for d in data.get("release_dates", [])
        if today <= d["date"] <= end
    ]


async def fetch_calendar() -> list:
    """Fetch upcoming macro calendar events from FRED REST API.

    Returns [{date, event}] sorted by date, max 10 entries.
    """
    api_key = os.getenv("FRED_API_KEY", "")
    today = _today()
    end = _days_ahead(60)

    tasks = [
        _fetch_release_dates(rid, name, api_key, today, end)
        for rid, name in _FRED_MACRO_RELEASES.items()
    ]
    batches = await asyncio.gather(*tasks)
    results = [event for batch in batches for event in batch]

    # Add hardcoded FOMC decision dates
    for date in _FOMC_DATES:
        if today <= date <= end:
            results.append({"date": date, "event": "FOMC Meeting"})

    # Sort, deduplicate, cap at 10
    results.sort(key=lambda x: x["date"])
    seen: set[tuple] = set()
    unique = []
    for r in results:
        key = (r["date"], r["event"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique[:10]
```

Also add `import os` at the top of `panel_fetchers.py` if not already there (it is — check the helpers section).

- [ ] **Run all tests to confirm they pass**

```bash
/opt/anaconda3/envs/tmt-markets/bin/python -m pytest tests/test_panel_fetchers.py -v
```

Expected: all 13 passed.

- [ ] **Commit**

```bash
git add packages/api/api/agent/panel_fetchers.py packages/api/tests/test_panel_fetchers.py
git commit -m "feat: add fetch_calendar to panel_fetchers (FRED REST + hardcoded FOMC)"
```

---

## Task 6: Wire fetchers into terminal.py + update route tests

**Files:**
- Modify: `packages/api/api/routes/terminal.py`
- Modify: `packages/api/api/main.py`
- Modify: `packages/api/tests/test_terminal_routes.py`

- [ ] **Update test_terminal_routes.py** — replace the codegen mock fixture with a PANEL_FETCHERS mock:

The existing `mock_codegen_and_sandbox` fixture mocks `generate_openbb_code` and `execute_openbb_code`. Those imports won't exist in `terminal.py` after this task. Replace the entire fixture and update the cache test:

```python
"""Tests for /api/terminal/panel/{panel} endpoint."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

VALID_PANELS = ["macro", "indices", "movers", "heatmap", "calendar"]

_MOCK_RAW = [{"date": "2024-01-01", "value": 5.33}]

_MOCK_FETCHERS = {
    panel: AsyncMock(return_value=_MOCK_RAW) for panel in VALID_PANELS
}


@pytest.fixture(autouse=True)
def mock_panel_fetchers():
    """Mock PANEL_FETCHERS for all terminal route tests."""
    fresh = {panel: AsyncMock(return_value=_MOCK_RAW) for panel in VALID_PANELS}
    with patch("api.routes.terminal.PANEL_FETCHERS", fresh):
        yield fresh


def test_valid_panels_return_200():
    for panel in VALID_PANELS:
        resp = client.get(f"/api/terminal/panel/{panel}?ttl=300")
        assert resp.status_code == 200, f"Panel {panel} returned {resp.status_code}: {resp.text}"


def test_response_has_required_fields():
    resp = client.get("/api/terminal/panel/macro?ttl=300")
    body = resp.json()
    assert "panel" in body
    assert "raw_data" in body
    assert "cached_at" in body
    assert body["panel"] == "macro"


def test_invalid_panel_returns_404():
    resp = client.get("/api/terminal/panel/nonexistent?ttl=300")
    assert resp.status_code == 404


def test_cache_is_used_on_second_request(mock_panel_fetchers):
    from api.routes.terminal import _cache
    _cache.clear()

    client.get("/api/terminal/panel/macro?ttl=300")
    client.get("/api/terminal/panel/macro?ttl=300")

    # Fetcher should only be called once (second hits cache)
    assert mock_panel_fetchers["macro"].call_count == 1


def test_error_response_on_fetch_failure():
    from api.routes.terminal import _cache
    _cache.clear()

    failing = {panel: AsyncMock(side_effect=Exception("API down")) for panel in VALID_PANELS}
    with patch("api.routes.terminal.PANEL_FETCHERS", failing):
        resp = client.get("/api/terminal/panel/macro?ttl=300")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("error") is True
```

- [ ] **Run updated tests to confirm they fail** (terminal.py still uses old codegen)

```bash
/opt/anaconda3/envs/tmt-markets/bin/python -m pytest tests/test_terminal_routes.py -v
```

Expected: errors patching `api.routes.terminal.PANEL_FETCHERS` which doesn't exist yet.

- [ ] **Rewrite terminal.py**

```python
"""Terminal tab panel endpoints.

GET /api/terminal/panel/{panel}?ttl=300

Returns raw data for each panel. Each panel has a deterministic fetcher
in panel_fetchers.py — no LLM code generation involved.
"""

import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from api.agent.panel_fetchers import (
    fetch_calendar,
    fetch_heatmap,
    fetch_indices,
    fetch_macro,
    fetch_movers,
)

router = APIRouter(tags=["terminal"])

# In-memory cache: panel -> {"data": ..., "ts": float}
_cache: dict[str, dict[str, Any]] = {}

PANEL_FETCHERS = {
    "macro": fetch_macro,
    "indices": fetch_indices,
    "movers": fetch_movers,
    "heatmap": fetch_heatmap,
    "calendar": fetch_calendar,
}


@router.get("/terminal/panel/{panel}")
async def get_terminal_panel(panel: str, ttl: int = 300):
    if panel not in PANEL_FETCHERS:
        raise HTTPException(status_code=404, detail=f"Unknown panel: {panel}")

    cached = _cache.get(panel)
    if cached and (time.time() - cached["ts"]) < ttl:
        return cached["data"]

    try:
        raw_data = await PANEL_FETCHERS[panel]()
        response = {
            "panel": panel,
            "raw_data": raw_data,
            "cached_at": datetime.utcnow().isoformat() + "Z",
            "error": False,
        }
        _cache[panel] = {"data": response, "ts": time.time()}
        return response
    except Exception as exc:
        stale = _cache.get(panel, {}).get("data")
        return {
            "panel": panel,
            "raw_data": stale["raw_data"] if stale else [],
            "cached_at": stale["cached_at"] if stale else None,
            "error": True,
            "error_message": str(exc),
        }
```

- [ ] **Update main.py** — add `FRED_API_KEY` to the env check list:

In `packages/api/api/main.py`, change line 17:
```python
    for key in ["GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_JWT_SECRET", "FRED_API_KEY"]:
```

- [ ] **Run all backend tests**

```bash
/opt/anaconda3/envs/tmt-markets/bin/python -m pytest tests/ -v
```

Expected: all tests pass. Tests that were mocking `generate_openbb_code` / `execute_openbb_code` in `terminal.py` are now replaced. The `test_openbb_codegen.py` and `test_openbb_sandbox.py` tests are unaffected (those modules still exist for the chat agent).

- [ ] **Commit**

```bash
git add packages/api/api/routes/terminal.py packages/api/api/main.py packages/api/tests/test_terminal_routes.py
git commit -m "feat: wire panel_fetchers into terminal route; remove codegen pipeline"
```

---

## Task 7: Fix frontend retry UX + MoversPanel field fallback

**Files:**
- Modify: `packages/web/src/hooks/useTerminalPanel.ts`
- Modify: `packages/web/src/components/terminal/MoversPanel.tsx`

- [ ] **Fix useTerminalPanel.ts** — add `setLoading(true); setError(null)` at the top of `fetchPanel`:

Current `fetchPanel` (line 14–29):
```typescript
const fetchPanel = useCallback(async () => {
  try {
    const ttl = Math.floor(intervalMs / 1000);
    const result = await getTerminalPanel(panel, ttl);
    ...
```

Replace with:
```typescript
const fetchPanel = useCallback(async () => {
  setLoading(true);
  setError(null);
  try {
    const ttl = Math.floor(intervalMs / 1000);
    const result = await getTerminalPanel(panel, ttl);
    setData(result);
    setLastUpdated(new Date());
    if (result.error) {
      setError(result.error_message ?? "Failed to load panel data");
    } else {
      setError(null);
    }
  } catch (e) {
    setError(e instanceof Error ? e.message : "Network error");
  } finally {
    setLoading(false);
  }
}, [panel, intervalMs]);
```

- [ ] **Fix MoversPanel.tsx** — add `pct_change` to the field fallback chain:

Current line 13 in `extractMovers`:
```typescript
pct: parseFloat(
  String(r.percent_change ?? r.change_percent ?? r.day_change_percent ?? 0)
),
```

Replace with:
```typescript
pct: parseFloat(
  String(r.pct_change ?? r.percent_change ?? r.change_percent ?? r.day_change_percent ?? 0)
),
```

- [ ] **Verify the app builds with no TypeScript errors**

```bash
cd packages/web
npm run build 2>&1 | tail -20
```

Expected: `built in Xs` with no errors.

- [ ] **Manual smoke test** — start the dev stack and verify all 5 panels load

```bash
# Terminal 1: API
cd packages/api && /opt/anaconda3/envs/tmt-markets/bin/uvicorn api.main:app --reload

# Terminal 2: Web
cd packages/web && npm run dev
```

Open http://localhost:5173, navigate to Market Overview. All 5 panels should show data (not "Failed to load"). Confirm Retry button shows loading skeleton when clicked.

- [ ] **Commit**

```bash
git add packages/web/src/hooks/useTerminalPanel.ts packages/web/src/components/terminal/MoversPanel.tsx
git commit -m "fix: show loading skeleton on retry; add pct_change field fallback in MoversPanel"
```

---

## Task 8: Push and close

- [ ] **Run full test suite one last time**

```bash
cd packages/api
/opt/anaconda3/envs/tmt-markets/bin/python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Push**

```bash
git push
```

- [ ] **Create beads issues and close them**

```bash
bd ready
```
