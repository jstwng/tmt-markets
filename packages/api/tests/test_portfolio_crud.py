"""Tests for POST /api/portfolios and PATCH /api/portfolios/{id}."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_current_user, AuthenticatedUser

client = TestClient(app)

FAKE_PORTFOLIO = {
    "id": "port-abc",
    "name": "My Portfolio",
    "tickers": ["AAPL"],
    "weights": [1.0],
    "constraints": None,
    "metadata": None,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
}


def _mock_user():
    return AuthenticatedUser(id="user-123", email="test@example.com")


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: _mock_user()
    yield
    app.dependency_overrides.clear()


def _insert_mock(returned_data):
    mock_sb = MagicMock()
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = returned_data
    return mock_sb


def test_create_portfolio_returns_201():
    mock_sb = _insert_mock([FAKE_PORTFOLIO])
    with patch("api.routes.portfolios.get_user_client", return_value=mock_sb):
        resp = client.post(
            "/api/portfolios",
            json={"name": "My Portfolio", "tickers": ["AAPL"], "weights": [1.0]},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "My Portfolio"
    assert body["id"] == "port-abc"
    mock_sb.table.return_value.insert.assert_called_once_with({
        "user_id": "user-123",
        "name": "My Portfolio",
        "tickers": ["AAPL"],
        "weights": [1.0],
    })


def test_create_portfolio_rejects_mismatched_lengths():
    resp = client.post(
        "/api/portfolios",
        json={"name": "Bad", "tickers": ["AAPL", "MSFT"], "weights": [1.0]},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 422


def test_create_portfolio_empty_holdings():
    empty = {**FAKE_PORTFOLIO, "tickers": [], "weights": []}
    with patch("api.routes.portfolios.get_user_client", return_value=_insert_mock([empty])):
        resp = client.post(
            "/api/portfolios",
            json={"name": "Empty", "tickers": [], "weights": []},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 201
    assert resp.json()["tickers"] == []


def _update_mock(returned_data):
    mock_sb = MagicMock()
    mock_sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = returned_data
    return mock_sb


def test_update_portfolio_returns_200():
    updated = {**FAKE_PORTFOLIO, "name": "Renamed", "tickers": ["AAPL", "MSFT"], "weights": [0.6, 0.4]}
    with patch("api.routes.portfolios.get_user_client", return_value=_update_mock([updated])):
        resp = client.patch(
            "/api/portfolios/port-abc",
            json={"name": "Renamed", "tickers": ["AAPL", "MSFT"], "weights": [0.6, 0.4]},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"
    assert resp.json()["tickers"] == ["AAPL", "MSFT"]


def test_update_portfolio_404_when_not_found():
    with patch("api.routes.portfolios.get_user_client", return_value=_update_mock([])):
        resp = client.patch(
            "/api/portfolios/nonexistent",
            json={"name": "X", "tickers": [], "weights": []},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 404


def test_update_portfolio_clears_perf_cache():
    updated = {**FAKE_PORTFOLIO}
    fake_cache = {"port-abc": {"data": {}, "ts": 9999999999.0}}
    with patch("api.routes.portfolios.get_user_client", return_value=_update_mock([updated])), \
         patch("api.routes.portfolios._perf_cache", fake_cache):
        client.patch(
            "/api/portfolios/port-abc",
            json={"name": "My Portfolio", "tickers": ["AAPL"], "weights": [1.0]},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert "port-abc" not in fake_cache
