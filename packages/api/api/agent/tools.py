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
# Tool declarations (Gemini Function Calling schema)
# ---------------------------------------------------------------------------

TOOL_DECLARATIONS = genai_types.Tool(
    function_declarations=[
        genai_types.FunctionDeclaration(
            name="fetch_prices",
            description=(
                "Fetch historical adjusted close prices for a list of tickers. "
                "Use this first before any portfolio analysis."
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
                "Estimate the annualized covariance matrix of asset returns. "
                "Returns a matrix and tickers list. Use ledoit_wolf by default."
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
                "Query any financial market data via OpenBB Platform. Use this for data requests "
                "NOT covered by the other tools: options chains, earnings, income statements, "
                "macro indicators, ETF holdings, short interest, institutional flows, SEC filings, "
                "economic data (CPI, GDP, unemployment), crypto prices, forex rates, and more. "
                "Pass a natural language description of the data needed."
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
    if name == "fetch_prices":
        return await asyncio.to_thread(_run_fetch_prices, args)
    elif name == "estimate_covariance":
        return await asyncio.to_thread(_run_estimate_covariance, args)
    elif name == "optimize_portfolio":
        return await asyncio.to_thread(_run_optimize_portfolio, args)
    elif name == "run_backtest":
        return await asyncio.to_thread(_run_backtest, args)
    elif name == "generate_efficient_frontier":
        return await asyncio.to_thread(_run_generate_frontier, args)
    else:
        raise ValueError(f"Unknown tool: {name}")


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
    prices = fetch_prices(
        tickers=args["tickers"],
        start_date=args["start_date"],
        end_date=args["end_date"],
    )
    return {
        "dates": [str(d.date()) for d in prices.index],
        "tickers": list(prices.columns),
        "prices": {col: prices[col].tolist() for col in prices.columns},
    }


def _run_estimate_covariance(args: dict[str, Any]) -> dict[str, Any]:
    prices = fetch_prices(
        tickers=args["tickers"],
        start_date=args["start_date"],
        end_date=args["end_date"],
    )
    result = estimate_covariance(prices, method=args.get("method", "ledoit_wolf"))
    return {
        "matrix": result.matrix.tolist(),
        "tickers": result.tickers,
        "method": result.method,
    }


def _run_optimize_portfolio(args: dict[str, Any]) -> dict[str, Any]:
    prices = fetch_prices(
        tickers=args["tickers"],
        start_date=args["start_date"],
        end_date=args["end_date"],
    )
    result = optimize_portfolio(
        prices,
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
    prices = fetch_prices(
        tickers=args["tickers"],
        start_date=args["start_date"],
        end_date=args["end_date"],
    )
    result = run_backtest(
        prices,
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


def _run_generate_frontier(args: dict[str, Any]) -> dict[str, Any]:
    prices = fetch_prices(
        tickers=args["tickers"],
        start_date=args["start_date"],
        end_date=args["end_date"],
    )
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
