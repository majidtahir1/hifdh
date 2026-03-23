"""
Pytest Configuration and Fixtures for Hifdh Review App Backend Tests.

This module provides shared fixtures for testing the backend components.
"""

import json
import sys
from pathlib import Path
from typing import Generator

import pytest

# Ensure backend is in the path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from backend.models import AyahText, ReviewSession, SessionState, Mistake, MistakeType
from backend.alignment.normalizer import ArabicTextNormalizer
from backend.alignment.engine import ContinuationAlignmentEngine, TranscribedWord
from backend.alignment.classifier import MistakeClassifier
from backend.services.quran_data import QuranDataService
from backend.services.session_store import SessionStore


# Data directory path
DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture
def data_dir() -> Path:
    """Fixture providing path to the data directory."""
    return DATA_DIR


@pytest.fixture
def quran_json_path(data_dir: Path) -> Path:
    """Fixture providing path to quran.json."""
    return data_dir / "quran.json"


@pytest.fixture
def juz_mapping_path(data_dir: Path) -> Path:
    """Fixture providing path to juz_mapping.json."""
    return data_dir / "juz_mapping.json"


@pytest.fixture
def quran_data(quran_json_path: Path) -> list[dict]:
    """Fixture providing loaded quran.json data."""
    with open(quran_json_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def juz_mapping(juz_mapping_path: Path) -> list[dict]:
    """Fixture providing loaded juz_mapping.json data."""
    with open(juz_mapping_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def normalizer() -> ArabicTextNormalizer:
    """Fixture providing an Arabic text normalizer."""
    return ArabicTextNormalizer()


@pytest.fixture
def normalizer_with_hamza() -> ArabicTextNormalizer:
    """Fixture providing an Arabic text normalizer with hamza normalization."""
    return ArabicTextNormalizer(normalize_hamza=True)


@pytest.fixture
def sample_ayah() -> AyahText:
    """Fixture providing a sample ayah for testing."""
    return AyahText(
        surah=1,
        ayah=1,
        juz=1,
        audio_url="https://example.com/audio/1_1.mp3",
        text_uthmani="بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
        text_normalized="بسم الله الرحمن الرحيم",
        text_tokens=["بسم", "الله", "الرحمن", "الرحيم"],
    )


@pytest.fixture
def sample_ayahs() -> list[AyahText]:
    """Fixture providing a list of sample ayahs for testing."""
    return [
        AyahText(
            surah=1,
            ayah=2,
            juz=1,
            audio_url="https://example.com/audio/1_2.mp3",
            text_uthmani="الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
            text_normalized="الحمد لله رب العالمين",
            text_tokens=["الحمد", "لله", "رب", "العالمين"],
        ),
        AyahText(
            surah=1,
            ayah=3,
            juz=1,
            audio_url="https://example.com/audio/1_3.mp3",
            text_uthmani="الرَّحْمَٰنِ الرَّحِيمِ",
            text_normalized="الرحمن الرحيم",
            text_tokens=["الرحمن", "الرحيم"],
        ),
        AyahText(
            surah=1,
            ayah=4,
            juz=1,
            audio_url="https://example.com/audio/1_4.mp3",
            text_uthmani="مَالِكِ يَوْمِ الدِّينِ",
            text_normalized="مالك يوم الدين",
            text_tokens=["مالك", "يوم", "الدين"],
        ),
    ]


@pytest.fixture
def alignment_engine(sample_ayahs: list[AyahText]) -> ContinuationAlignmentEngine:
    """Fixture providing a configured alignment engine."""
    return ContinuationAlignmentEngine(expected_ayahs=sample_ayahs)


@pytest.fixture
def classifier() -> MistakeClassifier:
    """Fixture providing a mistake classifier."""
    return MistakeClassifier()


@pytest.fixture
def quran_service() -> QuranDataService:
    """Fixture providing the Quran data service."""
    return QuranDataService(data_dir=DATA_DIR)


@pytest.fixture
def session_store() -> Generator[SessionStore, None, None]:
    """Fixture providing a clean session store."""
    store = SessionStore()
    yield store
    store.clear_all_sessions()


@pytest.fixture
def sample_session(session_store: SessionStore, sample_ayah: AyahText, sample_ayahs: list[AyahText]) -> ReviewSession:
    """Fixture providing a sample review session."""
    session_id = session_store.create_session(
        juz_range=(1, 1),
        prompt_ayah=sample_ayah,
        expected_ayahs=sample_ayahs,
        num_ayahs_to_recite=3,
    )
    return session_store.get_session(session_id)


@pytest.fixture
def sample_mistake() -> Mistake:
    """Fixture providing a sample mistake for testing."""
    return Mistake(
        mistake_type=MistakeType.WRONG_WORD,
        ayah=(1, 2),
        word_index=0,
        expected="الحمد",
        received="الحامد",
        confidence=0.85,
        is_penalty=True,
        timestamp_ms=1000,
    )


def make_transcribed_word(
    text: str,
    confidence: float = 0.9,
    timestamp_ms: int = 0,
    is_final: bool = True,
) -> TranscribedWord:
    """Helper function to create TranscribedWord objects."""
    return TranscribedWord(
        text=text,
        confidence=confidence,
        timestamp_ms=timestamp_ms,
        is_final=is_final,
    )


@pytest.fixture
def make_word():
    """Fixture providing the make_transcribed_word helper."""
    return make_transcribed_word
