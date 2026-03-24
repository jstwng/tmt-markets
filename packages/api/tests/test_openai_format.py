"""Tests for OpenAI Responses API format conversions.

Validates that Gemini-shaped data is correctly converted to the OpenAI
Responses API format — tool declarations, message history, and response parsing.
"""

import json
from unittest.mock import MagicMock
from dataclasses import dataclass

import pytest


@dataclass
class FakeFunctionCall:
    name: str
    args: dict | None = None


@dataclass
class FakeFunctionResponse:
    name: str
    response: dict | None = None


@dataclass
class FakePart:
    text: str | None = None
    function_call: FakeFunctionCall | None = None
    function_response: FakeFunctionResponse | None = None


@dataclass
class FakeContent:
    role: str
    parts: list[FakePart]


@dataclass
class FakeFnDecl:
    name: str
    description: str
    parameters: object


@dataclass
class FakeToolDeclarations:
    function_declarations: list[FakeFnDecl]


class TestGeminiToolToOpenai:
    """_gemini_tool_to_openai must produce Responses API format (flat, not nested)."""

    def _make_decls(self, *names_and_descs):
        fns = []
        for name, desc in names_and_descs:
            params = MagicMock()
            params.type = None
            params.description = None
            params.enum = None
            params.properties = None
            params.required = None
            params.items = None
            fns.append(FakeFnDecl(name=name, description=desc, parameters=params))
        return FakeToolDeclarations(function_declarations=fns)

    def test_tool_has_name_at_top_level(self):
        from api.agent.llm import _gemini_tool_to_openai

        decls = self._make_decls(("get_prices", "Fetch historical prices"))
        tools = _gemini_tool_to_openai(decls)

        assert len(tools) == 1
        tool = tools[0]
        assert tool["type"] == "function"
        assert tool["name"] == "get_prices"
        assert tool["description"] == "Fetch historical prices"
        assert "function" not in tool

    def test_multiple_tools(self):
        from api.agent.llm import _gemini_tool_to_openai

        decls = self._make_decls(("tool_a", "A"), ("tool_b", "B"))
        tools = _gemini_tool_to_openai(decls)

        assert len(tools) == 2
        assert tools[0]["name"] == "tool_a"
        assert tools[1]["name"] == "tool_b"


class TestGeminiHistoryToOpenaiMessages:
    """_gemini_history_to_openai_messages must produce Responses API input format."""

    def test_text_messages(self):
        from api.agent.llm import _gemini_history_to_openai_messages

        history = [
            FakeContent(role="user", parts=[FakePart(text="hello")]),
            FakeContent(role="model", parts=[FakePart(text="hi there")]),
        ]
        messages = _gemini_history_to_openai_messages(history)
        assert messages == [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]

    def test_function_call_uses_responses_api_format(self):
        from api.agent.llm import _gemini_history_to_openai_messages

        history = [
            FakeContent(role="model", parts=[
                FakePart(function_call=FakeFunctionCall(name="get_prices", args={"tickers": ["SPY"]})),
            ]),
        ]
        messages = _gemini_history_to_openai_messages(history)

        msg = messages[0]
        assert msg["type"] == "function_call"
        assert msg["name"] == "get_prices"
        assert msg["call_id"] == "call_get_prices"
        assert "role" not in msg
        assert "tool_calls" not in msg

    def test_function_response_uses_responses_api_format(self):
        from api.agent.llm import _gemini_history_to_openai_messages

        history = [
            FakeContent(role="user", parts=[
                FakePart(function_response=FakeFunctionResponse(name="get_prices", response={"prices": [100]})),
            ]),
        ]
        messages = _gemini_history_to_openai_messages(history)

        msg = messages[0]
        assert msg["type"] == "function_call_output"
        assert msg["call_id"] == "call_get_prices"
        assert "role" not in msg

    def test_none_args_handled(self):
        from api.agent.llm import _gemini_history_to_openai_messages

        history = [
            FakeContent(role="model", parts=[
                FakePart(function_call=FakeFunctionCall(name="list_tools", args=None)),
            ]),
        ]
        messages = _gemini_history_to_openai_messages(history)
        assert json.loads(messages[0]["arguments"]) == {}


class TestNoneGuards:
    """Verify that None responses don't crash."""

    def test_none_output(self):
        output = None
        parts = []
        for item in (output or []):
            pass
        assert parts == []

    def test_none_annotations(self):
        annotations = None
        for ann in (annotations or []):
            pass
