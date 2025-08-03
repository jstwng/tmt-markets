"""Fixed OpenBB codegen prompts for each Terminal panel.

Each entry has a single `user` prompt passed to generate_openbb_code().
The codegen module supplies its own system prompt; per-panel system prompts
are not supported and have been removed.
"""

PANEL_PROMPTS: dict[str, dict[str, str]] = {
    "macro": {
        "user": (
            "Fetch the last 90 days of daily data for the following FRED series as a single call: "
            "FEDFUNDS (Fed Funds Rate), DGS2 (2Y Treasury), DGS10 (10Y Treasury), CPIAUCSL (CPI), VIXCLS (VIX). "
            "Use: obb.economy.fred_series(symbol=['FEDFUNDS','DGS2','DGS10','CPIAUCSL','VIXCLS'], provider='fred')"
        ),
    },
    "indices": {
        "user": (
            "Fetch the last 10 days of daily price history for these tickers: "
            "SPY, QQQ, IWM, DIA, XLK, XLF, XLE, XLV, XLY, XLC. "
            "Use: obb.equity.price.historical(['SPY','QQQ','IWM','DIA','XLK','XLF','XLE','XLV','XLY','XLC'], "
            "start_date='REPLACE_START', end_date='REPLACE_END', provider='yfinance') "
            "where REPLACE_START is 10 trading days ago and REPLACE_END is today."
        ),
    },
    "movers": {
        "user": (
            "Fetch today's top gainers and losers from the US equity market. "
            "Use: obb.equity.market_snapshots(provider='yfinance')"
        ),
    },
    "heatmap": {
        "user": (
            "Fetch the last 3 days of daily price history for these sector ETFs: "
            "XLK, XLC, XLY, XLE, XLV, XLF, XLI, XLU, XLRE. "
            "Use: obb.equity.price.historical(['XLK','XLC','XLY','XLE','XLV','XLF','XLI','XLU','XLRE'], "
            "start_date='REPLACE_START_3', end_date='REPLACE_END', provider='yfinance') "
            "where REPLACE_START_3 is 3 days ago and REPLACE_END is today."
        ),
    },
    "calendar": {
        "user": (
            "Fetch the upcoming economic calendar events for the next 60 days. "
            "Use: obb.economy.calendar(start_date='REPLACE_START_60', end_date='REPLACE_END_60', provider='fmp') "
            "where REPLACE_START_60 is today and REPLACE_END_60 is 60 days from now."
        ),
    },
}
