# Navigation Simplification, Dashboard Rebuild & Terminal Tab

**Date:** 2026-04-08
**Status:** Approved

---

## Overview

Three coordinated changes:

1. **Navigation simplification** — collapse 6 tabs down to 4: Chat, Dashboard, Saved, Terminal. Remove standalone tool pages (Covariance, Portfolio, Backtest). Tool-specific analyses remain available exclusively as inline Chart Manifest outputs within the Chat thread.
2. **Dashboard rebuild** — Robinhood-style portfolio performance view with equity curve, positions table, and holdings pie chart.
3. **Terminal tab** — new read-only, auto-refreshing ambient market overview screen powered by live OpenBB data.

---

## 1. Navigation

### Changes to `App.tsx`

**Routes removed:**
- `/covariance` → `Covariance.tsx`
- `/portfolio` → `Portfolio.tsx`
- `/backtest` → `Backtest.tsx`

**Route added:**
- `/terminal` → `Terminal.tsx` (new)

**Routes unchanged:**
- `/` and `/c/:conversationId` → Chat
- `/dashboard` → Dashboard (rebuilt)
- `/saved` → Saved

**Nav bar:** 4 links — Chat · Dashboard · Saved · Terminal. Same styling as today (active underline, sticky header).

**Files deleted:** `Covariance.tsx`, `Portfolio.tsx`, `Backtest.tsx`

**Dashboard card grid removed:** The existing tool shortcut cards (`/covariance`, `/portfolio`, `/backtest` links) in `Dashboard.tsx` are removed entirely.

---

## 2. Dashboard

### Layout

Robinhood-style single-column layout with no scrolling on typical screens:

1. **Selector bar** (top) — portfolio dropdown (left) + total value input (right)
2. **Big value** — large centered portfolio value + today's dollar/% change
3. **Equity curve** — full-width responsive Plotly chart with SPY benchmark overlay and time selector
4. **Pie + stats row** — holdings pie chart (left) alongside 4 risk stat cards (right): Total Return, vs SPY alpha, Sharpe, Max Drawdown
5. **Positions table** — Ticker / Weight / Price / Day % / Value ($) / Return (total)
6. **Footer** — "Prices via yfinance · Last updated HH:MM"

### Portfolio Selector

- Dropdown populated from `GET /api/portfolios` — lists all saved portfolios by name
- Default: most recently saved (first in list)
- Selection persists in component state (not URL or localStorage — resets on page reload is acceptable)

### Portfolio Value Input

- Editable text field, top-right of selector bar
- Stored in `localStorage` keyed by portfolio id
- Used client-side to compute Value ($) column: `weight × total_value`
- Does not affect server-side computation

### Equity Curve

- Data from `GET /api/portfolio/performance?portfolio_id=`
- API always returns maximum available history (up to 5 years via yfinance)
- Period selector: 1M / 3M / 6M / 1Y / All — pill buttons, default 1M
- Switching period re-slices the already-fetched curve client-side (no new network request)
- Switching portfolio triggers a fresh API call
- Plotly `react-plotly.js` with `useResizeObserver` — fully responsive, redraws on container width change
- Two traces: portfolio cumulative return (solid black line + subtle fill), SPY benchmark (dashed gray)
- Hover tooltip: date + portfolio value
- Loading state: skeleton placeholder (gray rounded rect) while fetching
- Chart defaults: matches existing `chart-defaults.ts` (no gridlines, minimal axes, white background)

### Positions Table

Columns: Ticker | Weight | Price | Day % | Value ($) | Return (total since curve start)

- Price and Day % from current price data returned by `/api/portfolio/performance`
- Value ($) computed client-side: `weight × total_value`
- Return: `(current_price / price_at_curve_start) − 1`
- Red/green for Day % and Return columns only
- Skeleton rows while loading

### Risk Stats Cards (2×2 grid)

| Stat | Source |
|------|--------|
| Total Return | from API response `stats.total_return` |
| vs SPY | `stats.alpha` (portfolio return − SPY return over period) |
| Sharpe Ratio | `stats.sharpe` (trailing period) |
| Max Drawdown | `stats.max_drawdown` |

---

## 3. Terminal Tab

### Layout

Three rows, all panels independently fetched and rendered:

| Row | Panels | Width |
|-----|--------|-------|
| 1 | Macro | Full width |
| 2 | Equity Indices + Top Movers | 50% / 50% |
| 3 | Sector Heatmap + Macro Calendar | 50% / 50% |

Header bar: "Market Overview" title (left) + refresh interval dropdown (right): 1 min / **5 min** (default) / 15 min / 30 min. Stored in `localStorage`.

Each panel shows its own "Updated HH:MM" timestamp (bottom-right of panel header). Footer: "All data via OpenBB · Auto-refreshes every N min".

### Panel: Macro

Fields: Fed Funds Rate, 2Y Treasury yield, 10Y Treasury yield, 2s10s spread (bp, labeled "inverted" when negative), CPI YoY (most recent), VIX.

Each field: label / current value / directional change (day-over-day where applicable) / 30-day sparkline.

Layout: single horizontal row of 6 cells, scroll on overflow (mobile).

### Panel: Equity Indices

Tickers: SPY, QQQ, IWM, DIA (major indices) + XLK, XLF, XLE, XLV, XLY, XLC (sector ETFs, visually separated with lighter text).

Columns: ETF / Price / Day ($ and %) / 5-day sparkline.

### Panel: Top Movers

Source: S&P 500 constituents — top 5 gainers and top 5 losers by day % change.

Two columns side-by-side: Gainers (green header) / Losers (red header). Each row: Ticker / Day %.

### Panel: Sector Heatmap

9 sectors: XLK, XLC, XLY, XLE, XLV, XLF, XLI, XLU, XLRE.

Rendered as a 3×3 color-coded grid using the existing `HeatmapRenderer` color logic (green → white → red, proportional to day % change magnitude). Each cell: sector ticker + day %. No Plotly — plain CSS grid with inline background colors for performance.

### Panel: Macro Calendar

Upcoming economic events fetched via OpenBB economy calendar. Columns: Date / Event / Consensus estimate (where available, else "—").

Events shown: FOMC decisions, CPI releases, PPI, Jobs Report, Initial Claims. Sorted ascending by date. Show next ~8 events.

### Data Fetching

Each panel fetches independently from `GET /api/terminal/panel/{panel}`:

- `panel` ∈ `macro | indices | movers | heatmap | calendar`
- Frontend polls on the user-selected interval using `setInterval` + `clearInterval` on unmount/interval change
- On mount: fetch immediately, then start interval
- Interval stored in `localStorage` as `terminal_refresh_interval_ms`

On error: panel shows inline error state ("Failed to load · Retry") without affecting other panels. Stale data shown if available.

### Refresh Dropdown Behavior

- Changing the interval cancels the current timer and starts a new one immediately (no wait for old interval to expire)
- "Next refresh in X:XX" countdown displayed in header, updates every second

---

## 4. Backend

### New Endpoints

#### `GET /api/portfolios`
Returns list of saved portfolios from Supabase for the current user, ordered by `created_at` descending (most recent first).

```json
[{ "id": "uuid", "name": "Tech Portfolio", "created_at": "...", "tickers": ["AAPL","MSFT"] }]
```

#### `GET /api/portfolio/performance`

Query params: `portfolio_id` (optional, defaults to most recent portfolio by `created_at` desc).

Steps:
1. Load portfolio weights from Supabase
2. Fetch maximum available daily closes for all tickers + SPY in parallel via yfinance (`asyncio.gather`, up to 5 years)
3. Compute weighted daily return series, cumulate to index (base 100)
4. Compute stats over full history: Sharpe (annualized), max drawdown, total return, alpha vs SPY
5. Return current price and day % for each position (last two rows of price data)

Response:
```json
{
  "curve": [{ "date": "2024-01-02", "value": 100.0, "benchmark": 100.0 }],
  "positions": [{ "ticker": "AAPL", "weight": 0.42, "price": 175.20, "day_pct": 0.023, "total_return": 0.184 }],
  "stats": { "sharpe": 1.42, "max_drawdown": -0.081, "total_return": 0.243, "alpha": 0.062 }
}
```

Server-side cache: 15 min, keyed by `portfolio_id`. Simple in-memory dict with timestamp check.

#### `GET /api/terminal/panel/{panel}`

Query params: `ttl` (seconds, passed by frontend to match refresh interval, used for cache key expiry).

Each panel handler:
1. Checks in-memory cache — returns cached JSON if within TTL
2. Calls `generate_openbb_code()` with a fixed, panel-specific system prompt
3. Validates and executes the generated code in the OpenBB sandbox
4. Normalizes the result into the panel's display schema
5. Caches and returns

On codegen/execution failure after 4 retries: returns `{ "error": true, "message": "...", "stale_data": <last_cached_result_or_null> }`.

**No changes** to the existing chat agent, SSE pipeline, tool declarations, or `openbb_sandbox.py`.

---

## 5. New Files

### Frontend (`packages/web/src/`)

| File | Purpose |
|------|---------|
| `pages/Terminal.tsx` | Terminal tab root — header bar, panel grid, interval management |
| `pages/Dashboard.tsx` | Full rebuild (replaces existing stub) |
| `components/terminal/MacroPanel.tsx` | Macro metrics row |
| `components/terminal/IndicesPanel.tsx` | Equity indices table |
| `components/terminal/MoversPanel.tsx` | Top gainers/losers |
| `components/terminal/HeatmapPanel.tsx` | Sector color grid |
| `components/terminal/CalendarPanel.tsx` | Economic calendar |
| `components/terminal/PanelShell.tsx` | Shared panel wrapper (border, header, timestamp, error state) |
| `components/dashboard/EquityCurve.tsx` | Plotly equity chart with time selector |
| `components/dashboard/PositionsTable.tsx` | Positions table |
| `components/dashboard/HoldingsPie.tsx` | Pie chart (Plotly PieRenderer reuse) |
| `hooks/usePortfolioPerformance.ts` | Fetches + caches dashboard data |
| `hooks/useTerminalPanel.ts` | Per-panel fetch + polling hook |

### Backend (`packages/api/api/`)

| File | Purpose |
|------|---------|
| `routes/portfolio.py` | `/api/portfolios` and `/api/portfolio/performance` |
| `routes/terminal.py` | `/api/terminal/panel/{panel}` with panel handlers |
| `agent/terminal_prompts.py` | Fixed system prompts for each terminal panel's codegen |

---

## 6. Out of Scope

- Dark mode for Terminal (follows existing system, no new work)
- Real-time WebSocket streaming (polling only)
- Mobile responsive layout for Terminal panels (horizontal scroll on small screens is acceptable)
- Historical portfolio tracking (equity curve computed on-demand from weights, not logged over time)
- Editing portfolio weights from the Dashboard (read-only; portfolios managed via Chat)
