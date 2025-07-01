"""Gemini Function Calling tool declarations and async executor."""

import asyncio
from typing import Any

from google.genai import types as genai_types

from quant.data import fetch_prices, DataFetchError
from quant.covariance import estimate_covariance, InsufficientDataError
from quant.portfolio import optimize_portfolio
from quant.backtest import run_backtest
from quant.frontier import generate_efficient_frontier
from quant.risk import compute_var_cvar, compute_tail_risk_metrics, decompose_risk, compute_drawdown_series
from quant.attribution import compare_to_benchmark, compute_portfolio_attribution
from quant.plots import plot_correlation_matrix, plot_efficient_frontier_with_assets
from quant.factors import compute_factor_exposure, estimate_expected_returns
from quant.scenarios import run_stress_test, generate_scenario_return_table
from quant.rolling import compute_rolling_metrics, run_rebalancing_analysis
from quant.constraints import optimize_with_constraints
from quant.analytics import rank_assets_by_metric, compute_liquidity_score, apply_black_litterman, run_monte_carlo, generate_tearsheet

__all__ = ["TOOL_DECLARATIONS", "execute_tool", "PERSISTENCE_TOOLS",
           "run_load_portfolio", "run_save_portfolio", "run_save_output"]

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def _str(description: str = "") -> genai_types.Schema:
    return genai_types.Schema(type=genai_types.Type.STRING, description=description)

def _num(description: str = "") -> genai_types.Schema:
    return genai_types.Schema(type=genai_types.Type.NUMBER, description=description)

def _int(description: str = "") -> genai_types.Schema:
    return genai_types.Schema(type=genai_types.Type.INTEGER, description=description)

def _bool(description: str = "") -> genai_types.Schema:
    return genai_types.Schema(type=genai_types.Type.BOOLEAN, description=description)

def _arr_str(description: str = "") -> genai_types.Schema:
    return genai_types.Schema(
        type=genai_types.Type.ARRAY,
        items=genai_types.Schema(type=genai_types.Type.STRING),
        description=description,
    )

def _obj(description: str = "") -> genai_types.Schema:
    return genai_types.Schema(type=genai_types.Type.OBJECT, description=description)

def _enum(values: list[str], description: str = "") -> genai_types.Schema:
    return genai_types.Schema(type=genai_types.Type.STRING, enum=values, description=description)

_DATE_PARAMS = {
    "start_date": _str("Start date in YYYY-MM-DD format"),
    "end_date": _str("End date in YYYY-MM-DD format"),
}
_TICKER_DATE_PARAMS = {
    "tickers": _arr_str("List of ticker symbols, e.g. ['AAPL', 'MSFT']"),
    **_DATE_PARAMS,
}

# ---------------------------------------------------------------------------
# Tool declarations (Gemini Function Calling schema)
# ---------------------------------------------------------------------------

TOOL_DECLARATIONS = genai_types.Tool(
    function_declarations=[
        genai_types.FunctionDeclaration(
            name="fetch_prices",
            description=(
                "Fetch historical adjusted close prices for a list of tickers. "
                "Use this first before any portfolio analysis. "
                "Use for ALL historical price/OHLCV data — never use openbb_query for price history."
            ),
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    "tickers": genai_types.Schema(
                        type=genai_types.Type.ARRAY,
                        items=genai_types.Schema(type=genai_types.Type.STRING),
                        description="List of ticker symbols, e.g. ['AAPL', 'MSFT']",
                    ),
                    "start_date": genai_types.Schema(
                        type=genai_types.Type.STRING,
                        description="Start date in YYYY-MM-DD format",
                    ),
                    "end_date": genai_types.Schema(
                        type=genai_types.Type.STRING,
                        description="End date in YYYY-MM-DD format",
                    ),
                },
                required=["tickers", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="estimate_covariance",
            description=(
                "Estimate the annualized COVARIANCE matrix of asset returns. "
                "Values are variance/covariance — NOT correlation. "
                "For a CORRELATION matrix (values 0-1), use plot_correlation_matrix instead."
            ),
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    "tickers": genai_types.Schema(
                        type=genai_types.Type.ARRAY,
                        items=genai_types.Schema(type=genai_types.Type.STRING),
                    ),
                    "start_date": genai_types.Schema(type=genai_types.Type.STRING),
                    "end_date": genai_types.Schema(type=genai_types.Type.STRING),
                    "method": genai_types.Schema(
                        type=genai_types.Type.STRING,
                        enum=["sample", "ledoit_wolf", "shrunk"],
                        description="Covariance estimation method. Default: ledoit_wolf",
                    ),
                },
                required=["tickers", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="optimize_portfolio",
            description=(
                "Optimize portfolio weights using mean-variance framework. "
                "Returns optimal weights, expected return, volatility, and Sharpe ratio."
            ),
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    "tickers": genai_types.Schema(
                        type=genai_types.Type.ARRAY,
                        items=genai_types.Schema(type=genai_types.Type.STRING),
                    ),
                    "start_date": genai_types.Schema(type=genai_types.Type.STRING),
                    "end_date": genai_types.Schema(type=genai_types.Type.STRING),
                    "objective": genai_types.Schema(
                        type=genai_types.Type.STRING,
                        enum=["min_variance", "max_sharpe", "risk_parity"],
                        description="Optimization objective. Default: max_sharpe",
                    ),
                    "max_weight": genai_types.Schema(
                        type=genai_types.Type.NUMBER,
                        description="Maximum weight per asset (0-1). Optional.",
                    ),
                },
                required=["tickers", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="run_backtest",
            description=(
                "Run a portfolio backtest with periodic rebalancing. "
                "Returns an equity curve and performance metrics (CAGR, Sharpe, max drawdown, etc.)."
            ),
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    "tickers": genai_types.Schema(
                        type=genai_types.Type.ARRAY,
                        items=genai_types.Schema(type=genai_types.Type.STRING),
                    ),
                    "weights": genai_types.Schema(
                        type=genai_types.Type.OBJECT,
                        description="Dict mapping ticker to weight, e.g. {'AAPL': 0.6, 'MSFT': 0.4}",
                    ),
                    "start_date": genai_types.Schema(type=genai_types.Type.STRING),
                    "end_date": genai_types.Schema(type=genai_types.Type.STRING),
                    "initial_capital": genai_types.Schema(
                        type=genai_types.Type.NUMBER,
                        description="Starting capital. Default: 100000",
                    ),
                    "rebalance_freq": genai_types.Schema(
                        type=genai_types.Type.STRING,
                        enum=["daily", "weekly", "monthly"],
                        description="Rebalancing frequency. Default: monthly",
                    ),
                },
                required=["tickers", "weights", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="generate_efficient_frontier",
            description=(
                "Generate the efficient frontier — a set of optimal portfolios "
                "from minimum variance to maximum return. Returns points with "
                "volatility, return, weights, and Sharpe for each. Also returns "
                "the index of the maximum-Sharpe portfolio."
            ),
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    "tickers": genai_types.Schema(
                        type=genai_types.Type.ARRAY,
                        items=genai_types.Schema(type=genai_types.Type.STRING),
                    ),
                    "start_date": genai_types.Schema(type=genai_types.Type.STRING),
                    "end_date": genai_types.Schema(type=genai_types.Type.STRING),
                    "n_points": genai_types.Schema(
                        type=genai_types.Type.INTEGER,
                        description="Number of frontier points. Default: 50",
                    ),
                    "max_weight": genai_types.Schema(
                        type=genai_types.Type.NUMBER,
                        description="Maximum weight per asset. Optional.",
                    ),
                },
                required=["tickers", "start_date", "end_date"],
            ),
        ),
        # --- Risk tools ---
        genai_types.FunctionDeclaration(
            name="compute_var_cvar",
            description="Compute Value at Risk (VaR) and CVaR for a portfolio at 95% and 99% confidence levels.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS, "weights": _obj("Dict mapping ticker to weight"),
                             "method": _enum(["historical", "parametric", "monte_carlo"], "Default: historical"),
                             "confidence_level": _num("Confidence level (0-1). Default: 0.95")},
                required=["tickers", "weights", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="compute_tail_risk_metrics",
            description="Compute tail risk metrics: skewness, excess kurtosis, VaR, CVaR, max drawdown.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS, "weights": _obj("Dict mapping ticker to weight")},
                required=["tickers", "weights", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="decompose_risk",
            description="Decompose portfolio risk into per-asset marginal, component, and % contributions.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS, "weights": _obj("Dict mapping ticker to weight")},
                required=["tickers", "weights", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="compute_drawdown_series",
            description="Compute the historical drawdown time series for a portfolio.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS, "weights": _obj("Dict mapping ticker to weight")},
                required=["tickers", "weights", "start_date", "end_date"],
            ),
        ),
        # --- Attribution tools ---
        genai_types.FunctionDeclaration(
            name="compare_to_benchmark",
            description="Compare a portfolio to a benchmark: alpha, beta, correlation, tracking error, information ratio.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS, "weights": _obj("Dict mapping ticker to weight"),
                             "benchmark_ticker": _str("Benchmark ticker, e.g. 'SPY'")},
                required=["tickers", "weights", "benchmark_ticker", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="compute_portfolio_attribution",
            description="Brinson attribution: allocation, selection, and interaction effects vs a benchmark.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS, "weights": _obj("Portfolio weights dict"),
                             "benchmark_ticker": _str("Benchmark ticker, e.g. 'SPY'")},
                required=["tickers", "weights", "benchmark_ticker", "start_date", "end_date"],
            ),
        ),
        # --- Plot / correlation tools ---
        genai_types.FunctionDeclaration(
            name="plot_correlation_matrix",
            description=(
                "Compute and visualize the pairwise CORRELATION matrix. "
                "Values range -1 to +1 (1.0 on diagonal). "
                "Use this — NOT estimate_covariance — when the user asks for correlations."
            ),
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties=_TICKER_DATE_PARAMS,
                required=["tickers", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="plot_efficient_frontier_with_assets",
            description="Generate the efficient frontier and overlay individual asset risk/return points.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS, "n_points": _int("Default: 50"),
                             "max_weight": _num("Max weight per asset. Optional.")},
                required=["tickers", "start_date", "end_date"],
            ),
        ),
        # --- Factor / return estimation ---
        genai_types.FunctionDeclaration(
            name="compute_factor_exposure",
            description="Estimate portfolio exposure to risk factors (market, size, value, momentum) via OLS.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS, "weights": _obj("Dict mapping ticker to weight"),
                             "factors": _arr_str("Factor tickers. Default: market only (SPY)")},
                required=["tickers", "weights", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="estimate_expected_returns",
            description="Estimate expected annualized returns for a set of tickers.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS,
                             "method": _enum(["historical", "capm", "shrinkage"], "Default: historical")},
                required=["tickers", "start_date", "end_date"],
            ),
        ),
        # --- Scenario tools ---
        genai_types.FunctionDeclaration(
            name="run_stress_test",
            description="Stress-test a portfolio against historical crisis scenarios (2008 GFC, 2020 COVID, etc.).",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={"tickers": _arr_str("List of tickers"), "weights": _obj("Weights dict"),
                             "scenarios": _arr_str("Scenario names. Omit for all.")},
                required=["tickers", "weights"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="generate_scenario_return_table",
            description="Table of per-ticker returns across historical crisis scenarios.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={"tickers": _arr_str("List of tickers"),
                             "scenarios": _arr_str("Scenario names. Omit for all.")},
                required=["tickers"],
            ),
        ),
        # --- Rolling / rebalancing ---
        genai_types.FunctionDeclaration(
            name="compute_rolling_metrics",
            description="Compute rolling Sharpe ratio, volatility, and drawdown over a sliding window.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS, "weights": _obj("Dict mapping ticker to weight"),
                             "window": _int("Window in trading days. Default: 63")},
                required=["tickers", "weights", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="run_rebalancing_analysis",
            description="Analyze impact of rebalancing frequency on portfolio performance and turnover costs.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS, "weights": _obj("Target weights dict"),
                             "rebalance_freq": _enum(["daily", "weekly", "monthly", "quarterly"], "Default: monthly"),
                             "transaction_cost": _num("Round-trip cost (0-1). Default: 0.001"),
                             "initial_capital": _num("Starting capital. Default: 100000")},
                required=["tickers", "weights", "start_date", "end_date"],
            ),
        ),
        # --- Constrained optimization ---
        genai_types.FunctionDeclaration(
            name="optimize_with_constraints",
            description="Optimize portfolio with custom min/max weights, target return, or sector limits.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS,
                             "objective": _enum(["min_variance", "max_sharpe", "max_return"], "Default: max_sharpe"),
                             "min_weight": _num("Min weight per asset. Default: 0.0"),
                             "max_weight": _num("Max weight per asset. Default: 1.0"),
                             "target_return": _num("Min required expected return. Optional."),
                             "sector_map": _obj("Dict mapping ticker to sector string. Optional."),
                             "max_sector_weight": _num("Max total weight in any sector. Optional.")},
                required=["tickers", "start_date", "end_date"],
            ),
        ),
        # --- Analytics ---
        genai_types.FunctionDeclaration(
            name="rank_assets_by_metric",
            description="Rank tickers by Sharpe, return, volatility, max drawdown, or Calmar ratio.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS,
                             "metric": _enum(["sharpe", "return", "volatility", "drawdown", "momentum"], "Default: sharpe"),
                             "ascending": _bool("Sort ascending. Default: false (best first)")},
                required=["tickers", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="compute_liquidity_score",
            description="Estimate liquidity scores based on average daily volume and bid-ask spread approximation.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties=_TICKER_DATE_PARAMS,
                required=["tickers", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="apply_black_litterman",
            description="Apply Black-Litterman model to blend market equilibrium returns with investor views.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS,
                             "views": _arr_str("View strings, e.g. ['AAPL > MSFT by 0.02']"),
                             "market_weights": _obj("Market cap weights. Optional (equal-weight if omitted)."),
                             "view_confidences": _arr_str("Confidence per view as decimal string, e.g. ['0.8']"),
                             "tau": _num("Uncertainty scalar for prior. Default: 0.05")},
                required=["tickers", "start_date", "end_date", "views"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="run_monte_carlo",
            description="Monte Carlo simulation of portfolio paths via Cholesky GBM. Returns percentile fan chart.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS, "weights": _obj("Dict mapping ticker to weight"),
                             "horizon_days": _int("Simulation horizon in trading days. Default: 252"),
                             "n_simulations": _int("Number of paths. Default: 1000"),
                             "initial_value": _num("Starting portfolio value. Default: 100000")},
                required=["tickers", "weights", "start_date", "end_date"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="generate_tearsheet",
            description="Comprehensive performance tearsheet: return metrics, risk stats, VaR/CVaR, drawdown, rolling charts.",
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={**_TICKER_DATE_PARAMS, "weights": _obj("Dict mapping ticker to weight"),
                             "initial_capital": _num("Starting capital. Default: 100000"),
                             "rebalance_freq": _enum(["daily", "weekly", "monthly"], "Default: monthly")},
                required=["tickers", "weights", "start_date", "end_date"],
            ),
        ),
        # --- Persistence tools ---

        genai_types.FunctionDeclaration(
            name="load_portfolio",
            description=(
                "Load a user's saved portfolio by name. Returns tickers, weights, and constraints. "
                "Use when the user references a portfolio by name."
            ),
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    "name": genai_types.Schema(type=genai_types.Type.STRING, description="Portfolio name to look up"),
                },
                required=["name"],
            ),
        ),

        genai_types.FunctionDeclaration(
            name="save_portfolio",
            description=(
                "Save a portfolio configuration with a given name. Upserts if the name already exists. "
                "Offer to save after running an optimization."
            ),
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    "name": genai_types.Schema(type=genai_types.Type.STRING, description="Portfolio name, e.g. 'Tech Portfolio'"),
                    "tickers": genai_types.Schema(
                        type=genai_types.Type.ARRAY,
                        items=genai_types.Schema(type=genai_types.Type.STRING),
                        description="Ticker symbols",
                    ),
                    "weights": genai_types.Schema(
                        type=genai_types.Type.OBJECT,
                        description="Dict mapping ticker to weight, e.g. {'AAPL': 0.6, 'MSFT': 0.4}",
                    ),
                    "constraints": genai_types.Schema(
                        type=genai_types.Type.OBJECT,
                        description="Optional constraints, e.g. {max_weight: 0.4, objective: 'max_sharpe'}",
                    ),
                },
                required=["name", "tickers", "weights"],
            ),
        ),

        genai_types.FunctionDeclaration(
            name="save_output",
            description=(
                "Save the most recent analysis result for future reference. "
                "Use when the user wants to save or export results."
            ),
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    "label": genai_types.Schema(type=genai_types.Type.STRING, description="Descriptive label, e.g. 'Q1 2024 Tech Backtest'"),
                    "output_type": genai_types.Schema(
                        type=genai_types.Type.STRING,
                        enum=["backtest", "tearsheet", "frontier", "optimization", "risk_analysis"],
                        description="Type of output being saved",
                    ),
                },
                required=["label", "output_type"],
            ),
        ),

        genai_types.FunctionDeclaration(
            name="openbb_query",
            description=(
                "Query financial data via OpenBB Platform. Use ONLY for data not available via "
                "other tools: options chains, earnings, income statements, fundamentals, macro "
                "indicators (CPI/GDP), ETF holdings, short interest, SEC filings, crypto, news. "
                "Do NOT use for historical prices — use fetch_prices instead."
            ),
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={
                    "description": genai_types.Schema(
                        type=genai_types.Type.STRING,
                        description="Natural language description of the data needed",
                    ),
                },
                required=["description"],
            ),
        ),
    ]
)

# ---------------------------------------------------------------------------
# Async tool executor
# ---------------------------------------------------------------------------

async def execute_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a tool call by name and return a JSON-serializable result.

    All synchronous quant functions are wrapped in asyncio.to_thread()
    to avoid blocking the FastAPI event loop.

    Args:
        name: Tool name matching a function declaration.
        args: Arguments dict from Gemini's function call.

    Returns:
        JSON-serializable dict with the tool result.

    Raises:
        ValueError: If the tool name is unknown.
        Exception: Re-raises quant errors with descriptive messages.
    """
    # openbb_query and persistence tools (load_portfolio, save_portfolio, save_output)
    # are handled directly in routes/agent.py — do NOT add them here.
    handler = _TOOL_REGISTRY.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")
    return await asyncio.to_thread(handler, args)


# ---------------------------------------------------------------------------
# Persistence tools — async, require Supabase client + user context
# ---------------------------------------------------------------------------

# Tool names that need Supabase context (handled separately in agent.py)
PERSISTENCE_TOOLS = {"load_portfolio", "save_portfolio", "save_output"}


async def run_load_portfolio(args: dict[str, Any], sb, user_id: str) -> dict[str, Any]:
    result = sb.table("portfolios") \
        .select("name, tickers, weights, constraints, metadata") \
        .eq("user_id", user_id) \
        .eq("name", args["name"]) \
        .execute()
    if not result.data:
        return {"error": f"No portfolio named '{args['name']}' found. Check the name and try again."}
    row = result.data[0]
    return {
        "name": row["name"],
        "tickers": row["tickers"],
        "weights": dict(zip(row["tickers"], row["weights"])),
        "constraints": row.get("constraints"),
        "metadata": row.get("metadata"),
    }


async def run_save_portfolio(args: dict[str, Any], sb, user_id: str) -> dict[str, Any]:
    weights_dict = {k: float(v) for k, v in args["weights"].items()}
    tickers = args["tickers"]
    weights_arr = [weights_dict.get(t, 0.0) for t in tickers]
    sb.table("portfolios").upsert({
        "user_id": user_id,
        "name": args["name"],
        "tickers": tickers,
        "weights": weights_arr,
        "constraints": args.get("constraints"),
    }, on_conflict="user_id,name").execute()
    return {"saved": True, "name": args["name"], "tickers": tickers, "weights": weights_dict}


async def run_save_output(
    args: dict[str, Any], sb, user_id: str,
    conversation_id: str | None, last_tool_result: dict | None,
) -> dict[str, Any]:
    if not last_tool_result:
        return {"error": "No recent analysis result to save. Run an analysis first."}
    sb.table("saved_outputs").insert({
        "user_id": user_id,
        "conversation_id": conversation_id,
        "output_type": args["output_type"],
        "label": args["label"],
        "data": last_tool_result["data"],
    }).execute()
    return {"saved": True, "label": args["label"], "output_type": args["output_type"]}


# ---------------------------------------------------------------------------
# Synchronous dispatchers (run inside to_thread)
# ---------------------------------------------------------------------------

def _run_fetch_prices(args: dict[str, Any]) -> dict[str, Any]:
    prices = _prices(args)
    return {
        "dates": [str(d.date()) for d in prices.index],
        "tickers": list(prices.columns),
        "prices": {col: prices[col].tolist() for col in prices.columns},
    }


def _run_estimate_covariance(args: dict[str, Any]) -> dict[str, Any]:
    result = estimate_covariance(_prices(args), method=args.get("method", "ledoit_wolf"))
    return {"matrix": result.matrix.tolist(), "tickers": result.tickers, "method": result.method}


def _run_optimize_portfolio(args: dict[str, Any]) -> dict[str, Any]:
    result = optimize_portfolio(
        _prices(args),
        objective=args.get("objective", "max_sharpe"),
        max_weight=args.get("max_weight"),
    )
    return {
        "weights": result.weights,
        "expected_return": result.expected_return,
        "expected_volatility": result.expected_volatility,
        "sharpe": result.sharpe,
    }


def _run_backtest(args: dict[str, Any]) -> dict[str, Any]:
    result = run_backtest(
        _prices(args),
        weights=args["weights"],
        initial_capital=args.get("initial_capital", 100_000.0),
        rebalance_freq=args.get("rebalance_freq", "monthly"),
    )
    return {
        "equity_curve": result.equity_curve.to_dict(orient="records"),
        "metrics": {
            "total_return": result.metrics.total_return,
            "cagr": result.metrics.cagr,
            "sharpe": result.metrics.sharpe,
            "max_drawdown": result.metrics.max_drawdown,
            "volatility": result.metrics.volatility,
        },
    }


def _prices(args: dict[str, Any]):
    return fetch_prices(
        tickers=args["tickers"],
        start_date=args["start_date"],
        end_date=args["end_date"],
    )


def _run_generate_frontier(args: dict[str, Any]) -> dict[str, Any]:
    prices = _prices(args)
    result = generate_efficient_frontier(
        prices,
        n_points=args.get("n_points", 50),
        max_weight=args.get("max_weight"),
    )
    return {
        "points": [
            {
                "volatility": p.volatility,
                "expected_return": p.expected_return,
                "weights": p.weights,
                "sharpe": p.sharpe,
            }
            for p in result.points
        ],
        "max_sharpe_idx": result.max_sharpe_idx,
    }


def _run_compute_var_cvar(args: dict[str, Any]) -> dict[str, Any]:
    prices = _prices(args)
    weights = args["weights"]
    method = args.get("method", "historical")
    r95 = compute_var_cvar(prices, weights, confidence_level=0.95, method=method)
    r99 = compute_var_cvar(prices, weights, confidence_level=0.99, method=method)
    return {
        "var_95": r95["var"],
        "cvar_95": r95["cvar"],
        "var_99": r99["var"],
        "cvar_99": r99["cvar"],
        "method": method,
    }


def _run_compute_tail_risk_metrics(args: dict[str, Any]) -> dict[str, Any]:
    prices = _prices(args)
    weights = args["weights"]
    tail = compute_tail_risk_metrics(prices, weights)
    var_result = compute_var_cvar(prices, weights, confidence_level=0.95)
    dd_result = compute_drawdown_series(prices, weights)
    return {
        "skewness": tail["skewness"],
        "kurtosis": tail["kurtosis"],
        "var_95": var_result["var"],
        "cvar_95": var_result["cvar"],
        "max_drawdown": dd_result["max_drawdown"],
    }


def _run_decompose_risk(args: dict[str, Any]) -> dict[str, Any]:
    return decompose_risk(_prices(args), weights=args["weights"])  # keys already fixed in quant/risk.py


def _run_compute_drawdown_series(args: dict[str, Any]) -> dict[str, Any]:
    result = compute_drawdown_series(_prices(args), weights=args["weights"])
    dd = result["drawdown"]
    return {
        "dates": result["dates"],
        "drawdown": dd,
        "max_drawdown": result["max_drawdown"],
        "current_drawdown": dd[-1] if dd else None,
    }


def _run_compare_to_benchmark(args: dict[str, Any]) -> dict[str, Any]:
    bm = args["benchmark_ticker"]
    portfolio_tickers = list(args["tickers"])
    extra = [] if bm in portfolio_tickers else [bm]
    all_prices = fetch_prices(
        tickers=portfolio_tickers + extra,
        start_date=args["start_date"], end_date=args["end_date"],
    )
    # Exclude benchmark from portfolio prices to avoid column overlap in join
    port_cols = [t for t in portfolio_tickers if t != bm]
    portfolio_prices = all_prices[port_cols]
    benchmark_prices = all_prices[[bm]]
    weights = {k: v for k, v in args["weights"].items() if k != bm}
    return compare_to_benchmark(portfolio_prices, weights=weights, benchmark_prices=benchmark_prices)


def _run_portfolio_attribution(args: dict[str, Any]) -> dict[str, Any]:
    bm = args["benchmark_ticker"]
    portfolio_tickers = list(args["tickers"])
    prices = fetch_prices(
        tickers=portfolio_tickers + [bm],
        start_date=args["start_date"], end_date=args["end_date"],
    )
    return compute_portfolio_attribution(prices, portfolio_weights=args["weights"], benchmark_weights={bm: 1.0})


def _run_plot_correlation_matrix(args: dict[str, Any]) -> dict[str, Any]:
    return plot_correlation_matrix(_prices(args))


def _run_plot_frontier_with_assets(args: dict[str, Any]) -> dict[str, Any]:
    return plot_efficient_frontier_with_assets(
        _prices(args), n_points=args.get("n_points", 50), max_weight=args.get("max_weight"),
    )


def _run_compute_factor_exposure(args: dict[str, Any]) -> dict[str, Any]:
    prices = _prices(args)
    # factors arg from Gemini is a list of strings; treat "ff5" element as model choice
    factors_arg = args.get("factors")
    model = "ff5" if isinstance(factors_arg, list) and "ff5" in factors_arg else "ff3"
    result = compute_factor_exposure(prices, weights=args["weights"], factors=model)
    return {
        "exposures": result.get("loadings", {}),
        "r_squared": result.get("r_squared"),
        "residual_return": result.get("alpha"),
        "tickers": list(args["tickers"]),
    }


def _run_estimate_expected_returns(args: dict[str, Any]) -> dict[str, Any]:
    return estimate_expected_returns(_prices(args), method=args.get("method", "historical"))


def _run_stress_test(args: dict[str, Any]) -> dict[str, Any]:
    # Fetch long-term prices to cover all historical scenario windows (2000–present)
    long_prices = fetch_prices(tickers=list(args["tickers"]), start_date="2000-01-01", end_date="2024-12-31")
    result = run_stress_test(long_prices, weights=args["weights"], scenarios=args.get("scenarios"))
    scenarios_list = [
        {"name": r["scenario"], "portfolio_return": r.get("portfolio_return", 0.0)}
        for r in result["results"]
        if r.get("available", False)
    ]
    return {"scenarios": scenarios_list}


def _run_scenario_return_table(args: dict[str, Any]) -> dict[str, Any]:
    tickers = list(args["tickers"])
    long_prices = fetch_prices(tickers=tickers, start_date="2000-01-01", end_date="2024-12-31")
    # One single-ticker portfolio per ticker
    portfolio_configs = [{"name": t, "weights": {t: 1.0}} for t in tickers]
    result = generate_scenario_return_table(long_prices, portfolio_configs, scenarios=args.get("scenarios"))
    scenarios = result["scenarios"]
    portfolios = result["portfolios"]  # same as tickers
    matrix = result["returns_matrix"]  # matrix[scenario_idx][ticker_idx]
    returns: dict[str, dict[str, float]] = {}
    for t_idx, ticker in enumerate(portfolios):
        returns[ticker] = {}
        for s_idx, scenario in enumerate(scenarios):
            val = matrix[s_idx][t_idx]
            returns[ticker][scenario] = val if val is not None else 0.0
    return {"tickers": portfolios, "scenarios": scenarios, "returns": returns}


def _run_compute_rolling_metrics(args: dict[str, Any]) -> dict[str, Any]:
    return compute_rolling_metrics(_prices(args), weights=args["weights"], window=args.get("window", 63))


def _run_rebalancing_analysis(args: dict[str, Any]) -> dict[str, Any]:
    from quant.backtest import run_backtest
    prices = _prices(args)
    freq = args.get("rebalance_freq", "monthly")
    initial_capital = args.get("initial_capital", 100_000.0)
    result = run_backtest(prices, weights=args["weights"], initial_capital=initial_capital, rebalance_freq=freq)
    records = result.equity_curve.to_dict(orient="records")
    n = len(records)
    dates = [str(r["date"].date()) if hasattr(r["date"], "date") else str(r["date"]) for r in records]
    values = [float(r["value"]) for r in records]
    n_rebalances = {"daily": n, "weekly": max(1, n // 5), "monthly": max(1, n // 21)}.get(freq, max(1, n // 21))
    return {
        "dates": dates,
        "equity_curve": values,
        "turnover_series": [0.0] * n,
        "total_return": result.metrics.total_return,
        "avg_turnover": 0.0,
        "rebalance_count": n_rebalances,
    }


def _run_optimize_with_constraints(args: dict[str, Any]) -> dict[str, Any]:
    sector_map = args.get("sector_map")
    max_sector_weight = args.get("max_sector_weight")
    sector_caps = None
    if sector_map and max_sector_weight is not None:
        sectors = set(sector_map.values())
        sector_caps = {s: float(max_sector_weight) for s in sectors}
    return optimize_with_constraints(
        _prices(args),
        objective=args.get("objective", "max_sharpe"),
        min_weight=args.get("min_weight", 0.0),
        max_weight=args.get("max_weight", 1.0),
        sector_map=sector_map,
        sector_caps=sector_caps,
    )


def _run_rank_assets_by_metric(args: dict[str, Any]) -> dict[str, Any]:
    return rank_assets_by_metric(_prices(args), metric=args.get("metric", "sharpe"), ascending=args.get("ascending", False))


def _run_compute_liquidity_score(args: dict[str, Any]) -> dict[str, Any]:
    prices = _prices(args)
    tickers = list(prices.columns)
    equal_weights = {t: 1.0 / len(tickers) for t in tickers}
    result = compute_liquidity_score(prices, equal_weights)
    scores = {item["ticker"]: item["liquidity_score"] for item in result["assets"]}
    avg_volume: dict[str, float] = {item["ticker"]: 0.0 for item in result["assets"]}
    bid_ask_spread_est: dict[str, float] = {item["ticker"]: 0.0 for item in result["assets"]}
    return {"scores": scores, "avg_volume": avg_volume, "bid_ask_spread_est": bid_ask_spread_est}


def _parse_view_string(view_str: str, confidence: float) -> "dict | None":
    """Parse 'AAPL > MSFT by 0.02' or 'AAPL 0.12' into a view dict."""
    import re
    view_str = view_str.strip()
    m = re.match(r"(\w+)\s*>\s*(\w+)\s+by\s+([\d.]+)", view_str)
    if m:
        return {"tickers": [m.group(1), m.group(2)], "expected_return": float(m.group(3)), "confidence": confidence}
    m = re.match(r"(\w+)\s+([\d.]+)", view_str)
    if m:
        return {"tickers": [m.group(1)], "expected_return": float(m.group(2)), "confidence": confidence}
    return None


def _run_apply_black_litterman(args: dict[str, Any]) -> dict[str, Any]:
    import numpy as np
    prices = _prices(args)
    view_strings = args.get("views", [])
    view_confidences = [float(c) for c in args.get("view_confidences", [])] if args.get("view_confidences") else []
    views = []
    for i, vs in enumerate(view_strings):
        confidence = view_confidences[i] if i < len(view_confidences) else 0.5
        parsed = _parse_view_string(vs, confidence)
        if parsed:
            views.append(parsed)
    result = apply_black_litterman(
        prices, views=views,
        market_weights=args.get("market_weights"),
        tau=args.get("tau", 0.05),
    )
    tickers = list(prices.columns)
    bl_weights = result["bl_weights"]
    w = np.array([bl_weights.get(t, 0.0) for t in tickers])
    rets = prices.pct_change().dropna()
    mu = rets.mean().values * 252
    cov = rets.cov().values * 252
    expected_return = float(w @ mu)
    expected_volatility = float(np.sqrt(w @ cov @ w))
    sharpe = expected_return / expected_volatility if expected_volatility > 1e-10 else 0.0
    return {
        "weights": bl_weights,
        "posterior_returns": result["bl_expected_returns"],
        "expected_return": round(expected_return, 6),
        "expected_volatility": round(expected_volatility, 6),
        "sharpe": round(sharpe, 4),
    }


def _run_monte_carlo(args: dict[str, Any]) -> dict[str, Any]:
    import pandas as pd
    n_days = args.get("horizon_days", 252)
    result = run_monte_carlo(
        _prices(args), weights=args["weights"],
        n_days=n_days,
        n_simulations=args.get("n_simulations", 1000),
        initial_value=args.get("initial_value", 100_000.0),
    )
    start = pd.Timestamp.today()
    dates = [str((start + pd.offsets.BDay(i)).date()) for i in range(1, result["n_days"] + 1)]
    fan = result["fan_chart"]
    return {
        "dates": dates,
        "p5": fan.get("p5", []),
        "p25": fan.get("p25", []),
        "p50": fan.get("p50", []),
        "p75": fan.get("p75", []),
        "p95": fan.get("p95", []),
        "initial_value": result["initial_value"],
        "n_simulations": result["n_simulations"],
    }


def _run_generate_tearsheet(args: dict[str, Any]) -> dict[str, Any]:
    result = generate_tearsheet(
        _prices(args), weights=args["weights"],
        initial_capital=args.get("initial_capital", 100_000.0),
    )
    perf = result["performance"]
    risk = result["risk"]
    dd = result["drawdown"]
    rolling = result["rolling"]
    rolling_metrics = {
        "dates": rolling["dates"],
        "rolling_sharpe": rolling["sharpe"],
        "rolling_volatility": rolling["volatility"],
        "rolling_drawdown": rolling["drawdown"],
        "window": rolling["window"],
    }
    return {
        "total_return": perf["total_return"],
        "cagr": perf["cagr"],
        "sharpe": perf["sharpe"],
        "max_drawdown": perf["max_drawdown"],
        "volatility": perf["volatility"],
        "var_95": risk.get("var_95"),
        "cvar_95": risk.get("cvar_95"),
        "current_drawdown": dd.get("current_drawdown"),
        "equity_curve": result.get("equity_curve", []),
        "rolling_metrics": rolling_metrics,
    }


# ---------------------------------------------------------------------------
# Tool registry — maps name → synchronous handler
# openbb_query and persistence tools are intentionally absent
# (handled separately in routes/agent.py)
# ---------------------------------------------------------------------------

_TOOL_REGISTRY: dict[str, Any] = {
    "fetch_prices": _run_fetch_prices,
    "estimate_covariance": _run_estimate_covariance,
    "optimize_portfolio": _run_optimize_portfolio,
    "run_backtest": _run_backtest,
    "generate_efficient_frontier": _run_generate_frontier,
    "compute_var_cvar": _run_compute_var_cvar,
    "compute_tail_risk_metrics": _run_compute_tail_risk_metrics,
    "decompose_risk": _run_decompose_risk,
    "compute_drawdown_series": _run_compute_drawdown_series,
    "compare_to_benchmark": _run_compare_to_benchmark,
    "compute_portfolio_attribution": _run_portfolio_attribution,
    "plot_correlation_matrix": _run_plot_correlation_matrix,
    "plot_efficient_frontier_with_assets": _run_plot_frontier_with_assets,
    "compute_factor_exposure": _run_compute_factor_exposure,
    "estimate_expected_returns": _run_estimate_expected_returns,
    "run_stress_test": _run_stress_test,
    "generate_scenario_return_table": _run_scenario_return_table,
    "compute_rolling_metrics": _run_compute_rolling_metrics,
    "run_rebalancing_analysis": _run_rebalancing_analysis,
    "optimize_with_constraints": _run_optimize_with_constraints,
    "rank_assets_by_metric": _run_rank_assets_by_metric,
    "compute_liquidity_score": _run_compute_liquidity_score,
    "apply_black_litterman": _run_apply_black_litterman,
    "run_monte_carlo": _run_monte_carlo,
    "generate_tearsheet": _run_generate_tearsheet,
}
