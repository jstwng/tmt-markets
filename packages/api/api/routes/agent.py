"""AI agent route: SSE streaming chat endpoint powered by Gemini."""

import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from api.agent.client import create_gemini_client, MODEL_NAME
from api.agent.sessions import session_store
from api.agent.tools import TOOL_DECLARATIONS, execute_tool

router = APIRouter(tags=["agent"])

# Lazy-initialised singleton — avoids cold import overhead at startup
_gemini_client = None


def _get_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = create_gemini_client()
    return _gemini_client


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
      - thinking  {text}          — partial reasoning text from Gemini
      - tool_call {name, args}    — function call Gemini wants to make
      - tool_result {name, result} — output from the quant tool
      - text      {text}          — final text chunk from Gemini
      - error     {message}       — error (tool or API)
      - done      {}              — stream complete
    """
    async def generate() -> AsyncGenerator[dict, None]:
        try:
            session = await session_store.get_or_create(req.session_id)
            yield _sse("session", {"session_id": session.session_id})

            client = _get_client()

            # Add user message to history
            from google.genai import types as genai_types
            session.history.append(
                genai_types.Content(
                    role="user",
                    parts=[genai_types.Part(text=req.message)],
                )
            )

            # Agent loop: keep calling Gemini until it returns pure text (no more function calls)
            max_iterations = 8  # safety limit
            for _ in range(max_iterations):
                response = await _call_gemini(client, session.history)

                # Process response parts
                has_function_call = False
                tool_results_parts: list[genai_types.Part] = []

                for part in response.parts:
                    if part.text:
                        yield _sse("text", {"text": part.text})

                    if part.function_call:
                        has_function_call = True
                        fn = part.function_call
                        args = dict(fn.args) if fn.args else {}

                        yield _sse("tool_call", {"name": fn.name, "args": args})

                        try:
                            result = await execute_tool(fn.name, args)
                            yield _sse("tool_result", {"name": fn.name, "result": result})
                            tool_results_parts.append(
                                genai_types.Part(
                                    function_response=genai_types.FunctionResponse(
                                        name=fn.name,
                                        response={"result": result},
                                    )
                                )
                            )
                        except Exception as e:
                            error_msg = str(e)
                            yield _sse("error", {"message": f"Tool '{fn.name}' failed: {error_msg}"})
                            tool_results_parts.append(
                                genai_types.Part(
                                    function_response=genai_types.FunctionResponse(
                                        name=fn.name,
                                        response={"error": error_msg},
                                    )
                                )
                            )

                # Add model response to history
                session.history.append(
                    genai_types.Content(role="model", parts=response.parts)
                )

                if not has_function_call:
                    # Model returned text only — conversation turn complete
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


async def _call_gemini(client, history):
    """Call Gemini with the full conversation history."""
    import asyncio
    from api.agent.prompts import SYSTEM_PROMPT
    from google.genai import types as genai_types

    config = genai_types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[TOOL_DECLARATIONS],
        temperature=0.1,
        max_output_tokens=2048,
    )

    return await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL_NAME,
        contents=history,
        config=config,
    )


# ---------------------------------------------------------------------------
# Session lifecycle routes (Bead 6)
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
