"""Tests for search phase execution."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from api.agent.search import run_search_phase, SearchResult
from api.agent.llm import GroundingSource


def test_search_result_dataclass():
    r = SearchResult(text="NVDA beat earnings", sources=[])
    assert r.text == "NVDA beat earnings"
    assert r.sources == []


def _make_search_gemini_response(text="NVDA beat Q4", chunks=None):
    """Build a mock Gemini response for search-only call."""
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
    mock_response.text = text
    return mock_response


@pytest.mark.asyncio
@patch("api.agent.search.create_gemini_client")
@patch("api.agent.search.MODEL_NAME", "gemini-2.5-flash")
async def test_search_phase_returns_text_and_sources(mock_factory):
    chunk = MagicMock()
    chunk.web.uri = "https://reuters.com/nvda"
    chunk.web.title = "NVDA Earnings"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_search_gemini_response(
        text="NVIDIA reported record revenue",
        chunks=[chunk],
    )
    mock_factory.return_value = mock_client

    result = await run_search_phase("what did NVDA say on their earnings call?")

    assert result.text == "NVIDIA reported record revenue"
    assert len(result.sources) == 1
    assert result.sources[0].url == "https://reuters.com/nvda"
    assert result.sources[0].title == "NVDA Earnings"
    assert result.sources[0].index == 1


@pytest.mark.asyncio
@patch("api.agent.search.create_gemini_client")
@patch("api.agent.search.MODEL_NAME", "gemini-2.5-flash")
async def test_search_phase_no_grounding_returns_empty_sources(mock_factory):
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_search_gemini_response(
        text="Some answer", chunks=[],
    )
    mock_factory.return_value = mock_client

    result = await run_search_phase("some query")

    assert result.text == "Some answer"
    assert result.sources == []


@pytest.mark.asyncio
@patch("api.agent.search.create_gemini_client")
@patch("api.agent.search.MODEL_NAME", "gemini-2.5-flash")
async def test_search_phase_uses_google_search_tool(mock_factory):
    from google.genai import types as genai_types

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_search_gemini_response()
    mock_factory.return_value = mock_client

    await run_search_phase("test query")

    call_kwargs = mock_client.models.generate_content.call_args
    config = call_kwargs.kwargs.get("config") or call_kwargs.args[2]
    tool_list = config.tools
    has_google_search = any(
        isinstance(t, genai_types.Tool) and t.google_search is not None
        for t in tool_list
    )
    assert has_google_search, "Search phase must use GoogleSearch tool"


@pytest.mark.asyncio
@patch("api.agent.search.create_gemini_client")
@patch("api.agent.search.MODEL_NAME", "gemini-2.5-flash")
async def test_search_phase_non_retriable_exception_raises(mock_factory):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API error")
    mock_factory.return_value = mock_client

    with pytest.raises(Exception, match="API error"):
        await run_search_phase("query")


@pytest.mark.asyncio
@patch("api.agent.search._openai_search", new_callable=AsyncMock)
@patch("api.agent.search.create_gemini_client")
@patch("api.agent.search.MODEL_NAME", "gemini-2.5-flash")
async def test_search_phase_retriable_falls_back_to_openai(mock_factory, mock_openai):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("503 UNAVAILABLE")
    mock_factory.return_value = mock_client
    mock_openai.return_value = SearchResult(text="OpenAI answer", sources=[])

    result = await run_search_phase("query")

    assert result.text == "OpenAI answer"
    mock_openai.assert_called_once_with("query")
