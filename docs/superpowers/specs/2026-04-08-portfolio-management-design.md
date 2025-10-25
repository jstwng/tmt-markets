# Portfolio Management — Design Spec
**Date:** 2026-04-08  
**Status:** Approved

---

## Overview

Add full portfolio CRUD to the dashboard: create, rename, edit holdings, delete. No new pages or separate flows — all management happens inline within the existing dashboard. The dashboard remains visually unchanged during normal use; an edit mode toggle surfaces controls on demand.

---

## Scope

- Create a new portfolio (name prompt → edit mode)
- Rename an existing portfolio (editable name in edit mode)
- Add, edit, and remove holdings (ticker + dollar amount)
- Delete a portfolio (with inline confirmation)
- Two-way linking between total value and individual position amounts

Out of scope: weight constraints, optimization, importing from brokers.

---

## UI Design

### Dashboard Header (view mode)

The header row shows:
```
[Tech Growth ▾]  [✎ Edit]  [+ New]                    [Delete]
```

- **Portfolio selector** — existing dropdown, unchanged
- **✎ Edit** — enters edit mode for the selected portfolio
- **+ New** — opens the inline name prompt (see below)
- **Delete** — initiates inline delete confirmation

### Edit Mode

Clicking "✎ Edit" transforms the header and table in place. Layout and sizing do not change.

**Header (edit mode):**
```
[Tech Growth (input)]                        [Save]  [Cancel]
```
- Portfolio name becomes an editable text input
- Save/Cancel replace the Edit/New/Delete buttons

**Total Value (edit mode):**
- The `$50,000` display becomes an editable input with a subtle bottom underline
- Hint text: "Edit to scale all positions"
- Changing this field scales all position amounts proportionally and recalculates weights

**Positions table (edit mode):**
- Ticker and Amount columns become editable inputs (same size, subtle underline border)
- Weight column remains read-only — always derived, never typed
- Each row gains a `×` delete button (fades in; hidden in view mode)
- A `+ Add position` link appears below the last row (fades in)
- Changing any Amount recalculates all weights and updates the total value to the sum

**Visual signals for edit mode:**
- Subtle bottom underlines on editable fields
- `×` buttons and `+ Add position` fade in
- Save/Cancel in header — only indicator that edit mode is active
- No banners, no table border changes, no layout shifts

### New Portfolio Flow

1. User clicks **+ New** — the rest of the dashboard dims slightly
2. An inline name prompt appears below the header:
   ```
   [New Portfolio Name]
   [___________________]  [Create →]  [✕]
   ```
   - Input is auto-focused
   - Press Enter or click "Create →" to proceed
   - Click ✕ to cancel without creating anything
3. On confirm: a new empty portfolio is created (POST to backend), the selector switches to it, and edit mode activates
4. User adds positions and saves

### Delete Flow

1. User clicks **Delete** — header transforms inline:
   ```
   Delete "Tech Growth"? This cannot be undone.    [Confirm]  [Cancel]
   ```
2. On confirm: DELETE request sent, portfolio removed, selector switches to the next available portfolio. If no portfolios remain, the dashboard shows an empty state with only the "+ New" button visible.
3. On cancel: header returns to normal

---

## Data Model

No schema changes required. The existing `Portfolio` type is sufficient:

```typescript
interface Portfolio {
  id: string;
  name: string;
  tickers: string[];   // ["AAPL", "MSFT", "NVDA"]
  weights: number[];   // [0.45, 0.35, 0.20] — always derived, never stored as user input
  created_at: string;
  updated_at: string;
}
```

Frontend edit draft (ephemeral, not persisted):
```typescript
interface EditDraft {
  name: string;
  positions: Array<{ ticker: string; amount: number }>;
}
```

Weights and total value are always computed from `positions`:
- `totalValue = sum(positions.map(p => p.amount))`
- `weight[i] = positions[i].amount / totalValue`

When the user edits `totalValue` directly, each `amount` is scaled:
- `amount[i] = weight[i] * newTotalValue`

---

## Backend Changes

Two new endpoints needed (DELETE already exists):

### POST `/api/portfolios`
Create a new portfolio.

**Request:**
```json
{ "name": "Growth Portfolio", "tickers": [], "weights": [] }
```
**Response:** `Portfolio` object with `id`, `created_at`, etc.

### PATCH `/api/portfolios/{portfolio_id}`
Update name and/or holdings of an existing portfolio.

**Request:**
```json
{ "name": "Tech Growth", "tickers": ["AAPL", "MSFT"], "weights": [0.6, 0.4] }
```
**Response:** Updated `Portfolio` object.

Both endpoints require auth (same as existing routes) and belong to the authenticated user.

---

## Frontend State

New state in `Dashboard.tsx`:

```typescript
type EditMode = 
  | { type: 'off' }
  | { type: 'editing'; draft: EditDraft }
  | { type: 'creating' }           // name prompt visible
  | { type: 'deleting' }           // delete confirmation visible

const [editMode, setEditMode] = useState<EditMode>({ type: 'off' });
const [newPortfolioName, setNewPortfolioName] = useState('');
```

**On "Create →" (name prompt):**
1. `POST /api/portfolios` with `{ name, tickers: [], weights: [] }`
2. Switch selector to new portfolio id
3. Transition to `{ type: 'editing', draft: { name, positions: [] } }`

**On Save (edit mode):**
1. Compute `tickers` and `weights` from `draft.positions`
2. `PATCH /api/portfolios/{id}` with updated name, tickers, weights
3. Invalidate React Query cache for portfolios list and performance data
4. Exit edit mode

**On Cancel:** Discard draft, return to `{ type: 'off' }`.

**On Delete Confirm:** `DELETE /api/portfolios/{id}`, select first remaining portfolio, exit.

---

## Component Structure

All changes confined to existing files — no new component files needed for MVP.

- **`Dashboard.tsx`** — owns all edit mode state; conditionally renders editable inputs vs. display text in header and total value area
- **`PositionsTable.tsx`** — accepts `isEditMode: boolean` and `onDraftChange` callback; renders editable rows when in edit mode
- **`api/client.ts`** — add `createPortfolio()` and `updatePortfolio()` typed functions
- **`api/routes/portfolios.py`** — add POST and PATCH route handlers

---

## Acceptance Criteria

- [ ] User can create a portfolio via the name prompt; it persists in Supabase
- [ ] User can enter edit mode, modify holdings (add/edit/delete rows), and save
- [ ] Weights update live as amounts are changed; total value updates live as amounts change
- [ ] Editing total value scales all position amounts proportionally
- [ ] User can rename a portfolio in edit mode
- [ ] User can delete a portfolio with confirmation; selector moves to next portfolio
- [ ] Cancel discards all draft changes with no side effects
- [ ] All operations are scoped to the authenticated user
- [ ] Layout does not shift between view and edit mode
