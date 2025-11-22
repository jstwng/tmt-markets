# Intent Classifier & Two-Phase Tool Routing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace flat tool routing with an LLM-based intent classifier that routes queries to the correct execution path — search, quant, hybrid, or conversational — fixing misrouting, refusal, and missing fallback problems.

**Architecture:** A cheap Gemini Flash classifier call determines intent upfront. Search-intent queries run a separate Gemini call with only `google_search`. Quant-intent queries run the existing agent loop. Hybrid queries chain both. Conversational queries skip tools entirely. An openbb_query fallback chain catches structured-data failures by retrying as web search.

**Tech Stack:** Python 3.12, FastAPI, google-genai SDK, OpenAI SDK, pytest, SSE streaming

---

## File Structure

| File | Responsibility | Status |
|------|---------------|--------|
| `packages/api/api/agent/classifier.py` | Intent classification — `classify_intent()` | **Create** |
| `packages/api/api/agent/search.py` | Search phase — `run_search_phase()` | **Create** |
| `packages/api/api/agent/llm.py` | Remove `ground_text_with_search`, clean `__all__` | Modify |
| `packages/api/api/routes/agent.py` | Restructure `generate()` with classifier + search + fallback | Modify |
| `packages/api/api/agent/prompts.py` | Remove "When NOT to Use Any Tool", add hybrid instruction | Modify |
| `packages/api/api/agent/openbb_codegen.py` | Remove `obb.news.*` ban | Modify |
| `packages/api/tests/test_classifier.py` | Tests for classifier | **Create** |
| `packages/api/tests/test_search_phase.py` | Tests for search phase | **Create** |
| `packages/api/tests/test_llm_grounding.py` | Remove stale `google_search` config test | Modify |

---

### Task 1: Intent Classifier Module

**Files:**
- Create: `packages/api/tests/test_classifier.py`
- Create: `packages/api/api/agent/classifier.py`

- [ ] **Step 1: Write failing tests for classifier**

```python
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
    # Verify context was passed to LLM
    call_args = mock_llm.call_args
    user_message = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("user_message", "")
    assert "Active portfolio" in user_message


@pytest.mark.asyncio
@patch("api.agent.classifier.call_llm_text", new_callable=AsyncMock)
async def test_classify_llm_exception_defaults_hybrid(mock_llm):
    mock_llm.side_effect = Exception("LLM unavailable")
    result = await classify_intent("anything")
    assert result.intent == "hybrid"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/api && python -m pytest tests/test_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.agent.classifier'`

- [ ] **Step 3: Implement the classifier**

```python
"""Intent classifier for routing queries to the correct execution path."""

import json
import logging
from dataclasses import dataclass

from api.agent.llm import call_llm_text

logger = logging.getLogger(__name__)

__all__ = ["classify_intent", "IntentResult"]

_VALID_INTENTS = {"search", "quant", "hybrid", "conversational"}

CLASSIFIER_SYSTEM_PROMPT = """\
Classify the user's financial research query into exactly one category.

Categories:
- "search": needs real-time or recent information from the web — earnings call summaries, \
analyst commentary, recent news, management guidance, event reactions, "what did X say"
- "quant": needs computation with financial tools — portfolio optimization, backtesting, \
covariance/correlation, risk metrics, price data fetching, efficient frontier, stress \
testing, factor analysis, charts
- "hybrid": needs BOTH web search context AND quantitative computation — e.g., "how did \
the market react to the last CPI print" (needs search for what happened + price data \
for the move)
- "conversational": answerable from general knowledge without tools or search — \
explanations of concepts, follow-up clarifications, opinions, strategy discussion

Rules:
- If the query references recent events, specific dates, or "latest"/"last"/"recent" \
+ a company event → search or hybrid
- If the query asks for numbers, optimization, backtesting, risk analysis, or uses \
tickers with an analytical verb → quant
- If uncertain between search and hybrid, choose hybrid
- If uncertain between conversational and quant, choose quant

Output ONLY valid JSON: {"intent": "<category>"}
"""


@dataclass
class IntentResult:
    intent: str  # "search" | "quant" | "hybrid" | "conversational"


async def classify_intent(
    message: str,
    conversation_context: str | None = None,
) -> IntentResult:
    """Classify user message intent for routing.

    Args:
        message: The user's message.
        conversation_context: Optional one-line summary of recent conversation state.

    Returns:
        IntentResult with one of: search, quant, hybrid, conversational.
        Defaults to hybrid on any failure (safest — runs both phases).
    """
    user_input = message
    if conversation_context:
        user_input = f"{message}\n\nConversation context: {conversation_context}"

    try:
        raw = await call_llm_text(
            CLASSIFIER_SYSTEM_PROMPT,
            user_input,
            temperature=0.0,
            max_tokens=64,
        )
        parsed = json.loads(raw.strip())
        intent = parsed.get("intent", "hybrid")
        if intent not in _VALID_INTENTS:
            logger.warning("Classifier returned unknown intent %r, defaulting to hybrid", intent)
            intent = "hybrid"
        return IntentResult(intent=intent)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Classifier JSON parse failed (%s), defaulting to hybrid", e)
        return IntentResult(intent="hybrid")
    except Exception as e:
        logger.warning("Classifier call failed (%s), defaulting to hybrid", e)
        return IntentResult(intent="hybrid")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/api && python -m pytest tests/test_classifier.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/agent/classifier.py packages/api/tests/test_classifier.py
git commit -m "feat: add intent classifier for query routing"
```

---

### Task 2: Search Phase Module

**Files:**
- Create: `packages/api/tests/test_search_phase.py`
- Create: `packages/api/api/agent/search.py`

- [ ] **Step 1: Write failing tests for search phase**

```python
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
async def test_search_phase_exception_returns_empty(mock_factory):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API error")
    mock_factory.return_value = mock_client

    result = await run_search_phase("query")

    assert result.text == ""
    assert result.sources == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/api && python -m pytest tests/test_search_phase.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.agent.search'`

- [ ] **Step 3: Implement the search phase**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/api && python -m pytest tests/test_search_phase.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/agent/search.py packages/api/tests/test_search_phase.py
git commit -m "feat: add search phase module with google_search grounding"
```

---

### Task 3: Clean Up LLM Module

**Files:**
- Modify: `packages/api/api/agent/llm.py:20` (`__all__`), lines 110-157 (`ground_text_with_search`)
- Modify: `packages/api/tests/test_llm_grounding.py:86-105` (stale test)

- [ ] **Step 1: Remove `ground_text_with_search` from `llm.py`**

In `packages/api/api/agent/llm.py`, make two edits:

Edit 1 — line 20, update `__all__`:
```python
# OLD:
__all__ = ["call_llm", "call_llm_text", "ground_text_with_search", "LLMResponse", "LLMPart", "GroundingSource"]

# NEW:
__all__ = ["call_llm", "call_llm_text", "LLMResponse", "LLMPart", "GroundingSource"]
```

Edit 2 — delete lines 110-157 (the entire `ground_text_with_search` function and its blank line above the OpenAI section header).

- [ ] **Step 2: Remove stale test from `test_llm_grounding.py`**

Delete `test_gemini_grounding_config_includes_google_search` (lines 83-105 in `packages/api/tests/test_llm_grounding.py`). This test asserts that `_call_gemini` includes a `GoogleSearch` tool in its config — that is no longer true (google_search is now in the separate search phase, not in the function-calling path).

- [ ] **Step 3: Run remaining LLM tests to verify nothing broke**

Run: `cd packages/api && python -m pytest tests/test_llm_grounding.py -v`
Expected: All remaining tests PASS (the deleted test no longer runs)

- [ ] **Step 4: Commit**

```bash
git add packages/api/api/agent/llm.py packages/api/tests/test_llm_grounding.py
git commit -m "refactor: remove ground_text_with_search, superseded by search.py"
```

---

### Task 4: Update System Prompt

**Files:**
- Modify: `packages/api/api/agent/prompts.py:156-163` (remove section), add hybrid instruction

- [ ] **Step 1: Remove "When NOT to Use Any Tool" section**

In `packages/api/api/agent/prompts.py`, delete lines 156-163:
```python
# DELETE this entire section:
## When NOT to Use Any Tool
- Qualitative questions — "what did X say on their earnings call?", "summarize the news \
on Y", "what is management's guidance?" — do NOT call any tool. Answer directly from \
your training knowledge. You have extensive knowledge of earnings calls, analyst days, \
and corporate guidance through your training cutoff — use it. Only flag a knowledge \
cutoff if the question is clearly about very recent events you cannot know.
- Never mention tool names (openbb_query, fetch_prices, etc.) in your responses. \
Users don't know or care about the internal tooling.
```

- [ ] **Step 2: Add tool-name rule to Response Format section**

In the `## Response Format` section (line 165 after the deletion), add as the first bullet:

```python
- Never mention internal tool names (openbb_query, fetch_prices, etc.) in responses.\n\
```

So the Response Format section starts with:
```
## Response Format
- Never mention internal tool names (openbb_query, fetch_prices, etc.) in responses.
- After tool results, provide a concise interpretation (2-4 sentences). Quote specific numbers.
```

- [ ] **Step 3: Add hybrid-mode instruction after the Portfolio & Output Persistence section**

Append to the end of `SYSTEM_PROMPT` (before the closing `"""`):

```python
\n\n## When Research Context Is Provided\n\
If your conversation history contains a "[Research context from web search]" block, \
reference it in your analysis. Do not repeat the search — use the quantitative tools \
to add data to the research context already provided.
```

- [ ] **Step 4: Verify the prompt is syntactically valid**

Run: `cd packages/api && python -c "from api.agent.prompts import SYSTEM_PROMPT; print(len(SYSTEM_PROMPT))"`
Expected: prints a number (no import or syntax error)

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/agent/prompts.py
git commit -m "refactor: simplify system prompt, add hybrid-mode research context instruction"
```

---

### Task 5: Clean Up OpenBB Codegen Prompt

**Files:**
- Modify: `packages/api/api/agent/openbb_codegen.py:35-38`

- [ ] **Step 1: Remove the `obb.news.*` ban**

In `packages/api/api/agent/openbb_codegen.py`, delete lines 35-38:
```python
# DELETE:
Do NOT use these — they do not exist or do not work:
- obb.news.* (any path under obb.news)
- Any call for news articles, transcripts, summaries, or qualitative text
- Any call with provider="fmp" for news or text content
```

The codegen prompt should end with the examples and then:
```
Return ONLY the expression. No explanation, no markdown, no function definition.
```

- [ ] **Step 2: Verify codegen prompt is valid**

Run: `cd packages/api && python -c "from api.agent.openbb_codegen import CODEGEN_SYSTEM_PROMPT; print('OK')"`
Expected: prints `OK`

- [ ] **Step 3: Commit**

```bash
git add packages/api/api/agent/openbb_codegen.py
git commit -m "refactor: remove obb.news ban from codegen prompt, classifier handles routing"
```

---

### Task 6: Restructure Agent Loop with Classifier + Search + Fallback

**Files:**
- Modify: `packages/api/api/routes/agent.py`

This is the largest task. The `generate()` function in `agent.py` needs to be restructured to:
1. Classify intent before entering the loop
2. Run search phase for search/hybrid intents
3. Run conversational fast-path for conversational intent
4. Run existing agent loop for quant/hybrid intents
5. Add openbb_query fallback to web search

- [ ] **Step 1: Add new imports at the top of `agent.py`**

In `packages/api/api/routes/agent.py`, replace the existing imports (lines 13-14):

```python
# OLD:
from api.agent.llm import call_llm, GroundingSource

# NEW:
from api.agent.llm import call_llm, call_llm_text, GroundingSource
from api.agent.classifier import classify_intent
from api.agent.search import run_search_phase
```

- [ ] **Step 2: Add `_build_classifier_context` helper**

Add after the `_rebuild_gemini_history` function (after line 89):

```python
def _build_classifier_context(session, last_tool_name: str | None) -> str | None:
    """Build one-line conversation context for the intent classifier."""
    parts = []
    if session.active_portfolio:
        tickers = session.active_portfolio.get("tickers", [])
        parts.append(f"Active portfolio: {', '.join(tickers)}")
    if last_tool_name:
        parts.append(f"Last action: {last_tool_name}")
    return ". ".join(parts) + "." if parts else None
```

- [ ] **Step 3: Restructure `generate()` — classify and route**

Replace the agent loop section of `generate()`. The existing code from the `# ------ Agent loop ------` comment (line 162) through the end of the loop (line 303, where `if not has_function_call: break`) gets restructured.

Replace lines 162-303 with the following. Everything before (setup, conversation resolution, history loading, user message persistence) and after (finalize/persist) stays the same.

```python
            # ------ Classify intent ------
            last_tool = accumulated_tool_calls[-1]["name"] if accumulated_tool_calls else None
            classifier_context = _build_classifier_context(session, last_tool)
            intent_result = await classify_intent(req.message, classifier_context)
            logger.info("Intent classified as: %s", intent_result.intent)

            # ------ Phase 1: Search (if search or hybrid) ------
            search_text = ""
            if intent_result.intent in ("search", "hybrid"):
                search_result = await run_search_phase(req.message)
                search_text = search_result.text
                for src in search_result.sources:
                    if src.url not in seen_urls:
                        seen_urls.add(src.url)
                        all_grounding_sources.append(src)
                if search_text:
                    yield _sse("text", {"text": search_text})
                    accumulated_text += search_text

            # ------ Phase 2: Route by intent ------
            if intent_result.intent == "search":
                # Search-only: search text is the final answer, no agent loop
                pass

            elif intent_result.intent == "conversational":
                # No tools — plain text generation
                response_text = await call_llm_text(
                    dynamic_system_prompt, req.message,
                    temperature=0.1, max_tokens=2048,
                )
                yield _sse("text", {"text": response_text})
                accumulated_text += response_text

            else:
                # quant or hybrid — run the agent loop
                if intent_result.intent == "hybrid" and search_text:
                    # Inject search context into history for the agent loop
                    gemini_history.append(
                        genai_types.Content(role="model", parts=[
                            genai_types.Part(text=f"[Research context from web search]\n{search_text}")
                        ])
                    )
                    gemini_history.append(
                        genai_types.Content(role="user", parts=[
                            genai_types.Part(text="Now use the available quantitative tools to provide data-driven analysis.")
                        ])
                    )

                max_iterations = 8
                for _ in range(max_iterations):
                    llm_response = await call_llm(gemini_history, dynamic_system_prompt, TOOL_DECLARATIONS)

                    for src in llm_response.grounding_sources:
                        if src.url not in seen_urls:
                            seen_urls.add(src.url)
                            all_grounding_sources.append(src)

                    has_function_call = False
                    tool_results_parts: list[genai_types.Part] = []
                    model_parts: list[genai_types.Part] = []

                    for part in llm_response.parts:
                        if part.text:
                            accumulated_text += part.text
                            yield _sse("text", {"text": part.text})
                            model_parts.append(genai_types.Part(text=part.text))

                        if part.function_call:
                            has_function_call = True
                            fn_name = part.function_call["name"]
                            args = part.function_call["args"]

                            model_parts.append(genai_types.Part(
                                function_call=genai_types.FunctionCall(name=fn_name, args=args)
                            ))

                            yield _sse("tool_call", {"name": fn_name, "args": args})

                            try:
                                if fn_name == "openbb_query":
                                    description = args.get("description") or args.get("query", "")
                                    obb_client = get_obb_client()
                                    expression = None
                                    data = None
                                    last_error: str | None = None

                                    for attempt in range(1, 5):  # 4 attempts
                                        expression = await generate_openbb_code(description, error_context=last_error)
                                        wrapped = f"def fetch():\n    result = {expression}\n    return _normalize(result)\n"
                                        valid, reason = validate_code(wrapped)
                                        if not valid:
                                            last_error = f"Code validation failed: {reason}\nExpression attempted: {expression}"
                                            yield _sse("codegen_retry", {"attempt": attempt, "error": last_error})
                                            continue
                                        try:
                                            data = await execute_openbb_code(expression, obb_client)
                                            break
                                        except Exception as exec_err:
                                            last_error = (
                                                f"Expression attempted: {expression}\n"
                                                f"Error: {type(exec_err).__name__}: {exec_err}\n"
                                                f"Hint: {_classify_error(exec_err)}"
                                            )
                                            yield _sse("codegen_retry", {"attempt": attempt, "error": str(exec_err)})

                                    if data is None:
                                        # Fallback: try web search before erroring
                                        fallback = await run_search_phase(description)
                                        if fallback.text:
                                            yield _sse("text", {"text": fallback.text})
                                            accumulated_text += fallback.text
                                            for src in fallback.sources:
                                                if src.url not in seen_urls:
                                                    seen_urls.add(src.url)
                                                    all_grounding_sources.append(src)
                                            result = {"fallback_search": fallback.text}
                                        else:
                                            raise RuntimeError(f"OpenBB query failed after 4 attempts: {last_error}")

                                    else:
                                        manifest = await generate_chart_manifest(description, data, expression)
                                        result = {"result": data, "chart_manifest": manifest}

                                    last_tool_result = {"name": fn_name, "data": result}
                                elif fn_name in PERSISTENCE_TOOLS:
                                    if fn_name == "load_portfolio":
                                        result = await run_load_portfolio(args, sb, user.id)
                                        if fn_name == "load_portfolio" and isinstance(result, dict) and "tickers" in result:
                                            portfolio = {
                                                "name": result.get("name"),
                                                "tickers": result["tickers"],
                                                "weights": result.get("weights", []),
                                            }
                                            update_session_portfolio(conversation_id, portfolio)
                                            dynamic_system_prompt = SYSTEM_PROMPT + format_active_portfolio(portfolio)
                                    elif fn_name == "save_portfolio":
                                        result = await run_save_portfolio(args, sb, user.id)
                                    else:  # save_output
                                        result = await run_save_output(args, sb, user.id, conversation_id, last_tool_result)
                                else:
                                    result = await execute_tool(fn_name, args)
                                    last_tool_result = {"name": fn_name, "data": result}
                                    if fn_name == "optimize_portfolio" and isinstance(result, dict) and "weights" in result:
                                        portfolio = {
                                            "name": None,
                                            "tickers": list(result["weights"].keys()),
                                            "weights": list(result["weights"].values()),
                                        }
                                        update_session_portfolio(conversation_id, portfolio)
                                        dynamic_system_prompt = SYSTEM_PROMPT + format_active_portfolio(portfolio)
                                yield _sse("tool_result", {"name": fn_name, "result": result})

                                accumulated_tool_calls.append({
                                    "name": fn_name,
                                    "args": args,
                                    "result": result,
                                })

                                tool_results_parts.append(
                                    genai_types.Part(
                                        function_response=genai_types.FunctionResponse(
                                            name=fn_name,
                                            response={"result": result},
                                        )
                                    )
                                )
                            except Exception as e:
                                error_msg = str(e)
                                yield _sse("error", {"message": f"Tool '{fn_name}' failed: {error_msg}"})
                                accumulated_tool_calls.append({
                                    "name": fn_name,
                                    "args": args,
                                    "error": error_msg,
                                })
                                tool_results_parts.append(
                                    genai_types.Part(
                                        function_response=genai_types.FunctionResponse(
                                            name=fn_name,
                                            response={"error": error_msg},
                                        )
                                    )
                                )

                    if model_parts:
                        gemini_history.append(
                            genai_types.Content(role="model", parts=model_parts)
                        )

                    if not has_function_call:
                        break

                    gemini_history.append(
                        genai_types.Content(role="user", parts=tool_results_parts)
                    )
```

- [ ] **Step 4: Add logging import**

At the top of `agent.py`, add after the existing imports:

```python
import logging

logger = logging.getLogger(__name__)
```

- [ ] **Step 5: Verify the server starts without import errors**

Run: `cd packages/api && python -c "from api.routes.agent import router; print('OK')"`
Expected: prints `OK`

- [ ] **Step 6: Commit**

```bash
git add packages/api/api/routes/agent.py
git commit -m "feat: restructure agent loop with classifier routing, search phase, fallback chains"
```

---

### Task 7: Integration Smoke Test

**Files:** None (manual verification)

- [ ] **Step 1: Run full test suite**

Run: `cd packages/api && python -m pytest tests/ -v --tb=short`
Expected: All tests pass (classifier tests, search phase tests, existing tests)

- [ ] **Step 2: Verify no import cycles**

Run: `cd packages/api && python -c "from api.routes.agent import router; from api.agent.classifier import classify_intent; from api.agent.search import run_search_phase; print('All imports OK')"`
Expected: prints `All imports OK`

- [ ] **Step 3: Commit if any fixes were needed**

```bash
# Only if fixes were applied:
git add -A
git commit -m "fix: resolve integration issues from routing restructure"
```
