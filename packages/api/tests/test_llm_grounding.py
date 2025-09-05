"""Tests for GroundingSource extraction in LLMResponse."""
import pytest
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
