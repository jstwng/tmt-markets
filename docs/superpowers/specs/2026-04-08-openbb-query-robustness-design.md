# openbb_query Robustness — Design Spec

**Date:** 2026-04-08  
**Status:** Approved  
**Approach:** B — Expression-only codegen with safe boilerplate wrapper

---

## Problem Summary

The `openbb_query` tool fails consistently due to four root causes:

1. **Wrong routing** — LLM calls `openbb_query` for historical price data that `fetch_prices` handles better
2. **`.to_df()` bug** — `obb.user.preferences.output_type = "dataframe"` means OpenBB returns DataFrames directly, but the codegen prompt instructs the LLM to call `.to_df()`, causing `AttributeError` every time
3. **Weak retry context** — retries pass a bare exception string with no hint about what failed or how to fix it
4. **Fragile full-function codegen** — asking the LLM to generate datetime handling, serialization, and function wrappers creates too many failure points

---

## Design

### 1. Routing Fixes (`tools.py`, `prompts.py`)

**`fetch_prices` description update:**
> "Fetch historical adjusted close prices for a list of tickers. Use for ALL historical price/OHLCV data — never use openbb_query for price history."

**`openbb_query` description update:**
> "Query financial data via OpenBB Platform. Use ONLY for data not available via other tools: options chains, earnings, income statements, fundamentals, macro indicators (CPI/GDP), ETF holdings, short interest, SEC filings, news. Do NOT use for historical prices — use fetch_prices instead."

**System prompt addition** (`prompts.py`):
> "For historical price data, ALWAYS use fetch_prices. Never use openbb_query for price history."

---

### 2. Expression-only Codegen (`openbb_codegen.py`)

**What changes:** The LLM is asked to generate **one line only** — the OpenBB call expression. No function wrapper, no datetime math, no serialization.

**New codegen system prompt:**
- Output one line: the OpenBB call expression only
- No `def fetch()`, no imports, no `.to_df()`, no `.to_dict()`
- Hardcode dates as strings or use simple string arithmetic — no `datetime` module
- 5 canonical examples provided:
  - `obb.equity.price.historical("NVDA", start_date="2023-01-01", end_date="2026-01-01", provider="yfinance")`
  - `obb.equity.fundamental.income("AAPL", provider="yfinance")`
  - `obb.derivatives.options.chains("TSLA", provider="cboe")`
  - `obb.economy.fred_series(symbol="GDP")`
  - `obb.etf.holdings("SPY", provider="yfinance")`

**Boilerplate wrapper** (injected by `openbb_sandbox.py`):
```python
def fetch():
    result = <LLM_EXPRESSION>
    return _normalize(result)
```

**`_normalize(value)` helper** (injected into sandbox namespace):
```python
def _normalize(value):
    if isinstance(value, pd.DataFrame):
        return value.reset_index().to_dict(orient="records")
    if hasattr(value, "to_df"):            # OBBject — call .to_df()
        return value.to_df().reset_index().to_dict(orient="records")
    if hasattr(value, "results"):          # OBBject raw fallback
        results = value.results
        if isinstance(results, list):
            return [r.__dict__ if hasattr(r, "__dict__") else r for r in results]
        return results
    if isinstance(value, (list, dict)):
        return value
    return value
```

This eliminates the entire class of serialization/datetime/`.to_df()` errors at the framework level.

---

### 3. Chart Manifest Quality (`openbb_codegen.py`)

**Manifest system prompt additions:**
- "Always prefer a visual chart_type over a table. Use `time_series` for price/macro series, `candlestick` for OHLCV (has open/high/low/close), `bar` for earnings/comparisons, `pie` for allocations/compositions. Only use `table` if the data is genuinely tabular with no sensible visual encoding."
- Data shape hint injected before sending data to LLM: detect columns and include one-line hint e.g. *"Data shape hint: list of records with date column and close/open/high/low — consider candlestick or time_series."*

**Truncation fix:** Truncate at N records (100 records) instead of N characters, so the JSON stays valid and the LLM sees the full structure of each record.

**Shape detection logic** (`_detect_shape_hint(data: list[dict]) -> str`):
- Has `open`, `high`, `low`, `close` → "OHLCV — consider candlestick"
- Has `date`/`period` + one numeric field → "time series — consider time_series"
- Has categorical `name`/`label` + numeric `value` → "categorical — consider bar or pie"
- Otherwise → "tabular"

---

### 4. Retry Loop (`agent.py`, `openbb_codegen.py`)

**Retries:** Increase from 3 to 4.

**Richer error context per retry:**
```python
error_context = f"""
Expression attempted: {last_expression}
Error: {type(e).__name__}: {e}
Hint: {_classify_error(e)}
"""
```

**`_classify_error(e) -> str`** maps common errors to actionable hints:

| Error pattern | Hint |
|---|---|
| `AttributeError: 'DataFrame'... 'to_df'` | "Don't call .to_df() — result is already a DataFrame" |
| `TypeError: unexpected keyword argument` | "Check parameter names — the argument name may be wrong" |
| `AttributeError: 'OBBject'` | "Use .results or .to_df() on the OBBject, not direct attribute access" |
| `KeyError` | "Don't access specific column names — return the full result" |
| Default | Raw error message |

**SSE progress events:** Each retry yields a `codegen_retry` SSE event:
```json
{"event": "codegen_retry", "data": {"attempt": 2, "error": "AttributeError: ..."}}
```
Frontend already has `SSECodegenRetryEvent` typed for this.

---

## Files Changed

| File | Change |
|---|---|
| `api/agent/tools.py` | Update `fetch_prices` and `openbb_query` descriptions |
| `api/agent/prompts.py` | Add routing rule for price data |
| `api/agent/openbb_codegen.py` | Expression-only system prompt, data shape hint, record-count truncation, manifest visual preference |
| `api/agent/openbb_sandbox.py` | Expression wrapper, `_normalize` injected into namespace, `_classify_error` helper |
| `api/routes/agent.py` | Richer retry context, `codegen_retry` SSE events, 4 retries |

---

## Success Criteria

- "show me historical price chart for NVDA, AMD" → routes to `fetch_prices`, renders `PriceChart`
- "show me options chain for TSLA" → routes to `openbb_query`, generates expression, returns candlestick or table manifest
- No more `'DataFrame' object has no attribute 'to_df'` errors
- No more `module 'datetime' has no attribute 'now'` errors (codegen no longer generates datetime code)
- On failure, retry shows specific expression + actionable hint
- Chart manifests prefer visual types (time_series, candlestick) over table when data supports it
