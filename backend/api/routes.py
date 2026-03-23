"""
REST API routes for the Hifdh Review App.

Provides endpoints for:
- Session creation and management
- Ayah retrieval
- Next prompt generation
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from models import AyahText, ReviewSession, SessionState
from services.quran_data import get_quran_service
from services.session_store import get_session_store


router = APIRouter(prefix="/api", tags=["sessions"])


# Request/Response models using Pydantic for validation

class CreateSessionRequest(BaseModel):
    """Request body for creating a new session."""
    juz_start: int = Field(..., ge=1, le=30, description="Starting juz (inclusive)")
    juz_end: int = Field(..., ge=1, le=30, description="Ending juz (inclusive)")
    num_ayahs: int = Field(default=3, ge=1, le=20, description="Number of ayahs to recite")
    feedback_mode: str = Field(default="gentle", description="Feedback mode: immediate, gentle, post_ayah, post_session")


class AyahResponse(BaseModel):
    """Ayah data for API responses."""
    surah: int
    ayah: int
    juz: int
    text_uthmani: str
    text_normalized: str
    text_tokens: list[str]
    audio_url: str

    @classmethod
    def from_ayah_text(cls, ayah: AyahText) -> "AyahResponse":
        """Convert an AyahText to an AyahResponse."""
        return cls(
            surah=ayah.surah,
            ayah=ayah.ayah,
            juz=ayah.juz,
            text_uthmani=ayah.text_uthmani,
            text_normalized=ayah.text_normalized,
            text_tokens=ayah.text_tokens,
            audio_url=ayah.audio_url,
        )


class CreateSessionResponse(BaseModel):
    """Response body for session creation."""
    session_id: str
    prompt_ayah: AyahResponse
    expected_ayahs: list[AyahResponse]
    total_expected_words: int


class SessionStateResponse(BaseModel):
    """Response body for session state."""
    session_id: str
    state: str
    juz_range: tuple[int, int]
    num_ayahs_to_recite: int
    prompt_ayah: AyahResponse
    expected_ayahs: list[AyahResponse]
    total_expected_words: int
    confirmed_word_index: int
    tentative_word_index: int
    mistakes_count: int


class NextPromptResponse(BaseModel):
    """Response body for getting the next prompt."""
    prompt_ayah: AyahResponse
    expected_ayahs: list[AyahResponse]
    total_expected_words: int


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str


# API Endpoints

@router.post(
    "/sessions",
    response_model=CreateSessionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
    },
)
async def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
    """
    Create a new review session.

    Selects a random ayah from the specified juz range and prepares
    the expected continuation for recitation.
    """
    # Validate juz range
    if request.juz_start > request.juz_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"juz_start ({request.juz_start}) cannot be greater than juz_end ({request.juz_end})",
        )

    quran_service = get_quran_service()
    session_store = get_session_store()

    # Get random prompt ayah
    try:
        prompt_ayah = quran_service.get_random_ayah(request.juz_start, request.juz_end)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Get expected continuation
    try:
        expected_ayahs = quran_service.get_expected_continuation(prompt_ayah, request.num_ayahs)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Create session
    session_id = session_store.create_session(
        juz_range=(request.juz_start, request.juz_end),
        prompt_ayah=prompt_ayah,
        expected_ayahs=expected_ayahs,
        num_ayahs_to_recite=request.num_ayahs,
    )

    # Calculate total expected words
    total_words = sum(len(ayah.text_tokens) for ayah in expected_ayahs)

    return CreateSessionResponse(
        session_id=session_id,
        prompt_ayah=AyahResponse.from_ayah_text(prompt_ayah),
        expected_ayahs=[AyahResponse.from_ayah_text(a) for a in expected_ayahs],
        total_expected_words=total_words,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionStateResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
    },
)
async def get_session(session_id: str) -> SessionStateResponse:
    """
    Get the current state of a session.

    Returns session configuration, current position, and mistake count.
    """
    session_store = get_session_store()
    session = session_store.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return SessionStateResponse(
        session_id=session.id,
        state=session.state.value,
        juz_range=session.juz_range,
        num_ayahs_to_recite=session.num_ayahs_to_recite,
        prompt_ayah=AyahResponse.from_ayah_text(session.prompt_ayah),
        expected_ayahs=[AyahResponse.from_ayah_text(a) for a in session.expected_ayahs],
        total_expected_words=len(session.expected_tokens),
        confirmed_word_index=session.confirmed_word_index,
        tentative_word_index=session.tentative_word_index,
        mistakes_count=len(session.mistakes),
    )


@router.post(
    "/sessions/{session_id}/next",
    response_model=NextPromptResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        400: {"model": ErrorResponse, "description": "Invalid session state"},
    },
)
async def get_next_prompt(session_id: str) -> NextPromptResponse:
    """
    Get the next prompt ayah for a session.

    This endpoint is called after completing a round to get a new random
    prompt within the session's juz range.
    """
    session_store = get_session_store()
    session = session_store.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Session should be complete or just started
    if session.state not in (SessionState.COMPLETE, SessionState.WAITING_FOR_PROMPT_PLAYBACK):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot get next prompt in state: {session.state.value}",
        )

    quran_service = get_quran_service()

    # Get new random prompt
    juz_start, juz_end = session.juz_range
    prompt_ayah = quran_service.get_random_ayah(juz_start, juz_end)
    expected_ayahs = quran_service.get_expected_continuation(prompt_ayah, session.num_ayahs_to_recite)

    # Flatten expected tokens
    expected_tokens: list[str] = []
    for ayah in expected_ayahs:
        expected_tokens.extend(ayah.text_tokens)

    # Update session with new prompt
    session_store.update_session(
        session_id,
        {
            "state": SessionState.WAITING_FOR_PROMPT_PLAYBACK,
            "prompt_ayah": prompt_ayah,
            "expected_ayahs": expected_ayahs,
            "expected_tokens": expected_tokens,
            "confirmed_word_index": 0,
            "tentative_word_index": 0,
            "last_stable_alignment": 0,
            "confirmed_transcript": [],
            "tentative_transcript": [],
            "mistakes": [],
            "low_confidence_counter": 0,
            "recording_started_at": None,
            "last_chunk_at": None,
        },
    )

    total_words = len(expected_tokens)

    return NextPromptResponse(
        prompt_ayah=AyahResponse.from_ayah_text(prompt_ayah),
        expected_ayahs=[AyahResponse.from_ayah_text(a) for a in expected_ayahs],
        total_expected_words=total_words,
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
    },
)
async def delete_session(session_id: str) -> None:
    """
    Delete a session.

    Cleans up session resources. Called when user ends a review session.
    """
    session_store = get_session_store()

    if not session_store.delete_session(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )


@router.get(
    "/quran/ayah/{surah}/{ayah}",
    response_model=AyahResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Ayah not found"},
    },
)
async def get_ayah(surah: int, ayah: int) -> AyahResponse:
    """
    Get a specific ayah by surah and ayah number.

    Returns all three text forms plus the audio URL.
    """
    quran_service = get_quran_service()
    ayah_text = quran_service.get_ayah_by_ref(surah, ayah)

    if ayah_text is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ayah {surah}:{ayah} not found",
        )

    return AyahResponse.from_ayah_text(ayah_text)


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    quran_service = get_quran_service()
    session_store = get_session_store()

    return {
        "status": "healthy",
        "quran_ayahs_loaded": quran_service.get_total_ayahs(),
        "active_sessions": session_store.count_sessions(),
    }


# Alias for frontend compatibility
@router.post("/session/start", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(request: CreateSessionRequest) -> CreateSessionResponse:
    """Alias for create_session - frontend compatibility."""
    return await create_session(request)


@router.get("/juz")
async def get_all_juz() -> list[dict]:
    """Get info for all 30 juz."""
    quran_service = get_quran_service()
    juz_list = []
    for juz_num in range(1, 31):
        boundaries = quran_service.get_juz_boundaries(juz_num)
        ayah_count = len(quran_service.get_ayahs_in_juz(juz_num))
        start = boundaries.get("start", {}) if boundaries else {}
        end = boundaries.get("end", {}) if boundaries else {}
        juz_list.append({
            "juz_number": juz_num,
            "name": f"Juz {juz_num}",
            "total_ayahs": ayah_count,
            "start_surah": start.get("surah", 1),
            "start_ayah": start.get("ayah", 1),
            "end_surah": end.get("surah", 114),
            "end_ayah": end.get("ayah", 6),
        })
    return juz_list


@router.get("/juz/{juz_number}")
async def get_juz_info(juz_number: int) -> dict:
    """Get info for a specific juz."""
    if juz_number < 1 or juz_number > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid juz number: {juz_number}. Must be 1-30.",
        )

    quran_service = get_quran_service()
    boundaries = quran_service.get_juz_boundaries(juz_number)
    ayahs = quran_service.get_ayahs_in_juz(juz_number)
    start = boundaries.get("start", {}) if boundaries else {}
    end = boundaries.get("end", {}) if boundaries else {}

    return {
        "juz_number": juz_number,
        "name": f"Juz {juz_number}",
        "total_ayahs": len(ayahs),
        "start_surah": start.get("surah", 1),
        "start_ayah": start.get("ayah", 1),
        "end_surah": end.get("surah", 114),
        "end_ayah": end.get("ayah", 6),
    }
