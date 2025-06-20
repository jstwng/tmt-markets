"""In-memory conversation session store for multi-turn Gemini chats."""

import asyncio
import time
import uuid
from dataclasses import dataclass, field

from google.genai import types as genai_types

__all__ = ["SessionStore", "session_store"]

_SESSION_TTL_SECONDS = 3600  # 1 hour


@dataclass
class Session:
    """A single conversation session.

    Attributes:
        session_id: Unique identifier.
        history: Ordered list of Gemini Content objects (the conversation).
        created_at: Unix timestamp of creation.
        last_used: Unix timestamp of last access.
    """
    session_id: str
    history: list[genai_types.Content] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.last_used = time.time()

    def is_expired(self) -> bool:
        return time.time() - self.last_used > _SESSION_TTL_SECONDS


class SessionStore:
    """Thread-safe in-memory store for conversation sessions.

    Sessions expire after 1 hour of inactivity. Expired sessions are
    purged lazily on access and proactively on create/delete calls.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def create_session(self) -> str:
        """Create a new empty session and return its ID."""
        async with self._lock:
            self._purge_expired()
            session_id = str(uuid.uuid4())
            self._sessions[session_id] = Session(session_id=session_id)
            return session_id

    async def get_session(self, session_id: str) -> Session:
        """Retrieve a session by ID, updating its last_used timestamp.

        Raises:
            KeyError: If the session does not exist or has expired.
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.is_expired():
                if session is not None:
                    del self._sessions[session_id]
                raise KeyError(f"Session '{session_id}' not found or expired")
            session.touch()
            return session

    async def delete_session(self, session_id: str) -> None:
        """Delete a session. No-op if it doesn't exist."""
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def get_or_create(self, session_id: str | None) -> Session:
        """Get an existing session or create a new one.

        If session_id is None or the session is expired, creates a fresh session.
        Returns the session (caller should check session.session_id for the actual ID).
        """
        if session_id is not None:
            try:
                return await self.get_session(session_id)
            except KeyError:
                pass
        # Create new session
        new_id = await self.create_session()
        return await self.get_session(new_id)

    def _purge_expired(self) -> None:
        """Remove all expired sessions. Must be called with lock held."""
        expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired:
            del self._sessions[sid]


# Module-level singleton
session_store = SessionStore()
