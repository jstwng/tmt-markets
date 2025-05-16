from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import covariance, portfolio, backtest, data, agent

app = FastAPI(title="TMT Markets API", version="0.1.0")


@app.on_event("startup")
async def validate_env():
    """Warn at startup if GEMINI_API_KEY is missing (non-fatal)."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    if not os.environ.get("GEMINI_API_KEY"):
        import warnings
        warnings.warn(
            "GEMINI_API_KEY is not set. The /api/agent/chat endpoint will return errors. "
            "Add it to packages/api/.env",
            stacklevel=1,
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:5177"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(covariance.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(agent.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
