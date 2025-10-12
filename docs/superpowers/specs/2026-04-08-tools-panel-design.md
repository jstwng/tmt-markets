# Tools Panel — Design Spec

**Date:** 2026-04-08
**Status:** Approved

## Summary

A floating action button (FAB) fixed to the bottom-right of the Chat page. Clicking it opens a slide-in overlay panel listing all research assistant tools, grouped by category, with a fixed search bar and one example prompt per tool. Purely informational — no interactivity beyond search and dismiss.

---

## Architecture

### New files

**`packages/web/src/components/chat/ToolsPanel.tsx`**
The panel component. Receives `open: boolean` and `onClose: () => void` props. Renders:
- Fixed-position overlay anchored to the right edge, full viewport height
- Panel slides in/out via Tailwind transition (`translate-x-full` ↔ `translate-x-0`)
- Fixed search bar at the top of the panel
- Scrollable list of category groups below the search bar
- Backdrop div (full screen, transparent) behind the panel that dismisses on click
- Escape key listener that calls `onClose`

**`packages/web/src/data/tools-manifest.ts`**
Static array of tool definitions:
```ts
interface Tool {
  name: string;           // Human-readable: "Optimize Portfolio"
  description: string;   // One sentence
  examplePrompt: string; // Example user message
  category: ToolCategory;
}

type ToolCategory =
  | "Data"
  | "Portfolio"
  | "Risk"
  | "Backtesting"
  | "Covariance & Returns"
  | "Scenarios"
  | "Attribution"
  | "Charts & Reports";
```

### Modified files

**`packages/web/src/pages/Chat.tsx`**
- Adds `toolsPanelOpen` boolean state (default `false`)
- Renders `<ToolsPanel open={toolsPanelOpen} onClose={() => setToolsPanelOpen(false)} />` inside the chat layout
- Renders the FAB button: `fixed bottom-6 right-6`, uses `Wrench` icon from `lucide-react`, toggles `toolsPanelOpen`

---

## Content — Tool Categories

### Data (2 tools)
| Tool | Example Prompt |
|------|---------------|
| Price History | "Fetch daily prices for AAPL, MSFT from 2022 to 2024" |
| OpenBB Query | "Get earnings estimates and income statement for NVDA" |

### Portfolio (5 tools)
| Tool | Example Prompt |
|------|---------------|
| Optimize Portfolio | "Maximize Sharpe ratio for AAPL, MSFT, GOOGL over 2 years" |
| Efficient Frontier | "Show the efficient frontier for SPY, TLT, GLD, QQQ" |
| Constrained Optimization | "Optimize my portfolio with max 30% in any single stock" |
| Black-Litterman | "Apply Black-Litterman with my views on AAPL and TSLA" |
| Load / Save Portfolio | "Save this portfolio as 'Core Holdings'" |

### Risk (5 tools)
| Tool | Example Prompt |
|------|---------------|
| VaR / CVaR | "Compute 95% VaR for my portfolio over the last year" |
| Tail Risk Metrics | "What are the tail risk metrics for a 60/40 portfolio?" |
| Risk Decomposition | "Decompose risk contributions for SPY, TLT, GLD" |
| Drawdown Analysis | "Show max drawdown for a 60/40 SPY/TLT portfolio" |
| Liquidity Score | "Score the liquidity of my current holdings" |

### Backtesting (2 tools)
| Tool | Example Prompt |
|------|---------------|
| Backtest Portfolio | "Backtest a 60/40 SPY/TLT portfolio from 2022 to 2024" |
| Rebalancing Analysis | "How often should I rebalance SPY/TLT to maintain 60/40?" |

### Covariance & Returns (3 tools)
| Tool | Example Prompt |
|------|---------------|
| Covariance Matrix | "What is the covariance matrix for the Mag 7 in 2024?" |
| Factor Exposure | "Show factor exposure for my portfolio vs the market" |
| Expected Returns | "Estimate expected returns for AAPL, MSFT, GOOGL" |

### Scenarios (3 tools)
| Tool | Example Prompt |
|------|---------------|
| Stress Test | "Stress test my portfolio under a 2008-style crash" |
| Scenario Return Table | "Generate a scenario table for my portfolio" |
| Monte Carlo Simulation | "Run 1000 Monte Carlo paths for my portfolio over 5 years" |

### Attribution (2 tools)
| Tool | Example Prompt |
|------|---------------|
| Benchmark Comparison | "Compare my portfolio returns to SPY over 2 years" |
| Portfolio Attribution | "Break down my portfolio's return attribution" |

### Charts & Reports (5 tools)
| Tool | Example Prompt |
|------|---------------|
| Correlation Matrix | "Plot the correlation matrix for the Mag 7 stocks" |
| Frontier with Assets | "Show the efficient frontier with individual assets plotted" |
| Rolling Metrics | "Show rolling Sharpe ratio for my portfolio over 2 years" |
| Asset Ranking | "Rank AAPL, MSFT, GOOGL by Sharpe ratio in 2023" |
| Tearsheet | "Generate a full tearsheet for my portfolio" |

---

## Behavior

### Opening / closing
- FAB click: toggles panel open/closed
- ✕ button inside panel: closes
- Clicking the backdrop (outside panel): closes
- Escape key: closes

### Search
- Fixed input at the top of the panel, always visible when panel is open
- Filters in real-time across tool names and descriptions (client-side only)
- If search is non-empty, hides category headers and shows a flat filtered list
- If search returns no results, shows a "No tools match" empty state

### Animation
- Panel: `transition-transform duration-200 ease-in-out`
- Backdrop: `transition-opacity duration-200`
- FAB: no animation needed

### Panel dimensions
- Width: `w-72` (288px)
- Height: full viewport height (`h-screen`), fixed position
- Positioned: `fixed top-0 right-0 z-50`

---

## Non-goals

- No click-to-insert prompt behavior — purely informational
- No backend data fetching — tool list is static
- No persistence of open/closed state across page loads
