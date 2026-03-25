# Deterministic Classifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unreliable LLM-based intent classifier with a deterministic keyword scanner, and simplify agent routing from 4 paths to 2 (quant_only vs search_first → unified agent loop).

**Architecture:** A pure-Python keyword/regex scanner replaces the LLM classifier call. The scanner checks for quant tool keywords, ticker patterns, and search signals. The agent route collapses: every query runs the agent loop with all 28 tools; the only decision is whether to prepend a web search phase.

**Tech Stack:** Python (regex, sets), Pytest

---

### Task 1: Write the deterministic scanner

**Files:**
- Rewrite: `packages/api/api/agent/classifier.py`
- Rewrite: `packages/api/tests/test_classifier.py`

- [ ] **Step 1: Write failing tests for the scanner**

Replace the contents of `packages/api/tests/test_classifier.py` with:

```python
"""Tests for deterministic intent scanner."""

from api.agent.classifier import classify_intent


# --- Quant-only: tool keywords ---

def test_efficient_frontier_with_tickers():
    result = classify_intent("Show the efficient frontier for SPY, TLT, GLD, and QQQ")
    assert result.intent == "quant_only"


def test_backtest_portfolio():
    result = classify_intent("backtest NVDA AMD AVGO equal weight")
    assert result.intent == "quant_only"


def test_optimize_portfolio():
    result = classify_intent("optimize a portfolio of MSFT GOOG AMZN META")
    assert result.intent == "quant_only"


def test_correlation_matrix():
    result = classify_intent("plot the correlation matrix for AAPL MSFT GOOG")
    assert result.intent == "quant_only"


def test_sharpe_ratio():
    result = classify_intent("what is the sharpe ratio of SPY vs QQQ")
    assert result.intent == "quant_only"


def test_monte_carlo():
    result = classify_intent("run a monte carlo simulation for my portfolio")
    assert result.intent == "quant_only"


def test_stress_test():
    result = classify_intent("stress test NVDA AMD AVGO")
    assert result.intent == "quant_only"


def test_var_cvar():
    result = classify_intent("compute VaR and CVaR for SPY TLT")
    assert result.intent == "quant_only"


def test_tearsheet():
    result = classify_intent("generate a tearsheet for NVDA")
    assert result.intent == "quant_only"


def test_drawdown():
    result = classify_intent("show drawdown series for QQQ")
    assert result.intent == "quant_only"


def test_factor_exposure():
    result = classify_intent("compute factor exposure for AAPL MSFT")
    assert result.intent == "quant_only"


def test_black_litterman():
    result = classify_intent("apply black-litterman to NVDA AMD AVGO with bullish views")
    assert result.intent == "quant_only"


def test_fetch_prices():
    result = classify_intent("get prices for AAPL MSFT GOOG")
    assert result.intent == "quant_only"


def test_rolling_metrics():
    result = classify_intent("show rolling metrics for SPY")
    assert result.intent == "quant_only"


def test_rebalancing():
    result = classify_intent("run rebalancing analysis for my portfolio")
    assert result.intent == "quant_only"


def test_portfolio_reference():
    result = classify_intent("backtest that portfolio")
    assert result.intent == "quant_only"


def test_casual_phrasing():
    result = classify_intent("show me the frontier for SPY and QQQ")
    assert result.intent == "quant_only"


def test_analytical_verb_with_tickers():
    result = classify_intent("compare NVDA vs AMD performance")
    assert result.intent == "quant_only"


def test_scenario_analysis():
    result = classify_intent("run scenario analysis for NVDA AMD")
    assert result.intent == "quant_only"


def test_benchmark_comparison():
    result = classify_intent("compare my portfolio to SPY benchmark")
    assert result.intent == "quant_only"


def test_expected_returns():
    result = classify_intent("estimate expected returns for AAPL MSFT GOOG")
    assert result.intent == "quant_only"


def test_constrained_optimization():
    result = classify_intent("optimize with constraints: max 20% per name")
    assert result.intent == "quant_only"


def test_ticker_alias_hyperscalers():
    result = classify_intent("backtest the hyperscalers")
    assert result.intent == "quant_only"


def test_ticker_alias_semi_equipment():
    result = classify_intent("show efficient frontier for semi equipment names")
    assert result.intent == "quant_only"


# --- Search-first: temporal/news signals ---

def test_latest_earnings():
    result = classify_intent("what did NVDA say on their latest earnings call?")
    assert result.intent == "search_first"


def test_recent_news():
    result = classify_intent("any recent news on AAPL?")
    assert result.intent == "search_first"


def test_analyst_ratings():
    result = classify_intent("what are analysts saying about MSFT?")
    assert result.intent == "search_first"


def test_guidance():
    result = classify_intent("what guidance did META give for Q2?")
    assert result.intent == "search_first"


def test_price_target():
    result = classify_intent("what is the consensus price target for NVDA?")
    assert result.intent == "search_first"


def test_market_reaction():
    result = classify_intent("how did the market react to the CPI print?")
    assert result.intent == "search_first"


def test_what_happened():
    result = classify_intent("what happened to TSLA today?")
    assert result.intent == "search_first"


def test_sec_filing():
    result = classify_intent("any new SEC filings from AAPL?")
    assert result.intent == "search_first"


def test_upgrade_downgrade():
    result = classify_intent("was NVDA upgraded recently?")
    assert result.intent == "search_first"


def test_explicit_search():
    result = classify_intent("search for AMD revenue growth trends")
    assert result.intent == "search_first"


# --- Conflict: both signals → search_first ---

def test_hybrid_quant_and_search():
    result = classify_intent("backtest NVDA based on their latest earnings guidance")
    assert result.intent == "search_first"


def test_hybrid_optimize_with_recent():
    result = classify_intent("optimize portfolio with recent NVDA price targets in mind")
    assert result.intent == "search_first"


# --- No signal → search_first (safe default) ---

def test_ambiguous_defaults_to_search_first():
    result = classify_intent("tell me about NVDA")
    assert result.intent == "search_first"


def test_conceptual_with_tool_keyword_is_quant():
    """Even conceptual questions mentioning tool keywords route to quant."""
    result = classify_intent("what is the difference between Sharpe and Sortino?")
    assert result.intent == "quant_only"


def test_greeting_defaults_to_search_first():
    result = classify_intent("hello")
    assert result.intent == "search_first"


# --- IntentResult dataclass ---

def test_intent_result_dataclass():
    from api.agent.classifier import IntentResult
    r = IntentResult(intent="quant_only")
    assert r.intent == "quant_only"
```

Run: `cd packages/api && python -m pytest tests/test_classifier.py -v`
Expected: FAIL — `classify_intent` still returns the old intent values and is async.

- [ ] **Step 2: Rewrite classifier.py with deterministic scanner**

Replace the entire contents of `packages/api/api/agent/classifier.py` with:

```python
"""Deterministic intent scanner for routing queries.

Replaces the LLM-based classifier with keyword/regex matching.
Returns quant_only (skip search) or search_first (search then agent loop).
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

__all__ = ["classify_intent", "IntentResult"]


@dataclass
class IntentResult:
    intent: str  # "quant_only" | "search_first"


# ---------------------------------------------------------------------------
# Quant signals — tool keywords that indicate quantitative analysis
# ---------------------------------------------------------------------------

TOOL_KEYWORDS: set[str] = {
    "efficient frontier", "frontier",
    "backtest", "back-test", "back test",
    "optimize", "optimization", "optimise",
    "portfolio",
    "correlation", "covariance", "cov matrix",
    "sharpe", "sortino",
    "drawdown", "max drawdown",
    "stress test", "stress-test",
    "var", "cvar", "value at risk",
    "monte carlo",
    "tearsheet", "tear sheet",
    "factor exposure", "factor analysis",
    "rebalance", "rebalancing",
    "black-litterman", "black litterman",
    "risk decomposition", "risk decomp",
    "attribution",
    "benchmark",
    "tracking error",
    "information ratio",
    "volatility",
    "rolling metrics", "rolling sharpe", "rolling vol",
    "equity curve",
    "constrained optimization",
    "liquidity score",
    "expected returns",
    "scenario analysis", "scenario table",
    "heatmap", "heat map",
    "risk metrics",
    "alpha", "beta",
}

ANALYTICAL_VERBS: set[str] = {
    "show", "run", "compute", "plot", "generate", "compare",
    "analyze", "analyse", "calculate", "fetch", "get", "build",
    "construct", "chart", "graph", "visualize", "visualise",
    "simulate", "estimate", "decompose", "rank",
}

PORTFOLIO_REFS: set[str] = {
    "my portfolio", "the portfolio", "those positions",
    "that allocation", "that portfolio", "these positions",
    "load portfolio", "save portfolio",
}

TICKER_ALIASES: set[str] = {
    "hyperscalers", "semi equipment", "tech giants",
    "ai infrastructure", "mega-cap", "megacap", "faang",
    "mag seven", "magnificent seven", "mag 7",
}

# Matches 1-5 uppercase letters that look like tickers (SPY, NVDA, AAPL, etc.)
_TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")

# Common English words that look like tickers but aren't
_TICKER_EXCLUDE: set[str] = {
    "I", "A", "AN", "AND", "THE", "FOR", "OF", "TO", "IN", "ON", "AT",
    "IS", "IT", "OR", "BY", "AS", "IF", "DO", "NO", "SO", "UP", "MY",
    "ALL", "ANY", "BUT", "CAN", "DID", "GET", "HAS", "HAD", "HER",
    "HIM", "HIS", "HOW", "ITS", "LET", "MAY", "NEW", "NOT", "NOW",
    "OLD", "OUR", "OUT", "OWN", "RUN", "SAY", "SHE", "TOO", "USE",
    "WAY", "WHO", "BOY", "DAY", "EYE", "FAR", "FEW", "GOT", "HIT",
    "HOT", "JOB", "KEY", "LOT", "MAN", "NOR", "PUT", "RED", "SET",
    "SIT", "TOP", "TRY", "WAR", "WAS", "WIN", "WON", "YES", "YET",
    "YOU", "ARE", "BIG", "END", "ERA", "GDP", "IPO", "CEO", "CFO",
    "CPI", "FED", "SEC", "ETF", "USD", "EUR", "YEN", "OIL", "GAS",
    "AI", "ML", "US", "UK", "EU", "VS", "PM", "AM", "Q", "X",
    "SHOW", "WITH", "WHAT", "WHEN", "THIS", "THAT", "FROM", "HAVE",
    "WILL", "BEEN", "THAN", "THEM", "THEN", "ALSO", "BACK", "CALL",
    "COME", "EACH", "EVEN", "FIND", "GIVE", "GOOD", "HELP", "HERE",
    "HIGH", "JUST", "KEEP", "KNOW", "LAST", "LIKE", "LIST", "LONG",
    "LOOK", "MADE", "MAKE", "MANY", "MOST", "MUCH", "MUST", "NAME",
    "NEXT", "ONLY", "OVER", "PAST", "SAME", "SOME", "SUCH", "TAKE",
    "TELL", "VERY", "WANT", "WEEK", "WELL", "WERE", "WORK", "YEAR",
    "BOTH", "DOES", "DOWN", "GOES", "GONE", "INTO", "LEFT", "LESS",
    "LOSE", "LOST", "MOVE", "NEAR", "NEED", "ONCE", "OPEN", "PART",
    "RATE", "REAL", "REST", "RISE", "RISK", "SELL", "SENT", "SIDE",
    "SOON", "STAY", "STOP", "SURE", "TERM", "TURN", "UPON", "USED",
    "VIEW", "WAIT", "WIDE", "ZERO", "DATA", "BEST", "HALF",
    "FREE", "FULL", "HARD", "HELD", "HOME", "JUNE", "JULY",
    "LEAD", "LINE", "LIVE", "LOAD", "MARK", "MIND", "NOTE",
    "PAID", "PICK", "PLAN", "PLAY", "PLUS", "POOR", "PULL",
    "PUSH", "RANK", "RICH", "SAID", "SAVE", "SEEN", "SHIP",
    "SHOT", "SIZE", "SOLD", "SORT", "STEP", "TEST", "TIED",
    "TIME", "TOLD", "TRUE", "TYPE", "UNIT", "VAST", "VOTE",
    "BOND", "BOOK", "BULL", "BEAR", "CASH", "COST", "DEAL",
    "DEBT", "DROP", "DUMP", "EARN", "EDGE", "FALL", "FAST",
    "FLAT", "FLOW", "FUND", "GAIN", "GROW", "HOLD",
    "HUGE", "JUMP", "LATE", "LEAN", "LOAN",
    "LOSS", "MASS", "MISS", "PACE", "PAIR", "PEAK",
    "PURE", "RARE", "SAFE", "SLIM", "SLOW",
    "SOFT", "SWAP", "THIN", "TRIM", "WEAK", "WRAP",
}

# ---------------------------------------------------------------------------
# Search signals — temporal/news markers
# ---------------------------------------------------------------------------

TEMPORAL_MARKERS: set[str] = {
    "latest", "recent", "recently",
    "last quarter", "last earnings", "last call",
    "this week", "this month", "this quarter",
    "today", "yesterday", "tonight",
    "just announced", "breaking",
    "guidance",
    "2024", "2025", "2026",
}

NEWS_PATTERNS: list[str] = [
    r"\bwhat did .+ (?:say|report|announce|guide)",
    r"\bwhat happened\b",
    r"\bwhat'?s going on\b",
    r"\bwhat'?s new\b",
    r"\bnews\b",
    r"\bheadlines?\b",
    r"\banalyst(?:s)?\b",
    r"\bcommentary\b",
    r"\bupgrad(?:e|ed)\b",
    r"\bdowngrad(?:e|ed)\b",
    r"\brating(?:s)?\b",
    r"\bprice target(?:s)?\b",
    r"\bearnings call\b",
    r"\bconference call\b",
    r"\binvestor day\b",
    r"\bsec filing(?:s)?\b",
    r"\bmarket reaction\b",
    r"\bsentiment\b",
    r"\bconsensus\b",
    r"\bsearch for\b",
    r"\blook up\b",
    r"\bfind out\b",
    r"\bwhat is the current\b",
]

_NEWS_RE = re.compile("|".join(NEWS_PATTERNS), re.IGNORECASE)


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def _has_tickers(text: str) -> bool:
    """Return True if text contains likely stock ticker symbols."""
    candidates = _TICKER_RE.findall(text)
    return any(c not in _TICKER_EXCLUDE for c in candidates)


def _has_quant_signal(text: str) -> bool:
    """Return True if text matches quant-only patterns."""
    lower = text.lower()

    # Direct tool keyword match
    for kw in TOOL_KEYWORDS:
        if kw in lower:
            return True

    # Portfolio reference match
    for ref in PORTFOLIO_REFS:
        if ref in lower:
            return True

    # Ticker alias match
    for alias in TICKER_ALIASES:
        if alias in lower:
            return True

    # Analytical verb + tickers
    if _has_tickers(text):
        for verb in ANALYTICAL_VERBS:
            if re.search(rf"\b{verb}\b", lower):
                return True

    # Data fetch patterns
    if re.search(r"\bprices?\s+(?:for|of)\b", lower):
        return True
    if re.search(r"\breturns?\s+(?:for|of)\b", lower):
        return True
    if re.search(r"\bhow did .+ perform", lower):
        return True

    return False


def _has_search_signal(text: str) -> bool:
    """Return True if text matches search-first patterns."""
    lower = text.lower()

    for marker in TEMPORAL_MARKERS:
        if marker in lower:
            return True

    if _NEWS_RE.search(text):
        return True

    return False


def classify_intent(message: str, conversation_context: str | None = None) -> IntentResult:
    """Classify user message intent using deterministic keyword scanning.

    Args:
        message: The user's message.
        conversation_context: Ignored (kept for API compatibility).

    Returns:
        IntentResult with "quant_only" or "search_first".
    """
    has_quant = _has_quant_signal(message)
    has_search = _has_search_signal(message)

    if has_quant and not has_search:
        intent = "quant_only"
    else:
        # search signal, both signals, or neither → search_first
        intent = "search_first"

    logger.info("Scanner classified %r as %s (quant=%s, search=%s)",
                message[:80], intent, has_quant, has_search)
    return IntentResult(intent=intent)
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd packages/api && python -m pytest tests/test_classifier.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add packages/api/api/agent/classifier.py packages/api/tests/test_classifier.py
git commit -m "feat: replace LLM classifier with deterministic keyword scanner"
```

---

### Task 2: Simplify agent routing from 4 paths to 2

**Files:**
- Modify: `packages/api/api/routes/agent.py:192-240`

- [ ] **Step 1: Update the routing logic in agent.py**

In `packages/api/api/routes/agent.py`, replace the block from the classify intent comment through the end of the hybrid search injection (lines 192-240) with:

```python
            # ------ Classify intent (deterministic) ------
            yield _sse("tool_call", {"name": "classify_intent", "args": {}})
            intent_result = classify_intent(req.message)
            logger.info("Intent classified as: %s", intent_result.intent)
            yield _sse("tool_result", {"name": "classify_intent", "result": {"intent": intent_result.intent}})

            # ------ Search phase (if search_first) ------
            search_text = ""
            if intent_result.intent == "search_first":
                yield _sse("tool_call", {"name": "web_search", "args": {}})
                search_result = await run_search_phase(req.message)
                yield _sse("tool_result", {"name": "web_search", "result": {}})
                search_text = search_result.text
                for src in search_result.sources:
                    if src.url not in seen_urls:
                        seen_urls.add(src.url)
                        all_grounding_sources.append(src)
                if search_text:
                    yield _sse("text", {"text": search_text})
                    accumulated_text += search_text

            # ------ Agent loop (always runs) ------
            if search_text:
                gemini_history.append(
                    genai_types.Content(role="model", parts=[
                        genai_types.Part(text=f"[Research context from web search]\n{search_text}")
                    ])
                )
                gemini_history.append(
                    genai_types.Content(role="user", parts=[
                        genai_types.Part(text="Now use the available quantitative tools to provide data-driven analysis.")
                    ])
                )
```

This replaces the old 4-path routing. The agent loop code that follows (the `max_iterations` for loop) stays exactly the same — it already handles the `quant`/`hybrid` case. We just removed the `search`-only and `conversational` early exits.

- [ ] **Step 2: Remove unused imports**

In `packages/api/api/routes/agent.py`, the `call_llm_text` import is no longer needed since we removed the conversational path. Update the import line:

Find:
```python
from api.agent.llm import call_llm, call_llm_text, GroundingSource
```

Replace with:
```python
from api.agent.llm import call_llm, GroundingSource
```

Also remove the `_build_classifier_context` function (lines 97-105) — it's no longer used since the deterministic scanner ignores conversation context.

And remove these unused imports/references in the route function — the `call_llm_text` was the only consumer of these in the conversational path. Find and remove:
```python
from api.agent.classifier import classify_intent
```

This import stays — we still call `classify_intent`, it's just no longer async.

**Important:** The `classify_intent` call is no longer `await`ed since the new scanner is synchronous. Make sure the call reads:
```python
intent_result = classify_intent(req.message)
```
NOT:
```python
intent_result = await classify_intent(req.message)
```

- [ ] **Step 3: Remove the old 4-path routing block**

Make sure the old routing block is fully replaced. The section between `# ------ Phase 2: Route by intent ------` and the start of `max_iterations = 8` should be gone. The new code goes straight from search phase → search context injection → agent loop.

Specifically, these lines must be deleted:

```python
            # ------ Phase 2: Route by intent ------
            if intent_result.intent == "search" and search_text:
                # Search-only: search text is the final answer, no agent loop
                pass

            elif intent_result.intent in ("search", "conversational"):
                # No tools — plain text generation (also fallback when search returned empty)
                response_text = await call_llm_text(
                    dynamic_system_prompt, req.message,
                    temperature=0.1, max_tokens=2048,
                )
                yield _sse("text", {"text": response_text})
                accumulated_text += response_text

            else:
                # quant or hybrid — run the agent loop
                if intent_result.intent == "hybrid" and search_text:
                    # Inject search context into history for the agent loop
                    gemini_history.append(
                        genai_types.Content(role="model", parts=[
                            genai_types.Part(text=f"[Research context from web search]\n{search_text}")
                        ])
                    )
                    gemini_history.append(
                        genai_types.Content(role="user", parts=[
                            genai_types.Part(text="Now use the available quantitative tools to provide data-driven analysis.")
                        ])
                    )
```

And the agent loop (`max_iterations = 8` and everything inside it) must be de-indented by one level since it's no longer inside an `else:` block.

- [ ] **Step 4: Run backend tests to verify nothing broke**

Run: `cd packages/api && python -m pytest tests/ -v --ignore=tests/test_openbb_codegen.py`
Expected: ALL PASS (the classifier tests pass with new scanner, all other tests unaffected)

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/routes/agent.py
git commit -m "refactor: simplify agent routing from 4 paths to 2 — always run agent loop"
```

---

### Task 3: Verify end-to-end

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `cd packages/api && python -m pytest tests/ -v --ignore=tests/test_openbb_codegen.py`
Expected: ALL PASS

- [ ] **Step 2: Run all frontend tests**

Run: `cd packages/web && npx vitest run`
Expected: ALL PASS

- [ ] **Step 3: Commit (if any fixups needed)**

```bash
git add -u
git commit -m "fix: address test failures from classifier rewrite"
```

Only commit if Step 1 or 2 required fixes. Skip if everything passed clean.
