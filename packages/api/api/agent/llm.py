"""LLM abstraction with Gemini primary and OpenAI fallback.

Provides a unified interface that tries Gemini first, and if it gets a
503/UNAVAILABLE or rate-limit error, falls back to OpenAI with equivalent
tool-calling support.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

__all__ = ["call_llm", "call_llm_text", "LLMResponse", "LLMPart", "GroundingSource"]

_SUPERSCRIPT_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"


def _to_superscript(n: int) -> str:
    """Convert an integer to Unicode superscript digits (e.g. 12 → '¹²')."""
    return "".join(_SUPERSCRIPT_DIGITS[int(d)] for d in str(n))


@dataclass
class LLMPart:
    """Unified representation of a response part (text or function call)."""
    text: str | None = None
    function_call: dict | None = None  # {"name": str, "args": dict}


@dataclass
class GroundingSource:
    """A single grounded web citation from either Gemini or OpenAI search."""
    index: int
    title: str
    url: str
    date: str | None


@dataclass
class LLMResponse:
    """Unified LLM response."""
    parts: list[LLMPart] = field(default_factory=list)
    provider: str = ""  # "gemini" or "openai"
    grounding_sources: list["GroundingSource"] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

_GEMINI_RETRIABLE_ERRORS = ("503", "UNAVAILABLE", "overloaded", "high demand", "RESOURCE_EXHAUSTED")


def _is_gemini_retriable(exc: Exception) -> bool:
    msg = str(exc)
    return any(token in msg for token in _GEMINI_RETRIABLE_ERRORS)


async def _call_gemini(history, system_prompt: str, tool_declarations, config_overrides: dict | None = None) -> LLMResponse:
    from google import genai
    from google.genai import types as genai_types
    from api.agent.client import create_gemini_client, MODEL_NAME

    client = create_gemini_client()

    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[tool_declarations],
        temperature=0.1,
        max_output_tokens=2048,
    )

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL_NAME,
        contents=history,
        config=config,
    )

    parts = []
    for part in (response.parts or []):
        if part.text:
            parts.append(LLMPart(text=part.text))
        if part.function_call:
            fn = part.function_call
            parts.append(LLMPart(function_call={
                "name": fn.name,
                "args": dict(fn.args) if fn.args else {},
            }))

    # Extract Google Search grounding citations
    grounding_sources: list[GroundingSource] = []
    try:
        chunks = response.candidates[0].grounding_metadata.grounding_chunks or []
        for i, chunk in enumerate(chunks):
            web = getattr(chunk, "web", None)
            if web and getattr(web, "uri", None):
                grounding_sources.append(GroundingSource(
                    index=i + 1,
                    title=getattr(web, "title", None) or web.uri,
                    url=web.uri,
                    date=None,
                ))
    except (AttributeError, IndexError):
        pass  # No grounding metadata — search was not invoked

    return LLMResponse(parts=parts, provider="gemini", grounding_sources=grounding_sources)


# ---------------------------------------------------------------------------
# OpenAI fallback (Responses API)
# ---------------------------------------------------------------------------

def _gemini_tool_to_openai(tool_declarations) -> list[dict]:
    """Convert Gemini tool declarations to OpenAI Responses API format (flat)."""
    tools = []
    for fn_decl in tool_declarations.function_declarations:
        params = _schema_to_json_schema(fn_decl.parameters)
        tools.append({
            "type": "function",
            "name": fn_decl.name,
            "description": fn_decl.description or "",
            "parameters": params,
        })
    return tools


def _schema_to_json_schema(schema) -> dict:
    """Convert a Gemini Schema to JSON Schema dict for OpenAI."""
    from google.genai import types as genai_types

    type_map = {
        genai_types.Type.STRING: "string",
        genai_types.Type.NUMBER: "number",
        genai_types.Type.INTEGER: "integer",
        genai_types.Type.BOOLEAN: "boolean",
        genai_types.Type.ARRAY: "array",
        genai_types.Type.OBJECT: "object",
    }

    result: dict = {}
    if schema.type:
        result["type"] = type_map.get(schema.type, "string")
    if schema.description:
        result["description"] = schema.description
    if schema.enum:
        result["enum"] = list(schema.enum)

    if schema.type == genai_types.Type.OBJECT and schema.properties:
        result["properties"] = {
            name: _schema_to_json_schema(prop)
            for name, prop in schema.properties.items()
        }
        if schema.required:
            result["required"] = list(schema.required)

    if schema.type == genai_types.Type.ARRAY and schema.items:
        result["items"] = _schema_to_json_schema(schema.items)

    return result


def _gemini_history_to_openai_messages(history) -> list[dict]:
    """Convert Gemini Content history to OpenAI Responses API input format.
    Uses function_call / function_call_output types instead of Chat Completions format."""
    messages = []
    for content in history:
        role = "assistant" if content.role == "model" else "user"
        for part in content.parts:
            if hasattr(part, "text") and part.text:
                messages.append({"role": role, "content": part.text})
            elif hasattr(part, "function_call") and part.function_call:
                fn = part.function_call
                messages.append({
                    "type": "function_call",
                    "name": fn.name,
                    "arguments": json.dumps(dict(fn.args) if fn.args else {}),
                    "call_id": f"call_{fn.name}",
                })
            elif hasattr(part, "function_response") and part.function_response:
                fr = part.function_response
                messages.append({
                    "type": "function_call_output",
                    "call_id": f"call_{fr.name}",
                    "output": json.dumps(fr.response),
                })
    return messages


async def _call_openai(history, system_prompt: str, tool_declarations) -> LLMResponse:
    from openai import OpenAI, APIError

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set — cannot fall back to OpenAI")

    client = OpenAI(api_key=api_key)
    messages = _gemini_history_to_openai_messages(history)
    function_tools = _gemini_tool_to_openai(tool_declarations)
    tools = function_tools + [{"type": "web_search_preview"}]

    try:
        response = await asyncio.to_thread(
            client.responses.create,
            model="gpt-4o",
            instructions=system_prompt,
            input=messages,
            tools=tools,
            temperature=0.1,
            max_output_tokens=2048,
        )
    except APIError as e:
        logger.error("OpenAI Responses API error: %s", e)
        return LLMResponse(
            parts=[LLMPart(text="I encountered an issue processing your request. Please try again.")],
            provider="openai",
        )

    parts: list[LLMPart] = []
    grounding_sources: list[GroundingSource] = []
    source_idx = 0
    annotation_replacements: list[tuple[str, str]] = []

    for item in (response.output or []):
        if item.type == "function_call":
            parts.append(LLMPart(function_call={
                "name": item.name,
                "args": json.loads(item.arguments) if item.arguments else {},
            }))
        elif item.type == "message":
            for content in getattr(item, "content", []):
                if hasattr(content, "text") and content.text:
                    parts.append(LLMPart(text=content.text))
                for ann in (getattr(content, "annotations", []) or []):
                    if getattr(ann, "type", None) == "url_citation":
                        source_idx += 1
                        grounding_sources.append(GroundingSource(
                            index=source_idx,
                            title=getattr(ann, "title", None) or ann.url,
                            url=ann.url,
                            date=None,
                        ))
                        marker = getattr(ann, "text", None)
                        if marker:
                            annotation_replacements.append((marker, _to_superscript(source_idx)))

    # Replace OpenAI 【...】 markers with Unicode superscript numbers
    for part in parts:
        if part.text:
            for marker, superscript in annotation_replacements:
                part.text = part.text.replace(marker, superscript)

    return LLMResponse(parts=parts, provider="openai", grounding_sources=grounding_sources)


# ---------------------------------------------------------------------------
# Unified entrypoint
# ---------------------------------------------------------------------------

async def call_llm_text(system_prompt: str, user_message: str, temperature: float = 0.0, max_tokens: int = 4096) -> str:
    """Call LLM for plain text generation (no tools). Gemini primary, OpenAI fallback.

    Args:
        system_prompt: System instruction.
        user_message: User turn content.
        temperature: Sampling temperature.
        max_tokens: Max output tokens.

    Returns:
        Raw text response string.
    """
    async def _gemini() -> str:
        from google.genai import types as genai_types
        from api.agent.client import create_gemini_client, MODEL_NAME

        client = create_gemini_client()
        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL_NAME,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part(text=user_message)])],
            config=config,
        )
        return response.text or ""

    async def _openai() -> str:
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not set — cannot fall back to OpenAI")
        client = OpenAI(api_key=api_key)
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    try:
        return await _gemini()
    except Exception as e:
        if _is_gemini_retriable(e):
            logger.warning("Gemini unavailable for text call (%s), falling back to OpenAI", e)
            return await _openai()
        raise


async def call_llm(history, system_prompt: str, tool_declarations) -> LLMResponse:
    """Call LLM with Gemini as primary, OpenAI as fallback.

    Tries Gemini first. If it returns a 503/UNAVAILABLE/rate-limit error,
    falls back to OpenAI gpt-4o with the same tools and history.
    """
    try:
        return await _call_gemini(history, system_prompt, tool_declarations)
    except Exception as e:
        if _is_gemini_retriable(e):
            logger.warning("Gemini unavailable (%s), falling back to OpenAI", e)
            try:
                return await _call_openai(history, system_prompt, tool_declarations)
            except Exception as fallback_err:
                logger.error("OpenAI fallback also failed: %s", fallback_err)
                raise fallback_err from e
        raise
