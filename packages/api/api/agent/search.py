"""Search phase — Gemini with google_search primary, OpenAI web_search_preview fallback."""

import asyncio
import re
import json
import logging
import os
from dataclasses import dataclass

from api.agent.llm import GroundingSource, _is_gemini_retriable
from api.agent.client import create_gemini_client, MODEL_NAME

logger = logging.getLogger(__name__)

__all__ = ["run_search_phase", "SearchResult"]

_SUPERSCRIPT_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"


def _to_superscript(n: int) -> str:
    """Convert an integer to Unicode superscript digits (e.g. 12 → '¹²')."""
    return "".join(_SUPERSCRIPT_DIGITS[int(d)] for d in str(n))


SEARCH_SYSTEM_PROMPT = """\
You are an experienced TMT portfolio manager answering a financial research question \
using web search. Be concise, data-anchored, and cite specific figures when available. \
Institutional tone — no hype or colloquialisms.

Citation format: use Unicode superscript numbers (¹, ², ³, ⁴, ⁵) immediately after \
each claim, corresponding to the search result index that supports it. Every factual \
claim from a search result MUST have a superscript citation. \
Never fabricate source attributions — do not write "according to X" or "X reports" \
unless it is backed by a numbered search result.\
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

    # Gemini grounded search uses (domain.com) parenthetical citations.
    # Replace them with Unicode superscript numbers matching source indices.
    text = _replace_parenthetical_citations(text, sources)

    return SearchResult(text=text, sources=sources)


def _replace_parenthetical_citations(text: str, sources: list[GroundingSource]) -> str:
    """Replace (domain.com) citations with superscript numbers.

    Builds a domain→index map from sources, then replaces patterns like
    (example.com) or (sub.example.com) with the corresponding superscript.
    """
    if not sources:
        return text

    from urllib.parse import urlparse

    # Build domain → source index map (first occurrence wins)
    domain_to_idx: dict[str, int] = {}
    for src in sources:
        try:
            domain = urlparse(src.url).netloc.lower()
            # Also add without www. prefix
            bare = domain.removeprefix("www.")
            for d in (domain, bare):
                if d and d not in domain_to_idx:
                    domain_to_idx[d] = src.index
        except Exception:
            continue

    if not domain_to_idx:
        return text

    # Match (domain.tld) patterns — conservative: only inside parentheses
    def _replace(match: re.Match) -> str:
        domain = match.group(1).lower().strip()
        idx = domain_to_idx.get(domain)
        if idx is None:
            # Try without www.
            idx = domain_to_idx.get(domain.removeprefix("www."))
        if idx is not None:
            return _to_superscript(idx)
        return match.group(0)  # Leave unmatched parentheticals alone

    # Pattern: (word.word) or (word.word.word) — looks like a domain in parens
    return re.sub(r'\(([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\)', _replace, text)


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
    # Map annotation text markers to superscript numbers for replacement
    annotation_replacements: list[tuple[str, str]] = []

    for item in (response.output or []):
        if item.type == "message":
            for content in getattr(item, "content", []):
                if hasattr(content, "text") and content.text:
                    text += content.text
                for ann in (getattr(content, "annotations", []) or []):
                    if getattr(ann, "type", None) == "url_citation":
                        source_idx += 1
                        sources.append(GroundingSource(
                            index=source_idx,
                            title=getattr(ann, "title", None) or ann.url,
                            url=ann.url,
                            date=None,
                        ))
                        # OpenAI inserts 【...】 markers; replace with superscripts
                        marker = getattr(ann, "text", None)
                        if marker:
                            superscript = _to_superscript(source_idx)
                            annotation_replacements.append((marker, superscript))

    # Replace OpenAI citation markers with Unicode superscript numbers
    for marker, superscript in annotation_replacements:
        text = text.replace(marker, superscript)

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
