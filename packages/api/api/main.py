from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import covariance, portfolio, backtest, data

app = FastAPI(title="TMT Markets API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(covariance.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(data.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
