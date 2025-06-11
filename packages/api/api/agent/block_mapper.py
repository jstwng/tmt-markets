"""Build a blocks array from accumulated text and tool calls for message storage."""

from typing import Any


def build_blocks_for_storage(text: str, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert accumulated text + tool calls into a blocks array matching the frontend format.

    This is stored in the messages.blocks column so the frontend can replay
    conversations without re-running the block mapper.
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
            blocks.append({
                "type": "tool_result",
                "name": tc["name"],
                "result": tc["result"],
            })
        elif "error" in tc:
            blocks.append({
                "type": "error",
                "message": tc["error"],
            })

    if text:
        blocks.append({"type": "text", "text": text})

    return blocks
