"""
WebSocket handler for the Hifdh Review App.

Handles real-time audio streaming and feedback for recitation sessions.
"""

import base64
import json
import time
from dataclasses import asdict
from enum import Enum
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from models import (
    AyahText,
    Mistake,
    MistakeType,
    ReviewSession,
    SessionState,
)
from services.session_store import get_session_store
from services.transcription_handler import TranscriptionHandler


websocket_router = APIRouter()


class ClientMessageType(str, Enum):
    """Types of messages the client can send."""
    AUDIO_CHUNK = "audio_chunk"
    START_RECORDING = "start_recording"
    PAUSE_RECORDING = "pause_recording"
    STOP_RECORDING = "stop_recording"
    PROMPT_PLAYED = "prompt_played"  # Client signals prompt audio finished


class ServerMessageType(str, Enum):
    """Types of messages the server can send."""
    CONNECTED = "connected"
    SESSION_STATE = "session_state"
    TRANSCRIPTION = "transcription"
    MISTAKE = "mistake"
    SELF_CORRECTION = "self_correction"
    AYAH_COMPLETE = "ayah_complete"
    SESSION_COMPLETE = "session_complete"
    ERROR = "error"
    RECORDING_STARTED = "recording_started"
    RECORDING_PAUSED = "recording_paused"
    RECORDING_STOPPED = "recording_stopped"


class WebSocketManager:
    """
    Manages WebSocket connections for review sessions.

    Handles audio streaming, state management, and feedback emission.
    """

    def __init__(self):
        """Initialize the WebSocket manager."""
        self._active_connections: dict[str, WebSocket] = {}  # session_id -> websocket
        self._transcription_handlers: dict[str, TranscriptionHandler] = {}  # session_id -> handler

    async def connect(self, session_id: str, websocket: WebSocket) -> bool:
        """
        Accept a WebSocket connection for a session.

        Args:
            session_id: The session ID
            websocket: The WebSocket connection

        Returns:
            True if connection was successful, False if session not found.
        """
        session_store = get_session_store()
        session = session_store.get_session(session_id)

        if session is None:
            await websocket.close(code=4004, reason="Session not found")
            return False

        await websocket.accept()
        self._active_connections[session_id] = websocket

        # Send connected message with session state
        await self.send_message(
            session_id,
            ServerMessageType.CONNECTED,
            {
                "session_id": session_id,
                "state": session.state.value,
                "prompt_ayah": self._ayah_to_dict(session.prompt_ayah),
                "expected_ayahs": [self._ayah_to_dict(a) for a in session.expected_ayahs],
                "total_expected_words": len(session.expected_tokens),
            },
        )

        return True

    def disconnect(self, session_id: str) -> None:
        """
        Handle WebSocket disconnection.

        Args:
            session_id: The session ID
        """
        if session_id in self._active_connections:
            del self._active_connections[session_id]
        # Clean up transcription handler
        if session_id in self._transcription_handlers:
            del self._transcription_handlers[session_id]

    async def send_message(
        self, session_id: str, message_type: ServerMessageType, data: dict
    ) -> bool:
        """
        Send a message to the client.

        Args:
            session_id: The session ID
            message_type: Type of message to send
            data: Message payload

        Returns:
            True if message was sent, False if no active connection.
        """
        websocket = self._active_connections.get(session_id)
        if websocket is None:
            return False

        message = {"type": message_type.value, **data}
        await websocket.send_json(message)
        return True

    async def handle_message(self, session_id: str, message: dict) -> None:
        """
        Handle an incoming message from the client.

        Args:
            session_id: The session ID
            message: The parsed JSON message
        """
        message_type = message.get("type")

        if message_type == ClientMessageType.AUDIO_CHUNK.value:
            await self._handle_audio_chunk(session_id, message)
        elif message_type == ClientMessageType.START_RECORDING.value:
            await self._handle_start_recording(session_id)
        elif message_type == ClientMessageType.PAUSE_RECORDING.value:
            await self._handle_pause_recording(session_id)
        elif message_type == ClientMessageType.STOP_RECORDING.value:
            await self._handle_stop_recording(session_id)
        elif message_type == ClientMessageType.PROMPT_PLAYED.value:
            await self._handle_prompt_played(session_id)
        else:
            await self.send_message(
                session_id,
                ServerMessageType.ERROR,
                {"message": f"Unknown message type: {message_type}"},
            )

    async def _handle_prompt_played(self, session_id: str) -> None:
        """Handle client signaling that prompt audio has finished playing."""
        session_store = get_session_store()
        session = session_store.get_session(session_id)

        if session is None:
            return

        # Session is ready for recording
        await self.send_message(
            session_id,
            ServerMessageType.SESSION_STATE,
            {"state": "ready_to_record"},
        )

    async def _handle_start_recording(self, session_id: str) -> None:
        """Handle start recording request."""
        session_store = get_session_store()
        session = session_store.get_session(session_id)

        if session is None:
            await self.send_message(
                session_id,
                ServerMessageType.ERROR,
                {"message": "Session not found"},
            )
            return

        if session_store.start_recording(session_id):
            # Create transcription handler for this session
            self._transcription_handlers[session_id] = TranscriptionHandler(
                expected_ayahs=session.expected_ayahs,
                on_transcription=lambda confirmed, tentative: self._on_transcription(session_id, confirmed, tentative),
                on_mistake=lambda mistake: self._on_mistake(session_id, mistake),
                on_ayah_complete=lambda ayah, correct, total: self._on_ayah_complete(session_id, ayah, correct, total),
            )

            await self.send_message(
                session_id,
                ServerMessageType.RECORDING_STARTED,
                {"timestamp_ms": int(time.time() * 1000)},
            )
        else:
            await self.send_message(
                session_id,
                ServerMessageType.ERROR,
                {"message": "Failed to start recording"},
            )

    async def _on_transcription(self, session_id: str, confirmed: list, tentative: list) -> None:
        """Callback for transcription updates."""
        await self.emit_transcription(session_id, confirmed, tentative)

    async def _on_mistake(self, session_id: str, mistake: Mistake) -> None:
        """Callback for mistake detection."""
        await self.emit_mistake(session_id, mistake)

    async def _on_ayah_complete(self, session_id: str, ayah: AyahText, correct: int, total: int) -> None:
        """Callback for ayah completion."""
        await self.emit_ayah_complete(session_id, ayah, correct, total)

    async def _handle_pause_recording(self, session_id: str) -> None:
        """Handle pause recording request."""
        session_store = get_session_store()

        if session_store.set_session_state(session_id, SessionState.USER_PAUSED):
            await self.send_message(
                session_id,
                ServerMessageType.RECORDING_PAUSED,
                {"timestamp_ms": int(time.time() * 1000)},
            )
        else:
            await self.send_message(
                session_id,
                ServerMessageType.ERROR,
                {"message": "Failed to pause recording"},
            )

    async def _handle_stop_recording(self, session_id: str) -> None:
        """Handle stop recording request."""
        session_store = get_session_store()
        session = session_store.get_session(session_id)

        if session is None:
            await self.send_message(
                session_id,
                ServerMessageType.ERROR,
                {"message": "Session not found"},
            )
            return

        # Send recording stopped first
        await self.send_message(
            session_id,
            ServerMessageType.RECORDING_STOPPED,
            {"timestamp_ms": int(time.time() * 1000)},
        )

        # Get handler and run final transcription BEFORE marking complete
        handler = self._transcription_handlers.get(session_id)
        if handler:
            # Force final transcription of any remaining audio
            print(f"[WS] Running final transcription for session {session_id}")
            await handler.finalize()

            # Get summary from handler (with all mistakes)
            summary = handler.get_summary()
            print(f"[WS] Session summary: {summary['words_correct']}/{summary['total_words']} words correct, {len(summary['mistakes'])} mistakes")
            # Update session mistakes from handler
            session_store.update_session(session_id, {"mistakes": summary["mistakes"]})

        # NOW mark session as complete (after processing is done)
        session_store.set_session_state(session_id, SessionState.COMPLETE)

        # Refresh session to get updated mistakes
        session = session_store.get_session(session_id)

        # Send session summary LAST
        await self._send_session_complete(session_id, session)

    async def _handle_audio_chunk(self, session_id: str, message: dict) -> None:
        """
        Handle an incoming audio chunk.

        This is the main entry point for processing audio during recitation.
        The audio is forwarded to the transcription pipeline (to be implemented
        in the ML components).

        Args:
            session_id: The session ID
            message: Message containing audio data
        """
        session_store = get_session_store()
        session = session_store.get_session(session_id)

        if session is None:
            await self.send_message(
                session_id,
                ServerMessageType.ERROR,
                {"message": "Session not found"},
            )
            return

        if session.state != SessionState.RECORDING:
            await self.send_message(
                session_id,
                ServerMessageType.ERROR,
                {"message": f"Cannot process audio in state: {session.state.value}"},
            )
            return

        # Update last chunk timestamp
        session_store.update_last_chunk_time(session_id)

        # Extract audio data
        audio_data = message.get("data")
        timestamp_ms = message.get("timestamp_ms", int(time.time() * 1000))
        is_final = message.get("is_final", False)

        if audio_data is None:
            await self.send_message(
                session_id,
                ServerMessageType.ERROR,
                {"message": "No audio data in chunk"},
            )
            return

        # Decode base64 audio
        try:
            audio_bytes = base64.b64decode(audio_data)
        except Exception as e:
            await self.send_message(
                session_id,
                ServerMessageType.ERROR,
                {"message": f"Invalid audio data: {str(e)}"},
            )
            return

        # Forward to transcription handler for processing
        handler = self._transcription_handlers.get(session_id)
        if handler:
            await handler.process_audio_chunk(audio_bytes)
        else:
            # No handler - shouldn't happen if start_recording was called
            await self.send_message(
                session_id,
                ServerMessageType.ERROR,
                {"message": "No transcription handler - did you start recording?"},
            )

    async def emit_transcription(
        self,
        session_id: str,
        confirmed_words: list[dict],
        tentative_words: list[dict],
    ) -> None:
        """
        Emit a transcription update to the client.

        Called by the transcription pipeline when new words are available.

        Args:
            session_id: The session ID
            confirmed_words: List of confirmed word dicts with status
            tentative_words: List of tentative word dicts
        """
        print(f"[WS] Emitting transcription: {len(confirmed_words)} confirmed, {len(tentative_words)} tentative")
        await self.send_message(
            session_id,
            ServerMessageType.TRANSCRIPTION,
            {
                "confirmed_words": confirmed_words,
                "tentative_words": tentative_words,
            },
        )

    async def emit_mistake(self, session_id: str, mistake: Mistake) -> None:
        """
        Emit a mistake detection to the client.

        Called by the feedback engine when a mistake is confirmed.

        Args:
            session_id: The session ID
            mistake: The Mistake object
        """
        await self.send_message(
            session_id,
            ServerMessageType.MISTAKE,
            {
                "mistake_type": mistake.mistake_type.value,
                "word_index": mistake.word_index,
                "expected": mistake.expected,
                "received": mistake.received,
                "confidence": mistake.confidence,
                "is_penalty": mistake.is_penalty,
                "ayah": [mistake.ayah[0], mistake.ayah[1]],
            },
        )

    async def emit_self_correction(
        self, session_id: str, word_index: int, message: str = "You corrected yourself - no penalty"
    ) -> None:
        """
        Emit a self-correction notification to the client.

        Args:
            session_id: The session ID
            word_index: Index of the corrected word
            message: User-friendly message
        """
        await self.send_message(
            session_id,
            ServerMessageType.SELF_CORRECTION,
            {"word_index": word_index, "message": message},
        )

    async def emit_ayah_complete(
        self,
        session_id: str,
        ayah: AyahText,
        words_correct: int,
        words_total: int,
    ) -> None:
        """
        Emit ayah completion notification.

        Called when the user has completed reciting an ayah.

        Args:
            session_id: The session ID
            ayah: The completed ayah
            words_correct: Number of correct words
            words_total: Total words in the ayah
        """
        status = "correct" if words_correct == words_total else "has_mistakes"

        await self.send_message(
            session_id,
            ServerMessageType.AYAH_COMPLETE,
            {
                "ayah": {"surah": ayah.surah, "ayah": ayah.ayah},
                "status": status,
                "words_correct": words_correct,
                "words_total": words_total,
            },
        )

    async def _send_session_complete(self, session_id: str, session: ReviewSession) -> None:
        """
        Send session completion summary.

        Args:
            session_id: The session ID
            session: The session object
        """
        # Calculate summary statistics
        total_words = len(session.expected_tokens)
        mistake_penalties = sum(1 for m in session.mistakes if m.is_penalty)
        words_correct = total_words - mistake_penalties

        # Serialize mistakes
        mistakes_data = [
            {
                "mistake_type": m.mistake_type.value,
                "ayah": [m.ayah[0], m.ayah[1]],
                "word_index": m.word_index,
                "expected": m.expected,
                "received": m.received,
                "confidence": m.confidence,
                "is_penalty": m.is_penalty,
            }
            for m in session.mistakes
        ]

        # Calculate ayahs correct (an ayah is correct if it has no penalty mistakes)
        ayah_mistakes: dict[tuple[int, int], int] = {}
        for m in session.mistakes:
            if m.is_penalty:
                ayah_mistakes[m.ayah] = ayah_mistakes.get(m.ayah, 0) + 1

        ayahs_tested = len(session.expected_ayahs)
        ayahs_correct = ayahs_tested - len(ayah_mistakes)

        await self.send_message(
            session_id,
            ServerMessageType.SESSION_COMPLETE,
            {
                "summary": {
                    "ayahs_tested": ayahs_tested,
                    "ayahs_correct": ayahs_correct,
                    "total_words": total_words,
                    "words_correct": words_correct,
                    "mistakes": mistakes_data,
                }
            },
        )

    def _ayah_to_dict(self, ayah: AyahText) -> dict:
        """Convert an AyahText to a dictionary for JSON serialization."""
        return {
            "surah": ayah.surah,
            "ayah": ayah.ayah,
            "juz": ayah.juz,
            "text_uthmani": ayah.text_uthmani,
            "text_normalized": ayah.text_normalized,
            "text_tokens": ayah.text_tokens,
            "audio_url": ayah.audio_url,
        }


# Singleton WebSocket manager
websocket_manager = WebSocketManager()


@websocket_router.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for audio streaming.

    Handles bidirectional communication for:
    - Receiving audio chunks from client
    - Sending transcription updates
    - Sending mistake notifications
    - Sending session state updates
    """
    if not await websocket_manager.connect(session_id, websocket):
        return

    try:
        while True:
            # Receive message (can be text or binary)
            ws_message = await websocket.receive()

            # Handle text messages (JSON commands)
            if "text" in ws_message:
                data = ws_message["text"]
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    await websocket_manager.send_message(
                        session_id,
                        ServerMessageType.ERROR,
                        {"message": "Invalid JSON message"},
                    )
                    continue

                # Handle the message
                try:
                    await websocket_manager.handle_message(session_id, message)
                except Exception as e:
                    print(f"Error handling message: {e}")
                    import traceback
                    traceback.print_exc()
                    await websocket_manager.send_message(
                        session_id,
                        ServerMessageType.ERROR,
                        {"message": f"Server error: {str(e)}"},
                    )

            # Handle binary messages (audio data)
            elif "bytes" in ws_message:
                audio_bytes = ws_message["bytes"]
                # Process binary audio through transcription handler
                handler = websocket_manager._transcription_handlers.get(session_id)
                if handler:
                    try:
                        await handler.process_audio_chunk(audio_bytes)
                    except Exception as e:
                        print(f"Error processing audio: {e}")
                        import traceback
                        traceback.print_exc()

            # Handle disconnect
            elif ws_message.get("type") == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        websocket_manager.disconnect(session_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        websocket_manager.disconnect(session_id)


def get_websocket_manager() -> WebSocketManager:
    """Get the singleton WebSocket manager instance."""
    return websocket_manager
