from fastapi import APIRouter, HTTPException

from api.schemas.models import PortfolioOptimizeRequest, PortfolioOptimizeResponse
from quant.data import fetch_prices, DataFetchError
from quant.portfolio import optimize_portfolio

router = APIRouter(tags=["portfolio"])


@router.post("/portfolio/optimize", response_model=PortfolioOptimizeResponse)
async def optimize(req: PortfolioOptimizeRequest):
    try:
        prices = fetch_prices(req.tickers, req.start_date, req.end_date)
    except DataFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = optimize_portfolio(
            prices,
            objective=req.objective,
            max_weight=req.max_weight,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PortfolioOptimizeResponse(
        weights=result.weights,
        expected_return=result.expected_return,
        expected_volatility=result.expected_volatility,
        sharpe=result.sharpe,
    )
