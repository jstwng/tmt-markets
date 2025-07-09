"""Tests for GET /api/portfolio/performance."""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_current_user, AuthenticatedUser

client = TestClient(app)


def _mock_user():
    return AuthenticatedUser(id="user-123", email="test@example.com")


def _mock_prices_df(tickers: list[str], n_days: int = 252) -> pd.DataFrame:
    """Generate synthetic price DataFrame."""
    idx = pd.date_range("2023-01-01", periods=n_days, freq="B")
    data = {}
    for i, t in enumerate(tickers):
        np.random.seed(i)
        returns = np.random.normal(0.0005, 0.01, n_days)
        data[t] = 100 * np.cumprod(1 + returns)
    return pd.DataFrame(data, index=idx)


def _mock_supabase_portfolio():
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "id": "port-1",
            "name": "Tech Portfolio",
            "tickers": ["AAPL", "MSFT"],
            "weights": [0.6, 0.4],
            "user_id": "user-123",
        }
    ]
    return mock_sb


@pytest.fixture(autouse=True)
def mock_auth_and_supabase():
    # Use FastAPI dependency_overrides so the override actually takes effect
    app.dependency_overrides[get_current_user] = lambda: _mock_user()
    with patch("api.routes.portfolios.get_user_client", return_value=_mock_supabase_portfolio()), \
         patch("api.routes.portfolios._perf_cache", {}):
        yield
    app.dependency_overrides.clear()


def test_performance_returns_200():
    with patch(
        "api.routes.portfolios.fetch_prices",
        return_value=_mock_prices_df(["AAPL", "MSFT", "SPY"]),
    ):
        resp = client.get(
            "/api/portfolio/performance",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 200


def test_performance_response_shape():
    with patch(
        "api.routes.portfolios.fetch_prices",
        return_value=_mock_prices_df(["AAPL", "MSFT", "SPY"]),
    ):
        body = client.get(
            "/api/portfolio/performance",
            headers={"Authorization": "Bearer fake-token"},
        ).json()

        assert "curve" in body
        assert "positions" in body
        assert "stats" in body
        assert "portfolio_name" in body

        assert len(body["curve"]) > 0
        point = body["curve"][0]
        assert "date" in point and "value" in point and "benchmark" in point

        assert len(body["positions"]) == 2
        pos = body["positions"][0]
        for field in ("ticker", "weight", "price", "day_pct", "total_return"):
            assert field in pos

        stats = body["stats"]
        for field in ("sharpe", "max_drawdown", "total_return", "alpha"):
            assert field in stats


def test_performance_404_when_no_portfolio():
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    with patch("api.routes.portfolios.get_user_client", return_value=mock_sb):
        resp = client.get(
            "/api/portfolio/performance",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 404


def test_performance_cache_hit():
    """Second identical request should not call fetch_prices again."""
    with patch(
        "api.routes.portfolios.fetch_prices",
        return_value=_mock_prices_df(["AAPL", "MSFT", "SPY"]),
    ) as mock_fetch:
        client.get("/api/portfolio/performance", headers={"Authorization": "Bearer fake-token"})
        client.get("/api/portfolio/performance", headers={"Authorization": "Bearer fake-token"})
        assert mock_fetch.call_count == 1
