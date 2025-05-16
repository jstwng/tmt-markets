from fastapi import APIRouter, HTTPException

from api.schemas.models import CovarianceRequest, CovarianceResponse
from quant.data import fetch_prices, DataFetchError
from quant.covariance import estimate_covariance, InsufficientDataError

router = APIRouter(tags=["covariance"])


@router.post("/covariance", response_model=CovarianceResponse)
async def compute_covariance(req: CovarianceRequest):
    try:
        prices = fetch_prices(req.tickers, req.start_date, req.end_date)
    except DataFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = estimate_covariance(prices, method=req.method)
    except InsufficientDataError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CovarianceResponse(
        matrix=result.matrix.tolist(),
        tickers=result.tickers,
        method=result.method,
    )
