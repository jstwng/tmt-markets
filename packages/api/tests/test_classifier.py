"""Tests for intent classifier."""
import json
import pytest
from unittest.mock import AsyncMock, patch
from api.agent.classifier import classify_intent, IntentResult


def test_intent_result_dataclass():
    r = IntentResult(intent="search")
    assert r.intent == "search"


@pytest.mark.asyncio
@patch("api.agent.classifier.call_llm_text", new_callable=AsyncMock)
async def test_classify_search_intent(mock_llm):
    mock_llm.return_value = '{"intent": "search"}'
    result = await classify_intent("what did NVDA say on their last earnings call?")
    assert result.intent == "search"


@pytest.mark.asyncio
@patch("api.agent.classifier.call_llm_text", new_callable=AsyncMock)
async def test_classify_quant_intent(mock_llm):
    mock_llm.return_value = '{"intent": "quant"}'
    result = await classify_intent("optimize a portfolio of NVDA AMD AVGO")
    assert result.intent == "quant"


@pytest.mark.asyncio
@patch("api.agent.classifier.call_llm_text", new_callable=AsyncMock)
async def test_classify_hybrid_intent(mock_llm):
    mock_llm.return_value = '{"intent": "hybrid"}'
    result = await classify_intent("how did the market react to the last CPI print?")
    assert result.intent == "hybrid"


@pytest.mark.asyncio
@patch("api.agent.classifier.call_llm_text", new_callable=AsyncMock)
async def test_classify_conversational_intent(mock_llm):
    mock_llm.return_value = '{"intent": "conversational"}'
    result = await classify_intent("what is the difference between Sharpe and Sortino?")
    assert result.intent == "conversational"


@pytest.mark.asyncio
@patch("api.agent.classifier.call_llm_text", new_callable=AsyncMock)
async def test_classify_invalid_json_defaults_hybrid(mock_llm):
    mock_llm.return_value = "not valid json"
    result = await classify_intent("something weird")
    assert result.intent == "hybrid"


@pytest.mark.asyncio
@patch("api.agent.classifier.call_llm_text", new_callable=AsyncMock)
async def test_classify_unknown_intent_defaults_hybrid(mock_llm):
    mock_llm.return_value = '{"intent": "unknown_category"}'
    result = await classify_intent("something weird")
    assert result.intent == "hybrid"


@pytest.mark.asyncio
@patch("api.agent.classifier.call_llm_text", new_callable=AsyncMock)
async def test_classify_with_conversation_context(mock_llm):
    mock_llm.return_value = '{"intent": "quant"}'
    result = await classify_intent(
        "backtest that",
        conversation_context="Active portfolio: NVDA, AMD. Last action: optimize_portfolio.",
    )
    assert result.intent == "quant"
    call_args = mock_llm.call_args
    user_message = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("user_message", "")
    assert "Active portfolio" in user_message


@pytest.mark.asyncio
@patch("api.agent.classifier.call_llm_text", new_callable=AsyncMock)
async def test_classify_llm_exception_defaults_hybrid(mock_llm):
    mock_llm.side_effect = Exception("LLM unavailable")
    result = await classify_intent("anything")
    assert result.intent == "hybrid"
