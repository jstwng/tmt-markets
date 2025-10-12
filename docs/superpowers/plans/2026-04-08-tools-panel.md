# Tools Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a floating action button to the Chat page that opens a slide-in panel listing all research assistant tools grouped by category, with a search bar and one example prompt per tool.

**Architecture:** A static `tools-manifest.ts` data file drives a `ToolsPanel.tsx` overlay component. `Chat.tsx` owns the open/closed state and renders both the FAB and the panel. No backend calls — all data is hardcoded at build time.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4, Vitest + @testing-library/react, lucide-react

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `packages/web/src/data/tools-manifest.ts` | Static array of all tools with name, description, examplePrompt, category |
| Create | `packages/web/src/components/chat/ToolsPanel.tsx` | Slide-in panel: search bar, category groups, tool cards, dismiss logic |
| Modify | `packages/web/src/pages/Chat.tsx` | Add `toolsPanelOpen` state, FAB button, render `<ToolsPanel>` |
| Create | `packages/web/src/data/tools-manifest.test.ts` | Validate manifest shape and completeness |
| Create | `packages/web/src/components/chat/ToolsPanel.test.tsx` | Test render, search, and dismiss behaviors |

---

## Task 1: Create tools-manifest.ts

**Files:**
- Create: `packages/web/src/data/tools-manifest.ts`
- Create: `packages/web/src/data/tools-manifest.test.ts`

- [ ] **Step 1: Write the failing test**

Create `packages/web/src/data/tools-manifest.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { TOOLS_MANIFEST, CATEGORIES, type Tool, type ToolCategory } from "./tools-manifest";

describe("TOOLS_MANIFEST", () => {
  it("exports a non-empty array", () => {
    expect(Array.isArray(TOOLS_MANIFEST)).toBe(true);
    expect(TOOLS_MANIFEST.length).toBeGreaterThan(0);
  });

  it("every tool has required string fields", () => {
    for (const tool of TOOLS_MANIFEST) {
      expect(typeof tool.name).toBe("string");
      expect(tool.name.length).toBeGreaterThan(0);
      expect(typeof tool.description).toBe("string");
      expect(tool.description.length).toBeGreaterThan(0);
      expect(typeof tool.examplePrompt).toBe("string");
      expect(tool.examplePrompt.length).toBeGreaterThan(0);
      expect(typeof tool.category).toBe("string");
    }
  });

  it("every tool's category is a valid ToolCategory", () => {
    const validCategories = new Set<string>(CATEGORIES);
    for (const tool of TOOLS_MANIFEST) {
      expect(validCategories.has(tool.category)).toBe(true);
    }
  });

  it("tool names are unique", () => {
    const names = TOOLS_MANIFEST.map((t) => t.name);
    const unique = new Set(names);
    expect(unique.size).toBe(names.length);
  });

  it("every category has at least one tool", () => {
    for (const category of CATEGORIES) {
      const tools = TOOLS_MANIFEST.filter((t) => t.category === category);
      expect(tools.length).toBeGreaterThan(0);
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd packages/web && npx vitest run src/data/tools-manifest.test.ts
```

Expected: FAIL — `Cannot find module './tools-manifest'`

- [ ] **Step 3: Create tools-manifest.ts**

Create `packages/web/src/data/tools-manifest.ts`:

```ts
export type ToolCategory =
  | "Data"
  | "Portfolio"
  | "Risk"
  | "Backtesting"
  | "Covariance & Returns"
  | "Scenarios"
  | "Attribution"
  | "Charts & Reports";

export const CATEGORIES: ToolCategory[] = [
  "Data",
  "Portfolio",
  "Risk",
  "Backtesting",
  "Covariance & Returns",
  "Scenarios",
  "Attribution",
  "Charts & Reports",
];

export interface Tool {
  name: string;
  description: string;
  examplePrompt: string;
  category: ToolCategory;
}

export const TOOLS_MANIFEST: Tool[] = [
  // Data
  {
    name: "Price History",
    description: "Fetch historical adjusted close prices for one or more tickers.",
    examplePrompt: "Fetch daily prices for AAPL, MSFT from 2022 to 2024",
    category: "Data",
  },
  {
    name: "OpenBB Query",
    description: "Query financial data via OpenBB: options, earnings, fundamentals, macro indicators.",
    examplePrompt: "Get earnings estimates and income statement for NVDA",
    category: "Data",
  },

  // Portfolio
  {
    name: "Optimize Portfolio",
    description: "Find the optimal asset weights that maximize Sharpe ratio or minimize volatility.",
    examplePrompt: "Maximize Sharpe ratio for AAPL, MSFT, GOOGL over 2 years",
    category: "Portfolio",
  },
  {
    name: "Efficient Frontier",
    description: "Generate the mean-variance efficient frontier for a set of assets.",
    examplePrompt: "Show the efficient frontier for SPY, TLT, GLD, QQQ",
    category: "Portfolio",
  },
  {
    name: "Constrained Optimization",
    description: "Optimize a portfolio subject to constraints like position limits or sector caps.",
    examplePrompt: "Optimize my portfolio with a max 30% weight in any single stock",
    category: "Portfolio",
  },
  {
    name: "Black-Litterman",
    description: "Blend market equilibrium returns with investor views using the Black-Litterman model.",
    examplePrompt: "Apply Black-Litterman with my views that AAPL will outperform TSLA",
    category: "Portfolio",
  },
  {
    name: "Load / Save Portfolio",
    description: "Persist a named portfolio to your account or reload a previously saved one.",
    examplePrompt: "Save this portfolio as 'Core Holdings'",
    category: "Portfolio",
  },

  // Risk
  {
    name: "VaR / CVaR",
    description: "Compute Value at Risk and Conditional Value at Risk at a given confidence level.",
    examplePrompt: "Compute 95% VaR for my portfolio over the last year",
    category: "Risk",
  },
  {
    name: "Tail Risk Metrics",
    description: "Calculate skewness, kurtosis, and other tail risk statistics.",
    examplePrompt: "What are the tail risk metrics for a 60/40 SPY/TLT portfolio?",
    category: "Risk",
  },
  {
    name: "Risk Decomposition",
    description: "Break down total portfolio risk into per-asset marginal contributions.",
    examplePrompt: "Decompose risk contributions for SPY, TLT, GLD",
    category: "Risk",
  },
  {
    name: "Drawdown Analysis",
    description: "Compute the drawdown series and max drawdown for a portfolio.",
    examplePrompt: "Show max drawdown for a 60/40 SPY/TLT portfolio",
    category: "Risk",
  },
  {
    name: "Liquidity Score",
    description: "Score the relative liquidity of holdings based on average traded volume.",
    examplePrompt: "Score the liquidity of my current holdings",
    category: "Risk",
  },

  // Backtesting
  {
    name: "Backtest Portfolio",
    description: "Run a historical backtest for a fixed-weight portfolio over a date range.",
    examplePrompt: "Backtest a 60/40 SPY/TLT portfolio from 2022 to 2024",
    category: "Backtesting",
  },
  {
    name: "Rebalancing Analysis",
    description: "Analyze how rebalancing frequency affects portfolio performance and drift.",
    examplePrompt: "How often should I rebalance SPY/TLT to maintain a 60/40 split?",
    category: "Backtesting",
  },

  // Covariance & Returns
  {
    name: "Covariance Matrix",
    description: "Estimate the annualized covariance matrix of asset returns.",
    examplePrompt: "What is the covariance matrix for the Mag 7 stocks in 2024?",
    category: "Covariance & Returns",
  },
  {
    name: "Factor Exposure",
    description: "Compute a portfolio's exposure to common risk factors (market, size, value, momentum).",
    examplePrompt: "Show the factor exposure for my portfolio vs the market",
    category: "Covariance & Returns",
  },
  {
    name: "Expected Returns",
    description: "Estimate forward-looking expected returns using historical or factor-based methods.",
    examplePrompt: "Estimate expected returns for AAPL, MSFT, GOOGL",
    category: "Covariance & Returns",
  },

  // Scenarios
  {
    name: "Stress Test",
    description: "Simulate portfolio performance under historical stress scenarios (e.g. 2008, COVID).",
    examplePrompt: "Stress test my portfolio under a 2008-style market crash",
    category: "Scenarios",
  },
  {
    name: "Scenario Return Table",
    description: "Generate a table of portfolio returns across multiple predefined market scenarios.",
    examplePrompt: "Generate a scenario return table for my portfolio",
    category: "Scenarios",
  },
  {
    name: "Monte Carlo Simulation",
    description: "Run Monte Carlo paths to model the range of possible future portfolio outcomes.",
    examplePrompt: "Run 1000 Monte Carlo paths for my portfolio over 5 years",
    category: "Scenarios",
  },

  // Attribution
  {
    name: "Benchmark Comparison",
    description: "Compare portfolio returns, alpha, and beta against a benchmark index.",
    examplePrompt: "Compare my portfolio returns to SPY over 2 years",
    category: "Attribution",
  },
  {
    name: "Portfolio Attribution",
    description: "Break down return attribution by asset and time period.",
    examplePrompt: "Break down my portfolio's return attribution by holding",
    category: "Attribution",
  },

  // Charts & Reports
  {
    name: "Correlation Matrix",
    description: "Plot a heatmap of pairwise correlations between assets.",
    examplePrompt: "Plot the correlation matrix for the Mag 7 stocks",
    category: "Charts & Reports",
  },
  {
    name: "Frontier with Assets",
    description: "Plot the efficient frontier with individual asset risk/return points overlaid.",
    examplePrompt: "Show the efficient frontier with individual assets plotted",
    category: "Charts & Reports",
  },
  {
    name: "Rolling Metrics",
    description: "Compute rolling Sharpe ratio, volatility, or other metrics over a sliding window.",
    examplePrompt: "Show the rolling Sharpe ratio for my portfolio over 2 years",
    category: "Charts & Reports",
  },
  {
    name: "Asset Ranking",
    description: "Rank a list of assets by a chosen metric (Sharpe, return, volatility, etc.).",
    examplePrompt: "Rank AAPL, MSFT, GOOGL by Sharpe ratio in 2023",
    category: "Charts & Reports",
  },
  {
    name: "Tearsheet",
    description: "Generate a full performance tearsheet with key metrics, charts, and attribution.",
    examplePrompt: "Generate a full tearsheet for my portfolio",
    category: "Charts & Reports",
  },
];
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd packages/web && npx vitest run src/data/tools-manifest.test.ts
```

Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/web/src/data/tools-manifest.ts packages/web/src/data/tools-manifest.test.ts
git commit -m "feat: add tools manifest data"
```

---

## Task 2: Create ToolsPanel component

**Files:**
- Create: `packages/web/src/components/chat/ToolsPanel.tsx`
- Create: `packages/web/src/components/chat/ToolsPanel.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `packages/web/src/components/chat/ToolsPanel.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ToolsPanel from "./ToolsPanel";

describe("ToolsPanel", () => {
  it("does not render panel content when closed", () => {
    render(<ToolsPanel open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders the panel header when open", () => {
    render(<ToolsPanel open={true} onClose={vi.fn()} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Research Tools")).toBeInTheDocument();
  });

  it("renders all category headings when open with no search", () => {
    render(<ToolsPanel open={true} onClose={vi.fn()} />);
    expect(screen.getByText("Data")).toBeInTheDocument();
    expect(screen.getByText("Portfolio")).toBeInTheDocument();
    expect(screen.getByText("Risk")).toBeInTheDocument();
    expect(screen.getByText("Backtesting")).toBeInTheDocument();
    expect(screen.getByText("Covariance & Returns")).toBeInTheDocument();
    expect(screen.getByText("Scenarios")).toBeInTheDocument();
    expect(screen.getByText("Attribution")).toBeInTheDocument();
    expect(screen.getByText("Charts & Reports")).toBeInTheDocument();
  });

  it("renders tool names and example prompts", () => {
    render(<ToolsPanel open={true} onClose={vi.fn()} />);
    expect(screen.getByText("Price History")).toBeInTheDocument();
    expect(
      screen.getByText(/Fetch daily prices for AAPL/)
    ).toBeInTheDocument();
  });

  it("filters tools by name when searching", () => {
    render(<ToolsPanel open={true} onClose={vi.fn()} />);
    const input = screen.getByPlaceholderText("Search tools…");
    fireEvent.change(input, { target: { value: "backtest" } });
    expect(screen.getByText("Backtest Portfolio")).toBeInTheDocument();
    expect(screen.queryByText("Price History")).not.toBeInTheDocument();
  });

  it("shows empty state when search has no matches", () => {
    render(<ToolsPanel open={true} onClose={vi.fn()} />);
    const input = screen.getByPlaceholderText("Search tools…");
    fireEvent.change(input, { target: { value: "zzznomatch" } });
    expect(screen.getByText("No tools match.")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(<ToolsPanel open={true} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when backdrop is clicked", () => {
    const onClose = vi.fn();
    render(<ToolsPanel open={true} onClose={onClose} />);
    fireEvent.click(screen.getByTestId("tools-backdrop"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when Escape key is pressed", () => {
    const onClose = vi.fn();
    render(<ToolsPanel open={true} onClose={onClose} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("resets search query when panel closes", () => {
    const { rerender } = render(<ToolsPanel open={true} onClose={vi.fn()} />);
    const input = screen.getByPlaceholderText("Search tools…");
    fireEvent.change(input, { target: { value: "risk" } });
    expect((input as HTMLInputElement).value).toBe("risk");

    rerender(<ToolsPanel open={false} onClose={vi.fn()} />);
    rerender(<ToolsPanel open={true} onClose={vi.fn()} />);
    const freshInput = screen.getByPlaceholderText("Search tools…");
    expect((freshInput as HTMLInputElement).value).toBe("");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/web && npx vitest run src/components/chat/ToolsPanel.test.tsx
```

Expected: FAIL — `Cannot find module './ToolsPanel'`

- [ ] **Step 3: Create ToolsPanel.tsx**

Create `packages/web/src/components/chat/ToolsPanel.tsx`:

```tsx
import { useState, useEffect } from "react";
import { X, Search } from "lucide-react";
import { TOOLS_MANIFEST, CATEGORIES, type Tool } from "@/data/tools-manifest";

interface ToolsPanelProps {
  open: boolean;
  onClose: () => void;
}

export default function ToolsPanel({ open, onClose }: ToolsPanelProps) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  const q = query.trim().toLowerCase();
  const filtered = q
    ? TOOLS_MANIFEST.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q)
      )
    : null;

  return (
    <>
      <div
        data-testid="tools-backdrop"
        className="fixed inset-0 z-40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-label="Research tools"
        className="fixed top-0 right-0 z-50 h-screen w-72 bg-background border-l flex flex-col shadow-xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b shrink-0">
          <h2 className="text-sm font-semibold">Research Tools</h2>
          <button
            aria-label="Close"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Search */}
        <div className="px-3 py-2 border-b shrink-0">
          <div className="flex items-center gap-2 bg-muted rounded-md px-3 py-1.5">
            <Search size={12} className="text-muted-foreground shrink-0" />
            <input
              type="text"
              placeholder="Search tools…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="bg-transparent text-xs outline-none flex-1 placeholder:text-muted-foreground"
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto py-3">
          {filtered !== null ? (
            filtered.length === 0 ? (
              <p className="text-xs text-muted-foreground px-4 py-3">
                No tools match.
              </p>
            ) : (
              <div className="px-3 flex flex-col gap-2">
                {filtered.map((tool) => (
                  <ToolCard key={tool.name} tool={tool} />
                ))}
              </div>
            )
          ) : (
            CATEGORIES.map((category) => {
              const tools = TOOLS_MANIFEST.filter(
                (t) => t.category === category
              );
              return (
                <div key={category} className="mb-4">
                  <p className="px-4 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
                    {category}
                  </p>
                  <div className="px-3 flex flex-col gap-2">
                    {tools.map((tool) => (
                      <ToolCard key={tool.name} tool={tool} />
                    ))}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </>
  );
}

function ToolCard({ tool }: { tool: Tool }) {
  return (
    <div className="rounded-md border bg-card px-3 py-2">
      <p className="text-xs font-medium text-foreground">{tool.name}</p>
      <p className="mt-1 text-[11px] text-muted-foreground/70 italic leading-relaxed">
        &ldquo;{tool.examplePrompt}&rdquo;
      </p>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd packages/web && npx vitest run src/components/chat/ToolsPanel.test.tsx
```

Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/web/src/components/chat/ToolsPanel.tsx packages/web/src/components/chat/ToolsPanel.test.tsx
git commit -m "feat: add ToolsPanel component"
```

---

## Task 3: Wire FAB and ToolsPanel into Chat.tsx

**Files:**
- Modify: `packages/web/src/pages/Chat.tsx`

No isolated unit test needed here — the FAB and ToolsPanel wiring is integration-level behavior already covered by ToolsPanel's own tests. Verify manually in the browser.

- [ ] **Step 1: Add state and imports to Chat.tsx**

Open `packages/web/src/pages/Chat.tsx`. Add these to the existing imports:

```tsx
import { useState } from "react";  // already imported via useEffect — add useState
import { Wrench } from "lucide-react";
import ToolsPanel from "@/components/chat/ToolsPanel";
```

Note: `useEffect` and `useRef` are already imported. Add `useState` to that import line:

```tsx
import { useEffect, useRef, useState } from "react";
```

- [ ] **Step 2: Add toolsPanelOpen state inside the Chat component**

Inside the `Chat` function body, after the existing `const isEmpty = messages.length === 0;` line, add:

```tsx
const [toolsPanelOpen, setToolsPanelOpen] = useState(false);
```

- [ ] **Step 3: Add ToolsPanel and FAB to the JSX**

The `Chat` component currently returns:

```tsx
return (
  <div className="flex h-[calc(100vh-3.5rem)]">
    {/* Sidebar */}
    <Sidebar ... />
    {/* Main chat area */}
    <div className="flex flex-col flex-1 min-w-0">
      ...
    </div>
  </div>
);
```

Wrap the return in a fragment and append the panel and FAB after the outer `<div>`:

```tsx
return (
  <>
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Sidebar */}
      <Sidebar
        activeConversationId={conversationId}
        onNewConversation={handleNewConversation}
      />

      {/* Main chat area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header strip */}
        <div className="flex items-center justify-between py-3 border-b shrink-0 px-6">
          <div>
            <h1 className="text-base font-semibold tracking-tight">
              Research Assistant
            </h1>
            <p className="text-xs text-muted-foreground">
              Ask questions in natural language — portfolio analysis, backtesting,
              and more
            </p>
          </div>
          {!isEmpty && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                handleNewConversation();
                navigate("/");
              }}
              className="text-xs"
            >
              New conversation
            </Button>
          )}
        </div>

        {/* Message area */}
        <div className="flex-1 overflow-y-auto py-6">
          <div className="max-w-2xl mx-auto px-4 space-y-6">
            {isEmpty ? (
              <EmptyState onPrompt={sendMessage} />
            ) : (
              messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  isStreaming={
                    isStreaming && message === messages[messages.length - 1]
                  }
                />
              ))
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input bar */}
        <div className="shrink-0 border-t py-3">
          <div className="max-w-2xl mx-auto px-4">
            <ChatInput onSend={sendMessage} disabled={isStreaming} />
            <p className="text-[11px] text-muted-foreground/60 mt-2 text-center">
              Enter to send · Shift+Enter for new line
            </p>
          </div>
        </div>
      </div>
    </div>

    {/* Tools panel */}
    <ToolsPanel
      open={toolsPanelOpen}
      onClose={() => setToolsPanelOpen(false)}
    />

    {/* FAB */}
    <button
      onClick={() => setToolsPanelOpen((v) => !v)}
      aria-label="Open research tools"
      className="fixed bottom-6 right-6 z-30 flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90 transition-colors"
    >
      <Wrench size={18} />
    </button>
  </>
);
```

- [ ] **Step 4: Run full test suite**

```bash
cd packages/web && npx vitest run
```

Expected: All tests PASS (no regressions)

- [ ] **Step 5: Verify visually in the browser**

```bash
cd packages/web && npm run dev
```

Open http://localhost:5175, navigate to Chat. Confirm:
- Wrench FAB is visible bottom-right
- Clicking FAB opens the tools panel from the right
- All 8 category sections are visible
- Searching "sharpe" shows rolling metrics, optimize portfolio, etc.
- Escape, ✕ button, and backdrop click all close the panel
- Panel does not interfere with chat input or message scrolling

- [ ] **Step 6: Commit**

```bash
git add packages/web/src/pages/Chat.tsx
git commit -m "feat: wire ToolsPanel FAB into Chat page"
```
