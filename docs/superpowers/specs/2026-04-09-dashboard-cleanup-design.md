# Dashboard Cleanup Design

**Date:** 2026-04-09
**Status:** Approved

## Problem

Three UI issues on the Dashboard page need fixing:

1. Portfolio dropdown shows UUID instead of portfolio name on initial load
2. Performance metric cards have no timeframe subtitle — unclear what period the stats cover
3. Equity curve legend overlaps the left side of the chart

## Fix 1: Portfolio Dropdown Showing ID

**Root cause:** Radix `SelectValue` falls back to the raw `value` prop (the UUID) when the matching `SelectItem` isn't mounted yet (e.g., during loading or when `selectedId` is stale).

**Solution:** Derive a display name from `portfolios.find(p => p.id === selectedId)?.name` and render it explicitly inside `SelectValue` so the dropdown always shows a human-readable name regardless of render timing.

**File:** `packages/web/src/pages/Dashboard.tsx` (lines ~243-244)

## Fix 2: Metric Card Timeframe Subtitles

**Root cause:** `performance.stats` is always computed over the full history (all-time). The period selector only affects the equity curve slice, not the stats. There's no visual indication of this.

**Solution:** Add a subtitle line under each metric label showing "All Time". This accurately reflects what the stats represent.

**File:** `packages/web/src/pages/Dashboard.tsx` (lines ~460-462)

## Fix 3: Legend Overlapping Chart

**Root cause:** Legend is positioned at `y: 1.1` but the chart's top margin is only `8px`, so the legend renders on top of the data area.

**Solution:** Increase top margin from `8` to `32` in the Plotly layout to give the legend enough clearance above the chart.

**File:** `packages/web/src/components/dashboard/EquityCurve.tsx` (line 59)
