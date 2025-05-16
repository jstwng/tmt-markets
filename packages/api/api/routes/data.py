from fastapi import APIRouter, HTTPException

from api.schemas.models import PricesRequest, PricesResponse
from quant.data import fetch_prices, DataFetchError

router = APIRouter(tags=["data"])


@router.post("/data/prices", response_model=PricesResponse)
async def get_prices(req: PricesRequest):
    try:
        prices = fetch_prices(
            tickers=req.tickers,
            start_date=req.start_date,
            end_date=req.end_date,
            source=req.source,
        )
    except DataFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PricesResponse(
        dates=[str(d.date()) for d in prices.index],
        tickers=list(prices.columns),
        prices={col: prices[col].tolist() for col in prices.columns},
    )
