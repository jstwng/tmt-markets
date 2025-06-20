"""Gemini Function Calling tool declarations and async executor."""

import asyncio
from typing import Any

from google.genai import types as genai_types

from quant.data import fetch_prices, DataFetchError
from quant.covariance import estimate_covariance, InsufficientDataError
from quant.portfolio import optimize_portfolio
from quant.backtest import run_backtest
from quant.frontier import generate_efficient_frontier

__all__ = ["TOOL_DECLARATIONS", "execute_tool"]

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
