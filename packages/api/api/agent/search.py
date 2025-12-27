"""Search phase — Gemini with google_search primary, OpenAI web_search_preview fallback."""

import asyncio
import json
import logging
import os
from dataclasses import dataclass

from api.agent.llm import GroundingSource, _is_gemini_retriable
from api.agent.client import create_gemini_client, MODEL_NAME

logger = logging.getLogger(__name__)

__all__ = ["run_search_phase", "SearchResult"]

SEARCH_SYSTEM_PROMPT = """\
You are an experienced TMT portfolio manager answering a financial research question \
using web search. Be concise, data-anchored, and cite specific figures when available. \
Institutional tone — no hype or colloquialisms.\
"""


@dataclass
class SearchResult:
    text: str
    sources: list[GroundingSource]


async def _gemini_search(user_message: str) -> SearchResult:
    """Gemini call with ONLY google_search tool."""
    from google.genai import types as genai_types

    client = create_gemini_client()
    config = genai_types.GenerateContentConfig(
        system_instruction=SEARCH_SYSTEM_PROMPT,
        tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
        temperature=0.1,
        max_output_tokens=2048,
    )

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL_NAME,
        contents=[genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_message)],
        )],
        config=config,
    )

    text = response.text or ""

    sources: list[GroundingSource] = []
    try:
        chunks = response.candidates[0].grounding_metadata.grounding_chunks or []
        for i, chunk in enumerate(chunks):
            web = getattr(chunk, "web", None)
            if web and getattr(web, "uri", None):
                sources.append(GroundingSource(
                    index=i + 1,
                    title=getattr(web, "title", None) or web.uri,
                    url=web.uri,
                    date=None,
                ))
    except (AttributeError, IndexError):
        pass

    return SearchResult(text=text, sources=sources)


async def _openai_search(user_message: str) -> SearchResult:
    """OpenAI Responses API with web_search_preview tool."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set — cannot fall back to OpenAI search")

    client = OpenAI(api_key=api_key)
    response = await asyncio.to_thread(
        client.responses.create,
        model="gpt-4o",
        instructions=SEARCH_SYSTEM_PROMPT,
        input=[{"role": "user", "content": user_message}],
        tools=[{"type": "web_search_preview"}],
        temperature=0.1,
        max_output_tokens=2048,
    )

    text = ""
    sources: list[GroundingSource] = []
    source_idx = 0

    for item in response.output:
        if item.type == "message":
            for content in getattr(item, "content", []):
                if hasattr(content, "text") and content.text:
                    text += content.text
                for ann in getattr(content, "annotations", []):
                    if getattr(ann, "type", None) == "url_citation":
                        source_idx += 1
                        sources.append(GroundingSource(
                            index=source_idx,
                            title=getattr(ann, "title", None) or ann.url,
                            url=ann.url,
                            date=None,
                        ))

    return SearchResult(text=text, sources=sources)


async def run_search_phase(user_message: str) -> SearchResult:
    """Run web search. Gemini primary, OpenAI fallback.

    Raises on failure — does NOT silently return empty.
    """
    try:
        return await _gemini_search(user_message)
    except Exception as e:
        if _is_gemini_retriable(e):
            logger.warning("Gemini search unavailable (%s), falling back to OpenAI", e)
            return await _openai_search(user_message)
        raise
