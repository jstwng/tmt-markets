"""Search phase — Gemini call with google_search only, no function calling."""

import asyncio
import logging
from dataclasses import dataclass

from api.agent.llm import GroundingSource
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


async def run_search_phase(user_message: str) -> SearchResult:
    """Run a Gemini call with ONLY google_search to get grounded web results.

    Returns SearchResult with the response text and extracted citations.
    Returns empty SearchResult on any failure (never raises).
    """
    from google.genai import types as genai_types

    client = create_gemini_client()
    config = genai_types.GenerateContentConfig(
        system_instruction=SEARCH_SYSTEM_PROMPT,
        tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
        temperature=0.1,
        max_output_tokens=2048,
    )

    try:
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
    except Exception as e:
        logger.warning("Search phase failed: %s", e)
        return SearchResult(text="", sources=[])
