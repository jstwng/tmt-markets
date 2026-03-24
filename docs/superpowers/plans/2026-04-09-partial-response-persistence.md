# Partial Response Persistence on Error — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist partial assistant responses (tool calls, charts, text) plus an error block to the database even when a backend exception interrupts the agent loop, and fix a frontend race condition that wipes live streaming state.

**Architecture:** Extract a small `_build_assistant_blocks` helper in `block_mapper.py` that handles error appending, then restructure `agent.py`'s `generate()` to hoist accumulator variables before the try block and run the DB save in a `finally` block. A one-line ref-assignment fix in `Chat.tsx` prevents `loadConversation` from being triggered during streaming.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript (frontend), pytest

---

## File Map

| File | Change |
|------|--------|
| `packages/api/api/agent/block_mapper.py` | Add `_build_assistant_blocks` helper |
| `packages/api/tests/test_block_mapper.py` | Tests for new helper |
| `packages/api/api/routes/agent.py` | Hoist accumulators; finally-block persistence |
| `packages/web/src/pages/Chat.tsx` | Set `loadedRef.current` before `navigate` |

---

## Task 1: Add `_build_assistant_blocks` helper to `block_mapper.py`

Extracts the "build blocks + optionally append top-level error" logic into a testable unit.

**Files:**
- Modify: `packages/api/api/agent/block_mapper.py`
- Test: `packages/api/tests/test_block_mapper.py`

- [ ] **Step 1: Write failing tests**

Add to `packages/api/tests/test_block_mapper.py`:

```python
from api.agent.block_mapper import build_blocks_for_storage, _build_assistant_blocks


class TestBuildAssistantBlocks:
    def test_no_content_no_error_returns_empty(self):
        blocks = _build_assistant_blocks("", [], None)
        assert blocks == []

    def test_text_only_no_error(self):
        blocks = _build_assistant_blocks("Hello", [], None)
        assert blocks == [{"type": "text", "text": "Hello"}]

    def test_tool_call_no_error(self):
        tc = {"name": "fetch_prices", "args": {}, "result": {"prices": []}}
        blocks = _build_assistant_blocks("", [tc], None)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "tool_call"
        assert blocks[1]["type"] == "tool_result"

    def test_error_only_appends_error_block(self):
        blocks = _build_assistant_blocks("", [], ValueError("LLM failed"))
        assert blocks == [{"type": "error", "message": "LLM failed"}]

    def test_partial_results_plus_error(self):
        tc = {"name": "fetch_prices", "args": {}, "result": {"prices": []}}
        blocks = _build_assistant_blocks("partial text", [tc], RuntimeError("timeout"))
        types = [b["type"] for b in blocks]
        assert types == ["tool_call", "tool_result", "text", "error"]
        assert blocks[-1]["message"] == "timeout"

    def test_no_error_matches_build_blocks_for_storage(self):
        tc = {"name": "fetch_prices", "args": {}, "result": {"prices": []}}
        assert _build_assistant_blocks("hi", [tc], None) == build_blocks_for_storage("hi", [tc])
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd packages/api && python -m pytest tests/test_block_mapper.py::TestBuildAssistantBlocks -v
```

Expected: `ImportError: cannot import name '_build_assistant_blocks'`

- [ ] **Step 3: Implement `_build_assistant_blocks` in `block_mapper.py`**

Add at the bottom of `packages/api/api/agent/block_mapper.py`:

```python
def _build_assistant_blocks(
    text: str,
    tool_calls: list[dict[str, Any]],
    error: Exception | None,
) -> list[dict[str, Any]]:
    """Build display blocks for an assistant message, appending an error block if needed.

    Wraps build_blocks_for_storage and adds a top-level error block when the
    agent loop raised an exception (as opposed to a tool-level error, which
    build_blocks_for_storage already handles via the "error" key in tool_calls).
    """
    blocks = build_blocks_for_storage(text, tool_calls)
    if error is not None:
        blocks.append({"type": "error", "message": str(error)})
    return blocks
```

Also update the `__all__` export at the top of the file (if present) or just add the function — the file currently has no `__all__`.

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd packages/api && python -m pytest tests/test_block_mapper.py -v
```

Expected: All tests in `TestBuildBlocksForStorage` and `TestBuildAssistantBlocks` pass.

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/agent/block_mapper.py packages/api/tests/test_block_mapper.py
git commit -m "feat: add _build_assistant_blocks helper with error block support"
```

---

## Task 2: Restructure `agent.py` to persist partial response on exception

Hoist accumulators before the try block; use `finally` for the DB save; remove the duplicate save from the try block's success path.

**Files:**
- Modify: `packages/api/api/routes/agent.py`

> **No new unit tests** — `generate()` is a deeply-coupled async generator. The behavior is verified by the `_build_assistant_blocks` tests above and by manual smoke testing.

- [ ] **Step 1: Identify the variables to hoist**

In `generate()` (starting at line 117), the following are currently initialized inside the try block and must be accessible in `finally`:

| Variable | Current location | Initial value |
|----------|-----------------|---------------|
| `sb` | line 119 `sb = get_user_client(...)` | `None` |
| `conversation_id` | line 123 `conversation_id = req.conversation_id` | `req.conversation_id` |
| `accumulated_text` | line 179 | `""` |
| `accumulated_tool_calls` | line 180 | `[]` |
| `all_grounding_sources` | line 182 | `[]` |
| `next_ordinal` | line 157 (after history fetch) | `0` |
| `user_message_saved` | does not exist | `False` |

`user_message_saved` is a new flag set to `True` after the user message INSERT succeeds. The `finally` block skips the save when this is False — prevents a confusing empty assistant message if the conversation was never properly initialized.

- [ ] **Step 2: Apply the restructuring**

Replace the `generate()` function body in `packages/api/api/routes/agent.py`. The full new body (replace everything from `async def generate()` through the closing `except` block):

```python
    async def generate() -> AsyncGenerator[dict, None]:
        # Accumulators hoisted so finally can persist partial results
        sb = None
        conversation_id: str | None = req.conversation_id
        accumulated_text = ""
        accumulated_tool_calls: list[dict] = []
        all_grounding_sources: list[GroundingSource] = []
        next_ordinal = 0
        user_message_saved = False
        caught_error: Exception | None = None

        try:
            sb = get_user_client(access_token)
            client = _get_client()

            # ------ Resolve or create conversation ------
            if conversation_id:
                result = sb.table("conversations").select("id").eq("id", conversation_id).execute()
                if not result.data:
                    yield _sse("error", {"message": "Conversation not found"})
                    yield _sse("done", {})
                    return
            else:
                title = req.message[:80].strip()
                result = sb.table("conversations").insert({
                    "user_id": user.id,
                    "title": title,
                }).execute()
                conversation_id = result.data[0]["id"]

            yield _sse("conversation", {"conversation_id": conversation_id})

            # ------ Load existing history ------
            history_result = sb.table("messages") \
                .select("*") \
                .eq("conversation_id", conversation_id) \
                .order("ordinal") \
                .limit(100) \
                .execute()

            existing_messages = history_result.data or []

            # Load or reconstruct session state for portfolio context
            session = get_session(conversation_id, existing_messages)
            dynamic_system_prompt = SYSTEM_PROMPT + format_active_portfolio(session.active_portfolio)

            recent_messages = existing_messages[-50:] if len(existing_messages) > 50 else existing_messages
            gemini_history = _rebuild_gemini_history(recent_messages)

            next_ordinal = _get_next_ordinal(existing_messages)

            # ------ Persist user message ------
            sb.table("messages").insert({
                "conversation_id": conversation_id,
                "role": "user",
                "content": req.message,
                "blocks": [{"type": "text", "text": req.message}],
                "ordinal": next_ordinal,
            }).execute()
            next_ordinal += 1
            user_message_saved = True

            # ------ Add user message to Gemini history ------
            from google.genai import types as genai_types
            gemini_history.append(
                genai_types.Content(
                    role="user",
                    parts=[genai_types.Part(text=req.message)],
                )
            )

            # ------ Agent loop ------
            last_tool_result: dict | None = None
            seen_urls: set[str] = set()

            # ------ Classify intent ------
            yield _sse("tool_call", {"name": "classify_intent", "args": {}})
            last_tool = accumulated_tool_calls[-1]["name"] if accumulated_tool_calls else None
            classifier_context = _build_classifier_context(session, last_tool)
            intent_result = await classify_intent(req.message, classifier_context)
            logger.info("Intent classified as: %s", intent_result.intent)
            yield _sse("tool_result", {"name": "classify_intent", "result": {"intent": intent_result.intent}})

            # ------ Phase 1: Search (if search or hybrid) ------
            search_text = ""
            if intent_result.intent in ("search", "hybrid"):
                yield _sse("tool_call", {"name": "web_search", "args": {}})
                search_result = await run_search_phase(req.message)
                yield _sse("tool_result", {"name": "web_search", "result": {}})
                search_text = search_result.text
                for src in search_result.sources:
                    if src.url not in seen_urls:
                        seen_urls.add(src.url)
                        all_grounding_sources.append(src)
                if search_text:
                    yield _sse("text", {"text": search_text})
                    accumulated_text += search_text

            # ------ Phase 2: Route by intent ------
            if intent_result.intent == "search" and search_text:
                # Search-only: search text is the final answer, no agent loop
                pass

            elif intent_result.intent in ("search", "conversational"):
                # No tools — plain text generation (also fallback when search returned empty)
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
                                        if isinstance(result, dict) and "tickers" in result:
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

            yield _sse("done", {
                "grounding_sources": [asdict(s) for s in all_grounding_sources],
            })

        except Exception as e:
            caught_error = e
            yield _sse("error", {"message": str(e)})
            yield _sse("done", {})

        finally:
            # Always persist the assistant message if the conversation was initialized.
            # caught_error being set means partial results were streamed before the failure.
            if sb is not None and conversation_id is not None and user_message_saved:
                from api.agent.block_mapper import _build_assistant_blocks
                blocks = _build_assistant_blocks(accumulated_text, accumulated_tool_calls, caught_error)
                if blocks or accumulated_text:
                    sb.table("messages").insert({
                        "conversation_id": conversation_id,
                        "role": "assistant",
                        "content": accumulated_text or None,
                        "tool_calls": accumulated_tool_calls or None,
                        "blocks": blocks,
                        "grounding_sources": [asdict(s) for s in all_grounding_sources] or None,
                        "ordinal": next_ordinal,
                    }).execute()
                sb.table("conversations").update({
                    "updated_at": "now()",
                }).eq("id", conversation_id).execute()
```

Key differences from the original:
- `accumulated_text`, `accumulated_tool_calls`, `all_grounding_sources`, `conversation_id`, `sb`, `next_ordinal`, `user_message_saved`, `caught_error` declared before `try`
- `last_tool_result` and `seen_urls` remain inside `try` (not needed in `finally`)
- `user_message_saved = True` set immediately after the user message INSERT
- `done` SSE event moved to end of try block (success path only)
- `except` block only captures exception and yields error/done SSE events
- `finally` block calls `_build_assistant_blocks` and does the INSERT

- [ ] **Step 3: Verify no import needed at top level**

`_build_assistant_blocks` is imported inline inside `finally`. The existing top-of-function `from api.agent.block_mapper import build_blocks_for_storage` in the old try block can be removed — the new code uses `_build_assistant_blocks` which wraps it internally.

Check that `build_blocks_for_storage` is not used anywhere else in `agent.py`:

```bash
grep -n "build_blocks_for_storage" packages/api/api/routes/agent.py
```

Expected: no output (it should be gone after the edit).

- [ ] **Step 4: Smoke test — start the server and send a request**

```bash
cd packages/api && uvicorn api.main:app --reload --port 8000
```

In a second terminal:
```bash
curl -s -N -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <valid_token>" \
  -d '{"message": "What is 2+2?"}' | head -20
```

Expected: SSE events including `event: conversation`, `event: text`, `event: done` with no Python traceback in server logs.

- [ ] **Step 5: Commit**

```bash
git add packages/api/api/routes/agent.py
git commit -m "fix: persist partial assistant response in finally block, preserve on error"
```

---

## Task 3: Fix frontend race condition in `Chat.tsx`

When a new conversation is created (first SSE event), the navigate effect changes the URL. The URL-change effect then calls `loadConversation`, wiping live streaming state. Fix: mark `loadedRef.current` before navigating.

**Files:**
- Modify: `packages/web/src/pages/Chat.tsx:49-55`

> **No automated test** — this is a React render-lifecycle fix. Verified by manual smoke test.

- [ ] **Step 1: Apply the one-line fix**

In `packages/web/src/pages/Chat.tsx`, find the navigate effect (around line 49):

```tsx
  // Sync conversationId back to URL after first message creates it
  useEffect(() => {
    if (conversationId && !urlConversationId) {
      navigate(`/c/${conversationId}`, { replace: true });
      refetch();
    }
  }, [conversationId, urlConversationId, navigate, refetch]);
```

Replace with:

```tsx
  // Sync conversationId back to URL after first message creates it
  useEffect(() => {
    if (conversationId && !urlConversationId) {
      // Mark as loaded BEFORE navigating so the URL-change effect doesn't
      // call loadConversation and wipe live streaming state mid-response.
      loadedRef.current = conversationId;
      navigate(`/c/${conversationId}`, { replace: true });
      refetch();
    }
  }, [conversationId, urlConversationId, navigate, refetch]);
```

- [ ] **Step 2: Smoke test**

Start the dev server:
```bash
cd packages/web && npm run dev
```

1. Navigate to `/` (empty state)
2. Send a message: "Show the efficient frontier for SPY, TLT, GLD, and QQQ"
3. Verify the URL changes to `/c/<id>` AND the response streams and renders (charts, metrics appear)
4. Reload the page — verify the full conversation (user message + assistant charts/text) loads from DB

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/pages/Chat.tsx
git commit -m "fix: prevent loadConversation race during new conversation streaming"
```

---

## Task 4: End-to-end verification

- [ ] **Step 1: Run all backend tests**

```bash
cd packages/api && python -m pytest tests/ -v --tb=short
```

Expected: All tests pass. Pay attention to `test_block_mapper.py` — both `TestBuildBlocksForStorage` and `TestBuildAssistantBlocks` should be green.

- [ ] **Step 2: Manual error path verification**

To verify partial results persist on error, temporarily inject a failure at the end of the agent loop. In `agent.py`, add `raise RuntimeError("test error")` just before the success-path `yield _sse("done", ...)`:

```python
            raise RuntimeError("test error")  # TEMP: remove after test
            yield _sse("done", {
```

Send a message that produces tool results (e.g., "Show the efficient frontier for SPY, TLT, GLD, and QQQ"). Verify:
- The response streams tool results in the UI
- An error block appears at the end
- Reload the page — the tool results AND error block are visible

Remove the injected error after verifying.

- [ ] **Step 3: Push to remote**

```bash
git pull --rebase
git push
```
