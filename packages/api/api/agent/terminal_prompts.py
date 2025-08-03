"""Fixed OpenBB codegen prompts for each Terminal panel.

Each entry has:
  system: system prompt that constrains the LLM to one-line OpenBB expressions
  user:   the specific data request prompt

The LLM returns a single OpenBB expression (no assignments, no imports).
"""

_BASE_SYSTEM = """\
You are an OpenBB Python expression generator.
Output ONE LINE ONLY — the OpenBB function call expression.

Rules:
- Output exactly one line: the OpenBB function call expression
- Do NOT write def fetch(), imports, assignments, or comments
- The `obb` client is pre-injected; do not reference it otherwise
- Use hardcoded date strings (YYYY-MM-DD) — no datetime math
- Always use provider="yfinance" for equity/ETF calls unless instructed otherwise
- Always use provider="fred" for FRED series

Return ONLY the expression. No explanation, no markdown.
"""

PANEL_PROMPTS: dict[str, dict[str, str]] = {
    "macro": {
        "system": _BASE_SYSTEM + "\nReturn a list expression using a Python list literal if needed, but prefer a single obb call.",
        "user": (
            "Fetch the last 90 days of daily data for the following FRED series as a single call: "
            "FEDFUNDS (Fed Funds Rate), DGS2 (2Y Treasury), DGS10 (10Y Treasury), CPIAUCSL (CPI), VIXCLS (VIX). "
            "Use: obb.economy.fred_series(symbol=['FEDFUNDS','DGS2','DGS10','CPIAUCSL','VIXCLS'], provider='fred')"
        ),
    },
    "indices": {
        "system": _BASE_SYSTEM,
        "user": (
            "Fetch the last 10 days of daily price history for these tickers: "
            "SPY, QQQ, IWM, DIA, XLK, XLF, XLE, XLV, XLY, XLC. "
            "Use: obb.equity.price.historical(['SPY','QQQ','IWM','DIA','XLK','XLF','XLE','XLV','XLY','XLC'], "
            "start_date='REPLACE_START', end_date='REPLACE_END', provider='yfinance') "
            "where REPLACE_START is 10 trading days ago and REPLACE_END is today."
        ),
    },
    "movers": {
        "system": _BASE_SYSTEM,
        "user": (
            "Fetch today's top gainers and losers from the US equity market. "
            "Use: obb.equity.market_snapshots(provider='yfinance')"
        ),
    },
    "heatmap": {
        "system": _BASE_SYSTEM,
        "user": (
            "Fetch the last 3 days of daily price history for these sector ETFs: "
            "XLK, XLC, XLY, XLE, XLV, XLF, XLI, XLU, XLRE. "
            "Use: obb.equity.price.historical(['XLK','XLC','XLY','XLE','XLV','XLF','XLI','XLU','XLRE'], "
            "start_date='REPLACE_START', end_date='REPLACE_END', provider='yfinance') "
            "where REPLACE_START is 3 days ago and REPLACE_END is today."
        ),
    },
    "calendar": {
        "system": _BASE_SYSTEM,
        "user": (
            "Fetch the upcoming economic calendar events for the next 60 days. "
            "Use: obb.economy.calendar(start_date='REPLACE_START_60', end_date='REPLACE_END_60', provider='fmp') "
            "where REPLACE_START_60 is today and REPLACE_END_60 is 60 days from now."
        ),
    },
}
