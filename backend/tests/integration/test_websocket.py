"""
QA-010: Tests for WebSocket Session Handler.

This module tests the WebSocket connection and message handling in backend/api/websocket.py:
- WebSocket connection establishment
- Message types (client and server)
- Session state management
- Audio chunk handling (basic)
"""

import json
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

from backend.main import app
from backend.api.websocket import (
    WebSocketManager,
    ClientMessageType,
    ServerMessageType,
    websocket_manager,
)
from backend.services.session_store import get_session_store


@pytest.fixture
def sync_client():
    """Create synchronous test client for WebSocket testing."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async HTTP client for REST API setup."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear session store before each test."""
    store = get_session_store()
    store.clear_all_sessions()
    yield
    store.clear_all_sessions()


class TestWebSocketManager:
    """Test suite for WebSocketManager class."""

    def test_websocket_manager_creation(self):
        """Test WebSocketManager can be created."""
        manager = WebSocketManager()
        assert manager is not None
        assert hasattr(manager, "_active_connections")

    def test_disconnect_removes_connection(self):
        """Test disconnect removes connection from manager."""
        manager = WebSocketManager()
        manager._active_connections["test-session"] = None
        manager.disconnect("test-session")
        assert "test-session" not in manager._active_connections

    def test_disconnect_nonexistent_session(self):
        """Test disconnecting non-existent session doesn't error."""
        manager = WebSocketManager()
        # Should not raise
        manager.disconnect("nonexistent-session")


class TestClientMessageTypes:
    """Test suite for client message type enum."""

    def test_client_message_types_exist(self):
        """Test all client message types exist."""
        assert ClientMessageType.AUDIO_CHUNK.value == "audio_chunk"
        assert ClientMessageType.START_RECORDING.value == "start_recording"
        assert ClientMessageType.PAUSE_RECORDING.value == "pause_recording"
        assert ClientMessageType.STOP_RECORDING.value == "stop_recording"
        assert ClientMessageType.PROMPT_PLAYED.value == "prompt_played"


class TestServerMessageTypes:
    """Test suite for server message type enum."""

    def test_server_message_types_exist(self):
        """Test all server message types exist."""
        assert ServerMessageType.CONNECTED.value == "connected"
        assert ServerMessageType.SESSION_STATE.value == "session_state"
        assert ServerMessageType.TRANSCRIPTION.value == "transcription"
        assert ServerMessageType.MISTAKE.value == "mistake"
        assert ServerMessageType.SELF_CORRECTION.value == "self_correction"
        assert ServerMessageType.AYAH_COMPLETE.value == "ayah_complete"
        assert ServerMessageType.SESSION_COMPLETE.value == "session_complete"
        assert ServerMessageType.ERROR.value == "error"
        assert ServerMessageType.RECORDING_STARTED.value == "recording_started"
        assert ServerMessageType.RECORDING_PAUSED.value == "recording_paused"
        assert ServerMessageType.RECORDING_STOPPED.value == "recording_stopped"


class TestWebSocketConnection:
    """Test suite for WebSocket connection."""

    @pytest.mark.asyncio
    async def test_connect_valid_session(self, sync_client, async_client):
        """Test connecting to WebSocket with valid session."""
        # Create a session first via REST API
        response = await async_client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = response.json()["session_id"]

        # Connect via WebSocket
        with sync_client.websocket_connect(f"/ws/{session_id}") as websocket:
            # Should receive connected message
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_connect_invalid_session(self, sync_client):
        """Test connecting to WebSocket with invalid session ID."""
        with pytest.raises(Exception):
            # Should fail with 4004 close code
            with sync_client.websocket_connect("/ws/nonexistent-session"):
                pass

    @pytest.mark.asyncio
    async def test_connected_message_includes_session_info(self, sync_client, async_client):
        """Test connected message includes session information."""
        response = await async_client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1, "num_ayahs": 2},
        )
        session_id = response.json()["session_id"]

        with sync_client.websocket_connect(f"/ws/{session_id}") as websocket:
            data = websocket.receive_json()

            assert "prompt_ayah" in data
            assert "expected_ayahs" in data
            assert "total_expected_words" in data
            assert data["state"] == "waiting_for_prompt_playback"


class TestWebSocketMessageHandling:
    """Test suite for WebSocket message handling."""

    @pytest.mark.asyncio
    async def test_prompt_played_message(self, sync_client, async_client):
        """Test handling prompt_played message."""
        response = await async_client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = response.json()["session_id"]

        with sync_client.websocket_connect(f"/ws/{session_id}") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send prompt_played
            websocket.send_json({"type": "prompt_played"})

            # Should receive session_state message
            data = websocket.receive_json()
            assert data["type"] == "session_state"
            assert data["state"] == "ready_to_record"

    @pytest.mark.asyncio
    async def test_start_recording_message(self, sync_client, async_client):
        """Test handling start_recording message."""
        response = await async_client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = response.json()["session_id"]

        with sync_client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.receive_json()  # connected

            # Send start_recording
            websocket.send_json({"type": "start_recording"})

            # Should receive recording_started
            data = websocket.receive_json()
            assert data["type"] == "recording_started"
            assert "timestamp_ms" in data

    @pytest.mark.asyncio
    async def test_pause_recording_message(self, sync_client, async_client):
        """Test handling pause_recording message."""
        response = await async_client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = response.json()["session_id"]

        with sync_client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.receive_json()  # connected

            # Start recording first
            websocket.send_json({"type": "start_recording"})
            websocket.receive_json()  # recording_started

            # Pause recording
            websocket.send_json({"type": "pause_recording"})

            data = websocket.receive_json()
            assert data["type"] == "recording_paused"

    @pytest.mark.asyncio
    async def test_stop_recording_message(self, sync_client, async_client):
        """Test handling stop_recording message."""
        response = await async_client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = response.json()["session_id"]

        with sync_client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.receive_json()  # connected

            # Start recording
            websocket.send_json({"type": "start_recording"})
            websocket.receive_json()  # recording_started

            # Stop recording
            websocket.send_json({"type": "stop_recording"})

            # Should receive recording_stopped and session_complete
            data1 = websocket.receive_json()
            assert data1["type"] == "recording_stopped"

            data2 = websocket.receive_json()
            assert data2["type"] == "session_complete"
            assert "summary" in data2

    @pytest.mark.asyncio
    async def test_unknown_message_type(self, sync_client, async_client):
        """Test handling unknown message type."""
        response = await async_client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = response.json()["session_id"]

        with sync_client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.receive_json()  # connected

            # Send unknown type
            websocket.send_json({"type": "unknown_message_type"})

            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Unknown message type" in data["message"]

    @pytest.mark.asyncio
    async def test_invalid_json_message(self, sync_client, async_client):
        """Test handling invalid JSON message."""
        response = await async_client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = response.json()["session_id"]

        with sync_client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.receive_json()  # connected

            # Send invalid JSON
            websocket.send_text("not valid json{")

            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Invalid JSON" in data["message"]


class TestAudioChunkHandling:
    """Test suite for audio chunk handling."""

    @pytest.mark.asyncio
    async def test_audio_chunk_requires_recording_state(self, sync_client, async_client):
        """Test audio chunks require recording state."""
        response = await async_client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = response.json()["session_id"]

        with sync_client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.receive_json()  # connected

            # Send audio chunk without starting recording
            import base64
            audio_data = base64.b64encode(b"fake audio").decode()
            websocket.send_json({
                "type": "audio_chunk",
                "data": audio_data,
                "timestamp_ms": 1000,
            })

            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Cannot process audio" in data["message"]

    @pytest.mark.asyncio
    async def test_audio_chunk_missing_data(self, sync_client, async_client):
        """Test audio chunk with missing data field."""
        response = await async_client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = response.json()["session_id"]

        with sync_client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.receive_json()  # connected

            # Start recording
            websocket.send_json({"type": "start_recording"})
            websocket.receive_json()  # recording_started

            # Send audio chunk without data
            websocket.send_json({
                "type": "audio_chunk",
                "timestamp_ms": 1000,
            })

            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "No audio data" in data["message"]

    @pytest.mark.asyncio
    async def test_audio_chunk_invalid_base64(self, sync_client, async_client):
        """Test audio chunk with invalid base64 data."""
        response = await async_client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = response.json()["session_id"]

        with sync_client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.receive_json()  # connected

            # Start recording
            websocket.send_json({"type": "start_recording"})
            websocket.receive_json()  # recording_started

            # Send invalid base64
            websocket.send_json({
                "type": "audio_chunk",
                "data": "not valid base64!!!",
                "timestamp_ms": 1000,
            })

            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Invalid audio data" in data["message"]


class TestSessionCompleteSummary:
    """Test suite for session complete summary."""

    @pytest.mark.asyncio
    async def test_session_complete_includes_summary(self, sync_client, async_client):
        """Test session complete message includes summary."""
        response = await async_client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1, "num_ayahs": 2},
        )
        session_id = response.json()["session_id"]

        with sync_client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.receive_json()  # connected

            websocket.send_json({"type": "start_recording"})
            websocket.receive_json()

            websocket.send_json({"type": "stop_recording"})
            websocket.receive_json()  # recording_stopped

            data = websocket.receive_json()  # session_complete
            summary = data["summary"]

            assert "ayahs_tested" in summary
            assert "ayahs_correct" in summary
            assert "total_words" in summary
            assert "words_correct" in summary
            assert "mistakes" in summary


class TestGlobalWebSocketManager:
    """Test suite for global WebSocket manager."""

    def test_global_manager_exists(self):
        """Test global websocket_manager exists."""
        assert websocket_manager is not None
        assert isinstance(websocket_manager, WebSocketManager)

    def test_get_websocket_manager_function(self):
        """Test get_websocket_manager function."""
        from backend.api.websocket import get_websocket_manager
        manager = get_websocket_manager()
        assert manager is websocket_manager
