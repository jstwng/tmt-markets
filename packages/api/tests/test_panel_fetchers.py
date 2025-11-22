"""Unit tests for panel_fetchers — each fetcher mocks OBB and HTTP calls."""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from api.agent.panel_fetchers import fetch_macro


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
