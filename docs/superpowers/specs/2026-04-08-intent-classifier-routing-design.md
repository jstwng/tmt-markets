# Intent Classifier & Two-Phase Tool Routing

**Date:** 2026-04-08
**Status:** Approved

---

## Overview

Replace the flat "LLM sees all 33 tools and decides" architecture with a two-phase router: an LLM-based intent classifier determines the query type upfront, then routes to the appropriate execution path — search-only, quant-only, hybrid (search then quant), or conversational (no tools). This fixes three problems: misrouting qualitative queries to `openbb_query`, the Gemini `google_search` + function calling incompatibility, and the lack of fallback when `openbb_query` fails.

---

## Architecture

### Query Flow

```
User message
    │
    ▼
┌─────────────────────────┐
│  Intent Classifier       │  Gemini Flash, ~200ms
│  (classify_intent)       │  Output: search | quant | hybrid | conversational
└────────┬────────────────┘
         │
    ┌────┴────┬──────────┬──────────────┐
    ▼         ▼          ▼              ▼
 search     quant      hybrid      conversational
    │         │          │              │
    ▼         │          ▼              ▼
 Search      │       Search          Plain text
 phase       │       phase           (no tools)
 (google_    │       + inject        via call_llm_text
  search)    │       context
    │         │          │
    ▼         ▼          ▼
 Stream      Agent      Agent
 text +      loop       loop
 citations   (33 tools) (33 tools +
    │         │          search context)
    ▼         ▼          ▼
           done SSE with grounding_sources
```

### What changes

| File | Change |
|------|--------|
| `api/agent/classifier.py` | **New** — `classify_intent()` with constrained Gemini call |
| `api/agent/search.py` | **New** — `run_search_phase()` using Gemini with google_search only |
| `api/agent/llm.py` | Remove `ground_text_with_search` (moved to search.py) |
| `api/routes/agent.py` | Restructure `generate()`: classify → search phase → agent loop. Add openbb_query fallback. Add conversational fast-path |
| `api/agent/prompts.py` | Remove "When NOT to Use Any Tool" section. Add hybrid-mode instruction |
| `api/agent/openbb_codegen.py` | Remove `obb.news.*` ban (search queries no longer reach codegen) |

### What does NOT change

- `tools.py` — all 33 tool declarations unchanged
- `openbb_sandbox.py` — unchanged
- `router_state.py` — unchanged
- `client.py` — unchanged
- Frontend — no changes (existing SSE events, CitationsFooter, useChat all work as-is)
- Supabase schema — no changes
- The 8-iteration tool loop structure — unchanged
- OpenAI LLM fallback trigger (503/rate-limit) — unchanged
- SSE event types (text, tool_call, tool_result, error, done) — unchanged
- Session state / portfolio tracking — unchanged

---

## Section 1: Intent Classifier (`api/agent/classifier.py`)

### Function signature

```python
@dataclass
class IntentResult:
    intent: str  # "search" | "quant" | "hybrid" | "conversational"

async def classify_intent(
    message: str,
    conversation_context: str | None = None,
) -> IntentResult:
```

### Implementation

- Calls `call_llm_text` (Gemini Flash, temperature=0, max_tokens=64)
- Input: user message + optional conversation context (last 2-3 messages summarized, so "backtest that" resolves correctly)
- Output: JSON `{"intent": "<category>"}`
- Parses JSON; falls back to `"hybrid"` if parsing fails (safest default — runs both phases)

### Classifier system prompt

```
Classify the user's financial research query into exactly one category.

Categories:
- "search": needs real-time or recent information from the web — earnings call summaries, analyst commentary, recent news, management guidance, event reactions, "what did X say"
- "quant": needs computation with financial tools — portfolio optimization, backtesting, covariance/correlation, risk metrics, price data fetching, efficient frontier, stress testing, factor analysis, charts
- "hybrid": needs BOTH web search context AND quantitative computation — e.g., "how did the market react to the last CPI print" (needs search for what happened + price data for the move)
- "conversational": answerable from general knowledge without tools or search — explanations of concepts, follow-up clarifications, opinions, strategy discussion

Rules:
- If the query references recent events, specific dates, or "latest"/"last"/"recent" + a company event → search or hybrid
- If the query asks for numbers, optimization, backtesting, risk analysis, or uses tickers with an analytical verb → quant
- If uncertain between search and hybrid, choose hybrid
- If uncertain between conversational and quant, choose quant

Output ONLY valid JSON: {"intent": "<category>"}
```

### Conversation context

To handle follow-ups like "backtest that" or "what about NVDA", the classifier receives a one-line summary of the recent conversation state:

```python
# Built from session state and last assistant message
context = f"Active portfolio: {session.active_portfolio}. Last action: {last_tool_name or 'text response'}."
```

This is injected as a second line after the user message in the classifier prompt. Not a separate system prompt — just appended context.

### What each intent triggers

| Intent | Search Phase | Agent Loop | Tools visible to LLM |
|--------|-------------|------------|---------------------|
| `search` | Yes | No | None (google_search only) |
| `quant` | No | Yes | All 33 function tools |
| `hybrid` | Yes, then inject context | Yes | All 33 function tools |
| `conversational` | No | No | None (plain text call) |

---

## Section 2: Search Phase (`api/agent/search.py`)

### Function signature

```python
@dataclass
class SearchResult:
    text: str                          # Gemini's grounded response text
    sources: list[GroundingSource]     # extracted citations

async def run_search_phase(user_message: str) -> SearchResult:
```

### Implementation

- Calls Gemini with ONLY `google_search` tool (no function declarations)
- Uses a minimal system prompt: the PM persona + "Answer the user's question using web search. Be concise and cite your sources."
- Returns both the generated text AND the grounding sources
- This replaces `ground_text_with_search` in `llm.py` (which only returned sources, not text)

### Gemini config for search phase

```python
config = genai_types.GenerateContentConfig(
    system_instruction=search_system_prompt,
    tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
    temperature=0.1,
    max_output_tokens=2048,
)
```

### How search integrates with each intent

**For `search` intent:**
- Stream `SearchResult.text` to the user via `text` SSE events as the final response
- Attach `SearchResult.sources` to the `done` SSE event as `grounding_sources`
- Persist to Supabase with grounding_sources
- No agent loop runs

**For `hybrid` intent:**
- Stream search text to the user immediately (satisfies "stream something quick")
- Inject search result into Gemini conversation history before the agent loop:
  ```python
  # After user message in history, add search context
  gemini_history.append(Content(role="model", parts=[
      Part(text=f"[Research context from web search]\n{search_result.text}")
  ]))
  gemini_history.append(Content(role="user", parts=[
      Part(text="Now use the available quantitative tools to add data-driven analysis.")
  ]))
  ```
- Agent loop runs with all function tools — it has search context in history
- `SearchResult.sources` merged into `all_grounding_sources` (deduplicated by URL)

---

## Section 3: Agent Loop Changes (`api/routes/agent.py`)

### Restructured generate() flow

```python
async def generate():
    # ... existing setup: resolve conversation, load history, build gemini_history ...

    # Phase 0: Classify intent
    context = _build_classifier_context(session, accumulated_tool_calls)
    intent_result = await classify_intent(req.message, context)

    all_grounding_sources: list[GroundingSource] = []
    seen_urls: set[str] = set()

    # Phase 1: Search (if search or hybrid)
    search_text = ""
    if intent_result.intent in ("search", "hybrid"):
        search_result = await run_search_phase(req.message)
        search_text = search_result.text
        for src in search_result.sources:
            if src.url not in seen_urls:
                seen_urls.add(src.url)
                all_grounding_sources.append(src)
        # Stream search text immediately
        yield _sse("text", {"text": search_text})

    # Phase 2: Route based on intent
    if intent_result.intent == "search":
        # Search-only: search text is the final answer
        accumulated_text = search_text

    elif intent_result.intent == "conversational":
        # No tools — plain text generation
        response_text = await call_llm_text(
            dynamic_system_prompt, req.message,
            temperature=0.1, max_tokens=2048,
        )
        yield _sse("text", {"text": response_text})
        accumulated_text = response_text

    elif intent_result.intent in ("quant", "hybrid"):
        if intent_result.intent == "hybrid":
            # Inject search context into history
            gemini_history.append(Content(role="model", parts=[
                Part(text=f"[Research context from web search]\n{search_text}")
            ]))
            gemini_history.append(Content(role="user", parts=[
                Part(text="Now use the available quantitative tools to provide data-driven analysis.")
            ]))
            accumulated_text = search_text  # already streamed

        # ... existing agent loop (unchanged internally) ...

    # ... existing finalize: persist, done SSE ...
```

### Conversational fast-path

When intent is `conversational`:
- Call `call_llm_text(dynamic_system_prompt, req.message)` directly
- No tool declarations passed — model just answers
- This fixes the "I cannot provide a summary of NVIDIA's earnings call" refusal — without tools in context, the model answers from knowledge
- Faster response since Gemini doesn't evaluate 33 tool schemas

### Fallback chain for openbb_query failure

Current behavior: openbb_query retries 4 times, then surfaces a red error block.

New behavior — after 4 failed openbb_query attempts:
1. Before erroring out, run `run_search_phase(description)` using the openbb_query description as the search query
2. If search returns results, stream them as a text response with a prefix: the model incorporates the search results instead of showing an error
3. If search also fails, then surface the original error

```python
# In the openbb_query handler, after retry loop exhaustion:
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
        # Inject as tool result so the loop can continue
        result = {"fallback_search": fallback.text}
    else:
        raise RuntimeError(f"OpenBB query failed after 4 attempts: {last_error}")
```

---

## Section 4: System Prompt Changes (`api/agent/prompts.py`)

### Remove

The "When NOT to Use Any Tool" section (lines 156-161 currently):
```
## When NOT to Use Any Tool
- Qualitative questions — ...
- Never mention tool names ...
```

This is no longer needed — the classifier handles routing. Qualitative queries never reach the agent loop.

### Add

A short general rule to the existing "Response Format" section:
```
- Never mention internal tool names (openbb_query, fetch_prices, etc.) in responses.
```

A new hybrid-mode instruction added to the end of the prompt:
```
## When Research Context Is Provided
If your conversation history contains a "[Research context from web search]" block, 
reference it in your analysis. Do not repeat the search — use the quantitative tools 
to add data to the research context already provided.
```

### Keep unchanged

- Persona, macro framework, sub-sector intelligence
- Tool Usage Rules (fetch_prices first, etc.)
- Price Data Routing
- OpenBB Query Tool description (still needed for quant intent)
- Response Format, After-Results chains
- Portfolio & Output Persistence

---

## Section 5: Codegen Cleanup (`api/agent/openbb_codegen.py`)

### Remove

The `obb.news.*` ban from the codegen system prompt:
```
Do NOT use these — they do not exist or do not work:
- obb.news.* (any path under obb.news)
- Any call for news articles, transcripts, summaries, or qualitative text
- Any call with provider="fmp" for news or text content
```

This is no longer needed — search/qualitative queries are classified before they reach the agent loop, so `openbb_query` will never receive a news/transcript request.

---

## Section 6: LLM Module Cleanup (`api/agent/llm.py`)

### Remove

`ground_text_with_search()` function — its functionality is superseded by `run_search_phase()` in the new `search.py` module. Remove from `__all__` as well.

The unused import of `ground_text_with_search` in `routes/agent.py` was already removed in a previous commit.

---

## Acceptance Criteria

1. **"What did NVDA say on their last earnings call?"** — classified as `search`, answered with grounded web search text + citations in Sources footer. No openbb_query call. No tool names in response.
2. **"Optimize a portfolio of NVDA, AMD, AVGO"** — classified as `quant`, runs agent loop with fetch_prices → optimize_portfolio. No search phase. No citations.
3. **"How did the market react to the last CPI print?"** — classified as `hybrid`, streams search context immediately, then fetches price data around the CPI date and shows the move.
4. **"What's the difference between Sharpe and Sortino ratio?"** — classified as `conversational`, answered directly from model knowledge with no tools and no search. Fast response.
5. **"Backtest that"** (after an optimization) — classified as `quant` (conversation context tells the classifier there's an active portfolio). Runs backtest with session portfolio.
6. **openbb_query fails 4 times for a valid structured data request** — fallback to web search, user gets an answer instead of a red error block.
7. **Classifier fails to parse JSON** — defaults to `hybrid` (safest), both phases run.
8. **Latency:** classifier adds ~200ms. Search phase adds ~1-2s when invoked. Conversational queries are faster than today (no tool schema evaluation).
