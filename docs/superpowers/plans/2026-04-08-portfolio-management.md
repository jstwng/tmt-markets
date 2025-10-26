# Portfolio Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full portfolio CRUD to the dashboard — create, rename, edit holdings, delete — all inline with a minimal-diff edit mode toggle.

**Architecture:** Edit mode lives entirely in `Dashboard.tsx` as a discriminated union state. Pure math utilities (weight/amount calculations) extracted to a testable module. Backend gains POST + PATCH endpoints; the frontend API client wraps all four CRUD operations.

**Tech Stack:** FastAPI + Supabase (backend), React 19 + TypeScript + Tailwind + Vitest (frontend), pytest + FastAPI TestClient (backend tests)

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `packages/api/api/routes/portfolios.py` | Modify | Add POST + PATCH routes + Pydantic models |
| `packages/api/tests/test_portfolio_crud.py` | Create | Tests for POST + PATCH |
| `packages/web/src/lib/portfolio-math.ts` | Create | Pure functions: computeTotal, computeWeights, scaleAmounts |
| `packages/web/src/lib/portfolio-math.test.ts` | Create | Vitest tests for math utilities |
| `packages/web/src/api/client.ts` | Modify | Add createPortfolio, updatePortfolio, deletePortfolio |
| `packages/web/src/hooks/usePortfolioPerformance.ts` | Modify | Expose refetchPortfolios, refetchPerformance |
| `packages/web/src/components/dashboard/PositionsTable.tsx` | Modify | Add isEditMode prop + editable rows |
| `packages/web/src/pages/Dashboard.tsx` | Modify | Edit mode state machine, all header controls, empty state |

---

## Task 1: Backend — POST /api/portfolios

**Files:**
- Modify: `packages/api/api/routes/portfolios.py`
- Create: `packages/api/tests/test_portfolio_crud.py`

- [ ] **Step 1: Write the failing test**

Create `packages/api/tests/test_portfolio_crud.py`:

```python
"""Tests for POST /api/portfolios and PATCH /api/portfolios/{id}."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from api.auth import get_current_user, AuthenticatedUser

client = TestClient(app)

FAKE_PORTFOLIO = {
    "id": "port-abc",
    "name": "My Portfolio",
    "tickers": ["AAPL"],
    "weights": [1.0],
    "constraints": None,
    "metadata": None,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
}


def _mock_user():
    return AuthenticatedUser(id="user-123", email="test@example.com")


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: _mock_user()
    yield
    app.dependency_overrides.clear()


def _insert_mock(returned_data):
    mock_sb = MagicMock()
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = returned_data
    return mock_sb


def test_create_portfolio_returns_201():
    with patch("api.routes.portfolios.get_user_client", return_value=_insert_mock([FAKE_PORTFOLIO])):
        resp = client.post(
            "/api/portfolios",
            json={"name": "My Portfolio", "tickers": ["AAPL"], "weights": [1.0]},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "My Portfolio"
    assert body["id"] == "port-abc"


def test_create_portfolio_empty_holdings():
    empty = {**FAKE_PORTFOLIO, "tickers": [], "weights": []}
    with patch("api.routes.portfolios.get_user_client", return_value=_insert_mock([empty])):
        resp = client.post(
            "/api/portfolios",
            json={"name": "Empty", "tickers": [], "weights": []},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 201
    assert resp.json()["tickers"] == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd packages/api && python -m pytest tests/test_portfolio_crud.py::test_create_portfolio_returns_201 -v
```

Expected: FAIL with `422` or `404` (route doesn't exist yet).

- [ ] **Step 3: Add Pydantic models and POST route to portfolios.py**

Add after the existing imports in `packages/api/api/routes/portfolios.py` (after line 17, after `router = APIRouter(...)`):

```python
from pydantic import BaseModel


class CreatePortfolioRequest(BaseModel):
    name: str
    tickers: list[str] = []
    weights: list[float] = []


class UpdatePortfolioRequest(BaseModel):
    name: str
    tickers: list[str]
    weights: list[float]
```

Add after the existing `list_portfolios` route:

```python
@router.post("/portfolios", status_code=201)
async def create_portfolio(
    payload: CreatePortfolioRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    sb = get_user_client(credentials.credentials)
    result = (
        sb.table("portfolios")
        .insert(
            {
                "user_id": user.id,
                "name": payload.name,
                "tickers": payload.tickers,
                "weights": payload.weights,
            }
        )
        .execute()
    )
    return result.data[0]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd packages/api && python -m pytest tests/test_portfolio_crud.py::test_create_portfolio_returns_201 tests/test_portfolio_crud.py::test_create_portfolio_empty_holdings -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/routes/portfolios.py packages/api/tests/test_portfolio_crud.py
git commit -m "feat: add POST /api/portfolios endpoint"
```

---

## Task 2: Backend — PATCH /api/portfolios/{id}

**Files:**
- Modify: `packages/api/api/routes/portfolios.py`
- Modify: `packages/api/tests/test_portfolio_crud.py`

- [ ] **Step 1: Write the failing tests**

Append to `packages/api/tests/test_portfolio_crud.py`:

```python
def _update_mock(returned_data):
    mock_sb = MagicMock()
    mock_sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = returned_data
    return mock_sb


def test_update_portfolio_returns_200():
    updated = {**FAKE_PORTFOLIO, "name": "Renamed", "tickers": ["AAPL", "MSFT"], "weights": [0.6, 0.4]}
    with patch("api.routes.portfolios.get_user_client", return_value=_update_mock([updated])):
        resp = client.patch(
            "/api/portfolios/port-abc",
            json={"name": "Renamed", "tickers": ["AAPL", "MSFT"], "weights": [0.6, 0.4]},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"
    assert resp.json()["tickers"] == ["AAPL", "MSFT"]


def test_update_portfolio_404_when_not_found():
    with patch("api.routes.portfolios.get_user_client", return_value=_update_mock([])):
        resp = client.patch(
            "/api/portfolios/nonexistent",
            json={"name": "X", "tickers": [], "weights": []},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 404


def test_update_portfolio_clears_perf_cache():
    updated = {**FAKE_PORTFOLIO}
    fake_cache = {"port-abc": {"data": {}, "ts": 9999999999.0}}
    with patch("api.routes.portfolios.get_user_client", return_value=_update_mock([updated])), \
         patch("api.routes.portfolios._perf_cache", fake_cache):
        client.patch(
            "/api/portfolios/port-abc",
            json={"name": "My Portfolio", "tickers": ["AAPL"], "weights": [1.0]},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert "port-abc" not in fake_cache
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/api && python -m pytest tests/test_portfolio_crud.py::test_update_portfolio_returns_200 -v
```

Expected: FAIL (route doesn't exist).

- [ ] **Step 3: Add PATCH route to portfolios.py**

Add after the `create_portfolio` route:

```python
@router.patch("/portfolios/{portfolio_id}")
async def update_portfolio(
    portfolio_id: str,
    payload: UpdatePortfolioRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    sb = get_user_client(credentials.credentials)
    result = (
        sb.table("portfolios")
        .update(
            {
                "name": payload.name,
                "tickers": payload.tickers,
                "weights": payload.weights,
            }
        )
        .eq("id", portfolio_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    _perf_cache.pop(portfolio_id, None)
    return result.data[0]
```

- [ ] **Step 4: Run all CRUD tests**

```bash
cd packages/api && python -m pytest tests/test_portfolio_crud.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Run full backend test suite to check no regressions**

```bash
cd packages/api && python -m pytest --ignore=tests/test_openbb_sandbox.py --ignore=tests/test_openbb_codegen.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add packages/api/api/routes/portfolios.py packages/api/tests/test_portfolio_crud.py
git commit -m "feat: add PATCH /api/portfolios/{id} endpoint with cache invalidation"
```

---

## Task 3: Portfolio Math Utilities

**Files:**
- Create: `packages/web/src/lib/portfolio-math.ts`
- Create: `packages/web/src/lib/portfolio-math.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `packages/web/src/lib/portfolio-math.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { computeTotal, computeWeights, scaleAmounts } from "./portfolio-math";
import type { DraftPosition } from "./portfolio-math";

const pos = (ticker: string, amount: number): DraftPosition => ({ ticker, amount });

describe("computeTotal", () => {
  it("sums all amounts", () => {
    expect(computeTotal([pos("A", 600), pos("B", 400)])).toBe(1000);
  });
  it("returns 0 for empty array", () => {
    expect(computeTotal([])).toBe(0);
  });
  it("handles single position", () => {
    expect(computeTotal([pos("A", 50000)])).toBe(50000);
  });
});

describe("computeWeights", () => {
  it("returns proportional weights", () => {
    const w = computeWeights([pos("A", 600), pos("B", 400)]);
    expect(w[0]).toBeCloseTo(0.6);
    expect(w[1]).toBeCloseTo(0.4);
  });
  it("weights sum to 1", () => {
    const w = computeWeights([pos("A", 333), pos("B", 333), pos("C", 334)]);
    expect(w.reduce((s, x) => s + x, 0)).toBeCloseTo(1);
  });
  it("returns zeros when total is 0", () => {
    expect(computeWeights([pos("A", 0), pos("B", 0)])).toEqual([0, 0]);
  });
  it("returns empty array for no positions", () => {
    expect(computeWeights([])).toEqual([]);
  });
});

describe("scaleAmounts", () => {
  it("scales proportionally to new total", () => {
    const scaled = scaleAmounts([pos("A", 600), pos("B", 400)], 2000);
    expect(scaled[0].amount).toBeCloseTo(1200);
    expect(scaled[1].amount).toBeCloseTo(800);
  });
  it("preserves tickers", () => {
    const scaled = scaleAmounts([pos("AAPL", 500)], 1000);
    expect(scaled[0].ticker).toBe("AAPL");
  });
  it("distributes evenly when current total is 0", () => {
    const scaled = scaleAmounts([pos("A", 0), pos("B", 0)], 1000);
    expect(scaled[0].amount).toBeCloseTo(500);
    expect(scaled[1].amount).toBeCloseTo(500);
  });
  it("does not mutate original", () => {
    const original = [pos("A", 500)];
    scaleAmounts(original, 2000);
    expect(original[0].amount).toBe(500);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/web && npm test -- portfolio-math
```

Expected: FAIL — `portfolio-math` module not found.

- [ ] **Step 3: Implement portfolio-math.ts**

Create `packages/web/src/lib/portfolio-math.ts`:

```typescript
export interface DraftPosition {
  ticker: string;
  amount: number;
}

export function computeTotal(positions: DraftPosition[]): number {
  return positions.reduce((sum, p) => sum + p.amount, 0);
}

export function computeWeights(positions: DraftPosition[]): number[] {
  const total = computeTotal(positions);
  if (total === 0) return positions.map(() => 0);
  return positions.map((p) => p.amount / total);
}

export function scaleAmounts(positions: DraftPosition[], newTotal: number): DraftPosition[] {
  const total = computeTotal(positions);
  if (total === 0) {
    const even = positions.length > 0 ? newTotal / positions.length : 0;
    return positions.map((p) => ({ ...p, amount: even }));
  }
  const ratio = newTotal / total;
  return positions.map((p) => ({ ...p, amount: p.amount * ratio }));
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd packages/web && npm test -- portfolio-math
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add packages/web/src/lib/portfolio-math.ts packages/web/src/lib/portfolio-math.test.ts
git commit -m "feat: add portfolio math utilities (computeTotal, computeWeights, scaleAmounts)"
```

---

## Task 4: Frontend API Client — CRUD Functions

**Files:**
- Modify: `packages/web/src/api/client.ts`

- [ ] **Step 1: Add createPortfolio, updatePortfolio, deletePortfolio to client.ts**

Append to the end of `packages/web/src/api/client.ts`:

```typescript
export async function createPortfolio(
  token: string,
  payload: { name: string; tickers: string[]; weights: number[] }
): Promise<Portfolio> {
  const res = await fetch(`${API_BASE}/portfolios`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updatePortfolio(
  token: string,
  portfolioId: string,
  payload: { name: string; tickers: string[]; weights: number[] }
): Promise<Portfolio> {
  const res = await fetch(`${API_BASE}/portfolios/${encodeURIComponent(portfolioId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deletePortfolio(token: string, portfolioId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/portfolios/${encodeURIComponent(portfolioId)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await res.text());
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd packages/web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/api/client.ts
git commit -m "feat: add createPortfolio, updatePortfolio, deletePortfolio to API client"
```

---

## Task 5: Hook — Expose refetchPortfolios and refetchPerformance

**Files:**
- Modify: `packages/web/src/hooks/usePortfolioPerformance.ts`

- [ ] **Step 1: Rewrite usePortfolioPerformance.ts to expose refetch functions**

Replace the entire file content of `packages/web/src/hooks/usePortfolioPerformance.ts`:

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
  const [portfoliosKey, setPortfoliosKey] = useState(0);
  const [performanceKey, setPerformanceKey] = useState(0);

  useEffect(() => {
    if (!token) return;
    listPortfolios(token)
      .then((list) => {
        setPortfolios(list);
        if (list.length > 0 && !selectedId) setSelectedId(list[0].id);
      })
      .catch((e) => setError(e.message));
  }, [token, portfoliosKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!token || !selectedId) return;
    setLoading(true);
    setError(null);
    getPortfolioPerformance(token, selectedId)
      .then(setPerformance)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, selectedId, performanceKey]);

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

  const refetchPortfolios = useCallback(() => {
    setPortfoliosKey((k) => k + 1);
  }, []);

  const refetchPerformance = useCallback(() => {
    setPerformanceKey((k) => k + 1);
  }, []);

  return {
    portfolios,
    selectedId,
    setSelectedId,
    selectPortfolio,
    performance,
    slicedCurve,
    loading,
    error,
    period,
    setPeriod,
    refetchPortfolios,
    refetchPerformance,
  };
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd packages/web && npx tsc --noEmit
```

Expected: no errors (Dashboard.tsx uses `selectPortfolio` which is still exported).

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/hooks/usePortfolioPerformance.ts
git commit -m "feat: expose refetchPortfolios and refetchPerformance from hook"
```

---

## Task 6: PositionsTable — Edit Mode

**Files:**
- Modify: `packages/web/src/components/dashboard/PositionsTable.tsx`

- [ ] **Step 1: Rewrite PositionsTable.tsx to support edit mode**

Replace the entire file content of `packages/web/src/components/dashboard/PositionsTable.tsx`:

```typescript
import type { PositionData } from "@/api/client";
import type { DraftPosition } from "@/lib/portfolio-math";
import { computeWeights } from "@/lib/portfolio-math";
import { cn } from "@/lib/utils";

interface PositionsTableProps {
  positions: PositionData[];
  totalValue: number;
  loading?: boolean;
  isEditMode?: boolean;
  draft?: DraftPosition[];
  onDraftChange?: (draft: DraftPosition[]) => void;
}

function pct(n: number) {
  return `${n >= 0 ? "+" : ""}${(n * 100).toFixed(2)}%`;
}

function usd(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

export default function PositionsTable({
  positions,
  totalValue,
  loading,
  isEditMode = false,
  draft = [],
  onDraftChange,
}: PositionsTableProps) {
  const weights = computeWeights(draft);

  function handleTickerChange(index: number, value: string) {
    const next = draft.map((p, i) => (i === index ? { ...p, ticker: value.toUpperCase() } : p));
    onDraftChange?.(next);
  }

  function handleAmountChange(index: number, raw: string) {
    const cleaned = raw.replace(/[^0-9.]/g, "");
    const amount = parseFloat(cleaned) || 0;
    const next = draft.map((p, i) => (i === index ? { ...p, amount } : p));
    onDraftChange?.(next);
  }

  function handleDeleteRow(index: number) {
    onDraftChange?.(draft.filter((_, i) => i !== index));
  }

  function handleAddRow() {
    onDraftChange?.([...draft, { ticker: "", amount: 0 }]);
  }

  if (isEditMode) {
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
              <th className="text-right px-4 py-2 text-xs font-medium text-muted-foreground">Amount</th>
              <th className="w-8" />
            </tr>
          </thead>
          <tbody>
            {draft.map((pos, i) => (
              <tr key={i} className="border-b border-border/50 last:border-0">
                <td className="px-4 py-2">
                  <input
                    className="w-24 bg-transparent border-b border-border focus:border-foreground outline-none text-sm font-semibold"
                    value={pos.ticker}
                    onChange={(e) => handleTickerChange(i, e.target.value)}
                    placeholder="TICKER"
                  />
                </td>
                <td className="px-4 py-2 text-right text-muted-foreground text-sm">
                  {weights[i] !== undefined ? `${(weights[i] * 100).toFixed(1)}%` : "—"}
                </td>
                <td className="px-4 py-2 text-right">
                  <input
                    className="w-28 text-right bg-transparent border-b border-border focus:border-foreground outline-none text-sm"
                    value={pos.amount === 0 ? "" : usd(pos.amount)}
                    onChange={(e) => handleAmountChange(i, e.target.value)}
                    placeholder="$0"
                  />
                </td>
                <td className="px-4 py-2 text-center">
                  <button
                    onClick={() => handleDeleteRow(i)}
                    className="text-muted-foreground hover:text-destructive transition-colors text-base leading-none"
                    aria-label={`Remove ${pos.ticker}`}
                  >
                    ×
                  </button>
                </td>
              </tr>
            ))}
            <tr>
              <td colSpan={4} className="px-4 py-2 border-t border-dashed border-border/50">
                <button
                  onClick={handleAddRow}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  + Add position
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  }

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

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd packages/web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/components/dashboard/PositionsTable.tsx
git commit -m "feat: add edit mode to PositionsTable with inline ticker/amount inputs"
```

---

## Task 7: Dashboard — Edit Mode State and Header Controls

**Files:**
- Modify: `packages/web/src/pages/Dashboard.tsx`

- [ ] **Step 1: Rewrite Dashboard.tsx with edit mode state machine**

Replace the entire content of `packages/web/src/pages/Dashboard.tsx`:

```typescript
import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { usePortfolioPerformance } from "@/hooks/usePortfolioPerformance";
import { createPortfolio, updatePortfolio, deletePortfolio } from "@/api/client";
import { computeTotal, computeWeights, scaleAmounts } from "@/lib/portfolio-math";
import type { DraftPosition } from "@/lib/portfolio-math";
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

type EditMode =
  | { type: "off" }
  | { type: "editing"; draft: { name: string; positions: DraftPosition[] } }
  | { type: "creating" }
  | { type: "deleting" };

export default function Dashboard() {
  const { session } = useAuth();
  const token = session?.access_token;

  const {
    portfolios,
    selectedId,
    setSelectedId,
    selectPortfolio,
    performance,
    slicedCurve,
    loading,
    error,
    period,
    setPeriod,
    refetchPortfolios,
    refetchPerformance,
  } = usePortfolioPerformance(token);

  const [totalValue, setTotalValue] = useState<number>(100_000);
  const [valueInput, setValueInput] = useState<string>("$100,000");
  const [editMode, setEditMode] = useState<EditMode>({ type: "off" });
  const [newPortfolioName, setNewPortfolioName] = useState("");
  const [saving, setSaving] = useState(false);

  // Load persisted total value when portfolio changes
  useEffect(() => {
    if (!selectedId) return;
    const stored = localStorage.getItem(TOTAL_VALUE_KEY(selectedId));
    const val = stored ? parseFloat(stored) : 100_000;
    setTotalValue(val);
    setValueInput(
      new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(val)
    );
  }, [selectedId]);

  function handleValueBlur() {
    const cleaned = valueInput.replace(/[^0-9.]/g, "");
    const val = parseFloat(cleaned) || 100_000;
    setTotalValue(val);
    if (selectedId) localStorage.setItem(TOTAL_VALUE_KEY(selectedId), String(val));
    setValueInput(
      new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(val)
    );
  }

  // --- Edit mode handlers ---

  function handleStartEdit() {
    if (!performance) return;
    const positions: DraftPosition[] = performance.positions.map((p) => ({
      ticker: p.ticker,
      amount: Math.round(p.weight * totalValue),
    }));
    setEditMode({ type: "editing", draft: { name: performance.portfolio_name, positions } });
  }

  function handleDraftChange(positions: DraftPosition[]) {
    if (editMode.type !== "editing") return;
    const newTotal = computeTotal(positions);
    setTotalValue(newTotal);
    setValueInput(
      new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(newTotal)
    );
    setEditMode({ type: "editing", draft: { ...editMode.draft, positions } });
  }

  function handleEditTotalValue(raw: string) {
    if (editMode.type !== "editing") return;
    setValueInput(raw);
    const cleaned = raw.replace(/[^0-9.]/g, "");
    const newTotal = parseFloat(cleaned) || 0;
    if (newTotal > 0) {
      const scaled = scaleAmounts(editMode.draft.positions, newTotal);
      setEditMode({ type: "editing", draft: { ...editMode.draft, positions: scaled } });
      setTotalValue(newTotal);
    }
  }

  function handleEditTotalBlur() {
    const cleaned = valueInput.replace(/[^0-9.]/g, "");
    const newTotal = parseFloat(cleaned) || 0;
    if (editMode.type === "editing" && newTotal > 0) {
      setValueInput(
        new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "USD",
          maximumFractionDigits: 0,
        }).format(newTotal)
      );
    }
  }

  function handleCancelEdit() {
    setEditMode({ type: "off" });
    // Restore total value from storage
    if (selectedId) {
      const stored = localStorage.getItem(TOTAL_VALUE_KEY(selectedId));
      const val = stored ? parseFloat(stored) : 100_000;
      setTotalValue(val);
      setValueInput(
        new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "USD",
          maximumFractionDigits: 0,
        }).format(val)
      );
    }
  }

  async function handleSave() {
    if (editMode.type !== "editing" || !token || !selectedId) return;
    const { name, positions } = editMode.draft;
    const weights = computeWeights(positions);
    const tickers = positions.map((p) => p.ticker.toUpperCase());
    setSaving(true);
    try {
      await updatePortfolio(token, selectedId, { name, tickers, weights });
      await refetchPortfolios();
      refetchPerformance();
      setEditMode({ type: "off" });
    } catch (e) {
      // keep edit mode open, surface error
    } finally {
      setSaving(false);
    }
  }

  // --- Create portfolio ---

  function handleStartCreate() {
    setNewPortfolioName("");
    setEditMode({ type: "creating" });
  }

  async function handleConfirmCreate() {
    if (!token || !newPortfolioName.trim()) return;
    setSaving(true);
    try {
      const created = await createPortfolio(token, {
        name: newPortfolioName.trim(),
        tickers: [],
        weights: [],
      });
      await refetchPortfolios();
      setSelectedId(created.id);
      setEditMode({
        type: "editing",
        draft: { name: created.name, positions: [] },
      });
      setTotalValue(0);
      setValueInput("$0");
    } catch (e) {
      // stay on create prompt
    } finally {
      setSaving(false);
    }
  }

  // --- Delete portfolio ---

  function handleStartDelete() {
    setEditMode({ type: "deleting" });
  }

  async function handleConfirmDelete() {
    if (!token || !selectedId) return;
    setSaving(true);
    try {
      await deletePortfolio(token, selectedId);
      await refetchPortfolios();
      setEditMode({ type: "off" });
    } catch (e) {
      setEditMode({ type: "off" });
    } finally {
      setSaving(false);
    }
  }

  const todayChange = performance
    ? performance.positions.reduce((acc, p) => acc + p.day_pct * p.weight, 0)
    : 0;
  const todayChangeDollar = todayChange * totalValue;
  const lastUpdated = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const isEditing = editMode.type === "editing";
  const draft = isEditing ? (editMode as { type: "editing"; draft: { name: string; positions: DraftPosition[] } }).draft : null;
  const selectedPortfolio = portfolios.find((p) => p.id === selectedId);

  return (
    <div className="py-6 space-y-4 max-w-4xl">
      {/* Selector bar */}
      <div className="flex items-center justify-between gap-3">
        {/* Left: portfolio selector or edit name */}
        <div className="flex items-center gap-3 min-w-0">
          {isEditing && draft ? (
            <input
              className="w-48 h-8 text-sm border border-border rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-foreground bg-background"
              value={draft.name}
              onChange={(e) =>
                setEditMode({ type: "editing", draft: { ...draft, name: e.target.value } })
              }
              aria-label="Portfolio name"
            />
          ) : (
            <>
              <span className="text-xs text-muted-foreground uppercase tracking-wide shrink-0">
                Portfolio
              </span>
              <Select
                value={selectedId}
                onValueChange={selectPortfolio}
                disabled={portfolios.length === 0 || editMode.type !== "off"}
              >
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
            </>
          )}
        </div>

        {/* Right: action buttons */}
        <div className="flex items-center gap-2 shrink-0">
          {editMode.type === "off" && (
            <>
              {selectedId && performance && (
                <button
                  onClick={handleStartEdit}
                  className="text-xs text-muted-foreground hover:text-foreground border border-border rounded px-2 py-1 transition-colors"
                >
                  Edit
                </button>
              )}
              <button
                onClick={handleStartCreate}
                className="text-xs text-muted-foreground hover:text-foreground border border-border rounded px-2 py-1 transition-colors"
              >
                + New
              </button>
              {selectedId && portfolios.length > 0 && (
                <button
                  onClick={handleStartDelete}
                  className="text-xs text-muted-foreground hover:text-destructive border border-border rounded px-2 py-1 transition-colors"
                >
                  Delete
                </button>
              )}
            </>
          )}

          {isEditing && (
            <>
              <button
                onClick={handleSave}
                disabled={saving}
                className="text-xs border border-border rounded px-2 py-1 text-foreground hover:bg-accent transition-colors disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save"}
              </button>
              <button
                onClick={handleCancelEdit}
                className="text-xs text-muted-foreground hover:text-foreground border border-border rounded px-2 py-1 transition-colors"
              >
                Cancel
              </button>
            </>
          )}
        </div>
      </div>

      {/* Inline: New portfolio name prompt */}
      {editMode.type === "creating" && (
        <div className="border border-border rounded-lg px-4 py-3 flex items-center gap-3">
          <span className="text-xs text-muted-foreground uppercase tracking-wide shrink-0">
            Portfolio name
          </span>
          <input
            autoFocus
            className="flex-1 text-sm border-b border-border bg-transparent focus:outline-none focus:border-foreground"
            placeholder="e.g. Growth Portfolio"
            value={newPortfolioName}
            onChange={(e) => setNewPortfolioName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleConfirmCreate();
              if (e.key === "Escape") setEditMode({ type: "off" });
            }}
          />
          <button
            onClick={handleConfirmCreate}
            disabled={!newPortfolioName.trim() || saving}
            className="text-xs border border-border rounded px-3 py-1 text-foreground hover:bg-accent transition-colors disabled:opacity-40"
          >
            {saving ? "Creating…" : "Create →"}
          </button>
          <button
            onClick={() => setEditMode({ type: "off" })}
            className="text-xs text-muted-foreground hover:text-foreground"
            aria-label="Cancel"
          >
            ✕
          </button>
        </div>
      )}

      {/* Inline: Delete confirmation */}
      {editMode.type === "deleting" && selectedPortfolio && (
        <div className="border border-destructive/30 rounded-lg px-4 py-3 flex items-center gap-3">
          <span className="text-sm text-muted-foreground flex-1">
            Delete <span className="font-semibold text-foreground">{selectedPortfolio.name}</span>?
            This cannot be undone.
          </span>
          <button
            onClick={handleConfirmDelete}
            disabled={saving}
            className="text-xs text-destructive border border-destructive/50 rounded px-3 py-1 hover:bg-destructive/10 transition-colors disabled:opacity-50"
          >
            {saving ? "Deleting…" : "Confirm"}
          </button>
          <button
            onClick={() => setEditMode({ type: "off" })}
            className="text-xs text-muted-foreground hover:text-foreground border border-border rounded px-2 py-1 transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      {error && (
        <div className="text-sm text-red-600 border border-red-200 bg-red-50 rounded px-3 py-2">
          {error}
        </div>
      )}

      {/* Empty state — no portfolios */}
      {!loading && portfolios.length === 0 && editMode.type === "off" && (
        <div className="text-center py-16 text-muted-foreground">
          <div className="text-sm mb-3">No portfolios yet.</div>
          <button
            onClick={handleStartCreate}
            className="text-sm border border-border rounded px-4 py-2 hover:bg-accent transition-colors"
          >
            + Create your first portfolio
          </button>
        </div>
      )}

      {/* Dashboard content — hidden when no portfolio selected */}
      {(selectedId || isEditing) && (
        <>
          {/* Big portfolio value */}
          <div className="text-center py-2">
            <div className="text-4xl font-bold tracking-tight">
              {isEditing ? (
                <input
                  className="text-4xl font-bold tracking-tight text-center w-48 bg-transparent border-b border-border focus:outline-none focus:border-foreground"
                  value={valueInput}
                  onChange={(e) => handleEditTotalValue(e.target.value)}
                  onBlur={handleEditTotalBlur}
                  onKeyDown={(e) => e.key === "Enter" && handleEditTotalBlur()}
                  aria-label="Total portfolio value"
                />
              ) : (
                usd(totalValue)
              )}
            </div>
            {!isEditing && (
              <div
                className={cn(
                  "text-sm mt-1 font-medium",
                  todayChange >= 0 ? "text-green-600" : "text-red-600"
                )}
              >
                {todayChange >= 0 ? "+" : ""}
                {usd(todayChangeDollar)} ({pct(todayChange)}) Today
              </div>
            )}
            {isEditing && (
              <div className="text-xs text-muted-foreground mt-1">
                Edit to scale all positions proportionally
              </div>
            )}
          </div>

          {/* Equity curve — hidden in edit mode */}
          {!isEditing && (
            <EquityCurve
              curve={slicedCurve}
              period={period}
              onPeriodChange={setPeriod}
              loading={loading}
            />
          )}

          {/* Pie + stats — hidden in edit mode */}
          {!isEditing && (
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
                      {loading ? (
                        <div className="h-5 w-16 bg-muted/40 rounded animate-pulse" />
                      ) : (
                        stat.value
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Positions table */}
          <PositionsTable
            positions={performance?.positions ?? []}
            totalValue={totalValue}
            loading={loading && !isEditing}
            isEditMode={isEditing}
            draft={draft?.positions ?? []}
            onDraftChange={handleDraftChange}
          />

          <div className="text-xs text-muted-foreground text-right">
            Prices via yfinance · Last updated {lastUpdated}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd packages/web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Run the dev server and manually verify**

```bash
cd packages/web && npm run dev
```

Open http://localhost:5173/dashboard and verify:
- [ ] "Edit", "+ New", "Delete" buttons appear in the header
- [ ] Clicking "Edit" enters edit mode: portfolio name becomes an input, positions table shows editable rows with ticker/amount inputs, weight column auto-updates as amounts change
- [ ] Changing the large total value input scales all position amounts
- [ ] Clicking "Cancel" restores the original view with no changes
- [ ] Clicking "+ New" shows the name prompt inline
- [ ] Clicking "Delete" shows the inline confirmation

- [ ] **Step 4: Commit**

```bash
git add packages/web/src/pages/Dashboard.tsx
git commit -m "feat: add portfolio edit mode, create flow, and delete confirmation to Dashboard"
```

---

## Task 8: End-to-End Smoke Test

- [ ] **Step 1: Run the full backend test suite**

```bash
cd packages/api && python -m pytest --ignore=tests/test_openbb_sandbox.py --ignore=tests/test_openbb_codegen.py -v
```

Expected: all pass.

- [ ] **Step 2: Run the frontend test suite**

```bash
cd packages/web && npm test
```

Expected: all pass (includes new portfolio-math tests).

- [ ] **Step 3: Manual end-to-end verification**

Start both servers:
```bash
# Terminal 1
cd packages/api && uvicorn api.main:app --reload

# Terminal 2
cd packages/web && npm run dev
```

Run through the full flow:
- [ ] Create a new portfolio named "Test Portfolio" → confirm it appears in the selector
- [ ] Enter edit mode → add 2 positions (e.g., AAPL $30,000 + MSFT $20,000) → save → weights show 60%/40%
- [ ] Re-enter edit mode → change total value to $100,000 → confirm amounts scale to $60,000/$40,000
- [ ] Re-enter edit mode → rename portfolio → save → selector shows new name
- [ ] Delete the portfolio → confirm it disappears from the selector
- [ ] When no portfolios remain → empty state with "Create your first portfolio" shown

- [ ] **Step 4: Final push**

```bash
git push
```
