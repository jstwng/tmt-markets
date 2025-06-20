"""Tests for OpenBB code generation and chart manifest generation."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from api.agent.openbb_codegen import generate_openbb_code, generate_chart_manifest


class TestGenerateOpenbbCode:
    """Code generation via Gemini."""

    @pytest.mark.asyncio
    @patch("api.agent.openbb_codegen._call_gemini_codegen")
    async def test_returns_code_string(self, mock_call):
        mock_call.return_value = 'def fetch():\n    return obb.equity.price.historical("AAPL")'
        code = await generate_openbb_code("Get AAPL price history")
        assert "def fetch()" in code
        assert "obb.equity" in code

    @pytest.mark.asyncio
    @patch("api.agent.openbb_codegen._call_gemini_codegen")
    async def test_passes_error_context_on_retry(self, mock_call):
        mock_call.return_value = 'def fetch():\n    return {}'
        code = await generate_openbb_code(
            "Get AAPL prices",
            error_context="Previous attempt failed: NameError"
        )
        # Verify error_context was passed to the prompt
        call_args = mock_call.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "NameError" in prompt or mock_call.called


class TestGenerateChartManifest:
    """Chart manifest generation via Gemini."""

    @pytest.mark.asyncio
    @patch("api.agent.openbb_codegen._call_gemini_manifest")
    async def test_returns_valid_manifest(self, mock_call):
        mock_call.return_value = json.dumps({
            "chart_type": "time_series",
            "title": "AAPL Price History",
            "data": {"series": [{"name": "AAPL", "values": [{"date": "2024-01-01", "value": 150}]}]},
            "source": {"query": "test", "openbb_call": "test", "timestamp": "2024-01-01T00:00:00Z"}
        })
        manifest = await generate_chart_manifest(
            description="Get AAPL prices",
            data=[{"date": "2024-01-01", "close": 150}],
            code='obb.equity.price.historical("AAPL")'
        )
        assert manifest["chart_type"] == "time_series"
        assert manifest["title"] == "AAPL Price History"

    @pytest.mark.asyncio
    @patch("api.agent.openbb_codegen._call_gemini_manifest")
    async def test_handles_invalid_json(self, mock_call):
        mock_call.return_value = "not valid json"
        with pytest.raises(ValueError, match="manifest"):
            await generate_chart_manifest(
                description="test",
                data={},
                code="test"
            )
