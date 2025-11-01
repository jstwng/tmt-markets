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
    with patch("api.routes.portfolios.get_user_client", return_value=_insert_mock([FAKE_PORTFOLIO])):
        resp = client.post(
            "/api/portfolios",
            json={"name": "My Portfolio", "tickers": ["AAPL"], "weights": [1.0]},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "My Portfolio"
    assert body["id"] == "port-abc"


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
