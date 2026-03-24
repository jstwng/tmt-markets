"""Build a blocks array from accumulated text and tool calls for message storage."""

from typing import Any


def build_blocks_for_storage(text: str, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert accumulated text + tool calls into a display-ready blocks array.

    Stored in messages.blocks so the frontend can replay conversations without
    re-running the block mapper. The invariant: every block type here must have
    a corresponding renderer in MessageBubble.tsx.

    tool_call results that produce a chart_manifest (openbb_query) become
    manifest_chart blocks. All other tool results are stored as tool_result blocks
    for frontend hydration via mapToolResultToBlocks.
    """
    blocks: list[dict[str, Any]] = []

    for tc in tool_calls:
        blocks.append({
            "type": "tool_call",
            "name": tc["name"],
            "displayName": tc["name"],
            "args": tc.get("args", {}),
            "status": "complete",
        })

        if "result" in tc:
            result = tc["result"]
            if isinstance(result, dict) and result.get("chart_manifest"):
                # openbb_query: store display-ready manifest_chart block directly
                blocks.append({
                    "type": "manifest_chart",
                    "manifest": result["chart_manifest"],
                })
            else:
                # Other tools: store as tool_result for frontend hydration via mapToolResultToBlocks
                blocks.append({
                    "type": "tool_result",
                    "name": tc["name"],
                    "result": result,
                })

        if "error" in tc:
            blocks.append({
                "type": "error",
                "message": tc["error"],
            })

    if text:
        blocks.append({"type": "text", "text": text})

    return blocks


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
