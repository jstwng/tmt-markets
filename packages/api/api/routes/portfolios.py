"""REST endpoints for portfolio CRUD and performance computation."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import get_current_user, AuthenticatedUser
from api.supabase_client import get_user_client
from quant.data import fetch_prices, DataFetchError

router = APIRouter(tags=["portfolios"])
_bearer_scheme = HTTPBearer()

# In-memory cache: portfolio_id -> {"data": ..., "ts": float}
_perf_cache: dict[str, dict[str, Any]] = {}
_CACHE_TTL_SECONDS = 900  # 15 minutes


@router.get("/portfolios")
async def list_portfolios(
    user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    sb = get_user_client(credentials.credentials)
    result = (
        sb.table("portfolios")
        .select("id, name, tickers, weights, constraints, metadata, created_at, updated_at")
        .eq("user_id", user.id)
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data


@router.delete("/portfolios/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    sb = get_user_client(credentials.credentials)
    sb.table("portfolios").delete().eq("id", portfolio_id).execute()
    return {"deleted": portfolio_id}


@router.get("/portfolio/performance")
async def portfolio_performance(
    portfolio_id: str | None = None,
    user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    """Compute portfolio equity curve, position stats, and risk metrics.

    Always returns max available history (up to 5 years). The frontend slices
    by period client-side. Results cached for 15 minutes per portfolio_id.
    """
    sb = get_user_client(credentials.credentials)

    # Load portfolio — default to most recently updated
    query = (
        sb.table("portfolios")
        .select("id, name, tickers, weights, user_id")
        .eq("user_id", user.id)
        .order("updated_at", desc=True)
    )
    if portfolio_id:
        query = query.eq("id", portfolio_id)
    result = query.limit(1).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="No portfolio found")

    portfolio = result.data[0]
    cache_key = portfolio["id"]

    # Return cached result if fresh
    cached = _perf_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < _CACHE_TTL_SECONDS:
        return cached["data"]

    tickers: list[str] = portfolio["tickers"]
    weights: list[float] = portfolio["weights"]

    if len(tickers) != len(weights):
        raise HTTPException(status_code=422, detail="tickers and weights length mismatch")

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")

    all_tickers = list(dict.fromkeys(tickers + ["SPY"]))  # deduplicate, preserve order

    try:
        prices = await asyncio.to_thread(fetch_prices, all_tickers, start_date, end_date)
    except DataFetchError as exc:
        raise HTTPException(status_code=502, detail=f"Price fetch failed: {exc}")

    # --- Equity curve ---
    available = [t for t in tickers if t in prices.columns]
    available_weights = [weights[tickers.index(t)] for t in available]
    w = np.array(available_weights)
    if w.sum() > 0:
        w = w / w.sum()  # renormalize if any tickers missing

    port_prices = prices[available]
    returns = port_prices.pct_change().dropna()
    weighted_returns = (returns * w).sum(axis=1)
    cumulative = (1 + weighted_returns).cumprod() * 100

    spy_returns = prices["SPY"].pct_change().dropna()
    spy_cumulative = (1 + spy_returns).cumprod() * 100

    # Align dates
    dates = cumulative.index.intersection(spy_cumulative.index)

    curve = [
        {
            "date": str(d.date()),
            "value": round(float(cumulative[d]), 4),
            "benchmark": round(float(spy_cumulative[d]), 4),
        }
        for d in dates
    ]

    # --- Position stats ---
    positions = []
    for ticker, weight in zip(tickers, weights):
        if ticker not in prices.columns or len(prices[ticker]) < 2:
            continue
        col = prices[ticker]
        current_price = float(col.iloc[-1])
        prev_price = float(col.iloc[-2])
        day_pct = (current_price - prev_price) / prev_price if prev_price != 0 else 0.0
        start_price = float(col.iloc[0])
        total_return = (current_price - start_price) / start_price if start_price != 0 else 0.0
        positions.append(
            {
                "ticker": ticker,
                "weight": weight,
                "price": round(current_price, 2),
                "day_pct": round(day_pct, 6),
                "total_return": round(total_return, 6),
            }
        )

    # --- Risk stats ---
    std = weighted_returns.std()
    sharpe = float(weighted_returns.mean() / std * np.sqrt(252)) if std != 0 else 0.0
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = float(drawdown.min())
    total_return = float(cumulative.iloc[-1] / 100 - 1) if len(cumulative) > 0 else 0.0
    spy_total = float(spy_cumulative[dates].iloc[-1] / 100 - 1) if len(dates) > 0 else 0.0
    alpha = total_return - spy_total

    data = {
        "curve": curve,
        "positions": positions,
        "stats": {
            "sharpe": round(sharpe, 4),
            "max_drawdown": round(max_drawdown, 4),
            "total_return": round(total_return, 4),
            "alpha": round(alpha, 4),
        },
        "portfolio_name": portfolio["name"],
    }

    _perf_cache[cache_key] = {"data": data, "ts": time.time()}
    return data
