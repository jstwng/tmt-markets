"""Router session state: tracks active portfolio per conversation.

In-memory dict keyed by conversation_id. Reconstructed from DB message history
on cold start (e.g. after server restart).
"""
from dataclasses import dataclass, field


@dataclass
class RouterSession:
    """Per-conversation router state."""
    conversation_id: str
    active_portfolio: dict | None = None
    # active_portfolio shape: {name: str, tickers: list[str], weights: list[float]}


# Module-level store: lives for server process lifetime
_sessions: dict[str, RouterSession] = {}


def get_session(conversation_id: str, messages_data: list[dict]) -> RouterSession:
    """Return existing session or reconstruct from message history on cold start."""
    if conversation_id in _sessions:
        return _sessions[conversation_id]

    session = RouterSession(conversation_id=conversation_id)
    session.active_portfolio = _reconstruct_portfolio(messages_data)
    _sessions[conversation_id] = session
    return session


def update_session_portfolio(conversation_id: str, portfolio: dict) -> None:
    """Update the active portfolio for a conversation."""
    if conversation_id in _sessions:
        _sessions[conversation_id].active_portfolio = portfolio


def _reconstruct_portfolio(messages_data: list[dict]) -> dict | None:
    """Scan message history (newest first) for the most recent portfolio tool result."""
    for msg in reversed(messages_data):
        for tc in (msg.get("tool_calls") or []):
            name = tc.get("name")
            result = tc.get("result") or {}

            if name == "optimize_portfolio" and "weights" in result:
                weights_dict: dict = result["weights"]
                return {
                    "name": None,
                    "tickers": list(weights_dict.keys()),
                    "weights": list(weights_dict.values()),
                }

            if name == "load_portfolio" and "tickers" in result:
                return {
                    "name": result.get("name"),
                    "tickers": result["tickers"],
                    "weights": result.get("weights", []),
                }

    return None
