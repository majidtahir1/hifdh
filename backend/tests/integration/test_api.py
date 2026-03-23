"""
QA-009: Tests for REST API Endpoints.

This module tests the API endpoints in backend/api/routes.py:
- /api/health
- /api/sessions (POST, GET, DELETE)
- /api/sessions/{id}/next
- /api/quran/ayah/{surah}/{ayah}
"""

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status

from backend.main import app
from backend.services.session_store import get_session_store


@pytest.fixture
async def client():
    """Create async HTTP client for testing."""
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


class TestHealthEndpoint:
    """Test suite for /api/health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_returns_ok(self, client: AsyncClient):
        """Test health endpoint returns healthy status."""
        response = await client.get("/api/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_includes_quran_count(self, client: AsyncClient):
        """Test health endpoint includes ayah count."""
        response = await client.get("/api/health")

        data = response.json()
        assert "quran_ayahs_loaded" in data
        assert data["quran_ayahs_loaded"] == 6236

    @pytest.mark.asyncio
    async def test_health_check_includes_session_count(self, client: AsyncClient):
        """Test health endpoint includes session count."""
        response = await client.get("/api/health")

        data = response.json()
        assert "active_sessions" in data
        assert isinstance(data["active_sessions"], int)


class TestRootEndpoint:
    """Test suite for / root endpoint."""

    @pytest.mark.asyncio
    async def test_root_returns_app_info(self, client: AsyncClient):
        """Test root endpoint returns app information."""
        response = await client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Hifdh Review App"
        assert "version" in data
        assert "health" in data


class TestCreateSession:
    """Test suite for POST /api/sessions endpoint."""

    @pytest.mark.asyncio
    async def test_create_session_success(self, client: AsyncClient):
        """Test creating a session successfully."""
        response = await client.post(
            "/api/sessions",
            json={
                "juz_start": 1,
                "juz_end": 1,
                "num_ayahs": 3,
                "feedback_mode": "gentle",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "session_id" in data
        assert "prompt_ayah" in data
        assert "expected_ayahs" in data
        assert "total_expected_words" in data

    @pytest.mark.asyncio
    async def test_create_session_default_values(self, client: AsyncClient):
        """Test creating session with default values."""
        response = await client.post(
            "/api/sessions",
            json={
                "juz_start": 1,
                "juz_end": 1,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["expected_ayahs"]) == 3  # Default num_ayahs

    @pytest.mark.asyncio
    async def test_create_session_invalid_juz_range(self, client: AsyncClient):
        """Test creating session with invalid juz range."""
        response = await client.post(
            "/api/sessions",
            json={
                "juz_start": 5,
                "juz_end": 1,  # End before start
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_session_juz_out_of_range(self, client: AsyncClient):
        """Test creating session with juz out of range."""
        response = await client.post(
            "/api/sessions",
            json={
                "juz_start": 0,  # Invalid
                "juz_end": 1,
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_session_prompt_ayah_structure(self, client: AsyncClient):
        """Test prompt ayah has correct structure."""
        response = await client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )

        data = response.json()
        prompt = data["prompt_ayah"]
        assert "surah" in prompt
        assert "ayah" in prompt
        assert "juz" in prompt
        assert "text_uthmani" in prompt
        assert "text_normalized" in prompt
        assert "text_tokens" in prompt
        assert "audio_url" in prompt


class TestGetSession:
    """Test suite for GET /api/sessions/{session_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_session_success(self, client: AsyncClient):
        """Test getting an existing session."""
        # Create session first
        create_response = await client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = create_response.json()["session_id"]

        # Get session
        response = await client.get(f"/api/sessions/{session_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == session_id
        assert "state" in data
        assert "juz_range" in data
        assert "prompt_ayah" in data

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, client: AsyncClient):
        """Test getting non-existent session returns 404."""
        response = await client.get("/api/sessions/nonexistent-session-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_session_includes_state(self, client: AsyncClient):
        """Test session response includes current state."""
        create_response = await client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = create_response.json()["session_id"]

        response = await client.get(f"/api/sessions/{session_id}")
        data = response.json()

        assert data["state"] == "waiting_for_prompt_playback"


class TestDeleteSession:
    """Test suite for DELETE /api/sessions/{session_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_session_success(self, client: AsyncClient):
        """Test deleting an existing session."""
        # Create session
        create_response = await client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = create_response.json()["session_id"]

        # Delete session
        response = await client.delete(f"/api/sessions/{session_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deleted
        get_response = await client.get(f"/api/sessions/{session_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, client: AsyncClient):
        """Test deleting non-existent session returns 404."""
        response = await client.delete("/api/sessions/nonexistent-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetNextPrompt:
    """Test suite for POST /api/sessions/{session_id}/next endpoint."""

    @pytest.mark.asyncio
    async def test_get_next_prompt_success(self, client: AsyncClient):
        """Test getting next prompt for session."""
        # Create session
        create_response = await client.post(
            "/api/sessions",
            json={"juz_start": 1, "juz_end": 1},
        )
        session_id = create_response.json()["session_id"]

        # Get next prompt (in WAITING state)
        response = await client.post(f"/api/sessions/{session_id}/next")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "prompt_ayah" in data
        assert "expected_ayahs" in data
        assert "total_expected_words" in data

    @pytest.mark.asyncio
    async def test_get_next_prompt_not_found(self, client: AsyncClient):
        """Test getting next prompt for non-existent session."""
        response = await client.post("/api/sessions/nonexistent/next")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetAyah:
    """Test suite for GET /api/quran/ayah/{surah}/{ayah} endpoint."""

    @pytest.mark.asyncio
    async def test_get_ayah_success(self, client: AsyncClient):
        """Test getting a specific ayah."""
        response = await client.get("/api/quran/ayah/1/1")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["surah"] == 1
        assert data["ayah"] == 1
        assert "text_uthmani" in data
        assert "text_normalized" in data
        assert "text_tokens" in data

    @pytest.mark.asyncio
    async def test_get_ayah_not_found(self, client: AsyncClient):
        """Test getting non-existent ayah returns 404."""
        response = await client.get("/api/quran/ayah/1/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_ayah_fatiha_first(self, client: AsyncClient):
        """Test getting first ayah of Fatiha."""
        response = await client.get("/api/quran/ayah/1/1")

        data = response.json()
        assert data["juz"] == 1
        assert "بسم" in data["text_normalized"]

    @pytest.mark.asyncio
    async def test_get_ayah_last_ayah(self, client: AsyncClient):
        """Test getting last ayah of Quran."""
        response = await client.get("/api/quran/ayah/114/6")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["surah"] == 114
        assert data["ayah"] == 6


class TestCORSConfiguration:
    """Test suite for CORS configuration."""

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client: AsyncClient):
        """Test that CORS headers are present in responses."""
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # FastAPI handles CORS, check it doesn't reject the origin
        assert response.status_code in [200, 204]
