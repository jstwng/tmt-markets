# Terminal Panel Direct Fetchers

**Date:** 2026-04-08
**Status:** Approved

## Problem

Three of five Market Overview panels (MACRO, TOP MOVERS, MACRO CALENDAR) consistently show
"Failed to load" because their data pipeline routes through Gemini LLM code generation → AST
validation → sandboxed exec. Root causes found by local testing:

- **MACRO**: `obb.economy.fred_series` requires a FRED API key that was not configured.
- **MOVERS**: `obb.equity.market_snapshots` only supports `fmp`/`intrinio` providers (both paid);
  the prompt instructs `provider='yfinance'` which is invalid.
- **CALENDAR**: `obb.economy.calendar` with `provider='fmp'` requires an FMP key; with
  `provider='fred'` the `openbb_fred` extension crashes on malformed date strings (library bug).

The LLM code-generation layer adds latency and random failure modes for what are five
fixed, well-known data fetches. The chat agent uses the same codegen pipeline legitimately
(user-driven queries), but the terminal panels do not benefit from it.

Secondary bug: the Retry button shows no visual feedback because `fetchPanel` never sets
`loading = true` before re-fetching, so the error state stays displayed throughout.

## Solution

Replace the per-panel codegen pipeline with deterministic Python functions in a new
`panel_fetchers.py` module. Each function calls OpenBB (or FRED REST) directly with
hardcoded parameters. The rest of the stack (caching, error fallback, response shape) is
unchanged, so zero frontend component changes are required.

## Architecture

### Backend changes

**New file: `packages/api/api/agent/panel_fetchers.py`**

One `async` function per panel:

```
fetch_macro()    → obb.economy.fred_series (FRED provider, FRED key from env)
fetch_indices()  → obb.equity.price.historical (yfinance, 10 days)
fetch_movers()   → obb.equity.price.historical (yfinance, 5 days, 50-stock list) + day-change calc
fetch_heatmap()  → obb.equity.price.historical (yfinance, 3 days, 9 sector ETFs)
fetch_calendar() → direct FRED REST API calls (urllib, no OpenBB wrapper)
```

Each function returns a JSON-serializable list and raises on failure. `_normalize()` from
`openbb_sandbox.py` is reused for OpenBB result normalization.

**Modified: `packages/api/api/routes/terminal.py`**

- Remove imports: `generate_openbb_code`, `validate_code`, `execute_openbb_code`, `PANEL_PROMPTS`
- Remove functions: `_inject_dates()`, `_fetch_panel()`
- Add: `from api.agent.panel_fetchers import PANEL_FETCHERS` (dict mapping panel name → function)
- Replace `_fetch_panel(panel)` call with `await PANEL_FETCHERS[panel]()`

**Modified: `packages/api/api/agent/openbb_client.py`**

- Load `FRED_API_KEY` from env and set `obb.user.credentials.fred_api_key`

### Frontend changes

**Modified: `packages/web/src/hooks/useTerminalPanel.ts`**

- Add `setLoading(true); setError(null)` at the top of `fetchPanel()` so the loading
  skeleton shows immediately on both initial load and retry clicks.

## Per-panel fetcher details

### `fetch_macro()`

```python
obb.economy.fred_series(
    symbol=['FEDFUNDS', 'DGS2', 'DGS10', 'CPIAUCSL', 'VIXCLS'],
    provider='fred'
)
```

FRED returns a **wide-format** DataFrame (one column per symbol). The fetcher melts it to
long format so `MacroPanel`'s existing `extractSeriesLatest(rawData, symbol)` works unchanged:

```python
df.reset_index().melt(id_vars='date', var_name='symbol', value_name='value').dropna(subset=['value'])
```

Output shape: `[{date, symbol, value}, ...]`

### `fetch_indices()` / `fetch_heatmap()`

These already work. Deterministic calls replacing the codegen path, same parameters:

```python
# indices
obb.equity.price.historical(
    ['SPY','QQQ','IWM','DIA','XLK','XLF','XLE','XLV','XLY','XLC'],
    start_date=ten_days_ago, end_date=today, provider='yfinance'
)

# heatmap
obb.equity.price.historical(
    ['XLK','XLC','XLY','XLE','XLV','XLF','XLI','XLU','XLRE'],
    start_date=three_days_ago, end_date=today, provider='yfinance'
)
```

### `fetch_movers()`

`obb.equity.market_snapshots` does not support yfinance. Instead:

```python
obb.equity.price.historical(
    LARGE_CAP_TICKERS,  # 50 hardcoded S&P 500 large-caps
    start_date=five_days_ago, end_date=today, provider='yfinance'
)
```

Post-process: group by symbol, take last 2 rows, compute
`(close[-1] - close[-2]) / close[-2] * 100`. Return
`[{symbol, pct_change}, ...]` sorted by `pct_change` descending.

`MoversPanel`'s existing `extractMovers` currently reads `percent_change` /
`change_percent` / `day_change_percent`. We return `pct_change`, so one field name is
added to the fallback chain in `MoversPanel.tsx`.

`LARGE_CAP_TICKERS` (50 stocks, hardcoded):
```
AAPL MSFT NVDA AMZN GOOGL META BRK-B LLY JPM XOM
V UNH AVGO TSLA PG MA JNJ HD COST MRK
ABBV CVX WMT BAC PFE KO NFLX PM TMO CRM
ACN AMD INTC ORCL ADBE QCOM TXN INTU IBM GE
CAT DE MMM HON RTX BA LMT GS MS C
```

### `fetch_calendar()`

Bypass the broken `openbb_fred` calendar extension. Call FRED REST directly:

```
GET https://api.stlouisfed.org/fred/release/dates
    ?release_id={id}&api_key={key}&file_type=json
    &sort_order=asc&include_release_dates_with_no_data=true
```

Fetch for each of these release IDs in parallel (asyncio.gather):

| Release ID | Event label |
|-----------|-------------|
| 10 | CPI |
| 46 | PPI |
| 53 | GDP |
| 50 | Nonfarm Payrolls |
| 54 | PCE |
| 175 | Retail Sales |

Filter to `today <= date <= today + 60 days`. Deduplicate by (date, event).

**FOMC dates**: FRED release ID 101 publishes daily updates (not meeting dates). Hardcode
the Fed's published 2026 FOMC decision dates:

```python
FOMC_2026 = [
    '2026-05-07', '2026-06-17', '2026-07-29',
    '2026-09-16', '2026-10-28', '2026-12-10',
]
```

Add 2027 dates when they are published (Fed releases the schedule each December).

Output shape: `[{date, event}, ...]` sorted by date, max 10 entries.

`CalendarPanel`'s `extractEvents` currently filters by keywords and reads
`r.event ?? r.name ?? r.description`. We return `event` directly, so it works
unchanged.

## Error handling

No changes to the error contract. Each fetcher raises on failure; `terminal.py`'s
existing try/except catches it, returns stale cache or `error: true` response. The retry
UX fix ensures users see the loading skeleton while the retry is in flight.

## What is NOT changed

- `openbb_codegen.py` — still used by the chat agent
- `openbb_sandbox.py` — `_normalize()` is reused; the rest is still used by the chat agent
- `terminal_prompts.py` — no longer used by the terminal route; leave in place for now
- All five panel components (`MacroPanel`, `IndicesPanel`, etc.) — zero changes except
  adding `pct_change` to the field fallback list in `MoversPanel`
- Response schema from `/api/terminal/panel/{panel}` — identical

## Testing

For each panel, verify:
1. `GET /api/terminal/panel/{panel}` returns `error: false` with non-empty `raw_data`
2. Data renders correctly in the browser (no "Failed to load")
3. Retry button shows loading skeleton, then data or error

Manual test script: run each fetcher function in isolation against the real APIs before
wiring into the route.
