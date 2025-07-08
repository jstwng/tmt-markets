"""Tests that terminal prompts exist and are non-empty strings."""
from api.agent.terminal_prompts import PANEL_PROMPTS


def test_all_panels_have_prompts():
    for panel in ("macro", "indices", "movers", "heatmap", "calendar"):
        assert panel in PANEL_PROMPTS
        assert isinstance(PANEL_PROMPTS[panel]["system"], str)
        assert len(PANEL_PROMPTS[panel]["system"]) > 50
        assert isinstance(PANEL_PROMPTS[panel]["user"], str)
        assert len(PANEL_PROMPTS[panel]["user"]) > 10


def test_prompts_mention_obb():
    for panel, prompts in PANEL_PROMPTS.items():
        combined = prompts["system"] + prompts["user"]
        assert "obb" in combined.lower() or "openbb" in combined.lower(), \
            f"Panel '{panel}' prompt doesn't reference obb"
