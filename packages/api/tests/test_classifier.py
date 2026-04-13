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
