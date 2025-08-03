"""Terminal tab panel endpoints.

GET /api/terminal/panel/{panel}?ttl=300

Returns raw OpenBB data for each panel. Each panel uses a fixed codegen prompt,
executes in the OpenBB sandbox, and caches the result server-side for `ttl` seconds.
"""

import time
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from api.agent.openbb_codegen import generate_openbb_code
from api.agent.openbb_sandbox import execute_openbb_code, validate_code
from api.agent.terminal_prompts import PANEL_PROMPTS

router = APIRouter(tags=["terminal"])

# In-memory cache: panel -> {"data": ..., "ts": float, "ttl": int}
_cache: dict[str, dict[str, Any]] = {}

_MAX_RETRIES = 4


def _get_obb_client():
    from api.agent.openbb_client import get_obb_client
    return get_obb_client()


def _inject_dates(prompt: str) -> str:
    """Replace date placeholders with real dates.

    Replacements (most specific first to avoid prefix collisions):
      REPLACE_START_3   -> 3 days ago        (heatmap)
      REPLACE_START_60  -> today              (calendar start)
      REPLACE_END_60    -> 60 days from now   (calendar end)
      REPLACE_START     -> 10 days ago        (indices)
      REPLACE_END       -> today              (indices)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    ten_days_ago = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    sixty_days_out = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

    return (
        prompt
        .replace("REPLACE_START_3", three_days_ago)
        .replace("REPLACE_START_60", today)
        .replace("REPLACE_END_60", sixty_days_out)
        .replace("REPLACE_START", ten_days_ago)
        .replace("REPLACE_END", today)
    )


async def _fetch_panel(panel: str) -> list | dict:
    """Run codegen -> validate -> execute with up to _MAX_RETRIES attempts."""
    prompts = PANEL_PROMPTS[panel]
    user = _inject_dates(prompts["user"])
    obb = _get_obb_client()

    error_context = None
    for attempt in range(_MAX_RETRIES):
        code = await generate_openbb_code(user, error_context=error_context)
        valid, reason = validate_code(code)
        if not valid:
            error_context = f"Code failed AST validation: {reason}"
            continue
        try:
            result = await execute_openbb_code(code, obb)
            return result
        except Exception as exc:
            error_context = str(exc)

    raise RuntimeError(f"Panel '{panel}' failed after {_MAX_RETRIES} attempts. Last error: {error_context}")


@router.get("/terminal/panel/{panel}")
async def get_terminal_panel(panel: str, ttl: int = 300):
    if panel not in PANEL_PROMPTS:
        raise HTTPException(status_code=404, detail=f"Unknown panel: {panel}")

    cached = _cache.get(panel)
    if cached and (time.time() - cached["ts"]) < ttl:
        return cached["data"]

    try:
        raw_data = await _fetch_panel(panel)
        response = {
            "panel": panel,
            "raw_data": raw_data,
            "cached_at": datetime.utcnow().isoformat() + "Z",
            "error": False,
        }
        _cache[panel] = {"data": response, "ts": time.time()}
        return response
    except Exception as exc:
        stale = _cache.get(panel, {}).get("data")
        return {
            "panel": panel,
            "raw_data": stale["raw_data"] if stale else [],
            "cached_at": stale["cached_at"] if stale else None,
            "error": True,
            "error_message": str(exc),
        }
