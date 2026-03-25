# Deterministic Classifier with Unified Agent Loop

**Date**: 2026-04-09
**Status**: Approved

## Problem

The LLM-based intent classifier is unreliable. Queries like "Show the efficient frontier for SPY, TLT, GLD, and QQQ" — which explicitly mention a quant tool and tickers — get misclassified as `search`, causing web searches instead of running the quantitative tools. Prompt-tuning has failed to fix this after multiple attempts.

## Solution

Replace the LLM classifier with a deterministic keyword scanner. Collapse the 4-path routing (`search`/`quant`/`hybrid`/`conversational`) to 2 paths: `quant_only` (skip search) and `search_first` (search then agent loop). The agent loop always runs with all 28 tools regardless.

## Architecture

Two-layer system:
1. **Deterministic keyword scanner** — fast regex/set-based check. Returns `quant_only` or `search_first`.
2. **Unified agent loop** — always runs with all 28 tools. The scanner only decides whether to prepend a web search.

The LLM classifier (`call_llm_text` for classification) is deleted. The `conversational` path (`call_llm_text` with no tools) is deleted — the agent loop handles plain conversation naturally when it chooses not to call tools.

## Deterministic Scanner Logic

```
scan(query) → "quant_only" | "search_first"
```

### Quant-Only Signals (any match → skip search)

**Tool keywords:**
`efficient frontier`, `backtest`, `optimize`, `optimization`, `portfolio`, `correlation`, `covariance`, `sharpe`, `sortino`, `drawdown`, `stress test`, `var`, `cvar`, `value at risk`, `monte carlo`, `tearsheet`, `factor exposure`, `factor analysis`, `rebalance`, `rebalancing`, `black-litterman`, `risk decomposition`, `risk decomp`, `attribution`, `benchmark`, `tracking error`, `information ratio`, `alpha`, `beta`, `volatility`, `rolling metrics`, `equity curve`, `frontier`, `constrained optimization`, `liquidity score`, `expected returns`, `scenario analysis`, `heatmap`

**Analytical verbs (when paired with tickers or "portfolio"):**
`show`, `run`, `compute`, `plot`, `generate`, `compare`, `analyze`, `calculate`, `fetch`, `get`, `build`, `construct`, `chart`, `graph`, `visualize`, `simulate`, `estimate`, `decompose`, `rank`

**Data fetch patterns:**
- `price(s) for/of [TICKERS]`
- `how did [TICKER] perform`
- `returns for/of [TICKERS]`

**Portfolio references:**
- `my portfolio`, `the portfolio`, `those positions`, `that allocation`
- `load portfolio`, `save portfolio`

**Ticker detection:**
- 1-5 uppercase letters matching common exchange patterns (SPY, NVDA, AAPL, etc.)
- Known aliases from system prompt: `hyperscalers`, `semi equipment`, `tech giants`, `AI infrastructure`

### Search-First Signals (any match → run search then agent loop)

**Temporal markers:**
`latest`, `recent`, `recently`, `last quarter`, `last earnings`, `this week`, `this month`, `today`, `yesterday`, `Q1`/`Q2`/`Q3`/`Q4` + year, `2024`, `2025`, `2026`, `guidance`, `just announced`, `breaking`

**News/research patterns:**
- `what did [X] say/report/announce/guide`
- `what happened`, `what's going on`, `what's new`
- `news`, `headlines`, `analyst`, `commentary`, `upgrade`, `downgrade`, `rating`, `price target`
- `earnings call`, `conference call`, `investor day`, `SEC filing`
- `market reaction`, `sentiment`, `consensus`

**Explicit search intent:**
- `search for`, `look up`, `find out`, `what is the current`

### Conflict Resolution

- Both quant AND search signals → `search_first` (search context won't hurt, agent loop still runs all tools)
- Neither signal → `search_first` (safe default)

## Route Changes in agent.py

Current 4-path routing collapses to 2 paths:

```
quant_only:
  → skip search, run agent loop with all tools

search_first:
  → run search phase
  → inject search context into history
  → run agent loop with all tools
```

Eliminated paths:
- `conversational` (plain `call_llm_text` with no tools) — agent loop handles this naturally
- `search`-only (search text as final answer) — agent loop always runs after search

## Files Changed

| File | Change |
|---|---|
| `classifier.py` | Gut and rewrite — replace LLM classifier with deterministic scanner |
| `agent.py` | Simplify routing from 4 paths to 2 |
| `test_classifier.py` | Rewrite — test deterministic patterns instead of LLM mocks |

## Files NOT Changed

- `search.py` — search phase logic stays the same
- `llm.py` — agent loop LLM calls stay the same
- `tools.py` — tool declarations unchanged
- `prompts.py` — system prompt unchanged
- Frontend — no changes, SSE events are the same
