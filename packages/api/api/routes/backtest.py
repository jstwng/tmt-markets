from fastapi import APIRouter, HTTPException

from api.schemas.models import (
    BacktestRequest,
    BacktestResponse,
    BacktestMetrics as BacktestMetricsSchema,
    EquityCurvePoint,
)
from quant.data import fetch_prices, DataFetchError
from quant.backtest import run_backtest

router = APIRouter(tags=["backtest"])


@router.post("/backtest", response_model=BacktestResponse)
async def backtest(req: BacktestRequest):
    try:
        prices = fetch_prices(req.tickers, req.start_date, req.end_date)
    except DataFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = run_backtest(
            prices,
            weights=req.weights,
            initial_capital=req.initial_capital,
            rebalance_freq=req.rebalance_freq,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return BacktestResponse(
        equity_curve=[
            EquityCurvePoint(date=row["date"], value=row["value"])
            for _, row in result.equity_curve.iterrows()
        ],
        metrics=BacktestMetricsSchema(
            total_return=result.metrics.total_return,
            cagr=result.metrics.cagr,
            sharpe=result.metrics.sharpe,
            max_drawdown=result.metrics.max_drawdown,
            volatility=result.metrics.volatility,
        ),
    )
