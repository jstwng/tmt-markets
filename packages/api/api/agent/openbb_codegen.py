"""Gemini-powered code generation for OpenBB queries and chart manifests."""

import json
from typing import Any

from api.agent.llm import call_llm_text

__all__ = ["generate_openbb_code", "generate_chart_manifest"]

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

CODEGEN_SYSTEM_PROMPT = """\
You are an OpenBB Python expression generator. Given a natural language description
of financial data needed, output ONE LINE ONLY — the OpenBB call expression.

Rules:
- Output exactly one line: the OpenBB function call expression
- Do NOT write def fetch(), imports, assignments, or comments
- Do NOT call .to_df(), .to_dict(), or any serialization method
- The `obb` client is pre-injected. Do not reference it as anything else.
- Use hardcoded date strings (YYYY-MM-DD format) — no datetime math
- Always specify provider="yfinance" for equity/price calls unless another provider is more appropriate

Examples of valid output (one line each):
obb.equity.price.historical("NVDA", start_date="2023-01-01", end_date="2026-01-01", provider="yfinance")
obb.equity.fundamental.income("AAPL", provider="yfinance")
obb.derivatives.options.chains("TSLA", provider="cboe")
obb.economy.fred_series(symbol="GDP")
obb.etf.holdings("SPY", provider="yfinance")
obb.equity.fundamental.metrics("MSFT", provider="yfinance")
obb.equity.price.historical(["NVDA", "AMD"], start_date="2023-01-01", end_date="2026-01-01", provider="yfinance")

Do NOT use these — they do not exist or do not work:
- obb.news.* (any path under obb.news)
- Any call for news articles, transcripts, summaries, or qualitative text
- Any call with provider="fmp" for news or text content

Return ONLY the expression. No explanation, no markdown, no function definition.
"""

MANIFEST_SYSTEM_PROMPT = """\
You are a chart manifest generator. Given financial data and the query that \
produced it, output a JSON object describing how to visualize the data.

Available chart_type values:
- "time_series": for price history, macro series, equity curves
- "candlestick": for OHLCV data
- "heatmap": for correlation/covariance matrices
- "bar": for categorical comparisons (earnings, weights)
- "table": for tabular data (options chains, holdings, filings)
- "scatter": for X/Y plots (efficient frontier, factor regression)
- "area": for stacked attribution, drawdown fills
- "histogram": for return distributions, Monte Carlo terminal wealth
- "waterfall": for performance attribution breakdowns
- "fan": for Monte Carlo projection cones (percentile bands)
- "pie": for portfolio allocation, sector composition

Required JSON schema:
{
  "chart_type": "<one of the above>",
  "title": "<descriptive title>",
  "subtitle": "<optional context>",
  "data": { ... },
  "x_axis": {"label": "<axis label>", "type": "date|category|numeric"},
  "y_axis": {"label": "<axis label>", "type": "numeric|percent|currency"},
  "annotations": [{"type": "line|band|point", "value": <num>, "label": "<text>", "color": "<hex>"}],
  "source": {"query": "<original query>", "openbb_call": "<generated code>", "timestamp": "<ISO 8601>"}
}

Data shape must match the chart_type. Examples:
- time_series: {"series": [{"name": "AAPL", "values": [{"date": "2024-01-01", "value": 150}]}]}
- candlestick: {"candles": [{"date": "...", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 1000}]}
- heatmap: {"rows": ["A","B"], "cols": ["A","B"], "matrix": [[1, 0.5],[0.5, 1]]}
- bar: {"categories": ["Q1","Q2"], "series": [{"name": "Revenue", "values": [100, 120]}]}
- table: {"columns": [{"key": "ticker", "label": "Ticker"}], "rows": [{"ticker": "AAPL"}]}
- scatter: {"series": [{"name": "frontier", "points": [{"x": 0.1, "y": 0.08, "label": "Portfolio 1"}]}]}
- area: {"series": [{"name": "alloc", "values": [{"date": "2024-01-01", "value": 0.02}]}], "stacked": true}
- histogram: {"bins": [{"range": [-0.03, -0.02], "count": 5}]}
- waterfall: {"items": [{"label": "Start", "value": 100, "type": "absolute"}, {"label": "Growth", "value": 20, "type": "delta"}]}
- fan: {"dates": ["2024-01","2024-06"], "percentiles": [{"p": 10, "values": [100, 90]}, {"p": 50, "values": [100, 110]}]}
- pie: {"slices": [{"label": "AAPL", "value": 0.4}, {"label": "MSFT", "value": 0.6}]}

Visual preference: Always prefer a visual chart_type over a table.
Use "time_series" for price/macro series, "candlestick" for OHLCV data (has open/high/low/close columns),
"bar" for earnings/comparisons, "pie" for allocations/compositions.
Only use "table" if the data is genuinely tabular with no sensible visual encoding.

Return ONLY valid JSON. No markdown fences, no explanation.
"""

# ---------------------------------------------------------------------------
# Internal callers (Gemini primary, OpenAI fallback via call_llm_text)
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    """Remove markdown code fences that LLMs sometimes add despite instructions."""
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines)
    return text.strip()


async def _call_codegen(prompt: str) -> str:
    """Generate a single-line OpenBB expression. Falls back to OpenAI on Gemini quota."""
    text = await call_llm_text(CODEGEN_SYSTEM_PROMPT, prompt, temperature=0.0, max_tokens=2048)
    text = _strip_fences(text)
    # Return only the first non-empty line
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return text


async def _call_manifest(prompt: str) -> str:
    """Generate a chart manifest JSON. Falls back to OpenAI on Gemini quota."""
    text = await call_llm_text(MANIFEST_SYSTEM_PROMPT, prompt, temperature=0.0, max_tokens=4096)
    return _strip_fences(text)


# ---------------------------------------------------------------------------
# Shape detection
# ---------------------------------------------------------------------------

def _detect_shape_hint(data) -> str:
    """Detect the likely shape of data to hint the manifest generator."""
    if not isinstance(data, list) or len(data) == 0:
        return "unknown"
    first = data[0] if isinstance(data[0], dict) else {}
    keys = set(str(k).lower() for k in first.keys())
    if {"open", "high", "low", "close"}.issubset(keys):
        return "OHLCV price data — consider candlestick"
    date_keys = {"date", "period", "timestamp", "datetime", "time"}
    if date_keys & keys and len(keys) <= 6:
        return "time series — consider time_series"
    if {"name", "value"}.issubset(keys) or {"label", "value"}.issubset(keys):
        return "categorical — consider bar or pie"
    if {"symbol", "strike", "expiration"}.issubset(keys):
        return "options data — consider table"
    return "tabular data"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_openbb_code(
    description: str,
    error_context: str | None = None,
) -> str:
    """Generate OpenBB Python code from a natural language description.

    Args:
        description: What data the user wants.
        error_context: If retrying, the error from the previous attempt.

    Returns:
        Python source code string containing a fetch() function.
    """
    prompt = f"Data request: {description}"
    if error_context:
        prompt += f"\n\nPrevious attempt failed with this error:\n{error_context}\nPlease fix the code."
    return await _call_codegen(prompt)


async def generate_chart_manifest(
    description: str,
    data: Any,
    code: str,
) -> dict:
    """Generate a ChartManifest JSON from query results.

    Args:
        description: Original natural language query.
        data: The data returned by the OpenBB code execution.
        code: The Python code that produced the data.

    Returns:
        Parsed ChartManifest dict.

    Raises:
        ValueError: If Gemini returns invalid JSON.
    """
    from datetime import datetime as dt

    # Truncate to 100 records to keep JSON valid and show full record structure
    data_preview = data[:100] if isinstance(data, list) else data
    data_str = json.dumps(data_preview, default=str)

    shape_hint = _detect_shape_hint(data_preview)

    prompt = (
        f"Query: {description}\n\n"
        f"Generated code:\n{code}\n\n"
        f"Data shape hint: {shape_hint}\n\n"
        f"Data returned:\n{data_str}\n\n"
        f"Current timestamp: {dt.utcnow().isoformat()}Z"
    )

    raw = await _call_manifest(prompt)

    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse chart manifest JSON: {e}\nRaw response: {raw[:500]}")

    # Inject source metadata
    manifest.setdefault("source", {})
    manifest["source"]["query"] = description
    manifest["source"]["openbb_call"] = code
    manifest["source"].setdefault("timestamp", dt.utcnow().isoformat() + "Z")

    return manifest
