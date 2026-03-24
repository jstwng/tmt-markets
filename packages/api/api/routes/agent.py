"""AI agent route: SSE streaming chat endpoint powered by Gemini with Supabase persistence."""

import json
from dataclasses import asdict
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from api.agent.client import create_gemini_client, MODEL_NAME
from api.agent.llm import call_llm, call_llm_text, GroundingSource
from api.agent.classifier import classify_intent
from api.agent.search import run_search_phase
from api.agent.openbb_client import get_obb_client
from api.agent.openbb_codegen import generate_openbb_code, generate_chart_manifest
from api.agent.openbb_sandbox import validate_code, execute_openbb_code, _classify_error
from api.agent.tools import (
    TOOL_DECLARATIONS, execute_tool, PERSISTENCE_TOOLS,
    run_load_portfolio, run_save_portfolio, run_save_output,
)
from api.agent.router_state import get_session, update_session_portfolio
from api.agent.prompts import SYSTEM_PROMPT, format_active_portfolio
from api.auth import get_current_user, AuthenticatedUser
from api.supabase_client import get_user_client

import logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent"])

_bearer_scheme = HTTPBearer()

_gemini_client = None


def _get_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = create_gemini_client()
    return _gemini_client


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


def _sse(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data)}


def _get_next_ordinal(messages_data: list[dict]) -> int:
    if not messages_data:
        return 0
    return max(m["ordinal"] for m in messages_data) + 1


def _rebuild_gemini_history(messages_data: list[dict]) -> list:
    """Reconstruct Gemini Content objects from stored messages."""
    from google.genai import types as genai_types

    history = []
    for msg in messages_data:
        role = "user" if msg["role"] == "user" else "model"
        parts = []

        if msg.get("content") and not msg.get("tool_calls"):
            parts.append(genai_types.Part(text=msg["content"]))

        if msg.get("tool_calls"):
            if role == "model":
                for tc in msg["tool_calls"]:
                    parts.append(genai_types.Part(
                        function_call=genai_types.FunctionCall(
                            name=tc["name"],
                            args=tc.get("args", {}),
                        )
                    ))
            elif role == "user":
                for tc in msg["tool_calls"]:
                    if "result" in tc:
                        parts.append(genai_types.Part(
                            function_response=genai_types.FunctionResponse(
                                name=tc["name"],
                                response={"result": tc["result"]},
                            )
                        ))

        if parts:
            history.append(genai_types.Content(role=role, parts=parts))

    return history


def _build_classifier_context(session, last_tool_name: str | None) -> str | None:
    """Build one-line conversation context for the intent classifier."""
    parts = []
    if session.active_portfolio:
        tickers = session.active_portfolio.get("tickers", [])
        parts.append(f"Active portfolio: {', '.join(tickers)}")
    if last_tool_name:
        parts.append(f"Last action: {last_tool_name}")
    return ". ".join(parts) + "." if parts else None


@router.post("/agent/chat")
async def agent_chat(
    req: ChatRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    """Stream an agent response as Server-Sent Events with Supabase persistence."""
    access_token = credentials.credentials

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

    return EventSourceResponse(generate())


