"""Tests for /api/terminal/panel/{panel} endpoint."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

VALID_PANELS = ["macro", "indices", "movers", "heatmap", "calendar"]

_MOCK_RAW = [{"date": "2024-01-01", "value": 5.33}]


@pytest.fixture(autouse=True)
def mock_codegen_and_sandbox():
    """Mock generate_openbb_code and execute_openbb_code for all terminal tests."""
    with patch(
        "api.routes.terminal.generate_openbb_code",
        new_callable=AsyncMock,
        return_value='obb.economy.fred_series(symbol="FEDFUNDS", provider="fred")',
    ) as mock_gen, patch(
        "api.routes.terminal.execute_openbb_code",
        new_callable=AsyncMock,
        return_value=_MOCK_RAW,
    ) as mock_exec, patch(
        "api.routes.terminal._get_obb_client",
        return_value=MagicMock(),
    ):
        yield mock_gen, mock_exec


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


def test_cache_is_used_on_second_request(mock_codegen_and_sandbox):
    mock_gen, mock_exec = mock_codegen_and_sandbox
    # Clear cache first
    from api.routes.terminal import _cache
    _cache.clear()

    client.get("/api/terminal/panel/macro?ttl=300")
    client.get("/api/terminal/panel/macro?ttl=300")

    # generate_openbb_code should only be called once (second hits cache)
    assert mock_gen.call_count == 1


def test_error_response_on_codegen_failure():
    from api.routes.terminal import _cache
    _cache.clear()

    with patch(
        "api.routes.terminal.generate_openbb_code",
        new_callable=AsyncMock,
        side_effect=Exception("LLM quota exceeded"),
    ), patch("api.routes.terminal._get_obb_client", return_value=MagicMock()):
        resp = client.get("/api/terminal/panel/macro?ttl=300")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("error") is True
