"""
Session Store for the Hifdh Review App.

In-memory session storage with interface-based design for future
extensibility (Redis, Postgres, etc.).
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from models import AyahText, ReviewSession, SessionState


class SessionStoreInterface(ABC):
    """
    Abstract interface for session storage.

    Implementations can use in-memory storage (MVP), Redis, or a database.
    """

    @abstractmethod
    def create_session(
        self,
        juz_range: tuple[int, int],
        prompt_ayah: AyahText,
        expected_ayahs: list[AyahText],
        num_ayahs_to_recite: int,
    ) -> str:
        """
        Create a new review session.

        Args:
            juz_range: Tuple of (juz_start, juz_end)
            prompt_ayah: The ayah to play as a prompt
            expected_ayahs: The expected continuation ayahs
            num_ayahs_to_recite: Number of ayahs the user should recite

        Returns:
            The session ID.
        """
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[ReviewSession]:
        """
        Get a session by ID.

        Args:
            session_id: The session ID

        Returns:
            The ReviewSession if found, None otherwise.
        """
        pass

    @abstractmethod
    def update_session(self, session_id: str, updates: dict[str, Any]) -> bool:
        """
        Update a session with the given field updates.

        Args:
            session_id: The session ID
            updates: Dictionary of field names to new values

        Returns:
            True if update was successful, False if session not found.
        """
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID

        Returns:
            True if deletion was successful, False if session not found.
        """
        pass


class SessionStore(SessionStoreInterface):
    """
    In-memory session store implementation.

    Stores sessions in a dictionary. Suitable for MVP and single-instance
    deployments. For production, replace with Redis or database-backed
    implementation.
    """

    def __init__(self):
        """Initialize the in-memory session store."""
        self._sessions: dict[str, ReviewSession] = {}

    def create_session(
        self,
        juz_range: tuple[int, int],
        prompt_ayah: AyahText,
        expected_ayahs: list[AyahText],
        num_ayahs_to_recite: int,
    ) -> str:
        """
        Create a new review session.

        Args:
            juz_range: Tuple of (juz_start, juz_end)
            prompt_ayah: The ayah to play as a prompt
            expected_ayahs: The expected continuation ayahs
            num_ayahs_to_recite: Number of ayahs the user should recite

        Returns:
            The session ID.
        """
        session_id = str(uuid.uuid4())

        # Flatten expected tokens from all ayahs
        expected_tokens: list[str] = []
        for ayah in expected_ayahs:
            expected_tokens.extend(ayah.text_tokens)

        session = ReviewSession(
            id=session_id,
            state=SessionState.WAITING_FOR_PROMPT_PLAYBACK,
            juz_range=juz_range,
            num_ayahs_to_recite=num_ayahs_to_recite,
            prompt_ayah=prompt_ayah,
            expected_ayahs=expected_ayahs,
            expected_tokens=expected_tokens,
        )

        self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[ReviewSession]:
        """
        Get a session by ID.

        Args:
            session_id: The session ID

        Returns:
            The ReviewSession if found, None otherwise.
        """
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, updates: dict[str, Any]) -> bool:
        """
        Update a session with the given field updates.

        Args:
            session_id: The session ID
            updates: Dictionary of field names to new values

        Returns:
            True if update was successful, False if session not found.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False

        for field, value in updates.items():
            if hasattr(session, field):
                setattr(session, field, value)
            else:
                raise ValueError(f"Invalid session field: {field}")

        return True

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID

        Returns:
            True if deletion was successful, False if session not found.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def set_session_state(self, session_id: str, state: SessionState) -> bool:
        """
        Convenience method to update session state.

        Args:
            session_id: The session ID
            state: The new SessionState

        Returns:
            True if update was successful, False if session not found.
        """
        return self.update_session(session_id, {"state": state})

    def start_recording(self, session_id: str) -> bool:
        """
        Mark a session as recording and set the start timestamp.

        Args:
            session_id: The session ID

        Returns:
            True if update was successful, False if session not found.
        """
        import time

        return self.update_session(
            session_id,
            {
                "state": SessionState.RECORDING,
                "recording_started_at": time.time(),
            },
        )

    def update_last_chunk_time(self, session_id: str) -> bool:
        """
        Update the last chunk timestamp for a session.

        Args:
            session_id: The session ID

        Returns:
            True if update was successful, False if session not found.
        """
        import time

        return self.update_session(session_id, {"last_chunk_at": time.time()})

    def get_all_sessions(self) -> list[ReviewSession]:
        """
        Get all active sessions.

        Returns:
            List of all ReviewSession objects.
        """
        return list(self._sessions.values())

    def count_sessions(self) -> int:
        """
        Get the number of active sessions.

        Returns:
            Number of sessions currently stored.
        """
        return len(self._sessions)

    def clear_all_sessions(self) -> int:
        """
        Clear all sessions (for testing/cleanup).

        Returns:
            Number of sessions that were cleared.
        """
        count = len(self._sessions)
        self._sessions.clear()
        return count


# Singleton instance for app-wide use
_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """
    Get the singleton SessionStore instance.

    Creates the instance on first call.
    """
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
