"""Build a blocks array from accumulated text and tool calls for message storage."""

from typing import Any


def build_blocks_for_storage(text: str, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert accumulated text + tool calls into a display-ready blocks array.

    Stored in messages.blocks so the frontend can replay conversations without
    re-running the block mapper. The invariant: every block type here must have
    a corresponding renderer in MessageBubble.tsx.

    tool_call results that produce a chart_manifest (openbb_query) become
    manifest_chart blocks. All other tool results are dropped — they have no
    frontend renderer. Raw execution data is preserved separately in tool_calls.
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
                blocks.append({
                    "type": "manifest_chart",
                    "manifest": result["chart_manifest"],
                })
            # other tool results dropped — no frontend renderer exists for them

        if "error" in tc:
            blocks.append({
                "type": "error",
                "message": tc["error"],
            })

    if text:
        blocks.append({"type": "text", "text": text})

    return blocks
