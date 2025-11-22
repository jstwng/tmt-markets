"""Terminal tab panel endpoints.

GET /api/terminal/panel/{panel}?ttl=300

Returns raw data for each panel. Each panel has a deterministic fetcher
in panel_fetchers.py — no LLM code generation involved.
"""

import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from api.agent.panel_fetchers import (
    fetch_calendar,
    fetch_heatmap,
    fetch_indices,
    fetch_macro,
    fetch_movers,
)

router = APIRouter(tags=["terminal"])

# In-memory cache: panel -> {"data": ..., "ts": float}
_cache: dict[str, dict[str, Any]] = {}

PANEL_FETCHERS = {
    "macro": fetch_macro,
    "indices": fetch_indices,
    "movers": fetch_movers,
    "heatmap": fetch_heatmap,
    "calendar": fetch_calendar,
}


@router.get("/terminal/panel/{panel}")
async def get_terminal_panel(panel: str, ttl: int = 300):
    if panel not in PANEL_FETCHERS:
        raise HTTPException(status_code=404, detail=f"Unknown panel: {panel}")

    cached = _cache.get(panel)
    if cached and (time.time() - cached["ts"]) < ttl:
        return cached["data"]

    try:
        raw_data = await PANEL_FETCHERS[panel]()
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
