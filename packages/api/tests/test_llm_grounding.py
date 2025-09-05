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


@pytest.mark.asyncio
@patch("api.agent.client.create_gemini_client")
@patch("api.agent.client.MODEL_NAME", "gemini-2.5-flash")
async def test_gemini_grounding_config_includes_google_search(mock_factory):
    from api.agent.llm import _call_gemini
    from google.genai import types as genai_types

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_gemini_response()
    mock_factory.return_value = mock_client

    mock_tools = MagicMock()
    mock_tools.function_declarations = []
    await _call_gemini([], "system", mock_tools)

    call_kwargs = mock_client.models.generate_content.call_args
    config = call_kwargs.kwargs.get("config") or call_kwargs.args[2]
    tool_list = config.tools
    has_google_search = any(
        isinstance(t, genai_types.Tool) and t.google_search is not None
        for t in tool_list
    )
    assert has_google_search, "GenerateContentConfig.tools must include a GoogleSearch tool"
