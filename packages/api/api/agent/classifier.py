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
    "value at risk",
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
}

# Short keywords that require word-boundary matching to avoid false positives
# (e.g. "vary", "alphabetical", "beta testing")
_WORD_BOUNDARY_KEYWORDS: set[str] = {
    "var", "cvar", "alpha", "beta",
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
    "TELL", "VERY", "WANT", "WEEK", "WERE", "WORK", "YEAR",
    "BOTH", "DOES", "DOWN", "GOES", "GONE", "INTO", "LEFT", "LESS",
    "LOSE", "LOST", "MOVE", "NEAR", "NEED", "ONCE", "OPEN", "PART",
    "RATE", "REST", "RISE", "RISK", "SELL", "SENT", "SIDE",
    "SOON", "STAY", "STOP", "SURE", "TERM", "TURN", "UPON", "USED",
    "VIEW", "WAIT", "WIDE", "ZERO", "DATA", "BEST", "HALF",
    "FREE", "FULL", "HARD", "HELD", "HOME", "JUNE", "JULY",
    "LEAD", "LINE", "LIVE", "LOAD", "MARK", "MIND", "NOTE",
    "PAID", "PICK", "PLAN", "PLAY", "PLUS", "POOR", "PULL",
    "PUSH", "RANK", "RICH", "SAID", "SAVE", "SEEN", "SHIP",
    "SHOT", "SIZE", "SOLD", "SORT", "STEP", "TEST", "TIED",
    "TIME", "TOLD", "TRUE", "TYPE", "UNIT", "VAST", "VOTE",
    "BOOK", "CASH", "DEAL",
    "DEBT", "DROP", "DUMP", "EARN", "EDGE", "FALL",
    "FLAT", "FLOW", "FUND", "GROW",
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

    # Direct tool keyword match (substring — safe for multi-word/long keywords)
    for kw in TOOL_KEYWORDS:
        if kw in lower:
            return True

    # Short keywords matched with word boundaries to avoid substring false positives
    for kw in _WORD_BOUNDARY_KEYWORDS:
        if re.search(rf"\b{kw}\b", lower):
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
