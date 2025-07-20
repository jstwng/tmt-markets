"""Tests for build_blocks_for_storage in api/agent/block_mapper.py."""
import pytest
from api.agent.block_mapper import build_blocks_for_storage


class TestBuildBlocksForStorage:
    def test_text_only_produces_text_block(self):
        blocks = build_blocks_for_storage("Hello world", [])
        assert blocks == [{"type": "text", "text": "Hello world"}]

    def test_empty_text_no_text_block(self):
        blocks = build_blocks_for_storage("", [])
        assert blocks == []

    def test_tool_call_without_result_produces_only_tool_call_block(self):
        tc = {"name": "some_tool", "args": {"x": 1}}
        blocks = build_blocks_for_storage("", [tc])
        assert blocks == [
            {
                "type": "tool_call",
                "name": "some_tool",
                "displayName": "some_tool",
                "args": {"x": 1},
                "status": "complete",
            }
        ]

    def test_openbb_query_with_chart_manifest_produces_manifest_chart_block(self):
        manifest = {
            "chart_type": "time_series",
            "title": "Price Chart",
            "data": [1, 2, 3],
            "source": {"query": "q", "openbb_call": "c", "timestamp": "t"},
        }
        tc = {
            "name": "openbb_query",
            "args": {"query": "AAPL price"},
            "result": {"chart_manifest": manifest},
        }
        blocks = build_blocks_for_storage("", [tc])
        assert len(blocks) == 2
        assert blocks[0]["type"] == "tool_call"
        assert blocks[1] == {"type": "manifest_chart", "manifest": manifest}

    def test_tool_result_without_chart_manifest_is_stored(self):
        """Non-chart tool results are stored as tool_result blocks for frontend hydration."""
        tc = {
            "name": "fetch_prices",
            "args": {"tickers": ["AAPL"]},
            "result": {"prices": [100, 101], "dates": ["2024-01-01"]},
        }
        blocks = build_blocks_for_storage("", [tc])
        assert len(blocks) == 2
        assert blocks[0]["type"] == "tool_call"
        assert blocks[1] == {
            "type": "tool_result",
            "name": "fetch_prices",
            "result": {"prices": [100, 101], "dates": ["2024-01-01"]},
        }

    def test_error_produces_error_block(self):
        tc = {"name": "some_tool", "args": {}, "error": "Something went wrong"}
        blocks = build_blocks_for_storage("", [tc])
        assert len(blocks) == 2
        assert blocks[1] == {"type": "error", "message": "Something went wrong"}

    def test_multiple_tools_ordering(self):
        """tool_call → manifest_chart per chart tool; tool_result for others; text last."""
        manifest = {
            "chart_type": "bar",
            "title": "Chart",
            "data": {},
            "source": {"query": "q", "openbb_call": "c", "timestamp": "t"},
        }
        tool_calls = [
            {"name": "fetch_prices", "args": {}, "result": {"prices": []}},
            {"name": "openbb_query", "args": {}, "result": {"chart_manifest": manifest}},
        ]
        blocks = build_blocks_for_storage("Summary", tool_calls)
        types = [b["type"] for b in blocks]
        assert types == ["tool_call", "tool_result", "tool_call", "manifest_chart", "text"]
