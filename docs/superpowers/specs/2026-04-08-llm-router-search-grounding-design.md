# LLM Router: Search Grounding, Session State & Citation Rendering

**Date:** 2026-04-08
**Status:** Approved

---

## Overview

Enhance the existing agentic loop to function as a named "LLM router": a central orchestration layer that receives user input, decides whether to invoke search or quantitative tools, chains multiple tool calls sequentially, maintains explicit portfolio session state across turns, and renders grounded citations in the UI.

The existing `routes/agent.py` + `agent/llm.py` is the router. No new orchestration layer is added. The changes are additive enhancements to those files plus a new session state module and frontend citation component.

---

## Architecture

### What changes

| File | Change |
|------|--------|
| `api/agent/llm.py` | Add Google Search grounding to every Gemini call; extract `grounding_metadata`; return `grounding_sources` in `LLMResponse`; switch OpenAI fallback from Chat Completions to Responses API with `web_search_preview`; extract citations from OpenAI `annotations` |
| `api/agent/router_state.py` | New module — `RouterSession` dataclass + in-memory store + cold-start reconstruction |
| `api/routes/agent.py` | Inject `active_portfolio` into system prompt each turn; update session state after tool execution; attach `grounding_sources` to `done` SSE event and persisted message |
| `api/agent/prompts.py` | Add `format_active_portfolio()` helper that appends portfolio context block to system prompt |
| Supabase migration | Add `grounding_sources jsonb` column to `messages` table |
| `web/src/api/chat-types.ts` | Add `grounding_sources` field to message shape; add `GroundingSource` type |
| `web/src/hooks/useChat.ts` | Persist `grounding_sources` from `done` SSE event; hydrate from stored messages on reload |
| `web/src/components/chat/MessageBubble.tsx` | Render inline superscript citation markers + collapsed Sources footnote block |

---

## Section 1: LLM Layer (`agent/llm.py`)

### Google Search grounding

Enable on every Gemini `generate_content` call by adding `GoogleSearch` to the tools list alongside the existing function declarations:

```python
from google.genai import types as genai_types

config = genai_types.GenerateContentConfig(
    system_instruction=system_prompt,
    tools=[tool_declarations, genai_types.Tool(google_search=genai_types.GoogleSearch())],
    temperature=0.1,
    max_output_tokens=2048,
)
```

Gemini decides autonomously when to invoke search. No explicit function call or routing classifier is needed. After generation, extract citations from:

```python
grounding_chunks = response.candidates[0].grounding_metadata.grounding_chunks or []
```

Each chunk has `.web.uri` and `.web.title`. Map to `GroundingSource` with index, title, url, date (from `grounding_metadata.search_entry_point` or None if unavailable).

### OpenAI web search fallback

When the Gemini retriable-error path triggers, switch from `client.chat.completions.create` to the Responses API:

```python
from openai import OpenAI
response = client.responses.create(
    model="gpt-4o",
    tools=[{"type": "web_search_preview"}],
    input=messages,  # converted from Gemini history format
)
```

Extract citations from output annotations:
```python
for item in response.output:
    for content in getattr(item, "content", []):
        for annotation in getattr(content, "annotations", []):
            if annotation.type == "url_citation":
                # annotation.url, annotation.title, annotation.start_index
```

### Unified `GroundingSource` dataclass

```python
@dataclass
class GroundingSource:
    index: int
    title: str
    url: str
    date: str | None  # ISO date string or None
```

Add `grounding_sources: list[GroundingSource]` field to `LLMResponse`. Empty list when no search was invoked.

---

## Section 2: Session State (`agent/router_state.py`)

### `RouterSession` dataclass

```python
@dataclass
class RouterSession:
    conversation_id: str
    active_portfolio: dict | None = None
    # active_portfolio shape: {name: str, tickers: list[str], weights: list[float]}
```

### In-memory store

Module-level dict: `_sessions: dict[str, RouterSession]`. Keyed by `conversation_id`. Lives for the lifetime of the server process.

### Cold-start reconstruction

On first request for a `conversation_id` (store miss), scan the last 50 stored messages for the most recent tool result from `optimize_portfolio` or `load_portfolio`. Parse `active_portfolio` from that result. This ensures a server restart doesn't lose session context for active conversations.

### API

```python
def get_session(conversation_id: str, messages_data: list[dict]) -> RouterSession
def update_session_portfolio(conversation_id: str, portfolio: dict) -> None
```

---

## Section 3: Agent Loop (`routes/agent.py`)

### System prompt injection

Each turn, call `format_active_portfolio(session.active_portfolio)` and append to the system prompt before calling `call_llm`. If `active_portfolio` is None, nothing is appended.

```
Current working portfolio: NVDA (40%), AMD (35%), INTC (25%)
The user may refer to this as "the portfolio", "that", or "it".
```

### Session state updates after tool execution

After each successful tool call in the agent loop:
- `optimize_portfolio` result → extract tickers/weights, call `update_session_portfolio`
- `load_portfolio` result → extract portfolio fields, call `update_session_portfolio`
- All other tools → no session update

### `grounding_sources` in SSE and persistence

Accumulate `grounding_sources` from each `LLMResponse` across all iterations (dedup by URL). On the `done` event, include them:

```python
yield _sse("done", {"grounding_sources": [asdict(s) for s in all_sources]})
```

When persisting the assistant message to Supabase, include:
```python
sb.table("messages").insert({
    ...
    "grounding_sources": [asdict(s) for s in all_sources] or None,
}).execute()
```

---

## Section 4: Database Migration

Add column to `messages` table:

```sql
ALTER TABLE messages ADD COLUMN grounding_sources jsonb;
```

No backfill needed — existing messages without citations render normally (empty sources list).

---

## Section 5: Frontend

### Types (`chat-types.ts`)

```typescript
export interface GroundingSource {
  index: number;
  title: string;
  url: string;
  date: string | null;
}

// Add to Message type:
grounding_sources?: GroundingSource[];
```

### `useChat.ts` changes

- On `done` SSE event: attach `grounding_sources` to the current assistant message in state
- On `loadConversation`: hydrate `grounding_sources` from the stored message row (already in `blocks` JSONB or the new column)

### Citation rendering (`MessageBubble.tsx`)

For assistant messages with `grounding_sources.length > 0`:

1. **Inline markers** — insert `<sup>` elements at citation positions. Since Gemini doesn't return character offsets in grounding chunks, render markers sequentially after the message text as a grouped indicator (e.g., `¹ ²` at end of paragraph), rather than mid-sentence. If Gemini returns segment offsets in `grounding_metadata.grounding_supports`, use those for precise mid-sentence placement.

2. **Sources footnote block** — always collapsed by default. Structure:
   - Thin `border-t` divider
   - `"Sources (n)"` toggle with chevron, 11px, `text-gray-500`
   - On expand: numbered list, 11px, `text-gray-500`, each entry: `{index} {publication} · {title as link} · {date}`

3. **Superscript style**: `text-blue-400`, `font-bold`, `text-[15px]`, `vertical-align: super`, `leading-none`

4. **Collapsed by default** always — regardless of citation count. No "more than 3" threshold since collapsed-by-default is cleaner for a financial tool.

---

## What is NOT changing

- The 8-iteration tool-calling loop structure — unchanged
- The OpenAI LLM fallback trigger condition (503/rate-limit) — unchanged
- SSE event types (`text`, `tool_call`, `tool_result`, `error`, `done`) — `done` gains `grounding_sources` field, all others unchanged
- Supabase RLS policies — no new tables, existing policies cover the new column
- Auth flow — unchanged

---

## Acceptance Criteria

- A question like "what did NVIDIA say on their last earnings call?" triggers Gemini search grounding and returns a response with visible `¹` markers and a collapsed Sources block
- A follow-up "now optimize a portfolio around that thesis" executes quantitative tools without triggering search
- After `optimize_portfolio` runs, saying "remove TSLA from that" works without re-specifying tickers — session state provides the context
- Citations are persisted to the `grounding_sources` column and rehydrate identically on conversation reload
- OpenAI fallback path returns citations via the Responses API annotations field, rendered in the same Sources block format
- Server restart does not lose active portfolio state for conversations with recent tool results in message history
