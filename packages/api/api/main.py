from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import covariance, portfolio, backtest, data, agent, portfolios, outputs, terminal

app = FastAPI(title="TMT Markets API", version="0.1.0")


@app.on_event("startup")
async def validate_env():
    """Warn at startup if required env vars are missing."""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    missing = []
    for key in ["GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_JWT_SECRET", "FRED_API_KEY"]:
        if not os.environ.get(key):
            missing.append(key)
    if missing:
        import warnings
        warnings.warn(
            f"Missing env vars: {', '.join(missing)}. Some endpoints will not work. "
            "Check packages/api/.env",
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
app.include_router(portfolios.router, prefix="/api")
app.include_router(outputs.router, prefix="/api")
app.include_router(terminal.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
