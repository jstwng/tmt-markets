"""AI agent route: SSE streaming chat endpoint with Gemini + OpenAI fallback."""

import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from api.agent.llm import call_llm
from api.agent.sessions import session_store
from api.agent.tools import TOOL_DECLARATIONS, execute_tool

router = APIRouter(tags=["agent"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class SessionResponse(BaseModel):
    session_id: str


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

def _sse(event: str, data: dict) -> dict:
    """Format an SSE event dict for sse_starlette."""
    return {"event": event, "data": json.dumps(data)}


# ---------------------------------------------------------------------------
# Main chat endpoint
# ---------------------------------------------------------------------------

@router.post("/agent/chat")
async def agent_chat(req: ChatRequest):
    """Stream an agent response as Server-Sent Events.

    SSE event types:
      - session   {session_id}
      - thinking  {text}          — partial reasoning text
      - tool_call {name, args}    — function call the LLM wants to make
      - tool_result {name, result} — output from the quant tool
      - text      {text}          — final text chunk
      - error     {message}       — error (tool or API)
      - done      {}              — stream complete
    """
    async def generate() -> AsyncGenerator[dict, None]:
        try:
            session = await session_store.get_or_create(req.session_id)
            yield _sse("session", {"session_id": session.session_id})

            # Add user message to history
            from google.genai import types as genai_types
            from api.agent.prompts import SYSTEM_PROMPT

            session.history.append(
                genai_types.Content(
                    role="user",
                    parts=[genai_types.Part(text=req.message)],
                )
            )

            # Agent loop: keep calling LLM until it returns pure text (no more function calls)
            max_iterations = 8  # safety limit
            for _ in range(max_iterations):
                response = await call_llm(session.history, SYSTEM_PROMPT, TOOL_DECLARATIONS)

                # Process response parts (unified format from llm.py)
                has_function_call = False
                tool_results_parts: list[genai_types.Part] = []
                model_parts: list[genai_types.Part] = []

                for part in response.parts:
                    if part.text:
                        yield _sse("text", {"text": part.text})
                        model_parts.append(genai_types.Part(text=part.text))

                    if part.function_call:
                        has_function_call = True
                        fn_name = part.function_call["name"]
                        fn_args = part.function_call["args"]

                        yield _sse("tool_call", {"name": fn_name, "args": fn_args})

                        # Store the function call in history
                        model_parts.append(
                            genai_types.Part(
                                function_call=genai_types.FunctionCall(
                                    name=fn_name,
                                    args=fn_args,
                                )
                            )
                        )

                        if fn_name == "openbb_query":
                            from api.agent.openbb_codegen import generate_openbb_code, generate_chart_manifest
                            from api.agent.openbb_sandbox import validate_code, execute_openbb_code
                            from api.agent.openbb_client import get_obb_client

                            obb_client = get_obb_client()
                            openbb_error_context: str | None = None
                            openbb_result = None
                            openbb_code = ""
                            openbb_success = False
                            max_codegen_attempts = 3

                            for codegen_attempt in range(1, max_codegen_attempts + 1):
                                openbb_code = await generate_openbb_code(
                                    fn_args.get("description", ""),
                                    error_context=openbb_error_context,
                                )
                                yield _sse("codegen", {"code": openbb_code, "attempt": codegen_attempt})

                                valid, reason = validate_code(openbb_code)
                                if not valid:
                                    openbb_error_context = f"Validation failed: {reason}"
                                    yield _sse("codegen_retry", {
                                        "error": openbb_error_context,
                                        "attempt": codegen_attempt,
                                        "max_attempts": max_codegen_attempts,
                                    })
                                    continue

                                try:
                                    openbb_result = await execute_openbb_code(openbb_code, obb_client)
                                    openbb_success = True
                                    break
                                except Exception as exec_err:
                                    openbb_error_context = f"Execution failed: {str(exec_err)}"
                                    yield _sse("codegen_retry", {
                                        "error": openbb_error_context,
                                        "attempt": codegen_attempt,
                                        "max_attempts": max_codegen_attempts,
                                    })

                            if not openbb_success:
                                yield _sse("error", {
                                    "message": f"OpenBB query failed after {max_codegen_attempts} attempts: {openbb_error_context}"
                                })
                                tool_results_parts.append(
                                    genai_types.Part(
                                        function_response=genai_types.FunctionResponse(
                                            name=fn_name,
                                            response={"error": openbb_error_context},
                                        )
                                    )
                                )
                            else:
                                chart_manifest = await generate_chart_manifest(
                                    fn_args.get("description", ""),
                                    openbb_result,
                                    openbb_code,
                                )
                                yield _sse("tool_result", {
                                    "name": fn_name,
                                    "result": openbb_result,
                                    "chart_manifest": chart_manifest,
                                })
                                tool_results_parts.append(
                                    genai_types.Part(
                                        function_response=genai_types.FunctionResponse(
                                            name=fn_name,
                                            response={"result": openbb_result},
                                        )
                                    )
                                )
                        else:
                            try:
                                result = await execute_tool(fn_name, fn_args)
                                yield _sse("tool_result", {"name": fn_name, "result": result})
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
                                tool_results_parts.append(
                                    genai_types.Part(
                                        function_response=genai_types.FunctionResponse(
                                            name=fn_name,
                                            response={"error": error_msg},
                                        )
                                    )
                                )

                # Add model response to history (in Gemini format for session continuity)
                session.history.append(
                    genai_types.Content(role="model", parts=model_parts)
                )

                if not has_function_call:
                    break

                # Feed tool results back to model
                session.history.append(
                    genai_types.Content(role="user", parts=tool_results_parts)
                )

            yield _sse("done", {})

        except Exception as e:
            yield _sse("error", {"message": str(e)})
            yield _sse("done", {})

    return EventSourceResponse(generate())


# ---------------------------------------------------------------------------
# Session lifecycle routes
# ---------------------------------------------------------------------------

@router.post("/agent/sessions", response_model=SessionResponse)
async def create_session():
    """Create a new conversation session."""
    session_id = await session_store.create_session()
    return SessionResponse(session_id=session_id)


@router.delete("/agent/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session."""
    await session_store.delete_session(session_id)
    return JSONResponse(content={"deleted": session_id})
