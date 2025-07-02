# Nav Simplification, Dashboard Rebuild & Terminal Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the nav to 4 tabs (Chat, Dashboard, Saved, Terminal), rebuild the Dashboard as a Robinhood-style portfolio performance view, and add a Terminal tab with a live auto-refreshing market overview grid powered by OpenBB.

**Architecture:** Per-panel FastAPI endpoints with in-memory caching serve the Terminal; a new `/api/portfolio/performance` endpoint computes equity curves server-side using the existing `fetch_prices` helper and `asyncio.to_thread`. The frontend fetches independently per panel using a polling hook; the Dashboard uses `react-plotly.js` with `useResizeHandler` for a fully responsive chart.

**Tech Stack:** FastAPI + yfinance (backend), React 19 + Plotly.js + React Router 7 + Tailwind + shadcn (frontend), Supabase JWT auth, pytest + asyncio auto mode (tests).

---

## File Map

### Files to delete
- `packages/web/src/pages/Covariance.tsx`
- `packages/web/src/pages/Portfolio.tsx`
- `packages/web/src/pages/Backtest.tsx`

### Files to modify
- `packages/web/src/App.tsx` — remove 3 routes/imports, add Terminal route, update navItems
- `packages/web/src/api/client.ts` — add auth-aware helpers + new API functions + types
- `packages/api/api/routes/portfolios.py` — add `/api/portfolio/performance` endpoint
- `packages/api/api/main.py` — register terminal router

### Files to create
| Path | Responsibility |
|------|----------------|
| `packages/api/api/agent/terminal_prompts.py` | Fixed per-panel OpenBB codegen system prompts |
| `packages/api/api/routes/terminal.py` | `/api/terminal/panel/{panel}` with 5 handlers + cache |
| `packages/api/tests/test_portfolio_performance.py` | Tests for the performance endpoint |
| `packages/api/tests/test_terminal_routes.py` | Tests for terminal panel endpoints |
| `packages/web/src/hooks/usePortfolioPerformance.ts` | Fetch + period-slicing for Dashboard |
| `packages/web/src/hooks/useTerminalPanel.ts` | Polling hook for Terminal panels |
| `packages/web/src/components/dashboard/EquityCurve.tsx` | Plotly equity chart + time selector |
| `packages/web/src/components/dashboard/PositionsTable.tsx` | Positions table with skeleton |
| `packages/web/src/components/dashboard/HoldingsPie.tsx` | Pie chart |
| `packages/web/src/components/terminal/PanelShell.tsx` | Shared panel wrapper (border, header, timestamp, error state) |
| `packages/web/src/components/terminal/MacroPanel.tsx` | Macro metrics row |
| `packages/web/src/components/terminal/IndicesPanel.tsx` | Equity indices table |
| `packages/web/src/components/terminal/MoversPanel.tsx` | Top gainers/losers |
| `packages/web/src/components/terminal/HeatmapPanel.tsx` | Sector color grid |
| `packages/web/src/components/terminal/CalendarPanel.tsx` | Economic calendar |
| `packages/web/src/pages/Terminal.tsx` | Terminal tab root: header bar + panel grid + interval management |
| `packages/web/src/pages/Dashboard.tsx` | Full rebuild (replaces existing stub) |

---

## Task 1: Navigation Simplification

**Files:**
- Modify: `packages/web/src/App.tsx`
- Delete: `packages/web/src/pages/Covariance.tsx`, `packages/web/src/pages/Portfolio.tsx`, `packages/web/src/pages/Backtest.tsx`

- [ ] **Step 1: Delete the three standalone page files**

```bash
rm packages/web/src/pages/Covariance.tsx
rm packages/web/src/pages/Portfolio.tsx
rm packages/web/src/pages/Backtest.tsx
```

- [ ] **Step 2: Rewrite App.tsx**

Replace the full contents of `packages/web/src/App.tsx` with:

```tsx
import { Routes, Route, Link, useLocation } from "react-router";
import { useAuth } from "@/contexts/AuthContext";
import Login from "@/pages/Login";
import Chat from "@/pages/Chat";
import Dashboard from "@/pages/Dashboard";
import Saved from "@/pages/Saved";
import Terminal from "@/pages/Terminal";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const navItems = [
  { path: "/", label: "Chat" },
  { path: "/dashboard", label: "Dashboard" },
  { path: "/saved", label: "Saved" },
  { path: "/terminal", label: "Terminal" },
];

function App() {
  const { user, loading, signOut } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-muted-foreground text-sm">Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b sticky top-0 z-10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="max-w-6xl mx-auto flex h-14 items-center px-6">
          <Link to="/" className="font-bold text-base mr-8 no-underline text-foreground tracking-tight">
            TMT Markets
          </Link>
          <nav className="flex gap-1 flex-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "text-sm transition-colors no-underline px-3 py-1.5 rounded-md",
                  location.pathname === item.path || (item.path === "/" && location.pathname.startsWith("/c/"))
                    ? "bg-muted text-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <Button variant="ghost" size="sm" onClick={signOut} className="text-xs text-muted-foreground">
            Sign out
          </Button>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-6">
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/c/:conversationId" element={<Chat />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/saved" element={<Saved />} />
          <Route path="/terminal" element={<Terminal />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
```

Note: `Terminal` is imported but doesn't exist yet — TypeScript will error until Task 9. Create a stub now:

```bash
echo 'export default function Terminal() { return <div>Terminal</div>; }' > packages/web/src/pages/Terminal.tsx
```

- [ ] **Step 3: Verify the app compiles**

```bash
cd packages/web && npx tsc --noEmit
```

Expected: no errors related to removed imports (Covariance, Portfolio, Backtest are gone). Terminal stub satisfies the import.

- [ ] **Step 4: Commit**

```bash
git add packages/web/src/App.tsx packages/web/src/pages/Terminal.tsx
git commit -m "feat: simplify nav to Chat, Dashboard, Saved, Terminal; remove standalone tool pages"
```

---

## Task 2: Frontend API Types + Auth-Aware Client Helpers

**Files:**
- Modify: `packages/web/src/api/client.ts`

- [ ] **Step 1: Replace the contents of `packages/web/src/api/client.ts`**

```typescript
import type {
  CovarianceRequest,
  CovarianceResponse,
  EfficientFrontierRequest,
  EfficientFrontierResponse,
  PortfolioOptimizeRequest,
  PortfolioOptimizeResponse,
  BacktestRequest,
  BacktestResponse,
  PricesRequest,
  PricesResponse,
} from "./types";

const API_BASE = "/api";

// ---------------------------------------------------------------------------
// Base fetch helpers
// ---------------------------------------------------------------------------

async function post<TReq, TRes>(path: string, body: TReq): Promise<TRes> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail);
  }
  return res.json();
}

async function get<TRes>(path: string): Promise<TRes> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail);
  }
  return res.json();
}

async function authedGet<TRes>(path: string, token: string): Promise<TRes> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Types for new endpoints
// ---------------------------------------------------------------------------

export interface Portfolio {
  id: string;
  name: string;
  tickers: string[];
  weights: number[];
  created_at: string;
  updated_at: string;
}

export interface PerformanceCurvePoint {
  date: string;
  value: number;
  benchmark: number;
}

export interface PositionData {
  ticker: string;
  weight: number;
  price: number;
  day_pct: number;
  total_return: number;
}

export interface PortfolioPerformance {
  curve: PerformanceCurvePoint[];
  positions: PositionData[];
  stats: {
    sharpe: number;
    max_drawdown: number;
    total_return: number;
    alpha: number;
  };
  portfolio_name: string;
}

export interface MacroPanelData {
  fields: {
    label: string;
    value: string;
    change: string | null;
    sparkline: number[];
  }[];
}

export interface IndicesPanelData {
  rows: {
    ticker: string;
    price: number;
    day_change: number;
    day_pct: number;
    sparkline: number[];
    is_sector: boolean;
  }[];
}

export interface MoversPanelData {
  gainers: { ticker: string; day_pct: number }[];
  losers: { ticker: string; day_pct: number }[];
}

export interface HeatmapPanelData {
  sectors: { ticker: string; day_pct: number }[];
}

export interface CalendarPanelData {
  events: { date: string; event: string; consensus: string | null }[];
}

export type TerminalPanelData =
  | MacroPanelData
  | IndicesPanelData
  | MoversPanelData
  | HeatmapPanelData
  | CalendarPanelData;

export interface TerminalPanelResponse {
  panel: string;
  data: TerminalPanelData;
  cached_at: string;
  error?: string;
}

// ---------------------------------------------------------------------------
// Existing endpoints (unchanged)
// ---------------------------------------------------------------------------

export async function healthCheck(): Promise<{ status: string }> {
  return get("/health");
}

export async function computeCovariance(req: CovarianceRequest): Promise<CovarianceResponse> {
  return post("/covariance", req);
}

export async function optimizePortfolio(req: PortfolioOptimizeRequest): Promise<PortfolioOptimizeResponse> {
  return post("/portfolio/optimize", req);
}

export async function runBacktest(req: BacktestRequest): Promise<BacktestResponse> {
  return post("/backtest", req);
}

export async function fetchPrices(req: PricesRequest): Promise<PricesResponse> {
  return post("/data/prices", req);
}

export async function generateFrontier(req: EfficientFrontierRequest): Promise<EfficientFrontierResponse> {
  return post("/portfolio/frontier", req);
}

// ---------------------------------------------------------------------------
// New endpoints
// ---------------------------------------------------------------------------

export async function listPortfolios(token: string): Promise<Portfolio[]> {
  return authedGet("/portfolios", token);
}

export async function getPortfolioPerformance(
  token: string,
  portfolioId?: string
): Promise<PortfolioPerformance> {
  const qs = portfolioId ? `?portfolio_id=${encodeURIComponent(portfolioId)}` : "";
  return authedGet(`/portfolio/performance${qs}`, token);
}

export async function getTerminalPanel(
  panel: "macro" | "indices" | "movers" | "heatmap" | "calendar",
  ttl: number
): Promise<TerminalPanelResponse> {
  return get(`/terminal/panel/${panel}?ttl=${ttl}`);
}
```

- [ ] **Step 2: Verify TypeScript is happy**

```bash
cd packages/web && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/api/client.ts
git commit -m "feat: add auth-aware client helpers and types for portfolio/terminal endpoints"
```

---

## Task 3: Backend — Terminal Prompts

**Files:**
- Create: `packages/api/api/agent/terminal_prompts.py`

- [ ] **Step 1: Write the failing test**

Create `packages/api/tests/test_terminal_prompts.py`:

```python
"""Tests that terminal prompts exist and are non-empty strings."""
from api.agent.terminal_prompts import PANEL_PROMPTS


def test_all_panels_have_prompts():
    for panel in ("macro", "indices", "movers", "heatmap", "calendar"):
        assert panel in PANEL_PROMPTS
        assert isinstance(PANEL_PROMPTS[panel]["system"], str)
        assert len(PANEL_PROMPTS[panel]["system"]) > 50
        assert isinstance(PANEL_PROMPTS[panel]["user"], str)
        assert len(PANEL_PROMPTS[panel]["user"]) > 10


def test_prompts_mention_obb():
    for panel, prompts in PANEL_PROMPTS.items():
        combined = prompts["system"] + prompts["user"]
        assert "obb" in combined.lower() or "openbb" in combined.lower(), \
            f"Panel '{panel}' prompt doesn't reference obb"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd packages/api && python -m pytest tests/test_terminal_prompts.py -v
```

Expected: `FAILED — ModuleNotFoundError: No module named 'api.agent.terminal_prompts'`

- [ ] **Step 3: Create `packages/api/api/agent/terminal_prompts.py`**

```python
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
            "Use: obb.economy.calendar(start_date='REPLACE_START', end_date='REPLACE_END', provider='fmp') "
            "where REPLACE_START is today and REPLACE_END is 60 days from now."
        ),
    },
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd packages/api && python -m pytest tests/test_terminal_prompts.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/agent/terminal_prompts.py packages/api/tests/test_terminal_prompts.py
git commit -m "feat: add terminal panel OpenBB codegen prompts"
```

---

## Task 4: Backend — Terminal Panel Routes

**Files:**
- Create: `packages/api/api/routes/terminal.py`
- Create: `packages/api/tests/test_terminal_routes.py`
- Modify: `packages/api/api/main.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/api/tests/test_terminal_routes.py`:

```python
"""Tests for /api/terminal/panel/{panel} endpoint."""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

VALID_PANELS = ["macro", "indices", "movers", "heatmap", "calendar"]

_MOCK_RAW = [{"date": "2024-01-01", "value": 5.33}]


@pytest.fixture(autouse=True)
def mock_codegen_and_sandbox():
    """Mock generate_openbb_code and execute_openbb_code for all terminal tests."""
    with patch(
        "api.routes.terminal.generate_openbb_code",
        new_callable=AsyncMock,
        return_value='obb.economy.fred_series(symbol="FEDFUNDS", provider="fred")',
    ) as mock_gen, patch(
        "api.routes.terminal.execute_openbb_code",
        new_callable=AsyncMock,
        return_value=_MOCK_RAW,
    ) as mock_exec, patch(
        "api.routes.terminal._get_obb_client",
        return_value=MagicMock(),
    ):
        yield mock_gen, mock_exec


def test_valid_panels_return_200():
    for panel in VALID_PANELS:
        resp = client.get(f"/api/terminal/panel/{panel}?ttl=300")
        assert resp.status_code == 200, f"Panel {panel} returned {resp.status_code}: {resp.text}"


def test_response_has_required_fields():
    resp = client.get("/api/terminal/panel/macro?ttl=300")
    body = resp.json()
    assert "panel" in body
    assert "raw_data" in body
    assert "cached_at" in body
    assert body["panel"] == "macro"


def test_invalid_panel_returns_404():
    resp = client.get("/api/terminal/panel/nonexistent?ttl=300")
    assert resp.status_code == 404


def test_cache_is_used_on_second_request(mock_codegen_and_sandbox):
    mock_gen, mock_exec = mock_codegen_and_sandbox
    # Clear cache first
    from api.routes.terminal import _cache
    _cache.clear()

    client.get("/api/terminal/panel/macro?ttl=300")
    client.get("/api/terminal/panel/macro?ttl=300")

    # generate_openbb_code should only be called once (second hits cache)
    assert mock_gen.call_count == 1


def test_error_response_on_codegen_failure():
    from api.routes.terminal import _cache
    _cache.clear()

    with patch(
        "api.routes.terminal.generate_openbb_code",
        new_callable=AsyncMock,
        side_effect=Exception("LLM quota exceeded"),
    ), patch("api.routes.terminal._get_obb_client", return_value=MagicMock()):
        resp = client.get("/api/terminal/panel/macro?ttl=300")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("error") is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/api && python -m pytest tests/test_terminal_routes.py -v
```

Expected: `FAILED — ImportError` (module doesn't exist yet)

- [ ] **Step 3: Create `packages/api/api/routes/terminal.py`**

```python
"""Terminal tab panel endpoints.

GET /api/terminal/panel/{panel}?ttl=300

Returns raw OpenBB data for each panel. Each panel uses a fixed codegen prompt,
executes in the OpenBB sandbox, and caches the result server-side for `ttl` seconds.
"""

import time
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from api.agent.openbb_codegen import generate_openbb_code
from api.agent.openbb_sandbox import execute_openbb_code, validate_code
from api.agent.terminal_prompts import PANEL_PROMPTS

router = APIRouter(tags=["terminal"])

# In-memory cache: panel -> {"data": ..., "ts": float, "ttl": int}
_cache: dict[str, dict[str, Any]] = {}

_MAX_RETRIES = 4


def _get_obb_client():
    from api.agent.openbb_client import get_obb_client
    return get_obb_client()


def _inject_dates(prompt: str) -> str:
    """Replace REPLACE_START / REPLACE_END placeholders with real dates."""
    today = datetime.now().strftime("%Y-%m-%d")
    ten_days_ago = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    sixty_days_out = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

    return (
        prompt
        .replace("REPLACE_START", ten_days_ago)
        .replace("REPLACE_END", today)
        .replace("REPLACE_START_3", three_days_ago)
        .replace("REPLACE_START_60", today)
        .replace("REPLACE_END_60", sixty_days_out)
    )


async def _fetch_panel(panel: str) -> list | dict:
    """Run codegen → validate → execute with up to _MAX_RETRIES attempts."""
    prompts = PANEL_PROMPTS[panel]
    system = prompts["system"]
    user = _inject_dates(prompts["user"])
    obb = _get_obb_client()

    error_context = None
    for attempt in range(_MAX_RETRIES):
        code = await generate_openbb_code(user, error_context=error_context)
        valid, reason = validate_code(code)
        if not valid:
            error_context = f"Code failed AST validation: {reason}"
            continue
        try:
            result = await execute_openbb_code(code, obb)
            return result
        except Exception as exc:
            error_context = str(exc)

    raise RuntimeError(f"Panel '{panel}' failed after {_MAX_RETRIES} attempts. Last error: {error_context}")


@router.get("/terminal/panel/{panel}")
async def get_terminal_panel(panel: str, ttl: int = 300):
    if panel not in PANEL_PROMPTS:
        raise HTTPException(status_code=404, detail=f"Unknown panel: {panel}")

    cached = _cache.get(panel)
    if cached and (time.time() - cached["ts"]) < cached["ttl"]:
        return cached["data"]

    try:
        raw_data = await _fetch_panel(panel)
        response = {
            "panel": panel,
            "raw_data": raw_data,
            "cached_at": datetime.utcnow().isoformat() + "Z",
            "error": False,
        }
        _cache[panel] = {"data": response, "ts": time.time(), "ttl": ttl}
        return response
    except Exception as exc:
        stale = _cache.get(panel, {}).get("data")
        return {
            "panel": panel,
            "raw_data": stale["raw_data"] if stale else [],
            "cached_at": stale["cached_at"] if stale else None,
            "error": True,
            "error_message": str(exc),
        }
```

- [ ] **Step 4: Register the router in `packages/api/api/main.py`**

Add `from api.routes import terminal` to the imports and `app.include_router(terminal.router, prefix="/api")` after the existing routers:

```python
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
    for key in ["GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_JWT_SECRET"]:
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd packages/api && python -m pytest tests/test_terminal_routes.py -v
```

Expected: all 5 tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add packages/api/api/routes/terminal.py packages/api/api/main.py packages/api/tests/test_terminal_routes.py
git commit -m "feat: add /api/terminal/panel/{panel} endpoint with per-panel caching"
```

---

## Task 5: Backend — Portfolio Performance Endpoint

**Files:**
- Modify: `packages/api/api/routes/portfolios.py`
- Create: `packages/api/tests/test_portfolio_performance.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/api/tests/test_portfolio_performance.py`:

```python
"""Tests for GET /api/portfolio/performance."""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _mock_user():
    from api.auth import AuthenticatedUser
    return AuthenticatedUser(id="user-123", email="test@example.com")


def _mock_prices_df(tickers: list[str], n_days: int = 252) -> pd.DataFrame:
    """Generate synthetic price DataFrame."""
    idx = pd.date_range("2023-01-01", periods=n_days, freq="B")
    data = {}
    for i, t in enumerate(tickers):
        np.random.seed(i)
        returns = np.random.normal(0.0005, 0.01, n_days)
        data[t] = 100 * np.cumprod(1 + returns)
    return pd.DataFrame(data, index=idx)


def _mock_supabase_portfolio():
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "id": "port-1",
            "name": "Tech Portfolio",
            "tickers": ["AAPL", "MSFT"],
            "weights": [0.6, 0.4],
            "user_id": "user-123",
        }
    ]
    return mock_sb


@pytest.fixture(autouse=True)
def mock_auth_and_supabase():
    with patch("api.routes.portfolios.get_current_user", return_value=_mock_user()), \
         patch("api.routes.portfolios.get_user_client", return_value=_mock_supabase_portfolio()), \
         patch("api.routes.portfolios._perf_cache", {}):
        yield


def test_performance_returns_200():
    with patch(
        "api.routes.portfolios.fetch_prices",
        return_value=_mock_prices_df(["AAPL", "MSFT", "SPY"]),
    ):
        resp = client.get(
            "/api/portfolio/performance",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 200


def test_performance_response_shape():
    with patch(
        "api.routes.portfolios.fetch_prices",
        return_value=_mock_prices_df(["AAPL", "MSFT", "SPY"]),
    ):
        body = client.get(
            "/api/portfolio/performance",
            headers={"Authorization": "Bearer fake-token"},
        ).json()

        assert "curve" in body
        assert "positions" in body
        assert "stats" in body
        assert "portfolio_name" in body

        assert len(body["curve"]) > 0
        point = body["curve"][0]
        assert "date" in point and "value" in point and "benchmark" in point

        assert len(body["positions"]) == 2
        pos = body["positions"][0]
        for field in ("ticker", "weight", "price", "day_pct", "total_return"):
            assert field in pos

        stats = body["stats"]
        for field in ("sharpe", "max_drawdown", "total_return", "alpha"):
            assert field in stats


def test_performance_404_when_no_portfolio():
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    with patch("api.routes.portfolios.get_user_client", return_value=mock_sb):
        resp = client.get(
            "/api/portfolio/performance",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 404


def test_performance_cache_hit():
    """Second identical request should not call fetch_prices again."""
    with patch(
        "api.routes.portfolios.fetch_prices",
        return_value=_mock_prices_df(["AAPL", "MSFT", "SPY"]),
    ) as mock_fetch:
        client.get("/api/portfolio/performance", headers={"Authorization": "Bearer fake-token"})
        client.get("/api/portfolio/performance", headers={"Authorization": "Bearer fake-token"})
        assert mock_fetch.call_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/api && python -m pytest tests/test_portfolio_performance.py -v
```

Expected: `FAILED — endpoint /api/portfolio/performance returns 404` (not registered yet)

- [ ] **Step 3: Add the performance endpoint to `packages/api/api/routes/portfolios.py`**

Replace the full file with:

```python
"""REST endpoints for portfolio CRUD and performance computation."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import get_current_user, AuthenticatedUser
from api.supabase_client import get_user_client
from quant.data import fetch_prices, DataFetchError

router = APIRouter(tags=["portfolios"])
_bearer_scheme = HTTPBearer()

# In-memory cache: portfolio_id -> {"data": ..., "ts": float}
_perf_cache: dict[str, dict[str, Any]] = {}
_CACHE_TTL_SECONDS = 900  # 15 minutes


@router.get("/portfolios")
async def list_portfolios(
    user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    sb = get_user_client(credentials.credentials)
    result = (
        sb.table("portfolios")
        .select("id, name, tickers, weights, constraints, metadata, created_at, updated_at")
        .eq("user_id", user.id)
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data


@router.delete("/portfolios/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    sb = get_user_client(credentials.credentials)
    sb.table("portfolios").delete().eq("id", portfolio_id).execute()
    return {"deleted": portfolio_id}


@router.get("/portfolio/performance")
async def portfolio_performance(
    portfolio_id: str | None = None,
    user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    """Compute portfolio equity curve, position stats, and risk metrics.

    Always returns max available history (up to 5 years). The frontend slices
    by period client-side. Results cached for 15 minutes per portfolio_id.
    """
    sb = get_user_client(credentials.credentials)

    # Load portfolio — default to most recently updated
    query = (
        sb.table("portfolios")
        .select("id, name, tickers, weights, user_id")
        .eq("user_id", user.id)
        .order("updated_at", desc=True)
    )
    if portfolio_id:
        query = query.eq("id", portfolio_id)
    result = query.limit(1).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="No portfolio found")

    portfolio = result.data[0]
    cache_key = portfolio["id"]

    # Return cached result if fresh
    cached = _perf_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < _CACHE_TTL_SECONDS:
        return cached["data"]

    tickers: list[str] = portfolio["tickers"]
    weights: list[float] = portfolio["weights"]

    if len(tickers) != len(weights):
        raise HTTPException(status_code=422, detail="tickers and weights length mismatch")

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")

    all_tickers = list(dict.fromkeys(tickers + ["SPY"]))  # deduplicate, preserve order

    try:
        prices = await asyncio.to_thread(fetch_prices, all_tickers, start_date, end_date)
    except DataFetchError as exc:
        raise HTTPException(status_code=502, detail=f"Price fetch failed: {exc}")

    # --- Equity curve ---
    available = [t for t in tickers if t in prices.columns]
    available_weights = [weights[tickers.index(t)] for t in available]
    w = np.array(available_weights)
    if w.sum() > 0:
        w = w / w.sum()  # renormalize if any tickers missing

    port_prices = prices[available]
    returns = port_prices.pct_change().dropna()
    weighted_returns = (returns * w).sum(axis=1)
    cumulative = (1 + weighted_returns).cumprod() * 100

    spy_returns = prices["SPY"].pct_change().dropna()
    spy_cumulative = (1 + spy_returns).cumprod() * 100

    dates = cumulative.index.intersection(spy_cumulative.index)
    curve = [
        {
            "date": str(d.date()),
            "value": round(float(cumulative[d]), 4),
            "benchmark": round(float(spy_cumulative[d]), 4),
        }
        for d in dates
    ]

    # --- Position stats ---
    positions = []
    for ticker, weight in zip(tickers, weights):
        if ticker not in prices.columns or len(prices[ticker]) < 2:
            continue
        col = prices[ticker]
        current_price = float(col.iloc[-1])
        prev_price = float(col.iloc[-2])
        day_pct = (current_price - prev_price) / prev_price if prev_price != 0 else 0.0
        start_price = float(col.iloc[0])
        total_return = (current_price - start_price) / start_price if start_price != 0 else 0.0
        positions.append(
            {
                "ticker": ticker,
                "weight": weight,
                "price": round(current_price, 2),
                "day_pct": round(day_pct, 6),
                "total_return": round(total_return, 6),
            }
        )

    # --- Risk stats ---
    std = weighted_returns.std()
    sharpe = float(weighted_returns.mean() / std * np.sqrt(252)) if std != 0 else 0.0
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = float(drawdown.min())
    total_return = float(cumulative.iloc[-1] / 100 - 1) if len(cumulative) > 0 else 0.0
    spy_total = float(spy_cumulative[dates].iloc[-1] / 100 - 1) if len(dates) > 0 else 0.0
    alpha = total_return - spy_total

    data = {
        "curve": curve,
        "positions": positions,
        "stats": {
            "sharpe": round(sharpe, 4),
            "max_drawdown": round(max_drawdown, 4),
            "total_return": round(total_return, 4),
            "alpha": round(alpha, 4),
        },
        "portfolio_name": portfolio["name"],
    }

    _perf_cache[cache_key] = {"data": data, "ts": time.time()}
    return data
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd packages/api && python -m pytest tests/test_portfolio_performance.py -v
```

Expected: all 4 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/routes/portfolios.py packages/api/tests/test_portfolio_performance.py
git commit -m "feat: add GET /api/portfolio/performance with caching and parallel price fetching"
```

---

## Task 6: Frontend — usePortfolioPerformance Hook

**Files:**
- Create: `packages/web/src/hooks/usePortfolioPerformance.ts`

- [ ] **Step 1: Create `packages/web/src/hooks/usePortfolioPerformance.ts`**

```typescript
import { useCallback, useEffect, useMemo, useState } from "react";
import { listPortfolios, getPortfolioPerformance } from "@/api/client";
import type { Portfolio, PortfolioPerformance, PerformanceCurvePoint } from "@/api/client";

export type Period = "1m" | "3m" | "6m" | "1y" | "all";

const PERIOD_DAYS: Record<Period, number | null> = {
  "1m": 30,
  "3m": 90,
  "6m": 180,
  "1y": 365,
  "all": null,
};

export function usePortfolioPerformance(token: string | undefined) {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<Period>("1m");

  // Load portfolio list on mount
  useEffect(() => {
    if (!token) return;
    listPortfolios(token)
      .then((list) => {
        setPortfolios(list);
        if (list.length > 0) setSelectedId(list[0].id);
      })
      .catch((e) => setError(e.message));
  }, [token]);

  // Fetch performance when selected portfolio changes
  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    getPortfolioPerformance(token, selectedId)
      .then(setPerformance)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, selectedId]);

  const slicedCurve = useMemo((): PerformanceCurvePoint[] => {
    if (!performance) return [];
    const days = PERIOD_DAYS[period];
    if (days === null) return performance.curve;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString().slice(0, 10);
    return performance.curve.filter((p) => p.date >= cutoffStr);
  }, [performance, period]);

  const selectPortfolio = useCallback((id: string) => {
    setSelectedId(id);
  }, []);

  return {
    portfolios,
    selectedId,
    selectPortfolio,
    performance,
    slicedCurve,
    loading,
    error,
    period,
    setPeriod,
  };
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd packages/web && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/hooks/usePortfolioPerformance.ts
git commit -m "feat: add usePortfolioPerformance hook with period slicing"
```

---

## Task 7: Frontend — Dashboard Components

**Files:**
- Create: `packages/web/src/components/dashboard/EquityCurve.tsx`
- Create: `packages/web/src/components/dashboard/PositionsTable.tsx`
- Create: `packages/web/src/components/dashboard/HoldingsPie.tsx`

- [ ] **Step 1: Create `packages/web/src/components/dashboard/EquityCurve.tsx`**

```tsx
import Plot from "@/components/Plot";
import { BASE_LAYOUT, BASE_CONFIG } from "@/components/chat/charts/chart-defaults";
import type { PerformanceCurvePoint } from "@/api/client";
import type { Period } from "@/hooks/usePortfolioPerformance";
import { cn } from "@/lib/utils";

const PERIODS: Period[] = ["1m", "3m", "6m", "1y", "all"];

interface EquityCurveProps {
  curve: PerformanceCurvePoint[];
  period: Period;
  onPeriodChange: (p: Period) => void;
  loading?: boolean;
}

export default function EquityCurve({ curve, period, onPeriodChange, loading }: EquityCurveProps) {
  if (loading) {
    return (
      <div className="border border-border rounded-lg p-4">
        <div className="h-[200px] bg-muted/30 rounded animate-pulse" />
        <div className="flex justify-center gap-2 mt-3">
          {PERIODS.map((p) => (
            <div key={p} className="h-6 w-8 bg-muted/30 rounded-full animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const portfolioTrace = {
    x: curve.map((p) => p.date),
    y: curve.map((p) => p.value),
    type: "scatter" as const,
    mode: "lines" as const,
    name: "Portfolio",
    line: { color: "#111111", width: 2 },
    fill: "tozeroy" as const,
    fillcolor: "rgba(17,17,17,0.05)",
    hovertemplate: "%{x}<br>%{y:.1f}<extra>Portfolio</extra>",
  };

  const benchmarkTrace = {
    x: curve.map((p) => p.date),
    y: curve.map((p) => p.benchmark),
    type: "scatter" as const,
    mode: "lines" as const,
    name: "SPY",
    line: { color: "#cccccc", width: 1.5, dash: "dash" as const },
    hovertemplate: "%{x}<br>%{y:.1f}<extra>SPY</extra>",
  };

  return (
    <div className="border border-border rounded-lg p-4">
      <Plot
        data={[portfolioTrace, benchmarkTrace]}
        layout={{
          ...BASE_LAYOUT,
          height: 200,
          margin: { l: 48, r: 16, t: 8, b: 40 },
          showlegend: true,
          legend: { x: 0, y: 1.1, orientation: "h" as const, font: { size: 11 } },
          yaxis: {
            ...BASE_LAYOUT.yaxis,
            tickformat: ".0f",
            hoverformat: ".1f",
          },
          xaxis: {
            ...BASE_LAYOUT.xaxis,
            type: "date" as const,
          },
        }}
        config={BASE_CONFIG}
        style={{ width: "100%" }}
        useResizeHandler
      />
      <div className="flex justify-center gap-1 mt-2">
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => onPeriodChange(p)}
            className={cn(
              "text-xs px-3 py-1 rounded-full transition-colors",
              period === p
                ? "bg-foreground text-background"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {p.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `packages/web/src/components/dashboard/PositionsTable.tsx`**

```tsx
import type { PositionData } from "@/api/client";
import { cn } from "@/lib/utils";

interface PositionsTableProps {
  positions: PositionData[];
  totalValue: number;
  loading?: boolean;
}

function pct(n: number) {
  return `${n >= 0 ? "+" : ""}${(n * 100).toFixed(2)}%`;
}

function usd(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

export default function PositionsTable({ positions, totalValue, loading }: PositionsTableProps) {
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div className="px-4 py-2.5 border-b border-border">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Positions
        </span>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Ticker</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Weight</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Price</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Day</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Value</th>
            <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Return</th>
          </tr>
        </thead>
        <tbody>
          {loading
            ? Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-b border-border/50">
                  {Array.from({ length: 6 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-muted/40 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            : positions.map((pos) => (
                <tr key={pos.ticker} className="border-b border-border/50 last:border-0">
                  <td className="px-4 py-3 font-semibold">{pos.ticker}</td>
                  <td className="px-4 py-3 text-right text-muted-foreground">
                    {(pos.weight * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-right">{usd(pos.price)}</td>
                  <td
                    className={cn(
                      "px-4 py-3 text-right font-medium",
                      pos.day_pct >= 0 ? "text-green-600" : "text-red-600"
                    )}
                  >
                    {pct(pos.day_pct)}
                  </td>
                  <td className="px-4 py-3 text-right font-medium">
                    {usd(pos.weight * totalValue)}
                  </td>
                  <td
                    className={cn(
                      "px-4 py-3 text-right font-medium",
                      pos.total_return >= 0 ? "text-green-600" : "text-red-600"
                    )}
                  >
                    {pct(pos.total_return)}
                  </td>
                </tr>
              ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 3: Create `packages/web/src/components/dashboard/HoldingsPie.tsx`**

```tsx
import Plot from "@/components/Plot";
import { BASE_CONFIG } from "@/components/chat/charts/chart-defaults";
import type { PositionData } from "@/api/client";

interface HoldingsPieProps {
  positions: PositionData[];
  loading?: boolean;
}

const COLORS = ["#111111", "#555555", "#999999", "#cccccc", "#333333", "#777777"];

export default function HoldingsPie({ positions, loading }: HoldingsPieProps) {
  if (loading) {
    return (
      <div className="border border-border rounded-lg p-4 flex items-center justify-center">
        <div className="h-[160px] w-[160px] rounded-full bg-muted/30 animate-pulse" />
      </div>
    );
  }

  const trace = {
    labels: positions.map((p) => p.ticker),
    values: positions.map((p) => p.weight),
    type: "pie" as const,
    hole: 0.5,
    textinfo: "label+percent" as const,
    textposition: "outside" as const,
    marker: { colors: COLORS.slice(0, positions.length) },
    hovertemplate: "%{label}<br>%{percent}<extra></extra>",
  };

  return (
    <div className="border border-border rounded-lg p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
        Holdings
      </div>
      <Plot
        data={[trace as any]}
        layout={{
          paper_bgcolor: "#ffffff",
          plot_bgcolor: "#ffffff",
          margin: { l: 20, r: 20, t: 8, b: 8 },
          height: 160,
          showlegend: false,
          autosize: true,
        }}
        config={BASE_CONFIG}
        style={{ width: "100%" }}
        useResizeHandler
      />
    </div>
  );
}
```

- [ ] **Step 4: Verify TypeScript**

```bash
cd packages/web && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add packages/web/src/components/dashboard/
git commit -m "feat: add Dashboard components — EquityCurve, PositionsTable, HoldingsPie"
```

---

## Task 8: Frontend — Dashboard Page Rebuild

**Files:**
- Modify: `packages/web/src/pages/Dashboard.tsx`

- [ ] **Step 1: Replace `packages/web/src/pages/Dashboard.tsx`**

```tsx
import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { usePortfolioPerformance } from "@/hooks/usePortfolioPerformance";
import EquityCurve from "@/components/dashboard/EquityCurve";
import PositionsTable from "@/components/dashboard/PositionsTable";
import HoldingsPie from "@/components/dashboard/HoldingsPie";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

function usd(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

function pct(n: number) {
  return `${n >= 0 ? "+" : ""}${(n * 100).toFixed(2)}%`;
}

const TOTAL_VALUE_KEY = (id: string) => `portfolio_total_value_${id}`;

export default function Dashboard() {
  const { session } = useAuth();
  const token = session?.access_token;

  const {
    portfolios,
    selectedId,
    selectPortfolio,
    performance,
    slicedCurve,
    loading,
    error,
    period,
    setPeriod,
  } = usePortfolioPerformance(token);

  const [totalValue, setTotalValue] = useState<number>(100_000);
  const [valueInput, setValueInput] = useState<string>("$100,000");

  // Load persisted total value when portfolio changes
  useEffect(() => {
    if (!selectedId) return;
    const stored = localStorage.getItem(TOTAL_VALUE_KEY(selectedId));
    const val = stored ? parseFloat(stored) : 100_000;
    setTotalValue(val);
    setValueInput(
      new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(val)
    );
  }, [selectedId]);

  function handleValueBlur() {
    const cleaned = valueInput.replace(/[^0-9.]/g, "");
    const val = parseFloat(cleaned) || 100_000;
    setTotalValue(val);
    if (selectedId) localStorage.setItem(TOTAL_VALUE_KEY(selectedId), String(val));
    setValueInput(
      new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(val)
    );
  }

  const todayChange = performance
    ? performance.positions.reduce((acc, p) => acc + p.day_pct * p.weight, 0)
    : 0;
  const todayChangeDollar = todayChange * totalValue;
  const lastUpdated = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="py-6 space-y-4 max-w-4xl">
      {/* Selector bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground uppercase tracking-wide">Portfolio</span>
          <Select value={selectedId} onValueChange={selectPortfolio} disabled={portfolios.length === 0}>
            <SelectTrigger className="w-48 h-8 text-sm">
              <SelectValue placeholder={loading ? "Loading..." : "No portfolios"} />
            </SelectTrigger>
            <SelectContent>
              {portfolios.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Total Value</span>
          <input
            className="w-28 text-right text-sm font-semibold border border-border rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-foreground"
            value={valueInput}
            onChange={(e) => setValueInput(e.target.value)}
            onBlur={handleValueBlur}
            onKeyDown={(e) => e.key === "Enter" && handleValueBlur()}
          />
        </div>
      </div>

      {error && (
        <div className="text-sm text-red-600 border border-red-200 bg-red-50 rounded px-3 py-2">
          {error}
        </div>
      )}

      {/* Big portfolio value */}
      <div className="text-center py-2">
        <div className="text-4xl font-bold tracking-tight">{usd(totalValue)}</div>
        <div
          className={cn(
            "text-sm mt-1 font-medium",
            todayChange >= 0 ? "text-green-600" : "text-red-600"
          )}
        >
          {todayChange >= 0 ? "+" : ""}
          {usd(todayChangeDollar)} ({pct(todayChange)}) Today
        </div>
      </div>

      {/* Equity curve */}
      <EquityCurve
        curve={slicedCurve}
        period={period}
        onPeriodChange={setPeriod}
        loading={loading}
      />

      {/* Pie + stats */}
      <div className="grid grid-cols-2 gap-4">
        <HoldingsPie positions={performance?.positions ?? []} loading={loading} />
        <div className="grid grid-cols-2 gap-3">
          {[
            {
              label: "Total Return",
              value: performance ? pct(performance.stats.total_return) : "—",
              positive: (performance?.stats.total_return ?? 0) >= 0,
            },
            {
              label: "vs SPY",
              value: performance ? pct(performance.stats.alpha) : "—",
              positive: (performance?.stats.alpha ?? 0) >= 0,
            },
            {
              label: "Sharpe Ratio",
              value: performance ? performance.stats.sharpe.toFixed(2) : "—",
              positive: null,
            },
            {
              label: "Max Drawdown",
              value: performance ? pct(performance.stats.max_drawdown) : "—",
              positive: false,
            },
          ].map((stat) => (
            <div key={stat.label} className="border border-border rounded-lg p-3">
              <div className="text-xs text-muted-foreground">{stat.label}</div>
              <div
                className={cn(
                  "text-lg font-bold mt-1",
                  stat.positive === null
                    ? ""
                    : stat.positive
                    ? "text-green-600"
                    : "text-red-600"
                )}
              >
                {loading ? <div className="h-5 w-16 bg-muted/40 rounded animate-pulse" /> : stat.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Positions table */}
      <PositionsTable
        positions={performance?.positions ?? []}
        totalValue={totalValue}
        loading={loading}
      />

      <div className="text-xs text-muted-foreground text-right">
        Prices via yfinance · Last updated {lastUpdated}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd packages/web && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/pages/Dashboard.tsx
git commit -m "feat: rebuild Dashboard as Robinhood-style portfolio performance view"
```

---

## Task 9: Frontend — useTerminalPanel Hook

**Files:**
- Create: `packages/web/src/hooks/useTerminalPanel.ts`

- [ ] **Step 1: Create `packages/web/src/hooks/useTerminalPanel.ts`**

```typescript
import { useCallback, useEffect, useRef, useState } from "react";
import { getTerminalPanel } from "@/api/client";
import type { TerminalPanelResponse } from "@/api/client";

type Panel = "macro" | "indices" | "movers" | "heatmap" | "calendar";

export function useTerminalPanel(panel: Panel, intervalMs: number) {
  const [data, setData] = useState<TerminalPanelResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetch = useCallback(async () => {
    try {
      const ttl = Math.floor(intervalMs / 1000);
      const result = await getTerminalPanel(panel, ttl);
      setData(result);
      setLastUpdated(new Date());
      if (result.error) {
        setError(result.error_message ?? "Failed to load panel data");
      } else {
        setError(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setLoading(false);
    }
  }, [panel, intervalMs]);

  useEffect(() => {
    setLoading(true);
    fetch();

    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(fetch, intervalMs);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetch, intervalMs]);

  return { data, loading, error, lastUpdated, refetch: fetch };
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd packages/web && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/hooks/useTerminalPanel.ts
git commit -m "feat: add useTerminalPanel polling hook"
```

---

## Task 10: Frontend — Terminal Panel Components

**Files:**
- Create: `packages/web/src/components/terminal/PanelShell.tsx`
- Create: `packages/web/src/components/terminal/MacroPanel.tsx`
- Create: `packages/web/src/components/terminal/IndicesPanel.tsx`
- Create: `packages/web/src/components/terminal/MoversPanel.tsx`
- Create: `packages/web/src/components/terminal/HeatmapPanel.tsx`
- Create: `packages/web/src/components/terminal/CalendarPanel.tsx`

- [ ] **Step 1: Create `packages/web/src/components/terminal/PanelShell.tsx`**

Shared wrapper providing border, title, timestamp, error state, and skeleton.

```tsx
import { cn } from "@/lib/utils";

interface PanelShellProps {
  title: string;
  lastUpdated: Date | null;
  error: string | null;
  loading: boolean;
  onRetry?: () => void;
  children: React.ReactNode;
  className?: string;
}

export default function PanelShell({
  title,
  lastUpdated,
  error,
  loading,
  onRetry,
  children,
  className,
}: PanelShellProps) {
  const updatedStr = lastUpdated
    ? lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <div className={cn("border border-border rounded-lg overflow-hidden", className)}>
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </span>
        {updatedStr && (
          <span className="text-xs text-muted-foreground/60">Updated {updatedStr}</span>
        )}
      </div>
      <div className="p-4">
        {error ? (
          <div className="flex items-center justify-between text-sm text-red-600">
            <span>Failed to load</span>
            {onRetry && (
              <button onClick={onRetry} className="text-xs underline ml-2">
                Retry
              </button>
            )}
          </div>
        ) : loading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-4 bg-muted/30 rounded animate-pulse" />
            ))}
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `packages/web/src/components/terminal/MacroPanel.tsx`**

The backend returns raw OpenBB FRED series data. This component normalizes it for display.

```tsx
import { useTerminalPanel } from "@/hooks/useTerminalPanel";
import PanelShell from "./PanelShell";
import { cn } from "@/lib/utils";

interface MacroField {
  key: string;
  label: string;
  decimals: number;
  suffix: string;
  invertChange?: boolean;
}

const FIELDS: MacroField[] = [
  { key: "FEDFUNDS", label: "Fed Funds", decimals: 2, suffix: "%" },
  { key: "DGS2", label: "2Y Treasury", decimals: 2, suffix: "%" },
  { key: "DGS10", label: "10Y Treasury", decimals: 2, suffix: "%" },
  { key: "CPIAUCSL", label: "CPI YoY", decimals: 1, suffix: "%" },
  { key: "VIXCLS", label: "VIX", decimals: 1, suffix: "" },
];

function extractSeriesLatest(rawData: any[], symbol: string): { current: number | null; prev: number | null; sparkline: number[] } {
  if (!Array.isArray(rawData) || rawData.length === 0) {
    return { current: null, prev: null, sparkline: [] };
  }
  // FRED data comes as records with a 'symbol' or 'date'/'value' field
  const rows = rawData
    .filter((r: any) => {
      const sym = r.symbol ?? r.series_id ?? "";
      return symbol === "" || sym === symbol || Object.keys(r).includes("value");
    })
    .sort((a: any, b: any) => {
      const da = a.date ?? a.timestamp ?? "";
      const db = b.date ?? b.timestamp ?? "";
      return da.localeCompare(db);
    });

  const values = rows.map((r: any) => parseFloat(r.value ?? r.close ?? 0)).filter(isFinite);
  return {
    current: values.length > 0 ? values[values.length - 1] : null,
    prev: values.length > 1 ? values[values.length - 2] : null,
    sparkline: values.slice(-30),
  };
}

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const h = 24;
  const w = 64;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const last = values[values.length - 1];
  const first = values[0];
  const color = last >= first ? "#16a34a" : "#dc2626";
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: w, height: h }}>
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="1.5" />
    </svg>
  );
}

interface MacroPanelProps {
  intervalMs: number;
}

export default function MacroPanel({ intervalMs }: MacroPanelProps) {
  const { data, loading, error, lastUpdated, refetch } = useTerminalPanel("macro", intervalMs);
  const rawData: any[] = data?.raw_data ?? [];

  return (
    <PanelShell title="Macro" lastUpdated={lastUpdated} error={error} loading={loading} onRetry={refetch}>
      <div className="flex gap-0 overflow-x-auto -mx-4 px-4">
        {FIELDS.map((field, i) => {
          const { current, prev, sparkline } = extractSeriesLatest(rawData, field.key);
          const change = current !== null && prev !== null ? current - prev : null;
          return (
            <div
              key={field.key}
              className={cn(
                "flex-1 min-w-[90px] px-3",
                i < FIELDS.length - 1 && "border-r border-border"
              )}
            >
              <div className="text-xs text-muted-foreground mb-1">{field.label}</div>
              <div className="text-base font-bold">
                {current !== null ? `${current.toFixed(field.decimals)}${field.suffix}` : "—"}
              </div>
              {change !== null && (
                <div
                  className={cn(
                    "text-xs font-medium",
                    change >= 0 ? "text-green-600" : "text-red-600"
                  )}
                >
                  {change >= 0 ? "+" : ""}
                  {change.toFixed(field.decimals)}
                </div>
              )}
              <div className="mt-1">
                <Sparkline values={sparkline} />
              </div>
            </div>
          );
        })}
      </div>
    </PanelShell>
  );
}
```

- [ ] **Step 3: Create `packages/web/src/components/terminal/IndicesPanel.tsx`**

```tsx
import { useTerminalPanel } from "@/hooks/useTerminalPanel";
import PanelShell from "./PanelShell";
import { cn } from "@/lib/utils";

const MAJOR = ["SPY", "QQQ", "IWM", "DIA"];
const SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLC"];
const ALL_TICKERS = [...MAJOR, ...SECTORS];

function Sparkline5({ values }: { values: number[] }) {
  if (values.length < 2) return <div className="w-10 h-4" />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const h = 16;
  const w = 40;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const last = values[values.length - 1];
  const first = values[0];
  const color = last >= first ? "#16a34a" : "#dc2626";
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: w, height: h }}>
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="1.5" />
    </svg>
  );
}

function buildRows(rawData: any[]): { ticker: string; price: number | null; dayPct: number | null; sparkline: number[]; isSector: boolean }[] {
  if (!Array.isArray(rawData) || rawData.length === 0) {
    return ALL_TICKERS.map((t) => ({ ticker: t, price: null, dayPct: null, sparkline: [], isSector: SECTORS.includes(t) }));
  }

  const byTicker: Record<string, any[]> = {};
  for (const row of rawData) {
    const ticker = row.symbol ?? row.ticker ?? "";
    if (!byTicker[ticker]) byTicker[ticker] = [];
    byTicker[ticker].push(row);
  }

  return ALL_TICKERS.map((ticker) => {
    const rows = (byTicker[ticker] ?? []).sort((a: any, b: any) =>
      (a.date ?? "").localeCompare(b.date ?? "")
    );
    const closes = rows.map((r: any) => parseFloat(r.close ?? r.value ?? 0)).filter(isFinite);
    const price = closes.length > 0 ? closes[closes.length - 1] : null;
    const prev = closes.length > 1 ? closes[closes.length - 2] : null;
    const dayPct = price !== null && prev !== null && prev !== 0 ? (price - prev) / prev : null;
    return { ticker, price, dayPct, sparkline: closes.slice(-5), isSector: SECTORS.includes(ticker) };
  });
}

export default function IndicesPanel({ intervalMs }: { intervalMs: number }) {
  const { data, loading, error, lastUpdated, refetch } = useTerminalPanel("indices", intervalMs);
  const rows = buildRows(data?.raw_data ?? []);

  return (
    <PanelShell title="Equity Indices" lastUpdated={lastUpdated} error={error} loading={loading} onRetry={refetch}>
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left py-1.5 font-medium text-muted-foreground">ETF</th>
            <th className="text-right py-1.5 font-medium text-muted-foreground">Price</th>
            <th className="text-right py-1.5 font-medium text-muted-foreground">Day</th>
            <th className="text-right py-1.5 font-medium text-muted-foreground">5D</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.ticker} className="border-b border-border/40 last:border-0">
              <td className={cn("py-2 font-semibold", row.isSector && "text-muted-foreground")}>
                {row.ticker}
              </td>
              <td className={cn("text-right py-2", row.isSector && "text-muted-foreground")}>
                {row.price !== null ? `$${row.price.toFixed(2)}` : "—"}
              </td>
              <td
                className={cn(
                  "text-right py-2 font-medium",
                  row.dayPct === null
                    ? "text-muted-foreground"
                    : row.dayPct >= 0
                    ? "text-green-600"
                    : "text-red-600"
                )}
              >
                {row.dayPct !== null
                  ? `${row.dayPct >= 0 ? "+" : ""}${(row.dayPct * 100).toFixed(2)}%`
                  : "—"}
              </td>
              <td className="text-right py-2">
                <Sparkline5 values={row.sparkline} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </PanelShell>
  );
}
```

- [ ] **Step 4: Create `packages/web/src/components/terminal/MoversPanel.tsx`**

```tsx
import { useTerminalPanel } from "@/hooks/useTerminalPanel";
import PanelShell from "./PanelShell";
import { cn } from "@/lib/utils";

function extractMovers(rawData: any[]): {
  gainers: { ticker: string; pct: number }[];
  losers: { ticker: string; pct: number }[];
} {
  if (!Array.isArray(rawData) || rawData.length === 0) {
    return { gainers: [], losers: [] };
  }
  const withPct = rawData
    .map((r: any) => ({
      ticker: r.symbol ?? r.ticker ?? "",
      pct: parseFloat(r.percent_change ?? r.change_percent ?? r.day_change_percent ?? 0),
    }))
    .filter((r) => r.ticker && isFinite(r.pct))
    .sort((a, b) => b.pct - a.pct);

  return {
    gainers: withPct.slice(0, 5),
    losers: withPct.slice(-5).reverse(),
  };
}

export default function MoversPanel({ intervalMs }: { intervalMs: number }) {
  const { data, loading, error, lastUpdated, refetch } = useTerminalPanel("movers", intervalMs);
  const { gainers, losers } = extractMovers(data?.raw_data ?? []);

  return (
    <PanelShell
      title="Top Movers — S&P 500"
      lastUpdated={lastUpdated}
      error={error}
      loading={loading}
      onRetry={refetch}
    >
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs font-semibold text-green-600 uppercase tracking-wide mb-2">
            Gainers
          </div>
          <table className="w-full text-xs border-collapse">
            <tbody>
              {gainers.length === 0
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      <td className="py-1.5">
                        <div className="h-3 bg-muted/30 rounded animate-pulse" />
                      </td>
                    </tr>
                  ))
                : gainers.map((g) => (
                    <tr key={g.ticker} className="border-b border-border/30 last:border-0">
                      <td className="py-1.5 font-semibold">{g.ticker}</td>
                      <td className="py-1.5 text-right text-green-600 font-medium">
                        +{g.pct.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
        <div>
          <div className="text-xs font-semibold text-red-600 uppercase tracking-wide mb-2">
            Losers
          </div>
          <table className="w-full text-xs border-collapse">
            <tbody>
              {losers.length === 0
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      <td className="py-1.5">
                        <div className="h-3 bg-muted/30 rounded animate-pulse" />
                      </td>
                    </tr>
                  ))
                : losers.map((l) => (
                    <tr key={l.ticker} className="border-b border-border/30 last:border-0">
                      <td className="py-1.5 font-semibold">{l.ticker}</td>
                      <td className="py-1.5 text-right text-red-600 font-medium">
                        {l.pct.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      </div>
    </PanelShell>
  );
}
```

- [ ] **Step 5: Create `packages/web/src/components/terminal/HeatmapPanel.tsx`**

```tsx
import { useTerminalPanel } from "@/hooks/useTerminalPanel";
import PanelShell from "./PanelShell";

const SECTORS = ["XLK", "XLC", "XLY", "XLE", "XLV", "XLF", "XLI", "XLU", "XLRE"];

function dayPctForTicker(rawData: any[], ticker: string): number | null {
  const rows = rawData
    .filter((r: any) => (r.symbol ?? r.ticker ?? "") === ticker)
    .sort((a: any, b: any) => (a.date ?? "").localeCompare(b.date ?? ""));
  if (rows.length < 2) return null;
  const close = (r: any) => parseFloat(r.close ?? r.value ?? 0);
  const curr = close(rows[rows.length - 1]);
  const prev = close(rows[rows.length - 2]);
  return prev !== 0 ? (curr - prev) / prev : null;
}

function pctToColor(pct: number | null): string {
  if (pct === null) return "#f5f5f5";
  const intensity = Math.min(Math.abs(pct) / 0.03, 1); // saturate at ±3%
  if (pct > 0) {
    const g = Math.round(163 + intensity * (22 - 163));
    return `rgb(${Math.round(22 + intensity * (22 - 22))}, ${g}, ${Math.round(74 + intensity * (74 - 74))})`;
  } else {
    const r = Math.round(220 - intensity * (220 - 185));
    return `rgb(${r}, ${Math.round(38 + intensity * 10)}, ${Math.round(38 + intensity * 10)})`;
  }
}

// Simpler: interpolate between fixed stops
function pctToColorSimple(pct: number | null): { bg: string; text: string } {
  if (pct === null) return { bg: "#f5f5f5", text: "#666" };
  const clamped = Math.max(-0.03, Math.min(0.03, pct));
  const t = (clamped + 0.03) / 0.06; // 0=red, 0.5=white, 1=green
  if (t >= 0.5) {
    const intensity = (t - 0.5) * 2;
    const g = Math.round(200 + intensity * 55);
    const rb = Math.round(200 - intensity * 150);
    return { bg: `rgb(${rb},${g},${rb})`, text: intensity > 0.5 ? "#fff" : "#111" };
  } else {
    const intensity = (0.5 - t) * 2;
    const r = Math.round(200 + intensity * 55);
    const gb = Math.round(200 - intensity * 160);
    return { bg: `rgb(${r},${gb},${gb})`, text: intensity > 0.5 ? "#fff" : "#111" };
  }
}

export default function HeatmapPanel({ intervalMs }: { intervalMs: number }) {
  const { data, loading, error, lastUpdated, refetch } = useTerminalPanel("heatmap", intervalMs);
  const rawData: any[] = data?.raw_data ?? [];

  return (
    <PanelShell
      title="Sector Heatmap — Day %"
      lastUpdated={lastUpdated}
      error={error}
      loading={loading}
      onRetry={refetch}
    >
      <div className="grid grid-cols-3 gap-1.5">
        {SECTORS.map((ticker) => {
          const pct = loading ? null : dayPctForTicker(rawData, ticker);
          const { bg, text } = pctToColorSimple(pct);
          return (
            <div
              key={ticker}
              style={{ backgroundColor: loading ? undefined : bg, color: loading ? undefined : text }}
              className={`rounded p-2 text-xs ${loading ? "bg-muted/30 animate-pulse" : ""}`}
            >
              {!loading && (
                <>
                  <div className="font-semibold">{ticker}</div>
                  <div>{pct !== null ? `${pct >= 0 ? "+" : ""}${(pct * 100).toFixed(2)}%` : "—"}</div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </PanelShell>
  );
}
```

- [ ] **Step 6: Create `packages/web/src/components/terminal/CalendarPanel.tsx`**

```tsx
import { useTerminalPanel } from "@/hooks/useTerminalPanel";
import PanelShell from "./PanelShell";

const IMPORTANT_EVENTS = [
  "fomc", "cpi", "ppi", "nonfarm", "jobs", "unemployment", "gdp", "retail", "pce", "claims"
];

function extractEvents(rawData: any[]): { date: string; event: string; consensus: string | null }[] {
  if (!Array.isArray(rawData) || rawData.length === 0) return [];
  return rawData
    .filter((r: any) => {
      const name = (r.event ?? r.name ?? r.description ?? "").toLowerCase();
      return IMPORTANT_EVENTS.some((k) => name.includes(k));
    })
    .sort((a: any, b: any) => (a.date ?? "").localeCompare(b.date ?? ""))
    .slice(0, 8)
    .map((r: any) => ({
      date: r.date ? new Date(r.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "—",
      event: r.event ?? r.name ?? r.description ?? "Unknown",
      consensus: r.consensus_estimate ?? r.consensus ?? r.estimate ?? null,
    }));
}

export default function CalendarPanel({ intervalMs }: { intervalMs: number }) {
  const { data, loading, error, lastUpdated, refetch } = useTerminalPanel("calendar", intervalMs);
  const events = extractEvents(data?.raw_data ?? []);

  return (
    <PanelShell
      title="Macro Calendar"
      lastUpdated={lastUpdated}
      error={error}
      loading={loading}
      onRetry={refetch}
    >
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left py-1.5 font-medium text-muted-foreground">Date</th>
            <th className="text-left py-1.5 font-medium text-muted-foreground">Event</th>
            <th className="text-right py-1.5 font-medium text-muted-foreground">Consensus</th>
          </tr>
        </thead>
        <tbody>
          {events.length === 0 && !loading ? (
            <tr>
              <td colSpan={3} className="py-4 text-center text-muted-foreground">
                No upcoming events
              </td>
            </tr>
          ) : (
            (loading ? Array.from({ length: 5 }) : events).map((ev: any, i) => (
              <tr key={i} className="border-b border-border/40 last:border-0">
                {loading ? (
                  <td colSpan={3} className="py-2">
                    <div className="h-3 bg-muted/30 rounded animate-pulse" />
                  </td>
                ) : (
                  <>
                    <td className="py-2 text-muted-foreground whitespace-nowrap pr-3">{ev.date}</td>
                    <td className="py-2 font-medium">{ev.event}</td>
                    <td className="py-2 text-right text-muted-foreground">{ev.consensus ?? "—"}</td>
                  </>
                )}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </PanelShell>
  );
}
```

- [ ] **Step 7: Verify TypeScript**

```bash
cd packages/web && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 8: Commit**

```bash
git add packages/web/src/components/terminal/
git commit -m "feat: add Terminal panel components — PanelShell, Macro, Indices, Movers, Heatmap, Calendar"
```

---

## Task 11: Frontend — Terminal Page

**Files:**
- Modify: `packages/web/src/pages/Terminal.tsx` (replace the stub)

- [ ] **Step 1: Replace `packages/web/src/pages/Terminal.tsx`**

```tsx
import { useEffect, useRef, useState } from "react";
import MacroPanel from "@/components/terminal/MacroPanel";
import IndicesPanel from "@/components/terminal/IndicesPanel";
import MoversPanel from "@/components/terminal/MoversPanel";
import HeatmapPanel from "@/components/terminal/HeatmapPanel";
import CalendarPanel from "@/components/terminal/CalendarPanel";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const INTERVAL_OPTIONS = [
  { label: "1 min", ms: 60_000 },
  { label: "5 min", ms: 300_000 },
  { label: "15 min", ms: 900_000 },
  { label: "30 min", ms: 1_800_000 },
];

const STORAGE_KEY = "terminal_refresh_interval_ms";

function getStoredInterval(): number {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    const n = parseInt(stored, 10);
    if (INTERVAL_OPTIONS.some((o) => o.ms === n)) return n;
  }
  return 300_000; // default 5 min
}

export default function Terminal() {
  const [intervalMs, setIntervalMs] = useState<number>(getStoredInterval);
  const [countdown, setCountdown] = useState<number>(intervalMs / 1000);
  const lastTickRef = useRef<number>(Date.now());
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Countdown timer — ticks every second
  useEffect(() => {
    setCountdown(intervalMs / 1000);
    lastTickRef.current = Date.now();

    if (countdownRef.current) clearInterval(countdownRef.current);
    countdownRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) return intervalMs / 1000;
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [intervalMs]);

  function handleIntervalChange(value: string) {
    const ms = parseInt(value, 10);
    setIntervalMs(ms);
    localStorage.setItem(STORAGE_KEY, String(ms));
  }

  const mins = Math.floor(countdown / 60);
  const secs = countdown % 60;
  const countdownStr = `${mins}:${String(secs).padStart(2, "0")}`;

  return (
    <div className="py-6 space-y-3">
      {/* Header bar */}
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-base font-semibold tracking-tight">Market Overview</h1>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">Refresh</span>
          <Select value={String(intervalMs)} onValueChange={handleIntervalChange}>
            <SelectTrigger className="w-24 h-7 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {INTERVAL_OPTIONS.map((o) => (
                <SelectItem key={o.ms} value={String(o.ms)}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <span className="text-xs text-muted-foreground/60 tabular-nums">
            Next in {countdownStr}
          </span>
        </div>
      </div>

      {/* Row 1: Macro (full width) */}
      <MacroPanel intervalMs={intervalMs} />

      {/* Row 2: Indices + Movers */}
      <div className="grid grid-cols-2 gap-3">
        <IndicesPanel intervalMs={intervalMs} />
        <MoversPanel intervalMs={intervalMs} />
      </div>

      {/* Row 3: Heatmap + Calendar */}
      <div className="grid grid-cols-2 gap-3">
        <HeatmapPanel intervalMs={intervalMs} />
        <CalendarPanel intervalMs={intervalMs} />
      </div>

      <div className="text-xs text-muted-foreground text-right">
        All data via OpenBB · Auto-refreshes every{" "}
        {INTERVAL_OPTIONS.find((o) => o.ms === intervalMs)?.label ?? "5 min"}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd packages/web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Run all backend tests to confirm nothing broke**

```bash
cd packages/api && python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add packages/web/src/pages/Terminal.tsx
git commit -m "feat: add Terminal tab with live market overview grid and configurable refresh interval"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Task |
|-----------------|------|
| Nav: 4 tabs only (Chat, Dashboard, Saved, Terminal) | Task 1 |
| Remove Covariance, Portfolio, Backtest routes + files | Task 1 |
| Tool analyses remain as Chat inline Chart Manifests | Not changed (existing behavior preserved) |
| Dashboard: portfolio dropdown, default most recent | Task 8 |
| Dashboard: total value input, persisted per portfolio | Task 8 |
| Dashboard: large portfolio value + day change | Task 8 |
| Dashboard: full-width responsive equity curve | Task 7 (EquityCurve + useResizeHandler) |
| Dashboard: SPY benchmark overlay | Task 7, Task 5 |
| Dashboard: 1M/3M/6M/1Y/All time selector, client-side slice | Task 6 (usePortfolioPerformance.slicedCurve) |
| Dashboard: pie chart of holdings | Task 7 (HoldingsPie) |
| Dashboard: risk stats (Sharpe, Max DD, Total Return, Alpha) | Task 5 (backend), Task 8 (frontend) |
| Dashboard: positions table (Ticker/Weight/Price/Day%/Value/$\|Return) | Task 7 (PositionsTable) |
| Dashboard: skeleton loading states | Tasks 7, 8 |
| Dashboard: portfolios sorted desc by updated_at | Task 5 (`.order("updated_at", desc=True)` already present) |
| Terminal: 5 panels in 3-row grid | Task 11 |
| Terminal: Macro panel (6 FRED fields + sparklines) | Task 10 (MacroPanel) |
| Terminal: Equity Indices panel (SPY/QQQ/IWM/DIA + sectors, 5D sparkline) | Task 10 (IndicesPanel) |
| Terminal: Top Movers (5 gainers + 5 losers) | Task 10 (MoversPanel) |
| Terminal: Sector Heatmap (9 sectors, color-coded) | Task 10 (HeatmapPanel) |
| Terminal: Macro Calendar (8 upcoming events, consensus) | Task 10 (CalendarPanel) |
| Terminal: all data via openbb_query codegen loop | Tasks 3, 4 (terminal_prompts + routes/terminal.py) |
| Terminal: per-panel last-updated timestamp | Task 10 (PanelShell) |
| Terminal: configurable refresh interval (localStorage) | Task 11 |
| Terminal: countdown timer in header | Task 11 |
| Terminal: graceful per-panel error state | Task 10 (PanelShell), Task 9 (useTerminalPanel) |
| Backend: server-side cache for terminal panels | Task 4 (routes/terminal.py) |
| Backend: server-side cache for portfolio performance (15 min) | Task 5 |
| Backend: parallel price fetching (asyncio.to_thread) | Task 5 |
| White/black design system, red/green for price directionality only | All frontend tasks |

All spec requirements covered.
