# Dashboard Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three UI regressions/issues on the Dashboard: portfolio dropdown showing UUID, missing timeframe subtitles on metric cards, and legend overlapping the equity curve chart.

**Architecture:** Direct edits to two existing files — Dashboard.tsx for the dropdown and metric cards, EquityCurve.tsx for the legend overlap.

**Tech Stack:** React, TypeScript, Radix UI Select, Plotly.js

---

### Task 1: Fix Portfolio Dropdown Showing UUID

**Files:**
- Modify: `packages/web/src/pages/Dashboard.tsx:238-253`

**Context:** The `Select` component uses `selectedId` (a UUID) as its `value`. Radix's `SelectValue` falls back to showing this raw value when the matching `SelectItem` isn't mounted yet (during loading, or stale ID). Fix by explicitly rendering the portfolio name inside `SelectValue`.

- [ ] **Step 1: Derive the selected portfolio name**

In Dashboard.tsx, find the portfolio dropdown section (around line 238). Compute the display name before the `Select` component. Add this inside the render, before the `<Select>` tag:

```tsx
const selectedName = portfolios.find((p) => p.id === selectedId)?.name;
```

Note: This should be placed inside the component body where `portfolios` and `selectedId` are in scope — add it right before the JSX return or as an inline const in the JSX block.

- [ ] **Step 2: Pass the name to SelectValue**

Replace the current `SelectValue`:
```tsx
<SelectValue placeholder={loading ? "Loading..." : "No portfolios"} />
```

With:
```tsx
<SelectValue placeholder={loading ? "Loading..." : "No portfolios"}>
  {selectedName}
</SelectValue>
```

This ensures the trigger always shows the human-readable name, even if the `SelectItem` list hasn't rendered yet.

- [ ] **Step 3: Verify in browser**

Run: `npm run dev`
- Load the dashboard
- Confirm the dropdown shows the portfolio name, not a UUID
- Switch between portfolios — names should update correctly
- Reload the page — should still show name on initial load

- [ ] **Step 4: Commit**

```bash
git add packages/web/src/pages/Dashboard.tsx
git commit -m "fix: show portfolio name instead of UUID in dashboard dropdown"
```

---

### Task 2: Add Timeframe Subtitles to Metric Cards

**Files:**
- Modify: `packages/web/src/pages/Dashboard.tsx:437-478`

**Context:** The four metric cards (Total Return, vs SPY, Sharpe Ratio, Max Drawdown) show values from `performance.stats`, which is always computed over the full history. There's no visual indication of this. Add an "All Time" subtitle under each metric label.

- [ ] **Step 1: Add subtitle to each metric card**

In Dashboard.tsx, find the metric card rendering (around line 460). The current card markup is:

```tsx
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
```

Replace with:

```tsx
<div key={stat.label} className="border border-border rounded-lg p-3">
  <div className="text-xs text-muted-foreground">{stat.label}</div>
  <div className="text-[10px] text-muted-foreground/60">All Time</div>
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
```

The new line `<div className="text-[10px] text-muted-foreground/60">All Time</div>` sits between the label and the value, providing timeframe context without taking up much space.

- [ ] **Step 2: Verify in browser**

- Each metric card should now show the label, then "All Time" in smaller muted text, then the value
- The subtitle should be visually subtle — smaller and lighter than the label

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/pages/Dashboard.tsx
git commit -m "fix: add timeframe subtitle to dashboard metric cards"
```

---

### Task 3: Fix Legend Overlapping Equity Curve Chart

**Files:**
- Modify: `packages/web/src/components/dashboard/EquityCurve.tsx:59`

**Context:** The Plotly legend is positioned at `y: 1.1` (above the chart), but the top margin is only `8px`, so the legend renders on top of the chart data. Increase the top margin to give the legend room.

- [ ] **Step 1: Increase top margin**

In EquityCurve.tsx, find line 59:

```tsx
margin: { l: 48, r: 16, t: 8, b: 40 },
```

Replace with:

```tsx
margin: { l: 48, r: 16, t: 32, b: 40 },
```

- [ ] **Step 2: Verify in browser**

- The legend ("Portfolio" and "SPY") should sit above the chart without overlapping any data
- The chart should still look properly proportioned within its container

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/components/dashboard/EquityCurve.tsx
git commit -m "fix: increase chart top margin so legend doesn't overlap data"
```
