"""Tests for RouterSession in-memory state management."""
import pytest
from api.agent.router_state import (
    RouterSession,
    get_session,
    update_session_portfolio,
    _sessions,
)
from api.agent.prompts import format_active_portfolio


def setup_function():
    """Clear session store before each test."""
    _sessions.clear()


def test_get_session_creates_new_for_unknown_conversation():
    session = get_session("conv-abc", messages_data=[])
    assert session.conversation_id == "conv-abc"
    assert session.active_portfolio is None


def test_get_session_returns_cached_session():
    get_session("conv-abc", messages_data=[])
    get_session("conv-abc", messages_data=[])  # second call
    # Only one session should exist
    assert len([k for k in _sessions if k == "conv-abc"]) == 1


def test_update_session_portfolio_sets_portfolio():
    get_session("conv-xyz", messages_data=[])
    portfolio = {"name": "My Book", "tickers": ["NVDA", "AMD"], "weights": [0.6, 0.4]}
    update_session_portfolio("conv-xyz", portfolio)
    session = get_session("conv-xyz", messages_data=[])
    assert session.active_portfolio == portfolio


def test_cold_start_reconstructs_from_optimize_portfolio_result():
    """On first access, reconstruct active_portfolio from stored message history."""
    messages_data = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "name": "optimize_portfolio",
                    "result": {
                        "weights": {"NVDA": 0.5, "AMD": 0.3, "INTC": 0.2},
                        "expected_return": 0.18,
                    },
                }
            ],
        }
    ]
    session = get_session("conv-cold", messages_data=messages_data)
    assert session.active_portfolio is not None
    assert session.active_portfolio["tickers"] == ["NVDA", "AMD", "INTC"]
    assert session.active_portfolio["weights"] == [0.5, 0.3, 0.2]


def test_cold_start_reconstructs_from_load_portfolio_result():
    messages_data = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "name": "load_portfolio",
                    "result": {
                        "name": "TMT Core",
                        "tickers": ["NVDA", "MSFT"],
                        "weights": [0.7, 0.3],
                    },
                }
            ],
        }
    ]
    session = get_session("conv-load", messages_data=messages_data)
    assert session.active_portfolio["name"] == "TMT Core"
    assert session.active_portfolio["tickers"] == ["NVDA", "MSFT"]


def test_cold_start_no_portfolio_tools_leaves_none():
    messages_data = [
        {"role": "user", "content": "What is NVDA trading at?"},
        {"role": "assistant", "content": "NVDA is at $875.", "tool_calls": None},
    ]
    session = get_session("conv-empty", messages_data=messages_data)
    assert session.active_portfolio is None


def test_format_active_portfolio_none_returns_empty():
    assert format_active_portfolio(None) == ""


def test_format_active_portfolio_formats_tickers_and_weights():
    portfolio = {
        "name": "TMT Core",
        "tickers": ["NVDA", "AMD", "INTC"],
        "weights": [0.5, 0.3, 0.2],
    }
    result = format_active_portfolio(portfolio)
    assert "NVDA (50.0%)" in result
    assert "AMD (30.0%)" in result
    assert "INTC (20.0%)" in result
    assert "TMT Core" in result


def test_format_active_portfolio_no_name():
    portfolio = {"name": None, "tickers": ["NVDA"], "weights": [1.0]}
    result = format_active_portfolio(portfolio)
    assert "NVDA (100.0%)" in result
    # Should not error on None name
