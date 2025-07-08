# LLM Router: Search Grounding, Session State & Citation Rendering — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance the existing agentic loop with Google Search grounding, explicit portfolio session state, and inline citation rendering with a collapsed Sources toggle.

**Architecture:** The existing `routes/agent.py` + `agent/llm.py` loop is the router. Google Search grounding is enabled on every Gemini call via `GoogleSearch()` in `GenerateContentConfig`. The OpenAI fallback switches from Chat Completions to the Responses API to support `web_search_preview`. Session state lives in `agent/router_state.py` (in-memory dict keyed by `conversation_id`, cold-start reconstructed from DB). Citations are a new `CitationsFooter` React component appended to assistant messages.

**Tech Stack:** Python 3.12 / FastAPI / google-genai SDK 1.x / openai 2.x / React 19 / TypeScript / Tailwind CSS / Supabase Postgres

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Modify | `packages/api/api/agent/llm.py` | Add `GroundingSource` dataclass, Google Search grounding, OpenAI Responses API fallback, citation extraction |
| Create | `packages/api/api/agent/router_state.py` | `RouterSession` dataclass, in-memory session store, cold-start reconstruction |
| Modify | `packages/api/api/agent/prompts.py` | Add `format_active_portfolio()` helper |
| Modify | `packages/api/api/routes/agent.py` | Inject portfolio context, update session state, accumulate + emit grounding_sources |
| Create | `packages/api/tests/test_llm_grounding.py` | Tests for grounding extraction in both providers |
| Create | `packages/api/tests/test_router_state.py` | Tests for session state management |
| Supabase | migration SQL | Add `grounding_sources jsonb` column to `messages` |
| Modify | `packages/web/src/api/chat-types.ts` | Add `GroundingSource` interface, update `ChatMessage`, update `SSEDoneEvent` |
| Modify | `packages/web/src/hooks/useChat.ts` | Capture `grounding_sources` from `done` event, hydrate on `loadConversation` |
| Create | `packages/web/src/components/chat/CitationsFooter.tsx` | Collapsed Sources toggle with numbered links |
| Modify | `packages/web/src/components/chat/MessageBubble.tsx` | Render `CitationsFooter` after assistant message blocks |

---

## Task 1: `GroundingSource` dataclass and updated `LLMResponse`

**Files:**
- Modify: `packages/api/api/agent/llm.py`
- Create: `packages/api/tests/test_llm_grounding.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/api/tests/test_llm_grounding.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/api && python -m pytest tests/test_llm_grounding.py -v 2>&1 | head -30
```
Expected: `ImportError` — `GroundingSource` not defined yet.

- [ ] **Step 3: Add `GroundingSource` to `llm.py` and update `LLMResponse`**

In `packages/api/api/agent/llm.py`, after the existing `LLMPart` dataclass and before `LLMResponse`, add:

```python
@dataclass
class GroundingSource:
    """A single grounded web citation from either Gemini or OpenAI search."""
    index: int
    title: str
    url: str
    date: str | None
```

Update `LLMResponse`:

```python
@dataclass
class LLMResponse:
    """Unified LLM response."""
    parts: list[LLMPart] = field(default_factory=list)
    provider: str = ""  # "gemini" or "openai"
    grounding_sources: list["GroundingSource"] = field(default_factory=list)
```

Update `__all__`:

```python
__all__ = ["call_llm", "call_llm_text", "LLMResponse", "LLMPart", "GroundingSource"]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd packages/api && python -m pytest tests/test_llm_grounding.py -v
```
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/agent/llm.py packages/api/tests/test_llm_grounding.py
git commit -m "feat: add GroundingSource dataclass to LLMResponse"
```

---

## Task 2: Google Search grounding in Gemini calls

**Files:**
- Modify: `packages/api/api/agent/llm.py`
- Modify: `packages/api/tests/test_llm_grounding.py`

- [ ] **Step 1: Write the failing test**

Append to `packages/api/tests/test_llm_grounding.py`:

```python
import asyncio
import pytest
from unittest.mock import MagicMock, patch


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/api && python -m pytest tests/test_llm_grounding.py::test_gemini_extracts_grounding_chunks tests/test_llm_grounding.py::test_gemini_grounding_config_includes_google_search -v 2>&1 | head -30
```
Expected: FAIL — no `GoogleSearch` in config, no `grounding_sources` populated.

- [ ] **Step 3: Update `_call_gemini` in `llm.py`**

Replace the `_call_gemini` function body. The key changes are:
1. Add `genai_types.Tool(google_search=genai_types.GoogleSearch())` to the tools list in config
2. After `generate_content`, extract grounding chunks from `response.candidates[0].grounding_metadata`

```python
async def _call_gemini(history, system_prompt: str, tool_declarations, config_overrides: dict | None = None) -> LLMResponse:
    from google import genai
    from google.genai import types as genai_types
    from api.agent.client import create_gemini_client, MODEL_NAME

    client = create_gemini_client()

    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[tool_declarations, genai_types.Tool(google_search=genai_types.GoogleSearch())],
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
    for part in response.parts:
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd packages/api && python -m pytest tests/test_llm_grounding.py -v
```
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/agent/llm.py packages/api/tests/test_llm_grounding.py
git commit -m "feat: enable Google Search grounding on all Gemini calls, extract citations"
```

---

## Task 3: OpenAI Responses API fallback with web search citations

**Files:**
- Modify: `packages/api/api/agent/llm.py`
- Modify: `packages/api/tests/test_llm_grounding.py`

The existing `_call_openai` uses Chat Completions. Replace it with the Responses API (`client.responses.create`) which supports both custom function tools and `web_search_preview` simultaneously.

- [ ] **Step 1: Write the failing tests**

Append to `packages/api/tests/test_llm_grounding.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/api && python -m pytest tests/test_llm_grounding.py::test_openai_fallback_no_citations tests/test_llm_grounding.py::test_openai_fallback_extracts_url_citations -v 2>&1 | head -30
```
Expected: FAIL — current `_call_openai` uses Chat Completions, has no `grounding_sources`.

- [ ] **Step 3: Add `_gemini_history_to_openai_messages` helper and rewrite `_call_openai`**

In `packages/api/api/agent/llm.py`, add this helper (replaces the system-message part of the existing `_gemini_history_to_openai`):

```python
def _gemini_history_to_openai_messages(history) -> list[dict]:
    """Convert Gemini Content history to OpenAI message list WITHOUT system message.
    Used for the Responses API which takes instructions separately."""
    messages = []
    for content in history:
        role = "assistant" if content.role == "model" else "user"
        for part in content.parts:
            if hasattr(part, "text") and part.text:
                messages.append({"role": role, "content": part.text})
            elif hasattr(part, "function_call") and part.function_call:
                fn = part.function_call
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": f"call_{fn.name}",
                        "type": "function",
                        "function": {
                            "name": fn.name,
                            "arguments": json.dumps(dict(fn.args) if fn.args else {}),
                        }
                    }]
                })
            elif hasattr(part, "function_response") and part.function_response:
                fr = part.function_response
                messages.append({
                    "role": "tool",
                    "tool_call_id": f"call_{fr.name}",
                    "content": json.dumps(fr.response),
                })
    return messages
```

Replace `_call_openai` entirely:

```python
async def _call_openai(history, system_prompt: str, tool_declarations) -> LLMResponse:
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set — cannot fall back to OpenAI")

    client = OpenAI(api_key=api_key)
    messages = _gemini_history_to_openai_messages(history)
    function_tools = _gemini_tool_to_openai(tool_declarations)
    tools = function_tools + [{"type": "web_search_preview"}]

    response = await asyncio.to_thread(
        client.responses.create,
        model="gpt-4o",
        instructions=system_prompt,
        input=messages,
        tools=tools,
        temperature=0.1,
        max_output_tokens=2048,
    )

    parts: list[LLMPart] = []
    grounding_sources: list[GroundingSource] = []
    source_idx = 0

    for item in response.output:
        if item.type == "function_call":
            parts.append(LLMPart(function_call={
                "name": item.name,
                "args": json.loads(item.arguments) if item.arguments else {},
            }))
        elif item.type == "message":
            for content in getattr(item, "content", []):
                if hasattr(content, "text") and content.text:
                    parts.append(LLMPart(text=content.text))
                for ann in getattr(content, "annotations", []):
                    if getattr(ann, "type", None) == "url_citation":
                        source_idx += 1
                        grounding_sources.append(GroundingSource(
                            index=source_idx,
                            title=getattr(ann, "title", None) or ann.url,
                            url=ann.url,
                            date=None,
                        ))

    return LLMResponse(parts=parts, provider="openai", grounding_sources=grounding_sources)
```

- [ ] **Step 4: Run all grounding tests**

```bash
cd packages/api && python -m pytest tests/test_llm_grounding.py -v
```
Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/agent/llm.py packages/api/tests/test_llm_grounding.py
git commit -m "feat: switch OpenAI fallback to Responses API with web_search_preview, extract url_citation sources"
```

---

## Task 4: Router session state (`agent/router_state.py`)

**Files:**
- Create: `packages/api/api/agent/router_state.py`
- Create: `packages/api/tests/test_router_state.py`

- [ ] **Step 1: Write the failing tests**

```python
# packages/api/tests/test_router_state.py
"""Tests for RouterSession in-memory state management."""
import pytest
from api.agent.router_state import (
    RouterSession,
    get_session,
    update_session_portfolio,
    _sessions,
)


def setup_function():
    """Clear session store before each test."""
    _sessions.clear()


def test_get_session_creates_new_for_unknown_conversation():
    session = get_session("conv-abc", messages_data=[])
    assert session.conversation_id == "conv-abc"
    assert session.active_portfolio is None


def test_get_session_returns_cached_session():
    get_session("conv-abc", messages_data=[])
    get_session("conv-abc", messages_data=[])  # second call
    # Only one session should exist
    assert len([k for k in _sessions if k == "conv-abc"]) == 1


def test_update_session_portfolio_sets_portfolio():
    get_session("conv-xyz", messages_data=[])
    portfolio = {"name": "My Book", "tickers": ["NVDA", "AMD"], "weights": [0.6, 0.4]}
    update_session_portfolio("conv-xyz", portfolio)
    session = get_session("conv-xyz", messages_data=[])
    assert session.active_portfolio == portfolio


def test_cold_start_reconstructs_from_optimize_portfolio_result():
    """On first access, reconstruct active_portfolio from stored message history."""
    messages_data = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "name": "optimize_portfolio",
                    "result": {
                        "weights": {"NVDA": 0.5, "AMD": 0.3, "INTC": 0.2},
                        "expected_return": 0.18,
                    },
                }
            ],
        }
    ]
    session = get_session("conv-cold", messages_data=messages_data)
    assert session.active_portfolio is not None
    assert session.active_portfolio["tickers"] == ["NVDA", "AMD", "INTC"]
    assert session.active_portfolio["weights"] == [0.5, 0.3, 0.2]


def test_cold_start_reconstructs_from_load_portfolio_result():
    messages_data = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "name": "load_portfolio",
                    "result": {
                        "name": "TMT Core",
                        "tickers": ["NVDA", "MSFT"],
                        "weights": [0.7, 0.3],
                    },
                }
            ],
        }
    ]
    session = get_session("conv-load", messages_data=messages_data)
    assert session.active_portfolio["name"] == "TMT Core"
    assert session.active_portfolio["tickers"] == ["NVDA", "MSFT"]


def test_cold_start_no_portfolio_tools_leaves_none():
    messages_data = [
        {"role": "user", "content": "What is NVDA trading at?"},
        {"role": "assistant", "content": "NVDA is at $875.", "tool_calls": None},
    ]
    session = get_session("conv-empty", messages_data=messages_data)
    assert session.active_portfolio is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/api && python -m pytest tests/test_router_state.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError` — `router_state` not defined yet.

- [ ] **Step 3: Create `packages/api/api/agent/router_state.py`**

```python
"""Router session state: tracks active portfolio per conversation.

In-memory dict keyed by conversation_id. Reconstructed from DB message history
on cold start (e.g. after server restart).
"""
from dataclasses import dataclass, field


@dataclass
class RouterSession:
    """Per-conversation router state."""
    conversation_id: str
    active_portfolio: dict | None = None
    # active_portfolio shape: {name: str, tickers: list[str], weights: list[float]}


# Module-level store: lives for server process lifetime
_sessions: dict[str, RouterSession] = {}


def get_session(conversation_id: str, messages_data: list[dict]) -> RouterSession:
    """Return existing session or reconstruct from message history on cold start."""
    if conversation_id in _sessions:
        return _sessions[conversation_id]

    session = RouterSession(conversation_id=conversation_id)
    session.active_portfolio = _reconstruct_portfolio(messages_data)
    _sessions[conversation_id] = session
    return session


def update_session_portfolio(conversation_id: str, portfolio: dict) -> None:
    """Update the active portfolio for a conversation."""
    if conversation_id in _sessions:
        _sessions[conversation_id].active_portfolio = portfolio


def _reconstruct_portfolio(messages_data: list[dict]) -> dict | None:
    """Scan message history (newest first) for the most recent portfolio tool result."""
    for msg in reversed(messages_data):
        for tc in (msg.get("tool_calls") or []):
            name = tc.get("name")
            result = tc.get("result") or {}

            if name == "optimize_portfolio" and "weights" in result:
                weights_dict: dict = result["weights"]
                return {
                    "name": None,
                    "tickers": list(weights_dict.keys()),
                    "weights": list(weights_dict.values()),
                }

            if name == "load_portfolio" and "tickers" in result:
                return {
                    "name": result.get("name"),
                    "tickers": result["tickers"],
                    "weights": result.get("weights", []),
                }

    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd packages/api && python -m pytest tests/test_router_state.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/agent/router_state.py packages/api/tests/test_router_state.py
git commit -m "feat: add RouterSession in-memory store with cold-start portfolio reconstruction"
```

---

## Task 5: `format_active_portfolio` in `prompts.py`

**Files:**
- Modify: `packages/api/api/agent/prompts.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/api/tests/test_router_state.py — append to file
from api.agent.prompts import format_active_portfolio


def test_format_active_portfolio_none_returns_empty():
    assert format_active_portfolio(None) == ""


def test_format_active_portfolio_formats_tickers_and_weights():
    portfolio = {
        "name": "TMT Core",
        "tickers": ["NVDA", "AMD", "INTC"],
        "weights": [0.5, 0.3, 0.2],
    }
    result = format_active_portfolio(portfolio)
    assert "NVDA (50.0%)" in result
    assert "AMD (30.0%)" in result
    assert "INTC (20.0%)" in result
    assert "TMT Core" in result


def test_format_active_portfolio_no_name():
    portfolio = {"name": None, "tickers": ["NVDA"], "weights": [1.0]}
    result = format_active_portfolio(portfolio)
    assert "NVDA (100.0%)" in result
    # Should not error on None name
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/api && python -m pytest tests/test_router_state.py::test_format_active_portfolio_none_returns_empty -v 2>&1 | head -10
```
Expected: `ImportError` — `format_active_portfolio` not defined.

- [ ] **Step 3: Add `format_active_portfolio` to `prompts.py`**

At the bottom of `packages/api/api/agent/prompts.py`, after `SYSTEM_PROMPT`, add:

```python


def format_active_portfolio(portfolio: dict | None) -> str:
    """Return a system prompt appendix describing the current working portfolio.

    Returns empty string if no portfolio is active.
    """
    if not portfolio:
        return ""

    tickers = portfolio.get("tickers") or []
    weights = portfolio.get("weights") or []
    name = portfolio.get("name")

    allocations = ", ".join(
        f"{t} ({w * 100:.1f}%)"
        for t, w in zip(tickers, weights)
    )

    name_part = f'"{name}"' if name else "the current portfolio"
    return (
        f"\n\n## Active Working Portfolio\n"
        f"The user is currently working with {name_part}: {allocations}.\n"
        f"When they refer to 'the portfolio', 'that', 'it', or 'those positions', "
        f"they mean this portfolio. Do not ask them to re-specify tickers."
    )
```

- [ ] **Step 4: Run tests**

```bash
cd packages/api && python -m pytest tests/test_router_state.py -v
```
Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/agent/prompts.py packages/api/tests/test_router_state.py
git commit -m "feat: add format_active_portfolio system prompt helper"
```

---

## Task 6: Wire session state and `grounding_sources` into the agent loop

**Files:**
- Modify: `packages/api/api/routes/agent.py`

This task has no new tests (the agent loop is integration-heavy; existing behaviour is unchanged for non-search queries). Manual verification in acceptance criteria.

- [ ] **Step 1: Add imports at the top of `routes/agent.py`**

After the existing imports, add:

```python
from dataclasses import asdict
from api.agent.router_state import get_session, update_session_portfolio
from api.agent.prompts import SYSTEM_PROMPT, format_active_portfolio
```

Remove the existing `from api.agent.prompts import SYSTEM_PROMPT` line (it moves here).

- [ ] **Step 2: Load session and build dynamic system prompt at the start of `generate()`**

Inside `generate()`, after `existing_messages = history_result.data or []` and before persisting the user message, add:

```python
# Load or reconstruct session state for portfolio context
session = get_session(conversation_id, existing_messages)
dynamic_system_prompt = SYSTEM_PROMPT + format_active_portfolio(session.active_portfolio)
```

- [ ] **Step 3: Use `dynamic_system_prompt` in the agent loop**

In the agent loop, replace:

```python
llm_response = await call_llm(gemini_history, SYSTEM_PROMPT, TOOL_DECLARATIONS)
```

with:

```python
llm_response = await call_llm(gemini_history, dynamic_system_prompt, TOOL_DECLARATIONS)
```

- [ ] **Step 4: Accumulate `grounding_sources` across iterations**

Before the `for _ in range(max_iterations):` loop, add:

```python
from api.agent.llm import GroundingSource
all_grounding_sources: list[GroundingSource] = []
seen_urls: set[str] = set()
```

After `llm_response = await call_llm(...)` inside the loop, add:

```python
for src in llm_response.grounding_sources:
    if src.url not in seen_urls:
        seen_urls.add(src.url)
        all_grounding_sources.append(src)
```

- [ ] **Step 5: Update session state after tool execution**

After the `result = await execute_tool(fn_name, args)` line and the `last_tool_result` assignment, add a session update block. Find the section that handles non-persistence tools and add after `last_tool_result = {"name": fn_name, "data": result}`:

```python
# Update session portfolio state
if fn_name == "optimize_portfolio" and isinstance(result, dict) and "weights" in result:
    portfolio = {
        "name": None,
        "tickers": list(result["weights"].keys()),
        "weights": list(result["weights"].values()),
    }
    update_session_portfolio(conversation_id, portfolio)
    dynamic_system_prompt = SYSTEM_PROMPT + format_active_portfolio(portfolio)
```

After `result = await run_load_portfolio(args, sb, user.id)` in the persistence tools block:

```python
if fn_name == "load_portfolio" and isinstance(result, dict) and "tickers" in result:
    portfolio = {
        "name": result.get("name"),
        "tickers": result["tickers"],
        "weights": result.get("weights", []),
    }
    update_session_portfolio(conversation_id, portfolio)
    dynamic_system_prompt = SYSTEM_PROMPT + format_active_portfolio(portfolio)
```

- [ ] **Step 6: Include `grounding_sources` in `done` SSE event**

Replace:

```python
yield _sse("done", {})
```

with:

```python
yield _sse("done", {
    "grounding_sources": [asdict(s) for s in all_grounding_sources],
})
```

- [ ] **Step 7: Include `grounding_sources` in persisted message**

Replace the `sb.table("messages").insert({...}).execute()` block with:

```python
sb.table("messages").insert({
    "conversation_id": conversation_id,
    "role": "assistant",
    "content": accumulated_text or None,
    "tool_calls": accumulated_tool_calls or None,
    "blocks": blocks,
    "grounding_sources": [asdict(s) for s in all_grounding_sources] or None,
    "ordinal": next_ordinal,
}).execute()
```

- [ ] **Step 8: Verify the server starts without errors**

```bash
cd packages/api && python -c "from api.routes.agent import router; print('OK')"
```
Expected: `OK`

- [ ] **Step 9: Commit**

```bash
git add packages/api/api/routes/agent.py
git commit -m "feat: inject portfolio session state into system prompt, accumulate grounding_sources in agent loop"
```

---

## Task 7: Supabase database migration

**Files:**
- Supabase SQL migration

- [ ] **Step 1: Run the migration via Supabase MCP**

Execute this SQL against the project's Supabase instance:

```sql
ALTER TABLE messages ADD COLUMN IF NOT EXISTS grounding_sources jsonb;
```

- [ ] **Step 2: Verify the column exists**

Run:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'messages' AND column_name = 'grounding_sources';
```
Expected: one row returned with `data_type = 'jsonb'`.

- [ ] **Step 3: Commit migration note**

```bash
git commit --allow-empty -m "feat: add grounding_sources jsonb column to messages table (applied via Supabase)"
```

---

## Task 8: TypeScript types

**Files:**
- Modify: `packages/web/src/api/chat-types.ts`

- [ ] **Step 1: Add `GroundingSource` interface and update `ChatMessage` and `SSEDoneEvent`**

In `packages/web/src/api/chat-types.ts`, after the `MessageRole` type definition (line 73), add:

```typescript
// ---------------------------------------------------------------------------
// Search grounding citations
// ---------------------------------------------------------------------------

export interface GroundingSource {
  index: number;
  title: string;
  url: string;
  date: string | null;
}
```

Update `ChatMessage` to include grounding sources:

```typescript
export interface ChatMessage {
  id: string;
  role: MessageRole;
  blocks: MessageBlock[];
  timestamp: number;
  grounding_sources?: GroundingSource[];
}
```

Update `SSEDoneEvent`:

```typescript
export interface SSEDoneEvent {
  event: "done";
  data: { grounding_sources?: GroundingSource[] };
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd packages/web && npx tsc --noEmit 2>&1 | head -20
```
Expected: no errors related to the changed types.

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/api/chat-types.ts
git commit -m "feat: add GroundingSource type, update ChatMessage and SSEDoneEvent"
```

---

## Task 9: Wire `grounding_sources` into `useChat.ts`

**Files:**
- Modify: `packages/web/src/hooks/useChat.ts`

- [ ] **Step 1: Capture `grounding_sources` from the `done` SSE event**

In `useChat.ts`, find the `dispatchEvent` switch and update the `"done"` case:

```typescript
case "done": {
  const sources = (parsed.grounding_sources as GroundingSource[] | undefined) ?? [];
  if (sources.length > 0) {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === assistantId
          ? { ...m, grounding_sources: sources }
          : m
      )
    );
  }
  break;
}
```

Add the import at the top of the file:

```typescript
import type {
  ChatMessage,
  MessageBlock,
  ToolCallBlock,
  GroundingSource,
} from "@/api/chat-types";
```

- [ ] **Step 2: Hydrate `grounding_sources` on `loadConversation`**

In `loadConversation`, update the Supabase select query to include `grounding_sources`:

```typescript
const { data, error: fetchError } = await supabase
  .from("messages")
  .select("id, role, blocks, grounding_sources, created_at")
  .eq("conversation_id", id)
  .order("created_at", { ascending: true });
```

Update the `restored` mapping:

```typescript
const restored: ChatMessage[] = (data ?? []).map((row) => ({
  id: row.id,
  role: row.role as "user" | "assistant",
  blocks: (row.blocks as MessageBlock[]) ?? [],
  grounding_sources: (row.grounding_sources as GroundingSource[]) ?? [],
  timestamp: new Date(row.created_at).getTime(),
}));
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd packages/web && npx tsc --noEmit 2>&1 | head -20
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add packages/web/src/hooks/useChat.ts
git commit -m "feat: capture and hydrate grounding_sources in useChat"
```

---

## Task 10: `CitationsFooter` component

**Files:**
- Create: `packages/web/src/components/chat/CitationsFooter.tsx`

- [ ] **Step 1: Create the component**

```tsx
// packages/web/src/components/chat/CitationsFooter.tsx
import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { GroundingSource } from "@/api/chat-types";

interface CitationsFooterProps {
  sources: GroundingSource[];
}

export default function CitationsFooter({ sources }: CitationsFooterProps) {
  const [open, setOpen] = useState(false);

  if (sources.length === 0) return null;

  return (
    <div className="mt-2 border-t border-border pt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors select-none"
      >
        {open ? (
          <ChevronDown className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
        Sources ({sources.length})
      </button>

      {open && (
        <ol className="mt-2 space-y-1 list-none p-0">
          {sources.map((src) => (
            <li key={src.index} className="flex gap-1.5 text-[11px] text-muted-foreground leading-relaxed">
              <span className="shrink-0">{src.index}.</span>
              <span>
                <a
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 underline hover:text-blue-300"
                >
                  {src.title}
                </a>
                {src.date && (
                  <span className="ml-1.5 text-muted-foreground">· {src.date}</span>
                )}
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd packages/web && npx tsc --noEmit 2>&1 | head -20
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/components/chat/CitationsFooter.tsx
git commit -m "feat: add CitationsFooter component with collapsed Sources toggle"
```

---

## Task 11: Render citation markers and `CitationsFooter` in `MessageBubble.tsx`

**Files:**
- Modify: `packages/web/src/components/chat/MessageBubble.tsx`

The inline superscript markers (`¹ ²`) are rendered as a row after the last text block in the message, immediately before the `CitationsFooter`. This avoids complex mid-sentence text splitting while keeping markers visible.

- [ ] **Step 1: Update `MessageBubble.tsx`**

Replace the entire file content:

```tsx
import type { ChatMessage } from "@/api/chat-types";
import TextBlock from "./TextBlock";
import ChartBlock from "./ChartBlock";
import MetricsBlock from "./MetricsBlock";
import TableBlock from "./TableBlock";
import ToolCallBlock from "./ToolCallBlock";
import StreamingIndicator from "./StreamingIndicator";
import ManifestChartBlock from "./ManifestChartBlock";
import CitationsFooter from "./CitationsFooter";

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

export default function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isEmpty = message.blocks.length === 0;
  const sources = message.grounding_sources ?? [];

  if (isUser) {
    const textBlock = message.blocks.find((b) => b.type === "text");
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-muted rounded-2xl px-4 py-2.5 text-sm">
          {textBlock?.type === "text" ? textBlock.text : ""}
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] w-full space-y-3">
        {isEmpty && isStreaming && <StreamingIndicator />}

        {message.blocks.map((block, i) => {
          switch (block.type) {
            case "text":
              return <TextBlock key={i} text={block.text} />;

            case "chart":
              return (
                <div key={i} className="rounded border border-border overflow-hidden">
                  <ChartBlock block={block} />
                </div>
              );

            case "metrics":
              return <MetricsBlock key={i} block={block} />;

            case "table":
              return <TableBlock key={i} block={block} />;

            case "tool_call":
              return <ToolCallBlock key={i} block={block} />;

            case "manifest_chart":
              return <ManifestChartBlock key={i} manifest={block.manifest} />;

            case "error":
              return (
                <div
                  key={i}
                  className="text-sm text-destructive bg-destructive/10 rounded px-3 py-2"
                >
                  {block.message}
                </div>
              );

            default:
              return null;
          }
        })}

        {!isEmpty && isStreaming && <StreamingIndicator />}

        {/* Inline citation markers + collapsed sources block */}
        {sources.length > 0 && !isStreaming && (
          <div className="text-sm">
            <span className="text-muted-foreground mr-1">
              {sources.map((src) => (
                <sup
                  key={src.index}
                  className="text-blue-400 font-bold text-[15px] leading-none cursor-default mr-0.5"
                  style={{ verticalAlign: "super" }}
                >
                  {src.index}
                </sup>
              ))}
            </span>
            <CitationsFooter sources={sources} />
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd packages/web && npx tsc --noEmit 2>&1 | head -20
```
Expected: no errors.

- [ ] **Step 3: Start the dev server and manually verify**

```bash
cd packages/web && npm run dev
```

Open the chat, send a query like "What did NVIDIA say on their most recent earnings call?" and verify:
- Gemini responds with grounded content
- Blue `¹ ²` superscripts appear after the message text
- "Sources (n)" toggle is collapsed by default
- Clicking it expands the numbered source list with clickable links
- Reloading the conversation preserves citations

- [ ] **Step 4: Commit**

```bash
git add packages/web/src/components/chat/MessageBubble.tsx
git commit -m "feat: render citation superscripts and CitationsFooter in MessageBubble"
```

---

## Self-Review

**Spec coverage check:**
- [x] Google Search grounding via `GoogleSearch()` in GenerateContentConfig → Task 2
- [x] OpenAI web search via Responses API `web_search_preview` → Task 3
- [x] Model decides when to invoke search (ambient, not explicit function call) → Task 2
- [x] Unified `grounding_sources` array in streamed payload → Task 6 (done SSE event)
- [x] Persist `grounding_sources` in Supabase messages table → Tasks 7 + 6
- [x] Rehydrate citations on conversation reload → Task 9
- [x] 15px bold blue superscript markers → Task 11
- [x] Collapsed "Sources (n)" toggle → Task 10
- [x] Multi-step planning / tool chaining → existing loop unchanged, works as-is
- [x] Portfolio session state (`active_portfolio` explicit object) → Tasks 4 + 5
- [x] Inject portfolio context into every prompt turn → Task 6
- [x] Cold-start reconstruction after server restart → Task 4
- [x] Follow-up instructions like "remove TSLA from that" work → Tasks 4 + 5 + 6

**Type consistency check:** `GroundingSource` defined in Task 1 (Python), Task 8 (TypeScript). Referenced in Task 6 (`asdict`), Task 9 (`GroundingSource[]`), Task 10 (`sources: GroundingSource[]`), Task 11 (`grounding_sources ?? []`). All consistent.

**Placeholder scan:** No TBDs or TODOs found.
