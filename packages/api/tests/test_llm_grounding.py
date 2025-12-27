"""Tests for GroundingSource extraction in LLMResponse."""
import asyncio
import pytest
from unittest.mock import MagicMock, patch
from api.agent.llm import GroundingSource, LLMResponse, LLMPart


def test_grounding_source_defaults():
    s = GroundingSource(index=1, title="Reuters", url="https://reuters.com/a", date="2024-01-28")
    assert s.index == 1
    assert s.title == "Reuters"
    assert s.url == "https://reuters.com/a"
    assert s.date == "2024-01-28"


def test_grounding_source_date_optional():
    s = GroundingSource(index=1, title="X", url="https://x.com", date=None)
    assert s.date is None


def test_llm_response_grounding_sources_default_empty():
    r = LLMResponse(parts=[LLMPart(text="hello")], provider="gemini")
    assert r.grounding_sources == []


def _make_gemini_response(text="hello", chunks=None):
    """Build a mock Gemini GenerateContentResponse."""
    mock_part = MagicMock()
    mock_part.text = text
    mock_part.function_call = None

    mock_metadata = MagicMock()
    mock_metadata.grounding_chunks = chunks or []

    mock_candidate = MagicMock()
    mock_candidate.grounding_metadata = mock_metadata

    mock_response = MagicMock()
    mock_response.parts = [mock_part]
    mock_response.candidates = [mock_candidate]
    return mock_response


@pytest.mark.asyncio
@patch("api.agent.client.create_gemini_client")
@patch("api.agent.client.MODEL_NAME", "gemini-2.5-flash")
async def test_gemini_no_grounding_returns_empty_sources(mock_factory):
    from api.agent.llm import _call_gemini
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_gemini_response()
    mock_factory.return_value = mock_client

    mock_tools = MagicMock()
    mock_tools.function_declarations = []
    result = await _call_gemini([], "system", mock_tools)
    assert result.grounding_sources == []


@pytest.mark.asyncio
@patch("api.agent.client.create_gemini_client")
@patch("api.agent.client.MODEL_NAME", "gemini-2.5-flash")
async def test_gemini_extracts_grounding_chunks(mock_factory):
    from api.agent.llm import _call_gemini

    chunk = MagicMock()
    chunk.web.uri = "https://reuters.com/nvda"
    chunk.web.title = "NVIDIA Q4 Earnings"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_gemini_response(chunks=[chunk])
    mock_factory.return_value = mock_client

    mock_tools = MagicMock()
    mock_tools.function_declarations = []
    result = await _call_gemini([], "system", mock_tools)

    assert len(result.grounding_sources) == 1
    assert result.grounding_sources[0].index == 1
    assert result.grounding_sources[0].url == "https://reuters.com/nvda"
    assert result.grounding_sources[0].title == "NVIDIA Q4 Earnings"


def _make_openai_response(text="hello", url_citations=None, function_calls=None):
    """Build a mock OpenAI Responses API response."""
    output_items = []

    # Text message item with optional annotations
    annotations = []
    for cit in (url_citations or []):
        ann = MagicMock()
        ann.type = "url_citation"
        ann.url = cit["url"]
        ann.title = cit.get("title", cit["url"])
        annotations.append(ann)

    content_item = MagicMock()
    content_item.text = text
    content_item.annotations = annotations

    message_item = MagicMock()
    message_item.type = "message"
    message_item.content = [content_item]
    output_items.append(message_item)

    # Function call items
    for fc in (function_calls or []):
        fc_item = MagicMock()
        fc_item.type = "function_call"
        fc_item.name = fc["name"]
        fc_item.arguments = fc["arguments"]
        output_items.append(fc_item)

    mock_response = MagicMock()
    mock_response.output = output_items
    return mock_response


@pytest.mark.asyncio
@patch("openai.OpenAI")
async def test_openai_fallback_no_citations(mock_openai_cls):
    from api.agent.llm import _call_openai

    mock_client = MagicMock()
    mock_client.responses.create.return_value = _make_openai_response(text="result")
    mock_openai_cls.return_value = mock_client

    mock_tools = MagicMock()
    mock_tools.function_declarations = []

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        result = await _call_openai([], "system", mock_tools)

    assert result.provider == "openai"
    assert result.parts[0].text == "result"
    assert result.grounding_sources == []


@pytest.mark.asyncio
@patch("openai.OpenAI")
async def test_openai_fallback_extracts_url_citations(mock_openai_cls):
    from api.agent.llm import _call_openai

    mock_client = MagicMock()
    mock_client.responses.create.return_value = _make_openai_response(
        text="NVDA beat earnings",
        url_citations=[
            {"url": "https://reuters.com/nvda", "title": "NVDA Q4"},
            {"url": "https://bloomberg.com/nvda", "title": "Street View"},
        ],
    )
    mock_openai_cls.return_value = mock_client

    mock_tools = MagicMock()
    mock_tools.function_declarations = []

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        result = await _call_openai([], "system", mock_tools)

    assert len(result.grounding_sources) == 2
    assert result.grounding_sources[0].index == 1
    assert result.grounding_sources[0].url == "https://reuters.com/nvda"
    assert result.grounding_sources[0].title == "NVDA Q4"
    assert result.grounding_sources[1].index == 2


@pytest.mark.asyncio
@patch("openai.OpenAI")
async def test_openai_fallback_extracts_function_calls(mock_openai_cls):
    from api.agent.llm import _call_openai

    mock_client = MagicMock()
    mock_client.responses.create.return_value = _make_openai_response(
        function_calls=[{"name": "fetch_prices", "arguments": '{"tickers": ["NVDA"]}'}]
    )
    mock_openai_cls.return_value = mock_client

    mock_tools = MagicMock()
    mock_tools.function_declarations = []

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        result = await _call_openai([], "system", mock_tools)

    fn_parts = [p for p in result.parts if p.function_call]
    assert len(fn_parts) == 1
    assert fn_parts[0].function_call["name"] == "fetch_prices"
    assert fn_parts[0].function_call["args"] == {"tickers": ["NVDA"]}
